import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Match, MatchEvent } from '../types';
import { WorkspaceHeader } from './WorkspaceHeader';
import { VideoSection } from './VideoSection';
import { StatusPanel } from './StatusPanel';
import { ShortcutSheet } from './ShortcutSheet';
import { SidebarLogs } from './SidebarLogs';
import { useKeyboardShortcuts } from '../hooks/useKeyboardShortcuts';
import { saveMatchEvents } from '../services/api';

interface WorkspaceViewProps {
    currentMatch: Match;
    onBack: () => void;
    onMatchUpdated: (updatedMatch: Match) => void;
}

export const WorkspaceView: React.FC<WorkspaceViewProps> = ({
    currentMatch,
    onBack,
    onMatchUpdated
}) => {
    const videoRef = useRef<HTMLVideoElement>(null);
    const [pendingStartTime, setPendingStartTime] = useState<number | null>(null);
    const [activeGame, setActiveGame] = useState<number>(1);
    const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'failed'>('idle');

    // Freeze video URL for the duration of this workspace session so backend auto-saves (which return new S3 signature URLs) do not cause DOM src resets or interrupt video playback.
    const [videoSrc] = useState<string>(() => {
        return currentMatch.video_url || `/static/videos/uploads/${currentMatch.video_filename}`;
    });

    const autoSave = useCallback(async (updatedEvents: MatchEvent[]) => {
        setSaveStatus('saving');
        try {
            const result = await saveMatchEvents(currentMatch.id, updatedEvents);
            const mergedMatch: Match = {
                ...result,
                video_url: result.video_url || currentMatch.video_url,
                rendered_video_url: result.rendered_video_url || currentMatch.rendered_video_url
            };
            onMatchUpdated(mergedMatch);
            setSaveStatus('saved');
            setTimeout(() => setSaveStatus('idle'), 1500);
        } catch (err) {
            console.error('Save failed:', err);
            setSaveStatus('failed');
        }
    }, [currentMatch.id, currentMatch.video_url, currentMatch.rendered_video_url, onMatchUpdated]);

    const handleAddEvent = useCallback((newEvent: MatchEvent) => {
        const newEvents = [...currentMatch.events, newEvent];
        autoSave(newEvents);
    }, [currentMatch.events, autoSave]);

    const handleUndoEvent = useCallback(() => {
        if (currentMatch.events.length === 0) return;
        const newEvents = [...currentMatch.events];
        newEvents.pop();
        autoSave(newEvents);
    }, [currentMatch.events, autoSave]);

    // Attach shortcuts hook
    useKeyboardShortcuts({
        isActive: true,
        currentMatch,
        videoRef,
        pendingStartTime,
        setPendingStartTime,
        activeGame,
        onAddEvent: handleAddEvent,
        onUndoEvent: handleUndoEvent
    });

    const handleSeek = (time: number) => {
        if (videoRef.current && videoRef.current.src) {
            videoRef.current.currentTime = time;
            videoRef.current.play().catch(() => {});
        }
    };

    const handleToggleHighlight = (index: number, isHighlight: boolean) => {
        const updated = [...currentMatch.events];
        updated[index] = { ...updated[index], isHighlight };
        autoSave(updated);
    };

    const handleUpdateTimeout = (index: number, timeoutPlayer: string | null) => {
        const updated = [...currentMatch.events];
        updated[index] = { ...updated[index], timeout_player: timeoutPlayer };
        autoSave(updated);
    };

    const handleDeleteEvent = (index: number) => {
        const updated = currentMatch.events.filter((_, i) => i !== index);
        autoSave(updated);
    };

    const handleBackClick = () => {
        if (videoRef.current) {
            videoRef.current.pause();
            videoRef.current.src = '';
        }
        onBack();
    };

    useEffect(() => {
        if (videoRef.current) {
            videoRef.current.load();
        }
    }, [videoSrc]);

    return (
        <div className="workspace-view">
            <WorkspaceHeader currentMatch={currentMatch} onBack={handleBackClick} />

            <div className="workspace-grid">
                <div className="workspace-left">
                    <VideoSection ref={videoRef} src={videoSrc} />
                    <StatusPanel pendingStartTime={pendingStartTime} />
                    <ShortcutSheet />
                </div>

                <SidebarLogs
                    currentMatch={currentMatch}
                    activeGame={activeGame}
                    onChangeActiveGame={setActiveGame}
                    onSeek={handleSeek}
                    onToggleHighlight={handleToggleHighlight}
                    onUpdateTimeout={handleUpdateTimeout}
                    onDeleteEvent={handleDeleteEvent}
                    onSaveEvents={() => autoSave(currentMatch.events)}
                    saveStatus={saveStatus}
                />
            </div>
        </div>
    );
};
