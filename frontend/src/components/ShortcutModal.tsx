import React, { useEffect } from 'react';
import { Keyboard, X, Target, Navigation } from 'lucide-react';
import { Button } from './ui';

interface ShortcutModalProps {
    isOpen: boolean;
    onClose: () => void;
}

interface ShortcutItem {
    keys: string[];
    description: string;
}

interface ShortcutCategory {
    title: string;
    icon: React.ReactNode;
    items: ShortcutItem[];
}

export const ShortcutModal: React.FC<ShortcutModalProps> = ({ isOpen, onClose }) => {
    // Close modal on Escape key press
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === 'Escape' && isOpen) {
                onClose();
            }
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [isOpen, onClose]);

    if (!isOpen) return null;

    const categories: ShortcutCategory[] = [
        {
            title: 'Video & Seek Controls',
            icon: <Navigation size={14} />,
            items: [
                { keys: ['SPACE'], description: 'Play / Pause Video' },
                { keys: ['◄', '►'], description: 'Seek -2.0s / +2.0s' },
                { keys: [',', '.'], description: 'Frame / Seek -2.0s / +2.0s' },
                { keys: ['Shift', '◄ / ►'], description: 'Fine Seek (-0.1s / +0.1s)' },
                { keys: ['▲', '▼'], description: 'Jump +1m / -1m' }
            ]
        },
        {
            title: 'Point Logging & Scoring',
            icon: <Target size={14} />,
            items: [
                { keys: ['E'], description: 'Mark Rally Start Time' },
                { keys: ['D'], description: 'Mark Rally End Time' },
                { keys: ['1', 'or', 'A'], description: 'Log Point Won by Player 1' },
                { keys: ['2', 'or', 'S'], description: 'Log Point Won by Player 2' },
                { keys: ['Z'], description: 'Undo Last Logged Event' }
            ]
        }
    ];

    return (
        <div className="modal-backdrop" onClick={onClose}>
            <div className="shortcuts-modal" onClick={(e) => e.stopPropagation()}>
                <div className="modal-header">
                    <div className="modal-title-group">
                        <Keyboard size={20} className="modal-icon" />
                        <h2>Keyboard Shortcuts</h2>
                    </div>
                    <button
                        type="button"
                        className="close-btn"
                        onClick={onClose}
                        title="Close Modal"
                    >
                        <X size={18} />
                    </button>
                </div>

                <div className="shortcuts-modal-grid">
                    {categories.map((cat, idx) => (
                        <div key={idx} className="shortcut-category-block">
                            <div className="shortcut-category-title">
                                {cat.icon}
                                <span>{cat.title}</span>
                            </div>
                            <div className="shortcut-list">
                                {cat.items.map((item, iIdx) => (
                                    <div key={iIdx} className="shortcut-item-row">
                                        <span className="shortcut-label">{item.description}</span>
                                        <div className="shortcut-keys">
                                            {item.keys.map((k, kIdx) => (
                                                <React.Fragment key={kIdx}>
                                                    {k === 'or' ? (
                                                        <span className="key-separator">or</span>
                                                    ) : (
                                                        <kbd>{k}</kbd>
                                                    )}
                                                </React.Fragment>
                                            ))}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    ))}
                </div>

                <div className="shortcuts-modal-footer">
                    <Button variant="secondary" size="sm" onClick={onClose}>
                        Close
                    </Button>
                </div>
            </div>
        </div>
    );
};
