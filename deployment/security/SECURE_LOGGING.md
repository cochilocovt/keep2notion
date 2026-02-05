# Secure Logging Configuration

This document describes how to implement secure logging practices to prevent sensitive data from being logged while maintaining useful debugging information.

## Overview

The Keep-Notion-Sync application handles sensitive data including:
- User credentials (OAuth tokens, API keys)
- Note content
- Personal information
- Database passwords
- Encryption keys

This data must NEVER appear in logs.

## Logging Architecture

```
Application Logs → CloudWatch Logs → (Optional) S3 Archive
                                   → (Optional) Log Analysis Tools
```

## Sensitive Data Categories

### 1. Credentials
- OAuth tokens
- API keys
- Database passwords
- Encryption keys
- Session tokens

### 2. Personal Data
- Note content
- User email addresses
- IP addresses (in some jurisdictions)

### 3. System Secrets
- Internal API keys
- Service-to-service authentication tokens

## Implementation

### Python Logging Configuration

Create `shared/secure_logging.py`:

```python
import logging
import re
import os
from typing import Any, Dict

class SensitiveDataFilter(logging.Filter):
    """Filter to redact sensitive data from log messages"""
    
    # Patterns to detect and redact
    PATTERNS = [
        # OAuth tokens
        (r'Bearer\s+[A-Za-z0-9\-._~+/]+=*', 'Bearer [REDACTED]'),
        (r'"token":\s*"[^"]*"', '"token": "[REDACTED]"'),
        (r'"access_token":\s*"[^"]*"', '"access_token": "[REDACTED]"'),
        (r'"refresh_token":\s*"[^"]*"', '"refresh_token": "[REDACTED]"'),
        
        # API keys
        (r'"api_key":\s*"[^"]*"', '"api_key": "[REDACTED]"'),
        (r'"api_token":\s*"[^"]*"', '"api_token": "[REDACTED]"'),
        (r'api[_-]?key[=:]\s*[A-Za-z0-9\-._~+/]+', 'api_key=[REDACTED]'),
        
        # Passwords
        (r'"password":\s*"[^"]*"', '"password": "[REDACTED]"'),
        (r'password[=:]\s*[^\s&]+', 'password=[REDACTED]'),
        
        # Database connection strings
        (r'postgresql://[^:]+:[^@]+@', 'postgresql://[REDACTED]:[REDACTED]@'),
        (r'mysql://[^:]+:[^@]+@', 'mysql://[REDACTED]:[REDACTED]@'),
        
        # Email addresses (optional - depends on requirements)
        (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_REDACTED]'),
        
        # Credit card numbers (just in case)
        (r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', '[CARD_REDACTED]'),
        
        # AWS keys
        (r'AKIA[0-9A-Z]{16}', '[AWS_KEY_REDACTED]'),
        (r'aws_secret_access_key[=:]\s*[A-Za-z0-9/+=]+', 'aws_secret_access_key=[REDACTED]'),
    ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter and redact sensitive data from log record"""
        # Redact message
        if isinstance(record.msg, str):
            record.msg = self._redact(record.msg)
        
        # Redact args
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: self._redact_value(v) for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(self._redact_value(arg) for arg in record.args)
        
        return True
    
    def _redact(self, text: str) -> str:
        """Apply all redaction patterns to text"""
        for pattern, replacement in self.PATTERNS:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        return text
    
    def _redact_value(self, value: Any) -> Any:
        """Redact sensitive values"""
        if isinstance(value, str):
            return self._redact(value)
        elif isinstance(value, dict):
            return {k: self._redact_value(v) for k, v in value.items()}
        elif isinstance(value, (list, tuple)):
            return type(value)(self._redact_value(item) for item in value)
        return value


def setup_secure_logging(
    service_name: str,
    log_level: str = None,
    json_format: bool = True
) -> logging.Logger:
    """
    Setup secure logging with sensitive data filtering
    
    Args:
        service_name: Name of the service (e.g., 'api-gateway')
        log_level: Logging level (default: from LOG_LEVEL env var or INFO)
        json_format: Whether to use JSON format (recommended for CloudWatch)
    
    Returns:
        Configured logger instance
    """
    log_level = log_level or os.getenv('LOG_LEVEL', 'INFO')
    
    # Create logger
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    logger.handlers = []
    
    # Create handler
    handler = logging.StreamHandler()
    
    # Add sensitive data filter
    handler.addFilter(SensitiveDataFilter())
    
    # Set format
    if json_format:
        # JSON format for CloudWatch
        import json
        from datetime import datetime
        
        class JsonFormatter(logging.Formatter):
            def format(self, record):
                log_data = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'level': record.levelname,
                    'service': service_name,
                    'message': record.getMessage(),
                    'logger': record.name,
                    'module': record.module,
                    'function': record.funcName,
                    'line': record.lineno,
                }
                
                # Add exception info if present
                if record.exc_info:
                    log_data['exception'] = self.formatException(record.exc_info)
                
                # Add extra fields
                if hasattr(record, 'request_id'):
                    log_data['request_id'] = record.request_id
                
                return json.dumps(log_data)
        
        handler.setFormatter(JsonFormatter())
    else:
        # Standard format
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    
    return logger


# Utility functions for safe logging
def safe_dict(data: Dict[str, Any], safe_keys: list = None) -> Dict[str, Any]:
    """
    Create a safe version of a dictionary for logging
    
    Args:
        data: Dictionary to make safe
        safe_keys: List of keys that are safe to log (all others redacted)
    
    Returns:
        Dictionary with sensitive values redacted
    """
    if safe_keys is None:
        safe_keys = ['id', 'status', 'created_at', 'updated_at', 'count', 'total']
    
    return {
        k: v if k in safe_keys else '[REDACTED]'
        for k, v in data.items()
    }


def safe_url(url: str) -> str:
    """
    Redact sensitive parts of URL (query parameters, credentials)
    
    Args:
        url: URL to make safe
    
    Returns:
        URL with sensitive parts redacted
    """
    from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
    
    parsed = urlparse(url)
    
    # Redact credentials
    netloc = parsed.netloc
    if '@' in netloc:
        netloc = '[REDACTED]:[REDACTED]@' + netloc.split('@')[1]
    
    # Redact query parameters (keep keys, redact values)
    query_params = parse_qs(parsed.query)
    safe_params = {k: '[REDACTED]' for k in query_params.keys()}
    safe_query = urlencode(safe_params)
    
    return urlunparse((
        parsed.scheme,
        netloc,
        parsed.path,
        parsed.params,
        safe_query,
        ''  # Remove fragment
    ))
```

