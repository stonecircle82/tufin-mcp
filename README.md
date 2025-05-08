# Tufin MCP Server - Open Source Community Project

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE) <!-- Optional: Add license badge -->
<!-- Optional: Add build status, code coverage badges etc. -->

## Introduction

Welcome to the Tufin MCP (Multi-Controller Protocol) Server project! This open-source initiative aims to provide Tufin users with a powerful tool to bridge the gap between Tufin's robust APIs (SecureTrack and SecureChange) and modern AI development workflows.

By exposing Tufin functionalities through a secure, standardized REST API with Role-Based Access Control (RBAC), this server allows you to easily integrate Tufin data and actions into your custom scripts, applications, and AI agents (like those running in Cursor, ChatGPT Actions, Ollama, etc.).

**This is a community-driven project.** We encourage contributions! Whether it's adding new endpoint coverage, improving security, enhancing the client libraries, or fixing bugs, your input is valuable. Please check the [Contributing](#contributing) section for more details.

Find the project repository on GitHub: [https://github.com/stonecircle82/tufin-mcp](https://github.com/stonecircle82/tufin-mcp) <!-- ** ACTION REQUIRED: Replace with your actual repo URL ** -->

## Why Use This?

*   **Simplify AI Integration:** Provides a modern REST API layer over Tufin's existing APIs, making it easier to integrate with AI tools, chatbots, and automation scripts.
*   **Centralized Control:** Manage Tufin access and authentication from one place.
*   **Enhanced Security:** Adds API Key and Role-Based Access Control on top of Tufin's authentication.
*   **Extensibility:** Designed to be extended to cover more Tufin APIs and potentially other security platforms.
*   **Future Potential:** Aims to support newer Tufin APIs (like GraphQL) and features like bulk operations (e.g., adding devices from a file) which can be complex via direct API calls.

## Overview

This server acts as a secure proxy and abstraction layer for Tufin APIs (v25.1 targeted).

**Key Features:**
*   Standard REST/JSON API interface (documented via OpenAPI).
*   Centralized Tufin Authentication (using Basic Auth configured via environment variables).
*   API Key Authentication for MCP clients (keys are hashed using bcrypt).
*   Configurable Role-Based Access Control (Admin, Ticket Manager, User).
*   Endpoints for key SecureChange and SecureTrack operations (Ticketing, Devices, Topology).
*   Structured JSON Logging with Request IDs.
*   IP-based Rate Limiting.
*   Basic Python Client Library.
*   Docker support.

## Getting Started

### Prerequisites

*   Python 3.8+
*   Access to running Tufin SecureTrack and SecureChange instances (v25.1 compatible).
*   Docker (if running via container).
*   Git.

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/<your-username>/tufin-mcp.git # ** Replace URL **
    cd tufin-mcp
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate # On Windows use `venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### Configuration

Configuration is managed via environment variables or a `.env` file in the project root.

1.  **Create `.env` file:** Copy `.env.example` (if provided) or create `.env` manually.

2.  **Set required variables:**
    ```dotenv
    # Server Settings
    MCP_PORT=8000
    LOG_LEVEL="INFO" # DEBUG, INFO, WARNING, ERROR

    # Tufin Connection (REPLACE with your details)
    TUFIN_SECURETRACK_URL="https://your-securetrack-host"
    TUFIN_SECURECHANGE_URL="https://your-securechange-host"
    TUFIN_USERNAME="your_tufin_username"
    TUFIN_PASSWORD="your_tufin_password"
    TUFIN_SSL_VERIFY="True" # Set to False only if absolutely necessary (insecure!)
    TUFIN_API_TIMEOUT="30.0" # Timeout for Tufin API calls in seconds

    # --- Development API Keys (Insecure - For Dev/Test Only!) ---
    # For the default In-Memory secure store, provide initial RAW keys and roles via this JSON string.
    # The server will HASH the keys on startup and store them in memory.
    # DO NOT USE PRODUCTION KEYS HERE.
    DEV_API_KEYS='[{"key":"admin_key_abc", "role":"admin"}, {"key":"manager_key_xyz", "role":"ticket_manager"}, {"key":"user_key_123", "role":"user"}]'
    ```

    **SSL Verification Note (`TUFIN_SSL_VERIFY`):** By default, the server attempts to verify the SSL certificates of your Tufin instances (`TUFIN_SSL_VERIFY="True"`). Setting this to `"False"` disables verification, which can be necessary for environments using self-signed certificates, but it is **highly insecure for production** as it exposes the connection to man-in-the-middle attacks. If using internal CAs, consider configuring the underlying system or providing a custom CA bundle path (requires code modification).

    **Production Security Note:** API Keys are **hashed** using bcrypt. The default `InMemorySecureStore` loads raw keys from `DEV_API_KEYS` **only for development**. For production, you **MUST**: 
    1.  Replace `InMemorySecureStore` in `src/app/core/secure_store.py` with an implementation using a secure database or secrets manager (e.g., HashiCorp Vault).
    2.  Implement a secure process/endpoint for managing API keys (generating, storing hash+role, revoking).
    3.  Do not use `DEV_API_KEYS` in production.

## Running the Server

### Local Development (Uvicorn)

```bash
# From the project root directory
uvicorn src.app.main:app --reload --port ${MCP_PORT:-8000}
```
*   The `--reload` flag enables auto-reloading on code changes.
*   Uses the port defined in `.env` or defaults to 8000.

### Docker Container

1.  **Build the image:**
    ```bash
    # From the project root directory
    docker build -t tufin-mcp-server:latest .
    ```

2.  **Run the container:**
    ```bash
    docker run --rm -d \
      --name tufin-mcp \
      --env-file .env \
      -p ${MCP_PORT:-8000}:${MCP_PORT:-8000} \
      tufin-mcp-server:latest
    ```
    *   Loads environment variables from your local `.env` file.
    *   Maps the host port to the container port (defined by `MCP_PORT` or default 8000).

3.  **Accessing:** `http://localhost:${MCP_PORT:-8000}`
4.  **Logs:** `docker logs tufin-mcp` (`-f` to follow)
5.  **Stopping:** `docker stop tufin-mcp`

## Testing

This project uses `pytest` for testing.

1.  **Install test dependencies:**
    ```bash
    pip install -r requirements-dev.txt
    ```

2.  **Run tests:**
    ```bash
    # From the project root directory
    pytest
    ```
    *   You can run specific files: `pytest tests/api/v1/test_endpoints.py`
    *   Use `-v` for verbose output: `pytest -v`
    *   Use `-k` to filter tests by name: `pytest -k list_devices`

3.  **Test Coverage (Optional):**
    Install `pytest-cov` (`pip install pytest-cov`) and run:
    ```bash
    pytest --cov=src/app --cov-report=term-missing
    ```

## API Usage

### Authentication

Pass your generated API key in the `X-API-Key` HTTP header for all requests except `/health`.

### Authorization (RBAC)

Access is controlled by roles assigned to API keys during key creation (using a secure production process or via `DEV_API_KEYS` for development). Allowed roles for each endpoint are configured in `src/app/core/config.py` under `ENDPOINT_PERMISSIONS`.

*   **Roles:** `admin`, `ticket_manager`, `user`.
*   Attempting an action without the required permission results in `403 Forbidden`.

**Configuring Endpoint Permissions:**

The `ENDPOINT_PERMISSIONS` dictionary in `src/app/core/config.py` defines which roles can access which logical action (permission ID). Example:

```python
# src/app/core/config.py
ENDPOINT_PERMISSIONS: Dict[str, List[UserRole]] = {
    "list_devices": [UserRole.ADMIN, UserRole.TICKET_MANAGER, UserRole.USER],
    "get_device": [UserRole.ADMIN, UserRole.TICKET_MANAGER, UserRole.USER],
    "create_ticket": [UserRole.ADMIN, UserRole.TICKET_MANAGER],
    # ... other permissions ...
}
```

*   **Why this approach?** This centralizes access control policy in one place, making it easy to review and modify permissions without changing the endpoint code itself.
*   **How it works:** Each API endpoint route uses the `require_permission("permission_id")` dependency. This dependency checks if the role associated with the user's validated API key is present in the list defined for that specific `permission_id` in the `ENDPOINT_PERMISSIONS` dictionary.
*   **Customization:** You can easily customize access by modifying the list of `UserRole` enums for any given permission ID directly within `config.py`. Add new permission IDs as you add new endpoints.

### Rate Limiting

IP-based rate limits apply (default: 60/minute). Exceeding limits results in `429 Too Many Requests`.

### Endpoints Overview

The API structure is defined in `openapi.yaml`. You can explore this file directly or use tools like Swagger UI if the spec is served by the application (requires adding static file serving to `main.py`).

**Current Endpoint Summary:**
*   `GET /health`: Health check.
*   `POST /api/v1/tickets`: Create SecureChange ticket.
*   `GET /api/v1/tickets`: List SecureChange tickets (Supports filtering by `status`).
*   `GET /api/v1/tickets/{ticket_id}`: Get a specific SecureChange ticket.
*   `PUT /api/v1/tickets/{ticket_id}`: Update a SecureChange ticket.
*   `GET /api/v1/devices`: List SecureTrack devices (Supports filtering by `status`, `name`, `vendor`).
*   `GET /api/v1/devices/{device_id}`: Get SecureTrack device details.
*   `POST /api/v1/devices/bulk`: Add one or more devices (requires vendor-specific `device_data` in request body).
*   `POST /api/v1/devices/bulk/import`: Import managed devices (DGs, ADOMs, contexts, etc.) into existing management devices.
*   `GET /api/v1/topology/map`: Get SecureTrack topology map.
*   `POST /api/v1/topology/query`: Run a SecureTrack topology query.
*   `GET /api/v1/topology/path`: Run a SecureTrack topology path query. Returns a **summarized** result including `traffic_allowed`, `is_fully_routed`, and `path_device_names` (if allowed/routed).
*   `GET /api/v1/topology/path/image`: Get the topology path as an image (e.g., PNG).
*   `POST /api/v1/graphql/rules`: Query SecureTrack rules using GraphQL and TQL filter.

**Note:** Implementation requires verification against Tufin 25.1 REST API docs. Filter implementation needs checking against specific Tufin API syntax.

### Basic Examples (`curl`)

```bash
# Set environment variables for convenience
export MCP_URL="http://localhost:8000"
export MCP_API_KEY="your_api_key_here"

# Health Check
curl "$MCP_URL/health"

# List Devices
curl -H "X-API-Key: $MCP_API_KEY" "$MCP_URL/api/v1/devices?limit=5"

# Create Ticket (Requires appropriate role for the key)
curl -X POST -H "X-API-Key: $MCP_API_KEY" -H "Content-Type: application/json" \
     -d '{"subject": "API: Allow Port 443", "description": "...details..."}' \
     "$MCP_URL/api/v1/tickets"

# Example Topology Path Query
curl -G -H "X-API-Key: $MCP_API_KEY" "$MCP_URL/api/v1/topology/path" \
     --data-urlencode "src=1.1.1.1" \
     --data-urlencode "dst=8.8.8.8" \
     --data-urlencode "service=tcp:443"
# Example Topology Path Image Request (save to file)
curl -H "X-API-Key: $MCP_API_KEY" "$MCP_URL/api/v1/topology/path/image?src=1.1.1.1&dst=8.8.8.8&service=tcp:443" -o topology_path.png

# Example Add Device (Cisco ASA - requires ADMIN role & correct device_data)
curl -X POST -H "X-API-Key: $MCP_API_KEY" -H "Content-Type: application/json" \
     -d '{
           "devices": [
             {
               "display_name": "MCP-ASA-Test",
               "ip_address": "10.1.2.3",
               "vendor": "Cisco",
               "model": "ASA",
               "securetrack_domain": "Default",
               "enable_topology": true,
               "device_data": {
                 "user_name": "tufin-api-user", 
                 "password": "tufin-api-password",
                 "enable_password": "tufin-enable-password"
                 # Add other ASA specific fields from Tufin docs here
               }
             }
           ]
         }' \
     "$MCP_URL/api/v1/devices/bulk"

# Example Import Managed Devices (Panorama DG)
curl -X POST -H "X-API-Key: $MCP_API_KEY" -H "Content-Type: application/json" \
     -d '{
           "devices": [
             {
               "device_id": "1", 
               "device_data": {
                 "import_all": false,
                 "import_devices": [
                   {"name": "DG1", "import_all": false, "managed_devices": ["fw1"]}
                 ]
               }
             }
           ]
         }' \
     "$MCP_URL/api/v1/devices/bulk/import"

# Example GraphQL Rule Query (using curl and jq for readability)
# Find firewall rules allowing any source to 8.8.8.8
export TQL_FILTER="destination.ip 8.8.8.8"
curl -X POST -H "X-API-Key: $MCP_API_KEY" -H "Content-Type: application/json" \
     -d "{\"tql_filter\": \"$TQL_FILTER\"}" \
     "$MCP_URL/api/v1/graphql/rules" | jq
```

## OpenAPI Specification

An OpenAPI 3.0 specification file (`openapi.yaml`) is included in the root directory. This file formally describes the API, including endpoints, parameters, request/response schemas, and security requirements. It can be used with various tools:

*   **Code Generation:** Generate client libraries in different languages.
*   **API Documentation:** Use tools like Swagger UI or Redoc to render interactive documentation.
*   **AI Integration:** Import into platforms like ChatGPT Actions to enable interaction.
*   **Testing Tools:** Use with tools like Postman or Insomnia.

**(Optional Enhancement):** Consider configuring FastAPI to serve this specification automatically at `/openapi.yaml` and interactive documentation (Swagger UI/Redoc).

## Python Client Library

A basic Python client library structure is provided in `client_libs/python/`.

### Installation (from local source)

```bash
# From the project root directory
cd client_libs/python
pip install .
```

### Usage Example

```python
from tufin_mcp_client import TufinMCPClient, TufinMCPClientError

SERVER_URL = "http://localhost:8000" 
API_KEY = "your_api_key_here"

# Use as a context manager (recommended)
with TufinMCPClient(base_url=SERVER_URL, api_key=API_KEY) as client:
    try:
        health = client.get_health()
        print(f"Health: {health}")
        
        devices = client.list_devices()
        print(f"Devices Found: {devices.total}")
        
        # Example: Get first device if list is not empty
        if devices.devices:
            first_device_id = devices.devices[0].id
            device_details = client.get_device(first_device_id)
            print(f"Device {first_device_id}: {device_details.name} ({device_details.vendor})")
        
        # Example: Create Ticket 
        ticket_data = {
            "workflow_name": "Example Firewall Workflow", # Check configured workflows
            "subject": "Client Lib Test", 
            "details": { # Workflow specific fields go here
                "description": "Testing ticket creation via client",
                "priority": "Medium"
                 # Add other fields required by the specific workflow
            }
        }
        created_ticket = client.create_ticket(ticket_data)
        print(f"Created Ticket ID: {created_ticket.id}, Status: {created_ticket.status}")
        ticket_id = created_ticket.id
        
        if ticket_id:
            retrieved_ticket = client.get_ticket(ticket_id)
            print(f"Retrieved Ticket {ticket_id}: Subject: {retrieved_ticket.subject}")
            
            updated_data = {"status": "In Progress"} # Check actual updatable fields
            updated_ticket = client.update_ticket(ticket_id, updated_data)
            print(f"Updated Ticket {ticket_id}: Status: {updated_ticket.status}")
            
            # Example Add Device
            asa_device = {
              "display_name": "MCP-ASA-Test-Client",
              "ip_address": "10.1.2.4",
              "vendor": "Cisco",
              "model": "ASA",
              "securetrack_domain": "Default",
              "enable_topology": True,
              "device_data": {
                 "user_name": "tufin-api-user", 
                 "password": "tufin-api-password",
                 "enable_password": "tufin-enable-password"
              }
            }
            client.add_devices([asa_device]) # Pass as a list
            print("Device add request accepted.")
            
        # Example Import Managed Device
        import_details = {
            "devices": [
                {
                    "device_id": "1", # Panorama ID
                    "device_data": {
                        "import_all": False,
                        "import_devices": [
                            {"name": "DG_CLIENT", "import_all": True}
                        ]
                    }
                }
            ]
        }
        client.import_managed_devices(import_details)
        print("Managed device import request accepted.")

        # Example GraphQL Rule Query
        rule_filter = "action accept and source.ip 192.168.1.0/24"
        rules_response = client.query_rules_graphql(tql_filter=rule_filter)
        print(f"\nFound {rules_response.rules.count} rules matching filter:")
        for rule in rules_response.rules.values:
            print(f"  - ID: {rule.id}, Name: {rule.name}, Action: {rule.action}")
            
    except TufinMCPClientError as e:
        print(f"MCP Client Error: {e}")
        if e.status_code:
            print(f"  Status Code: {e.status_code}")
        if e.response_text:
            print(f"  Response: {e.response_text}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
```
**Note:** The client library provides basic functionality, error handling (`TufinMCPClientError`), and returns Pydantic models for responses. Further enhancements are planned (see Roadmap).

## JavaScript / TypeScript Client Library

A basic TypeScript client library structure **for interacting with the MCP Server API** is provided in `client_libs/javascript/`.

### Installation

```bash
# From your JS/TS project directory
npm install <path_to_client_libs/javascript> 
# or link for local development
# cd client_libs/javascript && npm link && cd ../../ && npm link tufin-mcp-client-js

# Or if published to npm:
# npm install tufin-mcp-client-js 
```
Make sure to build the client first if installing from source: `cd client_libs/javascript && npm run build && cd ../..`

### Usage Example (TypeScript)

```typescript
import { TufinMCPClient, TufinMCPClientError } from 'tufin-mcp-client-js'; // Adjust import path

const SERVER_URL = 'http://localhost:8000'; // Your MCP Server URL
const API_KEY = 'your_api_key_here';

const client = new TufinMCPClient(SERVER_URL, API_KEY);

async function runClient() {
    try {
        const health = await client.getHealth();
        console.log('Health:', health);

        const devices = await client.listDevices({ limit: 5 }); // Example param
        console.log(`Devices Found: ${devices.total}`);
        console.log('First device:', devices.devices[0]);
        
        // Example: Create Ticket
        const ticketData = {
            workflow_name: 'Example Firewall Workflow', // Check configured workflows
            subject: 'TS Client Test',
            details: {
                description: 'Testing ticket from TS client',
                priority: 'Low'
                // Add other workflow-specific fields
            }
        };
        const createdTicket = await client.createTicket(ticketData);
        console.log(`Created Ticket ID: ${createdTicket.id}, Status: ${createdTicket.status}`);

        // Example Add Device
        const asaDevice = {
          display_name: "MCP-ASA-Test-JS",
          ip_address: "10.1.2.5",
          vendor: "Cisco",
          model: "ASA",
          securetrack_domain: "Default",
          enable_topology: true,
          device_data: {
             user_name: "tufin-api-user", 
             password: "tufin-api-password",
             enable_password: "tufin-enable-password"
          }
        };
        await client.addDevices([asaDevice]); // Pass as an array
        console.log("Device add request accepted.");

        // Example Import Managed Device
        const importDetails = {
          devices: [
            {
              device_id: "1", // Panorama ID
              device_data: {
                import_all: false,
                import_devices: [
                  { name: "DG_JS_CLIENT", import_all: true }
                ]
              }
            }
          ]
        };
        await client.importManagedDevices(importDetails);
        console.log("Managed device import request accepted.");

        // Example GraphQL Rule Query
        const ruleFilter = "disabled true";
        const rulesResponse = await client.queryRulesGraphQL({tql_filter: ruleFilter});
        console.log(`\nFound ${rulesResponse.rules.count} disabled rules:`);
        rulesResponse.rules.values.forEach(rule => {
            console.log(`  - ID: ${rule.id}, Name: ${rule.name}`);
        });

    } catch (error) {
        if (error instanceof TufinMCPClientError) {
            console.error('MCP Client Error:', error.message);
            if (error.status) {
                console.error('  Status Code:', error.status);
            }
            if (error.data) {
                console.error('  Response Data:', error.data);
            }
        } else {
            console.error('An unexpected error occurred:', error);
        }
    }
}

runClient();
```
**Note:** This client is basic. It needs further development for comprehensive error handling, potential model parsing (if not relying on `any`), and more robust type safety.

## Direct Tufin API Client (Alternative)

For scenarios where you need to bypass the MCP Server and connect directly to the Tufin APIs using basic authentication, a separate, simpler JS/TS client library is available in `client_libs/javascript_direct/`. See the README within that directory for details.

## Integrating with AI Tools

*   **Core Requirements:** MCP Server URL, API Key.
*   **Methods:** Python Client Library or Direct API Calls.
*   **Tool Guidance:** Cursor, ChatGPT Actions (using `openapi.yaml`), Copilot (via code context), Ollama/OpenRouter (via intermediary script).
*   **Security Considerations:** Key Management, HTTPS, Least Privilege, Monitoring.

## Contributing

Contributions are welcome! Please see the [Contributing Guidelines](CONTRIBUTING.md) for details on how to get involved, report bugs, suggest features, and submit pull requests.

We also adhere to a [Code of Conduct](CODE_OF_CONDUCT.md).

## Roadmap / Future Enhancements

This list reflects known TODOs and potential future improvements:

*   **Verify & Refine Tufin REST API Logic:**
    *   Double-check all Tufin REST API endpoint paths, methods, request parameters/bodies (especially filtering syntax/capabilities), and response structures used in `src/app/clients/tufin.py` against the official Tufin 25.1 REST documentation.
    *   Ensure Pydantic models in `src/app/models/` accurately parse the verified Tufin REST API responses.
*   **GraphQL API Integration:**
    *   Explore and implement endpoints leveraging the Tufin SecureTrack GraphQL API ([Docs](https://forum.tufin.com/support/kc/GraphQL/R25-1/)) for potentially richer data retrieval (e.g., devices, rules, USP). **(Rule Query Added)**
    *   Allow dynamic selection of fields in GraphQL queries via MCP API.
*   **Bulk Operations:**
    *   Implement endpoints for bulk operations, such as adding/updating multiple devices from a file (e.g., CSV/Excel), **and importing managed devices**.
*   **Production Security:**
    *   Replace `InMemorySecureStore` with a production-ready solution (Database, Vault) and implement secure API key management (generation, revocation).
    *   Implement robust sensitive data masking in `src/app/core/logging_config.py`.
    *   Ensure proper SSL certificate verification (`TUFIN_SSL_VERIFY`) is configured for production deployments.
*   **Testing:**
    *   Add comprehensive unit and integration tests covering client logic, API endpoints, security, and error handling.
*   **Client Library:**
    *   Enhance the Python client library (error handling, response models/parsing).
    *   Enhance the JS/TS client library (error handling, build process).
*   **Tufin Client Refinements:**
    *   Add configurable timeouts and retry logic to the `httpx` client in `src/app/clients/tufin.py`.
*   **Deployment & DX:**
    *   Add further deployment guidance (e.g., Kubernetes manifests, production Gunicorn settings).
    *   Configure FastAPI to serve `openapi.yaml` and interactive docs (Swagger UI/Redoc).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.