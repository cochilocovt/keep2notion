# Admin Interface Service

Django-based web administration interface for the Google Keep to Notion Sync application.

## Overview

The Admin Interface provides a web-based dashboard for:
- Monitoring sync job status and history
- Manually triggering sync operations
- Managing user credentials (Google Keep OAuth, Notion API tokens)
- Viewing detailed sync logs and error messages
- Configuring system settings

## Technology Stack

- **Framework**: Django 4.2.9
- **Database**: PostgreSQL (via psycopg2-binary)
- **API Client**: httpx for communicating with Sync Service
- **Server**: Gunicorn for production deployment
- **Frontend**: Bootstrap 5 for responsive UI

## Project Structure

```
admin_interface/
├── admin_project/          # Django project settings
│   ├── settings.py        # Main configuration
│   ├── urls.py            # URL routing
│   └── wsgi.py            # WSGI application
├── sync_admin/            # Main Django app
│   ├── models.py          # Database models
│   ├── views.py           # View controllers
│   ├── admin.py           # Django admin configuration
│   └── migrations/        # Database migrations
├── templates/             # HTML templates
│   └── base.html          # Base template
├── static/                # Static files (CSS, JS, images)
│   └── css/
│       └── style.css      # Custom styles
├── manage.py              # Django management script
└── requirements.txt       # Python dependencies
```

## Configuration

The service uses environment variables for configuration:

- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: Django secret key for security
- `DEBUG`: Enable/disable debug mode
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts
- `SYNC_SERVICE_URL`: URL of the Sync Service
- `LOG_LEVEL`: Logging level (INFO, DEBUG, WARNING, ERROR)

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables (create `.env` file or export):
```bash
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/keep_notion_sync
export SECRET_KEY=your-secret-key-here
export SYNC_SERVICE_URL=http://localhost:8002
```

3. Run database migrations:
```bash
python manage.py migrate
```

4. Create a superuser for admin access:
```bash
python manage.py createsuperuser
```

5. Collect static files:
```bash
python manage.py collectstatic --noinput
```

6. Run the development server:
```bash
python manage.py runserver 0.0.0.0:8000
```

## Production Deployment

For production, use Gunicorn:

```bash
gunicorn admin_project.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

## Docker

Build and run with Docker:

```bash
docker build -t admin-interface .
docker run -p 8000:8000 --env-file .env admin-interface
```

## Features

### Dashboard
- Overview of recent sync jobs
- Success/failure statistics
- System health status

### Sync Job Management
- List all sync jobs with pagination
- Filter by status, user, date range
- View detailed job information and logs
- Retry failed jobs

### Credential Management
- Store and manage Google Keep OAuth tokens
- Store and manage Notion API tokens
- Encrypted storage for sensitive data

### Manual Sync Trigger
- Form to initiate sync jobs
- Select user and sync type (full/incremental)
- Real-time job status updates

## API Endpoints

The admin interface communicates with the Sync Service via HTTP:

- `POST /internal/sync/execute` - Trigger sync job
- `GET /internal/sync/status/{job_id}` - Get job status

## Security

- Credentials are encrypted using AES-256 before storage
- HTTPS enforced in production
- CSRF protection enabled
- Secure session management
- No sensitive data in logs

## Development

Run tests:
```bash
python manage.py test
```

Create new migrations:
```bash
python manage.py makemigrations
```

Access Django admin:
```
http://localhost:8000/admin/
```

## Troubleshooting

### Database Connection Issues
- Verify DATABASE_URL is correct
- Ensure PostgreSQL is running
- Check network connectivity

### Static Files Not Loading
- Run `python manage.py collectstatic`
- Verify STATIC_ROOT and STATIC_URL settings
- Check file permissions

### Import Errors
- Ensure shared module is in Python path
- Verify all dependencies are installed
- Check virtual environment activation
