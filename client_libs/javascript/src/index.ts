import axios, { AxiosInstance, AxiosRequestConfig, AxiosError } from 'axios';

// Define basic interfaces for expected responses (align with Python MCP models)
// These are simplified, ideally generate from OpenAPI spec or share types
interface HealthResponse {
    status: 'ok';
}

interface TicketResponse {
    id: number;
    subject?: string | null;
    description?: string | null;
    priority?: string | null;
    status: string;
    workflow_name?: string | null;
    // Add other fields exposed by MCP API
}

interface TicketListResponse {
    tickets: TicketResponse[];
    total: number;
    next_link?: string | null;
    previous_link?: string | null;
}

interface DeviceResponse {
    id: string;
    name?: string | null;
    vendor?: string | null;
    model?: string | null;
    version?: string | null; // maps to OS_Version
    ip_address?: string | null; // maps to ip
    domain_name?: string | null;
    status?: string | null;
    // Add other fields exposed by MCP API
}

interface DeviceListResponse {
    devices: DeviceResponse[];
    total: number;
    count: number;
}

interface TopologyPathResponse {
    traffic_allowed: boolean;
    is_fully_routed: boolean;
    path_device_names?: string[] | null;
}

// Custom Error class
export class TufinMCPClientError extends Error {
    status?: number;
    data?: any;

    constructor(message: string, status?: number, data?: any) {
        super(message);
        this.name = 'TufinMCPClientError';
        this.status = status;
        this.data = data;
    }
}

export class TufinMCPClient {
    private client: AxiosInstance;

    constructor(baseURL: string, apiKey: string, timeout: number = 30000) {
        this.client = axios.create({
            baseURL: baseURL,
            timeout: timeout,
            headers: {
                'X-API-Key': apiKey,
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        });
    }

    private async _request<T>(config: AxiosRequestConfig): Promise<T> {
        try {
            const response = await this.client.request<T>(config);
            return response.data;
        } catch (error) {
            if (axios.isAxiosError(error)) {
                const axiosError = error as AxiosError;
                const status = axiosError.response?.status;
                const data = axiosError.response?.data;
                const message = `Request failed with status ${status}: ${config.method?.toUpperCase()} ${config.url}`;
                console.error(message, data); // Log error details
                throw new TufinMCPClientError(message, status, data);
            } else {
                console.error('An unexpected error occurred', error);
                throw new TufinMCPClientError('An unexpected error occurred');
            }
        }
    }

    // --- Health ---
    async getHealth(): Promise<HealthResponse> {
        return this._request<HealthResponse>({ method: 'GET', url: '/health' });
    }

    // --- SecureChange Tickets ---
    async listTickets(params?: Record<string, any>): Promise<TicketListResponse> {
        return this._request<TicketListResponse>({ method: 'GET', url: '/api/v1/tickets', params });
    }

    async createTicket(ticketData: Record<string, any>): Promise<TicketResponse> {
        // Requires workflow_name and details object within ticketData
        return this._request<TicketResponse>({ method: 'POST', url: '/api/v1/tickets', data: ticketData });
    }

    async getTicket(ticketId: number): Promise<TicketResponse> {
        return this._request<TicketResponse>({ method: 'GET', url: `/api/v1/tickets/${ticketId}` });
    }

    async updateTicket(ticketId: number, ticketData: Record<string, any>): Promise<TicketResponse> {
        return this._request<TicketResponse>({ method: 'PUT', url: `/api/v1/tickets/${ticketId}`, data: ticketData });
    }

    // --- SecureTrack Devices ---
    async listDevices(params?: Record<string, any>): Promise<DeviceListResponse> {
        return this._request<DeviceListResponse>({ method: 'GET', url: '/api/v1/devices', params });
    }

    async getDevice(deviceId: string): Promise<DeviceResponse> {
        return this._request<DeviceResponse>({ method: 'GET', url: `/api/v1/devices/${deviceId}` });
    }

    // --- SecureTrack Topology ---
    async getTopologyPath(params: { src: string; dst: string; service: string }): Promise<TopologyPathResponse> {
        return this._request<TopologyPathResponse>({ method: 'GET', url: '/api/v1/topology/path', params });
    }
    
    async getTopologyPathImage(params: { src: string; dst: string; service: string }): Promise<Blob> {
        // Gets the topology path image as a Blob.
        try {
            const response = await this.client.request<Blob>({
                method: 'GET', 
                url: '/api/v1/topology/path/image', 
                params: params,
                responseType: 'blob'
            });
            return response.data;
        } catch (error) {
            if (axios.isAxiosError(error)) {
                const axiosError = error as AxiosError;
                const status = axiosError.response?.status;
                const data = axiosError.response?.data;
                const message = `Request failed with status ${status}: GET /api/v1/topology/path/image`;
                console.error(message, data);
                throw new TufinMCPClientError(message, status, data);
            } else {
                console.error('An unexpected error occurred getting topology image', error);
                throw new TufinMCPClientError('An unexpected error occurred getting topology image');
            }
        }
    }
} 