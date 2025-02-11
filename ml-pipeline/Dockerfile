FROM python:3.8-slim

WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . .

# Ensure the run script is executable (if not already set)
RUN chmod +x run_pipeline.sh

# Use the run script as the container's entrypoint
ENTRYPOINT ["./run_pipeline.sh"]
