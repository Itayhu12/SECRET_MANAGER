FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY ./ .

# Create storage directory
RUN mkdir -p storage/secrets storage/shares

# Environment defaults (override at runtime)
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV STORAGE_PATH=storage

# Expose port
EXPOSE 5000

# Run with waitress (production WSGI)
CMD ["python", "-m", "waitress", "--host=0.0.0.0", "--port=5000", "app:create_app()"]