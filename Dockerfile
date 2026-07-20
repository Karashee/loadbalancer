# Use Python 3.11 slim image for smaller footprint
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY server/ ./server/

# Expose port 5000
EXPOSE 5000

# Set environment variable (can be overridden at runtime)
ENV SERVER_ID=unknown

# Run the Flask application
CMD ["python", "server/app.py"]
