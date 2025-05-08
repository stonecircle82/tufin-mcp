import axios, { AxiosInstance, AxiosRequestConfig, AxiosError } from 'axios';
import https from 'https'; // Needed for potential SSL verification bypass

// Custom Error class
export class TufinDirectClientError extends Error {
    status?: number;
    data?: any;
    originalError?: Error;

    constructor(message: string, status?: number, data?: any, originalError?: Error) {
        super(message);
        this.name = 'TufinDirectClientError';
        this.status = status;
        this.data = data;
        this.originalError = originalError;
    }
}

// Interface for constructor options
interface TufinDirectClientOptions {
    secureTrackUrl: string;
    secureChangeUrl: string;
    username: string;
    password: string;
    timeout?: number; // milliseconds
    rejectUnauthorized?: boolean; // For self-signed certs (use with caution!)
}

export class TufinDirectClient {
    private stClient: AxiosInstance;
    private scClient: AxiosInstance;
    private basicAuthHeader: string;

    constructor(options: TufinDirectClientOptions) {
        const { 
            secureTrackUrl, 
            secureChangeUrl, 
            username, 
            password, 
            timeout = 30000, 
            rejectUnauthorized = true // Default to secure
        } = options;

        // Create Basic Auth header value
        const credentials = Buffer.from(`${username}:${password}`).toString('base64');
        this.basicAuthHeader = `Basic ${credentials}`;
        
        // Create HTTPS agent for potentially bypassing SSL verification
        const httpsAgent = new https.Agent({
            rejectUnauthorized: rejectUnauthorized,
        });

        // Create separate Axios instances for SecureTrack and SecureChange
        this.stClient = axios.create({
            baseURL: secureTrackUrl.replace(/\/$/, '') + '/securetrack/api', // Append base path
            timeout: timeout,
            headers: {
                'Authorization': this.basicAuthHeader,
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            httpsAgent: httpsAgent
        });

        this.scClient = axios.create({
            baseURL: secureChangeUrl.replace(/\/$/, '') + '/securechangeworkflow/api/securechange', // Append base path
            timeout: timeout,
            headers: {
                'Authorization': this.basicAuthHeader,
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            httpsAgent: httpsAgent
        });
    }

    // Generic request handler
    private async _request<T>(client: AxiosInstance, config: AxiosRequestConfig, expectStatus: number = 200): Promise<T> {
        try {
            // console.debug(`Tufin Direct Request: ${config.method} ${client.defaults.baseURL}${config.url}`, config.params, config.data);
            const response = await client.request<T>(config);
            
            // Handle non-standard success codes like 202 for bulk add
            if (response.status !== expectStatus && expectStatus === 202 && response.status === 202) {
                 console.info(`Request successful with status ${response.status} (expected ${expectStatus})`);
                 return {} as T; // Return empty object or specific type for 202
            }
            // Check if status matches expected explicitly for non-200 success codes if needed
            // else if (response.status !== expectStatus) { ... throw ... }
            
            return response.data;
        } catch (error) {
            let message = 'Tufin API request failed';
            let status: number | undefined = undefined;
            let responseData: any = undefined;

            if (axios.isAxiosError(error)) {
                const axiosError = error as AxiosError;
                status = axiosError.response?.status;
                responseData = axiosError.response?.data;
                message = `Request failed with status ${status}: ${config.method?.toUpperCase()} ${client.defaults.baseURL}${config.url}`;
                console.error(message, responseData); 
            } else if (error instanceof Error) {
                message = `An unexpected error occurred: ${error.message}`;
                console.error(message, error);
            } else {
                 console.error('An unexpected non-error object was thrown', error);
            }
            throw new TufinDirectClientError(message, status, responseData, error instanceof Error ? error : undefined);
        }
    }

    // --- SecureTrack Devices --- 
    async listDevices(params?: Record<string, any>): Promise<any> { // Returns raw Tufin response
        return this._request<any>(this.stClient, { method: 'GET', url: '/devices', params });
    }

    async getDevice(deviceId: string): Promise<any> {
        return this._request<any>(this.stClient, { method: 'GET', url: `/devices/${deviceId}` });
    }

    async addDevices(devices: Array<Record<string, any>>): Promise<void> {
        // Tufin uses POST /devices/bulk/ for this
        const requestBody = { devices }; 
        // Expect 202 Accepted
        await this._request<void>(this.stClient, { method: 'POST', url: '/devices/bulk/', data: requestBody }, 202);
    }

    async importManagedDevices(importData: { devices: Array<Record<string, any>> }): Promise<void> {
        // Imports managed devices into existing parent devices.
        // Expect 202 Accepted
        await this._request<void>(this.stClient, { method: 'POST', url: '/devices/bulk/import', data: importData }, 202);
    }

    // --- SecureTrack Topology --- 
    async getTopologyPath(params: { src: string; dst: string; service: string }): Promise<any> {
        return this._request<any>(this.stClient, { method: 'GET', url: '/topology/path', params });
    }

    async getTopologyPathImage(params: { src: string; dst: string; service: string }): Promise<ArrayBuffer> { // Use ArrayBuffer for Node.js
        // Requires specific responseType
        const config: AxiosRequestConfig = { 
            method: 'GET', 
            url: '/topology/path_image', 
            params,
            responseType: 'arraybuffer' 
        };
        return this._request<ArrayBuffer>(this.stClient, config);
    }
    
    // --- GraphQL ---
    async queryRulesGraphQL(filterData: { tql_filter?: string | null }): Promise<any> { // Keep response as any for now
        return this._request<any>({ method: 'POST', url: '/api/v1/graphql/rules', data: filterData });
    }
    
    // --- SecureChange Tickets ---
    async listTickets(params?: Record<string, any>): Promise<any> {
        return this._request<any>(this.scClient, { method: 'GET', url: '/tickets', params });
    }

    async createTicket(ticketData: Record<string, any>): Promise<any> {
        // Requires constructing the { "ticket": { ... } } structure
        // Client should pass this structure in ticketData for simplicity here
        return this._request<any>(this.scClient, { method: 'POST', url: '/tickets', data: ticketData });
    }

    async getTicket(ticketId: number): Promise<any> {
        return this._request<any>(this.scClient, { method: 'GET', url: `/tickets/${ticketId}` });
    }

    async updateTicket(ticketId: number, ticketData: Record<string, any>): Promise<any> {
        return this._request<any>(this.scClient, { method: 'PUT', url: `/tickets/${ticketId}`, data: ticketData });
    }

    // Add getTicketHistory later if needed
} 