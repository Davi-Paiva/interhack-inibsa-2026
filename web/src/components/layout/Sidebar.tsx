import { useRef } from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  AlertCircle, 
  Building2, 
  Activity,
  Upload
} from 'lucide-react';
import { cn } from '../../utils/helpers';

const navigation = [
  { name: 'Overview', href: '/', icon: LayoutDashboard },
  { name: 'Priority Queue', href: '/priority-queue', icon: AlertCircle },
  { name: 'Clinics', href: '/clinics', icon: Building2 }
];

export function Sidebar() {
  const fileInputRef = useRef<HTMLInputElement>(null);

  return (
    <div className="flex w-full flex-col border-b border-gray-200 bg-white md:h-screen md:w-64 md:border-b-0 md:border-r">
      {/* Logo/Brand */}
      <div className="flex h-16 items-center border-b border-gray-200 px-4 md:px-6">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600">
            <Activity className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-gray-900">RiskMonitor</h1>
            <p className="text-xs text-gray-500">Commercial Intel</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-x-auto px-3 py-3 md:space-y-1 md:py-4">
        <div className="flex gap-2 md:block">
        {navigation.map((item) => (
          <NavLink
            key={item.name}
            to={item.href}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-600 hover:bg-gray-100'
              )
            }
          >
            <item.icon className="h-5 w-5" />
            {item.name}
          </NavLink>
        ))}
        </div>
      </nav>

      <div className="border-t border-gray-200 p-3 md:p-4">
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          accept=".csv,.json,.xlsx,.xls"
          aria-label="Upload data file"
        />
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          className="flex w-full items-center justify-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
        >
          <Upload className="h-4 w-4" />
          Upload data
        </button>
      </div>

      {/* Footer */}
      <div className="hidden border-t border-gray-200 p-4 md:block">
        <div className="text-xs text-gray-500">
          <p className="font-medium">Sistema v1.0</p>
          <p className="mt-1">Última actualización: Hoy</p>
        </div>
      </div>
    </div>
  );
}
