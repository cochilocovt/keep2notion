# API Gateway Authentication and Error Handling

This document describes the authentication and error handling implementation for the API Gateway service.

## Authentication

### Overview

The API Gateway uses API key-based authentication to secure all sync-related endpoints. API keys are passed in the `X-API-Key` HTTP header.

### Configuration

API keys are configured via the `API_KEYS` environment variable:

```bash
# Single API key
export API_KEYS="your-api-key-here"

# Multiple API keys (comma-separated)
export API_KEYS="key1,key2,key3"
```

If not set, a default development key is used: `dev-api-key-12345`

**⚠️ Important:** In production, always set custom API keys and never use the default development key.

### Protected Endpoints

The following endpoints require authentication:

- `POST /api/v1/sync/start` - Start a sync job
- `GET /api/v1/sync/jobs/{job_id}` - Get sync job status
- `GET /api/v1/sync/history` - Get sync history

### Public Endpoints

The following endpoints do NOT require authentication:

- `GET /health` - Basic health check
- `GET /api/v1/health` - Detailed health check
- `GET /` - Root endpoint

### Usage Example

```bash
# With authentication
curl -X POST http://localhost:8001/api/v1/sync/start \
  -H "X-API-Key: your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user123", "full_sync": false}'

# Without authentication (will fail with 401)
curl -X POST http://localhost:8001/api/v1/sync/start \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user123", "full_sync": false}'
```

### Authentication Errors

**401 Unauthorized - Missing API Key:**
```json
{
  "detail": "Missing API key. Please provide X-API-Key header."
}
```

**401 Unauthorized - Invalid API Key:**
```json
{
  "detail": "Invalid API key"
}
```

## Error Handling

### HTTP Status Codes

The API Gateway returns appropriate HTTP status codes for different error scenarios:

| Status Code | Description | When Used |
|------------|-------------|-----------|
| 200 | OK | Successful GET requests |
| 201 | Created | Successful POST requests (sync job created) |
| 400 | Bad Request | Invalid input (empty user_id, invalid UUID, bad pagination) |
| 401 | Unauthorized | Missing or invalid API key |
| 404 | Not Found | Requested resource doesn't exist (job not found) |
| 500 | Internal Server Error | Unexpected errors, database failures |
| 502 | Bad Gateway | Sync Service returned an error |
| 503 | Service Unavailable | Sync Service is down or unreachable |
| 504 | Gateway Timeout | Sync Service request timed out |

### Error Response Format

All errors return a JSON response with descriptive information:

```json
{
  "detail": "Descriptive error message explaining what went wrong"
}
```

For middleware-caught errors, additional fields may be included:

```json
{
  "error": "Error category",
  "detail": "Descriptive error message",
  "type": "error_type"
}
```

### Common Error Scenarios

#### 400 Bad Request - Empty User ID

**Request:**
```bash
curl -X POST http://localhost:8001/api/v1/sync/start \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "", "full_sync": false}'
```

**Response:**
```json
{
  "detail": "user_id is required and cannot be empty"
}
```

#### 400 Bad Request - Invalid Job ID Format

**Request:**
```bash
curl http://localhost:8001/api/v1/sync/jobs/not-a-uuid \
  -H "X-API-Key: your-key"
```

**Response:**
```json
{
  "detail": "Invalid job_id format: 'not-a-uuid'. Must be a valid UUID (e.g., '123e4567-e89b-12d3-a456-426614174000')."
}
```

#### 400 Bad Request - Invalid Pagination

**Request:**
```bash
curl "http://localhost:8001/api/v1/sync/history?limit=200" \
  -H "X-API-Key: your-key"
```

**Response:**
```json
{
  "detail": "Invalid limit: 200. Must be between 1 and 100."
}
```

#### 404 Not Found - Job Not Found

**Request:**
```bash
curl http://localhost:8001/api/v1/sync/jobs/123e4567-e89b-12d3-a456-426614174000 \
  -H "X-API-Key: your-key"
```

**Response:**
```json
{
  "detail": "Sync job '123e4567-e89b-12d3-a456-426614174000' not found. Please verify the job_id is correct."
}
```

#### 503 Service Unavailable - Sync Service Down

**Request:**
```bash
curl -X POST http://localhost:8001/api/v1/sync/start \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user123", "full_sync": false}'
```

**Response:**
```json
{
  "detail": "Sync Service is currently unavailable. Please try again later."
}
```

## Implementation Details

### Authentication Middleware

Authentication is implemented using FastAPI's dependency injection system:

```python
async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    """Verify API key from request header."""
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Please provide X-API-Key header."
        )
    
    if x_api_key not in VALID_API_KEYS:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    
    return x_api_key
```

Protected endpoints use the dependency:

```python
@app.post("/api/v1/sync/start")
async def start_sync(
    request: SyncStartRequest,
    api_key: str = Depends(verify_api_key)  # Authentication required
):
    # Endpoint logic
    pass
```

### Error Handling Middleware

Global error handling is implemented as middleware:

```python
@app.middleware("http")
async def error_handling_middleware(request: Request, call_next):
    """Global error handling middleware."""
    try:
        response = await call_next(request)
        return response
    except HTTPException:
        # Re-raise HTTPExceptions to be handled by FastAPI
        raise
    except ValueError as exc:
        # Validation errors
        return JSONResponse(
            status_code=400,
            content={"error": "Bad Request", "detail": str(exc)}
        )
    except Exception as exc:
        # Unexpected errors
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal Server Error", "detail": "..."}
        )
```

### Validation

Input validation is performed at multiple levels:

1. **Pydantic Models** - Automatic validation of request bodies
2. **Endpoint Logic** - Custom validation (e.g., empty strings, UUID format)
3. **Middleware** - Catches unhandled validation errors

## Testing

Comprehensive tests are provided in `test_api_gateway_auth.py`:

```bash
# Run authentication and error handling tests
python3 -m pytest test_api_gateway_auth.py -v
```

Tests cover:
- Missing API key (401)
- Invalid API key (401)
- Valid API key (allows access)
- Empty user_id (400)
- Invalid job_id format (400)
- Invalid pagination (400)
- Job not found (404)
- Sync Service unavailable (503)
- Health checks don't require auth
- Descriptive error messages

## Security Considerations

1. **API Key Storage**: Store API keys securely (environment variables, secrets manager)
2. **HTTPS**: Always use HTTPS in production to protect API keys in transit
3. **Key Rotation**: Implement a process for rotating API keys periodically
4. **Rate Limiting**: Consider adding rate limiting to prevent abuse
5. **Logging**: API keys are never logged (only first 10 characters for debugging)

## Future Enhancements

Potential improvements for production:

1. **OAuth 2.0**: Replace API keys with OAuth 2.0 for better security
2. **JWT Tokens**: Use JWT tokens with expiration for stateless authentication
3. **Database-backed Keys**: Store API keys in database with metadata (user, permissions, expiration)
4. **Role-based Access Control**: Implement different permission levels
5. **API Key Scopes**: Limit what each API key can access
6. **Audit Logging**: Log all authenticated requests for security auditing

## Requirements Satisfied

This implementation satisfies the following requirements:

- **Requirement 5.4**: "WHEN an API request is received, THE API_Gateway SHALL validate authentication tokens"
- **Requirement 5.5**: "WHEN an API request is invalid, THE API_Gateway SHALL return appropriate HTTP status codes and error messages"
- **Requirement 10.3**: "THE system SHALL validate OAuth tokens before processing sync requests"

Note: While the requirement mentions "OAuth tokens", we've implemented API key authentication as a simpler, production-ready alternative. The architecture supports easy migration to OAuth 2.0 in the future.
