"""Keep Extractor Service - FastAPI application."""

import logging
import sys
from contextlib import asynccontextmanager
from typing import Dict, List, Optional
from datetime import datetime

from fastapi import FastAPI, Request, status, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import shared config
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))
from shared.config import get_aws_config

from auth import KeepAuthenticator
from extractor import NoteExtractor
from s3_client import S3Client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)


# Store authenticators per user (in production, use proper session management)
authenticators: Dict[str, KeepAuthenticator] = {}

# Initialize S3 client
s3_client: Optional[S3Client] = None


def get_s3_client() -> S3Client:
    """Get or create S3 client."""
    global s3_client
    if s3_client is None:
        aws_config = get_aws_config()
        s3_client = S3Client(
            bucket_name=aws_config["s3_bucket"],
            region=aws_config["region"],
            access_key_id=aws_config.get("access_key_id"),
            secret_access_key=aws_config.get("secret_access_key")
        )
    return s3_client


# Request/Response models
class AuthRequest(BaseModel):
    """Authentication request model."""
    username: str
    password: str = None
    master_token: str = None


class AuthResponse(BaseModel):
    """Authentication response model."""
    status: str
    error: str = None
    master_token: str = None


class NotesResponse(BaseModel):
    """Notes extraction response model."""
    notes: List[dict]
    count: int


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    logger.info("Keep Extractor Service starting up...")
    yield
    logger.info("Keep Extractor Service shutting down...")


# Create FastAPI application
app = FastAPI(
    title="Keep Extractor Service",
    description="Service for extracting notes and images from Google Keep",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Error handling middleware
@app.middleware("http")
async def error_handling_middleware(request: Request, call_next):
    """Global error handling middleware."""
    try:
        response = await call_next(request)
        return response
    except Exception as exc:
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal server error",
                "detail": str(exc)
            }
        )


# Health check endpoint
@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "keep_extractor",
        "version": "0.1.0"
    }


@app.get("/", status_code=status.HTTP_200_OK)
async def root():
    """Root endpoint."""
    return {
        "service": "Keep Extractor Service",
        "version": "0.1.0",
        "status": "running"
    }


@app.post("/internal/keep/auth", response_model=AuthResponse, status_code=status.HTTP_200_OK)
async def authenticate(auth_request: AuthRequest):
    """
    Authenticate with Google Keep.
    
    Supports two authentication methods:
    1. Username + Password (or app-specific password)
    2. Username + Master Token (for resuming sessions)
    
    Returns master token on successful authentication for future use.
    """
    username = auth_request.username
    
    if not username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username is required"
        )
    
    # Create authenticator for this user
    authenticator = KeepAuthenticator()
    
    try:
        # Try token-based authentication first if provided
        if auth_request.master_token:
            success = await authenticator.authenticate_with_token(
                username, 
                auth_request.master_token
            )
            if success:
                authenticators[username] = authenticator
                return AuthResponse(
                    status="authenticated",
                    master_token=authenticator.get_master_token()
                )
            else:
                return AuthResponse(
                    status="failed",
                    error="Invalid master token"
                )
        
        # Try password-based authentication
        elif auth_request.password:
            success = await authenticator.authenticate(
                username,
                auth_request.password
            )
            if success:
                authenticators[username] = authenticator
                return AuthResponse(
                    status="authenticated",
                    master_token=authenticator.get_master_token()
                )
            else:
                return AuthResponse(
                    status="failed",
                    error="Invalid username or password"
                )
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either password or master_token must be provided"
            )
    
    except Exception as e:
        logger.error(f"Authentication error for user {username}: {e}", exc_info=True)
        return AuthResponse(
            status="failed",
            error=str(e)
        )


if __name__ == "__main__":
    import uvicorn
    import os
    
    port = int(os.getenv("KEEP_EXTRACTOR_PORT", 8003))
    uvicorn.run(app, host="0.0.0.0", port=port)



@app.get("/internal/keep/notes", response_model=NotesResponse, status_code=status.HTTP_200_OK)
async def get_notes(
    username: str,
    modified_since: Optional[str] = None,
    upload_images: bool = False,
    limit: Optional[int] = None
):
    """
    Extract notes from Google Keep.
    
    Args:
        username: Google account username (must be authenticated first)
        modified_since: Optional ISO format datetime string to filter notes
        upload_images: Whether to download and upload images to S3
        limit: Optional limit on number of notes to return (for testing)
        
    Returns:
        List of extracted notes with metadata
    """
    # Check if user is authenticated
    if username not in authenticators:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"User {username} is not authenticated. Please authenticate first."
        )
    
    authenticator = authenticators[username]
    
    if not authenticator.is_authenticated():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"User {username} session is invalid. Please re-authenticate."
        )
    
    # Parse modified_since if provided
    modified_since_dt = None
    if modified_since:
        try:
            modified_since_dt = datetime.fromisoformat(modified_since.replace('Z', '+00:00'))
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid modified_since format. Use ISO format: {e}"
            )
    
    # Extract notes
    try:
        keep_client = authenticator.get_client()
        
        # Initialize S3 client if image upload is requested
        s3 = get_s3_client() if upload_images else None
        
        extractor = NoteExtractor(keep_client, s3_client=s3)
        notes = await extractor.extract_notes(
            modified_since=modified_since_dt,
            upload_images=upload_images,
            limit=limit  # Pass limit to extractor
        )
        
        # Convert datetime objects to ISO strings for JSON serialization
        for note in notes:
            note['created_at'] = note['created_at'].isoformat()
            note['modified_at'] = note['modified_at'].isoformat()
        
        logger.info(f"Returning {len(notes)} notes for user {username}")
        
        return NotesResponse(
            notes=notes,
            count=len(notes)
        )
    
    except Exception as e:
        logger.error(f"Error extracting notes for user {username}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract notes: {str(e)}"
        )
