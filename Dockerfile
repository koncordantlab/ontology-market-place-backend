# Base image: Python 3.11 on Debian Bookworm slim (compatible with Leapcell and Vercel)
FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080

WORKDIR /app

# Install runtime dependencies that are commonly needed by Python packages
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       curl \
       ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first for better docker layer caching
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Copy the app source code
COPY . .

# Expose default port (most platforms use $PORT; default to 8080)
EXPOSE ${PORT}

# Run the FastAPI app (use sh -c to expand ${PORT} environment variable)
CMD ["sh", "-c", "python -m uvicorn main:app --host 0.0.0.0 --port ${PORT}"]