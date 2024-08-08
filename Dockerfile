FROM python:3.9-slim

# Set environment variables to ensure scripts are always run as expected
ENV PYTHONUNBUFFERED=1
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

# Create and set the working directory inside the container
WORKDIR /app

# Install Chromium and its dependencies
RUN apt-get update && \
    apt-get install -y \
    chromium-driver \
    libglib2.0-0 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxi6 \
    libxtst6 \
    libpangocairo-1.0-0 \
    libxrandr2 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libgtk-3-0 \
    libgbm1 \
    libpangoft2-1.0-0 \
    build-essential \
    curl \
    unzip \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire scraper directory into the container
COPY ..

# Set the default command to run the Python script
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5050"]