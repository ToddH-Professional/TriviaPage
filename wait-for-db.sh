#!/usr/bin/env bash
set -e

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
while ! nc -z postgres 5432; do
  sleep 1
done
echo "PostgreSQL is up!"

# Run migrations
flask db init || true  # Ignore error if already initialized
flask db migrate -m "Initial migration"
flask db upgrade

# Start the application
exec flask run --host=0.0.0.0 --port=8080
