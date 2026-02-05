# Database Setup

This directory contains the PostgreSQL database schema and migrations for the Google Keep to Notion sync application.

## Schema

The database schema is defined in `schema.sql` and includes the following tables:

- **sync_jobs**: Tracks sync job execution and status
- **sync_state**: Records which notes have been synced to Notion
- **credentials**: Stores encrypted user credentials
- **sync_logs**: Detailed logs for each sync job

## Migrations

Database migrations are managed using Alembic. Migration files are located in `migrations/versions/`.

### Running Migrations

1. Ensure PostgreSQL is running and DATABASE_URL is set in your environment
2. Run migrations:

```bash
cd database
alembic upgrade head
```

### Creating New Migrations

```bash
cd database
alembic revision -m "Description of changes"
```

Edit the generated file in `migrations/versions/` to add your schema changes.

## Initial Setup

The schema is automatically applied when using docker-compose (via the init script). For manual setup:

```bash
psql -U postgres -d keep_notion_sync -f schema.sql
```

## Connection String

Default connection string for local development:
```
postgresql://postgres:postgres@localhost:5432/keep_notion_sync
```

Configure via the `DATABASE_URL` environment variable.
