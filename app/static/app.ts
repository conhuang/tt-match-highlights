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

interface ResumeSession {
    matchId: string;
    uploadId: string;
    originalFilename: string;
    fileSize: number;
    matchName: string;
    player1: string;
    player2: string;
    parts: UploadPart[];
}

let activeResumeSession: ResumeSession | null = null;
let isOffline = false;
let retryTimeoutId: any = null;

// Initial Load
document.addEventListener("DOMContentLoaded", () => {
    loadMatches();
    checkActiveResumeSession();
});

// Check if there is an interrupted upload stored in localStorage
function checkActiveResumeSession(): void {
    for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && key.startsWith("s3_upload_")) {
            try {
                const item = localStorage.getItem(key);
                if (item) {
                    activeResumeSession = JSON.parse(item);
                    setupResumeUI();
                    break;
                }
            } catch (err) {
                console.error("Failed to parse active resume session:", err);
            }
        }
    }
}

// Pre-fill form and display resume message
function setupResumeUI(): void {
    if (!activeResumeSession) return;

    matchNameInput.value = activeResumeSession.matchName;
    player1Input.value = activeResumeSession.player1;
    player2Input.value = activeResumeSession.player2;

    matchNameInput.disabled = true;
    player1Input.disabled = true;
    player2Input.disabled = true;

    const dropText = dropZone.querySelector(".drop-text") as HTMLParagraphElement;
    if (dropText) {
        dropText.innerHTML = `
            <div style="font-weight: 600; color: #ff9800; margin-bottom: 5px;">⚠️ Interrupted Upload Detected</div>
            <div style="margin-bottom: 10px;">Please drag or select the original file to resume:</div>
            <div style="font-weight: 500; font-size: 1.1em; color: #4caf50; background: rgba(76, 175, 80, 0.1); padding: 5px 10px; border-radius: 4px; display: inline-block;">${activeResumeSession.originalFilename}</div>
        `;
    }
    dropZone.classList.add("resume-mode");

    // Inject Discard button
    let discardBtn = document.getElementById("discard-resume-btn") as HTMLButtonElement | null;
    if (!discardBtn) {
        discardBtn = document.createElement("button");
        discardBtn.id = "discard-resume-btn";
        discardBtn.type = "button";
        discardBtn.textContent = "Discard Interrupted Upload";
        discardBtn.style.cssText = "margin-top: 15px; background-color: #f44336; border: none; color: white; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-size: 0.9em; margin-right: 10px;";
        discardBtn.addEventListener("click", discardActiveSession);
        
        submitBtn.parentNode!.insertBefore(discardBtn, submitBtn);
    }

    submitBtn.textContent = "Resume Upload";
    submitBtn.disabled = true; 
}

