from fastapi import APIRouter, Depends, status, Query, Request, HTTPException, Response
from typing import List, Any, Optional

# Import dependencies
from ....core.config import UserRole
from ....core.dependencies import require_permission
from ....clients.tufin import TufinApiClient, get_tufin_client
from ....models.securetrack import (
    DeviceResponse, DeviceListResponse, 
    TopologyPathResponse, # Removed TopologyMapResponse
    DeviceBulkAddRequest, DeviceBulkAddResponse,
    DeviceBulkImportRequest, DeviceBulkImportResponse,
    RuleQueryRequest, RuleQueryResponse # Add GraphQL Rule models
)
# Import limiter from the new location
from ....core.limiter import limiter
# Import logger
import logging
logger = logging.getLogger(__name__)

router = APIRouter()

# Define roles allowed to access device/topology info
# Adjust these based on specific endpoint needs
READ_ROLES = [UserRole.ADMIN, UserRole.TICKET_MANAGER, UserRole.USER]

@router.get(
    "/devices", 
    response_model=DeviceListResponse, # Placeholder
    tags=["SecureTrack Devices"],
    dependencies=[Depends(require_permission("list_devices"))]
)
@limiter.limit("100/minute")
async def list_devices(
    request: Request,
    # Updated filter parameters based on Tufin API info (verify names!)
    status: Optional[str] = Query(None, description="Filter by device status (e.g., 'started', 'stopped')"),
    name: Optional[str] = Query(None, description="Filter by device name (contains - check Tufin docs for syntax)"),
    vendor: Optional[str] = Query(None, description="Filter by vendor name"),
    # Remove limit/offset as they are not supported directly by Tufin REST API apparently
    # limit: int = Query(100, ge=1, le=1000),
    # offset: int = Query(0, ge=0),
    tufin_client: TufinApiClient = Depends(get_tufin_client)
) -> DeviceListResponse:
    """
    List SecureTrack devices based on query parameters.
    Requires list_devices permission.
    """
    # Construct filter dict (Verify keys against Tufin API)
    filters = {}
    if status: filters["status"] = status
    if name: filters["name"] = name # How Tufin handles partial matches needs verification
    if vendor: filters["vendor"] = vendor
    
    # Call the client method
    tufin_response = await tufin_client.list_securetrack_devices(
        filters=filters if filters else None
    )
    
    # Map TufinDevice objects to our MCP API DeviceResponse objects
    mcp_devices = [
        DeviceResponse.model_validate(tufin_dev) 
        for tufin_dev in tufin_response.device # Access device list directly now
    ]
    
    # Construct the final MCP API response (using count/total from Tufin)
    return DeviceListResponse(
        devices=mcp_devices, 
        total=tufin_response.total,
        count=tufin_response.count 
        # Removed limit/offset 
    )

@router.get(
    "/devices/{device_id}", 
    response_model=DeviceResponse, 
    tags=["SecureTrack Devices"],
    dependencies=[Depends(require_permission("get_device"))]
)
@limiter.limit("100/minute")
async def get_device(
    request: Request,
    device_id: str, # Changed to string based on Tufin schema
    tufin_client: TufinApiClient = Depends(get_tufin_client)
) -> DeviceResponse:
    """
    Get details for a specific SecureTrack device.
    Requires get_device permission.
    """
    # Call the client method
    tufin_device_data = await tufin_client.get_securetrack_device(device_id)
    
    # Map TufinDevice model to our MCP API DeviceResponse model
    mcp_response = DeviceResponse.model_validate(tufin_device_data)
    return mcp_response

@router.get(
    "/topology/path", # Changed path
    response_model=TopologyPathResponse, # Use MCP API Response model
    tags=["SecureTrack Topology"],
    dependencies=[Depends(require_permission("get_topology_path"))]
)
@limiter.limit("20/minute")
async def get_topology_path_query(
    request: Request,
    src: str = Query(..., description="Source IP address or object name"),
    dst: str = Query(..., description="Destination IP address or object name (with optional port like host:port)"),
    service: str = Query(..., description="Service name (e.g., 'any', 'Facebook') or port/protocol (e.g., 'tcp:80')"),
    tufin_client: TufinApiClient = Depends(get_tufin_client)
) -> TopologyPathResponse:
    """
    Run a topology path query in SecureTrack using GET.
    Returns a summarized result indicating if traffic is allowed and routed.
    Requires get_topology_path permission.
    """
    # Call the client method - gets the detailed Tufin response model
    tufin_result = await tufin_client.get_topology_path(
        src=src, dst=dst, service=service
    )
    
    # Process the detailed result into a summary
    is_routed = not bool(tufin_result.unrouted_elements) # Fully routed if unrouted_elements is empty/None
    
    device_names = []
    if tufin_result.device_info:
        device_names = [dev.name for dev in tufin_result.device_info if dev.name]
        
    # Construct the summarized MCP API response
    mcp_response = TopologyPathResponse(
        traffic_allowed=tufin_result.traffic_allowed,
        is_fully_routed=is_routed,
        # Only include path device names if traffic is allowed and routed
        path_device_names=device_names if (tufin_result.traffic_allowed and is_routed) else None 
    )
    
    return mcp_response

