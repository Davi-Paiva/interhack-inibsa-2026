import { Search} from 'lucide-react';
import { Input } from '../ui/Input';

interface HeaderProps {
  title: string;
  subtitle?: string;
}

export function Header({ title, subtitle }: HeaderProps) {
  return (
    <header className="border-b border-gray-200 bg-white">
      <div className="flex flex-col gap-3 px-4 py-4 md:h-16 md:flex-row md:items-center md:justify-between md:px-6 md:py-0">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{title}</h1>
          {subtitle && (
            <p className="text-sm text-gray-500">{subtitle}</p>
          )}
        </div>

        <div className="flex items-center gap-4">
          {/* Search */}
          <div className="relative w-full md:w-64">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <Input
              type="search"
              placeholder="Buscar clínicas..."
              className="pl-9"
            />
          </div>
        </div>
      </div>
    </header>
  );
}
