#!/bin/bash
set -e

# Start PostgreSQL in background
docker-entrypoint.sh postgres &

# Wait for PostgreSQL to be ready
until pg_isready -U postgres -h localhost; do
  sleep 1
done

# Load sample data
psql -U postgres -f /docker-entrypoint-initdb.d/99-sample-data.sql

# Wait for PostgreSQL to finish
wait
