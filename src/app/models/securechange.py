from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

# These models need verification against the actual Tufin SecureChange API v25.1!

# --- Tufin API Specific Parsing Models --- 

# Basic reusable components
class Link(BaseModel):
    href: Optional[str] = Field(None, alias="@href")

class IPInfo(BaseModel):
    id: Optional[str] = None
    ip: Optional[str] = None
    ipType: Optional[str] = None
    subnetMask: Optional[str] = None

class IPListWrapper(BaseModel):
    ip: List[IPInfo] = Field(default=[])

# Simplified placeholder for complex object references
ObjectReferenceDTO = Dict[str, Any] 
PartyDTO = Dict[str, Any] 
MembersOfListDTO = Dict[str, Any]

class DmInlineMembersWrapper(BaseModel):
    member: List[ObjectReferenceDTO] = Field(default=[]) # Placeholder

class ApplicationDetails(BaseModel):
    name: Optional[str] = None
    id: Optional[str] = None
    type: Optional[str] = None
    display_name: Optional[str] = None
    uid: Optional[str] = None
    management_domain: Optional[str] = None
    link: Optional[Link] = None
    ips: Optional[IPListWrapper] = None
    DM_INLINE_members: Optional[DmInlineMembersWrapper] = Field(None, alias="DM_INLINE_members")

class DateDetails(BaseModel):
    value: Optional[str] = None # Consider datetime validator
    name: Optional[str] = None
    id: Optional[int] = None # long -> int
    read_only: Optional[bool] = None

class CommentAttachment(BaseModel):
    name: Optional[str] = None
    uid: Optional[Dict] = None # Unknown structure
    link: Optional[Link] = None

class CommentAttachmentWrapper(BaseModel):
    attachment: List[CommentAttachment] = Field(default=[])

class Comment(BaseModel):
    id: Optional[int] = None # long -> int
    type: Optional[str] = None
    content: Optional[str] = None
    user: Optional[str] = None
    created: Optional[DateDetails] = None
    task_name: Optional[str] = None
    user_id: Optional[int] = None # long -> int
    attachments: Optional[CommentAttachmentWrapper] = None

class CommentWrapper(BaseModel):
    comment: List[Comment] = Field(default=[])

class WorkflowInfo(BaseModel):
    name: Optional[str] = None
    id: Optional[int] = None # long -> int
    uses_topology: Optional[bool] = None

class Permission(BaseModel):
    name: Optional[str] = None
    value: Optional[bool] = None
    key: Optional[str] = None

class PermissionWrapper(BaseModel):
    permission: List[Permission] = Field(default=[])

class Role(BaseModel):
    name: Optional[str] = None
    permissions: Optional[PermissionWrapper] = None
    id: Optional[int] = None # long -> int
    role_link: Optional[Link] = None
    description: Optional[str] = None

class RoleWrapper(BaseModel):
    role: List[Role] = Field(default=[])

class LdapConfiguration(BaseModel):
    name: Optional[str] = None
    id: Optional[int] = None # long -> int
    port: Optional[int] = None
    server: Optional[str] = None
    base_dn: Optional[str] = None
    user_dn: Optional[str] = None
    trust_any_certificate: Optional[bool] = None
    ldap_vendor: Optional[str] = None
    connect_using_ssl: Optional[bool] = None
    connect_timeout: Optional[int] = None

class DomainInfo(BaseModel):
    name: Optional[str] = None
    id: Optional[int] = None # long -> int
    description: Optional[str] = None

class DomainInfoWrapper(BaseModel):
    domain: List[DomainInfo] = Field(default=[])

class User(BaseModel): # Simplified PartyDTO
    name: Optional[str] = None
    permissions: Optional[PermissionWrapper] = None
    id: Optional[int] = None # long -> int
    type: Optional[Dict] = None # Unknown structure
    display_name: Optional[str] = None
    origin_type: Optional[str] = None
    link: Optional[Link] = None
    email: Optional[str] = None
    ldapDn: Optional[str] = None
    roles: Optional[RoleWrapper] = None
    authentication_method: Optional[str] = None
    ldap_configuration: Optional[LdapConfiguration] = None
    member_of: Optional[Dict] = None # Simplified MembersOfListDTO
    domains: Optional[DomainInfoWrapper] = None

