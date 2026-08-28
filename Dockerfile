# Use Python 3.10 slim for PaddleOCR compatibility on Linux
FROM python:3.10-slim

# Prevent Python from writing .pyc and buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Install required system dependencies for OpenCV and PaddleOCR on Linux
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libgomp1 \
    libgthread-2.0-0 \
    fontconfig \
    libfontconfig1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app/ /app/app/
COPY web_app/ /app/web_app/

# Expose port
EXPOSE 8000

# Start Uvicorn server dynamically binding to Railway $PORT
CMD ["sh", "-c", "uvicorn web_app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
