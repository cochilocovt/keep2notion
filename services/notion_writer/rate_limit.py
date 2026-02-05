"""Rate limit handling for Notion API."""

import logging
import time
from typing import Callable, Any
from functools import wraps

from notion_client.errors import APIResponseError

logger = logging.getLogger(__name__)


def handle_rate_limit(max_retries: int = 3):
    """
    Decorator to handle Notion API rate limits with automatic retry.
    
    Notion API returns 429 status code when rate limited, along with
    a Retry-After header indicating how long to wait.
    
    Args:
        max_retries: Maximum number of retry attempts
    
    Returns:
        Decorated function that handles rate limits
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            retries = 0
            
            while retries <= max_retries:
                try:
                    return await func(*args, **kwargs)
                
                except APIResponseError as e:
                    # Check if this is a rate limit error (429)
                    if e.code == "rate_limited" or (hasattr(e, 'status') and e.status == 429):
                        retries += 1
                        
                        if retries > max_retries:
                            logger.error(f"Max retries ({max_retries}) exceeded for rate limit")
                            raise
                        
                        # Extract retry-after from error response
                        retry_after = _extract_retry_after(e)
                        
                        logger.warning(
                            f"Rate limit hit. Waiting {retry_after} seconds before retry "
                            f"(attempt {retries}/{max_retries})"
                        )
                        
                        time.sleep(retry_after)
                        continue
                    
                    # Not a rate limit error, re-raise
                    raise
            
            # Should not reach here, but just in case
            raise Exception(f"Failed after {max_retries} retries")
        
        return wrapper
    return decorator


def _extract_retry_after(error: APIResponseError) -> float:
    """
    Extract retry-after duration from Notion API error.
    
    Args:
        error: APIResponseError from Notion client
    
    Returns:
        Number of seconds to wait before retrying
    """
    # Default wait time if not specified
    default_wait = 1.0
    
    try:
        # Try to get retry-after from error response
        if hasattr(error, 'response') and error.response:
            response = error.response
            
            # Check headers for Retry-After
            if hasattr(response, 'headers'):
                retry_after = response.headers.get('Retry-After')
                if retry_after:
                    try:
                        return float(retry_after)
                    except ValueError:
                        pass
            
            # Check response body for retry_after
            if hasattr(response, 'json'):
                try:
                    body = response.json()
                    if 'retry_after' in body:
                        return float(body['retry_after'])
                except Exception:
                    pass
        
        # Use exponential backoff as fallback
        return default_wait
    
    except Exception as e:
        logger.warning(f"Error extracting retry-after: {e}")
        return default_wait
