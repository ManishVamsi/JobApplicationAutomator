import { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useAuthStore } from './store/authStore';
import { setupInterceptors } from './lib/api';
import { AppShell } from './components/AppShell';
import { LoginPage } from './pages/LoginPage';
import { JobListPage } from './pages/JobListPage';
import { JobSourcesPage } from './pages/JobSourcesPage';
import { LinkedInPostsPage } from './pages/LinkedInPostsPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

// Set up interceptors once (outside component to avoid re-registration)
let interceptorsSetUp = false;

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <AppShell>{children}</AppShell>;
}

function PublicRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  if (isAuthenticated) return <Navigate to="/jobs" replace />;
  return <>{children}</>;
}

export default function App() {
  useEffect(() => {
    if (!interceptorsSetUp) {
      setupInterceptors(
        () => useAuthStore.getState().accessToken,
        (token) => useAuthStore.getState().setAccessToken(token),
        () => useAuthStore.getState().logout(),
      );
      interceptorsSetUp = true;
    }
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<PublicRoute><LoginPage /></PublicRoute>} />
          <Route path="/jobs" element={<ProtectedRoute><JobListPage /></ProtectedRoute>} />
          <Route path="/sources" element={<ProtectedRoute><JobSourcesPage /></ProtectedRoute>} />
          <Route path="/linkedin" element={<ProtectedRoute><LinkedInPostsPage /></ProtectedRoute>} />
          <Route path="*" element={<Navigate to="/jobs" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
