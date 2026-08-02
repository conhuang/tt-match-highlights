import { Match, MatchEvent, CreateMatchInput, InitializeResponse, UploadPart, ResumeSession, RenderJob, RenderOptions } from '../types';

const CHUNK_SIZE = 50 * 1024 * 1024; // 50MB
const CONCURRENCY_LIMIT = 3;

export function getAuthHeaders(): Record<string, string> {
    const token = sessionStorage.getItem('beta_id_token') || localStorage.getItem('beta_id_token');
    if (!token) return {};
    return {
        'Authorization': `Bearer ${token}`,
        'X-Beta-Auth-Token': token
    };
}

export async function verifyAuthToken(token: string): Promise<any> {
    const response = await fetch('/api/auth/verify', {
        headers: {
            'Authorization': `Bearer ${token}`,
            'X-Beta-Auth-Token': token
        }
    });
    if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || 'Authentication failed or email not whitelisted.');
    }
    return response.json();
}

export async function fetchMatches(): Promise<Match[]> {
    const response = await fetch('/api/matches', {
        headers: { ...getAuthHeaders() }
    });
    if (!response.ok) {
        throw new Error('Failed to fetch matches.');
    }
    return response.json();
}

export async function fetchMatch(matchId: string): Promise<Match> {
    const response = await fetch(`/api/matches/${matchId}`, {
        headers: { ...getAuthHeaders() }
    });
    if (!response.ok) {
        throw new Error('Failed to load match details.');
    }
    return response.json();
}

export async function createMatch(input: CreateMatchInput): Promise<Match> {
    const response = await fetch('/api/matches', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify(input)
    });
    if (!response.ok) {
        throw new Error('Failed to create match metadata.');
    }
    return response.json();
}

export async function deleteMatch(matchId: string): Promise<void> {
    const response = await fetch(`/api/matches/${matchId}`, {
        method: 'DELETE',
        headers: { ...getAuthHeaders() }
    });
    if (!response.ok) {
        throw new Error('Failed to delete match.');
    }
}

