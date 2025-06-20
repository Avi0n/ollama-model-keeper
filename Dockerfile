# Build stage
FROM python:3.10-slim AS builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements (if separate, here we'd copy requirements.txt)
# For simplicity, install ollama directly
RUN pip install --no-cache-dir ollama

# Copy the script
COPY ollama_model_keeper.py .

# Run stage
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Create non-root user
RUN useradd -m -r appuser && chown appuser:appuser /app

# Copy Python dependencies from builder
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy the script
COPY --from=builder /app/ollama_model_keeper.py .

# Switch to non-root user
USER appuser

# Set entrypoint to run the script
ENTRYPOINT ["python3", "ollama_model_keeper.py"]