from pydantic import BaseModel, Field
from typing import List, Optional

# These models need verification against the actual Tufin SecureChange API v25.1!

# --- Tufin API Specific Parsing Models --- 

class TufinTicket(BaseModel):
    """Represents a single ticket from Tufin API response."""
    id: int
    subject: str
    status: Optional[str] = None # Or use an Enum if statuses are known
    # Add other fields returned by Tufin (e.g., workflow_name, priority, created_date)
    
    class Config:
        from_attributes = True

class TufinTicketListWrapper(BaseModel):
    """Intermediate model for nested 'ticket' list."""
    ticket: List[TufinTicket] = Field(default=[])
    
class TufinTicketListResponse(BaseModel):
    """Model for the full Tufin list tickets response."""
    tickets: TufinTicketListWrapper
    total: int

# --- MCP API Request/Response Models --- 

class TicketBase(BaseModel):
    subject: str
    description: Optional[str] = None
    # Add other common fields for creation/update if needed

class TicketCreate(TicketBase):
    pass 

class TicketUpdate(BaseModel):
    subject: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    # Add other updatable fields

class TicketResponse(TicketBase):
    """Ticket representation returned by our MCP API."""
    id: int 
    status: str
    # Add other fields WE want to expose

    class Config:
        from_attributes = True

class TicketListResponse(BaseModel):
    """Ticket list representation returned by our MCP API."""
    tickets: List[TicketResponse]
    total: int
    limit: int
    offset: int 