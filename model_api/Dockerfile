FROM python:3.14.1-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get upgrade -y zlib1g && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir tensorflow==2.16.1 keras==3.0.5

COPY requirements.txt .
COPY main.py .
COPY config.py .
COPY .env .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
