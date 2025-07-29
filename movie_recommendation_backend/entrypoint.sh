#!/bin/sh

# Optional: run database migrations if RUN_MIGRATIONS is true
if [ "$RUN_MIGRATIONS" = "true" ]; then
    echo "🟡 Running migrations..."
    python3 manage.py migrate --noinput
fi

# Start the app normally
echo "🟢 Starting server..."
exec gunicorn movie_recommendation_backend.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120 --log-level info
