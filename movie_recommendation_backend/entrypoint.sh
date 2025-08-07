#!/bin/sh

# Exit immediately if a command exits with a non-zero status
set -e

# Clear all existing data from database
echo "🧹 Clearing database..."
python3 manage.py flush --noinput

# Always run database migrations
echo "🚀 Running migrations..."
python3 manage.py migrate --noinput

# Remove seeding flag since we cleared the database
rm -f /app/.db_seeded

# Seed the database using the standalone script
echo "Seeding database..."
python3 movie_recommendation_backend/seed_users.py
touch /app/.db_seeded

# Seed genres (required before seeding movies)
echo "🌱 Seeding genres..."
python3 manage.py seed_genres

# Seed popular movies
echo "🎬 Seeding popular movies (5 pages)..."
python3 manage.py seed_movies --popular --pages 5 --force

# Optional: seed users if still needed
# echo "👤 Seeding users..."
# python3 movie_recommendation_backend/seed_users.py

# Mark database as seeded
touch /app/.db_seeded

# Start the app normally
echo "Starting server..."
exec gunicorn movie_recommendation_backend.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120 --log-level info


