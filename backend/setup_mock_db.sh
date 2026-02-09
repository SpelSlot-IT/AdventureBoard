#!/bin/bash
# Setup MariaDB in WSL for AdventureBoard

set -e

echo "=========================================="
echo "Setting up MariaDB in WSL for AdventureBoard"
echo "=========================================="

# Check if MariaDB/MySQL is already installed
if command -v mysql &> /dev/null; then
    echo "MariaDB/MySQL is already installed"
    mysql --version
else
    echo "Installing MariaDB server..."
    # Update apt (may show warnings about Docker repo, but will continue)
    sudo apt update || true
    sudo apt install -y mariadb-server
fi

# Start MariaDB service
echo ""
echo "Starting MariaDB service..."
sudo service mariadb start

# Check if MariaDB is running
if sudo service mariadb status | grep -q "active (running)"; then
    echo "✓ MariaDB is running"
else
    echo "✗ Failed to start MariaDB"
    exit 1
fi

# Set root password and create database
echo ""
echo "Setting up database and user..."
sudo mysql <<EOF
-- Set root password
ALTER USER 'root'@'localhost' IDENTIFIED BY 'mysql';
FLUSH PRIVILEGES;

-- Create database if it doesn't exist
CREATE DATABASE IF NOT EXISTS adventuredb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Show databases
SHOW DATABASES;
EOF

echo ""
echo "=========================================="
echo "MariaDB setup complete!"
echo "=========================================="
echo ""
echo "Database: adventuredb"
echo "User: root"
echo "Password: mysql"
echo "Host: localhost"

