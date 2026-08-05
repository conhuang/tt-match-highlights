import React, { useState } from 'react';
import { Match } from '../types';
import { Trash2, Star, Save, Film, Download, Edit2, Check, Clock, X } from 'lucide-react';
import { Button } from './ui';
import { computeScoresAndGames } from '../utils/scoring';
import { exportEventsToCSV } from '../utils/csvExporter';

interface SidebarLogsProps {
    currentMatch: Match;
    activeGame: number;
    onChangeActiveGame: (game: number) => void;
    onSeek: (time: number) => void;
    onToggleHighlight: (index: number, isHighlight: boolean) => void;
    onUpdateTimeout: (index: number, timeoutPlayer: string | null) => void;
    onUpdateEventTimestamp?: (index: number, newStart: number, newEnd: number, newWinner?: string | null) => void;
    onDeleteEvent: (index: number) => void;
    onSaveEvents: () => void;
    saveStatus: 'idle' | 'saving' | 'saved' | 'failed';
    onOpenRenderModal: () => void;
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
    activeGame,
    onChangeActiveGame,
    onSeek,
    onToggleHighlight,
    onUpdateTimeout,
    onUpdateEventTimestamp,
    onDeleteEvent,
    onSaveEvents,
    saveStatus,
    onOpenRenderModal,
    getCurrentVideoTime
}) => {
    const events = computeScoresAndGames(currentMatch.events, currentMatch.player1, currentMatch.player2);
    const [editingIndex, setEditingIndex] = useState<number | null>(null);
    const [editStart, setEditStart] = useState<string>('');
    const [editEnd, setEditEnd] = useState<string>('');
    const [editWinner, setEditWinner] = useState<string | null>(null);

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
        const s = parseTimeString(editStart);
        const e = parseTimeString(editEnd);
        if (isNaN(s) || isNaN(e) || s < 0 || e <= s) {
            alert('End time must be greater than start time. Enter formatted MM:SS.s (e.g. 01:15.5) or seconds.');
            return;
        }
        if (onUpdateEventTimestamp) {
            onUpdateEventTimestamp(index, s, e, editWinner);
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
        <div className="workspace-right">
            <div className="sidebar-header">
                <h2>Point Logs ({events.length})</h2>
                <div className="game-selector">
                    <label htmlFor="active-game">Game:</label>
                    <input
                        type="number"
                        id="active-game"
                        min="1"
                        max="9"
                        value={activeGame}
                        onChange={(e) => onChangeActiveGame(parseInt(e.target.value) || 1)}
                    />
                </div>
            </div>

            <div className="events-list">
                {events.length === 0 ? (
                    <p className="empty-state">
                        No points logged yet. Use <strong>E</strong>/<strong>D</strong> to mark start time, then <strong>1</strong>/<strong>2</strong> to log point winners.
                    </p>
                ) : (
                    events.map((event, index) => {
                        const isP1 = event.winner === currentMatch.player1;
                        const isP2 = event.winner === currentMatch.player2;
                        const isEditing = editingIndex === index;

                        return (
                            <div key={`${event.start}-${index}`} className="event-card">
                                <div className="event-card-header">
                                    {!isEditing ? (
                                        <div className="time-link-container">
                                            <button
                                                type="button"
                                                className="time-link-btn"
                                                onClick={() => onSeek(event.start)}
                                            >
                                                {formatTime(event.start)} - {formatTime(event.end)}
                                            </button>
                                        </div>
                                    ) : (
                                        <div className="timestamp-edit-controls">
                                            <div className="edit-controls-row">
                                                <div className="edit-time-group">
                                                    {getCurrentVideoTime ? (
                                                        <button
                                                            type="button"
                                                            className="capture-time-btn"
                                                            onClick={handleSetStartCurrentTime}
                                                            title="Click to set Start time to current video playback time"
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
                                                            title="Click to set End time to current video playback time"
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

                                            <div className="edit-controls-row">
                                                <div className="edit-time-group edit-winner-select-group">
                                                    <label>Winner:</label>
                                                    <select
                                                        value={editWinner || ''}
                                                        onChange={(e) => setEditWinner(e.target.value || null)}
                                                        className="edit-winner-select"
                                                    >
                                                        <option value={currentMatch.player1}>{currentMatch.player1}</option>
                                                        <option value={currentMatch.player2}>{currentMatch.player2}</option>
                                                        <option value="">No Winner (Clip Only)</option>
                                                    </select>
                                                </div>

                                                <div className="edit-action-btns">
                                                    <button
                                                        type="button"
                                                        className="save-timestamp-btn"
                                                        onClick={() => saveEditing(index)}
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

                                    {!isEditing && (
                                        <div className="event-winner-wrapper">
                                            <span className={`event-winner ${isP1 ? 'p1' : isP2 ? 'p2' : 'none'}`}>
                                                {event.winner ? `${event.winner} Wins Point` : 'No Winner'}
                                            </span>
                                            <button
                                                type="button"
                                                className="icon-btn edit-timestamp-btn"
                                                onClick={() => startEditing(index, event.start, event.end, event.winner)}
                                                title="Edit Event Details"
                                            >
                                                <Edit2 size={12} />
                                            </button>
                                        </div>
                                    )}
                                </div>

                                <div className="event-details">
                                    <span className="event-score-info">
                                        Game {event.game} • Score: {event.score_before}
                                    </span>

                                    <div className="event-inputs">
                                        <button
                                            type="button"
                                            className={`highlight-toggle-btn ${event.isHighlight ? 'active' : ''}`}
                                            onClick={() => onToggleHighlight(index, !event.isHighlight)}
                                            title={event.isHighlight ? "Click to remove highlight" : "Click to mark this point as a highlight"}
                                        >
                                            <Star size={14} className={event.isHighlight ? 'star-active' : ''} />
                                        </button>

                                        <label className="timeout-label">
                                            TO:
                                            <select
                                                value={event.timeout_player || ''}
                                                onChange={(e) => onUpdateTimeout(index, e.target.value || null)}
                                            >
                                                <option value="">None</option>
                                                <option value={currentMatch.player1}>{currentMatch.player1}</option>
                                                <option value={currentMatch.player2}>{currentMatch.player2}</option>
                                            </select>
                                        </label>

                                        <button
                                            type="button"
                                            className="event-delete-btn"
                                            onClick={() => onDeleteEvent(index)}
                                            title="Delete Point Log"
                                        >
                                            <Trash2 size={14} />
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
                    style={{ flex: 1.4 }}
                >
                    {saveStatus === 'saving' ? 'Saving...' : saveStatus === 'saved' ? 'Saved ✓' : 'Save Events'}
                </Button>
                <Button
                    variant="secondary"
                    icon={<Download size={16} />}
                    className="download-csv-btn"
                    onClick={() => exportEventsToCSV(currentMatch)}
                    disabled={events.length === 0}
                    title="Export point logs and rally details to CSV"
                    style={{ flex: 1 }}
                >
                    Export CSV
                </Button>
                <Button
                    variant="render"
                    icon={<Film size={16} />}
                    onClick={onOpenRenderModal}
                    title="Render scored match or highlights reel"
                    style={{ flex: 1 }}
                >
                    Render Highlights
                </Button>
            </div>
        </div>
    );
};
