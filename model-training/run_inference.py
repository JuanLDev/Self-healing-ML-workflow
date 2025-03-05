import os
import io
import json
import zipfile
import shutil
import numpy as np
import pandas as pd
import tensorflow as tf
from minio import Minio
from sklearn.preprocessing import MinMaxScaler

MINIO_URL = "127.0.0.1:9000"
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

MODEL_NAME = "stock_forex_price_prediction_model.zip"
MODEL_DIR = "/tmp/stock_forex_price_prediction_model"


FEATURES = ["open", "high", "low", "volume"]

def load_model():
    """Fetch and load the trained model from MinIO."""
    try:
        print(f"📥 Fetching model: {MODEL_NAME} from MinIO...")
        response = client.get_object(MODELS_BUCKET, MODEL_NAME)
        model_zip_path = f"/tmp/{MODEL_NAME}"

        with open(model_zip_path, "wb") as file_data:
            for d in response.stream(32 * 1024):
                file_data.write(d)

        if os.path.exists(MODEL_DIR):
            shutil.rmtree(MODEL_DIR)

        with zipfile.ZipFile(model_zip_path, "r") as zip_ref:
            zip_ref.extractall(MODEL_DIR)

        print(f"✅ Model successfully extracted to {MODEL_DIR}")
        return tf.keras.models.load_model(MODEL_DIR)

    except Exception as e:
        print(f"❌ Error loading model from MinIO: {e}")
        return None

def fetch_latest_data():
    """Fetch the latest available processed data for all assets."""
    try:
        data_frames = []
        for obj in client.list_objects(PROCESSED_DATA_BUCKET):
            file_name = obj.object_name
            print(f"📥 Fetching processed data: {file_name}")
            response = client.get_object(PROCESSED_DATA_BUCKET, file_name)
            df = pd.read_json(response)
            data_frames.append(df)

        if data_frames:
            combined_df = pd.concat(data_frames, ignore_index=True)
            print(f"✅ Successfully fetched and combined {len(data_frames)} datasets.")
            return combined_df
        else:
            print("❌ No processed data found.")
            return None

    except Exception as e:
        print(f"❌ Error fetching processed data: {e}")
        return None

def preprocess_data(data):
    """Prepares data for prediction."""
    if data is None or data.empty:
        print("❌ No data available for predictions.")
        return None, None, None

    print("\n🔥 Checking Processed Data Before Prediction 🔥")
    print(f"Data Columns: {data.columns}")
    print("Sample Data:")
    print(data.head())

    for col in FEATURES + ["close"]:
        data[col] = pd.to_numeric(data[col], errors="coerce")

    if data[FEATURES + ["close"]].isnull().sum().sum() > 0:
        print("⚠️ Warning: Found NaN values after conversion. Filling with column mean.")
        data[FEATURES + ["close"]] = data[FEATURES + ["close"]].fillna(data[FEATURES + ["close"]].mean())

    print(f"\n📊 Using Features: {FEATURES}")
    print(f"🔎 Data types before scaling:\n{data[FEATURES].dtypes}")

    scaler = MinMaxScaler()
    features_scaled = scaler.fit_transform(data[FEATURES])  

    features_scaled = features_scaled.reshape((features_scaled.shape[0], features_scaled.shape[1], 1))

    return features_scaled, scaler, data

def predict(model):
    """Run inference using the trained model on the fetched data."""
    data = fetch_latest_data()
    if data is None:
        return

    features_scaled, scaler, processed_data = preprocess_data(data)
    if features_scaled is None:
        return

    print("🚀 Running Model Prediction...")
    predictions = model.predict(features_scaled)

    processed_data["close"] = pd.to_numeric(processed_data["close"], errors="coerce")
    min_price = processed_data["close"].min()
    max_price = processed_data["close"].max()

    predicted_prices = predictions.flatten() * (max_price - min_price) + min_price

    processed_data["predicted_price"] = predicted_prices

    print("\n📊 **Predictions:**")
    for _, row in processed_data.iterrows():
        print(f"🔹 {row['symbol']}: Predicted Close Price = {row['predicted_price']:.4f}")

if __name__ == "__main__":
    model = load_model()
    if model is None:
        exit(1)

    predict(model)
