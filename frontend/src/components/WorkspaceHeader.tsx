import React from 'react';
import { Match } from '../types';
import { ArrowLeft, LogOut } from 'lucide-react';

interface WorkspaceHeaderProps {
    currentMatch: Match;
    onBack: () => void;
    onOpenRenderModal?: () => void;
    onLogout?: () => void;
}

export const WorkspaceHeader: React.FC<WorkspaceHeaderProps> = ({ currentMatch, onBack, onOpenRenderModal, onLogout }) => {
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
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                {onOpenRenderModal && (
                    <button className="btn btn-primary btn-sm render-header-btn" onClick={onOpenRenderModal}>
                        🎬 Render Video
                    </button>
                )}
                {onLogout && (
                    <button
                        onClick={onLogout}
                        className="btn-secondary"
                        style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', padding: '0.4rem 0.8rem', fontSize: '0.8rem' }}
                    >
                        <LogOut size={15} />
                        <span>Sign Out</span>
                    </button>
                )}
            </div>
        </header>
    );
};
