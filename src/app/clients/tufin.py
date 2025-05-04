import httpx
import logging
from fastapi import HTTPException, status
from typing import Optional, Dict, Any

from ..core.config import Settings, settings
from ..models.securetrack import (
    TufinDeviceListResponse, TufinDevice, 
    TufinTopologyPathResponse
)
from ..models.securechange import (
    TicketResponse, TicketCreate, TicketListResponse, TicketUpdate, 
    TufinTicketListResponse 
)

logger = logging.getLogger(__name__)

# Global variable to hold the singleton client instance
# Note: This is simple; more robust solutions exist for managing state.
_tufin_client_instance: Optional["TufinApiClient"] = None

class TufinApiClient:
    """Asynchronous client for interacting with Tufin SecureTrack and SecureChange APIs."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.securetrack_base_url = settings.TUFIN_SECURETRACK_URL.rstrip('/')
        self.securechange_base_url = settings.TUFIN_SECURECHANGE_URL.rstrip('/')
        
        # Setup basic authentication
        auth = httpx.BasicAuth(settings.TUFIN_USERNAME, settings.TUFIN_PASSWORD)
        
        # Initialize httpx client
        # Use TUFIN_SSL_VERIFY setting from config
        self._client = httpx.AsyncClient(
            auth=auth, 
            verify=settings.TUFIN_SSL_VERIFY, 
            timeout=settings.TUFIN_API_TIMEOUT # Add timeout from settings
            # If using custom cert path: verify=settings.TUFIN_SSL_CERT_PATH or settings.TUFIN_SSL_VERIFY
        )

    async def close(self):
        """Closes the underlying httpx client."""
        await self._client.aclose()

    async def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Internal helper method to make requests and handle common errors."""
        try:
            response = await self._client.request(method, url, **kwargs)
            response.raise_for_status() # Raises HTTPStatusError for 4xx/5xx responses
            return response
        except httpx.TimeoutException as e:
            logger.error(f"Tufin API request timed out: {e}")
            raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="Tufin API request timed out")
        except httpx.RequestError as e:
            logger.error(f"Error connecting to Tufin API: {e}")
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Could not connect to Tufin API: {e.url}")
        except httpx.HTTPStatusError as e:
            logger.error(f"Tufin API returned error {e.response.status_code}: {e.response.text}")
            # Try to return Tufin's error message if possible
            detail = f"Tufin API error: {e.response.status_code}"
            try:
                error_data = e.response.json()
                if isinstance(error_data, dict) and 'message' in error_data:
                    detail += f" - {error_data['message']}"
                else:
                    detail += f" - {e.response.text[:100]}..."
            except Exception:
                detail += f" - {e.response.text[:100]}..."
            raise HTTPException(status_code=e.response.status_code, detail=detail)

    # --- SecureTrack Methods --- 

    async def get_securetrack_domains(self) -> dict:
        """Gets the list of SecureTrack domains."""
        url = f"{self.securetrack_base_url}/securetrack/api/domains"
        logger.info(f"Requesting SecureTrack domains from {url}")
        response = await self._request("GET", url)
        return response.json()
        
    async def list_securetrack_devices(self, filters: Optional[Dict[str, Any]] = None) -> TufinDeviceListResponse:
        """Lists devices managed by SecureTrack using filter parameters."""
        url = f"{self.securetrack_base_url}/securetrack/api/devices"
        params = {}
        if filters:
            # Construct filter query parameters based on Tufin's expected format
            # Assuming simple key=value for now, like ?status=started&vendor=Cisco
            # VERIFY THIS against Tufin REST API docs!
            # Tufin might expect a single `filter` param with specific syntax.
            params.update(filters) 
            logger.info(f"Applying device filters (needs verification): {filters}")
            
        logger.info(f"Requesting SecureTrack devices from {url} with params: {params}")
        # Use GET params, not request body for filters usually
        response = await self._request("GET", url, params=params if params else None)
        
        # Parse the response using the Tufin-specific Pydantic model
        try:
            # Response structure is now {"device": [...], "count": N, "total": M}
            parsed_response = TufinDeviceListResponse.model_validate(response.json())
            return parsed_response
        except Exception as e:
            logger.error(f"Failed to parse Tufin device list response: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to parse response from Tufin API (Device List)"
            )
            
    async def get_securetrack_device(self, device_id: str) -> TufinDevice: # Changed device_id to str
        """Gets details for a specific device from SecureTrack."""
        # Assuming the endpoint path is /securetrack/api/devices/{device_id}
        # Verify this against Tufin documentation!
        url = f"{self.securetrack_base_url}/securetrack/api/devices/{device_id}"
        logger.info(f"Requesting SecureTrack device details from {url}")
        response = await self._request("GET", url)
        
        # Parse the response using the Pydantic model
        try:
            # Assuming the response body directly contains the device object
            # Adjust parsing if it's nested (e.g., response.json()['device'])
            parsed_response = TufinDevice.model_validate(response.json())
            return parsed_response
        except Exception as e:
            logger.error(f"Failed to parse Tufin device details response: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to parse response from Tufin API (Device Details)"
            )
            
    async def get_topology_path(self, src: str, dst: str, service: str) -> TufinTopologyPathResponse:
        """Runs a topology path query in SecureTrack using GET /topology/path."""
        # Endpoint verified from user input
        url = f"{self.securetrack_base_url}/securetrack/api/topology/path"
        params = {"src": src, "dst": dst, "service": service}
        logger.info(f"Running SecureTrack topology path query via {url} with params {params}")
        
        # Make GET request with query parameters
        response = await self._request("GET", url, params=params)
        
        # Parse the response
        try:
            parsed_response = TufinTopologyPathResponse.model_validate(response.json())
            return parsed_response
        except Exception as e:
            logger.error(f"Failed to parse Tufin topology path response: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to parse response from Tufin API (Topology Path)"
            )

    # TODO: Implement topology methods

    # --- SecureChange Methods --- 
    
    async def create_securechange_ticket(self, ticket_data: TicketCreate) -> TicketResponse:
        """Creates a new ticket in SecureChange."""
        # Assuming the endpoint path is /securechangeworkflow/api/securechange/tickets
        # Verify this against Tufin documentation!
        url = f"{self.securechange_base_url}/securechangeworkflow/api/securechange/tickets"
        logger.info(f"Creating SecureChange ticket via {url}")
        
        # Prepare request body from Pydantic model
        request_body = ticket_data.model_dump(exclude_unset=True) # Only send fields that were set
        
        response = await self._request("POST", url, json=request_body)
        
        # Parse the response using the Pydantic model
        try:
            # Assuming the response body directly contains the created ticket object
            created_ticket = TicketResponse.model_validate(response.json())
            logger.info(f"Successfully created SecureChange ticket ID: {created_ticket.id}")
            return created_ticket
        except Exception as e:
            logger.error(f"Failed to parse Tufin create ticket response: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to parse response from Tufin API (Create Ticket)"
            )

    async def list_securechange_tickets(self, limit: int = 100, offset: int = 0, filters: Optional[Dict[str, Any]] = None) -> TufinTicketListResponse:
        """Lists tickets from SecureChange. Returns the parsed Tufin response structure."""
        # Assuming endpoint path is /securechangeworkflow/api/securechange/tickets
        # Verify this against Tufin documentation!
        url = f"{self.securechange_base_url}/securechangeworkflow/api/securechange/tickets"
        params = {"offset": offset, "limit": limit}
        if filters:
            # Implement proper filter formatting based on Tufin docs
            # Example: might need to join filters into a single query param string
            logger.info(f"Applying ticket filters (needs verification): {filters}")
            params.update(filters) # Simple add for now, likely needs adjustment
            
        logger.info(f"Requesting SecureChange tickets from {url} with params: {params}")
        response = await self._request("GET", url, params=params)
        
        # Parse the response using the Tufin-specific Pydantic model
        try:
            parsed_response = TufinTicketListResponse.model_validate(response.json())
            return parsed_response
        except Exception as e:
            logger.error(f"Failed to parse Tufin ticket list response: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to parse response from Tufin API (Ticket List)"
            )

    async def get_securechange_ticket(self, ticket_id: int) -> TicketResponse:
        """Gets details for a specific ticket from SecureChange."""
        # Assuming endpoint path is /securechangeworkflow/api/securechange/tickets/{ticket_id}
        # Verify this against Tufin documentation!
        url = f"{self.securechange_base_url}/securechangeworkflow/api/securechange/tickets/{ticket_id}"
        logger.info(f"Requesting SecureChange ticket details from {url}")
        response = await self._request("GET", url)
        
        # Parse the response
        try:
            parsed_response = TicketResponse.model_validate(response.json())
            return parsed_response
        except Exception as e:
            logger.error(f"Failed to parse Tufin ticket details response: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to parse response from Tufin API (Ticket Details)"
            )

    async def update_securechange_ticket(self, ticket_id: int, ticket_data: TicketUpdate) -> TicketResponse:
        """Updates an existing ticket in SecureChange."""
        # Assuming endpoint path is PUT /securechangeworkflow/api/securechange/tickets/{ticket_id}
        # Verify this against Tufin documentation!
        url = f"{self.securechange_base_url}/securechangeworkflow/api/securechange/tickets/{ticket_id}"
        logger.info(f"Updating SecureChange ticket {ticket_id} via {url}")
        
        # Prepare request body
        request_body = ticket_data.model_dump(exclude_unset=True)
        
        response = await self._request("PUT", url, json=request_body)
        
        # Parse the response
        try:
            updated_ticket = TicketResponse.model_validate(response.json())
            logger.info(f"Successfully updated SecureChange ticket ID: {updated_ticket.id}")
            return updated_ticket
        except Exception as e:
            logger.error(f"Failed to parse Tufin update ticket response: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to parse response from Tufin API (Update Ticket)"
            )

# --- Client Lifecycle Functions --- 

async def create_tufin_client() -> TufinApiClient:
    """Creates the singleton Tufin API client instance."""
    global _tufin_client_instance
    if _tufin_client_instance is None:
        logger.info("Creating singleton TufinApiClient instance.")
        _tufin_client_instance = TufinApiClient(settings)
    return _tufin_client_instance

async def close_tufin_client():
    """Closes the singleton Tufin API client instance if it exists."""
    global _tufin_client_instance
    if _tufin_client_instance:
        logger.info("Closing singleton TufinApiClient instance.")
        await _tufin_client_instance.close()
        _tufin_client_instance = None

# --- Dependency Function (Updated) --- 

async def get_tufin_client() -> TufinApiClient:
    """FastAPI dependency function to get the shared Tufin client instance."""
    if _tufin_client_instance is None:
        # This might happen if called before startup event finishes or after shutdown
        logger.error("Tufin client accessed before initialization or after shutdown.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail="Tufin API client is not available."
        )
    return _tufin_client_instance 