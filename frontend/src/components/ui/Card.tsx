import React from 'react';

export interface CardProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'title'> {
    title?: string | React.ReactNode;
    headerIcon?: React.ReactNode;
    headerExtra?: React.ReactNode;
    variant?: 'default' | 'glass' | 'resume' | 'flat';
}

export const Card: React.FC<CardProps> = ({
    title,
    headerIcon,
    headerExtra,
    variant = 'default',
    children,
    className = '',
    ...props
}) => {
    const hasHeader = title || headerIcon || headerExtra;

    return (
        <div className={`ui-card ui-card-${variant} ${className}`} {...props}>
            {hasHeader && (
                <div className="ui-card-header">
                    <div className="ui-card-title-row">
                        {headerIcon && <span className="ui-card-header-icon">{headerIcon}</span>}
                        {typeof title === 'string' ? <h3>{title}</h3> : title}
                    </div>
                    {headerExtra && <div className="ui-card-header-extra">{headerExtra}</div>}
                </div>
            )}
            <div className="ui-card-body">{children}</div>
        </div>
    );
};
