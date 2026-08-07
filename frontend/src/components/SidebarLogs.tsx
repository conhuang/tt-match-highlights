import React, { useState } from 'react';
import { Match } from '../types';
import { Trash2, Star, Edit3, Check, Clock, X, ArrowUpDown, Download, Save } from 'lucide-react';
import { Button } from './ui';
import { computeScoresAndGames } from '../utils/scoring';
import { exportEventsToCSV } from '../utils/csvExporter';

interface SidebarLogsProps {
    currentMatch: Match;
    onSeek: (time: number) => void;
    onToggleHighlight: (index: number, isHighlight: boolean) => void;
    onUpdateTimeout: (index: number, timeoutPlayer: string | null) => void;
    onUpdateEventTimestamp?: (index: number, newStart: number, newEnd: number, newWinner?: string | null) => void;
    onDeleteEvent: (index: number) => void;
    onSaveEvents?: () => void;
    saveStatus?: 'idle' | 'saving' | 'saved' | 'failed';
    getCurrentVideoTime?: () => number;
}

function formatTime(seconds: number): string {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 10);
    const pad = (num: number) => num.toString().padStart(2, '0');
    return `${pad(m)}:${pad(s)}.${ms}`;
}

function parseTimeString(str: string): number {
    const trimmed = str.trim();
    if (!trimmed) return NaN;
    if (trimmed.includes(':')) {
        const parts = trimmed.split(':');
        if (parts.length === 2) {
            const minutes = parseFloat(parts[0]);
            const seconds = parseFloat(parts[1]);
            if (!isNaN(minutes) && !isNaN(seconds)) {
                return minutes * 60 + seconds;
            }
        } else if (parts.length === 3) {
            const hours = parseFloat(parts[0]);
            const minutes = parseFloat(parts[1]);
            const seconds = parseFloat(parts[2]);
            if (!isNaN(hours) && !isNaN(minutes) && !isNaN(seconds)) {
                return hours * 3600 + minutes * 60 + seconds;
            }
        }
    }
    return parseFloat(trimmed);
}

