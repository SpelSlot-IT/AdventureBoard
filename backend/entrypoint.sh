#!/bin/bash
set -e

# Wait for database to be ready (optional, but helpful)
echo "Waiting for database to be ready..."
sleep 2

# Change to the app directory where migrations can find the app
cd /app

# Set Flask app environment variable
export FLASK_APP=app:create_app

# Run database migrations
echo "Running database migrations..."
flask db upgrade || {
    echo "Migration failed, but continuing..."
}

# Start the application
echo "Starting application..."
exec "$@"
