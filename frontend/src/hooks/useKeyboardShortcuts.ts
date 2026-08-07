import { useEffect, RefObject } from 'react';
import { Match, MatchEvent } from '../types';

interface KeyboardShortcutsOptions {
    isActive: boolean;
    currentMatch: Match | null;
    videoRef: RefObject<HTMLVideoElement | null>;
    pendingStartTime: number | null;
    setPendingStartTime: (time: number | null) => void;
    activeGame: number;
    onAddEvent: (newEvent: MatchEvent) => void;
    onUndoEvent: () => void;
    onToggleHighlightLastEvent?: () => void;
    onSetTimeoutLastEvent?: (player: 'player1' | 'player2') => void;
}

export function useKeyboardShortcuts({
    isActive,
    currentMatch,
    videoRef,
    pendingStartTime,
    setPendingStartTime,
    activeGame,
    onAddEvent,
    onUndoEvent,
    onToggleHighlightLastEvent,
    onSetTimeoutLastEvent
}: KeyboardShortcutsOptions) {
    useEffect(() => {
        if (!isActive || !currentMatch) return;

        const handleKeyDown = (e: KeyboardEvent) => {
            const activeEl = document.activeElement;
            if (
                activeEl &&
                (activeEl.tagName === 'INPUT' ||
                 activeEl.tagName === 'TEXTAREA' ||
                 activeEl.tagName === 'SELECT')
            ) {
                return;
            }

            const key = e.key.toLowerCase();
            const video = videoRef.current;

            if (e.key === ' ') {
                e.preventDefault();
                if (video && video.src) {
                    if (video.paused) {
                        video.play().catch(() => {});
                    } else {
                        video.pause();
                    }
                }
            } else if (key === 'e' || key === 'd') {
                if (video) {
                    const time = parseFloat(video.currentTime.toFixed(2));
                    setPendingStartTime(time);
                }
            } else if ((key === '1' || key === 'a' || key === '2' || key === 's') && !e.shiftKey && e.key !== '!' && e.key !== '@') {
                if (pendingStartTime === null) {
                    alert("Please mark the Start Time first using 'E' or 'D'.");
                    return;
                }

                if (!video) return;

                const endTime = parseFloat(video.currentTime.toFixed(2));
                if (endTime <= pendingStartTime) {
                    alert("End time must be greater than start time.");
                    return;
                }

                const winnerName = (key === '1' || key === 'a') ? currentMatch.player1 : currentMatch.player2;

                const newEvent: MatchEvent = {
                    start: pendingStartTime,
                    end: endTime,
                    winner: winnerName,
                    timeout_player: null,
                    isHighlight: false,
                    game: activeGame
                };

                onAddEvent(newEvent);
                setPendingStartTime(null);
            } else if (key === 'z') {
                onUndoEvent();
            } else if (key === 'h') {
                if (onToggleHighlightLastEvent) {
                    onToggleHighlightLastEvent();
                }
            } else if ((e.shiftKey && (e.key === '1' || e.key === '!')) || (e.shiftKey && (e.key === '2' || e.key === '@'))) {
                if (onSetTimeoutLastEvent) {
                    const player = (e.key === '1' || e.key === '!') ? 'player1' : 'player2';
                    onSetTimeoutLastEvent(player);
                }
            } else if (e.key === 'ArrowLeft' || key === ',' || e.key === 'ArrowRight' || key === '.' || e.key === 'ArrowUp' || e.key === 'ArrowDown') {
                if (video) {
                    e.preventDefault();
                    let delta = 0;
                    if (e.key === 'ArrowLeft' || key === ',') {
                        delta = e.shiftKey ? -0.1 : -2.0;
                    } else if (e.key === 'ArrowRight' || key === '.') {
                        delta = e.shiftKey ? 0.1 : 2.0;
                    } else if (e.key === 'ArrowUp') {
                        delta = 60.0;
                    } else if (e.key === 'ArrowDown') {
                        delta = -60.0;
                    }

                    const currentRate = video.playbackRate;
                    const wasPlaying = !video.paused;
                    const targetTime = Math.max(0, Math.min(video.duration || Infinity, video.currentTime + delta));
                    video.currentTime = targetTime;
                    video.playbackRate = currentRate;
                    if (wasPlaying) {
                        video.play().catch(() => {});
                    }
                }
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [
        isActive,
        currentMatch,
        videoRef,
        pendingStartTime,
        setPendingStartTime,
        activeGame,
        onAddEvent,
        onUndoEvent,
        onToggleHighlightLastEvent,
        onSetTimeoutLastEvent
    ]);
}
