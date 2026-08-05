import React from 'react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: 'primary' | 'secondary' | 'danger' | 'ghost' | 'render' | 'signout';
    size?: 'sm' | 'md' | 'lg';
    icon?: React.ReactNode;
    isLoading?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
    variant = 'secondary',
    size = 'md',
    icon,
    isLoading = false,
    children,
    className = '',
    disabled,
    ...props
}) => {
    const variantClass = `btn-${variant}`;
    const sizeClass = `btn-${size}`;

    return (
        <button
            type="button"
            className={`btn ${variantClass} ${sizeClass} ${className}`}
            disabled={disabled || isLoading}
            {...props}
        >
            {icon && <span className="btn-icon-wrapper">{icon}</span>}
            {children && <span>{children}</span>}
        </button>
    );
};
