import os
import pandas as pd
import yfinance as yf
from time import sleep
from datetime import datetime, timedelta
from minio import Minio
import io
from prometheus_client import Counter, start_http_server
import time


files_fetched = Counter('files_fetched_total', 'Number of CSV files successfully fetched')
fetch_errors = Counter('fetch_errors_total', 'Number of errors encountered when fetching stock/forex data')


EPHEMERAL_WAIT = 15

MINIO_URL = "http://minio-service.default.svc.cluster.local:9000"
MINIO_ACCESS_KEY = "admin"
MINIO_SECRET_KEY = "password"
RAW_DATA_BUCKET = "raw-data"


STOCKS = ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]
FOREX_PAIRS = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X"] 


minio_client = Minio(
    MINIO_URL,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)
def wait_for_minio():
    for _ in range(30):  # Retry for 30 seconds
        try:
            response = requests.get(f"{MINIO_URL}/minio/health/live")
            if response.status_code == 200:
                print("✅ MinIO is available!")
                return True
        except requests.exceptions.RequestException:
            pass
        print("⏳ Waiting for MinIO...")
        time.sleep(2)
    print("❌ MinIO is unavailable!")
    return False

if not wait_for_minio():
    exit(1)

if not minio_client.bucket_exists(RAW_DATA_BUCKET):
    minio_client.make_bucket(RAW_DATA_BUCKET)
    print(f"Bucket {RAW_DATA_BUCKET} created.")

def object_exists(bucket, object_name):
    """Check if object already exists in MinIO bucket."""
    try:
        minio_client.stat_object(bucket, object_name)
        return True
    except Exception:
        return False

def fetch_yfinance_data(symbol, is_forex=False):
    """Fetch last 5 days of historical data for a given stock or forex pair."""
    try:
        data = yf.download(symbol, period="5d", interval="1d")
        if data.empty:
            print(f"Error: No data found for {symbol}")
            fetch_errors.inc()
            return None
        
        data.reset_index(inplace=True)
        data["symbol"] = symbol
        if is_forex:
            data.rename(columns={"Adj Close": "close"}, inplace=True) 
        else:
            data.rename(columns={"Open": "open", "High": "high", "Low": "low", "Adj Close": "close", "Volume": "volume"}, inplace=True)

        return data

    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        fetch_errors.inc()
        return None

def upload_to_minio(file_name, data):
    """Upload a DataFrame as a CSV file to MinIO."""
    try:
        csv_data = data.to_csv(index=False).encode("utf-8")
        csv_stream = io.BytesIO(csv_data)

        minio_client.put_object(
            bucket_name=RAW_DATA_BUCKET,
            object_name=file_name,
            data=csv_stream,
            length=len(csv_data),
            content_type="text/csv"
        )
        print(f"File {file_name} uploaded to bucket {RAW_DATA_BUCKET}")
    except Exception as e:
        print(f"Error uploading file {file_name}: {e}")
        fetch_errors.inc()

def fetch_and_store_data():
    """Fetch stock & forex data and upload to MinIO if not already present."""
    all_symbols = STOCKS + FOREX_PAIRS
    for symbol in all_symbols:
        file_name = f"{symbol}_historical_data.csv"
        if object_exists(RAW_DATA_BUCKET, file_name):
            print(f"Data for {symbol} already exists in bucket {RAW_DATA_BUCKET}. Skipping fetch.")
            continue

        print(f"Fetching data for {symbol}...")
        is_forex = symbol in FOREX_PAIRS  
        data = fetch_yfinance_data(symbol, is_forex)
        if data is not None:
            upload_to_minio(file_name, data)
            files_fetched.inc()
        sleep(5) 

if __name__ == "__main__":
   
    start_http_server(8080)
    print("Prometheus metrics available on :8080/metrics")

    fetch_and_store_data()


    print(f"Sleeping {EPHEMERAL_WAIT}s before exit to allow scraping...")
    time.sleep(EPHEMERAL_WAIT)
    print("Exiting fetch script.")
