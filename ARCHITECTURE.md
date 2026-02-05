# Architecture Overview

## Project Structure

```
.
├── services/                    # Microservices
│   ├── api_gateway/            # FastAPI REST API gateway
│   │   ├── __init__.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── admin_interface/        # Django admin web interface
│   │   ├── __init__.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── sync_service/           # Sync orchestrator
│   │   ├── __init__.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── keep_extractor/         # Google Keep integration
│   │   ├── __init__.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   └── notion_writer/          # Notion integration
│       ├── __init__.py
│       ├── Dockerfile
│       └── requirements.txt
├── shared/                      # Shared package
│   ├── __init__.py
│   ├── models.py               # Common data models
│   ├── config.py               # Configuration utilities
│   ├── requirements.txt
│   └── README.md
├── database/                    # Database schema and migrations
│   ├── schema.sql              # PostgreSQL schema
│   ├── alembic.ini             # Alembic configuration
│   ├── migrations/             # Alembic migrations
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │       └── 001_initial_schema.py
│   ├── requirements.txt
│   └── README.md
├── docker-compose.yml           # Local development setup
├── .env.example                 # Environment variables template
├── .gitignore
├── setup.sh                     # Setup script
├── README.md
└── ARCHITECTURE.md              # This file
```

## Service Communication

```
External Client → API Gateway → Sync Service → Keep Extractor → Google Keep
                                              ↓
                                              → Notion Writer → Notion API
                                              ↓
                                              → PostgreSQL

Administrator → Admin Interface → Sync Service → ...
```

## Technology Stack

- **API Gateway**: FastAPI, Python 3.11
- **Admin Interface**: Django 4.2, Python 3.11
- **Sync Service**: FastAPI, Python 3.11
- **Keep Extractor**: FastAPI, gkeepapi, boto3, Python 3.11
- **Notion Writer**: FastAPI, notion-client, boto3, Python 3.11
- **Database**: PostgreSQL 15
- **Containerization**: Docker, Docker Compose
- **Cloud**: AWS (ECS/EKS, RDS, S3, Secrets Manager, CloudWatch)

## Service Ports

- API Gateway: 8001
- Admin Interface: 8000
- Sync Service: 8002
- Keep Extractor: 8003
- Notion Writer: 8004
- PostgreSQL: 5432

## Data Flow

1. User triggers sync via API Gateway or Admin Interface
2. Request forwarded to Sync Service
3. Sync Service queries database for sync state
4. Sync Service calls Keep Extractor to fetch notes
5. Keep Extractor downloads images to S3
6. Sync Service calls Notion Writer for each note
7. Notion Writer uploads images from S3 to Notion
8. Sync Service updates sync state in database
9. Response returned to user

## Development Workflow

1. Clone repository
2. Copy `.env.example` to `.env` and configure
3. Run `./setup.sh` to set up local environment
4. Run `docker-compose up` to start all services
5. Access admin interface at http://localhost:8000
6. Access API at http://localhost:8001

## Deployment

The application is designed to be deployed on AWS:

- **Container Orchestration**: ECS or EKS
- **Database**: RDS PostgreSQL
- **Storage**: S3 for images
- **Secrets**: AWS Secrets Manager
- **Monitoring**: CloudWatch

See individual service directories for deployment details.
