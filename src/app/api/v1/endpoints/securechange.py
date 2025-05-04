from fastapi import APIRouter, Depends, status, Request, Query
from typing import List, Any, Optional # Use Any for now for Tufin responses

# Import dependencies
from ....core.config import UserRole
from ....core.dependencies import require_permission # Updated import
from ....clients.tufin import TufinApiClient, get_tufin_client
from ....models.securechange import TicketCreate, TicketUpdate, TicketResponse, TicketListResponse # Placeholder models
# Import limiter from the new location
from ....core.limiter import limiter

router = APIRouter()

# Apply rate limiting & permission check
@router.post(
    "/tickets", 
    response_model=TicketResponse, # Placeholder
    status_code=status.HTTP_201_CREATED,
    tags=["SecureChange Tickets"],
    dependencies=[Depends(require_permission("create_ticket"))] # Use permission ID
)
@limiter.limit("30/minute") # Example specific limit for this endpoint
async def create_ticket(
    request: Request,
    ticket_data: TicketCreate, 
    tufin_client: TufinApiClient = Depends(get_tufin_client)
) -> TicketResponse: # Add return type hint
    """
    Create a new SecureChange ticket.
    Requires create_ticket permission.
    """
    # Call the client method
    created_ticket = await tufin_client.create_securechange_ticket(ticket_data)
    # The client method already returns the correct Pydantic model
    return created_ticket

@router.get(
    "/tickets", 
    response_model=TicketListResponse, # Use MCP API Response model
    tags=["SecureChange Tickets"],
    dependencies=[Depends(require_permission("list_tickets"))]
)
@limiter.limit("100/minute")
async def list_tickets(
    request: Request,
    status: Optional[str] = Query(None, description="Filter by ticket status"), 
    # Add other relevant filters
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    tufin_client: TufinApiClient = Depends(get_tufin_client)
) -> TicketListResponse: 
    """
    List SecureChange tickets based on query parameters.
    Requires list_tickets permission.
    """
    # Basic filter construction (adapt based on Tufin API)
    filters = {}
    if status: filters["status"] = status
    # Add other filters

    # Call the client method which returns the parsed Tufin response
    tufin_response = await tufin_client.list_securechange_tickets(
        limit=limit,
        offset=offset,
        filters=filters if filters else None
    )
    
    # Map TufinTicket objects to our MCP API TicketResponse objects
    mcp_tickets = [
        TicketResponse.model_validate(tufin_ticket) 
        for tufin_ticket in tufin_response.tickets.ticket # Access nested list
    ]
    
    # Construct the final MCP API response
    return TicketListResponse(
        tickets=mcp_tickets, 
        total=tufin_response.total,
        limit=limit, 
        offset=offset
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
    ticket = await tufin_client.get_securechange_ticket(ticket_id)
    # Client method returns the correct Pydantic model
    return ticket

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
    updated_ticket = await tufin_client.update_securechange_ticket(ticket_id, ticket_data)
    return updated_ticket