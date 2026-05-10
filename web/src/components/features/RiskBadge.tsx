import { Badge } from '../ui/Badge';
import type { RiskLevel } from '../../types';

interface RiskBadgeProps {
  level: RiskLevel;
  showLabel?: boolean;
}

const labels: Record<RiskLevel, string> = {
  low: 'Bajo',
  medium: 'Medio',
  high: 'Alto',
  critical: 'Crítico',
};

export function RiskBadge({ level, showLabel = true }: RiskBadgeProps) {
  return (
    <Badge variant={level}>
      {showLabel ? labels[level] : level.toUpperCase()}
    </Badge>
  );
}
