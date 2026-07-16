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

// Elements
const matchForm = document.getElementById("match-form") as HTMLFormElement;
const matchNameInput = document.getElementById("match-name") as HTMLInputElement;
const player1Input = document.getElementById("player-1") as HTMLInputElement || document.getElementById("player1") as HTMLInputElement;
const player2Input = document.getElementById("player-2") as HTMLInputElement || document.getElementById("player2") as HTMLInputElement;
const dropZone = document.getElementById("drop-zone") as HTMLDivElement;
const fileInput = document.getElementById("file-input") as HTMLInputElement;
const progressContainer = document.getElementById("progress-container") as HTMLDivElement;
const progressFill = document.getElementById("progress-fill") as HTMLDivElement;
const progressLabel = document.getElementById("progress-label") as HTMLSpanElement;
const submitBtn = document.getElementById("submit-btn") as HTMLButtonElement;
const matchesList = document.getElementById("matches-list") as HTMLDivElement;

let selectedFile: File | null = null;

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
    input.addEventListener("input", validateForm);
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

        // Step 2: Upload Video File
        uploadVideo(match.id, selectedFile);

    } catch (error: any) {
        alert(error.message || "An error occurred during match creation.");
        submitBtn.disabled = false;
    }
});

function uploadVideo(matchId: string, file: File): void {
    progressContainer.style.display = "flex";
    
    const formData = new FormData();
    formData.append("file", file);

    const xhr = new XMLHttpRequest();
    
    xhr.upload.addEventListener("progress", (e: ProgressEvent) => {
        if (e.lengthComputable) {
            const percent = (e.loaded / e.total) * 100;
            progressFill.style.width = `${percent}%`;
            progressLabel.textContent = `${percent.toFixed(0)}%`;
        }
    });

    xhr.open("POST", `/api/matches/${matchId}/upload`);
    
    xhr.onload = () => {
        if (xhr.status === 200) {
            resetForm();
            loadMatches();
        } else {
            alert("Video upload failed.");
            submitBtn.disabled = false;
        }
    };

    xhr.onerror = () => {
        alert("Network error during upload.");
        submitBtn.disabled = false;
    };

    xhr.send(formData);
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

        // Remove element from DOM or reload
        loadMatches();
    } catch (error: any) {
        alert(error.message || "Could not delete match.");
    }
}

// Expose deleteMatch globally so HTML onclick can access it
(window as any).deleteMatch = deleteMatch;
