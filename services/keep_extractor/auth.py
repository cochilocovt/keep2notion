"""Google Keep authentication module."""

import logging
from typing import Optional

import gkeepapi

from retry import retry_with_exponential_backoff

logger = logging.getLogger(__name__)


class KeepAuthenticator:
    """Handles Google Keep authentication."""
    
    def __init__(self):
        """Initialize the authenticator."""
        self.keep_client: Optional[gkeepapi.Keep] = None
    
    @retry_with_exponential_backoff(
        max_retries=3,
        initial_delay=1.0,
        exponential_base=2.0,
        exceptions=(Exception,)
    )
    async def authenticate(self, username: str, password: str) -> bool:
        """
        Authenticate with Google Keep using username and password.
        
        Note: gkeepapi uses username/password or app-specific password.
        In production, this should be replaced with proper OAuth 2.0 flow.
        
        Args:
            username: Google account username/email
            password: Google account password or app-specific password
            
        Returns:
            bool: True if authentication successful, False otherwise
        """
        try:
            self.keep_client = gkeepapi.Keep()
            self.keep_client.login(username, password)
            logger.info(f"Successfully authenticated with Google Keep for user: {username}")
            return True
        except Exception as e:
            logger.error(f"Authentication failed for user {username}: {e}")
            self.keep_client = None
            return False
    
    @retry_with_exponential_backoff(
        max_retries=3,
        initial_delay=1.0,
        exponential_base=2.0,
        exceptions=(Exception,)
    )
    async def authenticate_with_token(self, username: str, master_token: str) -> bool:
        """
        Authenticate with Google Keep using a master token.
        
        Args:
            username: Google account username/email
            master_token: Google Keep master token
            
        Returns:
            bool: True if authentication successful, False otherwise
        """
        try:
            self.keep_client = gkeepapi.Keep()
            self.keep_client.resume(username, master_token)
            logger.info(f"Successfully resumed session with Google Keep for user: {username}")
            return True
        except Exception as e:
            logger.error(f"Token authentication failed for user {username}: {e}")
            self.keep_client = None
            return False
    
    def get_master_token(self) -> Optional[str]:
        """
        Get the master token for the current session.
        This can be stored and reused for future authentication.
        
        Returns:
            Optional[str]: Master token if authenticated, None otherwise
        """
        if self.keep_client:
            return self.keep_client.getMasterToken()
        return None
    
    def is_authenticated(self) -> bool:
        """Check if currently authenticated."""
        return self.keep_client is not None
    
    def get_client(self) -> Optional[gkeepapi.Keep]:
        """Get the authenticated Keep client."""
        return self.keep_client