### Usage in Services

#### API Gateway Example

```python
from shared.secure_logging import setup_secure_logging, safe_dict, safe_url

# Setup logger
logger = setup_secure_logging('api-gateway')

# Safe logging examples
@app.post("/api/v1/sync/start")
async def start_sync(request: SyncRequest):
    # DON'T: Log the entire request (may contain tokens)
    # logger.info(f"Sync request: {request}")
    
    # DO: Log only safe fields
    logger.info(
        "Sync request received",
        extra={
            'user_id': request.user_id,
            'full_sync': request.full_sync,
            'request_id': request.request_id
        }
    )
    
    # When logging dictionaries
    user_data = get_user_data(request.user_id)
    logger.debug(f"User data: {safe_dict(user_data, safe_keys=['id', 'created_at'])}")
    
    # When logging URLs
    api_url = "https://api.example.com/data?token=secret123"
    logger.info(f"Calling API: {safe_url(api_url)}")
```

#### Sync Service Example

```python
from shared.secure_logging import setup_secure_logging

logger = setup_secure_logging('sync-service')

async def sync_notes(user_id: str, credentials: dict):
    logger.info(f"Starting sync for user: {user_id}")
    
    # DON'T: Log credentials
    # logger.debug(f"Using credentials: {credentials}")
    
    # DO: Log that credentials were loaded
    logger.debug(f"Credentials loaded for user: {user_id}")
    
    try:
        notes = await keep_extractor.get_notes(credentials['google_token'])
        
        # DON'T: Log note content
        # logger.info(f"Retrieved notes: {notes}")
        
        # DO: Log metadata only
        logger.info(f"Retrieved {len(notes)} notes for user: {user_id}")
        
    except Exception as e:
        # DON'T: Log exception with sensitive data
        # logger.error(f"Sync failed: {e}", exc_info=True)
        
        # DO: Log error type and sanitized message
        logger.error(
            f"Sync failed for user: {user_id}",
            extra={
                'error_type': type(e).__name__,
                'error_message': str(e)[:100]  # Truncate to avoid leaking data
            }
        )
```

### FastAPI Middleware for Request Logging

```python
from fastapi import Request
import time
import uuid

@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())
    
    # Add request ID to logger context
    logger = logging.LoggerAdapter(
        logging.getLogger('api-gateway'),
        {'request_id': request_id}
    )
    
    # Log request (safe parts only)
    logger.info(
        "Request received",
        extra={
            'method': request.method,
            'path': request.url.path,
            'client_ip': request.client.host,
            'user_agent': request.headers.get('user-agent', 'unknown')[:100]
        }
    )
    
    # Process request
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    # Log response
    logger.info(
        "Request completed",
        extra={
            'status_code': response.status_code,
            'duration_ms': round(duration * 1000, 2)
        }
    )
    
    return response
```

## CloudWatch Configuration

### Log Retention

Set appropriate retention periods in `deployment/terraform/cloudwatch.tf`:

