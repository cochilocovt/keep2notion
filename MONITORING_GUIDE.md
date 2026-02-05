# Monitoring Guide - Google Keep to Notion Sync

This guide explains how to monitor your sync application, check logs, and troubleshoot issues.

## Table of Contents
1. [Monitoring Tools](#monitoring-tools)
2. [Checking Service Health](#checking-service-health)
3. [Viewing Logs](#viewing-logs)
4. [Managing Sync Jobs](#managing-sync-jobs)
5. [Common Issues](#common-issues)

---

## Monitoring Tools

### 1. Admin Interface (Web UI)
**URL**: http://localhost:8000

The admin interface provides:
- Dashboard with sync statistics
- List of all sync jobs with filters
- Detailed view of each job with logs
- Ability to trigger, retry, and abort sync jobs
- Credential management

### 2. Docker Logs
View real-time logs from Docker containers:

```bash
# View all services
docker-compose logs -f

# View specific service
docker-compose logs -f sync_service
docker-compose logs -f keep_extractor
docker-compose logs -f notion_writer
docker-compose logs -f admin_interface

# View last N lines
docker-compose logs --tail 100 sync_service

# View logs since specific time
docker-compose logs --since 30m sync_service
```

### 3. Service Status
Check if all services are running:

```bash
# List running containers
docker-compose ps

# Check service health
curl http://localhost:8005/health  # Sync Service
curl http://localhost:8003/health  # Keep Extractor
curl http://localhost:8004/health  # Notion Writer
curl http://localhost:8000/        # Admin Interface
```

---

## Checking Service Health

### Health Check Endpoints

Each service has a `/health` endpoint:

**Sync Service** (Port 8005):
```bash
curl http://localhost:8005/health
```

Response:
```json
{
  "status": "healthy",
  "service": "sync_service",
  "version": "0.1.0",
  "dependencies": {
    "database": "up",
    "keep_extractor": "up",
    "notion_writer": "up"
  }
}
```

**Keep Extractor** (Port 8003):
```bash
curl http://localhost:8003/health
```

**Notion Writer** (Port 8004):
```bash
curl http://localhost:8004/health
```

### Dashboard Health Status

Visit http://localhost:8000 to see:
- Overall system health
- Database connectivity
- Sync service status
- Recent job statistics

---

## Viewing Logs

### 1. Admin Interface Logs

**View Job Logs**:
1. Go to http://localhost:8000/sync-jobs/
2. Click on any job to see detailed logs
3. Logs show:
   - Timestamp
   - Log level (INFO, WARNING, ERROR)
   - Note ID (if applicable)
   - Message

**Filter Logs**:
- Logs are paginated (100 per page)
- Sorted by most recent first
- Color-coded by severity

### 2. Docker Container Logs

**Real-time monitoring**:
```bash
# Follow all logs
docker-compose logs -f

# Follow specific service with grep filter
docker-compose logs -f sync_service | grep ERROR
docker-compose logs -f keep_extractor | grep "Successfully uploaded"
```

**Search logs for specific errors**:
```bash
# Find authentication errors
docker-compose logs sync_service | grep -i "authentication"

# Find timeout errors
docker-compose logs sync_service | grep -i "timeout"

# Find failed notes
docker-compose logs sync_service | grep -i "failed to process"
```

**Export logs to file**:
```bash
# Export all logs
docker-compose logs > sync_logs_$(date +%Y%m%d_%H%M%S).log

# Export specific service logs
docker-compose logs sync_service > sync_service_$(date +%Y%m%d_%H%M%S).log
```

### 3. Log Locations

Logs are stored in:
- **Docker stdout/stderr**: Captured by Docker daemon
- **Database**: Sync logs stored in `sync_logs` table
- **Admin Interface**: Accessible via web UI

---

## Managing Sync Jobs

### View Sync Jobs

**Admin Interface**:
1. Go to http://localhost:8000/sync-jobs/
2. Filter by:
   - Status (running, completed, failed, cancelled)
   - User ID
   - Date range
3. Click on job ID to see details

**Job Statuses**:
- `queued`: Job created, waiting to start
- `running`: Job is currently executing
- `completed`: Job finished successfully
- `failed`: Job encountered an error
- `cancelled`: Job was aborted by user

### Trigger Manual Sync

**Via Admin Interface**:
1. Go to http://localhost:8000/sync/trigger/
2. Select user
3. Choose sync type:
   - **Full Sync**: Sync all notes
   - **Incremental Sync**: Only sync modified notes
4. Click "Trigger Sync"

**Via API**:
```bash
curl -X POST http://localhost:8005/internal/sync/execute \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "your-email@gmail.com",
    "full_sync": false
  }'
```

### Abort Running Job

**Via Admin Interface**:
1. Go to http://localhost:8000/sync-jobs/
2. Click on the running job
3. Click "Abort Sync Job" button
4. Confirm the action

**Via API**:
```bash
curl -X POST http://localhost:8005/internal/sync/abort/{job_id}
```

**Note**: Aborting a job marks it as cancelled but may not immediately stop the actual sync process if it's already running. The job will be marked as cancelled in the database.

### Retry Failed Job

**Via Admin Interface**:
1. Go to http://localhost:8000/sync-jobs/
2. Click on the failed job
3. Click "Retry Sync Job" button
4. A new job will be created

---

## Common Issues

### Issue 1: Sync Job Timeout

**Symptoms**:
- Job shows "failed" status
- Error message: "ReadTimeout" or "httpx.ReadTimeout"
- Images were uploaded to S3 but job failed

**Cause**: The sync took longer than the HTTP timeout (now set to 30 minutes)

**Solution**:
- ✅ **Fixed**: Timeout increased to 30 minutes (1800 seconds)
- For very large syncs (1000+ notes with images), consider:
  - Running incremental syncs more frequently
  - Breaking up large syncs into smaller batches

**Check logs**:
```bash
docker-compose logs sync_service | grep -i "timeout"
```

### Issue 2: Authentication Failed

**Symptoms**:
- Error: "Keep authentication failed"
- Error: "Invalid master token"

**Cause**: Master token expired or incorrect

**Solution**:
1. Generate a new master token:
   ```bash
   python3 get_master_token_python.py
   ```
2. Update credentials at http://localhost:8000/config/credentials/
3. Retry the sync job

**Check logs**:
```bash
docker-compose logs keep_extractor | grep -i "auth"
```

### Issue 3: Service Not Responding

**Symptoms**:
- "Failed to connect to Sync Service"
- Health check returns "down"

**Solution**:
1. Check if service is running:
   ```bash
   docker-compose ps
   ```

2. Restart the service:
   ```bash
   docker-compose restart sync_service
   ```

3. Check service logs:
   ```bash
   docker-compose logs sync_service --tail 50
   ```

4. Rebuild if needed:
   ```bash
   docker-compose up -d --build sync_service
   ```

### Issue 4: Database Connection Error

**Symptoms**:
- "Database health check failed"
- "Connection refused" errors

**Solution**:
1. Check if PostgreSQL is running:
   ```bash
   docker-compose ps postgres
   ```

2. Restart database:
   ```bash
   docker-compose restart postgres
   ```

3. Check database logs:
   ```bash
   docker-compose logs postgres
   ```

### Issue 5: Image Upload Failures

**Symptoms**:
- Error: "Failed to process image"
- Error: "KeyError: 'location'"
- Some images missing in Notion

**Cause**: 
- Network issues downloading from Google
- Invalid image URLs
- S3 upload failures

**Solution**:
1. Check keep_extractor logs:
   ```bash
   docker-compose logs keep_extractor | grep -i "image"
   ```

2. Verify S3 credentials in `.env`:
   ```bash
   grep AWS_ .env
   ```

3. Check S3 bucket:
   - Verify bucket exists
   - Check access permissions
   - View uploaded images in AWS Console

4. Retry the sync job (failed images will be retried)

### Issue 6: Jobs Stuck in "Running" Status

**Symptoms**:
- Job shows "running" for a long time
- No recent log entries
- Service appears healthy

**Cause**: 
- Job may have crashed without updating status
- Long-running sync with many images

**Solution**:
1. Check if sync is actually running:
   ```bash
   docker-compose logs sync_service --tail 50
   docker-compose logs keep_extractor --tail 50
   ```

2. If no recent activity, abort the job:
   - Go to http://localhost:8000/sync-jobs/{job_id}/
   - Click "Abort Sync Job"

3. Restart services if needed:
   ```bash
   docker-compose restart sync_service
   ```

---

## Monitoring Best Practices

### 1. Regular Health Checks
Set up a cron job or monitoring tool to check service health:

```bash
#!/bin/bash
# health_check.sh

services=("sync_service:8005" "keep_extractor:8003" "notion_writer:8004")

for service in "${services[@]}"; do
  name="${service%%:*}"
  port="${service##*:}"
  
  if curl -sf http://localhost:$port/health > /dev/null; then
    echo "✓ $name is healthy"
  else
    echo "✗ $name is down"
    # Send alert here
  fi
done
```

### 2. Log Rotation
Docker logs can grow large. Configure log rotation in `docker-compose.yml`:

```yaml
services:
  sync_service:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### 3. Monitor Disk Space
Check disk usage for Docker volumes:

```bash
docker system df
docker volume ls
```

Clean up old data:
```bash
docker system prune -a --volumes
```

### 4. Database Monitoring
Check database size and performance:

```bash
# Connect to database
docker-compose exec postgres psql -U postgres -d keep_notion_sync

# Check table sizes
SELECT 
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

# Check sync job counts
SELECT status, COUNT(*) FROM sync_jobs GROUP BY status;
```

### 5. Performance Metrics
Track key metrics:
- Average sync duration
- Success rate
- Notes processed per hour
- Failed notes percentage

View in dashboard: http://localhost:8000

---

## Getting Help

If you encounter issues not covered here:

1. **Check logs first**: Most issues are visible in logs
2. **Search error messages**: Copy exact error text and search
3. **Verify configuration**: Check `.env` file and credentials
4. **Test components individually**: Use health endpoints
5. **Restart services**: Often resolves transient issues

**Useful commands**:
```bash
# Full system restart
docker-compose down && docker-compose up -d

# View all logs
docker-compose logs -f

# Check service status
docker-compose ps

# Rebuild everything
docker-compose up -d --build
```