export async function saveMatchEvents(matchId: string, events: MatchEvent[]): Promise<Match> {
    const response = await fetch(`/api/matches/${matchId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ events })
    });
    if (!response.ok) {
        throw new Error('Failed to save match events.');
    }
    return response.json();
}

export async function fetchUploadedParts(matchId: string, uploadId: string, originalFilename: string): Promise<{ PartNumber: number; ETag: string }[]> {
    try {
        const response = await fetch(`/api/matches/${matchId}/upload/parts?upload_id=${uploadId}&original_filename=${encodeURIComponent(originalFilename)}`, {
            headers: { ...getAuthHeaders() }
        });
        if (!response.ok) return [];
        const data = await response.json();
        return data.parts || [];
    } catch {
        return [];
    }
}

export async function abortUpload(matchId: string, uploadId: string, originalFilename: string): Promise<void> {
    try {
        await fetch(`/api/matches/${matchId}/upload/abort?upload_id=${uploadId}&original_filename=${encodeURIComponent(originalFilename)}`, {
            method: 'POST',
            headers: { ...getAuthHeaders() }
        });
    } catch {
        // Ignored
    }
    clearResumeSession(matchId);
}

// LocalStorage Persistence Helpers
export function getStoredResumeSession(): ResumeSession | null {
    for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && key.startsWith('s3_upload_')) {
            try {
                const item = localStorage.getItem(key);
                if (item) {
                    return JSON.parse(item);
                }
            } catch {
                // Ignore parse error
            }
        }
    }
    return null;
}

export function saveResumeSession(session: ResumeSession): void {
    localStorage.setItem(`s3_upload_${session.matchId}`, JSON.stringify(session));
}

export function clearResumeSession(matchId: string): void {
    localStorage.removeItem(`s3_upload_${matchId}`);
}

export async function runUploadQueue(
    matchId: string,
    file: File,
    uploadId: string,
    parts: UploadPart[],
    originalFilename: string,
    onProgress: (percent: number, uploadedMB: number, totalMB: number, statusText: string) => void
): Promise<void> {
    onProgress(0, 0, Math.round(file.size / (1024 * 1024)), 'Checking uploaded parts on server...');

    const uploadedParts = await fetchUploadedParts(matchId, uploadId, originalFilename);
    const uploadedPartNumbers = new Set<number>(uploadedParts.map(p => p.PartNumber));

    const completedParts: { PartNumber: number; ETag: string }[] = [...uploadedParts];
    const partProgress: { [key: number]: number } = {};

    // Populate partProgress for already uploaded parts
    for (const p of parts) {
        if (uploadedPartNumbers.has(p.PartNumber)) {
            const start = (p.PartNumber - 1) * CHUNK_SIZE;
            const end = Math.min(start + CHUNK_SIZE, file.size);
            partProgress[p.PartNumber] = end - start;
        }
    }

    const remainingParts = parts.filter(p => !uploadedPartNumbers.has(p.PartNumber));

    const updateProgress = () => {
        let totalUploaded = 0;
        for (const p in partProgress) {
            totalUploaded += partProgress[p];
        }
        const percent = Math.min((totalUploaded / file.size) * 100, 99.9);
        const uploadedMB = Math.round(totalUploaded / (1024 * 1024));
        const totalMB = Math.round(file.size / (1024 * 1024));
        onProgress(percent, uploadedMB, totalMB, `Uploading: ${percent.toFixed(1)}%`);
    };

    updateProgress();

    if (remainingParts.length === 0) {
        onProgress(100, Math.round(file.size / (1024 * 1024)), Math.round(file.size / (1024 * 1024)), 'Finalizing video assembly...');
        await finalizeUpload(matchId, uploadId, completedParts, originalFilename);
        return;
    }

    let uploadAborted = false;

    const uploadChunk = (part: UploadPart): Promise<void> => {
        return new Promise((resolve, reject) => {
            const start = (part.PartNumber - 1) * CHUNK_SIZE;
            const end = Math.min(start + CHUNK_SIZE, file.size);
            const blob = file.slice(start, end);

            const xhr = new XMLHttpRequest();
            xhr.open('PUT', part.UploadUrl);

            xhr.upload.addEventListener('progress', (e: ProgressEvent) => {
                if (e.lengthComputable) {
                    partProgress[part.PartNumber] = e.loaded;
                    updateProgress();
                }
            });

            xhr.onload = () => {
                if (xhr.status === 200) {
                    let etag = xhr.getResponseHeader('ETag');
                    if (!etag && xhr.responseText) {
                        try {
                            const res = JSON.parse(xhr.responseText);
                            etag = res.ETag;
                        } catch {
                            // Ignore json error
                        }
                    }

                    if (etag) {
                        completedParts.push({ PartNumber: part.PartNumber, ETag: etag });
                        partProgress[part.PartNumber] = end - start;
                        updateProgress();
                        resolve();
                    } else {
                        reject(new Error(`No ETag header returned for Part #${part.PartNumber}`));
                    }
                } else {
                    reject(new Error(`Failed to upload Part #${part.PartNumber}. Status: ${xhr.status}`));
                }
            };

            xhr.onerror = () => reject(new Error(`Network error during Part #${part.PartNumber}`));
            xhr.send(blob);
        });
    };

    const queue = [...remainingParts];
    const workers: Promise<void>[] = [];

    const startWorker = async (): Promise<void> => {
        while (queue.length > 0 && !uploadAborted) {
            const part = queue.shift();
            if (part) {
                try {
                    await uploadChunk(part);
                } catch (err) {
                    uploadAborted = true;
                    throw err;
                }
            }
        }
    };

    for (let i = 0; i < Math.min(CONCURRENCY_LIMIT, remainingParts.length); i++) {
        workers.push(startWorker());
    }

    try {
        await Promise.all(workers);
    } catch (err) {
        onProgress(0, 0, Math.round(file.size / (1024 * 1024)), 'Connection lost. Retrying automatically...');
        throw err;
    }

    await finalizeUpload(matchId, uploadId, completedParts, originalFilename);
}

