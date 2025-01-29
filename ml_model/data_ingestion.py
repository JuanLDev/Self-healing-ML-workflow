from flask import Flask
import os
from minio import Minio
import pandas as pd
import io
import time
from threading import Thread

# Initialize Flask app
app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health():
    """Liveness probe endpoint."""
    return "OK", 200

@app.route('/ready', methods=['GET'])
def readiness():
    """Readiness probe endpoint."""
    return "Ready", 200

# MinIO configuration
MINIO_URL = os.getenv("MINIO_URL", "localhost:9000")
MINIO_ACCESS_KEY = "admin"
MINIO_SECRET_KEY = "password"
RAW_DATA_BUCKET = "raw-data"
PROCESSED_DATA_BUCKET = "processed-data"
MODELS_BUCKET = "models"

# Initialize MinIO client
client = Minio(
    MINIO_URL,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

# Ensure required MinIO buckets exist
def ensure_bucket(bucket_name):
    if not client.bucket_exists(bucket_name):
        print(f"Bucket '{bucket_name}' does not exist. Creating...")
        client.make_bucket(bucket_name)
        print(f"Bucket '{bucket_name}' created successfully.")

# Flask must start before probes begin
def start_flask():
    print("Starting Flask server...")
    app.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False)

# Main function
if __name__ == "__main__":
    # Ensure MinIO is reachable before starting
    print("Checking MinIO availability...")
    while True:
        try:
            if client.bucket_exists("raw-data"):
                print("MinIO is up and running.")
                break
        except Exception as e:
            print(f"MinIO not reachable yet: {e}")
        time.sleep(5)  # Retry every 5 seconds

    # Start Flask server first
    flask_thread = Thread(target=start_flask)
    flask_thread.start()

    time.sleep(10)  # Ensure Flask starts before probes trigger

    print("Starting main data ingestion process...")

    # Ensure buckets exist
    ensure_bucket(RAW_DATA_BUCKET)
    ensure_bucket(PROCESSED_DATA_BUCKET)
    ensure_bucket(MODELS_BUCKET)

    while True:
        try:
            raw_files = client.list_objects(RAW_DATA_BUCKET)
            for obj in raw_files:
                file_name = obj.object_name
                print(f"Processing file: {file_name}")

                # Fetch the raw data
                response = client.get_object(RAW_DATA_BUCKET, file_name)
                raw_data = pd.read_csv(response)

                # Preprocess the data
                print("Preprocessing data...")
                processed_data = raw_data.dropna().reset_index(drop=True)
                processed_data.columns = [col.lower() for col in processed_data.columns]

                # Upload processed data
                processed_file_name = file_name.replace(".csv", "_processed.json")
                data_json = processed_data.to_json(orient='records', indent=2)
                client.put_object(
                    PROCESSED_DATA_BUCKET,
                    processed_file_name,
                    data=io.BytesIO(data_json.encode('utf-8')),
                    length=len(data_json.encode('utf-8')),
                    content_type='application/json'
                )
                print(f"Processed data uploaded to {PROCESSED_DATA_BUCKET}/{processed_file_name}")

        except Exception as e:
            print(f"Error processing files: {e}")

        time.sleep(30)


if __name__ == "__main__":
    # Ensure MinIO is reachable before starting
    print("Checking MinIO availability...")
    while True:
        try:
            if client.bucket_exists("raw-data"):
                print("MinIO is up and running.")
                break
        except Exception as e:
            print(f"MinIO not reachable yet: {e}")
        time.sleep(5)  # Retry every 5 seconds

    print("Starting Flask server...")
    app.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False)

    # Start the main data processing loop
    main_loop()
