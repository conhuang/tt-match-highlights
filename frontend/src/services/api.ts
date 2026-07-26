import { Match, MatchEvent, CreateMatchInput, InitializeResponse, UploadPart } from '../types';

const CHUNK_SIZE = 50 * 1024 * 1024; // 50MB
const CONCURRENCY_LIMIT = 3;

export async function fetchMatches(): Promise<Match[]> {
    const response = await fetch('/api/matches');
    if (!response.ok) {
        throw new Error('Failed to fetch matches.');
    }
    return response.json();
}

export async function fetchMatch(matchId: string): Promise<Match> {
    const response = await fetch(`/api/matches/${matchId}`);
    if (!response.ok) {
        throw new Error('Failed to load match details.');
    }
    return response.json();
}

export async function createMatch(input: CreateMatchInput): Promise<Match> {
    const response = await fetch('/api/matches', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(input)
    });
    if (!response.ok) {
        throw new Error('Failed to create match metadata.');
    }
    return response.json();
}

export async function deleteMatch(matchId: string): Promise<void> {
    const response = await fetch(`/api/matches/${matchId}`, {
        method: 'DELETE'
    });
    if (!response.ok) {
        throw new Error('Failed to delete match.');
    }
}

export async function saveMatchEvents(matchId: string, events: MatchEvent[]): Promise<Match> {
    const response = await fetch(`/api/matches/${matchId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ events })
    });
    if (!response.ok) {
        throw new Error('Failed to save match events.');
    }
    return response.json();
}

export async function uploadVideoMultipart(
    matchId: string,
    file: File,
    onProgress: (percent: number, uploadedMB: number, totalMB: number, statusText: string) => void
): Promise<void> {
    onProgress(0, 0, Math.round(file.size / (1024 * 1024)), 'Initializing upload...');

    // 1. Initialize Multipart Upload
    const initResponse = await fetch(`/api/matches/${matchId}/upload/initialize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            filename: file.name,
            file_size: file.size
        })
    });

    if (!initResponse.ok) {
        throw new Error('Failed to initialize multipart upload.');
    }

    const { upload_id, parts, original_filename }: InitializeResponse = await initResponse.json();

    const completedParts: { PartNumber: number; ETag: string }[] = [];
    const partProgress: { [key: number]: number } = {};

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
                        } catch (err) {
                            // ignore json parse error
                        }
                    }

                    if (etag) {
                        completedParts.push({
                            PartNumber: part.PartNumber,
                            ETag: etag
                        });
                        partProgress[part.PartNumber] = end - start;
                        updateProgress();
                        resolve();
                    } else {
                        reject(new Error(`No ETag returned for part ${part.PartNumber}`));
                    }
                } else {
                    reject(new Error(`Part upload failed with status ${xhr.status}`));
                }
            };

            xhr.onerror = () => reject(new Error(`Network error during part ${part.PartNumber} upload`));
            xhr.send(blob);
        });
    };

    const queue = [...parts];
    const workers: Promise<void>[] = [];

    const startWorker = async () => {
        while (queue.length > 0) {
            const part = queue.shift();
            if (part) {
                try {
                    await uploadChunk(part);
                } catch (err) {
                    await fetch(`/api/matches/${matchId}/upload/abort?upload_id=${upload_id}&original_filename=${encodeURIComponent(original_filename)}`, {
                        method: 'POST'
                    }).catch(() => {});
                    throw err;
                }
            }
        }
    };

    for (let i = 0; i < Math.min(CONCURRENCY_LIMIT, parts.length); i++) {
        workers.push(startWorker());
    }

    await Promise.all(workers);

    onProgress(100, Math.round(file.size / (1024 * 1024)), Math.round(file.size / (1024 * 1024)), 'Finalizing upload...');

    const completeResponse = await fetch(`/api/matches/${matchId}/upload/complete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            upload_id,
            parts: completedParts,
            original_filename
        })
    });

    if (!completeResponse.ok) {
        throw new Error('Failed to finalize video assembly on server.');
    }
}