// Call backend /abort API and reset form
async function discardActiveSession(): Promise<void> {
    if (!activeResumeSession) return;
    if (!confirm("Are you sure you want to discard this upload? Any progress will be lost and S3 temporary storage will be cleaned up.")) {
        return;
    }

    const { matchId, uploadId, originalFilename } = activeResumeSession;
    const discardBtn = document.getElementById("discard-resume-btn") as HTMLButtonElement | null;
    if (discardBtn) discardBtn.disabled = true;

    try {
        progressContainer.style.display = "flex";
        progressLabel.textContent = "Aborting upload on AWS S3...";
        
        await fetch(`/api/matches/${matchId}/upload/abort?upload_id=${uploadId}&original_filename=${encodeURIComponent(originalFilename)}`, {
            method: "POST"
        });
    } catch (err) {
        console.warn("Failed to abort multipart upload on S3, clearing locally anyway:", err);
    }

    localStorage.removeItem(`s3_upload_${matchId}`);
    activeResumeSession = null;

    if (discardBtn) discardBtn.remove();
    submitBtn.textContent = "Create Match";
    
    matchNameInput.disabled = false;
    player1Input.disabled = false;
    player2Input.disabled = false;

    resetForm();
    loadMatches();
}

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
    
    if (activeResumeSession) {
        if (file.name !== activeResumeSession.originalFilename || file.size !== activeResumeSession.fileSize) {
            alert(`Please select the exact same file to resume:\nName: ${activeResumeSession.originalFilename}\nSize: ${(activeResumeSession.fileSize / (1024 * 1024)).toFixed(1)} MB`);
            selectedFile = null;
            dropZone.classList.remove("file-selected");
            if (dropText) {
                setupResumeUI();
            }
            validateForm();
            return;
        }
    }

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
    if (activeResumeSession) {
        const matches = selectedFile && 
                        selectedFile.name === activeResumeSession.originalFilename && 
                        selectedFile.size === activeResumeSession.fileSize;
        submitBtn.disabled = !matches;
        return;
    }

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

    if (activeResumeSession) {
        try {
            progressContainer.style.display = "flex";
            progressLabel.textContent = "Checking upload progress on S3...";
            
            const discardBtn = document.getElementById("discard-resume-btn");
            if (discardBtn) discardBtn.remove();
            
            await runUploadQueue(
                activeResumeSession.matchId,
                selectedFile,
                activeResumeSession.uploadId,
                activeResumeSession.parts,
                activeResumeSession.originalFilename
            );
        } catch (error: any) {
            alert(error.message || "An error occurred during upload resume.");
            setupResumeUI();
        }
        return;
    }
    
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
        await uploadVideoMultipart(match.id, selectedFile, matchData.name, matchData.player1, matchData.player2);

    } catch (error: any) {
        alert(error.message || "An error occurred during match creation.");
        submitBtn.disabled = false;
    }
});

// Multipart Uploader Initiation
async function uploadVideoMultipart(matchId: string, file: File, matchName: string, player1: string, player2: string): Promise<void> {
    progressContainer.style.display = "flex";
    progressLabel.textContent = "Initializing upload...";

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
    
    console.log("Multipart upload initialized successfully!");
    console.log("  Upload ID:", upload_id);
    
    // Save to localStorage so we can resume if tab is closed
    localStorage.setItem(`s3_upload_${matchId}`, JSON.stringify({
        matchId,
        uploadId: upload_id,
        originalFilename: original_filename,
        fileSize: file.size,
        matchName,
        player1,
        player2,
        parts
    }));

    await runUploadQueue(matchId, file, upload_id, parts, original_filename);
}