export const SidebarLogs: React.FC<SidebarLogsProps> = ({
    currentMatch,
    onSeek,
    onToggleHighlight,
    onUpdateTimeout,
    onUpdateEventTimestamp,
    onDeleteEvent,
    onSaveEvents,
    saveStatus = 'idle',
    getCurrentVideoTime
}) => {
    const rawEvents = computeScoresAndGames(currentMatch.events, currentMatch.player1, currentMatch.player2);
    const [isReversed, setIsReversed] = useState<boolean>(false);
    const [editingIndex, setEditingIndex] = useState<number | null>(null);
    const [editStart, setEditStart] = useState<string>('');
    const [editEnd, setEditEnd] = useState<string>('');
    const [editWinner, setEditWinner] = useState<string | null>(null);

    const displayEvents = rawEvents.map((event, originalIndex) => ({ event, originalIndex }));
    if (isReversed) {
        displayEvents.reverse();
    }

    const startEditing = (index: number, start: number, end: number, winner?: string | null) => {
        setEditingIndex(index);
        setEditStart(formatTime(start));
        setEditEnd(formatTime(end));
        setEditWinner(winner || null);
    };

    const cancelEditing = () => {
        setEditingIndex(null);
    };

    const saveEditing = (index: number) => {
        const startSec = parseTimeString(editStart);
        const endSec = parseTimeString(editEnd);

        if (isNaN(startSec) || isNaN(endSec)) {
            alert('Please enter valid timestamps in MM:SS.s format.');
            return;
        }

        if (endSec <= startSec) {
            alert('End timestamp must be strictly after Start timestamp.');
            return;
        }

        if (onUpdateEventTimestamp) {
            onUpdateEventTimestamp(index, startSec, endSec, editWinner);
        }
        setEditingIndex(null);
    };

    const handleSetStartCurrentTime = () => {
        if (getCurrentVideoTime) {
            setEditStart(formatTime(getCurrentVideoTime()));
        }
    };

    const handleSetEndCurrentTime = () => {
        if (getCurrentVideoTime) {
            setEditEnd(formatTime(getCurrentVideoTime()));
        }
    };

    return (
        <div className="sidebar-logs-card">
            <div className="sidebar-header">
                <h2>Point Logs ({rawEvents.length})</h2>
                <button
                    type="button"
                    className={`reverse-order-btn ${isReversed ? 'active' : ''}`}
                    onClick={() => setIsReversed(!isReversed)}
                    title={isReversed ? "Click to view Oldest First" : "Click to view Newest First"}
                >
                    <ArrowUpDown size={13} />
                    <span>{isReversed ? 'Newest First' : 'Oldest First'}</span>
                </button>
            </div>

            <div className="events-list">
                {displayEvents.length === 0 ? (
                    <p className="empty-state">
                        No points logged yet. Use <strong>E</strong>/<strong>D</strong> to mark start time, then <strong>1</strong>/<strong>2</strong> to log point winners.
                    </p>
                ) : (
                    displayEvents.map(({ event, originalIndex }) => {
                        const isP1 = event.winner === currentMatch.player1;
                        const isP2 = event.winner === currentMatch.player2;
                        const isEditing = editingIndex === originalIndex;

                        return (
                            <div key={`${event.start}-${originalIndex}`} className="event-card">
                                <div className="event-card-header">
                                    {!isEditing ? (
                                        <>
                                            <div className="time-link-container">
                                                <button
                                                    type="button"
                                                    className="time-link-btn"
                                                    onClick={() => onSeek(event.start)}
                                                >
                                                    {formatTime(event.start)} - {formatTime(event.end)}
                                                </button>
                                            </div>
                                            <div className="event-winner-wrapper">
                                                <span className={`event-winner ${isP1 ? 'p1' : isP2 ? 'p2' : 'none'}`}>
                                                    {event.winner ? `${event.winner} Wins Point` : 'No Winner'}
                                                </span>
                                                <button
                                                    type="button"
                                                    className="icon-btn-base edit-timestamp-btn"
                                                    onClick={() => startEditing(originalIndex, event.start, event.end, event.winner)}
                                                    title="Edit Event Details"
                                                >
                                                    <Edit3 size={12} />
                                                </button>
                                            </div>
                                        </>
                                    ) : (
                                        <div className="timestamp-edit-controls stacked">
                                            <div className="edit-time-stack">
                                                <div className="edit-time-group">
                                                    {getCurrentVideoTime ? (
                                                        <button
                                                            type="button"
                                                            className="capture-time-btn"
                                                            onClick={handleSetStartCurrentTime}
                                                            title="Set Start time to current video playback time"
                                                        >
                                                            <Clock size={10} /> Start
                                                        </button>
                                                    ) : (
                                                        <span className="time-btn-label">Start</span>
                                                    )}
                                                    <input
                                                        type="text"
                                                        value={editStart}
                                                        onChange={(e) => setEditStart(e.target.value)}
                                                        className="timestamp-input"
                                                        placeholder="MM:SS.s"
                                                    />
                                                </div>

                                                <div className="edit-time-group">
                                                    {getCurrentVideoTime ? (
                                                        <button
                                                            type="button"
                                                            className="capture-time-btn"
                                                            onClick={handleSetEndCurrentTime}
                                                            title="Set End time to current video playback time"
                                                        >
                                                            <Clock size={10} /> End
                                                        </button>
                                                    ) : (
                                                        <span className="time-btn-label">End</span>
                                                    )}
                                                    <input
                                                        type="text"
                                                        value={editEnd}
                                                        onChange={(e) => setEditEnd(e.target.value)}
                                                        className="timestamp-input"
                                                        placeholder="MM:SS.s"
                                                    />
                                                </div>
                                            </div>

                                            <div className="edit-right-column">
                                                <div className="edit-time-group edit-winner-select-group">
                                                    <label>Winner:</label>
                                                    <select
                                                        value={editWinner || ''}
                                                        onChange={(e) => setEditWinner(e.target.value || null)}
                                                        className="edit-winner-select"
                                                    >
                                                        <option value={currentMatch.player1}>{currentMatch.player1}</option>
                                                        <option value={currentMatch.player2}>{currentMatch.player2}</option>
                                                        <option value="">No Winner</option>
                                                    </select>
                                                </div>

                                                <div className="edit-action-btns">
                                                    <button
                                                        type="button"
                                                        className="save-timestamp-btn"
                                                        onClick={() => saveEditing(originalIndex)}
                                                        title="Save Details"
                                                    >
                                                        <Check size={14} />
                                                    </button>
                                                    <button
                                                        type="button"
                                                        className="cancel-timestamp-btn"
                                                        onClick={cancelEditing}
                                                        title="Cancel Editing"
                                                    >
                                                        <X size={14} />
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    )}
                                </div>

                                <div className="event-details">
                                    <span className="event-score-info">
                                        Game {event.game} • Score: {event.score_before}
                                    </span>
                                    <button
                                        type="button"
                                        className={`icon-btn-base highlight-toggle-btn ${event.isHighlight ? 'active' : ''}`}
                                        onClick={() => onToggleHighlight(originalIndex, !event.isHighlight)}
                                        title={event.isHighlight ? "Click to remove highlight" : "Click to mark this point as a highlight"}
                                    >
                                        <Star size={14} className={event.isHighlight ? 'star-active' : ''} />
                                    </button>
                                    <div className="event-inputs">
                                        <label className="timeout-label" title="Record an ITTF Timeout taken by a player">
                                            <span className="timeout-sublabel">Timeout</span>
                                            <select
                                                value={event.timeout_player || ''}
                                                onChange={(e) => onUpdateTimeout(originalIndex, e.target.value || null)}
                                                className="timeout-select-inline"
                                            >
                                                <option value="">None</option>
                                                <option value={currentMatch.player1}>{currentMatch.player1}</option>
                                                <option value={currentMatch.player2}>{currentMatch.player2}</option>
                                            </select>
                                        </label>

                                        <button
                                            type="button"
                                            className="icon-btn-base delete-event-btn"
                                            onClick={() => onDeleteEvent(originalIndex)}
                                            title="Delete Point Log"
                                        >
                                            <Trash2 size={13} />
                                        </button>
                                    </div>
                                </div>
                            </div>
                        );
                    })
                )}
            </div>

            <div className="workspace-actions">
                <Button
                    variant="primary"
                    icon={<Save size={16} />}
                    onClick={onSaveEvents}
                    disabled={saveStatus === 'saving'}
                    style={{ flex: 1 }}
                >
                    {saveStatus === 'saving' ? 'Saving...' : saveStatus === 'saved' ? 'Saved ✓' : 'Save Events'}
                </Button>
                <Button
                    variant="secondary"
                    icon={<Download size={16} />}
                    className="download-csv-btn"
                    onClick={() => exportEventsToCSV(currentMatch)}
                    disabled={rawEvents.length === 0}
                    title="Export point logs and rally details to CSV"
                    style={{ flex: 1 }}
                >
                    Export CSV
                </Button>
            </div>
        </div>
    );
};
