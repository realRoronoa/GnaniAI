import React from 'react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'accent' | 'destructive' | 'outline' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  isPill?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  isPill = false,
  leftIcon,
  rightIcon,
  className = '',
  disabled,
  ...props
}) => {
  let baseStyles =
    'inline-flex items-center justify-center font-medium transition-all duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed';

  let variantStyles = '';
  switch (variant) {
    case 'primary':
      // Console primary: deep forest
      variantStyles = 'bg-ink-2 hover:bg-ink text-surface shadow-sm active:scale-[0.98]';
      break;
    case 'accent':
      // Brand primary: burnt copper
      variantStyles = 'bg-accent hover:bg-accent-hover text-white shadow-sm active:scale-[0.98]';
      break;
    case 'secondary':
      variantStyles = 'bg-surface hover:bg-surface-2 text-ink border border-line shadow-sm';
      break;
    case 'destructive':
      variantStyles = 'bg-status-err hover:bg-status-err/90 text-white shadow-sm';
      break;
    case 'outline':
      variantStyles = 'bg-transparent border border-line hover:border-text-2 text-text hover:bg-surface-2/40';
      break;
    case 'ghost':
      variantStyles = 'bg-transparent hover:bg-surface-2/60 text-text hover:text-ink';
      break;
  }

  let sizeStyles = '';
  switch (size) {
    case 'sm':
      sizeStyles = 'text-xs px-3 py-1.5 gap-1.5 h-8';
      break;
    case 'md':
      sizeStyles = 'text-sm px-4 py-2 gap-2 h-9';
      break;
    case 'lg':
      sizeStyles = 'text-base px-6 py-2.5 gap-2.5 h-11';
      break;
  }

  const radiusStyles = isPill ? 'rounded-full' : 'rounded-md';

  return (
    <button
      className={`${baseStyles} ${variantStyles} ${sizeStyles} ${radiusStyles} ${className}`}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? (
        <span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
      ) : (
        leftIcon
      )}
      <span>{children}</span>
      {!isLoading && rightIcon}
    </button>
  );
};

