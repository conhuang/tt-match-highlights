interface Match {
    id: string;
    owner_username: string;
    name: string;
    player1: string;
    player2: string;
    created_at: string;
    video_filename?: string | null;
    original_filename?: string | null;
    rendered_video_filename?: string | null;
    events: any[];
}

interface UploadPart {
    PartNumber: number;
    UploadUrl: string;
}

interface InitializeResponse {
    upload_id: string;
    parts: UploadPart[];
    unique_filename: string;
    original_filename: string;
}

// Elements
const matchForm = document.getElementById("match-form") as HTMLFormElement;
const matchNameInput = document.getElementById("match-name") as HTMLInputElement;
const player1Input = document.getElementById("player1") as HTMLInputElement;
const player2Input = document.getElementById("player2") as HTMLInputElement;
const dropZone = document.getElementById("drop-zone") as HTMLDivElement;
const fileInput = document.getElementById("file-input") as HTMLInputElement;
const progressContainer = document.getElementById("progress-container") as HTMLDivElement;
const progressFill = document.getElementById("progress-fill") as HTMLDivElement;
const progressLabel = document.getElementById("progress-label") as HTMLSpanElement;
const submitBtn = document.getElementById("submit-btn") as HTMLButtonElement;
const matchesList = document.getElementById("matches-list") as HTMLDivElement;

let selectedFile: File | null = null;
const CHUNK_SIZE = 50 * 1024 * 1024; // 50MB Chunks (Standard S3 minimum is 5MB)
const CONCURRENCY_LIMIT = 3;         // Max parallel chunk uploads

// Initial Load
document.addEventListener("DOMContentLoaded", () => {
    loadMatches();
});

// Drag & Drop Handlers
dropZone.addEventListener("click", () => fileInput.click());

dropZone.addEventListener("dragover", (e: DragEvent) => {
    e.preventDefault();
    dropZone.classList.add("dragover");
});

dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("dragover");
});

dropZone.addEventListener("drop", (e: DragEvent) => {
    e.preventDefault();
    dropZone.classList.remove("dragover");
    
    if (e.dataTransfer && e.dataTransfer.files.length > 0) {
        handleFileSelect(e.dataTransfer.files[0]);
    }
});

fileInput.addEventListener("change", () => {
    if (fileInput.files && fileInput.files.length > 0) {
        handleFileSelect(fileInput.files[0]);
    }
});

function handleFileSelect(file: File): void {
    if (file.type !== "video/mp4" && file.type !== "video/quicktime") {
        alert("Please select an MP4 or MOV video file.");
        return;
    }
    
    selectedFile = file;
    dropZone.classList.add("file-selected");
    const dropText = dropZone.querySelector(".drop-text") as HTMLParagraphElement;
    if (dropText) {
        dropText.textContent = `Selected: ${file.name} (${(file.size / (1024 * 1024)).toFixed(1)} MB)`;
    }
    validateForm();
}

// Form Validation
const inputs = [matchNameInput, player1Input, player2Input];
inputs.forEach(input => {
    if (input) {
        input.addEventListener("input", validateForm);
    }
});

function validateForm(): void {
    const isFormValid = matchNameInput.value.trim() !== "" &&
                        player1Input.value.trim() !== "" &&
                        player2Input.value.trim() !== "";
    
    submitBtn.disabled = !(isFormValid && selectedFile !== null);
}

// Create Match & Upload Handler
matchForm.addEventListener("submit", async (e: Event) => {
    e.preventDefault();
    
    if (!selectedFile) return;

    submitBtn.disabled = true;
    
    try {
        // Step 1: Create Match record in DB
        const matchData = {
            name: matchNameInput.value.trim(),
            player1: player1Input.value.trim(),
            player2: player2Input.value.trim()
        };

        const createResponse = await fetch("/api/matches", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(matchData)
        });

        if (!createResponse.ok) {
            throw new Error("Failed to create match metadata.");
        }

        const match: Match = await createResponse.json();

        // Step 2: Begin S3 Direct Multipart Upload sequence
        await uploadVideoMultipart(match.id, selectedFile);

    } catch (error: any) {
        alert(error.message || "An error occurred during match creation.");
        submitBtn.disabled = false;
    }
});

