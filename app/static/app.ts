interface Event {
    start: number;
    end: number;
    winner: string;
    timeout_player?: string | null;
    isHighlight: boolean;
    game: number;
    score_before: string;
}

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
    video_url?: string | null;
    rendered_video_url?: string | null;
    events: Event[];
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

// DOM Elements
const container = document.querySelector(".container") as HTMLDivElement;
const dashboardView = document.getElementById("dashboard-view") as HTMLDivElement;
const workspaceView = document.getElementById("workspace-view") as HTMLDivElement;

// Dashboard Form Elements
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

// Workspace Elements
const backBtn = document.getElementById("back-btn") as HTMLButtonElement;
const workspaceTitle = document.getElementById("workspace-title") as HTMLHeadingElement;
const videoPlayer = document.getElementById("video-player") as HTMLVideoElement;
const pendingStartLabel = document.getElementById("pending-start-label") as HTMLSpanElement;
const activeGameInput = document.getElementById("active-game") as HTMLInputElement;
const eventsList = document.getElementById("events-list") as HTMLDivElement;
const saveEventsBtn = document.getElementById("save-events-btn") as HTMLButtonElement;
const renderBtn = document.getElementById("render-btn") as HTMLButtonElement;

// Global State
let selectedFile: File | null = null;
let currentMatch: Match | null = null;
let pendingStartTime: number | null = null;

const CHUNK_SIZE = 50 * 1024 * 1024; // 50MB Chunks
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

// Dashboard Click Delegator (Opens Workspace View)
matchesList.addEventListener("click", (e: Event) => {
    const target = e.target as HTMLElement;
    if (target.classList.contains("delete-btn")) {
        return; // Handled by deleteMatch
    }
    const matchItem = target.closest(".match-item");
    if (matchItem) {
        const matchId = matchItem.getAttribute("data-id");
        if (matchId) {
            selectMatchForWorkspace(matchId);
        }
    }
});

async function selectMatchForWorkspace(matchId: string): Promise<void> {
    try {
        const response = await fetch(`/api/matches/${matchId}`);
        if (!response.ok) throw new Error("Failed to load match details.");
        
        const match: Match = await response.json();
        if (!match.video_filename) {
            alert("This match does not have an uploaded video yet. Please upload a video first.");
            return;
        }
        
        openWorkspace(match);
    } catch (error: any) {
        alert(error.message || "Error entering workspace.");
    }
}

// --- WORKSPACE VIEW CONTROLLER ---
function openWorkspace(match: Match): void {
    currentMatch = match;
    
    // Toggle views
    dashboardView.style.display = "none";
    workspaceView.style.display = "block";
    container.classList.add("workspace-active");
    
    workspaceTitle.textContent = `${match.name} Workspace (${match.player1} vs ${match.player2})`;
    
    // Set video player src (pre-signed URL or local fallbacks)
    if (match.video_url) {
        videoPlayer.src = match.video_url;
    } else {
        videoPlayer.src = `/static/videos/uploads/${match.video_filename}`;
    }
    videoPlayer.load();
    
    // Reset state
    pendingStartTime = null;
    pendingStartLabel.textContent = "None";
    activeGameInput.value = "1";
    
    renderEvents();
}

function renderEvents(): void {
    if (!currentMatch) return;
    
    if (currentMatch.events.length === 0) {
        eventsList.innerHTML = `
            <p class="empty-state">No points logged yet. Use E/D to mark start and 1/2 keys to log winners.</p>
        `;
        return;
    }
    
    // Events must be sorted chronologically for correct sidebar rendering
    currentMatch.events.sort((a, b) => a.start - b.start);
    
    eventsList.innerHTML = currentMatch.events.map((event, index) => {
        const startStr = formatTime(event.start);
        const endStr = formatTime(event.end);
        const isP1 = event.winner === currentMatch?.player1;
        const winnerClass = isP1 ? "p1" : "p2";
        
        return `
            <div class="event-card">
                <div class="event-card-header">
                    <button class="time-link-btn" onclick="seekVideo(${event.start})">${startStr} - ${endStr}</button>
                    <span class="event-winner ${winnerClass}">${event.winner} Wins Point</span>
                </div>
                <div class="event-details">
                    <span>Game ${event.game} • Score: ${event.score_before}</span>
                    <div class="event-inputs">
                        <label>
                            <input type="checkbox" ${event.isHighlight ? "checked" : ""} onchange="toggleEventHighlight(${index}, this.checked)">
                            ⭐ Highlight
                        </label>
                        <label>
                            TO:
                            <select onchange="updateEventTimeout(${index}, this.value)" style="background: transparent; color: #fff; border: 1px solid var(--border-color); border-radius: 3px; font-size: 0.75rem;">
                                <option value="" ${!event.timeout_player ? "selected" : ""}>None</option>
                                <option value="${currentMatch?.player1}" ${event.timeout_player === currentMatch?.player1 ? "selected" : ""}>P1</option>
                                <option value="${currentMatch?.player2}" ${event.timeout_player === currentMatch?.player2 ? "selected" : ""}>P2</option>
                            </select>
                        </label>
                        <button class="event-delete-btn" onclick="deleteEvent(${index})">Delete</button>
                    </div>
                </div>
            </div>
        `;
    }).join("");
}

