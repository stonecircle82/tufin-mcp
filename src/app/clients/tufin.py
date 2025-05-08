import httpx
import logging
import json
from fastapi import HTTPException, status
from typing import Optional, Dict, Any, List

from ..core.config import Settings, settings
from ..models.securetrack import (
    TufinDeviceListResponse, TufinDevice, 
    TufinTopologyPathResponse,
    DeviceBulkAddRequest,
    DeviceBulkImportRequest,
    TufinImportDeviceItem
)
from ..models.securechange import (
    TicketResponse, TicketCreate, TicketListResponse, TicketUpdate, 
    TufinTicketListResponse, TufinTicket
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
        # Determine GraphQL URL (use ST base if not explicitly set, appending common path)
        self.graphql_url = (settings.TUFIN_GRAPHQL_URL or f"{self.securetrack_base_url}/sg/api/v1/graphql").rstrip('/')
        
        auth = httpx.BasicAuth(settings.TUFIN_USERNAME, settings.TUFIN_PASSWORD)
        # Use TUFIN_SSL_VERIFY setting from config
        self._client = httpx.AsyncClient(
            auth=auth, 
            verify=settings.TUFIN_SSL_VERIFY, 
            timeout=settings.TUFIN_API_TIMEOUT 
        )
        # Note: We use the same client for REST and GraphQL assuming same base auth and SSL settings.
        # If GraphQL needs different base URL/auth/headers, create a separate httpx client.

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

    async def execute_graphql_query(self, query: str, variables: Optional[Dict] = None) -> Dict[str, Any]:
        """Executes a GraphQL query against the configured Tufin GraphQL endpoint."""
        logger.info(f"Executing GraphQL query against {self.graphql_url}")
        request_body = {"query": query}
        if variables:
            request_body["variables"] = variables
        
        logger.debug(f"GraphQL request body: {request_body}")
        
        # Use the core client, assuming GraphQL endpoint is reachable with same auth/settings
        # Need error handling specific to GraphQL responses (e.g., {"errors": [...]})
        try:
            # Use POST for GraphQL
            response = await self._client.request(
                "POST", 
                self.graphql_url, 
                json=request_body,
                headers={"Content-Type": "application/json"} # Ensure header is set
            )
            response.raise_for_status() # Check for HTTP errors
            
            json_response = response.json()
            
            # Check for GraphQL-level errors
            if "errors" in json_response and json_response["errors"]:
                error_detail = json.dumps(json_response["errors"])
                logger.error(f"GraphQL query returned errors: {error_detail}")
                # Map to a suitable HTTP error status
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, # Or 502 if it indicates upstream issue
                    detail=f"GraphQL query failed: {error_detail[:200]}..."
                )
            
            if "data" not in json_response:
                 logger.error(f"GraphQL response missing 'data' field: {json_response}")
                 raise HTTPException(
                     status_code=status.HTTP_502_BAD_GATEWAY,
                     detail="Invalid GraphQL response structure from Tufin (missing data)"
                 )
                 
            return json_response["data"] # Return only the data part

        except httpx.HTTPStatusError as e: # Handle HTTP errors from _client.request
            logger.error(f"HTTP error executing GraphQL query {e.response.status_code}: {e.response.text}")
            detail = f"Tufin API error: {e.response.status_code} - {e.response.text[:100]}..."
            raise HTTPException(status_code=e.response.status_code, detail=detail)
        except httpx.RequestError as e: 
             logger.error(f"Connection error executing GraphQL query: {e}")
             raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Could not connect to Tufin GraphQL API: {e.url}")
        except Exception as e:
            logger.error(f"Unexpected error executing GraphQL query: {e}", exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal error during GraphQL query.")

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

    async def get_topology_path_image(self, src: str, dst: str, service: str) -> bytes:
        """Gets the topology path image from SecureTrack."""
        # Endpoint assumed based on user input and documentation link
        url = f"{self.securetrack_base_url}/securetrack/api/topology/path_image"
        params = {"src": src, "dst": dst, "service": service}
        logger.info(f"Requesting SecureTrack topology path image via {url} with params {params}")
        
        # Make GET request, expect binary response
        # Use the base _request method but handle potential non-JSON response outside
        try:
            response = await self._client.request("GET", url, params=params)
            response.raise_for_status()
            # Return raw image bytes
            return response.content
        except httpx.TimeoutException as e:
            logger.error(f"Tufin API request timed out: {e}")
            raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="Tufin API request timed out")
        except httpx.RequestError as e:
            logger.error(f"Error connecting to Tufin API: {e}")
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Could not connect to Tufin API: {e.url}")
        except httpx.HTTPStatusError as e:
            logger.error(f"Tufin API returned error {e.response.status_code} for path image: {e.response.text}")
            detail = f"Tufin API error: {e.response.status_code} - {e.response.text[:100]}..."
            raise HTTPException(status_code=e.response.status_code, detail=detail)

    async def add_securetrack_devices(self, bulk_add_request: DeviceBulkAddRequest) -> None:
        """Adds one or more devices to SecureTrack using the bulk endpoint."""
        # Endpoint and method verified from user input
        url = f"{self.securetrack_base_url}/securetrack/api/devices/bulk/"
        logger.info(f"Adding {len(bulk_add_request.devices)} device(s) via {url}")
        
        # Prepare request body - Tufin expects {"devices": [...]} according to schema example
        # Our DeviceBulkAddRequest model already matches this structure when dumped.
        request_body = bulk_add_request.model_dump()
        
        logger.debug(f"Tufin add devices request body: {request_body}") # Mask credentials before logging!
        
        # Use _request but expect 202, not necessarily JSON response
        try:
            response = await self._client.request("POST", url, json=request_body)
            # Check for 202 Accepted specifically
            if response.status_code != status.HTTP_202_ACCEPTED:
                # Raise exception if not 202, trying to parse potential error detail
                response.raise_for_status() 
            
            # Success (202 Accepted) - Tufin will process async
            logger.info(f"Device add request accepted by Tufin (Status {response.status_code}). Processing is asynchronous.")
            return None # Indicate acceptance, no specific data returned

        except httpx.HTTPStatusError as e:
            # Handle 4xx/5xx errors specifically if needed, reusing existing logic
            logger.error(f"Tufin API returned error {e.response.status_code} adding devices: {e.response.text}")
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
        except httpx.RequestError as e: # Handle connection errors etc.
             logger.error(f"Error connecting to Tufin API for add devices: {e}")
             raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Could not connect to Tufin API: {e.url}")
        except Exception as e:
            logger.error(f"Unexpected error during add devices: {e}", exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal error during device add request.")

    async def import_securetrack_managed_devices(self, import_request: DeviceBulkImportRequest) -> None:
        """Imports managed devices into existing parent devices using POST /devices/bulk/import."""
        # Endpoint verified from user input
        url = f"{self.securetrack_base_url}/securetrack/api/devices/bulk/import"
        logger.info(f"Importing managed devices for {len(import_request.devices)} parent(s) via {url}")
        
        # Transform MCP request structure to Tufin API structure
        tufin_device_list = []
        for item in import_request.devices:
            # Construct the Tufin device_data based on MCP request
            # Note: This assumes a certain mapping. Needs careful validation based on how
            # Tufin actually expects different device types (ASA vs Panorama vs Cloud) 
            # within the single device_data field for this endpoint.
            # The API examples suggest the structure within device_data varies slightly.
            # We pass the structured list from MCP into the 'import_devices' key for Tufin.
            tufin_dev_data = {
                "import_all": item.device_data.import_all,
                "import_devices": [dev.model_dump(exclude_none=True) for dev in item.device_data.import_devices],
                "collect_rule_usage_traffic_logs": item.device_data.collect_rule_usage,
                "collect_object_usage_traffic_logs": item.device_data.collect_object_usage
            }
            
            tufin_item = TufinImportDeviceItem(
                device_id=item.device_id,
                device_data=tufin_dev_data
                # We are omitting outer fields like enable_topology, vendor, model for import
                # Add them here if Tufin requires/uses them for the import operation
            )
            tufin_device_list.append(tufin_item.model_dump(exclude_none=True))
            
        # Final Tufin request body
        request_body = {"devices": tufin_device_list}
        
        logger.debug(f"Tufin import devices request body: {request_body}")
        
        # Use _request but expect 202
        try:
            response = await self._client.request("POST", url, json=request_body)
            if response.status_code != status.HTTP_202_ACCEPTED:
                response.raise_for_status()
            
            logger.info(f"Managed device import request accepted by Tufin (Status {response.status_code}).")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"Tufin API returned error {e.response.status_code} importing devices: {e.response.text}")
            detail = f"Tufin API error: {e.response.status_code} - {e.response.text[:100]}..."
            # Try to get more detail
            try: detail = e.response.json().get('message', detail) 
            except: pass
            raise HTTPException(status_code=e.response.status_code, detail=detail)
        except httpx.RequestError as e: 
             logger.error(f"Error connecting to Tufin API for import devices: {e}")
             raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Could not connect to Tufin API: {e.url}")
        except Exception as e:
            logger.error(f"Unexpected error during import devices: {e}", exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal error during device import request.")

    async def query_rules_graphql(self, tql_filter: Optional[str] = None) -> Dict[str, Any]:
        """Queries SecureTrack rules using GraphQL and TQL filter."""
        # Define a standard set of fields to retrieve
        # Expand this based on common needs
        rule_fields = """
            id
            name
            action
            comment
            disabled
            implicit
            metadata { certificationStatus technicalOwner applicationOwner ruleDescription businessOwner } 
            source { text zones { text } }
            destination { text zones { text } }
            service { text }
            application { text }
            user { text }
            installOn { text }
            vpn { text }
            # Add more fields as needed, e.g., loggingDetails { text }, schedule { text }
        """
        
        query = f"""
            query($tqlFilter: String) {{
                rules(filter: $tqlFilter) {{
                    count
                    values {{
                        {rule_fields}
                    }}
                }}
            }}
        """
        
        variables = {"tqlFilter": tql_filter or ""}
        
        # Execute the query
        # Returns the content of the "data" field from the GraphQL response
        graphql_data = await self.execute_graphql_query(query=query, variables=variables)
        
        # Expecting {"rules": {"count": N, "values": [...]}} inside the data
        if "rules" not in graphql_data or not isinstance(graphql_data["rules"], dict):
             logger.error(f"GraphQL rules query response missing 'rules' field or wrong type: {graphql_data}")
             raise HTTPException(
                 status_code=status.HTTP_502_BAD_GATEWAY,
                 detail="Invalid GraphQL response structure from Tufin (missing rules data)"
             )
             
        return graphql_data # Return the full data dict containing {"rules": ...}

    # --- SecureChange Methods --- 
    
    async def create_securechange_ticket(self, workflow_name: str, ticket_details: Dict[str, Any]) -> TufinTicket:
        """Creates a new ticket in SecureChange using a specific workflow."""
        # Path verified by user
        url = f"{self.securechange_base_url}/securechangeworkflow/api/securechange/tickets"
        logger.info(f"Creating SecureChange ticket for workflow '{workflow_name}' via {url}")
        
        # Construct the request body expected by Tufin's addTicket
        # This structure needs verification based on Tufin API examples
        # Assuming common fields are passed within the main ticket structure
        # along with workflow-specific fields from ticket_details.
        request_body = {
            "ticket": {
                "workflow": {"name": workflow_name},
                # Add common fields if they are expected here (e.g., subject, priority)
                # **ticket_details should contain the workflow-specific fields
                **ticket_details 
            }
        }
        
        logger.debug(f"Tufin create ticket request body: {request_body}") # Be careful logging potentially sensitive details
        response = await self._request("POST", url, json=request_body)
        
        # Parse the response using the detailed TufinTicket model
        try:
            created_ticket = TufinTicket.model_validate(response.json())
            logger.info(f"Successfully created SecureChange ticket ID: {created_ticket.id}")
            return created_ticket
        except Exception as e:
            logger.error(f"Failed to parse Tufin create ticket response: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to parse response from Tufin API (Create Ticket)"
            )

    async def list_securechange_tickets(self, filters: Optional[Dict[str, Any]] = None) -> TufinTicketListResponse:
        """Lists tickets from SecureChange. Returns the parsed Tufin response structure."""
        # Endpoint verified from user input
        url = f"{self.securechange_base_url}/securechangeworkflow/api/securechange/tickets"
        params = {}
        if filters:
            # Implement proper filter formatting based on Tufin docs
            # Example: might need to join filters into a single query param string
            # Or Tufin might accept direct query params like ?status=Pending&requester=user1
            logger.info(f"Applying ticket filters (needs verification): {filters}")
            params.update(filters) # Simple add for now, likely needs adjustment
            
        logger.info(f"Requesting SecureChange tickets from {url} with params: {params}")
        response = await self._request("GET", url, params=params if params else None)
        
        # Parse the response using the detailed Tufin-specific Pydantic model
        try:
            # This model now includes the 'ticket' list and next/previous links
            parsed_response = TufinTicketListResponse.model_validate(response.json())
            return parsed_response
        except Exception as e:
            logger.error(f"Failed to parse Tufin ticket list response: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to parse response from Tufin API (Ticket List)"
            )

    async def get_securechange_ticket(self, ticket_id: int) -> TufinTicket:
        """Gets details for a specific ticket from SecureChange. Returns the parsed Tufin structure."""
        # Endpoint verified from user input
        url = f"{self.securechange_base_url}/securechangeworkflow/api/securechange/tickets/{ticket_id}"
        logger.info(f"Requesting SecureChange ticket details from {url}")
        response = await self._request("GET", url)
        
        # Parse the response using the detailed TufinTicket model
        try:
            parsed_response = TufinTicket.model_validate(response.json())
            return parsed_response
        except Exception as e:
            logger.error(f"Failed to parse Tufin ticket details response: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to parse response from Tufin API (Ticket Details)"
            )

    async def update_securechange_ticket(self, ticket_id: int, ticket_data: TicketUpdate) -> TufinTicket: # Updated return type
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
            updated_ticket = TufinTicket.model_validate(response.json())
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