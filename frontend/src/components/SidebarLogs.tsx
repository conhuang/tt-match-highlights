import React from 'react';
import { Match } from '../types';
import { Trash2, Star, Save, Film } from 'lucide-react';

interface SidebarLogsProps {
    currentMatch: Match;
    activeGame: number;
    onChangeActiveGame: (game: number) => void;
    onSeek: (time: number) => void;
    onToggleHighlight: (index: number, isHighlight: boolean) => void;
    onUpdateTimeout: (index: number, timeoutPlayer: string | null) => void;
    onDeleteEvent: (index: number) => void;
    onSaveEvents: () => void;
    saveStatus: 'idle' | 'saving' | 'saved' | 'failed';
    onOpenRenderModal: () => void;
}

function formatTime(seconds: number): string {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 10);
    const pad = (num: number) => num.toString().padStart(2, '0');
    return `${pad(m)}:${pad(s)}.${ms}`;
}

export const SidebarLogs: React.FC<SidebarLogsProps> = ({
    currentMatch,
    activeGame,
    onChangeActiveGame,
    onSeek,
    onToggleHighlight,
    onUpdateTimeout,
    onDeleteEvent,
    onSaveEvents,
    saveStatus,
    onOpenRenderModal
}) => {
    const events = [...currentMatch.events].sort((a, b) => a.start - b.start);

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

                        return (
                            <div key={`${event.start}-${index}`} className="event-card">
                                <div className="event-card-header">
                                    <button
                                        type="button"
                                        className="time-link-btn"
                                        onClick={() => onSeek(event.start)}
                                    >
                                        {formatTime(event.start)} - {formatTime(event.end)}
                                    </button>
                                    <span className={`event-winner ${isP1 ? 'p1' : 'p2'}`}>
                                        {event.winner} Wins Point
                                    </span>
                                </div>

                                <div className="event-details">
                                    <span className="event-score-info">
                                        Game {event.game} • Score: {event.score_before}
                                    </span>

                                    <div className="event-inputs">
                                        <label className="checkbox-label">
                                            <input
                                                type="checkbox"
                                                checked={event.isHighlight}
                                                onChange={(e) => onToggleHighlight(index, e.target.checked)}
                                            />
                                            <Star size={12} className={event.isHighlight ? 'star-active' : ''} />
                                            Highlight
                                        </label>

                                        <label className="timeout-label">
                                            TO:
                                            <select
                                                value={event.timeout_player || ''}
                                                onChange={(e) => onUpdateTimeout(index, e.target.value || null)}
                                            >
                                                <option value="">None</option>
                                                <option value={currentMatch.player1}>P1</option>
                                                <option value={currentMatch.player2}>P2</option>
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
                <button
                    type="button"
                    className="primary-btn"
                    onClick={onSaveEvents}
                    disabled={saveStatus === 'saving'}
                >
                    <Save size={16} />
                    {saveStatus === 'saving' ? 'Saving...' : saveStatus === 'saved' ? 'Saved ✓' : 'Save Events'}
                </button>
                <button
                    type="button"
                    className="secondary-btn render-trigger-btn"
                    onClick={onOpenRenderModal}
                    title="Render scored match or highlights reel"
                >
                    <Film size={16} />
                    Render Highlights
                </button>
            </div>
        </div>
    );
};
