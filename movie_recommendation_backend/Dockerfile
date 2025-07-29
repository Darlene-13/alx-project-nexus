# Use official python runtime as a base image
FROM python:3.11-slim

# Set the environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    postgresql-client \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . /app/

# Create the directory for static and media files
RUN mkdir -p /app/staticfiles/ /app/mediafiles/

# ✅ Copy entrypoint before switching to non-root user
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# ✅ Create non-root user for security (after entrypoint is ready)
RUN adduser --disabled-password --gecos '' movie_recommendation_user \
    && chown -R movie_recommendation_user:movie_recommendation_user /app \
    && chown movie_recommendation_user:movie_recommendation_user /entrypoint.sh

# ✅ Switch to non-root user
USER movie_recommendation_user

# Set the entrypoint
ENTRYPOINT ["/entrypoint.sh"]

# Expose port
EXPOSE 8000

# Optional fallback (usually ignored if entrypoint handles startup)
CMD ["python3", "manage.py", "runserver", "0.0.0.0:8000"]
