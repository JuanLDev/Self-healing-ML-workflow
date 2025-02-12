import os
import time
import io
import pandas as pd
from minio import Minio

MINIO_URL = "minio-service.default.svc.cluster.local:9000"
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "admin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "password")
RAW_DATA_BUCKET = "raw-data"
PROCESSED_DATA_BUCKET = "processed-data"
MODELS_BUCKET = "models"

client = Minio(
    MINIO_URL,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

def ensure_bucket(bucket_name):
    """Check if a MinIO bucket exists; if not, create it."""
    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name)
        print(f"Bucket '{bucket_name}' created.")
    else:
        print(f"Bucket '{bucket_name}' already exists.")

def run_ingestion():
    """Run ingestion exactly once—process each CSV in raw-data, upload to processed-data, then exit."""
    print("Starting one-time data ingestion...")

    # Ensure buckets exist
    ensure_bucket(RAW_DATA_BUCKET)
    ensure_bucket(PROCESSED_DATA_BUCKET)
    ensure_bucket(MODELS_BUCKET)

    # List all objects in RAW_DATA_BUCKET
    raw_files = client.list_objects(RAW_DATA_BUCKET)
    for obj in raw_files:
        file_name = obj.object_name
        if not file_name.endswith(".csv"):
            print(f"Skipping non-CSV file: {file_name}")
            continue

        print(f"Processing file: {file_name}")
        try:
            response = client.get_object(RAW_DATA_BUCKET, file_name)
            raw_df = pd.read_csv(response)

            # Example preprocessing: drop NaN, rename columns to lowercase
            processed_df = raw_df.dropna().reset_index(drop=True)
            processed_df.columns = [c.lower() for c in processed_df.columns]

            processed_file_name = file_name.replace(".csv", "_processed.json")
            data_json = processed_df.to_json(orient='records', indent=2)

            # Upload processed JSON
            client.put_object(
                PROCESSED_DATA_BUCKET,
                processed_file_name,
                data=io.BytesIO(data_json.encode('utf-8')),
                length=len(data_json.encode('utf-8')),
                content_type='application/json'
            )
            print(f"Processed data uploaded: {PROCESSED_DATA_BUCKET}/{processed_file_name}")

        except Exception as e:
            print(f"Error processing {file_name}: {e}")

    print("Data ingestion completed. Exiting.")

if __name__ == "__main__":
    run_ingestion()
