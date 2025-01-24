import pandas as pd

# Preprocessing function
def preprocess_data(data):
    # Drop missing values
    data = data.dropna()

    # Normalize numerical columns (example)
    numeric_columns = data.select_dtypes(include=["float64", "int64"]).columns
    data[numeric_columns] = (data[numeric_columns] - data[numeric_columns].mean()) / data[numeric_columns].std()

    # One-hot encode categorical columns (example)
    categorical_columns = data.select_dtypes(include=["object"]).columns
    data = pd.get_dummies(data, columns=categorical_columns)

    print("Data preprocessing complete!")
    return data

if __name__ == "__main__":
    # Load raw data
    raw_data = pd.read_csv("example_data.csv")  # Replace with data_ingestion output
    processed_data = preprocess_data(raw_data)
    print(processed_data.head())
