FROM python:3.9-slim

# Install build dependencies for tgcrypto and other C extensions
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy all repo files into container
COPY . /app

# Install requirements after gcc is available
RUN pip install --no-cache-dir -r requirements.txt

# Start your bot
CMD ["python", "bot.py"]
