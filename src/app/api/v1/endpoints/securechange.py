from fastapi import APIRouter, Depends, status, Request, Query, Body
from typing import List, Any, Optional # Use Any for now for Tufin responses
from fastapi.exceptions import HTTPException

# Import dependencies
from ....core.config import UserRole, settings # Add settings
from ....core.dependencies import require_permission, AuthenticatedUser # Add AuthenticatedUser
from ....clients.tufin import TufinApiClient, get_tufin_client
from ....models.securechange import TicketCreate, TicketUpdate, TicketResponse, TicketListResponse # Placeholder models
# Import limiter from the new location
from ....core.limiter import limiter
# Import logger
import logging
logger = logging.getLogger(__name__)

router = APIRouter()

# --- Helper Dependency for Workflow Check --- 
async def check_workflow_permission( 
    workflow_name: str, # Get from request body later
    current_user: AuthenticatedUser = Depends(require_permission("create_ticket")) 
) -> str: # Return workflow_name if allowed
    allowed_roles = settings.ALLOWED_WORKFLOWS.get(workflow_name)
    if allowed_roles is None:
        logger.warning(f"Attempt to create ticket for unconfigured workflow: {workflow_name}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Workflow '{workflow_name}' is not configured or allowed."
        )
    if current_user.role not in allowed_roles:
        logger.warning(
            f"Role '{current_user.role.value}' not permitted for workflow '{workflow_name}'. "
            f"Requires one of: {[r.value for r in allowed_roles]}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions for workflow '{workflow_name}'."
        )
    logger.info(f"Workflow permission check passed for '{workflow_name}' (Role: {current_user.role.value})")
    return workflow_name

# Apply rate limiting & permission check (via check_workflow_permission)
@router.post(
    "/tickets", 
    response_model=TicketResponse, # Use MCP Response model
    status_code=status.HTTP_201_CREATED,
    tags=["SecureChange Tickets"],
    # Removed direct permission check, handled by check_workflow_permission
    # dependencies=[Depends(require_permission("create_ticket"))] 
)
@limiter.limit("30/minute")
async def create_ticket(
    request: Request,
    ticket_request: TicketCreate, # Use the new request model
    tufin_client: TufinApiClient = Depends(get_tufin_client),
    # Inject the workflow check dependency - it also runs require_permission("create_ticket")
    # We don't need the result directly here, just need it to pass
    _allowed_workflow: str = Depends(lambda workflow_name=Body(...): check_workflow_permission(workflow_name=ticket_request.workflow_name)) 
    # ^ This lambda is a bit complex to get workflow_name from body into dependency check.
    # Alternative: Check permission inside the endpoint function.
) -> TicketResponse:
    """
    Create a new SecureChange ticket for a specific, configured workflow.
    Requires create_ticket permission and role permission for the specific workflow.
    """
    
    # --- Alternative Permission Check (if dependency injection is too complex) ---
    # current_user = await require_permission("create_ticket")(request) # Manually call if needed
    # allowed_roles_for_workflow = settings.ALLOWED_WORKFLOWS.get(ticket_request.workflow_name)
    # if allowed_roles_for_workflow is None or current_user.role not in allowed_roles_for_workflow:
    #    raise HTTPException(status_code=403, detail=f"Not allowed for workflow {ticket_request.workflow_name}")
    # --- End Alternative --- 
    
    # Prepare data for the client method (extract common fields + details dict)
    # This assumes Tufin expects common fields at the same level as workflow-specific ones
    # Adjust based on verified Tufin request structure for addTicket
    tufin_ticket_data = {
        "subject": ticket_request.subject,
        "description": ticket_request.description,
        "priority": ticket_request.priority,
        **ticket_request.details # Merge workflow-specific details
    }

    # Call the client method, which returns the detailed TufinTicket model
    created_tufin_ticket = await tufin_client.create_securechange_ticket(
        workflow_name=ticket_request.workflow_name, 
        ticket_details=tufin_ticket_data
    )
    
    # Map the detailed TufinTicket to the simplified MCP API TicketResponse
    mcp_response = TicketResponse.model_validate(created_tufin_ticket)
    # Manually add workflow_name if not automatically mapped by model_validate
    if mcp_response.workflow_name is None and created_tufin_ticket.workflow:
        mcp_response.workflow_name = created_tufin_ticket.workflow.name
        
    return mcp_response

