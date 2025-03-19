import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env

MINIO_URL = os.getenv("MINIO_URL", "minio-service.default.svc.cluster.local:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "admin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "password")
MODEL_BUCKET = os.getenv("MODEL_BUCKET", "models")
MODEL_FILE = os.getenv("MODEL_FILE", "stock_forex_price_prediction_model.zip")
