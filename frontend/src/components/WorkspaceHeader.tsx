import React from 'react';
import { Match } from '../types';
import { ArrowLeft, LogOut } from 'lucide-react';
import { Button } from './ui';

interface WorkspaceHeaderProps {
    currentMatch: Match;
    onBack: () => void;
    onLogout?: () => void;
}

export const WorkspaceHeader: React.FC<WorkspaceHeaderProps> = ({ currentMatch, onBack, onLogout }) => {
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
                <h1 className="workspace-title">{currentMatch.name} Workspace</h1>
                <span className="workspace-subtitle">
                    {currentMatch.player1} <span className="vs">vs</span> {currentMatch.player2}
                </span>
            </div>
            {onLogout && (
                <Button
                    variant="signout"
                    size="sm"
                    icon={<LogOut size={15} />}
                    onClick={onLogout}
                    title="Sign Out of Beta Session"
                >
                    Sign Out
                </Button>
            )}
        </header>
    );
};
