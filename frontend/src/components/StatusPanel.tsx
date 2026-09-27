import React, { useState } from 'react';
import { Clock, Keyboard, ChevronDown, ChevronUp, X, Target, Navigation, Sparkles } from 'lucide-react';
import { Button } from './ui';

interface StatusPanelProps {
    pendingStartTime: number | null;
    player1?: string;
    player2?: string;
}

interface ShortcutItem {
    keys: string[];
    description: string;
}

interface ShortcutCategory {
    title: string;
    icon: React.ReactNode;
    items: ShortcutItem[];
    isFullWidth?: boolean;
}

function formatMmSs(seconds: number): string {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    const pad = (num: number) => num.toString().padStart(2, '0');
    return `${pad(m)}:${pad(s)}`;
}

export const StatusPanel: React.FC<StatusPanelProps> = ({ 
    pendingStartTime,
    player1 = 'Player 1',
    player2 = 'Player 2'
}) => {
    const [isKeystrokesOpen, setIsKeystrokesOpen] = useState<boolean>(false);
    const p1 = player1?.trim() || 'Player 1';
    const p2 = player2?.trim() || 'Player 2';

    const categories: ShortcutCategory[] = [
        {
            title: 'Playback & Seek Controls',
            icon: <Navigation size={14} />,
            items: [
                { keys: ['SPACE'], description: 'Play / Pause Video' },
                { keys: ['◄', '►', 'or', ',', '.'], description: 'Seek -2.0s / +2.0s' },
                { keys: ['▲', '▼', 'or', '<', '>'], description: 'Jump -1m / +1m' }
            ]
        },
        {
            title: 'Point Logging & Timing',
            icon: <Target size={14} />,
            items: [
                { keys: ['E'], description: 'Mark Rally Start Time' },
                { keys: ['1'], description: `Log Point Won by ${p1}` },
                { keys: ['2'], description: `Log Point Won by ${p2}` },
                { keys: ['3'], description: 'Log No Winner Clip' }
            ]
        },
        {
            title: 'Point Modifiers & Actions',
            icon: <Sparkles size={14} />,
            isFullWidth: true,
            items: [
                { keys: ['H'], description: 'Toggle Highlight on Last Point' },
                { keys: ['Shift', '+', '1'], description: `${p1} Timeout After Last Point` },
                { keys: ['Z'], description: 'Undo Last Logged Event' },
                { keys: ['Shift', '+', '2'], description: `${p2} Timeout After Last Point` }
            ]
        }
    ];

    return (
        <div className="status-panel-container">
            <div className="status-panel">
                <div className="status-item">
                    <Clock size={16} className="status-icon" />
                    <span className="status-label">Pending Start Time:</span>
                    <span className={`status-value ${pendingStartTime !== null ? 'active' : ''}`}>
                        {pendingStartTime !== null ? formatMmSs(pendingStartTime) : 'None'}
                    </span>
                </div>
                <Button
                    variant="secondary"
                    size="sm"
                    icon={<Keyboard size={14} />}
                    onClick={() => setIsKeystrokesOpen(!isKeystrokesOpen)}
                    title="Toggle Keyboard Keystrokes"
                >
                    <span>Keystrokes</span>
                    {isKeystrokesOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                </Button>
            </div>

            {isKeystrokesOpen && (
                <div className="collapsible-keystrokes-card">
                    <div className="card-header">
                        <div className="modal-title-group">
                            <Keyboard size={18} className="modal-icon" />
                            <h3>Keyboard Shortcuts</h3>
                        </div>
                        <button
                            type="button"
                            className="close-btn"
                            onClick={() => setIsKeystrokesOpen(false)}
                            title="Collapse Keystrokes"
                        >
                            <X size={16} />
                        </button>
                    </div>

                    <div className="shortcuts-modal-container">
                        {categories.map((cat, idx) => (
                            <div key={idx} className={cat.isFullWidth ? "shortcut-category-block full-width" : "shortcut-category-block"}>
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
                                                        ) : k === '+' ? (
                                                            <span className="key-plus">+</span>
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
                </div>
            )}
        </div>
    );
};
