import pytest
from httpx import AsyncClient
import respx # For mocking HTTP calls

# Import config and roles for setting up test keys/permissions if needed
# This assumes direct access for test setup - adjust if using fixtures
from src.app.core.config import settings, UserRole
from src.app.core.secure_store import secure_store_instance, pwd_context # Access store/hashing for setup

# --- Test Keys (for development/testing ONLY) --- 
# Match roles defined in DEV_API_KEYS or add specific test keys
# WARNING: Do not use real keys here!
TEST_ADMIN_KEY = "test_admin_key_123"
TEST_USER_KEY = "test_user_key_456"
INVALID_KEY = "invalid_key_789"

@pytest.fixture(scope="module", autouse=True)
async def setup_test_keys():
    """Fixture to ensure test keys are loaded into the in-memory store."""
    # Manually add hashed keys for testing - bypasses DEV_API_KEYS env var reliance
    # Clear existing keys first if necessary
    secure_store_instance._storage = {} # Accessing protected member for test setup
    
    hashed_admin = pwd_context.hash(TEST_ADMIN_KEY)
    hashed_user = pwd_context.hash(TEST_USER_KEY)
    
    secure_store_instance._storage[hashed_admin] = UserRole.ADMIN
    secure_store_instance._storage[hashed_user] = UserRole.USER
    print(f"Loaded test keys: {len(secure_store_instance._storage)}")
    # No yield needed for module scope fixture setting up state

# --- Test Cases --- 

@pytest.mark.asyncio
async def test_health_check(test_client: AsyncClient):
    """Test the public /health endpoint."""
    response = await test_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_list_devices_unauthorized(test_client: AsyncClient):
    """Test accessing a protected endpoint without API key."""
    response = await test_client.get("/api/v1/devices")
    assert response.status_code == 401
    assert "Missing API Key" in response.json()["detail"]

@pytest.mark.asyncio
async def test_list_devices_invalid_key(test_client: AsyncClient):
    """Test accessing a protected endpoint with an invalid API key."""
    headers = {"X-API-Key": INVALID_KEY}
    response = await test_client.get("/api/v1/devices", headers=headers)
    assert response.status_code == 401
    assert "Invalid API Key" in response.json()["detail"]

@pytest.mark.asyncio
@respx.mock # Enable mocking external HTTP calls for this test
async def test_list_devices_success(test_client: AsyncClient, respx_mock):
    """Test successful access to /api/v1/devices with mocking."""
    headers = {"X-API-Key": TEST_USER_KEY} # User role should have access

    # Mock the Tufin API call made by the client
    # Construct the expected URL the client will call
    tufin_devices_url = f"{settings.TUFIN_SECURETRACK_URL.rstrip('/')}/securetrack/api/devices"
    
    # Define the mocked Tufin API response
    mock_tufin_response = {
        "device": [
            {"id": "dev1", "name": "Firewall-Test", "vendor": "TestVendor"},
            {"id": "dev2", "name": "Router-Test", "vendor": "OtherVendor"}
        ],
        "count": 2,
        "total": 2
    }
    
    # Route the mock: when the client calls this URL, return the mock response
    respx_mock.get(tufin_devices_url).mock(return_value=respx.Response(200, json=mock_tufin_response))

    # Make the request to our MCP server
    response = await test_client.get("/api/v1/devices", headers=headers, params={"status": "started"}) 
    
    # Assertions on our MCP server's response
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["count"] == 2
    assert len(data["devices"]) == 2
    assert data["devices"][0]["id"] == "dev1"
    assert data["devices"][0]["vendor"] == "TestVendor"

@pytest.mark.asyncio
async def test_get_device_forbidden(test_client: AsyncClient):
    """Test role restriction - trying to access admin-only endpoint with user key."""
    # Assuming /tufin-version requires ADMIN based on previous setup
    # We need to ensure this permission is set correctly in config
    headers = {"X-API-Key": TEST_USER_KEY} 
    # Mock the Tufin call for domains (needed by the /tufin-version endpoint)
    # Use respx if the endpoint actually makes an external call
    # For simplicity, assume it might fail before the Tufin call due to RBAC
    response = await test_client.get("/tufin-version", headers=headers)
    assert response.status_code == 403
    assert "Insufficient permissions" in response.json()["detail"]

# TODO: Add tests for:
# - Other endpoints (GET/POST/PUT tickets, GET device, topology)
# - Different roles and permissions
# - Rate limiting (requires simulating multiple requests)
# - Specific filter parameters
# - Error handling (e.g., Tufin API returning 500) 