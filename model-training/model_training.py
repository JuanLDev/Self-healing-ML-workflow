import os
import shutil
import pandas as pd
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, LSTM, Dropout
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler
from minio import Minio

# --- PROMETHEUS IMPORTS ---
from prometheus_client import Counter, start_http_server, Histogram
import time

EPHEMERAL_WAIT = 15  # Wait so we can be scraped

# METRICS
training_runs = Counter('training_runs_total', 'How many times the model training has run')
training_errors = Counter('training_errors_total', 'Number of errors during training')
training_duration = Histogram('training_duration_seconds',
                              'Histogram of training function durations')

MINIO_URL = "minio-service.default.svc.cluster.local:9000"
MINIO_ACCESS_KEY = "admin"
MINIO_SECRET_KEY = "password"
PROCESSED_DATA_BUCKET = "processed-data"
MODELS_BUCKET = "models"

client = Minio(
    MINIO_URL,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

def fetch_processed_data(file_name):
    try:
        print(f"Fetching processed data: {file_name} from bucket: {PROCESSED_DATA_BUCKET}")
        response = client.get_object(PROCESSED_DATA_BUCKET, file_name)
        data = pd.read_json(response)
        print("Processed data fetched successfully.")
        return data
    except Exception as e:
        print(f"Error fetching processed data: {e}")
        training_errors.inc()
        return None

def save_model_to_minio(model, model_name):
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
        print(f"Model uploaded successfully to bucket: {MODELS_BUCKET}/{model_name}.zip")

    except Exception as e:
        print(f"Error saving model to MinIO: {e}")
        training_errors.inc()

def build_model(input_shape):
    model = Sequential([
        LSTM(50, return_sequences=True, input_shape=input_shape),
        Dropout(0.2),
        LSTM(50, return_sequences=False),
        Dropout(0.2),
        Dense(25),
        Dense(1)
    ])
    model.compile(optimizer='adam', loss='mean_squared_error')
    print("Model architecture built successfully.")
    return model

@training_duration.time()  # measure how long the train_model function takes
def train_model(data):
    try:
        features = data.drop(['date', 'symbol', 'close'], axis=1)
        target = data['close']

        scaler = MinMaxScaler(feature_range=(0, 1))
        features_scaled = scaler.fit_transform(features)
        target_scaled = scaler.fit_transform(target.values.reshape(-1, 1))

        X_train, X_test, y_train, y_test = train_test_split(features_scaled, target_scaled,
                                                            test_size=0.2, random_state=42)

        X_train = X_train.reshape((X_train.shape[0], X_train.shape[1], 1))
        X_test = X_test.reshape((X_test.shape[0], X_test.shape[1], 1))

        model = build_model((X_train.shape[1], 1))
        model.fit(X_train, y_train, batch_size=32, epochs=10, validation_data=(X_test, y_test))

        print("Model training complete.")
        return model

    except Exception as e:
        print(f"Error during model training: {e}")
        training_errors.inc()
        return None

if __name__ == "__main__":
    # Start HTTP server for metrics
    start_http_server(8080)
    print("Prometheus metrics available at :8080/metrics")

    file_name = "AAPL_historical_data_processed.json" 
    processed_data = fetch_processed_data(file_name)

    if processed_data is not None:
        print("Starting model training...")
        training_runs.inc()  # increment training run
        trained_model = train_model(processed_data)

        if trained_model is not None:
            save_model_to_minio(trained_model, "stock_price_prediction_model")

    print(f"Sleeping {EPHEMERAL_WAIT}s to allow scraping, then exiting.")
    time.sleep(EPHEMERAL_WAIT)
    print("Exiting training script.")
