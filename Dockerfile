FROM python:3.11-slim

WORKDIR /app

# Add cache busting layer
ARG CACHEBUST=1

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Upgrade pip and setuptools
RUN pip install --no-cache-dir --upgrade pip setuptools

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

CMD ["python", "bot.py"]