@router.get(
    "/tickets", 
    response_model=TicketListResponse, # Use MCP API Response model
    tags=["SecureChange Tickets"],
    dependencies=[Depends(require_permission("list_tickets"))]
)
@limiter.limit("100/minute")
async def list_tickets(
    request: Request,
    # Add Tufin filter query parameters (verify exact names/types with docs)
    status: Optional[str] = Query(None, description="Filter by ticket status (e.g., Open, Resolved)"), 
    workflow: Optional[str] = Query(None, description="Filter by workflow name"),
    requester: Optional[str] = Query(None, description="Filter by requester username (or 'CURRENT_USER')"), 
    subject: Optional[str] = Query(None, description="Filter by subject (contains)"),
    # NOTE: limit/offset are not standard Tufin parameters here, pagination via next/prev links
    # limit: int = Query(100, ge=1, le=1000), 
    # offset: int = Query(0, ge=0),
    tufin_client: TufinApiClient = Depends(get_tufin_client)
) -> TicketListResponse: 
    """
    List SecureChange tickets based on query parameters.
    Requires list_tickets permission.
    """
    # Construct filter dict (Verify keys against Tufin API)
    filters = {}
    if status: filters["status"] = status
    if workflow: filters["workflow"] = workflow
    if requester: filters["requester"] = requester # How does Tufin handle CURRENT_USER?
    if subject: filters["subject"] = subject # How does Tufin handle contains?
    # Add other filters

    # Call the client method which returns the parsed Tufin response
    tufin_response = await tufin_client.list_securechange_tickets(
        # Removed limit/offset
        filters=filters if filters else None
    )
    
    # Map TufinTicket objects to our MCP API TicketResponse objects
    mcp_tickets = [
        TicketResponse.model_validate(tufin_ticket) 
        for tufin_ticket in tufin_response.ticket # Access ticket list directly
    ]
    
    # Construct the final MCP API response, including pagination links
    return TicketListResponse(
        tickets=mcp_tickets, 
        # Total is not in the Tufin list response apparently
        total=len(mcp_tickets), # Or try to parse from links if needed? Defaulting to count in batch.
        next_link=tufin_response.next.href if tufin_response.next else None,
        previous_link=tufin_response.previous.href if tufin_response.previous else None
    )

@router.get(
    "/tickets/{ticket_id}",
    response_model=TicketResponse,
    tags=["SecureChange Tickets"],
    dependencies=[Depends(require_permission("get_ticket"))] 
)
@limiter.limit("100/minute")
async def get_ticket(
    request: Request,
    ticket_id: int,
    tufin_client: TufinApiClient = Depends(get_tufin_client)
) -> TicketResponse:
    """
    Get details for a specific SecureChange ticket.
    Requires get_ticket permission.
    """
    # Client returns the detailed TufinTicket model
    tufin_ticket = await tufin_client.get_securechange_ticket(ticket_id)
    # Map the detailed Tufin model to the simplified MCP response model
    mcp_response = TicketResponse.model_validate(tufin_ticket)
    # Manually add workflow_name if not automatically mapped
    if mcp_response.workflow_name is None and tufin_ticket.workflow:
        mcp_response.workflow_name = tufin_ticket.workflow.name
        
    return mcp_response

@router.put(
    "/tickets/{ticket_id}",
    response_model=TicketResponse,
    tags=["SecureChange Tickets"],
    dependencies=[Depends(require_permission("update_ticket"))]
)
@limiter.limit("30/minute") # Stricter limit for updates
async def update_ticket(
    request: Request,
    ticket_id: int,
    ticket_data: TicketUpdate, # Use the update model for request body
    tufin_client: TufinApiClient = Depends(get_tufin_client)
) -> TicketResponse:
    """
    Update an existing SecureChange ticket.
    Requires update_ticket permission.
    """
    # Client returns detailed TufinTicket
    updated_tufin_ticket = await tufin_client.update_securechange_ticket(ticket_id, ticket_data)
    # Map to MCP response
    mcp_response = TicketResponse.model_validate(updated_tufin_ticket)
    if mcp_response.workflow_name is None and updated_tufin_ticket.workflow:
        mcp_response.workflow_name = updated_tufin_ticket.workflow.name
        
    return mcp_response