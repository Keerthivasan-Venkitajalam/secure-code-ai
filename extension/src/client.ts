import axios, { AxiosInstance } from 'axios';

export interface AnalyzeRequest {
    code: string;
    file_path: string;
    max_iterations?: number;
}

export interface Vulnerability {
    location: string;
    vuln_type: string;
    severity: string;
    description: string;
    cwe_id?: string;
    confidence?: number;
}

export interface Patch {
    code: string;
    diff: string;
    verified: boolean;
}

export interface AnalyzeResponse {
    analysis_id: string;
    vulnerabilities: Vulnerability[];
    patches: Patch[];
    execution_time: number;
    errors: string[];
    logs: string[];
    workflow_complete: boolean;
}

export class SecureCodeAIClient {
    private client: AxiosInstance;
    private endpoint: string;

    constructor(endpoint: string) {
        this.endpoint = endpoint;
        this.client = axios.create({
            baseURL: endpoint,
            timeout: 60000, // 60 second timeout
            headers: {
                'Content-Type': 'application/json'
            }
        });
    }

    updateEndpoint(endpoint: string) {
        this.endpoint = endpoint;
        this.client = axios.create({
            baseURL: endpoint,
            timeout: 60000,
            headers: {
                'Content-Type': 'application/json'
            }
        });
    }

    async checkHealth(): Promise<boolean> {
        try {
            const response = await this.client.get('/health');
            return response.data.status === 'healthy';
        } catch (error) {
            console.error('Health check failed:', error);
            return false;
        }
    }

    async analyzeCode(code: string, filePath: string, maxIterations: number = 3): Promise<AnalyzeResponse> {
        const request: AnalyzeRequest = {
            code,
            file_path: filePath,
            max_iterations: maxIterations
        };

        try {
            const response = await this.client.post<AnalyzeResponse>('/analyze', request);
            return response.data;
        } catch (error) {
            if (axios.isAxiosError(error)) {
                throw new Error(`API Error: ${error.response?.data?.detail || error.message}`);
            }
            throw error;
        }
    }
}
