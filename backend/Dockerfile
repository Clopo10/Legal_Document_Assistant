# /backend/Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Copy requirements first for faster rebuilds
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the FastAPI code
COPY backend/ .

EXPOSE 8000

# Start FastAPI using Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]