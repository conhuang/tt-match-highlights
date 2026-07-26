import React, { useRef, useState } from 'react';
import { UploadCloud, Film, RefreshCw, Trash2 } from 'lucide-react';
import { ResumeSession } from '../types';

interface UploadZoneProps {
    selectedFile: File | null;
    onFileSelect: (file: File) => void;
    uploading: boolean;
    progressPercent: number;
    uploadedMB: number;
    totalMB: number;
    statusText: string;
    resumeSession: ResumeSession | null;
    onDiscardResume: () => void;
}

export const UploadZone: React.FC<UploadZoneProps> = ({
    selectedFile,
    onFileSelect,
    uploading,
    progressPercent,
    uploadedMB,
    totalMB,
    statusText,
    resumeSession,
    onDiscardResume
}) => {
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [isDragOver, setIsDragOver] = useState(false);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            validateAndSelect(e.target.files[0]);
        }
    };

    const validateAndSelect = (file: File) => {
        if (file.type !== 'video/mp4' && file.type !== 'video/quicktime' && !file.name.endsWith('.mp4') && !file.name.endsWith('.mov')) {
            alert('Please select an MP4 or MOV video file.');
            return;
        }

        if (resumeSession) {
            if (file.name !== resumeSession.originalFilename || file.size !== resumeSession.fileSize) {
                alert(`Please select the exact same file to resume upload:\n\nRequired Name: ${resumeSession.originalFilename}\nRequired Size: ${(resumeSession.fileSize / (1024 * 1024)).toFixed(1)} MB`);
                return;
            }
        }

        onFileSelect(file);
    };

    const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        setIsDragOver(false);
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            validateAndSelect(e.dataTransfer.files[0]);
        }
    };

    return (
        <div className="upload-zone-wrapper">
            {resumeSession && !uploading && (
                <div className="resume-banner">
                    <div className="resume-banner-info">
                        <RefreshCw size={16} className="resume-icon" />
                        <span>
                            Unfinished upload found for <strong>{resumeSession.matchName}</strong> ({resumeSession.player1} vs {resumeSession.player2}).
                            Select <code>{resumeSession.originalFilename}</code> to resume.
                        </span>
                    </div>
                    <button
                        type="button"
                        className="discard-resume-btn"
                        onClick={(e) => {
                            e.stopPropagation();
                            onDiscardResume();
                        }}
                    >
                        <Trash2 size={14} /> Discard Session
                    </button>
                </div>
            )}

            <div
                className={`drop-zone ${isDragOver ? 'dragover' : ''} ${selectedFile ? 'file-selected' : ''} ${resumeSession ? 'resume-mode' : ''}`}
                onClick={() => !uploading && fileInputRef.current?.click()}
                onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
                onDragLeave={() => setIsDragOver(false)}
                onDrop={handleDrop}
            >
                <input
                    type="file"
                    ref={fileInputRef}
                    accept="video/mp4,video/quicktime"
                    style={{ display: 'none' }}
                    onChange={handleFileChange}
                    disabled={uploading}
                />

                <div className="drop-zone-content">
                    {selectedFile ? (
                        <Film className="drop-icon active" size={32} />
                    ) : (
                        <UploadCloud className="drop-icon" size={32} />
                    )}

                    <p className="drop-text">
                        {selectedFile
                            ? `Selected: ${selectedFile.name} (${(selectedFile.size / (1024 * 1024)).toFixed(1)} MB)`
                            : resumeSession
                            ? `Click or drag "${resumeSession.originalFilename}" to resume upload`
                            : 'Drag video file here or click to browse'}
                    </p>
                    <span className="drop-hint">Supports MP4 and MOV formats</span>
                </div>

                {uploading && (
                    <div className="progress-container">
                        <div className="progress-bar">
                            <div className="progress-fill" style={{ width: `${progressPercent}%` }} />
                        </div>
                        <span className="progress-label">
                            {statusText} {totalMB > 0 ? `(${uploadedMB}MB / ${totalMB}MB)` : ''}
                        </span>
                    </div>
                )}
            </div>
        </div>
    );
};
