# Use slim Python
FROM python:3.11-slim

# Set workdir
WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies with uv
ENV UV_PROJECT_ENVIRONMENT=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"
RUN uv sync --no-dev

# Copy app code
COPY . .

# Make entrypoint script executable
RUN chmod +x entrypoint.sh

# Expose Gunicorn port
EXPOSE 5000

# Use entrypoint to run migrations before starting app
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:5000", "app:create_app()"]
