#!/bin/sh

# Clear all existing data from database
echo "Clearing database..."
python3 manage.py flush --noinput

# Always run database migrations
echo "Running migrations..."
python3 manage.py migrate --noinput

# Remove seeding flag since we cleared the database
rm -f /app/.db_seeded

# Seed only if not already seeded
if [ ! -f /app/.db_seeded ]; then
  echo "Seeding database..."
  python manage.py seed_data
  touch /app/.db_seeded
else
  echo "Database already seeded, skipping..."
fi

# Seed the database using the standalone script
echo "Seeding database..."
python3 movie_recommendation_backend/seed_users.py
touch /app/.db_seeded

# Start the app normally
echo "Starting server..."
exec gunicorn movie_recommendation_backend.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120 --log-level info