// Core upload queue execution with parallel workers & auto-resume retry state machine
async function runUploadQueue(matchId: string, file: File, upload_id: string, parts: UploadPart[], original_filename: string): Promise<void> {
    let uploadedParts: any[] = [];
    try {
        const res = await fetch(`/api/matches/${matchId}/upload/parts?upload_id=${upload_id}&original_filename=${encodeURIComponent(original_filename)}`);
        if (!res.ok) throw new Error("Failed to fetch uploaded parts.");
        const data = await res.json();
        uploadedParts = data.parts;
    } catch (err) {
        console.warn("Could not query uploaded parts from S3, assuming none are uploaded:", err);
    }

    const uploadedPartNumbers = new Set<number>(uploadedParts.map(p => p.PartNumber));
    const completedParts: { PartNumber: number; ETag: string }[] = [...uploadedParts];
    const partProgress: { [key: number]: number } = {};

    // Pre-fill progress for already completed parts
    uploadedParts.forEach(p => {
        const start = (p.PartNumber - 1) * CHUNK_SIZE;
        const end = Math.min(start + CHUNK_SIZE, file.size);
        partProgress[p.PartNumber] = end - start;
    });

    const updateOverallProgress = () => {
        let totalUploaded = 0;
        for (const partNum in partProgress) {
            totalUploaded += partProgress[partNum];
        }
        const percent = Math.min((totalUploaded / file.size) * 100, 99.9);
        progressFill.style.width = `${percent}%`;
        progressLabel.textContent = `Uploading: ${percent.toFixed(1)}% (${(totalUploaded / (1024 * 1024)).toFixed(0)}MB / ${(file.size / (1024 * 1024)).toFixed(0)}MB)`;
    };
    updateOverallProgress();

    // Filter out remaining parts
    const remainingParts = parts.filter(p => !uploadedPartNumbers.has(p.PartNumber));
    if (remainingParts.length === 0) {
        await finalizeUpload(matchId, upload_id, completedParts, original_filename);
        return;
    }

    // Queue workers
    const queue = [...remainingParts];
    const workers: Promise<void>[] = [];
    let uploadAborted = false;

    const uploadChunk = (part: UploadPart): Promise<void> => {
        return new Promise((resolve, reject) => {
            const start = (part.PartNumber - 1) * CHUNK_SIZE;
            const end = Math.min(start + CHUNK_SIZE, file.size);
            const blob = file.slice(start, end);

            console.log(`Starting upload of Part #${part.PartNumber}/${parts.length} (size: ${(blob.size / (1024 * 1024)).toFixed(1)}MB)...`);

            const xhr = new XMLHttpRequest();
            xhr.open("PUT", part.UploadUrl);

            xhr.upload.addEventListener("progress", (e: ProgressEvent) => {
                if (e.lengthComputable) {
                    partProgress[part.PartNumber] = e.loaded;
                    updateOverallProgress();
                }
            });

            xhr.onload = () => {
                if (xhr.status === 200) {
                    let etag = xhr.getResponseHeader("ETag");
                    
                    if (!etag && xhr.responseText) {
                        try {
                            const res = JSON.parse(xhr.responseText);
                            etag = res.ETag;
                        } catch (err) {}
                    }
                    
                    if (etag) {
                        console.log(`Successfully uploaded Part #${part.PartNumber}. ETag: ${etag}`);
                        completedParts.push({
                            PartNumber: part.PartNumber,
                            ETag: etag
                        });
                        partProgress[part.PartNumber] = end - start;
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
        console.warn("Upload interrupted due to network error, entering auto-resume mode:", err);
        handleOfflineMode(matchId, file, upload_id, parts, original_filename);
        return;
    }

    await finalizeUpload(matchId, upload_id, completedParts, original_filename);
}

// Wait for internet to restore and auto-resume the upload
function handleOfflineMode(matchId: string, file: File, upload_id: string, parts: UploadPart[], original_filename: string): void {
    if (isOffline) return;
    isOffline = true;

    progressLabel.textContent = "Connection lost. Retrying automatically...";
    progressFill.classList.add("progress-paused");

    const tryResume = async () => {
        try {
            console.log("Auto-resume: checking network connection...");
            const res = await fetch(`/api/matches/${matchId}/upload/parts?upload_id=${upload_id}&original_filename=${encodeURIComponent(original_filename)}`);
            if (res.ok) {
                console.log("Connection restored! Resuming upload...");
                isOffline = false;
                progressFill.classList.remove("progress-paused");
                window.removeEventListener("online", tryResume);
                if (retryTimeoutId) clearTimeout(retryTimeoutId);
                
                runUploadQueue(matchId, file, upload_id, parts, original_filename);
                return;
            }
        } catch (e) {
            console.log("Auto-resume: still offline, waiting to retry...");
        }

        retryTimeoutId = setTimeout(tryResume, 10000);
    };

    window.addEventListener("online", tryResume);
    retryTimeoutId = setTimeout(tryResume, 5000);
}

// Send complete multipart request to backend
async function finalizeUpload(matchId: string, upload_id: string, completedParts: { PartNumber: number; ETag: string }[], original_filename: string): Promise<void> {
    console.log("All chunks successfully uploaded. Finalizing complete request to assemble video...");
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
        let errorMsg = "Failed to assemble the video on S3.";
        try {
            const errData = await completeResponse.json();
            if (errData && errData.detail) errorMsg = errData.detail;
        } catch (e) {}
        throw new Error(errorMsg);
    }

    console.log("Video assembled and upload workflow completed successfully!");
    
    localStorage.removeItem(`s3_upload_${matchId}`);
    activeResumeSession = null;
    
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
    dropZone.classList.remove("resume-mode");
    
    const discardBtn = document.getElementById("discard-resume-btn") as HTMLButtonElement | null;
    if (discardBtn) discardBtn.remove();
    submitBtn.textContent = "Create Match";

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
