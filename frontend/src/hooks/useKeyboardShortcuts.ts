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
}

export function useKeyboardShortcuts({
    isActive,
    currentMatch,
    videoRef,
    pendingStartTime,
    setPendingStartTime,
    activeGame,
    onAddEvent,
    onUndoEvent
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
            } else if (key === '1' || key === 'a' || key === '2' || key === 's') {
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
                    game: activeGame,
                    score_before: "0-0"
                };

                onAddEvent(newEvent);
                setPendingStartTime(null);
            } else if (key === 'z') {
                onUndoEvent();
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
        onUndoEvent
    ]);
}
