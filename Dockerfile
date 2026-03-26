# Use official Python image as base image
FROM python:3.10

# Set working directory
WORKDIR /app

# Skip system package installation - network is blocked
# The base python image includes necessary tools

# Copy application code into the container
COPY . /app

# Upgrade pip and install dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install gunicorn

# Create non-privileged user and set file permissions
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app && \
    chmod -R 755 /app && \
    # Make code directories read-only for appuser (prevent code modification)
    chmod -R 555 /app/model && \
    chmod -R 555 /app/api && \
    # Keep /app/instance writable for database and uploads
    chmod -R 755 /app/instance && \
    # Restrict access to /proc to prevent reading parent process env vars
    chmod 700 /proc 2>/dev/null || true

# Switch to non-privileged user
USER appuser

# Set environment variables
ENV FLASK_ENV=production \
    GUNICORN_CMD_ARGS="--workers=5 --threads=2 --bind=0.0.0.0:8328 --timeout=30 --access-logfile -"

# Expose application port
EXPOSE 8328

# Start Gunicorn server
CMD ["gunicorn", "main:app"]
