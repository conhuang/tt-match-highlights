import React, { useState, useEffect } from 'react';
import { Match } from '../types';
import { X, Save, Edit3, User, Trophy } from 'lucide-react';

interface EditMatchModalProps {
    isOpen: boolean;
    currentMatch: Match;
    onClose: () => void;
    onSave: (updates: { name?: string; player1?: string; player2?: string; first_server?: 'player1' | 'player2' }) => Promise<void>;
}

export const EditMatchModal: React.FC<EditMatchModalProps> = ({
    isOpen,
    currentMatch,
    onClose,
    onSave
}) => {
    const [name, setName] = useState<string>(currentMatch.name || '');
    const [player1, setPlayer1] = useState<string>(currentMatch.player1 || '');
    const [player2, setPlayer2] = useState<string>(currentMatch.player2 || '');
    const [firstServer, setFirstServer] = useState<'player1' | 'player2'>(currentMatch.first_server || 'player1');
    const [isSaving, setIsSaving] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (isOpen) {
            setName(currentMatch.name || '');
            setPlayer1(currentMatch.player1 || '');
            setPlayer2(currentMatch.player2 || '');
            setFirstServer(currentMatch.first_server || 'player1');
            setError(null);
        }
    }, [isOpen, currentMatch]);

    if (!isOpen) return null;

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
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
            await onSave({
                name: name.trim(),
                player1: player1.trim(),
                player2: player2.trim(),
                first_server: firstServer
            });
            onClose();
        } catch (err: any) {
            setError(err.message || 'Failed to update match details.');
        } finally {
            setIsSaving(false);
        }
    };

    return (
        <div className="modal-backdrop" onClick={onClose}>
            <div className="modal-content edit-match-modal" onClick={(e) => e.stopPropagation()}>
                <div className="modal-header">
                    <div className="modal-title-group">
                        <Edit3 size={20} className="modal-icon" />
                        <h2>Edit Match Details</h2>
                    </div>
                    <button type="button" className="close-btn" onClick={onClose}>
                        <X size={18} />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="modal-body">
                    {error && <div className="auth-error-banner">{error}</div>}

                    <div className="form-group">
                        <label htmlFor="edit-match-name">
                            <Trophy size={14} /> Match Title
                        </label>
                        <input
                            id="edit-match-name"
                            type="text"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            placeholder="e.g. Semi-Finals: Jonsen vs Ryan"
                            required
                        />
                    </div>

                    <div className="form-row">
                        <div className="form-group">
                            <label htmlFor="edit-player1">
                                <User size={14} /> Player 1 Name
                            </label>
                            <input
                                id="edit-player1"
                                type="text"
                                value={player1}
                                onChange={(e) => setPlayer1(e.target.value)}
                                placeholder="Player 1"
                                required
                            />
                        </div>

                        <div className="form-group">
                            <label htmlFor="edit-player2">
                                <User size={14} /> Player 2 Name
                            </label>
                            <input
                                id="edit-player2"
                                type="text"
                                value={player2}
                                onChange={(e) => setPlayer2(e.target.value)}
                                placeholder="Player 2"
                                required
                            />
                        </div>
                    </div>

                    <div className="modal-actions">
                        <button type="button" className="secondary-btn" onClick={onClose} disabled={isSaving}>
                            Cancel
                        </button>
                        <button type="submit" className="primary-btn" disabled={isSaving}>
                            <Save size={16} />
                            {isSaving ? 'Saving...' : 'Save Changes'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};
