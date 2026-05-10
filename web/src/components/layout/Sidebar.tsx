import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  AlertCircle, 
  Building2, 
  Activity
} from 'lucide-react';
import { cn } from '../../utils/helpers';

const navigation = [
  { name: 'Overview', href: '/', icon: LayoutDashboard },
  { name: 'Priority Queue', href: '/priority-queue', icon: AlertCircle },
  { name: 'Clinics', href: '/clinics', icon: Building2 }
];

export function Sidebar() {
  return (
    <div className="flex h-screen w-64 flex-col border-r border-gray-200 bg-white">
      {/* Logo/Brand */}
      <div className="flex h-16 items-center border-b border-gray-200 px-6">
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
      <nav className="flex-1 space-y-1 px-3 py-4">
        {navigation.map((item) => (
          <NavLink
            key={item.name}
            to={item.href}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
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
      </nav>

      {/* Footer */}
      <div className="border-t border-gray-200 p-4">
        <div className="text-xs text-gray-500">
          <p className="font-medium">Sistema v1.0</p>
          <p className="mt-1">Última actualización: Hoy</p>
        </div>
      </div>
    </div>
  );
}
