import React from 'react';
import { Match } from '../types';
import { Trash2, Video, Calendar, Trophy } from 'lucide-react';

interface MatchesListProps {
    matches: Match[];
    onSelectMatch: (matchId: string) => void;
    onDeleteMatch: (matchId: string) => void;
}

export const MatchesList: React.FC<MatchesListProps> = ({ matches, onSelectMatch, onDeleteMatch }) => {
    if (matches.length === 0) {
        return <p className="empty-state">No matches uploaded yet. Create one above to get started!</p>;
    }

    return (
        <div className="matches-list">
            {matches.map((match) => {
                const isReady = Boolean(match.video_filename);
                const dateStr = new Date(match.created_at).toLocaleDateString(undefined, {
                    month: 'short',
                    day: 'numeric',
                    year: 'numeric'
                });

                return (
                    <div
                        key={match.id}
                        className="match-item"
                        onClick={() => onSelectMatch(match.id)}
                    >
                        <div className="match-info">
                            <div className="match-title-row">
                                <Trophy size={16} className="match-icon" />
                                <span className="match-title">{match.name}</span>
                            </div>
                            <span className="match-players">
                                {match.player1} <span className="vs">vs</span> {match.player2}
                            </span>
                            <span className="match-date">
                                <Calendar size={12} /> {dateStr}
                            </span>
                        </div>

                        <div className="match-meta">
                            <span className={`match-status ${isReady ? 'status-ready' : 'status-uploading'}`}>
                                <Video size={12} /> {isReady ? 'Ready' : 'Uploading'}
                            </span>
                            <button
                                type="button"
                                className="delete-btn"
                                onClick={(e) => {
                                    e.stopPropagation();
                                    onDeleteMatch(match.id);
                                }}
                                title="Delete Match"
                            >
                                <Trash2 size={16} />
                            </button>
                        </div>
                    </div>
                );
            })}
        </div>
    );
};
