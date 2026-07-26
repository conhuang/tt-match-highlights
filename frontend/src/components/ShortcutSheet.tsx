import React from 'react';
import { Keyboard } from 'lucide-react';

export const ShortcutSheet: React.FC = () => {
    return (
        <div className="shortcuts-card">
            <div className="card-header">
                <Keyboard size={16} />
                <h3>Keyboard Shortcuts</h3>
            </div>
            <div className="shortcut-rows">
                <div className="shortcut-row">
                    <kbd>SPACE</kbd> <span>Play / Pause Video</span>
                </div>
                <div className="shortcut-row">
                    <kbd>E</kbd> or <kbd>D</kbd> <span>Mark Clip Start Time</span>
                </div>
                <div className="shortcut-row">
                    <kbd>1</kbd> or <kbd>A</kbd> <span>Log Point Won by Player 1</span>
                </div>
                <div className="shortcut-row">
                    <kbd>2</kbd> or <kbd>S</kbd> <span>Log Point Won by Player 2</span>
                </div>
                <div className="shortcut-row">
                    <kbd>Z</kbd> <span>Undo Last Event</span>
                </div>
            </div>
        </div>
    );
};
