import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Mail, ArrowRight, KeyRound, Zap, Loader2 } from 'lucide-react';
import api from '../lib/api';
import { useAuthStore } from '../store/authStore';

type Step = 'email' | 'otp';

export function LoginPage() {
  const [step, setStep] = useState<Step>('email');
  const [email, setEmail] = useState('');
  const [otp, setOtp] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();
  const { setAccessToken } = useAuthStore();

  const handleRequestOTP = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await api.post('/auth/request-otp', { email });
      setStep('otp');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to send OTP');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOTP = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await api.post('/auth/verify-otp', { email, code: otp });
      setAccessToken(res.data.access_token);

      // Fetch user profile
      const profileRes = await api.get('/users/me');
      useAuthStore.getState().setUser(profileRes.data);

      navigate('/jobs');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid OTP');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-(--color-bg-primary) p-4">
      {/* Background glow effect */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-(--color-accent) opacity-5 rounded-full blur-[120px]" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-500 opacity-5 rounded-full blur-[120px]" />
      </div>

      <div className="relative w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-(--color-accent) shadow-(--shadow-glow) mb-4">
            <Zap className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-(--color-text-primary)">
            Job Application Assistant
          </h1>
          <p className="text-(--color-text-secondary) mt-1">
            Sign in with your email to get started
          </p>
        </div>

        {/* Card */}
        <div className="bg-(--color-bg-card) border border-(--color-border-default) rounded-(--radius-xl) shadow-(--shadow-elevated) p-8">
          {step === 'email' ? (
            <form onSubmit={handleRequestOTP} className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-(--color-text-secondary) mb-1.5">
                  Email address
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4.5 h-4.5 text-(--color-text-muted)" />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@company.com"
                    required
                    className="w-full pl-10 pr-4 py-2.5 bg-(--color-bg-input) border border-(--color-border-default) rounded-(--radius-md) text-sm text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:border-(--color-border-focus) focus:outline-none transition-colors"
                  />
                </div>
              </div>

              {error && (
                <p className="text-sm text-(--color-error) bg-(--color-error-subtle) px-3 py-2 rounded-(--radius-md)">
                  {error}
                </p>
              )}

              <button
                type="submit"
                disabled={loading || !email}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-(--color-accent) hover:bg-(--color-accent-hover) text-white font-medium rounded-(--radius-md) transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-md hover:shadow-lg"
              >
                {loading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <>
                    Send Code <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>
          ) : (
            <form onSubmit={handleVerifyOTP} className="space-y-5">
              <div className="text-center mb-2">
                <p className="text-sm text-(--color-text-secondary)">
                  Code sent to <span className="text-(--color-accent) font-medium">{email}</span>
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-(--color-text-secondary) mb-1.5">
                  6-digit code
                </label>
                <div className="relative">
                  <KeyRound className="absolute left-3 top-1/2 -translate-y-1/2 w-4.5 h-4.5 text-(--color-text-muted)" />
                  <input
                    type="text"
                    value={otp}
                    onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                    placeholder="000000"
                    maxLength={6}
                    required
                    autoFocus
                    className="w-full pl-10 pr-4 py-2.5 bg-(--color-bg-input) border border-(--color-border-default) rounded-(--radius-md) text-sm text-(--color-text-primary) placeholder:text-(--color-text-muted) text-center tracking-[0.4em] text-lg font-mono focus:border-(--color-border-focus) focus:outline-none transition-colors"
                  />
                </div>
              </div>

              {error && (
                <p className="text-sm text-(--color-error) bg-(--color-error-subtle) px-3 py-2 rounded-(--radius-md)">
                  {error}
                </p>
              )}

              <button
                type="submit"
                disabled={loading || otp.length !== 6}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-(--color-accent) hover:bg-(--color-accent-hover) text-white font-medium rounded-(--radius-md) transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-md hover:shadow-lg"
              >
                {loading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  'Verify & Sign In'
                )}
              </button>

              <button
                type="button"
                onClick={() => { setStep('email'); setOtp(''); setError(''); }}
                className="w-full text-sm text-(--color-text-muted) hover:text-(--color-text-secondary) transition-colors"
              >
                ← Use a different email
              </button>
            </form>
          )}
        </div>

        <p className="text-center text-xs text-(--color-text-muted) mt-6">
          No password needed — we'll send a secure login code to your email.
        </p>
      </div>
    </div>
  );
}
