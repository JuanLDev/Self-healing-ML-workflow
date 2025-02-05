# Base image with Python
FROM python:3.8-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system utilities
RUN apt-get update && apt-get install -y curl procps

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the project files into the container
COPY . /app/

# Expose a port for health checks (used later in Kubernetes)
EXPOSE 8080

# Define the default command to run the pipeline
CMD ["python", "data_ingestion.py"]
