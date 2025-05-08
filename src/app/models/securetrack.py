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

# --- MCP API Device Add Models --- 

class DeviceDataAdd(BaseModel):
    """Generic placeholder for device_data. Client must provide correct structure."""
    # Allows any extra fields
    class Config:
        extra = "allow"

class DeviceAddRequest(BaseModel):
    """Request model for adding a single device within the bulk request."""
    display_name: str
    ip_address: Optional[str] = None # Required depending on device type
    vendor: str 
    model: Optional[str] = None
    # Add other common fields from the outer Tufin schema if needed (e.g., enable_topology)
    enable_topology: Optional[bool] = True 
    securetrack_domain: Optional[str] = "Default" # Example default
    # device_data is required by Tufin, structure varies by vendor/model
    device_data: Dict[str, Any] = Field(..., description="Vendor/Model specific configuration and credentials.")

class DeviceBulkAddRequest(BaseModel):
    """Request model for the MCP API to add one or more devices."""
    devices: List[DeviceAddRequest] = Field(..., min_length=1)

class DeviceBulkAddResponse(BaseModel):
    """Response model indicating acceptance of the bulk add request."""
    message: str
    detail: Optional[str] = None
    # Tufin API only returns 202, no details on individual successes/failures immediately 

# --- MCP/Tufin API Device Import Models --- 

# Define structures for different types of managed devices to import
# Based on Tufin examples for POST /devices/bulk/import
class ImportablePanoramaDG(BaseModel):
    name: str
    import_all: bool
    managed_devices: Optional[List[str]] = None # Only present if import_all is false

class ImportableFortiManagerADOM(BaseModel):
    name: str
    import_all: bool
    managed_devices: Optional[List[str]] = None # Only present if import_all is false

class ImportableMerakiOrg(BaseModel):
    name: str
    import_all: bool
    managed_devices: Optional[List[str]] = None # Only present if import_all is false

class ImportableAzureVNet(BaseModel):
    name: str

class ImportableAWSVPC(BaseModel):
    name: str

class ImportableAristaEOS(BaseModel):
    name: str

# Generic Device Data for Import request (Tufin API structure)
# This will contain vendor-specific import lists
class TufinImportDeviceData(BaseModel):
    import_all: bool # Seems common, but might be specific per type
    # This field holds the varying list structures based on parent type
    # Using Any here for flexibility, validation happens based on context
    import_devices: List[Any] 
    # Include other fields if common across import types (e.g., usage flags?)
    collect_rule_usage_traffic_logs: Optional[bool] = None
    collect_object_usage_traffic_logs: Optional[bool] = None
    collect_dynamic_topology: Optional[bool] = None
    # Arista specific?
    user_name: Optional[str] = None 
    password: Optional[str] = None
    enable: Optional[bool] = None
    enable_password: Optional[str] = None

    class Config:
        extra = 'allow' # Allow other fields if needed for specific types

# Represents one item in the Tufin bulk import request list
class TufinImportDeviceItem(BaseModel):
    device_id: str # ID of the *parent* management device
    enable_topology: Optional[bool] = None # Optional outer fields
    # device_data contents MUST match the requirements for the parent device_id type
    device_data: TufinImportDeviceData
    # Arista specific?
    securetrack_domain: Optional[str] = None
    securetrack_server: Optional[str] = None
    model: Optional[str] = None
    vendor: Optional[str] = None

# --- MCP API Request/Response Models for Import --- 

class ManagedDeviceImportDetail(BaseModel):
    """Details of managed devices to import (used in MCP request)."""
    # Structure mirrors Tufin examples where applicable
    name: str
    import_all: Optional[bool] = None # Applicable for Panorama, FortiManager, Meraki
    managed_devices: Optional[List[str]] = None # For specific device listing

class DeviceImportRequestData(BaseModel):
    """Data specific to the import operation for a parent device (MCP Request)."""
    import_all: bool
    import_devices: List[ManagedDeviceImportDetail] # Use structured list
    # Add optional common flags if desired at MCP level
    collect_rule_usage: Optional[bool] = None
    collect_object_usage: Optional[bool] = None

class DeviceImportItem(BaseModel):
    """Represents a single parent device update in the MCP bulk import request."""
    device_id: str = Field(..., description="ID of the existing parent management device (e.g., Panorama, FortiManager).")
    device_data: DeviceImportRequestData = Field(..., description="Details of the managed devices to import.")

class DeviceBulkImportRequest(BaseModel):
    """Request model for the MCP API to import managed devices."""
    devices: List[DeviceImportItem] = Field(..., min_length=1)

class DeviceBulkImportResponse(BaseModel):
    """Response model indicating acceptance of the bulk import request."""
    message: str
    detail: Optional[str] = None
    # Tufin API only returns 202, no details on individual successes/failures immediately 

# --- GraphQL Rule Query Models --- 

class RuleQueryRequest(BaseModel):
    tql_filter: Optional[str] = Field(None, description="Tufin Query Language (TQL) filter string.")
    # Add other potential parameters like field selection later if needed

# Simplified models for common fields returned by GraphQL query
# These should be expanded based on the actual 'rule_fields' requested in the client
class RuleZoneInfo(BaseModel):
    text: Optional[str] = None

class RuleNetworkObjectInfo(BaseModel):
    text: Optional[str] = None
    zones: Optional[List[RuleZoneInfo]] = None

class RuleServiceObjectInfo(BaseModel):
    text: Optional[str] = None

class RuleApplicationObjectInfo(BaseModel):
    text: Optional[str] = None

class RuleUserObjectInfo(BaseModel):
    text: Optional[str] = None

class RuleInstallOnObjectInfo(BaseModel):
    text: Optional[str] = None

class RuleVpnObjectInfo(BaseModel):
    text: Optional[str] = None

class RuleMetadata(BaseModel):
    certificationStatus: Optional[str] = None
    technicalOwner: Optional[str] = None
    applicationOwner: Optional[str] = None
    ruleDescription: Optional[str] = None
    businessOwner: Optional[str] = None

class RuleDetail(BaseModel):
    """Represents selected details of a firewall rule returned by MCP."""
    id: str # Assuming GraphQL ID is string
    name: Optional[str] = None
    action: Optional[str] = None
    comment: Optional[str] = None
    disabled: Optional[bool] = None
    implicit: Optional[bool] = None
    metadata: Optional[RuleMetadata] = None
    source: Optional[RuleNetworkObjectInfo] = None
    destination: Optional[RuleNetworkObjectInfo] = None
    service: Optional[RuleServiceObjectInfo] = None
    application: Optional[RuleApplicationObjectInfo] = None
    user: Optional[RuleUserObjectInfo] = None
    installOn: Optional[RuleInstallOnObjectInfo] = Field(None, alias="installOn")
    vpn: Optional[RuleVpnObjectInfo] = None

    class Config:
        populate_by_name = True

class RuleQueryResponseValues(BaseModel):
    """Structure within GraphQL response containing list of rules."""
    count: int
    values: List[RuleDetail] = Field(default=[])

class RuleQueryResponse(BaseModel):
    """MCP API response for a rule query."""
    rules: RuleQueryResponseValues

    class Config:
        populate_by_name = True # Allow alias mapping