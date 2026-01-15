# Use slim Python
FROM python:3.11-slim

# Set workdir
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code from board directory
COPY . .

# Make entrypoint script executable
RUN chmod +x entrypoint.sh

# Expose Gunicorn port
EXPOSE 5000

# Use entrypoint to run migrations before starting app
ENTRYPOINT ["entrypoint.sh"]
CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:5000", "app:create_app()"]
