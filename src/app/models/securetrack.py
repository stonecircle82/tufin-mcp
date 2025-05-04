from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

# Adjusted based on assumed Tufin API structure.
# Verify against actual documentation!

# --- Tufin API Specific Parsing Models (Based on provided REST Schema) ---

class TufinLicense(BaseModel):
    type: Optional[str] = None
    status: Optional[str] = None
    sku: Optional[str] = None
    expiration: Optional[str] = None # Consider datetime parsing later
    used: Optional[int] = None

class TufinLicenseWrapper(BaseModel):
    license: List[TufinLicense] = Field(default=[])

class TufinDevice(BaseModel):
    """Represents a single device parsed from Tufin REST API response."""
    # Using Optional for most fields as presence might vary
    id: str # ID seems to be string in the schema
    name: Optional[str] = None
    rule_usage_mode: Optional[str] = None
    status: Optional[str] = None
    context_name: Optional[str] = None
    ip: Optional[str] = Field(None, alias='ip') # Keep original name if needed for alias
    latest_revision: Optional[str] = None
    virtual_type: Optional[str] = None
    parent_id: Optional[int] = None
    module_type: Optional[str] = None
    object_usage_mode: Optional[str] = None
    installed_policy: Optional[str] = None
    licenses: Optional[TufinLicenseWrapper] = None
    OS_Version: Optional[str] = Field(None, alias='OS_Version') # Alias if needed
    offline: Optional[bool] = None
    model: Optional[str] = None
    vendor: Optional[str] = None
    domain_id: Optional[str] = None # Assuming string based on id type
    domain_name: Optional[str] = None
    module_uid: Optional[str] = None
    topology: Optional[bool] = None

    class Config:
        from_attributes = True 
        populate_by_name = True # Allow using alias ('OS_Version') and field name ('os_version')

# Removed TufinDeviceListWrapper as the top level is now a dict with 'device' list
# class TufinDeviceListWrapper(BaseModel):
#     device: List[TufinDevice] = Field(default=[])

class TufinDeviceListResponse(BaseModel):
    """Model representing the full /devices response from Tufin REST API."""
    device: List[TufinDevice] = Field(default=[])
    count: int
    total: int # Using int, assume Pydantic handles large numbers. Or use str if truly needed.

# --- MCP API Response Models --- 

class DeviceResponse(BaseModel):
    """Device representation returned by our MCP API."""
    id: str 
    name: Optional[str] = None
    vendor: Optional[str] = None
    model: Optional[str] = None
    version: Optional[str] = Field(None, alias="OS_Version") # Map OS_Version to version
    ip_address: Optional[str] = Field(None, alias="ip") # Map ip to ip_address
    domain_name: Optional[str] = None 
    status: Optional[str] = None
    # Add other fields WE want to expose from TufinDevice

    class Config:
        from_attributes = True
        populate_by_name = True # Allow populating by alias

class DeviceListResponse(BaseModel):
    """Device list representation returned by our MCP API."""
    devices: List[DeviceResponse]
    total: int 
    count: int # Number of devices in this response
    # Removed limit/offset as they are not used in the Tufin API based on new info
    # limit: int
    # offset: int

# Removed TopologyMapResponse as the API doesn't exist

# Removed TopologyQueryRequest as parameters are passed via query
# class TopologyQueryRequest(BaseModel):
#     source: str
#     destination: str
#     service: Optional[str] = None

# --- Tufin Topology Path Response Models --- 
# Based on provided schema for GET /securetrack/api/topology/path
# Using Optional for most fields, verify exact requirements from docs

class NatEntry(BaseModel):
    type: Optional[Dict] = None # Or define specific NAT type structure
    originalServices: Optional[List[str]] = None
    policyRuleNumber: Optional[int] = None # Marked long, using int
    originalIps: Optional[List[str]] = None
    translatedIps: Optional[List[str]] = None
    translatedServices: Optional[List[str]] = None
    objectNames: Optional[List[str]] = None

class InterfaceInfo(BaseModel):
    name: Optional[str] = None
    ip: Optional[str] = None
    subnet: Optional[str] = None
    vpnConnection: Optional[str] = None
    incomingVrf: Optional[str] = None