```hcl
resource "aws_cloudwatch_log_group" "api_gateway" {
  name              = "/aws/eks/keep-notion-sync/api-gateway"
  retention_in_days = 30  # Adjust based on compliance requirements
  
  tags = local.common_tags
}
```

### Log Encryption

Ensure logs are encrypted at rest:

```hcl
resource "aws_kms_key" "cloudwatch_logs" {
  description             = "KMS key for CloudWatch Logs encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true
  
  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "api_gateway" {
  name              = "/aws/eks/keep-notion-sync/api-gateway"
  retention_in_days = 30
  kms_key_id        = aws_kms_key.cloudwatch_logs.arn
  
  tags = local.common_tags
}
```

### Metric Filters for Security Events

```hcl
# Alert on authentication failures
resource "aws_cloudwatch_log_metric_filter" "auth_failures" {
  name           = "authentication-failures"
  log_group_name = aws_cloudwatch_log_group.api_gateway.name
  pattern        = "[time, request_id, level = ERROR, message = *authentication*failed*]"
  
  metric_transformation {
    name      = "AuthenticationFailures"
    namespace = "KeepNotionSync/Security"
    value     = "1"
  }
}

# Alert on potential data leaks
resource "aws_cloudwatch_log_metric_filter" "potential_leaks" {
  name           = "potential-data-leaks"
  log_group_name = aws_cloudwatch_log_group.api_gateway.name
  pattern        = "[time, request_id, level, message = *password* || message = *token* || message = *secret*]"
  
  metric_transformation {
    name      = "PotentialDataLeaks"
    namespace = "KeepNotionSync/Security"
    value     = "1"
  }
}
```

## Testing Secure Logging

Create `shared/test_secure_logging.py`:

```python
import logging
from secure_logging import SensitiveDataFilter, setup_secure_logging

def test_sensitive_data_filter():
    """Test that sensitive data is properly redacted"""
    
    filter = SensitiveDataFilter()
    
    # Test cases
    test_cases = [
        # OAuth tokens
        ('Bearer abc123xyz', 'Bearer [REDACTED]'),
        ('"token": "secret123"', '"token": "[REDACTED]"'),
        
        # Passwords
        ('"password": "mypass123"', '"password": "[REDACTED]"'),
        ('password=secret', 'password=[REDACTED]'),
        
        # Database URLs
        ('postgresql://user:pass@localhost/db', 'postgresql://[REDACTED]:[REDACTED]@localhost/db'),
        
        # API keys
        ('"api_key": "sk_live_123"', '"api_key": "[REDACTED]"'),
        
        # AWS keys
        ('AKIAIOSFODNN7EXAMPLE', '[AWS_KEY_REDACTED]'),
    ]
    
    for input_text, expected in test_cases:
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='',
            lineno=0,
            msg=input_text,
            args=(),
            exc_info=None
        )
        filter.filter(record)
        assert record.msg == expected, f"Failed: {input_text} -> {record.msg} (expected: {expected})"
    
    print("All tests passed!")

if __name__ == '__main__':
    test_sensitive_data_filter()
```

## Compliance Considerations

### GDPR
- Don't log personal data without consent
- Implement log retention policies
- Provide ability to delete user logs

### PCI DSS
- Never log full credit card numbers
- Mask PANs if logging is necessary
- Secure log storage and transmission

### HIPAA
- Don't log protected health information (PHI)
- Encrypt logs at rest and in transit
- Implement access controls

## Monitoring and Alerts

### Alert on Sensitive Data in Logs

```python
# CloudWatch alarm for potential data leaks
resource "aws_cloudwatch_metric_alarm" "data_leak_alert" {
  alarm_name          = "keep-notion-sync-potential-data-leak"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "PotentialDataLeaks"
  namespace           = "KeepNotionSync/Security"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "Alert when sensitive data might be in logs"
  alarm_actions       = [aws_sns_topic.security_alerts.arn]
  
  tags = local.common_tags
}
```

## Best Practices

1. **Never log**:
   - Passwords or password hashes
   - OAuth tokens or API keys
   - Session tokens
   - Credit card numbers
   - Social security numbers
   - Full note content

2. **Always log**:
   - Request IDs for tracing
   - User IDs (not usernames/emails)
   - Timestamps
   - Status codes
   - Error types (not full error messages)
   - Performance metrics

3. **Use structured logging**:
   - JSON format for easy parsing
   - Consistent field names
   - Include context (request_id, user_id)

4. **Implement log levels properly**:
   - ERROR: Actual errors requiring attention
   - WARNING: Potential issues
   - INFO: Important business events
   - DEBUG: Detailed debugging (never in production)

5. **Regular audits**:
   - Review logs for sensitive data
   - Update redaction patterns
   - Test logging filters

## Additional Resources

- [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)
- [AWS CloudWatch Logs Best Practices](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/WhatIsCloudWatchLogs.html)
- [GDPR Logging Guidelines](https://gdpr.eu/data-processing-agreement/)
