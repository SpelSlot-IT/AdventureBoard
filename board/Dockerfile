# Use slim Python
FROM python:3.11-slim

# Set workdir
WORKDIR /app

# Install dependencies
COPY board/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code from board directory
COPY board/ .

# Copy migrations directory from root
COPY migrations/ /app/migrations

# Make entrypoint script executable
RUN chmod +x /app/entrypoint.sh

# Expose Gunicorn port
EXPOSE 5000

# Use entrypoint to run migrations before starting app
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:5000", "app:create_app()"]
