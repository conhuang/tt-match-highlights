import React from 'react';
import { CreateMatchInput } from '../types';

interface MatchFormProps {
    formData: CreateMatchInput;
    onChange: (field: keyof CreateMatchInput, value: string) => void;
}

export const MatchForm: React.FC<MatchFormProps> = ({ formData, onChange }) => {
    return (
        <div className="form-group-container">
            <div className="form-row">
                <input
                    type="text"
                    id="match-name"
                    placeholder="Match Name (e.g. Finals 2026)"
                    value={formData.name}
                    onChange={(e) => onChange('name', e.target.value)}
                    required
                    autoComplete="off"
                    className="input-field"
                />
            </div>
            <div className="form-grid">
                <input
                    type="text"
                    id="player1"
                    placeholder="Player 1 Name"
                    value={formData.player1}
                    onChange={(e) => onChange('player1', e.target.value)}
                    required
                    autoComplete="off"
                    className="input-field"
                />
                <input
                    type="text"
                    id="player2"
                    placeholder="Player 2 Name"
                    value={formData.player2}
                    onChange={(e) => onChange('player2', e.target.value)}
                    required
                    autoComplete="off"
                    className="input-field"
                />
            </div>
        </div>
    );
};
