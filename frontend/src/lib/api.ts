import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1';

const api = axios.create({
  baseURL: API_BASE,
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
});

export default api;

// ─── Interceptor setup (call once from App after store is available) ───
export function setupInterceptors(
  getAccessToken: () => string | null,
  setAccessToken: (token: string) => void,
  logout: () => void,
) {
  // Request: attach access token
  api.interceptors.request.use((config) => {
    const token = getAccessToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  });

  // Response: auto-refresh on 401
  let isRefreshing = false;
  let failedQueue: Array<{
    resolve: (value: unknown) => void;
    reject: (reason?: unknown) => void;
  }> = [];

  const processQueue = (error: unknown, token: string | null = null) => {
    failedQueue.forEach(({ resolve, reject }) => {
      if (error) reject(error);
      else resolve(token);
    });
    failedQueue = [];
  };

  api.interceptors.response.use(
    (response) => response,
    async (error) => {
      const originalRequest = error.config;

      if (error.response?.status === 401 && !originalRequest._retry) {
        if (isRefreshing) {
          return new Promise((resolve, reject) => {
            failedQueue.push({ resolve, reject });
          }).then((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            return api(originalRequest);
          });
        }

        originalRequest._retry = true;
        isRefreshing = true;

        try {
          const expiredToken = getAccessToken();
          const response = await axios.post(
            `${API_BASE}/auth/refresh`,
            {},
            {
              withCredentials: true,
              headers: expiredToken
                ? { Authorization: `Bearer ${expiredToken}` }
                : {},
            }
          );

          const newToken = response.data.access_token;
          setAccessToken(newToken);
          processQueue(null, newToken);

          originalRequest.headers.Authorization = `Bearer ${newToken}`;
          return api(originalRequest);
        } catch (refreshError) {
          processQueue(refreshError, null);
          logout();
          window.location.href = '/login';
          return Promise.reject(refreshError);
        } finally {
          isRefreshing = false;
        }
      }

      return Promise.reject(error);
    }
  );
}