async function finalizeUpload(
    matchId: string,
    uploadId: string,
    completedParts: { PartNumber: number; ETag: string }[],
    originalFilename: string
): Promise<void> {
    const completeResponse = await fetch(`/api/matches/${matchId}/upload/complete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({
            upload_id: uploadId,
            parts: completedParts,
            original_filename: originalFilename
        })
    });

    if (!completeResponse.ok) {
        let errorMsg = 'Failed to assemble the video on server.';
        try {
            const errData = await completeResponse.json();
            if (errData && errData.detail) errorMsg = errData.detail;
        } catch {
            // Ignore
        }
        throw new Error(errorMsg);
    }

    clearResumeSession(matchId);
}

export async function uploadVideoMultipart(
    matchId: string,
    file: File,
    matchName: string,
    player1: string,
    player2: string,
    onProgress: (percent: number, uploadedMB: number, totalMB: number, statusText: string) => void
): Promise<void> {
    onProgress(0, 0, Math.round(file.size / (1024 * 1024)), 'Initializing upload...');

    const initResponse = await fetch(`/api/matches/${matchId}/upload/initialize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({
            filename: file.name,
            file_size: file.size
        })
    });

    if (!initResponse.ok) {
        throw new Error('Failed to initialize multipart upload.');
    }

    const { upload_id, parts, original_filename }: InitializeResponse = await initResponse.json();

    const session: ResumeSession = {
        matchId,
        uploadId: upload_id,
        originalFilename: original_filename,
        fileSize: file.size,
        matchName,
        player1,
        player2,
        parts
    };

    saveResumeSession(session);

    await runUploadQueue(matchId, file, upload_id, parts, original_filename, onProgress);
}

export async function createRenderJob(
    matchId: string,
    type: 'full_match' | 'highlights',
    label?: string,
    options?: Partial<RenderOptions>
): Promise<RenderJob> {
    const response = await fetch(`/api/matches/${matchId}/renders`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({
            type,
            label,
            options: {
                highlights_only: type === 'highlights',
                include_scoreboard: true,
                include_game_cards: true,
                cpu_mode: true,
                ...options
            }
        })
    });
    if (!response.ok) {
        let errText = 'Failed to initiate video rendering.';
        try {
            const errData = await response.json();
            if (errData && errData.detail) errText = errData.detail;
        } catch {
            // Ignore
        }
        throw new Error(errText);
    }
    return response.json();
}

export async function fetchMatchRenders(matchId: string): Promise<RenderJob[]> {
    const response = await fetch(`/api/matches/${matchId}/renders`, {
        headers: { ...getAuthHeaders() }
    });
    if (!response.ok) {
        throw new Error('Failed to fetch render jobs.');
    }
    return response.json();
}

export async function fetchRenderStatus(matchId: string, renderId: string): Promise<RenderJob> {
    const response = await fetch(`/api/matches/${matchId}/renders/${renderId}/status`, {
        headers: { ...getAuthHeaders() }
    });
    if (!response.ok) {
        throw new Error('Failed to fetch render status.');
    }
    return response.json();
}

export async function deleteRenderJob(matchId: string, renderId: string): Promise<void> {
    const response = await fetch(`/api/matches/${matchId}/renders/${renderId}`, {
        method: 'DELETE',
        headers: { ...getAuthHeaders() }
    });
    if (!response.ok) {
        throw new Error('Failed to delete render job.');
    }
}

export async function cancelRenderJob(matchId: string, renderId: string): Promise<void> {
    const response = await fetch(`/api/matches/${matchId}/renders/${renderId}/cancel`, {
        method: 'POST',
        headers: { ...getAuthHeaders() }
    });
    if (!response.ok) {
        throw new Error('Failed to cancel render job.');
    }
}
