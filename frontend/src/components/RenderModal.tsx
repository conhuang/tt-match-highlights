import React, { useState } from 'react';
import { RenderOptions } from '../types';
import { Film, X, CheckSquare, Square, Sliders } from 'lucide-react';

interface RenderModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSubmit: (type: 'full_match' | 'highlights', label: string, options: RenderOptions) => void;
    hasHighlights: boolean;
    isRendering: boolean;
}

export const RenderModal: React.FC<RenderModalProps> = ({
    isOpen,
    onClose,
    onSubmit,
    hasHighlights,
    isRendering
}) => {
    const [renderType, setRenderType] = useState<'full_match' | 'highlights'>('full_match');
    const [label, setLabel] = useState<string>('Full Scored Match');
    const [includeScoreboard, setIncludeScoreboard] = useState<boolean>(true);
    const [includeGameCards, setIncludeGameCards] = useState<boolean>(true);
    const [cpuMode, setCpuMode] = useState<boolean>(true);

    if (!isOpen) return null;

    const handleTypeChange = (type: 'full_match' | 'highlights') => {
        setRenderType(type);
        setLabel(type === 'highlights' ? 'Highlights Reel' : 'Full Scored Match');
        if (type === 'highlights') {
            setIncludeGameCards(false); // Default game cards off for highlights reel
        } else {
            setIncludeGameCards(true);
        }
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        onSubmit(renderType, label, {
            highlights_only: renderType === 'highlights',
            include_scoreboard: includeScoreboard,
            include_game_cards: includeGameCards,
            cpu_mode: cpuMode
        });
    };

    return (
        <div className="modal-backdrop" onClick={onClose}>
            <div className="modal-content card" onClick={(e) => e.stopPropagation()}>
                <div className="modal-header">
                    <div className="modal-title-row">
                        <Film className="accent-icon" size={22} />
                        <h2>Configure Render Output</h2>
                    </div>
                    <button type="button" className="close-btn" onClick={onClose}>
                        <X size={18} />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="render-form">
                    <div className="form-group">
                        <label className="group-label">Render Mode</label>
                        <div className="mode-selector-grid">
                            <button
                                type="button"
                                className={`mode-card ${renderType === 'full_match' ? 'active' : ''}`}
                                onClick={() => handleTypeChange('full_match')}
                            >
                                <div className="mode-title">Full Scored Match</div>
                                <div className="mode-desc">Includes all rallies with live score overlay & set titles</div>
                            </button>

                            <button
                                type="button"
                                className={`mode-card ${renderType === 'highlights' ? 'active' : ''}`}
                                onClick={() => handleTypeChange('highlights')}
                            >
                                <div className="mode-title">⭐ Highlights Reel</div>
                                <div className="mode-desc">High-energy reel containing only starred highlight points</div>
                            </button>
                        </div>
                    </div>

                    <div className="form-group">
                        <label htmlFor="render-label" className="group-label">Render Label</label>
                        <input
                            type="text"
                            id="render-label"
                            value={label}
                            onChange={(e) => setLabel(e.target.value)}
                            className="input-field"
                            placeholder="e.g. 1080p Final Render"
                            required
                        />
                    </div>

                    <div className="form-group">
                        <label className="group-label">Render Options</label>
                        <div className="toggles-list">
                            <label className="toggle-item" onClick={() => setIncludeScoreboard(!includeScoreboard)}>
                                {includeScoreboard ? <CheckSquare className="checkbox-icon active" size={18} /> : <Square className="checkbox-icon" size={18} />}
                                <div className="toggle-text">
                                    <span className="toggle-title">Include Scoreboard Overlay</span>
                                    <span className="toggle-desc">Render dynamic broadcast scoreboard in corner</span>
                                </div>
                            </label>

                            <label className="toggle-item" onClick={() => setIncludeGameCards(!includeGameCards)}>
                                {includeGameCards ? <CheckSquare className="checkbox-icon active" size={18} /> : <Square className="checkbox-icon" size={18} />}
                                <div className="toggle-text">
                                    <span className="toggle-title">Include Inter-Game Title Cards</span>
                                    <span className="toggle-desc">Insert 2-second "Game 1", "Game 2" cards between sets</span>
                                </div>
                            </label>

                            <label className="toggle-item" onClick={() => setCpuMode(!cpuMode)}>
                                {cpuMode ? <CheckSquare className="checkbox-icon active" size={18} /> : <Square className="checkbox-icon" size={18} />}
                                <div className="toggle-text">
                                    <span className="toggle-title">Software CPU Encoder (libx264)</span>
                                    <span className="toggle-desc">Maximum compatibility & reliable quality</span>
                                </div>
                            </label>
                        </div>
                    </div>

                    {renderType === 'highlights' && !hasHighlights && (
                        <div className="warning-banner">
                            ⚠️ No points are currently tagged with ⭐ Highlight in this match. Please star at least one point before rendering a Highlights Reel.
                        </div>
                    )}

                    <div className="modal-actions">
                        <button type="button" className="secondary-btn" onClick={onClose}>
                            Cancel
                        </button>
                        <button
                            type="submit"
                            className="primary-btn"
                            disabled={isRendering || (renderType === 'highlights' && !hasHighlights)}
                        >
                            <Sliders size={16} />
                            {isRendering ? 'Starting Render...' : 'Start Render Job'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};
