import httpx
from typing import Optional, Dict, Any, List

# Placeholder models - ideally import/share from the main app models 
# or define client-specific representations
class TicketResponse:
    pass
class DeviceResponse:
    pass

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
    def list_tickets(self, params: Optional[Dict] = None) -> Dict[str, Any]:
        """List SecureChange tickets. Returns raw API response dict."""
        return self._request("GET", "/api/v1/tickets", params=params)
        
    def create_ticket(self, ticket_data: Dict) -> Dict[str, Any]:
        """Create a SecureChange ticket. Returns raw API response dict."""
        return self._request("POST", "/api/v1/tickets", json=ticket_data)
        
    def get_ticket(self, ticket_id: int) -> Dict[str, Any]:
        """Get details for a specific SecureChange ticket. Returns raw API response dict."""
        return self._request("GET", f"/api/v1/tickets/{ticket_id}")

    def update_ticket(self, ticket_id: int, ticket_data: Dict) -> Dict[str, Any]:
        """Update an existing SecureChange ticket. Returns raw API response dict."""
        return self._request("PUT", f"/api/v1/tickets/{ticket_id}", json=ticket_data)

    # --- SecureTrack Devices --- 
    def list_devices(self, params: Optional[Dict] = None) -> Dict[str, Any]:
        """List SecureTrack devices. Returns raw API response dict."""
        return self._request("GET", "/api/v1/devices", params=params)
        
    def get_device(self, device_id: int) -> Dict[str, Any]:
        """Get details for a specific SecureTrack device. Returns raw API response dict."""
        return self._request("GET", f"/api/v1/devices/{device_id}")

    # --- SecureTrack Topology --- 
    def get_topology_map(self) -> Dict[str, Any]:
        """Get the SecureTrack topology map. Returns raw API response dict."""
        return self._request("GET", "/api/v1/topology/map")
        
    def run_topology_query(self, query_data: Dict) -> Dict[str, Any]:
        """Run a SecureTrack topology query. Returns raw API response dict."""
        return self._request("POST", "/api/v1/topology/query", json=query_data)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close() 