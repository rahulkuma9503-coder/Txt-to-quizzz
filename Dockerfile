# Use official Python base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables (for local development)
# For production, set these in runtime environment
ENV PORT=10000
ENV TELEGRAM_TOKEN=""
ENV OWNER_ID=""
ENV MONGO_URI=""

# Run the application
CMD ["python", "bot.py"]
