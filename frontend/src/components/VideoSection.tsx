import { forwardRef, useState } from 'react';
import { Match } from '../types';
import { Badge } from './ui';
import { Film, Sliders, Monitor } from 'lucide-react';

interface VideoSectionProps {
    src: string;
    match: Match;
    activePreviewUrl?: string | null;
}

export const VideoSection = forwardRef<HTMLVideoElement, VideoSectionProps>(({ src, match, activePreviewUrl }, ref) => {
    const [detectedWidth, setDetectedWidth] = useState<number | null>(null);
    const [detectedHeight, setDetectedHeight] = useState<number | null>(null);

    const handleLoadedMetadata = (e: React.SyntheticEvent<HTMLVideoElement>) => {
        const video = e.currentTarget;
        if (video.videoWidth && video.videoHeight) {
            setDetectedWidth(video.videoWidth);
            setDetectedHeight(video.videoHeight);
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

    return (
        <div className="video-card">
            <div className="video-resolution-bar">
                <div className="video-res-left">
                    {activePreviewUrl ? (
                        <Badge variant="rendering" icon={<Film size={12} />}>
                            Render Preview
                        </Badge>
                    ) : (
                        <Badge variant="info" icon={<Sliders size={12} />}>
                            Preview: 720p
                        </Badge>
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

