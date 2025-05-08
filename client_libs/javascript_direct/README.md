# Tufin Direct API Client (JavaScript/TypeScript)

This is a **simple** client library for interacting **directly** with the Tufin SecureTrack and SecureChange REST APIs using basic authentication.

**Note:** This client bypasses the Tufin MCP Server and connects straight to your Tufin instances. It does *not* use the API Key or RBAC features provided by the MCP server.

## Installation

```bash
# From your JS/TS project directory
npm install <path_to_tufin-mcp/client_libs/javascript_direct>
# Or link for local development:
# cd client_libs/javascript_direct && npm link && cd ../../ && npm link tufin-direct-client-js

# Make sure to build first if installing from source:
# cd client_libs/javascript_direct && npm run build && cd ../..
```

## Configuration

When creating the client, you need to provide:

*   `secureTrackUrl`: The base URL for your SecureTrack instance (e.g., `https://your-securetrack`).
*   `secureChangeUrl`: The base URL for your SecureChange instance (e.g., `https://your-securechange`).
*   `username`: A Tufin username with appropriate API permissions.
*   `password`: The password for the Tufin user.
*   `timeout` (Optional): Request timeout in milliseconds (default: 30000).
*   `rejectUnauthorized` (Optional): Set to `false` to bypass SSL certificate verification (e.g., for self-signed certs). **Warning:** This is insecure and should only be used in trusted environments.

**Security Warning:** Store Tufin credentials securely (e.g., environment variables, secrets manager). Do not hardcode them in your source code.

## Usage Example (TypeScript)

```typescript
import { TufinDirectClient, TufinDirectClientError } from 'tufin-direct-client-js'; // Adjust import

async function main() {
    const options = {
        secureTrackUrl: process.env.TUFIN_ST_URL || 'https://your-securetrack',
        secureChangeUrl: process.env.TUFIN_SC_URL || 'https://your-securechange',
        username: process.env.TUFIN_USERNAME || 'your-tufin-user',
        password: process.env.TUFIN_PASSWORD || 'your-tufin-password',
        rejectUnauthorized: process.env.TUFIN_SSL_VERIFY === 'false' ? false : true,
    };

    const client = new TufinDirectClient(options);

    try {
        console.log("Listing devices...");
        const devicesResponse = await client.listDevices({ status: 'started' }); // Example filter
        // Raw Tufin response - structure needs checking against docs
        console.log(`Found ${devicesResponse?.total || 'unknown'} total devices.`);
        if (devicesResponse?.device?.length > 0) {
            console.log(`First device: ${devicesResponse.device[0].name}`);
        }

        console.log("\nRunning topology path query...");
        const pathParams = { src: '1.1.1.1', dst: '8.8.8.8', service: 'tcp:443' };
        const pathResponse = await client.getTopologyPath(pathParams);
        console.log(`Topology Path Allowed: ${pathResponse?.traffic_allowed}`);

        // Add calls to other methods like listTickets, addDevices etc.
        // Remember to construct the correct request body for addDevices and createTicket

    } catch (error) {
        if (error instanceof TufinDirectClientError) {
            console.error("Tufin Direct Client Error:", error.message);
            console.error("  Status:", error.status);
            console.error("  Data:", error.data);
        } else {
            console.error("Unexpected Error:", error);
        }
    }
}

main();
```

## Available Methods

*   `listDevices(params?)`
*   `getDevice(deviceId)`
*   `addDevices(devices[])`
*   `importManagedDevices(importData)`
*   `getTopologyPath(params)`
*   `getTopologyPathImage(params)` (returns ArrayBuffer)
*   `queryRulesGraphQL(filterData)`
*   `listTickets(params?)`
*   `createTicket(ticketData)`
*   `getTicket(ticketId)`
*   `updateTicket(ticketId, ticketData)`

