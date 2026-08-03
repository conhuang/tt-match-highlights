import React from 'react';
import { Match } from '../types';
import { ArrowLeft, LogOut } from 'lucide-react';

interface WorkspaceHeaderProps {
    currentMatch: Match;
    onBack: () => void;
    onLogout?: () => void;
}

export const WorkspaceHeader: React.FC<WorkspaceHeaderProps> = ({ currentMatch, onBack, onLogout }) => {
    return (
        <header className="workspace-header">
            <button className="back-btn" onClick={onBack}>
                <ArrowLeft size={16} /> Matches
            </button>
            <div className="title-wrapper">
                <h1 className="workspace-title">{currentMatch.name} Workspace</h1>
                <span className="workspace-subtitle">
                    {currentMatch.player1} <span className="vs">vs</span> {currentMatch.player2}
                </span>
            </div>
            {onLogout && (
                <button type="button" onClick={onLogout} className="signout-btn" title="Sign Out of Beta Session">
                    <LogOut size={15} />
                    <span>Sign Out</span>
                </button>
            )}
        </header>
    );
};
