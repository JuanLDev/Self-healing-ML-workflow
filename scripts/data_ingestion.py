import os
from minio import Minio
import pandas as pd
import io
import json
from data_preprocessing import preprocess_data

# MinIO configuration
MINIO_URL = "localhost:9000"
MINIO_ACCESS_KEY = "admin"
MINIO_SECRET_KEY = "password"
RAW_DATA_BUCKET = "raw-data"
PROCESSED_DATA_BUCKET = "processed-data"

# Initialize MinIO client
client = Minio(
    MINIO_URL,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

# Fetch raw data
def fetch_raw_data(file_name):
    try:
        print(f"Fetching raw data: {file_name} from bucket: {RAW_DATA_BUCKET}")
        response = client.get_object(RAW_DATA_BUCKET, file_name)
        data = pd.read_csv(response)
        print("Raw data fetched successfully.")
        return data
    except Exception as e:
        print(f"Error fetching raw data: {e}")
        return None

# Upload processed data
def upload_processed_data(file_name, data):
    try:
        if data.empty:
            print("Error: Processed data is empty. Skipping upload.")
            return

        # Serialize DataFrame to JSON
        data_json = data.to_json(orient='records', indent=2)

        # Upload JSON data to MinIO
        client.put_object(
            PROCESSED_DATA_BUCKET,
            file_name,
            data=io.BytesIO(data_json.encode('utf-8')),
            length=len(data_json.encode('utf-8')),
            content_type='application/json'
        )
        print(f"Processed data uploaded successfully to {PROCESSED_DATA_BUCKET}/{file_name}")
    except Exception as e:
        print(f"Error uploading processed data: {e}")

if __name__ == "__main__":
    # Example usage
    print("Starting data ingestion process...")
    raw_data = fetch_raw_data("example_data.csv")
    
    if raw_data is not None:
        print("Raw data retrieved, starting preprocessing...")
        try:
            processed_data = preprocess_data(raw_data)
            print("Preprocessing complete, uploading processed data...")
            upload_processed_data("processed_data.json", processed_data)
        except Exception as e:
            print(f"Error during preprocessing or upload: {e}")
    else:
        print("Raw data not available. Exiting process.")
