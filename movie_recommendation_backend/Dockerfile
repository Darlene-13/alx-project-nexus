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

# Copy the requirements file into the cointainer
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . /app/

# Create the directory for static files
RUN mkdir -p /app/staticfiles/
# Create a directory for the media files
RUN mkdir -p /app/mediafiles/

# Create  non-root user for security
RUN adduser --disabled-password --gecos '' movie_recommendation_user \
    && chown -R movie_recommendation_user:movie_recommendation_user /app
