# Use slim Python
FROM python:3.11-slim

# Set workdir
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Expose Gunicorn port
EXPOSE 5000

# Start app with Gunicorn, pointing at the factory
CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:5000", "app:create_app()"]