class UserWrapper(BaseModel):
    user: List[User] = Field(default=[])

class Members(BaseModel):
    user: Optional[UserWrapper] = None
    partial_list: Optional[bool] = None

class GroupPermission(BaseModel):
    name: Optional[str] = None
    value: Optional[bool] = None

class GroupPermissionWrapper(BaseModel):
    groupPermission: List[GroupPermission] = Field(default=[])

class NotificationGroup(BaseModel): # Simplified PartyDTO
    members: Optional[Members] = None
    groupPermissions: Optional[GroupPermissionWrapper] = None
    description: Optional[str] = None
    name: Optional[str] = None
    permissions: Optional[PermissionWrapper] = None
    id: Optional[int] = None # long -> int
    type: Optional[Dict] = None # Unknown structure
    display_name: Optional[str] = None
    origin_type: Optional[str] = None
    link: Optional[Link] = None
    email: Optional[str] = None
    ldapDn: Optional[str] = None
    roles: Optional[RoleWrapper] = None
    authentication_method: Optional[str] = None
    ldap_configuration: Optional[LdapConfiguration] = None
    member_of: Optional[UserWrapper] = None # Simplified structure
    domains: Optional[DomainInfoWrapper] = None

class FieldInfo(BaseModel):
    name: Optional[str] = None
    id: Optional[int] = None # long -> int
    read_only: Optional[bool] = None

class FieldInfoWrapper(BaseModel):
    field: List[FieldInfo] = Field(default=[])

class UnlicensedDevice(BaseModel): # Simplified ObjectReferenceDTO
    name: Optional[str] = None
    id: Optional[str] = None
    type: Optional[str] = None
    display_name: Optional[str] = None
    uid: Optional[str] = None
    management_domain: Optional[str] = None
    link: Optional[Link] = None
    ips: Optional[IPListWrapper] = None
    DM_INLINE_members: Optional[DmInlineMembersWrapper] = Field(None, alias="DM_INLINE_members")

class UnlicensedDeviceWrapper(BaseModel):
    unlicensed_device_for_automation: List[UnlicensedDevice] = Field(default=[])

class PotentialHandlerWrapper(BaseModel):
    user: List[User] = Field(default=[]) # Uses simplified User model

class TaskInfo(BaseModel):
    name: Optional[str] = None
    fields: Optional[FieldInfoWrapper] = None
    id: Optional[int] = None # long -> int
    status: Optional[str] = None
    unlicensed_devices_for_automation: Optional[UnlicensedDeviceWrapper] = None
    task_business_duration: Optional[int] = None # long -> int
    assignee: Optional[str] = None
    pending_reason: Optional[str] = None
    assignee_id: Optional[int] = None # long -> int
    is_assigner: Optional[bool] = None
    pending_reason_description: Optional[str] = None
    potential_handlers: Optional[PotentialHandlerWrapper] = None

class TaskInfoWrapper(BaseModel):
    task: List[TaskInfo] = Field(default=[])

class StepInfo(BaseModel):
    name: Optional[str] = None
    id: Optional[int] = None # long -> int
    tasks: Optional[TaskInfoWrapper] = None
    skipped: Optional[bool] = None
    redone: Optional[bool] = None
    business_duration: Optional[int] = None # long -> int

class StepInfoWrapper(BaseModel):
    step: List[StepInfo] = Field(default=[])

class ExternalData(BaseModel):
    request_id: Optional[str] = None
    requester: Optional[str] = None

class CurrentStepInfo(BaseModel):
    name: Optional[str] = None
    id: Optional[int] = None # long -> int

