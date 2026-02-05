"""Notion Writer - handles page creation and updates in Notion."""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from notion_client import Client
from notion_client.errors import APIResponseError

# Handle both relative and absolute imports
try:
    from .rate_limit import handle_rate_limit
except ImportError:
    from rate_limit import handle_rate_limit

logger = logging.getLogger(__name__)


class NotionWriter:
    """Handles writing notes to Notion databases."""
    
    def __init__(self, api_token: str):
        """
        Initialize Notion Writer.
        
        Args:
            api_token: Notion API integration token
        """
        self.client = Client(auth=api_token)
        self.api_token = api_token
    
    @handle_rate_limit(max_retries=3)
    async def create_page(
        self,
        database_id: str,
        note: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Create a new Notion page from a Google Keep note.
        
        Args:
            database_id: Notion database ID where the page will be created
            note: Dictionary containing note data with keys:
                - title: str
                - content: str
                - created_at: str (ISO format)
                - labels: List[str]
                - images: List[Dict] with keys: s3_url, filename
        
        Returns:
            Dictionary with page_id and url
        
        Raises:
            APIResponseError: If Notion API request fails
        """
        try:
            # Get database schema to find the title property name
            database = self.client.databases.retrieve(database_id=database_id)
            title_property_name = None
            
            # Find the title property
            for prop_name, prop_config in database.get("properties", {}).items():
                if prop_config.get("type") == "title":
                    title_property_name = prop_name
                    break
            
            if not title_property_name:
                # Fallback to "Name" if no title property found (shouldn't happen)
                title_property_name = "Name"
                logger.warning(f"No title property found in database, using default: {title_property_name}")
            
            # Prepare page properties using the correct title property name
            properties = self._build_page_properties(note, title_property_name)
            
            # Prepare page content blocks
            children = self._build_content_blocks(note)
            
            # Create page in Notion
            logger.info(f"Creating Notion page for note: {note.get('title', 'Untitled')}")
            response = self.client.pages.create(
                parent={"database_id": database_id},
                properties=properties,
                children=children
            )
            
            page_id = response["id"]
            page_url = response["url"]
            
            logger.info(f"Successfully created Notion page: {page_id}")
            
            return {
                "page_id": page_id,
                "url": page_url
            }
        
        except APIResponseError as e:
            logger.error(f"Notion API error creating page: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating page: {e}", exc_info=True)
            raise
    
    @handle_rate_limit(max_retries=3)
    async def update_page(
        self,
        page_id: str,
        note: Dict[str, Any]
    ) -> Dict[str, bool]:
        """
        Update an existing Notion page.
        
        Args:
            page_id: Notion page ID to update
            note: Dictionary containing note data (same format as create_page)
        
        Returns:
            Dictionary with page_id and updated status
        
        Raises:
            APIResponseError: If Notion API request fails
        """
        try:
            # Update page properties
            properties = self._build_page_properties(note)
            
            logger.info(f"Updating Notion page: {page_id}")
            self.client.pages.update(
                page_id=page_id,
                properties=properties
            )
            
            # Append new content blocks
            children = self._build_content_blocks(note)
            if children:
                self.client.blocks.children.append(
                    block_id=page_id,
                    children=children
                )
            
            logger.info(f"Successfully updated Notion page: {page_id}")
            
            return {
                "page_id": page_id,
                "updated": True
            }
        
        except APIResponseError as e:
            logger.error(f"Notion API error updating page: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error updating page: {e}", exc_info=True)
            raise
    
    def _build_page_properties(self, note: Dict[str, Any], title_property_name: str = "Name") -> Dict[str, Any]:
        """
        Build Notion page properties from note data.
        
        Args:
            note: Note dictionary
            title_property_name: Name of the title property in the database
        
        Returns:
            Dictionary of Notion page properties
        """
        properties = {}
        
        # Title property - use the database's actual title property name
        title = note.get("title", "Untitled")
        properties[title_property_name] = {
            "title": [
                {
                    "type": "text",
                    "text": {"content": title}
                }
            ]
        }
        
        # Don't add other properties - they may not exist in the database
        # Users can add them manually in Notion if needed
        
        return properties
    
    def _build_content_blocks(self, note: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Build Notion content blocks from note data.
        
        Args:
            note: Note dictionary
        
        Returns:
            List of Notion block objects
        """
        blocks = []
        
        # Add text content as paragraph blocks
        content = note.get("content", "")
        if content:
            # Split content into paragraphs
            paragraphs = content.split("\n")
            for paragraph in paragraphs:
                if paragraph.strip():  # Skip empty lines
                    blocks.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {"content": paragraph}
                                }
                            ]
                        }
                    })
        
        # Add images as image blocks
        images = note.get("images", [])
        for image in images:
            s3_url = image.get("s3_url")
            if s3_url:
                blocks.append({
                    "object": "block",
                    "type": "image",
                    "image": {
                        "type": "external",
                        "external": {"url": s3_url}
                    }
                })
        
        return blocks
