import os
from minio import Minio
import pandas as pd
import io

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

# Preprocess the raw data
def preprocess_data(data):
    try:
        print("Starting data preprocessing...")
        # Example preprocessing: dropping NaN values and resetting index
        data = data.dropna().reset_index(drop=True)
        # Convert column names to lowercase (example normalization)
        data.columns = [col.lower() for col in data.columns]
        print("Data preprocessing completed successfully.")
        return data
    except Exception as e:
        print(f"Error during data preprocessing: {e}")
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
    print("Starting data ingestion process...")
    
    # List all files in the raw-data bucket
    try:
        raw_files = client.list_objects(RAW_DATA_BUCKET)
        for obj in raw_files:
            file_name = obj.object_name
            print(f"Processing file: {file_name}")

            # Fetch the raw data
            raw_data = fetch_raw_data(file_name)
            if raw_data is not None:
                try:
                    # Preprocess the data
                    print("Preprocessing data...")
                    processed_data = preprocess_data(raw_data)
                    
                    if processed_data is not None:
                        print("Preprocessing complete.")
                        # Upload the processed data
                        processed_file_name = file_name.replace(".csv", "_processed.json")
                        upload_processed_data(processed_file_name, processed_data)
                    else:
                        print(f"Failed to preprocess data for {file_name}. Skipping...")
                except Exception as e:
                    print(f"Error during preprocessing or upload: {e}")
            else:
                print(f"Skipping file: {file_name} due to errors.")
    except Exception as e:
        print(f"Error listing files in bucket {RAW_DATA_BUCKET}: {e}")
