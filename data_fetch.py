import requests
import pandas as pd
from time import sleep
from datetime import datetime, timedelta
from minio import Minio
import io  # Import io to handle byte streams

# Alpha Vantage API key
API_KEY = "LHQ19J02WBX5VBCX"

# Top 5 companies (use stock symbols)
COMPANIES = ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]

# Alpha Vantage base URL
BASE_URL = "https://www.alphavantage.co/query"

# MinIO configuration
MINIO_URL = "minio-service.default.svc.cluster.local:9000"
MINIO_ACCESS_KEY = "admin"
MINIO_SECRET_KEY = "password"
RAW_DATA_BUCKET = "raw-data"

# Initialize MinIO client
minio_client = Minio(
    MINIO_URL,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

# Ensure bucket exists
if not minio_client.bucket_exists(RAW_DATA_BUCKET):
    minio_client.make_bucket(RAW_DATA_BUCKET)
    print(f"Bucket {RAW_DATA_BUCKET} created.")

def fetch_historical_data(symbol):
    """Fetch last 5 days of historical data for a given company."""
    try:
        # Request parameters for Alpha Vantage API
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "apikey": API_KEY,
            "outputsize": "compact"  # Returns ~100 days of data
        }

        # API request
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status()  # Raise exception for bad status codes

        data = response.json()

        # Extract the "Time Series" section
        if "Time Series (Daily)" not in data:
            print(f"Error: Could not fetch data for {symbol}. Response: {data}")
            return None

        time_series = data["Time Series (Daily)"]

        # Get the last 5 days of data
        today = datetime.today()
        last_5_days = []
        for i in range(5):
            date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            if date in time_series:
                day_data = {
                    "symbol": symbol,
                    "date": date,
                    "open": time_series[date]["1. open"],
                    "high": time_series[date]["2. high"],
                    "low": time_series[date]["3. low"],
                    "close": time_series[date]["4. close"],
                    "volume": time_series[date]["5. volume"]
                }
                last_5_days.append(day_data)

        return last_5_days

    except Exception as e:
        print(f"An error occurred for {symbol}: {e}")
        return None

def upload_to_minio(file_name, data):
    """Upload data to the MinIO raw-data bucket."""
    try:
        # Convert DataFrame to CSV in memory
        csv_data = data.to_csv(index=False).encode("utf-8")

        # Create a byte stream from the CSV data
        csv_stream = io.BytesIO(csv_data)

        # Upload to MinIO
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

def fetch_and_store_data():
    """Fetch data for the top 5 companies and upload to MinIO."""
    for company in COMPANIES:
        print(f"Fetching data for {company}...")
        data = fetch_historical_data(company)
        if data:
            # Convert list of dicts to DataFrame
            df = pd.DataFrame(data)
            file_name = f"{company}_historical_data.csv"

            # Upload to MinIO
            upload_to_minio(file_name, df)

        # Wait 15 seconds to avoid hitting the rate limit
        sleep(15)

if __name__ == "__main__":
    fetch_and_store_data()
