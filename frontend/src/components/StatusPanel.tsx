import React from 'react';
import { Clock } from 'lucide-react';

interface StatusPanelProps {
    pendingStartTime: number | null;
}

export const StatusPanel: React.FC<StatusPanelProps> = ({ pendingStartTime }) => {
    return (
        <div className="status-panel">
            <div className="status-item">
                <Clock size={16} className="status-icon" />
                <span className="status-label">Pending Start Time:</span>
                <span className={`status-value ${pendingStartTime !== null ? 'active' : ''}`}>
                    {pendingStartTime !== null ? `${pendingStartTime.toFixed(1)}s` : 'None'}
                </span>
            </div>
        </div>
    );
};
