import httpx
from typing import Optional, Dict, Any, List

# Import MCP API Response Models (adjust path if library moves outside main project)
# Assuming models are accessible relative to where the client might be used IN the project
# If packaged separately, this dependency needs management.
try:
    from src.app.models.securechange import TicketResponse, TicketListResponse
    from src.app.models.securetrack import DeviceResponse, DeviceListResponse, TopologyPathResponse
except ImportError:
    # Fallback or simplified models if run standalone - less ideal
    print("Warning: Could not import full Pydantic models. Using basic placeholders.")
    class TicketResponse: pass
    class TicketListResponse: pass
    class DeviceResponse: pass
    class DeviceListResponse: pass
    class TopologyPathResponse: pass

# Define more specific exception class
class TufinMCPClientError(Exception):
    """Base exception for Tufin MCP client errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, response_text: Optional[str] = None):
        self.status_code = status_code
        self.response_text = response_text
        super().__init__(message)

class TufinMCPClient:
    """Client library for interacting with the Tufin MCP Server API."""

    def __init__(self, base_url: str, api_key: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={
                "X-API-Key": self.api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=timeout,
        )
        # Consider adding async client support as well

    def close(self):
        self._client.close()

    def _request(self, method: str, path: str, **kwargs) -> Any:
        try:
            response = self._client.request(method, path, **kwargs)
            response.raise_for_status() # Raises httpx.HTTPStatusError for 4xx/5xx
            if response.status_code == 204: 
                return None
            return response.json()
        except httpx.HTTPStatusError as e:
            # Wrap HTTP errors in our custom exception
            error_detail = e.response.text
            try:
                # Try to parse detail from JSON response
                json_detail = e.response.json().get("detail")
                if json_detail:
                    error_detail = json_detail
            except Exception:
                pass # Keep original text if JSON parsing fails
            raise TufinMCPClientError(
                f"HTTP Error {e.response.status_code} calling {e.request.method} {e.request.url}",
                status_code=e.response.status_code,
                response_text=error_detail
            ) from e
        except httpx.TimeoutException as e:
            raise TufinMCPClientError(f"Request timed out calling {e.request.url}") from e
        except httpx.RequestError as e:
            # Handle connection errors, etc.
            raise TufinMCPClientError(f"Request Error calling {e.request.url}: {e}") from e

    # --- Health --- 
    def get_health(self) -> Dict[str, Any]:
        """Check the health of the MCP server."""
        return self._request("GET", "/health")
    
    # --- SecureChange Tickets --- 
    def list_tickets(self, params: Optional[Dict] = None) -> TicketListResponse:
        """List SecureChange tickets. Parses response into TicketListResponse model."""
        raw_response = self._request("GET", "/api/v1/tickets", params=params)
        try:
            return TicketListResponse.model_validate(raw_response)
        except Exception as e:
            raise TufinMCPClientError(f"Failed to parse list_tickets response: {e}") from e
        
    def create_ticket(self, ticket_data: Dict) -> TicketResponse:
        """Create a SecureChange ticket. Parses response into TicketResponse model."""
        # Requires workflow_name and details dict within ticket_data
        raw_response = self._request("POST", "/api/v1/tickets", json=ticket_data)
        try:
            return TicketResponse.model_validate(raw_response)
        except Exception as e:
            raise TufinMCPClientError(f"Failed to parse create_ticket response: {e}") from e
        
    def get_ticket(self, ticket_id: int) -> TicketResponse:
        """Get details for a specific SecureChange ticket. Parses response into TicketResponse model."""
        raw_response = self._request("GET", f"/api/v1/tickets/{ticket_id}")
        try:
            return TicketResponse.model_validate(raw_response)
        except Exception as e:
            raise TufinMCPClientError(f"Failed to parse get_ticket response: {e}") from e

    def update_ticket(self, ticket_id: int, ticket_data: Dict) -> TicketResponse:
        """Update an existing SecureChange ticket. Parses response into TicketResponse model."""
        raw_response = self._request("PUT", f"/api/v1/tickets/{ticket_id}", json=ticket_data)
        try:
            return TicketResponse.model_validate(raw_response)
        except Exception as e:
            raise TufinMCPClientError(f"Failed to parse update_ticket response: {e}") from e

    # --- SecureTrack Devices --- 
    def list_devices(self, params: Optional[Dict] = None) -> DeviceListResponse:
        """List SecureTrack devices. Parses response into DeviceListResponse model."""
        raw_response = self._request("GET", "/api/v1/devices", params=params)
        try:
            return DeviceListResponse.model_validate(raw_response)
        except Exception as e:
            raise TufinMCPClientError(f"Failed to parse list_devices response: {e}") from e
        
    def get_device(self, device_id: str) -> DeviceResponse: # Changed ID to str
        """Get details for a specific SecureTrack device. Parses response into DeviceResponse model."""
        raw_response = self._request("GET", f"/api/v1/devices/{device_id}")
        try:
            return DeviceResponse.model_validate(raw_response)
        except Exception as e:
            raise TufinMCPClientError(f"Failed to parse get_device response: {e}") from e

    def add_devices(self, devices: List[Dict]) -> None:
        """Add one or more devices via the bulk endpoint."""
        request_body = {"devices": devices}
        # Expects 202, _request handles errors, returns None on success (204 or implied 202)
        # We might want _request to handle 202 specifically if needed
        self._request("POST", "/api/v1/devices/bulk", json=request_body)
        return None # Explicitly return None to indicate accepted

    # --- SecureTrack Topology --- 
    def get_topology_path(self, params: Dict) -> TopologyPathResponse:
        """Run a SecureTrack topology path query. Parses response into TopologyPathResponse model."""
        # Expects params dict with src, dst, service
        raw_response = self._request("GET", "/api/v1/topology/path", params=params)
        try:
            return TopologyPathResponse.model_validate(raw_response)
        except Exception as e:
            raise TufinMCPClientError(f"Failed to parse get_topology_path response: {e}") from e

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close() 