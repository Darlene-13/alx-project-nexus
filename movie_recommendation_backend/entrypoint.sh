#!/bin/sh

# Always run database migrations
echo "Running migrations..."
python3 manage.py migrate --noinput

# Seed only if not already seeded
if [ ! -f /app/.db_seeded ]; then
  echo "Seeding database..."
  python manage.py seed_data
  touch /app/.db_seeded
else
  echo "Database already seeded, skipping..."
fi

# Start the app normally
echo "Starting server..."
exec gunicorn movie_recommendation_backend.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120 --log-level info

