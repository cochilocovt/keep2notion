FROM python:3.11-slim

WORKDIR /app

# Copy shared module
COPY shared/ /app/shared/

# Copy service files
COPY services/sync_service/ /app/services/sync_service/

# Upgrade pip and install dependencies with retry
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --retries 5 --timeout 60 -r /app/shared/requirements.txt && \
    pip install --no-cache-dir --retries 5 --timeout 60 -r /app/services/sync_service/requirements.txt

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8005

# Run the service
CMD ["python", "-m", "uvicorn", "services.sync_service.main:app", "--host", "0.0.0.0", "--port", "8005"]
