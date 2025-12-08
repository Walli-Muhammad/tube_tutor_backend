# Use a lightweight Python base image
FROM python:3.9-slim

# 1. Install system dependencies (FFmpeg is crucial here)
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean

# 2. Set up the working directory
WORKDIR /app

# 3. Copy your requirement file and install Python libraries
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy the rest of your application code
COPY . .

# 5. Open port 10000
EXPOSE 10000

# 6. Run the app using Gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:10000", "app:app", "--timeout", "120"]