class RouteInfo(BaseModel):
    routeDestination: Optional[str] = None
    nextHopIp: Optional[str] = None
    outgoingInterfaceName: Optional[str] = None
    outgoingVrf: Optional[str] = None
    mplsInputLabel: Optional[str] = None
    mplsOutputLabel: Optional[str] = None
    evpnInputLabel: Optional[str] = None
    evpnOutputLabel: Optional[str] = None
    evpnType: Optional[str] = None

class NextDevice(BaseModel):
    name: Optional[str] = None
    routes: Optional[List[RouteInfo]] = None

class IpsecInfo(BaseModel):
    name: Optional[str] = None
    type: Optional[Dict] = None # Or define specific type structure
    acl: Optional[str] = None
    peer: Optional[str] = None
    seqNumber: Optional[int] = None
    outgoingInterface: Optional[InterfaceInfo] = None
    participatingGateways: Optional[List[str]] = None
    satelliteGateways: Optional[List[str]] = None
    sourceIp: Optional[str] = None

class PbrAction(BaseModel):
    value: Optional[str] = None
    type: Optional[str] = None

class PbrEntry(BaseModel):
    actions: Optional[List[PbrAction]] = None
    interfaceName: Optional[str] = None
    seqNumber: Optional[int] = None
    routeMapName: Optional[str] = None
    aclName: Optional[str] = None

class RuleInfo(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    type: Optional[str] = None
    sourceNegated: Optional[bool] = None
    sources: Optional[List[str]] = None
    aclName: Optional[str] = None
    destNegated: Optional[bool] = None
    serviceNegated: Optional[bool] = None
    ruleIdentifier: Optional[str] = None
    ruleUid: Optional[str] = None
    destinations: Optional[List[str]] = None
    services: Optional[List[str]] = None
    applications: Optional[List[str]] = None
    users: Optional[List[str]] = None
    urlCategories: Optional[List[str]] = None
    action: Optional[str] = None
    ruleScope: Optional[str] = None
    tenantName: Optional[str] = None
    contractName: Optional[str] = None
    subjectName: Optional[str] = None
    serviceGraphName: Optional[str] = None
    ruleDirection: Optional[str] = None
    rulePriority: Optional[str] = None
    destinationZones: Optional[List[str]] = None
    sourceZones: Optional[List[str]] = None

class BindingInfo(BaseModel):
    name: Optional[str] = None
    rules: Optional[List[RuleInfo]] = None
    enforcedOn: Optional[List[str]] = None
    error: Optional[str] = None

class SdwanEntry(BaseModel):
    members: Optional[str] = None
    seqNumber: Optional[int] = None
    policyName: Optional[str] = None
    ruleName: Optional[str] = None

class DevicePathInfo(BaseModel): # Renamed from DeviceInfo to avoid conflict
    name: Optional[str] = None
    id: Optional[int] = None
    type: Optional[str] = None
    natList: Optional[List[NatEntry]] = None
    incomingInterfaces: Optional[List[InterfaceInfo]] = None
    vendor: Optional[str] = None
    nextDevices: Optional[List[NextDevice]] = None
    ipsecList: Optional[List[IpsecInfo]] = None
    pbrEntryList: Optional[List[PbrEntry]] = None
    bindings: Optional[List[BindingInfo]] = None
    sdwanEntryJsonList: Optional[List[SdwanEntry]] = None

class UnroutedElement(BaseModel):
    source: Optional[List[str]] = None
    destination: Optional[str] = None

class TufinTopologyPathResponse(BaseModel): # Renamed from TopologyQueryResponse
    """Model for the Tufin response from GET /securetrack/api/topology/path."""
    traffic_allowed: bool
    device_info: Optional[List[DevicePathInfo]] = None
    unrouted_elements: Optional[List[UnroutedElement]] = None

# --- MCP API Response Model --- 
class TopologyPathResponse(BaseModel):
    """Summarized path query response returned by our MCP API for easier consumption."""
    traffic_allowed: bool
    is_fully_routed: bool # True if no unrouted elements were found
    # Optional: Add a simple list of device names in the path if traffic is allowed and routed
    path_device_names: Optional[List[str]] = None 
    # Removed complex nested fields path_details and unrouted_elements
    # path_details: Optional[List[DevicePathInfo]] = Field(None, alias="device_info")
    # unrouted_elements: Optional[List[UnroutedElement]] = None

    # No Config needed unless we were mapping from a different source object directly 