FROM python:3.9-slim

# Install build tools (needed for tgcrypto & other C extensions)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run your bot
CMD ["python", "main.py"]
