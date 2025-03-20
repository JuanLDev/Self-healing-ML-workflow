import os
import io
import zipfile
import numpy as np
import pandas as pd
import tensorflow as tf
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from minio import Minio
from config import MINIO_URL, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MODEL_BUCKET, MODEL_FILE

app = FastAPI(title="Stock & Forex Price Prediction API", version="1.0")

# MinIO Client
minio_client = Minio(
    MINIO_URL,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

# Model Storage Path
MODEL_PATH = "/tmp/model"
MODEL_FILE_PATH = os.path.join(MODEL_PATH, "model.keras")

class PredictionRequest(BaseModel):
    open: float
    high: float
    low: float
    volume: float

def download_and_load_model():
    """Downloads the model from MinIO and loads it into TensorFlow."""
    try:
        os.makedirs(MODEL_PATH, exist_ok=True)

        try:
            minio_client.stat_object(MODEL_BUCKET, MODEL_FILE)
        except minio.error.S3Error as e:
            if e.code == "NoSuchKey":
                print(f"⚠️  Model file '{MODEL_FILE}' not found in bucket '{MODEL_BUCKET}'")
                return None
            raise  

        response = minio_client.get_object(MODEL_BUCKET, MODEL_FILE)
        with zipfile.ZipFile(io.BytesIO(response.read()), "r") as zip_ref:
            zip_ref.extractall(MODEL_PATH)

        print("✅ Model downloaded and extracted successfully!")
        return tf.keras.models.load_model(MODEL_FILE_PATH)

    except Exception as e:
        print(f"🚨 Error loading model: {str(e)}")
        return None


model = download_and_load_model()

@app.get("/")
def root():
    return {"message": "Stock & Forex Prediction API is running"}

@app.post("/predict/")
def predict(data: PredictionRequest):
    """Make a prediction using the model."""
    if not model:
        raise HTTPException(
            status_code=503,
            detail="Model not loaded. Please check if the model file exists in storage."
        )

    try:
        features = np.array([[data.open, data.high, data.low, data.volume]])
        prediction = model.predict(features)[0][0]
        return {"predicted_price": float(prediction)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {e}")

@app.get("/healthz")
def health():
    """Health check endpoint for Kubernetes probes."""
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "model_status": "Model loaded successfully" if model else "Model file not found"
    }
