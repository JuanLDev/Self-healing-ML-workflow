#!/bin/bash
set -e  # This causes the script to exit immediately if any command returns a non-zero exit code

echo "Starting data fetch..."
python data_fetch.py
echo "Data fetch complete."

echo "Starting data ingestion..."
python data_ingestion.py
echo "Data ingestion complete."

echo "Starting model training..."
python model_training.py
echo "Model training complete."
