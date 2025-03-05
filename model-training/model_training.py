import os
import shutil
import pandas as pd
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, LSTM, Dropout
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler
from minio import Minio
from prometheus_client import Counter, start_http_server, Histogram
import time
import io


EPHEMERAL_WAIT = 15

training_runs = Counter('training_runs_total', 'How many times the model training has run')
training_errors = Counter('training_errors_total', 'Number of errors during training')
training_duration = Histogram('training_duration_seconds', 'Histogram of training function durations')

MINIO_URL = "http://minio-service.default.svc.cluster.local:9000"
MINIO_ACCESS_KEY = "admin"
MINIO_SECRET_KEY = "password"
PROCESSED_DATA_BUCKET = "processed-data"
MODELS_BUCKET = "models"

client = Minio(
    MINIO_URL.replace("http://", ""),  
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

def list_processed_files():
    try:
        files = [obj.object_name for obj in client.list_objects(PROCESSED_DATA_BUCKET) if obj.object_name.endswith("_processed.json")]
        print(f"Found {len(files)} processed data files.")
        return files
    except Exception as e:
        print(f"Error listing processed data files: {e}")
        return []

def fetch_processed_data(file_name):
    """Fetch processed data from MinIO and return as Pandas DataFrame."""
    try:
        print(f"Fetching processed data: {file_name}")
        response = client.get_object(PROCESSED_DATA_BUCKET, file_name)
        data = pd.read_json(io.BytesIO(response.read()))
        print(f"✅ Successfully fetched {file_name}, shape: {data.shape}")
        return data
    except Exception as e:
        print(f"❌ Error fetching processed data: {e}")
        training_errors.inc()
        return None

def save_model_to_minio(model, model_name):
    """Save and upload trained model to MinIO."""
    try:
        temp_model_dir = f"/tmp/{model_name}"
        model.save(temp_model_dir)
        print(f"Model saved locally to {temp_model_dir}")

        zip_file_path = f"/tmp/{model_name}.zip"
        shutil.make_archive(temp_model_dir, 'zip', temp_model_dir)
        print(f"Model directory compressed to {zip_file_path}")

        with open(zip_file_path, "rb") as zip_file:
            client.put_object(
                bucket_name=MODELS_BUCKET,
                object_name=f"{model_name}.zip",
                data=zip_file,
                length=os.path.getsize(zip_file_path),
                content_type="application/zip"
            )
        print(f"Model uploaded successfully to {MODELS_BUCKET}/{model_name}.zip")

    except Exception as e:
        print(f"❌ Error saving model to MinIO: {e}")
        training_errors.inc()

def build_model(input_shape):
    """Build LSTM model for stock and forex price prediction."""
    model = Sequential([
        LSTM(50, return_sequences=True, input_shape=input_shape),
        Dropout(0.2),
        LSTM(50, return_sequences=False),
        Dropout(0.2),
        Dense(25),
        Dense(1)
    ])
    model.compile(optimizer='adam', loss='mean_squared_error')
    print("✅ Model architecture built successfully.")
    return model

@training_duration.time()  
def train_model(data):
    """Preprocess data and train LSTM model."""
    try:
        print("\n🔥 Checking Processed Data Before Training 🔥")
        print("Data Columns:", data.columns)
        print("Sample Data:\n", data.head())

        data['symbol'] = data['symbol'].astype(str)

        # Ensure numeric conversion
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_cols:
            data[col] = pd.to_numeric(data[col], errors='coerce')  

        # Drop any row with NaN after conversion
        data = data.dropna()

        print(f"✅ Data After Cleaning, Shape: {data.shape}")

        if data.shape[0] == 0:
            raise ValueError("❌ All data was dropped after cleaning. Ensure valid numeric values exist.")

        features = data[['open', 'high', 'low', 'volume']] 
        target = data['close']

        print(f"📊 Features shape: {features.shape}, Target shape: {target.shape}")

        scaler = MinMaxScaler(feature_range=(0, 1))
        features_scaled = scaler.fit_transform(features)
        target_scaled = scaler.fit_transform(target.values.reshape(-1, 1))

        X_train, X_test, y_train, y_test = train_test_split(features_scaled, target_scaled, test_size=0.2, random_state=42)

        X_train = X_train.reshape((X_train.shape[0], X_train.shape[1], 1))
        X_test = X_test.reshape((X_test.shape[0], X_test.shape[1], 1))

        model = build_model((X_train.shape[1], 1))
        model.fit(X_train, y_train, batch_size=32, epochs=10, validation_data=(X_test, y_test))

        print("🎉 Model training complete.")
        return model

    except Exception as e:
        print(f"❌ Error during model training: {e}")
        training_errors.inc()
        return None

if __name__ == "__main__":
    start_http_server(8080)
    print("📡 Prometheus metrics available at :8080/metrics")

    processed_files = list_processed_files()

    if not processed_files:
        print("❌ No processed data files found. Exiting.")
        exit(1)

    combined_data = []
    
    for file_name in processed_files:
        data = fetch_processed_data(file_name)
        if data is not None:
            combined_data.append(data)

    if combined_data:
        all_data = pd.concat(combined_data, ignore_index=True)
        print("✅ All processed data fetched successfully.")

        print("🚀 Starting model training...")
        training_runs.inc() 
        trained_model = train_model(all_data)

        if trained_model is not None:
            save_model_to_minio(trained_model, "stock_forex_price_prediction_model")

    print(f"⏳ Sleeping {EPHEMERAL_WAIT}s to allow scraping, then exiting.")
    time.sleep(EPHEMERAL_WAIT)
    print("👋 Exiting training script.")
