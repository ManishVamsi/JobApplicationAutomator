import type { ReactNode } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { Briefcase, Share2, LogOut, Settings, Zap } from 'lucide-react';
import { useAuthStore } from '../store/authStore';
import api from '../lib/api';

interface AppShellProps {
  children: ReactNode;
}

const navItems = [
  { to: '/jobs', label: 'Jobs', icon: Briefcase },
  { to: '/sources', label: 'Job Sources', icon: Settings },
  { to: '/linkedin', label: 'LinkedIn Posts', icon: Share2 },
];

export function AppShell({ children }: AppShellProps) {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = async () => {
    try {
      await api.post('/auth/logout');
    } catch {
      // Ignore errors — clear client state regardless
    }
    logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <aside className="w-64 bg-(--color-bg-secondary) border-r border-(--color-border-default) flex flex-col fixed h-full z-10">
        {/* Logo */}
        <div className="p-5 border-b border-(--color-border-default)">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-(--radius-lg) bg-(--color-accent) flex items-center justify-center shadow-(--shadow-glow)">
              <Zap className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-base font-bold text-(--color-text-primary) tracking-tight">
                JobApp
              </h1>
              <p className="text-xs text-(--color-text-muted)">Assistant</p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-3 space-y-1">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-(--radius-md) text-sm font-medium transition-all duration-150 ${
                  isActive
                    ? 'bg-(--color-accent-subtle) text-(--color-accent-hover) shadow-sm'
                    : 'text-(--color-text-secondary) hover:bg-(--color-bg-hover) hover:text-(--color-text-primary)'
                }`
              }
            >
              <Icon className="w-4.5 h-4.5" />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* User section */}
        <div className="p-3 border-t border-(--color-border-default)">
          <div className="px-3 py-2 mb-2">
            <p className="text-sm font-medium text-(--color-text-primary) truncate">
              {user?.name || user?.email || 'User'}
            </p>
            <p className="text-xs text-(--color-text-muted) truncate">
              {user?.email}
            </p>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 w-full px-3 py-2 rounded-(--radius-md) text-sm text-(--color-text-secondary) hover:bg-(--color-error-subtle) hover:text-(--color-error) transition-all"
          >
            <LogOut className="w-4 h-4" />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 ml-64">
        <div className="p-(--spacing-page) max-w-7xl mx-auto">
          {children}
        </div>
      </main>
    </div>
  );
}
