import React from 'react';
import { Disc } from 'lucide-react';
import { Match } from '../types';

interface FirstServerCardProps {
    currentMatch: Match;
    onFirstServerChange: (firstServer: 'player1' | 'player2') => Promise<void>;
}

export const FirstServerCard: React.FC<FirstServerCardProps> = ({
    currentMatch,
    onFirstServerChange
}) => {
    const p1 = currentMatch.player1 || 'Player 1';
    const p2 = currentMatch.player2 || 'Player 2';
    const activeServer = currentMatch.first_server || 'player1';

    return (
        <section className="first-server-card card compact-single-row">
            <div className="single-row-content">
                <div className="row-label-left">
                    <Disc className="accent-icon" size={16} />
                    <span className="card-row-title">Game 1 Server</span>
                </div>

                <div className="server-toggle-pill-compact">
                    <button
                        type="button"
                        className={`chip-toggle server-compact-btn ${activeServer === 'player1' ? 'active' : ''}`}
                        onClick={() => onFirstServerChange('player1')}
                    >
                        🏓 {p1}
                    </button>
                    <button
                        type="button"
                        className={`chip-toggle server-compact-btn ${activeServer === 'player2' ? 'active' : ''}`}
                        onClick={() => onFirstServerChange('player2')}
                    >
                        🏓 {p2}
                    </button>
                </div>
            </div>
        </section>
    );
};
