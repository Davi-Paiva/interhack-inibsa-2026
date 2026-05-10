import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { cn } from '../../utils/helpers';

interface KPICardProps {
  title: string;
  value: string | number;
  change?: number;
  trend?: 'up' | 'down' | 'stable';
  icon?: React.ReactNode;
  suffix?: string;
}

export function KPICard({ title, value, change, trend, icon, suffix }: KPICardProps) {
  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus;
  const trendColor = trend === 'up' ? 'text-red-600' : trend === 'down' ? 'text-green-600' : 'text-gray-600';

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-gray-500">
          {title}
        </CardTitle>
        {icon && <div className="text-gray-500">{icon}</div>}
      </CardHeader>
      <CardContent>
        <div className="text-3xl font-bold text-gray-900">
          {value}
          {suffix && <span className="text-lg font-normal text-gray-500 ml-1">{suffix}</span>}
        </div>
        {change !== undefined && (
          <div className={cn('flex items-center gap-1 text-sm mt-1', trendColor)}>
            <TrendIcon className="h-4 w-4" />
            <span>{Math.abs(change)}%</span>
            <span className="text-gray-500">vs mes anterior</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
