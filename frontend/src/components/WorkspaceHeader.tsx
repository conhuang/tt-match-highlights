import React, { useState, useEffect } from 'react';
import { Match } from '../types';
import { ArrowLeft, LogOut, Edit3, Check, X } from 'lucide-react';
import { Button } from './ui';

interface WorkspaceHeaderProps {
    currentMatch: Match;
    onBack: () => void;
    onSaveMetadata: (updates: { name?: string; player1?: string; player2?: string }) => Promise<void>;
    onLogout?: () => void;
}

export const WorkspaceHeader: React.FC<WorkspaceHeaderProps> = ({ currentMatch, onBack, onSaveMetadata, onLogout }) => {
    const [isEditing, setIsEditing] = useState<boolean>(false);
    const [name, setName] = useState<string>(currentMatch.name || '');
    const [player1, setPlayer1] = useState<string>(currentMatch.player1 || '');
    const [player2, setPlayer2] = useState<string>(currentMatch.player2 || '');
    const [isSaving, setIsSaving] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        setName(currentMatch.name || '');
        setPlayer1(currentMatch.player1 || '');
        setPlayer2(currentMatch.player2 || '');
    }, [currentMatch]);

    const handleSave = async () => {
        if (!name.trim()) {
            setError('Match title cannot be empty.');
            return;
        }
        if (!player1.trim() || !player2.trim()) {
            setError('Player names cannot be empty.');
            return;
        }
        if (player1.trim().toLowerCase() === player2.trim().toLowerCase()) {
            setError('Player names must be distinct.');
            return;
        }

        try {
            setIsSaving(true);
            setError(null);
            await onSaveMetadata({
                name: name.trim(),
                player1: player1.trim(),
                player2: player2.trim()
            });
            setIsEditing(false);
        } catch (err: any) {
            setError(err.message || 'Failed to update match details.');
        } finally {
            setIsSaving(false);
        }
    };

    const handleCancel = () => {
        setName(currentMatch.name || '');
        setPlayer1(currentMatch.player1 || '');
        setPlayer2(currentMatch.player2 || '');
        setError(null);
        setIsEditing(false);
    };

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
                {!isEditing ? (
                    <div className="title-with-edit">
                        <div className="header-text-block">
                            <h1 className="workspace-title">{currentMatch.name} Workspace</h1>
                            <span className="workspace-subtitle">
                                {currentMatch.player1} <span className="vs">vs</span> {currentMatch.player2}
                            </span>
                        </div>
                        <button
                            type="button"
                            className="edit-metadata-btn"
                            onClick={() => setIsEditing(true)}
                            title="Edit Match Title & Player Names Inline"
                        >
                            <Edit3 size={15} /> Edit
                        </button>
                    </div>
                ) : (
                    <div className="inline-header-editor">
                        {error && <div className="header-inline-error">{error}</div>}
                        <div className="inline-editor-inputs">
                            <input
                                type="text"
                                className="inline-name-input"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                placeholder="Match Title"
                            />
                            <div className="inline-players-row">
                                <input
                                    type="text"
                                    className="inline-player-input"
                                    value={player1}
                                    onChange={(e) => setPlayer1(e.target.value)}
                                    placeholder="Player 1"
                                />
                                <span className="vs">vs</span>
                                <input
                                    type="text"
                                    className="inline-player-input"
                                    value={player2}
                                    onChange={(e) => setPlayer2(e.target.value)}
                                    placeholder="Player 2"
                                />
                            </div>
                        </div>
                        <div className="inline-editor-actions">
                            <button
                                type="button"
                                className="save-inline-btn"
                                onClick={handleSave}
                                disabled={isSaving}
                                title="Save Title & Names"
                            >
                                <Check size={16} />
                            </button>
                            <button
                                type="button"
                                className="cancel-inline-btn"
                                onClick={handleCancel}
                                disabled={isSaving}
                                title="Cancel"
                            >
                                <X size={16} />
                            </button>
                        </div>
                    </div>
                )}
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
