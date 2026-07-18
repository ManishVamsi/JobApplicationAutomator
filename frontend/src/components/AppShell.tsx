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
    <div className="h-screen flex overflow-hidden">
      {/* Sidebar — fixed-width flex child, not position:fixed */}
      <aside className="w-60 flex-shrink-0 bg-(--color-bg-sidebar) border-r border-(--color-border-default) flex flex-col">
        {/* Logo */}
        <div className="px-5 py-5 border-b border-(--color-border-subtle)">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-(--radius-lg) bg-(--color-accent) flex items-center justify-center">
              <Zap className="w-4 h-4 text-(--color-text-inverse)" />
            </div>
            <div>
              <h1 className="text-sm font-semibold text-(--color-text-primary) tracking-tight leading-tight">
                JobApp
              </h1>
              <p className="text-[11px] text-(--color-text-muted) leading-tight">Assistant</p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-0.5">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-3 py-2 rounded-(--radius-md) text-[13px] font-medium transition-all duration-150 ${
                  isActive
                    ? 'bg-(--color-accent-light) text-(--color-accent) shadow-sm'
                    : 'text-(--color-text-secondary) hover:bg-(--color-bg-hover) hover:text-(--color-text-primary)'
                }`
              }
            >
              <Icon className="w-4 h-4" />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* User section */}
        <div className="px-3 py-3 border-t border-(--color-border-subtle)">
          <div className="px-3 py-2 mb-1">
            <p className="text-[13px] font-medium text-(--color-text-primary) truncate">
              {user?.name || user?.email || 'User'}
            </p>
            <p className="text-[11px] text-(--color-text-muted) truncate">
              {user?.email}
            </p>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 w-full px-3 py-2 rounded-(--radius-md) text-[13px] text-(--color-text-secondary) hover:bg-(--color-error-subtle) hover:text-(--color-error) transition-all"
          >
            <LogOut className="w-3.5 h-3.5" />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main content — fills remaining space with independent scroll */}
      <main className="flex-1 overflow-y-auto">
        <div className="p-(--spacing-page) max-w-5xl mx-auto">
          {children}
        </div>
      </main>
    </div>
  );
}