class ApplicationChange(BaseModel): # Simplified
    # Define based on actual structure if needed
    pass

class ApplicationChangeWrapper(BaseModel):
    application_change: List[ApplicationChange] = Field(default=[])

class CompletionDetails(BaseModel):
    stepId: Optional[int] = None # long -> int

# --- Main Tufin Ticket Models --- 

class TufinTicket(BaseModel):
    """Represents a single ticket from Tufin API response using nested models."""
    priority: Optional[str] = None
    id: Optional[int] = None # long -> int
    status: Optional[str] = None
    application_details: Optional[ApplicationDetails] = None
    comments: Optional[CommentWrapper] = None
    expiration_date: Optional[str] = None # Consider datetime
    subject: Optional[str] = None
    domain_name: Optional[str] = None
    workflow: Optional[WorkflowInfo] = None
    referenced_ticket: Optional[ApplicationDetails] = None # Reusing ApplicationDetails structure
    create_date: Optional[DateDetails] = None
    update_date: Optional[DateDetails] = None
    close_date: Optional[DateDetails] = None
    requester: Optional[str] = None
    notification_group: Optional[NotificationGroup] = None
    sla_status: Optional[str] = None
    sla_outcome: Optional[str] = None
    sla_tracking_state: Optional[str] = None
    steps: Optional[StepInfoWrapper] = None
    requester_id: Optional[int] = None # long -> int
    expiration_status: Optional[Dict] = None # Unknown structure
    business_duration: Optional[int] = None # long -> int
    expiration_field_name: Optional[str] = None
    external_data: Optional[ExternalData] = None
    current_step: Optional[CurrentStepInfo] = None
    application_changes: Optional[ApplicationChangeWrapper] = None
    completion_details: Optional[CompletionDetails] = None

    class Config:
        from_attributes = True

class TufinTicketListWrapper(BaseModel):
    """Wrapper for the list of tickets in the Tufin GET /tickets response."""
    ticket: List[TufinTicket] = Field(default=[])
    
class TufinTicketListResponse(BaseModel):
    """Model for the full Tufin GET /tickets response, including pagination links."""
    # Note: The schema shows the list directly under root, not nested like device list
    # Adjust if schema example was simplified
    # tickets: Optional[TufinTicketListWrapper] = None 
    ticket: List[TufinTicket] = Field(default=[]) # Assuming list is direct
    # Total field is missing from the list schema provided, relying on next/prev links?
    # total: Optional[int] = None
    next: Optional[Link] = None
    previous: Optional[Link] = None

# --- MCP API Request/Response Models --- 

class TicketBase(BaseModel):
    # Basic fields likely common to most workflows for creation via MCP
    subject: str
    description: Optional[str] = None
    priority: Optional[str] = None # Example common field
    # Add other common fields if applicable

class TicketCreate(BaseModel):
    """Request model for creating a ticket via the MCP API."""
    workflow_name: str = Field(..., description="The exact name of the Tufin SecureChange workflow to use.")
    # Use a generic dict for workflow-specific details
    details: Dict[str, Any] = Field(..., description="Workflow-specific fields required by Tufin.")
    # Include common fields if they are part of the main request, not nested
    subject: str 
    description: Optional[str] = None
    priority: Optional[str] = None

class TicketUpdate(BaseModel):
    subject: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    # Add other updatable fields

class TicketResponse(TicketBase):
    """Ticket representation returned by our MCP API (potentially simplified)."""
    id: int 
    status: str
    workflow_name: Optional[str] = None # Expose workflow name
    # Add other fields WE want to expose from the detailed TufinTicket model

    class Config:
        from_attributes = True

class TicketListResponse(BaseModel):
    """Ticket list representation returned by our MCP API."""
    tickets: List[TicketResponse]
    total: int
    # Add pagination links if Tufin API provides them
    next_link: Optional[str] = None
    previous_link: Optional[str] = None
    # limit: int # Removed
    # offset: int # Removed 