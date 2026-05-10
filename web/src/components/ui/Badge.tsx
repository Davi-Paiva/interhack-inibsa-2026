import { cn } from '../../utils/helpers';
import type { RiskLevel } from '../../types';

interface BadgeProps {
  children: React.ReactNode;
  variant?: RiskLevel | 'default' | 'outline';
  className?: string;
}

const variantStyles = {
  default: 'bg-primary text-primary-foreground',
  outline: 'border border-input bg-background',
  low: 'bg-green-100 text-green-800 border-green-200',
  medium: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  high: 'bg-orange-100 text-orange-800 border-orange-200',
  critical: 'bg-red-100 text-red-800 border-red-200',
};

export function Badge({ children, variant = 'default', className }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors',
        variantStyles[variant],
        className
      )}
    >
      {children}
    </span>
  );
}
