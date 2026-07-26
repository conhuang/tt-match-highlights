import React, { useRef, useState } from 'react';
import { UploadCloud, Film } from 'lucide-react';

interface UploadZoneProps {
    selectedFile: File | null;
    onFileSelect: (file: File) => void;
    uploading: boolean;
    progressPercent: number;
    uploadedMB: number;
    totalMB: number;
    statusText: string;
}

export const UploadZone: React.FC<UploadZoneProps> = ({
    selectedFile,
    onFileSelect,
    uploading,
    progressPercent,
    uploadedMB,
    totalMB,
    statusText
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
        <div
            className={`drop-zone ${isDragOver ? 'dragover' : ''} ${selectedFile ? 'file-selected' : ''}`}
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
    );
};