function formatTime(seconds: number): string {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 10);
    const pad = (num: number) => num.toString().padStart(2, '0');
    return `${pad(m)}:${pad(s)}.${ms}`;
}

// Real-time Event Persistence Auto-Saver
async function autoSaveEvents(): Promise<void> {
    if (!currentMatch) return;
    
    saveEventsBtn.disabled = true;
    saveEventsBtn.textContent = "Saving...";
    
    try {
        const response = await fetch(`/api/matches/${currentMatch.id}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                events: currentMatch.events
            })
        });
        
        if (!response.ok) throw new Error("Auto-save failed.");
        
        const updatedMatch: Match = await response.json();
        // Update client-side state with backend-calculated scores and games
        currentMatch.events = updatedMatch.events;
        renderEvents();
        
        saveEventsBtn.textContent = "Saved";
        setTimeout(() => {
            if (saveEventsBtn && saveEventsBtn.textContent === "Saved") {
                saveEventsBtn.textContent = "Save Events";
                saveEventsBtn.disabled = false;
            }
        }, 1000);
    } catch (error) {
        console.error("Auto-save error:", error);
        saveEventsBtn.textContent = "Save Failed";
        saveEventsBtn.disabled = false;
    }
}

// Global Keyboard Shortcut Engine
window.addEventListener("keydown", (e: KeyboardEvent) => {
    // Disable shortcuts if not in workspace or if user is active in inputs/selects
    if (!currentMatch) return;
    const activeEl = document.activeElement;
    if (activeEl && (activeEl.tagName === "INPUT" || activeEl.tagName === "TEXTAREA" || activeEl.tagName === "SELECT")) {
        return;
    }
    
    const key = e.key.toLowerCase();
    
    if (e.key === " ") {
        e.preventDefault(); // Stop spacebar scrolling the page
        if (videoPlayer.paused) {
            videoPlayer.play();
        } else {
            videoPlayer.pause();
        }
    } else if (key === "e" || key === "d") {
        pendingStartTime = videoPlayer.currentTime;
        pendingStartLabel.textContent = `${pendingStartTime.toFixed(1)}s`;
        console.log(`[SHORTCUT] Marked Start Time: ${pendingStartTime.toFixed(1)}s`);
    } else if (key === "1" || key === "a" || key === "2" || key === "s") {
        if (pendingStartTime === null) {
            alert("Please mark the Start Time first using 'E' or 'D'.");
            return;
        }
        const endTime = videoPlayer.currentTime;
        if (endTime <= pendingStartTime) {
            alert("End time must be greater than start time.");
            return;
        }
        
        const winnerName = (key === "1" || key === "a") ? currentMatch.player1 : currentMatch.player2;
        const activeGame = parseInt(activeGameInput.value) || 1;
        
        const newEvent: Event = {
            start: parseFloat(pendingStartTime.toFixed(2)),
            end: parseFloat(endTime.toFixed(2)),
            winner: winnerName,
            timeout_player: null,
            isHighlight: false,
            game: activeGame,
            score_before: "0-0" // Populated by backend
        };
        
        currentMatch.events.push(newEvent);
        console.log(`[SHORTCUT] Logged Point for ${winnerName} (Start: ${newEvent.start}s, End: ${newEvent.end}s)`);
        
        // Reset local start marker
        pendingStartTime = null;
        pendingStartLabel.textContent = "None";
        
        autoSaveEvents();
    } else if (key === "z") {
        if (currentMatch.events.length > 0) {
            const removed = currentMatch.events.pop();
            console.log("[SHORTCUT] Undone last event:", removed);
            autoSaveEvents();
        }
    }
});

// Workspace Controls Click Handlers
backBtn.addEventListener("click", () => {
    videoPlayer.pause();
    videoPlayer.src = "";
    
    currentMatch = null;
    workspaceView.style.display = "none";
    dashboardView.style.display = "block";
    container.classList.remove("workspace-active");
    
    loadMatches();
});

saveEventsBtn.addEventListener("click", () => {
    autoSaveEvents();
});

// Global Seek/Highlight Helpers for dynamic HTML buttons
(window as any).seekVideo = (time: number) => {
    videoPlayer.currentTime = time;
    videoPlayer.play();
};

(window as any).toggleEventHighlight = (index: number, checked: boolean) => {
    if (currentMatch) {
        currentMatch.events[index].isHighlight = checked;
        autoSaveEvents();
    }
};

(window as any).updateEventTimeout = (index: number, value: string) => {
    if (currentMatch) {
        currentMatch.events[index].timeout_player = value === "" ? null : value;
        autoSaveEvents();
    }
};

(window as any).deleteEvent = (index: number) => {
    if (currentMatch) {
        currentMatch.events.splice(index, 1);
        autoSaveEvents();
    }
};

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
