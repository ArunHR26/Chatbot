/**
 * API client for Cloud-Native RAG backend
 * Supports both legacy (/api) and versioned (/api/v1) endpoints
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Use API v1 by default, fall back to legacy if needed
const API_VERSION = '/api/v1';
const LEGACY_API = '/api';

export interface Message {
    role: 'user' | 'assistant';
    content: string;
}

export interface IngestResponse {
    success: boolean;
    document_id: string;
    filename: string;
    chunks_created: number;
    message: string;
}

export interface Document {
    id: string;
    name: string;
    created_at: string;
    chunks: number;
}

export interface Stats {
    documents: number;
    chunks: number;
}

export interface DeleteResponse {
    success: boolean;
    document_id: string;
    chunks_deleted: number;
}

/**
 * Upload a PDF document for ingestion
 */
export async function uploadDocument(file: File): Promise<IngestResponse> {
    const formData = new FormData();
    formData.append('file', file);

    // Try v1 first, fall back to legacy
    let response = await fetch(`${API_BASE_URL}${API_VERSION}/ingest`, {
        method: 'POST',
        body: formData,
    });

    if (response.status === 404) {
        // Fall back to legacy endpoint
        response = await fetch(`${API_BASE_URL}${LEGACY_API}/ingest`, {
            method: 'POST',
            body: formData,
        });
    }

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
        throw new Error(error.detail || 'Failed to upload document');
    }

    return response.json();
}

/**
 * Send a chat message and handle streaming response
 */
export async function sendChatMessage(
    message: string,
    history: Message[],
    onContent: (chunk: string) => void,
    onSources: (sources: string[]) => void
): Promise<void> {
    // Try v1 first, fall back to legacy
    let response = await fetch(`${API_BASE_URL}${API_VERSION}/chat`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            message,
            history: history.slice(-10), // Keep last 10 messages
        }),
    });

    if (response.status === 404) {
        response = await fetch(`${API_BASE_URL}${LEGACY_API}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message,
                history: history.slice(-10),
            }),
        });
    }

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Chat failed' }));
        throw new Error(error.detail || 'Failed to get response');
    }

    const reader = response.body?.getReader();
    if (!reader) {
        throw new Error('No response body');
    }

    const decoder = new TextDecoder();

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const text = decoder.decode(value, { stream: true });
        const lines = text.split('\n').filter(line => line.trim());

        for (const line of lines) {
            if (line.startsWith('data: ')) {
                try {
                    const data = JSON.parse(line.slice(6));

                    if (data.type === 'content') {
                        onContent(data.data);
                    } else if (data.type === 'sources') {
                        onSources(data.data);
                    } else if (data.type === 'done') {
                        // Streaming complete
                    }
                } catch {
                    // Ignore parse errors for incomplete chunks
                }
            }
        }
    }
}

/**
 * List all ingested documents
 */
export async function listDocuments(): Promise<Document[]> {
    let response = await fetch(`${API_BASE_URL}${API_VERSION}/documents`);

    if (response.status === 404) {
        response = await fetch(`${API_BASE_URL}${LEGACY_API}/documents`);
    }

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Failed to list documents' }));
        throw new Error(error.detail || 'Failed to list documents');
    }

    const data = await response.json();
    return data.documents;
}

/**
 * Delete a document by ID
 */
export async function deleteDocument(documentId: string): Promise<DeleteResponse> {
    const response = await fetch(`${API_BASE_URL}${API_VERSION}/documents/${documentId}`, {
        method: 'DELETE',
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Failed to delete document' }));
        throw new Error(error.detail || 'Failed to delete document');
    }

    return response.json();
}

/**
 * Get system statistics
 */
export async function getStats(): Promise<Stats> {
    const response = await fetch(`${API_BASE_URL}${API_VERSION}/stats`);

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Failed to get stats' }));
        throw new Error(error.detail || 'Failed to get stats');
    }

    return response.json();
}

/**
 * Health check
 */
export async function healthCheck(): Promise<boolean> {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        return response.ok;
    } catch {
        return false;
    }
}
