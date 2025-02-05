from flask import Flask, Response 
import os
from minio import Minio
import pandas as pd
import io
import time
from threading import Thread
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

# Initialize Flask app
app = Flask(__name__)
@app.route('/metrics')
def metrics():
    data = generate_latest()
    return Response(data, mimetype=CONTENT_TYPE_LATEST)

@app.route('/health', methods=['GET'])
def health():
    """Liveness probe endpoint."""
    return "OK", 200

@app.route('/ready', methods=['GET'])
def readiness():
    """Readiness probe endpoint."""
    return "Ready", 200
# Function to start Flask server
def start_flask():
    print("Starting Flask server...")
    app.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False)


# MinIO configuration
MINIO_URL = os.getenv("MINIO_URL", "minio-service.default.svc.cluster.local:9000")
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
    """Check if a MinIO bucket exists; if not, create it."""
    try:
        if not client.bucket_exists(bucket_name):
            print(f"Bucket '{bucket_name}' does not exist. Creating...")
            client.make_bucket(bucket_name)
            print(f"Bucket '{bucket_name}' created successfully.")
        else:
            print(f"Bucket '{bucket_name}' already exists.")
    except Exception as e:
        print(f"Error checking/creating bucket {bucket_name}: {e}")


# Main data ingestion and processing loop
def main_loop():
    print("Starting main data ingestion process...")

    # Ensure MinIO buckets exist
    ensure_bucket(RAW_DATA_BUCKET)
    ensure_bucket(PROCESSED_DATA_BUCKET)
    ensure_bucket(MODELS_BUCKET)

    while True:
        try:
            raw_files = client.list_objects(RAW_DATA_BUCKET)
            for obj in raw_files:
                file_name = obj.object_name
                print(f"Processing file: {file_name}")

                # Fetch raw data
                response = client.get_object(RAW_DATA_BUCKET, file_name)
                raw_data = pd.read_csv(response)

                # Preprocess the data
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

        time.sleep(30)  # Wait before checking for new files again

if __name__ == "__main__":
    # Start Flask first to ensure readiness & liveness probes work
    flask_thread = Thread(target=start_flask)
    flask_thread.start()

    time.sleep(10)  # Ensure Flask starts before probes check

    # Check MinIO availability before starting data processing
    print("Checking MinIO availability...")
    while True:
        try:
            if client.bucket_exists(RAW_DATA_BUCKET):
                print("MinIO is up and running.")
                break
        except Exception as e:
            print(f"MinIO not reachable yet: {e}")
        time.sleep(5)  # Retry every 5 seconds

    # Start the main data ingestion process
    main_loop()
