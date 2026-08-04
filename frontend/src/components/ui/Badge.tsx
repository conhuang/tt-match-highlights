import React from 'react';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
    variant?: 'live' | 'ready' | 'rendering' | 'completed' | 'failed' | 'info' | 'warning' | 'player1' | 'player2';
    icon?: React.ReactNode;
}

export const Badge: React.FC<BadgeProps> = ({
    variant = 'info',
    icon,
    children,
    className = '',
    ...props
}) => {
    return (
        <span className={`ui-badge ui-badge-${variant} ${className}`} {...props}>
            {icon && <span className="ui-badge-icon">{icon}</span>}
            {children && <span>{children}</span>}
        </span>
    );
};
