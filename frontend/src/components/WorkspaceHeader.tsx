import React from 'react';
import { Match } from '../types';
import { ArrowLeft } from 'lucide-react';

interface WorkspaceHeaderProps {
    currentMatch: Match;
    onBack: () => void;
    onOpenRenderModal?: () => void;
}

export const WorkspaceHeader: React.FC<WorkspaceHeaderProps> = ({ currentMatch, onBack, onOpenRenderModal }) => {
    return (
        <header className="workspace-header">
            <button className="back-btn" onClick={onBack}>
                <ArrowLeft size={16} /> Dashboard
            </button>
            <div className="title-wrapper">
                <h1 className="workspace-title">{currentMatch.name} Workspace</h1>
                <span className="workspace-subtitle">
                    {currentMatch.player1} <span className="vs">vs</span> {currentMatch.player2}
                </span>
            </div>
            {onOpenRenderModal && (
                <button className="btn btn-primary btn-sm render-header-btn" onClick={onOpenRenderModal}>
                    🎬 Render Video
                </button>
            )}
        </header>
    );
};
