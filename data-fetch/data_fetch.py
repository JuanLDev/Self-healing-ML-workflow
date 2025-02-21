import os
import requests
import pandas as pd
from time import sleep
from datetime import datetime, timedelta
from minio import Minio
import io

# --- PROMETHEUS IMPORTS ---
from prometheus_client import Counter, start_http_server
import time

# METRICS
files_fetched = Counter('files_fetched_total', 'Number of CSV files successfully fetched')
fetch_errors = Counter('fetch_errors_total', 'Number of errors encountered when fetching stock data')

# SLEEP DURATION (seconds) so ephemeral pod remains up for scraping
EPHEMERAL_WAIT = 15

# MINIO / API CONFIG
MINIO_URL = "minio-service.default.svc.cluster.local:9000"
API_KEY = "6IJ7XFL5KIUSUWCL"
COMPANIES = ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]
BASE_URL = "https://www.alphavantage.co/query"

MINIO_ACCESS_KEY = "admin"
MINIO_SECRET_KEY = "password"
RAW_DATA_BUCKET = "raw-data"

minio_client = Minio(
    MINIO_URL,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

if not minio_client.bucket_exists(RAW_DATA_BUCKET):
    minio_client.make_bucket(RAW_DATA_BUCKET)
    print(f"Bucket {RAW_DATA_BUCKET} created.")

def object_exists(bucket, object_name):
    try:
        minio_client.stat_object(bucket, object_name)
        return True
    except Exception:
        return False

def fetch_historical_data(symbol):
    """Fetch last 5 days of historical data for a given company."""
    try:
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "apikey": API_KEY,
            "outputsize": "compact"
        }
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()

        if "Time Series (Daily)" not in data:
            print(f"Error: Could not fetch data for {symbol}. Response: {data}")
            fetch_errors.inc()  # increment error counter
            return None

        time_series = data["Time Series (Daily)"]
        today = datetime.today()
        last_5_days = []
        for i in range(5):
            date_str = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            if date_str in time_series:
                day_data = {
                    "symbol": symbol,
                    "date": date_str,
                    "open": time_series[date_str]["1. open"],
                    "high": time_series[date_str]["2. high"],
                    "low": time_series[date_str]["3. low"],
                    "close": time_series[date_str]["4. close"],
                    "volume": time_series[date_str]["5. volume"]
                }
                last_5_days.append(day_data)

        return last_5_days

    except Exception as e:
        print(f"An error occurred for {symbol}: {e}")
        fetch_errors.inc()
        return None

def upload_to_minio(file_name, data):
    """Upload a DataFrame as a CSV file to the MinIO raw-data bucket."""
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
    """Fetch data for each company and upload to MinIO if not already present."""
    for company in COMPANIES:
        file_name = f"{company}_historical_data.csv"
        if object_exists(RAW_DATA_BUCKET, file_name):
            print(f"Data for {company} already exists in bucket {RAW_DATA_BUCKET}. Skipping fetch.")
            continue

        print(f"Fetching data for {company}...")
        data = fetch_historical_data(company)
        if data:
            df = pd.DataFrame(data)
            upload_to_minio(file_name, df)
            files_fetched.inc()  # increment success counter
        sleep(15)  # Delay to respect API rate limits

if __name__ == "__main__":
    # Start Prometheus metrics server on port 8080
    start_http_server(8080)
    print("Prometheus metrics available on :8080/metrics")

    fetch_and_store_data()

    # Keep container alive briefly so Prometheus can scrape
    print(f"Sleeping {EPHEMERAL_WAIT}s before exit to allow scraping...")
    time.sleep(EPHEMERAL_WAIT)
    print("Exiting fetch script.")
