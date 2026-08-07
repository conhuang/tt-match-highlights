import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Match, MatchEvent, RenderOptions } from '../types';
import { WorkspaceHeader } from './WorkspaceHeader';
import { VideoSection } from './VideoSection';
import { StatusPanel } from './StatusPanel';
import { SidebarLogs } from './SidebarLogs';
import { RenderHistory } from './RenderHistory';
import { MatchStatsView } from './MatchStatsView';
import { useKeyboardShortcuts } from '../hooks/useKeyboardShortcuts';
import { saveMatchEvents, updateMatch, createRenderJob, fetchMatchRenders, deleteRenderJob, cancelRenderJob } from '../services/api';
import { RenderOptionsForm } from './RenderOptionsForm';
import { FirstServerCard } from './FirstServerCard';

interface WorkspaceViewProps {
    currentMatch: Match;
    onBack: () => void;
    onMatchUpdated: (updatedMatch: Match) => void;
    onLogout?: () => void;
}

export const WorkspaceView: React.FC<WorkspaceViewProps> = ({
    currentMatch,
    onBack,
    onMatchUpdated,
    onLogout
}) => {
    const videoRef = useRef<HTMLVideoElement>(null);
    const [pendingStartTime, setPendingStartTime] = useState<number | null>(null);
    const [isRenderingJob, setIsRenderingJob] = useState<boolean>(false);

    // Initial raw video URL
    const rawVideoUrl = currentMatch.video_url || `/static/videos/uploads/${currentMatch.video_filename}`;
    const [activeVideoSrc, setActiveVideoSrc] = useState<string>(rawVideoUrl);
    const [activePreviewUrl, setActivePreviewUrl] = useState<string | null>(null);

    // Polling for active render jobs progress
    useEffect(() => {
        const hasActiveRender = currentMatch.renders?.some(
            r => r.status === 'rendering' || r.status === 'pending'
        );
        if (!hasActiveRender) return;

        const interval = setInterval(async () => {
            try {
                const renders = await fetchMatchRenders(currentMatch.id);
                onMatchUpdated({
                    ...currentMatch,
                    renders
                });
            } catch (err) {
                console.error('Render polling error:', err);
            }
        }, 2500);

        return () => clearInterval(interval);
    }, [currentMatch.id, currentMatch.renders, onMatchUpdated]);

    const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'failed'>('idle');

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
            setTimeout(() => setSaveStatus('idle'), 2000);
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

    const handleToggleHighlightLastEvent = useCallback(() => {
        if (currentMatch.events.length === 0) return;
        const sorted = [...currentMatch.events].sort((a, b) => a.start - b.start || a.end - b.end);
        const lastIndex = sorted.length - 1;
        sorted[lastIndex] = { ...sorted[lastIndex], isHighlight: !sorted[lastIndex].isHighlight };
        autoSave(sorted);
    }, [currentMatch.events, autoSave]);

    const handleSetTimeoutLastEvent = useCallback((player: 'player1' | 'player2') => {
        if (currentMatch.events.length === 0) return;
        const sorted = [...currentMatch.events].sort((a, b) => a.start - b.start || a.end - b.end);
        const lastIndex = sorted.length - 1;
        const targetPlayer = player === 'player1' ? currentMatch.player1 : currentMatch.player2;
        const newTimeout = sorted[lastIndex].timeout_player === targetPlayer ? null : targetPlayer;
        sorted[lastIndex] = { ...sorted[lastIndex], timeout_player: newTimeout };
        autoSave(sorted);
    }, [currentMatch.events, currentMatch.player1, currentMatch.player2, autoSave]);

    // Attach shortcuts hook
    useKeyboardShortcuts({
        isActive: true,
        currentMatch,
        videoRef,
        pendingStartTime,
        setPendingStartTime,
        activeGame: 1,
        onAddEvent: handleAddEvent,
        onUndoEvent: handleUndoEvent,
        onToggleHighlightLastEvent: handleToggleHighlightLastEvent,
        onSetTimeoutLastEvent: handleSetTimeoutLastEvent
    });

    const handleSeek = (time: number) => {
        if (videoRef.current && videoRef.current.src) {
            const currentRate = videoRef.current.playbackRate;
            videoRef.current.currentTime = time;
            videoRef.current.playbackRate = currentRate;
            videoRef.current.play().catch(() => {});
        }
    };

    const handleToggleHighlight = (index: number, isHighlight: boolean) => {
        const sorted = [...currentMatch.events].sort((a, b) => a.start - b.start || a.end - b.end);
        if (sorted[index]) {
            sorted[index] = { ...sorted[index], isHighlight };
            autoSave(sorted);
        }
    };

    const handleUpdateTimeout = (index: number, timeoutPlayer: string | null) => {
        const sorted = [...currentMatch.events].sort((a, b) => a.start - b.start || a.end - b.end);
        if (sorted[index]) {
            sorted[index] = { ...sorted[index], timeout_player: timeoutPlayer };
            autoSave(sorted);
        }
    };

    const handleUpdateEventTimestamp = (index: number, newStart: number, newEnd: number, newWinner?: string | null) => {
        const sorted = [...currentMatch.events].sort((a, b) => a.start - b.start || a.end - b.end);
        if (sorted[index]) {
            sorted[index] = {
                ...sorted[index],
                start: newStart,
                end: newEnd,
                winner: newWinner !== undefined ? newWinner : sorted[index].winner
            };
            sorted.sort((a, b) => a.start - b.start || a.end - b.end);
            autoSave(sorted);
        }
    };

    const handleDeleteEvent = (index: number) => {
        const sorted = [...currentMatch.events].sort((a, b) => a.start - b.start || a.end - b.end);
        const updated = sorted.filter((_, i) => i !== index);
        autoSave(updated);
    };

    const handleCreateRender = async (
        type: 'full_match' | 'highlights',
        label: string,
        options: RenderOptions
    ) => {
        setIsRenderingJob(true);
        try {
            const newJob = await createRenderJob(currentMatch.id, type, label, options);
            const updatedRenders = [...(currentMatch.renders || []), newJob];
            onMatchUpdated({
                ...currentMatch,
                renders: updatedRenders
            });
        } catch (err: any) {
            alert(err.message || 'Failed to start render job.');
        } finally {
            setIsRenderingJob(false);
        }
    };

    const handleDeleteRender = async (renderId: string) => {
        if (!window.confirm('Are you sure you want to delete this rendered video?')) return;
        try {
            await deleteRenderJob(currentMatch.id, renderId);
            const updatedRenders = (currentMatch.renders || []).filter(r => r.id !== renderId);
            onMatchUpdated({
                ...currentMatch,
                renders: updatedRenders
            });
            if (activePreviewUrl) {
                const deleted = currentMatch.renders?.find(r => r.id === renderId);
                if (deleted && deleted.video_url === activePreviewUrl) {
                    setActiveVideoSrc(rawVideoUrl);
                    setActivePreviewUrl(null);
                }
            }
        } catch (err: any) {
            alert(err.message || 'Failed to delete render job.');
        }
    };

    const handleCancelRender = async (renderId: string) => {
        try {
            await cancelRenderJob(currentMatch.id, renderId);
            const renders = await fetchMatchRenders(currentMatch.id);
            onMatchUpdated({
                ...currentMatch,
                renders
            });
        } catch (err: any) {
            alert(err.message || 'Failed to cancel render job.');
        }
    };

    const handlePreviewRender = (videoUrl: string) => {
        setActiveVideoSrc(videoUrl);
        setActivePreviewUrl(videoUrl);
    };

    const handleResetToOriginalVideo = () => {
        setActiveVideoSrc(rawVideoUrl);
        setActivePreviewUrl(null);
    };

    const handleBackClick = () => {
        if (videoRef.current) {
            videoRef.current.pause();
            videoRef.current.src = '';
        }
        onBack();
    };

    const handleSaveMetadata = async (updates: { name?: string; player1?: string; player2?: string; first_server?: 'player1' | 'player2' }) => {
        const updated = await updateMatch(currentMatch.id, updates);
        onMatchUpdated(updated);
    };

    return (
        <div className="workspace-view">
            <WorkspaceHeader
                currentMatch={currentMatch}
                onBack={handleBackClick}
                onSaveMetadata={handleSaveMetadata}
                onLogout={onLogout}
            />

            <div className="workspace-grid">
                <div className="workspace-left">
                    <VideoSection ref={videoRef} src={activeVideoSrc} />
                    <StatusPanel pendingStartTime={pendingStartTime} />
                    <RenderHistory
                        renders={currentMatch.renders || []}
                        onPreviewRender={handlePreviewRender}
                        onDeleteRender={handleDeleteRender}
                        onCancelRender={handleCancelRender}
                        activePreviewUrl={activePreviewUrl}
                        onResetToOriginalVideo={handleResetToOriginalVideo}
                    />
                    <MatchStatsView
                        match={currentMatch}
                        onJumpToTime={handleSeek}
                    />
                </div>
                <div className="workspace-right">
                    <FirstServerCard
                        currentMatch={currentMatch}
                        onFirstServerChange={async (fs: 'player1' | 'player2') => {
                            try {
                                const updated = await updateMatch(currentMatch.id, { first_server: fs });
                                onMatchUpdated(updated);
                            } catch (err) {
                                console.error('Failed to update first server:', err);
                            }
                        }}
                    />
                    <SidebarLogs
                        currentMatch={currentMatch}
                        onSeek={handleSeek}
                        onToggleHighlight={handleToggleHighlight}
                        onUpdateTimeout={handleUpdateTimeout}
                        onUpdateEventTimestamp={handleUpdateEventTimestamp}
                        onDeleteEvent={handleDeleteEvent}
                        onSaveEvents={() => autoSave(currentMatch.events)}
                        saveStatus={saveStatus}
                        getCurrentVideoTime={() => videoRef.current?.currentTime || 0}
                    />
                    <RenderOptionsForm
                        onSubmit={handleCreateRender}
                        hasHighlights={currentMatch.events.some(e => e.isHighlight)}
                        isRendering={isRenderingJob}
                        player1={currentMatch.player1}
                        player2={currentMatch.player2}
                    />
                </div>
            </div>
        </div>
    );
};