**Note:** Methods currently return the raw JSON response (`any`) or binary data from the Tufin API. You will need to refer to the Tufin API documentation for the exact structure of the responses.

## Integrating with AI Tools

Using this **direct client library** with AI tools differs from using the MCP Server API. This library connects directly to Tufin using username/password authentication, bypassing the MCP Server's API Key and RBAC features.

### Cursor

As a developer using Cursor, you can directly import and use this client library in your Node.js/TypeScript projects.

1.  **Installation:** Make sure the client is installed or linked in your project (see Installation section).
2.  **Import & Use:** Import the `TufinDirectClient` and use it in your code. **Crucially, manage Tufin credentials securely using environment variables or a secrets manager.**

```typescript
// Example within your project code (e.g., a script run via node)
import { TufinDirectClient, TufinDirectClientError } from 'tufin-direct-client-js';

async function runDirectTufinTask() {
    const options = {
        secureTrackUrl: process.env.TUFIN_ST_URL || 'https://your-securetrack', // Load from env
        secureChangeUrl: process.env.TUFIN_SC_URL || 'https://your-securechange', // Load from env
        username: process.env.TUFIN_USERNAME || 'your-tufin-user', // Load from env
        password: process.env.TUFIN_PASSWORD || 'your-tufin-password', // Load from env
        rejectUnauthorized: process.env.TUFIN_SSL_VERIFY === 'false' ? false : true,
    };

    const client = new TufinDirectClient(options);

    try {
        // Ask Cursor to help generate calls based on your needs
        console.log("Getting device details directly...");
        const device = await client.getDevice("some-device-id"); 
        console.log("Device:", device);

    } catch (error) {
        // Handle errors
        console.error("Error calling Tufin directly:", error);
    }
}

runDirectTufinTask();
```

*   You can ask Cursor to help write the specific client calls (`listDevices`, `createTicket`, etc.) based on the methods provided by the library.
*   Keep the `index.ts` file of this library open in Cursor for better context.

### ChatGPT / Claude / Other LLMs

Large Language Models like ChatGPT and Claude **cannot directly execute local JavaScript code or libraries** like this one within their standard interfaces (e.g., chat UI, basic API calls).

To enable interaction, you need an intermediary layer:

1.  **Wrapper API Service (Recommended for Actions/Tool Use):**
    *   Build a separate, simple web server (e.g., using Node.js/Express, Cloud Functions, etc.).
    *   This new server *uses* the `TufinDirectClient` library internally.
    *   The server exposes its own simple REST or GraphQL API endpoints (e.g., `/list-tufin-devices`, `/create-tufin-ticket`).
    *   **Crucially:** This wrapper server securely stores and uses the necessary Tufin username/password credentials to initialize `TufinDirectClient`.
    *   Define an OpenAPI specification for *this wrapper service*.
    *   Configure the LLM (e.g., ChatGPT Action, Claude tool use) to call *your wrapper service's API*, potentially securing the wrapper service itself with an API key or other mechanism suitable for the LLM.
    *   **Pros:** Enables direct interaction from the LLM chat interface.
    *   **Cons:** Requires building and hosting an additional service; this service needs secure credential management for Tufin.

2.  **Code Generation:**
    *   Ask the LLM (ChatGPT, Claude, Cursor) to *write* the Node.js/TypeScript code required to perform a specific task *using the `TufinDirectClient` library*.
    *   Provide the LLM with the library's code (`index.ts`) or the Available Methods section from this README as context.
    *   You (the developer) then take the generated code snippet, integrate it into your local project, ensure secure credential handling (e.g., via environment variables), and execute it yourself.
    *   **Pros:** No extra service needed.
    *   **Cons:** Requires a developer to run the generated code; not direct interaction from the chat interface.

**In summary:** For direct LLM interaction (like ChatGPT Actions), you generally need a server-side API. This *direct* client library is best suited for use within your own scripts and applications or via code generation workflows facilitated by tools like Cursor. 