@router.get(
    "/topology/path/image", # New path for image
    # responses is used to describe the binary response in OpenAPI
    responses={
        200: {
            "content": {"image/png": {}}, # Assume PNG, adjust if needed
            "description": "Topology path image generated successfully."
        },
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        404: {"description": "Path or resources not found to generate image"},
        429: {"description": "Rate Limit Exceeded"},
        502: {"description": "Error retrieving data from Tufin"},
        504: {"description": "Tufin API Timeout"}
    },
    tags=["SecureTrack Topology"],
    dependencies=[Depends(require_permission("get_topology_path_image"))]
)
@limiter.limit("10/minute") # Limit image generation requests
async def get_topology_path_image(
    request: Request,
    src: str = Query(..., description="Source IP address or object name"),
    dst: str = Query(..., description="Destination IP address or object name (with optional port like host:port)"),
    service: str = Query(..., description="Service name (e.g., 'any', 'Facebook') or port/protocol (e.g., 'tcp:80')"),
    tufin_client: TufinApiClient = Depends(get_tufin_client)
) -> Response:
    """
    Get the topology path image from SecureTrack.
    Requires get_topology_path_image permission.
    Returns image data (e.g., PNG).
    """
    try:
        image_bytes = await tufin_client.get_topology_path_image(
            src=src, dst=dst, service=service
        )
        # Determine media type (default to png, could be configurable or detected)
        media_type = "image/png" 
        return Response(content=image_bytes, media_type=media_type)
    except HTTPException as e:
        # Re-raise HTTP exceptions from the client
        raise e
    except Exception as e:
        # Catch unexpected errors during image retrieval
        logger.error(f"Unexpected error getting topology image: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error retrieving topology image")

# Removed original POST /topology/query placeholder
# TODO: Implement /topology/query endpoint -> This was the placeholder, now removed. 

@router.post(
    "/devices/bulk",
    response_model=DeviceBulkAddResponse,
    status_code=status.HTTP_202_ACCEPTED, # Match Tufin's success code
    tags=["SecureTrack Devices"],
    dependencies=[Depends(require_permission("add_devices"))]
)
@limiter.limit("10/minute") # Limit bulk operations
async def add_devices_bulk(
    request: Request,
    add_request: DeviceBulkAddRequest,
    tufin_client: TufinApiClient = Depends(get_tufin_client)
) -> DeviceBulkAddResponse:
    """
    Add one or more devices to SecureTrack.
    Requires add_devices permission.
    The request body requires vendor/model specific data in the 'device_data' field.
    Returns 202 Accepted on success, processing happens asynchronously in Tufin.
    """
    await tufin_client.add_securetrack_devices(add_request)
    # If client doesn't raise an exception, it was accepted by Tufin
    return DeviceBulkAddResponse(message="Device add request accepted by Tufin for processing.")

@router.post(
    "/devices/bulk/import",
    response_model=DeviceBulkImportResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["SecureTrack Devices"],
    dependencies=[Depends(require_permission("import_managed_devices"))]
)
@limiter.limit("5/minute") # Stricter limit for bulk import
async def import_managed_devices_bulk(
    request: Request,
    import_request: DeviceBulkImportRequest,
    tufin_client: TufinApiClient = Depends(get_tufin_client)
) -> DeviceBulkImportResponse:
    """
    Import managed devices (Device Groups, ADOMs, Contexts, VNets, etc.) 
    into existing parent management devices in SecureTrack.
    Requires import_managed_devices permission.
    The request body requires details specific to the parent device type.
    Returns 202 Accepted on success, processing happens asynchronously in Tufin.
    """
    await tufin_client.import_securetrack_managed_devices(import_request)
    return DeviceBulkImportResponse(message="Managed device import request accepted by Tufin for processing.") 

@router.post(
    "/graphql/rules", # New endpoint path
    response_model=RuleQueryResponse,
    tags=["SecureTrack GraphQL"],
    dependencies=[Depends(require_permission("query_rules_graphql"))]
)
@limiter.limit("30/minute") # Limit potentially complex queries
async def query_rules_graphql(
    request: Request,
    query_request: RuleQueryRequest,
    tufin_client: TufinApiClient = Depends(get_tufin_client)
) -> RuleQueryResponse:
    """
    Query SecureTrack firewall rules using GraphQL and a TQL filter.
    Returns a standard set of rule properties.
    Requires query_rules_graphql permission.
    """
    logger.info(f"Received GraphQL rule query with filter: {query_request.tql_filter}")
    
    # Call the client method which returns the parsed GraphQL data dictionary
    graphql_data = await tufin_client.query_rules_graphql(
        tql_filter=query_request.tql_filter
    )
    
    # Validate the received data against our Pydantic response model
    try:
        mcp_response = RuleQueryResponse.model_validate(graphql_data)
        return mcp_response
    except Exception as e:
        logger.error(f"Failed to validate GraphQL rule query response: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to parse or validate response from Tufin GraphQL API (Rules Query)"
        ) 