// Multipart Uploader with Parallel Workers
async function uploadVideoMultipart(matchId: string, file: File): Promise<void> {
    progressContainer.style.display = "flex";
    progressLabel.textContent = "Initializing upload...";

    // 1. Initialize Multipart Upload
    const initResponse = await fetch(`/api/matches/${matchId}/upload/initialize`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            filename: file.name,
            file_size: file.size
        })
    });

    if (!initResponse.ok) {
        throw new Error("Failed to initialize multipart upload.");
    }

    const { upload_id, parts, original_filename }: InitializeResponse = await initResponse.json();
    
    const completedParts: { PartNumber: number; ETag: string }[] = [];
    let uploadedBytesTotal = 0;
    const partProgress: { [key: number]: number } = {};

    // Progress updates
    const updateOverallProgress = () => {
        let totalUploaded = 0;
        for (const partNum in partProgress) {
            totalUploaded += partProgress[partNum];
        }
        const percent = Math.min((totalUploaded / file.size) * 100, 99.9);
        progressFill.style.width = `${percent}%`;
        progressLabel.textContent = `Uploading: ${percent.toFixed(1)}% (${(totalUploaded / (1024 * 1024)).toFixed(0)}MB / ${(file.size / (1024 * 1024)).toFixed(0)}MB)`;
    };

    // Helper to upload a single part
    const uploadChunk = (part: UploadPart): Promise<void> => {
        return new Promise((resolve, reject) => {
            const start = (part.PartNumber - 1) * CHUNK_SIZE;
            const end = Math.min(start + CHUNK_SIZE, file.size);
            const blob = file.slice(start, end);

            const xhr = new XMLHttpRequest();
            
            // Check if uploading to local mock endpoint or direct to S3
            // In local dev, we use PUT, in S3 we use PUT as well
            const method = part.UploadUrl.startsWith("/") ? "PUT" : "PUT";
            xhr.open(method, part.UploadUrl);

            // Do not send Content-Type header when uploading direct to S3 (let it default)
            // But if it's the local mock uploader, we don't need boundary formatting either.

            xhr.upload.addEventListener("progress", (e: ProgressEvent) => {
                if (e.lengthComputable) {
                    partProgress[part.PartNumber] = e.loaded;
                    updateOverallProgress();
                }
            });

            xhr.onload = () => {
                if (xhr.status === 200) {
                    // Extract ETag. For S3, it is returned in the ETag header
                    let etag = xhr.getResponseHeader("ETag");
                    
                    // For local mock uploader, it might be returned in the JSON response body
                    if (!etag && xhr.responseText) {
                        try {
                            const res = JSON.parse(xhr.responseText);
                            etag = res.ETag;
                        } catch (err) {}
                    }
                    
                    if (etag) {
                        // S3 ETags usually contain quotes, e.g. '"a5be..."', keep them
                        completedParts.push({
                            PartNumber: part.PartNumber,
                            ETag: etag
                        });
                        partProgress[part.PartNumber] = end - start; // Set full chunk as uploaded
                        updateOverallProgress();
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

    // 2. Queue and execute chunk uploads with Concurrency Control
    const queue = [...parts];
    const workers: Promise<void>[] = [];

    const startWorker = async (): Promise<void> => {
        while (queue.length > 0) {
            const part = queue.shift();
            if (part) {
                try {
                    await uploadChunk(part);
                } catch (err) {
                    // Abort upload on S3 if any part fails
                    await fetch(`/api/matches/${matchId}/upload/abort?upload_id=${upload_id}&original_filename=${encodeURIComponent(original_filename)}`, {
                        method: "POST"
                    });
                    throw err;
                }
            }
        }
    };

    // Launch parallel workers
    for (let i = 0; i < Math.min(CONCURRENCY_LIMIT, parts.length); i++) {
        workers.push(startWorker());
    }

    // Wait for all chunk uploads to finish
    await Promise.all(workers);

    // 3. Finalize upload (Complete Multipart Upload)
    progressLabel.textContent = "Finalizing upload (assembling video)...";
    
    const completeResponse = await fetch(`/api/matches/${matchId}/upload/complete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            upload_id: upload_id,
            parts: completedParts,
            original_filename: original_filename
        })
    });

    if (!completeResponse.ok) {
        throw new Error("Failed to assemble the video on S3.");
    }

    resetForm();
    loadMatches();
}

function resetForm(): void {
    matchForm.reset();
    selectedFile = null;
    progressContainer.style.display = "none";
    progressFill.style.width = "0%";
    progressLabel.textContent = "0%";
    dropZone.classList.remove("file-selected");
    
    const dropText = dropZone.querySelector(".drop-text") as HTMLParagraphElement;
    if (dropText) {
        dropText.textContent = "Drag video file here or click to select";
    }
    submitBtn.disabled = true;
}

// Load Matches list
async function loadMatches(): Promise<void> {
    try {
        const response = await fetch("/api/matches");
        if (!response.ok) throw new Error("Could not fetch matches list.");
        
        const matches: Match[] = await response.json();
        renderMatches(matches);
    } catch (error) {
        console.error(error);
        matchesList.innerHTML = `<p class="empty-state">Failed to load matches.</p>`;
    }
}

function renderMatches(matches: Match[]): void {
    if (matches.length === 0) {
        matchesList.innerHTML = `<p class="empty-state">No matches uploaded yet.</p>`;
        return;
    }

    matchesList.innerHTML = matches.map(match => {
        const status = match.video_filename ? "ready" : "uploading";
        const statusClass = match.video_filename ? "status-ready" : "status-uploading";
        const dateStr = new Date(match.created_at).toLocaleDateString(undefined, {
            month: 'short',
            day: 'numeric',
            year: 'numeric'
        });

        return `
            <div class="match-item" data-id="${match.id}">
                <div class="match-info">
                    <span class="match-title">${match.name}</span>
                    <span class="match-players">${match.player1} vs ${match.player2} • ${dateStr}</span>
                </div>
                <div class="match-meta">
                    <span class="match-status ${statusClass}">${status}</span>
                    <button class="delete-btn" onclick="deleteMatch('${match.id}')">Delete</button>
                </div>
            </div>
        `;
    }).join("");
}

// Delete Match
async function deleteMatch(matchId: string): Promise<void> {
    if (!confirm("Are you sure you want to delete this match and its video files?")) {
        return;
    }

    try {
        const response = await fetch(`/api/matches/${matchId}`, {
            method: "DELETE"
        });

        if (!response.ok) throw new Error("Failed to delete match.");

        loadMatches();
    } catch (error: any) {
        alert(error.message || "Could not delete match.");
    }
}

(window as any).deleteMatch = deleteMatch;
