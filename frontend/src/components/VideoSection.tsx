import { forwardRef } from 'react';

interface VideoSectionProps {
    src: string;
}

export const VideoSection = forwardRef<HTMLVideoElement, VideoSectionProps>(({ src }, ref) => {
    return (
        <div className="video-card">
            <video
                ref={ref}
                src={src}
                controls
                preload="auto"
                className="video-player"
            />
        </div>
    );
});

VideoSection.displayName = 'VideoSection';
