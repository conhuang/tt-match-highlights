import React from 'react';
import { Clock, Keyboard } from 'lucide-react';
import { Button } from './ui';

interface StatusPanelProps {
    pendingStartTime: number | null;
    onOpenShortcuts?: () => void;
}

export const StatusPanel: React.FC<StatusPanelProps> = ({ pendingStartTime, onOpenShortcuts }) => {
    return (
        <div className="status-panel">
            <div className="status-item">
                <Clock size={16} className="status-icon" />
                <span className="status-label">Pending Start Time:</span>
                <span className={`status-value ${pendingStartTime !== null ? 'active' : ''}`}>
                    {pendingStartTime !== null ? `${pendingStartTime.toFixed(1)}s` : 'None'}
                </span>
            </div>
            {onOpenShortcuts && (
                <Button
                    variant="secondary"
                    size="sm"
                    icon={<Keyboard size={14} />}
                    onClick={onOpenShortcuts}
                    title="View Keyboard Shortcuts"
                >
                    Shortcuts
                </Button>
            )}
        </div>
    );
};
