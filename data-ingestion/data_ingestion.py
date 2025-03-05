import os
import time
import io
import pandas as pd
from minio import Minio

from prometheus_client import Counter, start_http_server

EPHEMERAL_WAIT = 15  


ingestion_files_processed = Counter('ingestion_files_processed_total', 'Number of raw CSV files processed')
ingestion_rows_processed = Counter('ingestion_rows_processed_total', 'Number of rows processed during ingestion')

MINIO_URL = "http://minio-service.default.svc.cluster.local:9000"
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
    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name)
        print(f"Bucket '{bucket_name}' created.")
    else:
        print(f"Bucket '{bucket_name}' already exists.")

def standardize_dataframe(df, file_name):
    """
    Standardizes dataframe column names to match expected format for both Stocks and Forex.
    """
    df = df.rename(columns=lambda x: x.strip().lower()) 
    if 'date' not in df.columns:  
        print(f"Skipping {file_name}: No 'date' column found!")
        return None

    if "symbol" not in df.columns:
        df["symbol"] = file_name.split("_")[0] 


    if 'open' in df.columns and 'high' in df.columns and 'low' in df.columns and 'close' in df.columns:
        return df[['date', 'symbol', 'open', 'high', 'low', 'close', 'volume']]


    elif 'open' in df.columns and 'high' in df.columns and 'low' in df.columns and 'close' in df.columns:
        return df[['date', 'symbol', 'open', 'high', 'low', 'close', 'volume']]

    print(f"Skipping {file_name}: Required columns missing!")
    return None

def run_ingestion():
    """Run ingestion exactly once—process each CSV in raw-data, upload JSON to processed-data, then exit."""
    print("Starting one-time data ingestion...")

    
    ensure_bucket(RAW_DATA_BUCKET)
    ensure_bucket(PROCESSED_DATA_BUCKET)
    ensure_bucket(MODELS_BUCKET)

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
            ingestion_files_processed.inc()  

            row_count = len(raw_df)
            ingestion_rows_processed.inc(row_count)


            processed_df = standardize_dataframe(raw_df, file_name)
            if processed_df is None:
                continue

            processed_file_name = file_name.replace(".csv", "_processed.json")
            data_json = processed_df.to_json(orient='records', indent=2)

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

    start_http_server(8080)
    print("Prometheus metrics listening on :8080/metrics")

    run_ingestion()


    print(f"Sleeping {EPHEMERAL_WAIT}s before exit to allow scraping...")
    time.sleep(EPHEMERAL_WAIT)
    print("Exiting ingestion script.")
