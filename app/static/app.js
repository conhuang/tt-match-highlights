// Elements
const matchForm = document.getElementById("match-form");
const matchNameInput = document.getElementById("match-name");
const player1Input = document.getElementById("player1");
const player2Input = document.getElementById("player2");
const dropZone = document.getElementById("drop-zone");
const fileInput = document.getElementById("file-input");
const progressContainer = document.getElementById("progress-container");
const progressFill = document.getElementById("progress-fill");
const progressLabel = document.getElementById("progress-label");
const submitBtn = document.getElementById("submit-btn");
const matchesList = document.getElementById("matches-list");

let selectedFile = null;
const CHUNK_SIZE = 50 * 1024 * 1024; // 50MB Chunks
const CONCURRENCY_LIMIT = 3;         // Max parallel chunk uploads

// Initial Load
document.addEventListener("DOMContentLoaded", () => {
    loadMatches();
});

// Drag & Drop Handlers
dropZone.addEventListener("click", () => fileInput.click());

dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("dragover");
});

dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("dragover");
});

dropZone.addEventListener("drop", (e) => {
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

function handleFileSelect(file) {
    if (file.type !== "video/mp4" && file.type !== "video/quicktime") {
        alert("Please select an MP4 or MOV video file.");
        return;
    }
    
    selectedFile = file;
    dropZone.classList.add("file-selected");
    const dropText = dropZone.querySelector(".drop-text");
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

function validateForm() {
    const isFormValid = matchNameInput.value.trim() !== "" &&
                        player1Input.value.trim() !== "" &&
                        player2Input.value.trim() !== "";
    
    submitBtn.disabled = !(isFormValid && selectedFile !== null);
}

// Create Match & Upload Handler
matchForm.addEventListener("submit", async (e) => {
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

        const match = await createResponse.json();

        // Step 2: Begin S3 Direct Multipart Upload sequence
        await uploadVideoMultipart(match.id, selectedFile);

    } catch (error) {
        alert(error.message || "An error occurred during match creation.");
        submitBtn.disabled = false;
    }
});

// Multipart Uploader with Parallel Workers
async function uploadVideoMultipart(matchId, file) {
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

    const { upload_id, parts, original_filename } = await initResponse.json();
    
    const completedParts = [];
    const partProgress = {};

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
    const uploadChunk = (part) => {
        return new Promise((resolve, reject) => {
            const start = (part.PartNumber - 1) * CHUNK_SIZE;
            const end = Math.min(start + CHUNK_SIZE, file.size);
            const blob = file.slice(start, end);

            const xhr = new XMLHttpRequest();
            const method = part.UploadUrl.startsWith("/") ? "PUT" : "PUT";
            xhr.open(method, part.UploadUrl);

            xhr.upload.addEventListener("progress", (e) => {
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

    // 2. Queue and execute chunk uploads with Concurrency Control
    const queue = [...parts];
    const workers = [];

    const startWorker = async () => {
        while (queue.length > 0) {
            const part = queue.shift();
            if (part) {
                try {
                    await uploadChunk(part);
                } catch (err) {
                    await fetch(`/api/matches/${matchId}/upload/abort?upload_id=${upload_id}&original_filename=${encodeURIComponent(original_filename)}`, {
                        method: "POST"
                    });
                    throw err;
                }
            }
        }
    };

    for (let i = 0; i < Math.min(CONCURRENCY_LIMIT, parts.length); i++) {
        workers.push(startWorker());
    }

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

function resetForm() {
    matchForm.reset();
    selectedFile = null;
    progressContainer.style.display = "none";
    progressFill.style.width = "0%";
    progressLabel.textContent = "0%";
    dropZone.classList.remove("file-selected");
    
    const dropText = dropZone.querySelector(".drop-text");
    if (dropText) {
        dropText.textContent = "Drag video file here or click to select";
    }
    submitBtn.disabled = true;
}

// Load Matches list
async function loadMatches() {
    try {
        const response = await fetch("/api/matches");
        if (!response.ok) throw new Error("Could not fetch matches list.");
        
        const matches = await response.json();
        renderMatches(matches);
    } catch (error) {
        console.error(error);
        matchesList.innerHTML = `<p class="empty-state">Failed to load matches.</p>`;
    }
}

function renderMatches(matches) {
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
async function deleteMatch(matchId) {
    if (!confirm("Are you sure you want to delete this match and its video files?")) {
        return;
    }

    try {
        const response = await fetch(`/api/matches/${matchId}`, {
            method: "DELETE"
        });

        if (!response.ok) throw new Error("Failed to delete match.");

        loadMatches();
    } catch (error) {
        alert(error.message || "Could not delete match.");
    }
}

window.deleteMatch = deleteMatch;
