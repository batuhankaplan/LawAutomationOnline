# yargitay_mcp_module/client.py

import httpx
from bs4 import BeautifulSoup # Still needed for pre-processing HTML before markitdown
from typing import Dict, Any, List, Optional
import logging
import html
import re
import tempfile
import os
# from markitdown import MarkItDown  # Temporarily disabled due to onnxruntime DLL issues

from .models import (
    YargitayDetailedSearchRequest,
    YargitayApiSearchResponse,      
    YargitayApiDecisionEntry,
    YargitayApiResponseInnerData,
    YargitayDocumentMarkdown,     
    CompactYargitaySearchResult 
)

logger = logging.getLogger(__name__)
# Basic logging configuration if no handlers are configured
if not logger.hasHandlers():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class YargitayOfficialApiClient:
    """
    API Client for Yargitay's official decision search system.
    Targets the detailed search endpoint (e.g., /aramadetaylist) based on user-provided payload.
    """
    BASE_URL = "https://karararama.yargitay.gov.tr"
    # The form action was "/detayliArama". This often maps to an API endpoint like "/aramadetaylist".
    # This should be confirmed with the actual API.
    DETAILED_SEARCH_ENDPOINT = "/aramadetaylist" 
    DOCUMENT_ENDPOINT = "/getDokuman"

    def __init__(self, request_timeout: float = 60.0):
        self.http_client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Content-Type": "application/json; charset=UTF-8",
                "Accept": "application/json, text/plain, */*",
                "X-Requested-With": "XMLHttpRequest",
                "X-KL-KIS-Ajax-Request": "Ajax_Request", # Seen in a Yargitay client example
                "Referer": f"{self.BASE_URL}/" # Some APIs might check referer
            },
            timeout=request_timeout,
            verify=False # SSL verification disabled as per original user code - use with caution
        )

    async def search_detailed_decisions(
        self, 
        search_params: YargitayDetailedSearchRequest
    ) -> YargitayApiSearchResponse:
        """
        Performs a detailed search for decisions in Yargitay
        using the structured search_params.
        """
        # Create the main payload structure with the 'data' key
        request_payload = {"data": search_params.model_dump(exclude_none=True, by_alias=True)}
        
        logger.info(f"YargitayOfficialApiClient: Performing detailed search with payload: {request_payload}")

        try:
            response = await self.http_client.post(self.DETAILED_SEARCH_ENDPOINT, json=request_payload)
            response.raise_for_status() # Raise an exception for HTTP 4xx or 5xx status codes
            response_json_data = response.json()
            
            # DEBUG: Raw response'u detaylı logla
            logger.info(f"YargitayOfficialApiClient: Raw API response: {response_json_data}")
            logger.info(f"YargitayOfficialApiClient: Response keys: {list(response_json_data.keys()) if isinstance(response_json_data, dict) else 'Not a dict'}")
            logger.info(f"YargitayOfficialApiClient: Response type: {type(response_json_data)}")
            
            # Response format'ını kontrol et
            if isinstance(response_json_data, dict):
                data_field = response_json_data.get("data")
                logger.info(f"YargitayOfficialApiClient: 'data' field type: {type(data_field)}")
                logger.info(f"YargitayOfficialApiClient: 'data' field value: {data_field}")
                
                if data_field is None:
                    logger.warning("YargitayOfficialApiClient: 'data' field is None - API format may have changed")
                    # Boş response döndür
                    return YargitayApiSearchResponse(
                        data=YargitayApiResponseInnerData(
                            data=[],
                            recordsTotal=0,
                            recordsFiltered=0
                        )
                    )
            
            # Validate and parse the response using Pydantic models
            api_response = YargitayApiSearchResponse(**response_json_data)

            # Populate the document_url for each decision entry
            if api_response.data and api_response.data.data:
                for decision_item in api_response.data.data:
                    decision_item.document_url = f"{self.BASE_URL}{self.DOCUMENT_ENDPOINT}?id={decision_item.id}"
            
            return api_response

        except httpx.RequestError as e:
            logger.error(f"YargitayOfficialApiClient: HTTP request error during detailed search: {e}")
            raise # Re-raise to be handled by the calling MCP tool
        except Exception as e: # Catches Pydantic ValidationErrors as well
            logger.error(f"YargitayOfficialApiClient: Error processing or validating detailed search response: {e}")
            # DEBUG: Response'u yeniden logla
            try:
                response_json_data = response.json()
                logger.error(f"YargitayOfficialApiClient: Failed response data: {response_json_data}")
            except:
                logger.error(f"YargitayOfficialApiClient: Could not parse response as JSON")
            raise

    def _convert_html_to_markdown(self, html_from_api_data_field: str) -> Optional[str]:
        """
        Takes raw HTML string (from Yargitay API 'data' field for a document),
        pre-processes it, and converts it to simple text format.
        MarkItDown temporarily disabled due to onnxruntime DLL issues.
        Returns cleaned text or None if conversion fails.
        """
        if not html_from_api_data_field:
            return None

        try:
            # Pre-process HTML: unescape entities and fix common escaped sequences
            processed_html = html.unescape(html_from_api_data_field)
            processed_html = processed_html.replace('\\"', '"')
            processed_html = processed_html.replace('\\r\\n', '\n')
            processed_html = processed_html.replace('\\n', '\n')
            processed_html = processed_html.replace('\\t', '\t')
            
            # Use BeautifulSoup for basic HTML to text conversion
            soup = BeautifulSoup(processed_html, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text and clean it up
            text = soup.get_text()
            
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            logger.info("Successfully converted HTML to text (MarkItDown disabled).")
            return text

        except Exception as e:
            logger.error(f"Error during HTML to text conversion: {e}")
            return processed_html  # Return processed HTML as fallback

    async def get_decision_document_as_markdown(self, id: str) -> YargitayDocumentMarkdown:
        """
        Retrieves a specific Yargitay decision by its ID and returns its content
        as Markdown.
        Based on user-provided /getDokuman response structure.
        """
        document_api_url = f"{self.DOCUMENT_ENDPOINT}?id={id}"
        source_url = f"{self.BASE_URL}{document_api_url}" # The original URL of the document
        logger.info(f"YargitayOfficialApiClient: Fetching document for Markdown conversion (ID: {id})")

        try:
            response = await self.http_client.get(document_api_url)
            response.raise_for_status()
            
            # Expecting JSON response with HTML content in the 'data' field
            response_json = response.json()
            html_content_from_api = response_json.get("data")

            if not isinstance(html_content_from_api, str):
                logger.error(f"YargitayOfficialApiClient: 'data' field in API response is not a string or not found (ID: {id}).")
                raise ValueError("Expected HTML content not found in API response's 'data' field.")

            markdown_content = self._convert_html_to_markdown(html_content_from_api)

            return YargitayDocumentMarkdown(
                id=id,
                markdown_content=markdown_content,
                source_url=source_url
            )
        except httpx.RequestError as e:
            logger.error(f"YargitayOfficialApiClient: HTTP error fetching document for Markdown (ID: {id}): {e}")
            raise
        except ValueError as e: # For JSON parsing errors or missing 'data' field
             logger.error(f"YargitayOfficialApiClient: Error processing document response for Markdown (ID: {id}): {e}")
             raise
        except Exception as e: # For other unexpected errors
            logger.error(f"YargitayOfficialApiClient: General error fetching/processing document for Markdown (ID: {id}): {e}")
            raise

    async def close_client_session(self):
        """Closes the HTTPX client session."""
        await self.http_client.aclose()
        logger.info("YargitayOfficialApiClient: HTTP client session closed.")