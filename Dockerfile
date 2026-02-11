FROM python:3.11-slim

# Metadata
LABEL maintainer="VigilAI Team"
LABEL description="AI Copilot for Streamers - Twitch Chat Moderation Bot"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
# This will take a while on first build due to torch and transformers
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directory for model cache
RUN mkdir -p /app/.cache

# Set environment variable for Hugging Face cache
ENV TRANSFORMERS_CACHE=/app/.cache
ENV HF_HOME=/app/.cache

# Run the application
CMD ["python", "main.py"]
