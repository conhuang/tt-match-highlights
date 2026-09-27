import { forwardRef, useState, useEffect, useRef } from 'react';
import { Match } from '../types';
import { Badge } from './ui';
import { Film, Sliders, Monitor, ChevronDown, Check } from 'lucide-react';

export interface ResolutionOption {
    id: string;
    label: string;
    url: string;
}

interface VideoSectionProps {
    src: string;
    match: Match;
    activePreviewUrl?: string | null;
    selectedResolution?: string;
    onSelectResolution?: (resolutionId: string) => void;
    availableResolutions?: ResolutionOption[];
    pendingSeekTime?: number | null;
    wasPlaying?: boolean;
    onSeekRestored?: () => void;
}

export const VideoSection = forwardRef<HTMLVideoElement, VideoSectionProps>(({
    src,
    match,
    activePreviewUrl,
    selectedResolution = '720p',
    onSelectResolution,
    availableResolutions = [],
    pendingSeekTime,
    wasPlaying,
    onSeekRestored
}, ref) => {
    const [detectedWidth, setDetectedWidth] = useState<number | null>(null);
    const [detectedHeight, setDetectedHeight] = useState<number | null>(null);
    const [isMenuOpen, setIsMenuOpen] = useState<boolean>(false);
    const dropdownRef = useRef<HTMLDivElement>(null);

    // Close resolution menu on outside click
    useEffect(() => {
        const handleClickOutside = (e: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
                setIsMenuOpen(false);
            }
        };
        if (isMenuOpen) {
            document.addEventListener('mousedown', handleClickOutside);
        }
        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, [isMenuOpen]);

    const handleLoadedMetadata = (e: React.SyntheticEvent<HTMLVideoElement>) => {
        const video = e.currentTarget;
        if (video.videoWidth && video.videoHeight) {
            setDetectedWidth(video.videoWidth);
            setDetectedHeight(video.videoHeight);
        }

        // Restore playback position on resolution switch
        if (pendingSeekTime !== null && pendingSeekTime !== undefined) {
            video.currentTime = pendingSeekTime;
            if (wasPlaying) {
                video.play().catch(() => {});
            }
            onSeekRestored?.();
        }
    };

    const width = match.width || detectedWidth;
    const height = match.height || detectedHeight;

    const getResolutionLabel = () => {
        if (!width || !height) return '1080p (1920×1080)';
        const label = height >= 2160 ? '4K' : height >= 1440 ? '1440p' : height >= 1080 ? '1080p' : height >= 720 ? '720p' : `${height}p`;
        return `${width}×${height} (${label})`;
    };

    const origRes = getResolutionLabel();

    // Clean label for current selected resolution without parentheses
    const currentOpt = availableResolutions.find(r => r.id === selectedResolution);
    const displayResLabel = currentOpt ? currentOpt.label : (selectedResolution === 'original' ? 'Original' : selectedResolution);

    return (
        <div className="video-card">
            <div className="video-resolution-bar">
                <div className="video-res-left">
                    {activePreviewUrl ? (
                        <Badge variant="rendering" icon={<Film size={12} />}>
                            Render Preview
                        </Badge>
                    ) : (
                        <div className="resolution-selector-container" ref={dropdownRef}>
                            <button
                                type="button"
                                className="resolution-selector-btn"
                                onClick={() => setIsMenuOpen(!isMenuOpen)}
                                title="Change preview playback resolution"
                                aria-label="Change preview playback resolution"
                            >
                                <Sliders size={12} className="res-icon" />
                                <span>Preview: {displayResLabel}</span>
                                <ChevronDown size={11} className={`res-chevron ${isMenuOpen ? 'open' : ''}`} />
                            </button>
                            {isMenuOpen && (
                                <div className="resolution-dropdown-menu">
                                    <div className="resolution-dropdown-header">Resolution</div>
                                    {availableResolutions.map((opt) => (
                                        <button
                                            key={opt.id}
                                            type="button"
                                            className={`resolution-dropdown-item ${selectedResolution === opt.id ? 'active' : ''}`}
                                            onClick={() => {
                                                onSelectResolution?.(opt.id);
                                                setIsMenuOpen(false);
                                            }}
                                        >
                                            <span>{opt.label}</span>
                                            {selectedResolution === opt.id && (
                                                <Check size={12} className="res-check-icon" />
                                            )}
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}
                </div>
                <div className="video-res-right" title="Final renders will be cut directly from your full original resolution source video">
                    <Monitor size={13} className="res-monitor-icon" />
                    <span className="source-res-label">
                        Original Source: <strong>{origRes}</strong>
                    </span>
                    <span className="source-render-cut-note">
                        (Final render is cut from original)
                    </span>
                </div>
            </div>
            <div className="video-viewport-wrapper">
                <video
                    ref={ref}
                    src={src}
                    controls
                    preload="auto"
                    className="video-player"
                    onLoadedMetadata={handleLoadedMetadata}
                />
            </div>
        </div>
    );
});

VideoSection.displayName = 'VideoSection';

