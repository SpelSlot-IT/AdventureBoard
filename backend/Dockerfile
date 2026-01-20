# Use slim Python
FROM python:3.11-slim

# Set workdir
WORKDIR /app

#
# Install dependencies with uv
COPY pyproject.toml .
RUN pip install --no-cache-dir uv
RUN uv sync --system --no-dev

# Copy app code
COPY . .

# Make entrypoint script executable
RUN chmod +x entrypoint.sh

# Expose Gunicorn port
EXPOSE 5000

# Use entrypoint to run migrations before starting app
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:5000", "app:create_app()"]
