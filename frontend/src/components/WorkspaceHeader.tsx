import React from 'react';
import { Match } from '../types';
import { ArrowLeft, LogOut, Edit3 } from 'lucide-react';
import { Button } from './ui';

interface WorkspaceHeaderProps {
    currentMatch: Match;
    onBack: () => void;
    onLogout?: () => void;
    onOpenEditModal?: () => void;
}

export const WorkspaceHeader: React.FC<WorkspaceHeaderProps> = ({ currentMatch, onBack, onLogout, onOpenEditModal }) => {
    return (
        <header className="workspace-header">
            <Button
                variant="secondary"
                size="sm"
                icon={<ArrowLeft size={16} />}
                onClick={onBack}
            >
                Matches
            </Button>
            <div className="title-wrapper">
                <div className="title-with-edit">
                    <h1 className="workspace-title">{currentMatch.name} Workspace</h1>
                    {onOpenEditModal && (
                        <button
                            type="button"
                            className="edit-metadata-btn"
                            onClick={onOpenEditModal}
                            title="Edit Match Title & Player Names"
                        >
                            <Edit3 size={16} /> Edit
                        </button>
                    )}
                </div>
                <span className="workspace-subtitle">
                    {currentMatch.player1} <span className="vs">vs</span> {currentMatch.player2}
                </span>
            </div>
            {onLogout && (
                <div className="header-actions">
                    <Button
                        variant="signout"
                        size="sm"
                        icon={<LogOut size={15} />}
                        onClick={onLogout}
                        title="Sign Out of Beta Session"
                    >
                        Sign Out
                    </Button>
                </div>
            )}
        </header>
    );
};
