import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import { useNavigate } from "react-router-dom";
import api from "@/lib/api";

export interface User {
  user_id: number;
  username: string;
  role: string | null;
  full_name: string | null;
  email: string | null;
  active: boolean;
  created_at: string;
}

export interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const TOKEN_KEY = "ovulite_token";
const REFRESH_TOKEN_KEY = "ovulite_refresh_token";
const TOKEN_REFRESH_INTERVAL = 25 * 60 * 1000; // 25 minutes (5 min before 30 min expiry)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(
    () => localStorage.getItem(TOKEN_KEY),
  );
  const [refreshToken, setRefreshToken] = useState<string | null>(
    () => localStorage.getItem(REFRESH_TOKEN_KEY),
  );
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  const loadUser = useCallback(async (accessToken: string) => {
    try {
      const res = await api.get<User>("/auth/me", {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      setUser(res.data);
    } catch {
      // Token invalid or expired — clear it
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(REFRESH_TOKEN_KEY);
      setToken(null);
      setRefreshToken(null);
      setUser(null);
    }
  }, []);

  const refreshAccessToken = useCallback(async () => {
    const storedRefreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
    if (!storedRefreshToken) {
      console.log("[AuthContext] No refresh token available");
      return false;
    }

    try {
      console.log("[AuthContext] Refreshing access token...");
      const res = await api.post<{ access_token: string; refresh_token: string; token_type: string }>(
        "/auth/refresh",
        { refresh_token: storedRefreshToken },
      );

      const newAccessToken = res.data.access_token;
      localStorage.setItem(TOKEN_KEY, newAccessToken);
      setToken(newAccessToken);
      console.log("[AuthContext] Token refreshed successfully");
      return true;
    } catch (error) {
      console.error("[AuthContext] Token refresh failed:", error);
      // Clear tokens and logout
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(REFRESH_TOKEN_KEY);
      setToken(null);
      setRefreshToken(null);
      setUser(null);
      return false;
    }
  }, []);

  // Set up automatic token refresh interval
  useEffect(() => {
    if (!token || !refreshToken) return;

    console.log("[AuthContext] Setting up automatic token refresh (every 25 min)");
    const interval = setInterval(() => {
      refreshAccessToken();
    }, TOKEN_REFRESH_INTERVAL);

    return () => clearInterval(interval);
  }, [token, refreshToken, refreshAccessToken]);

  // On mount: if token exists, validate and load user
  useEffect(() => {
    if (token) {
      loadUser(token).finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Centralized 401 handling from API interceptor.
  // Try to refresh token before logging out.
  useEffect(() => {
    const onUnauthorized = async () => {
      console.log("[AuthContext] Received 401 - attempting token refresh");
      const refreshed = await refreshAccessToken();
      if (!refreshed) {
        // Refresh failed, logout
        navigate("/login");
      }
    };

    window.addEventListener("ovulite:unauthorized", onUnauthorized);
    return () => {
      window.removeEventListener("ovulite:unauthorized", onUnauthorized);
    };
  }, [navigate, refreshAccessToken]);

  const login = useCallback(
    async (username: string, password: string) => {
      // FastAPI OAuth2PasswordRequestForm expects form-encoded data
      const params = new URLSearchParams();
      params.append("username", username);
      params.append("password", password);

      console.log("[AuthContext] Attempting login for user:", username);
      try {
        const res = await api.post<{ 
          access_token: string; 
          refresh_token: string; 
          token_type: string; 
        }>(
          "/auth/login",
          params,
          { headers: { "Content-Type": "application/x-www-form-urlencoded" } },
        );

        console.log("[AuthContext] Login successful, got tokens");
        const accessToken = res.data.access_token;
        const refreshTokenValue = res.data.refresh_token;
        localStorage.setItem(TOKEN_KEY, accessToken);
        localStorage.setItem(REFRESH_TOKEN_KEY, refreshTokenValue);
        setToken(accessToken);
        setRefreshToken(refreshTokenValue);

        // Load user profile
        console.log("[AuthContext] Fetching user profile with token...");
        const userRes = await api.get<User>("/auth/me", {
          headers: { Authorization: `Bearer ${accessToken}` },
        });
        console.log("[AuthContext] Got user profile:", userRes.data.username);
        setUser(userRes.data);

        navigate("/app");
      } catch (error) {
        console.error("[AuthContext] Login failed:", error);
        throw error;
      }
    },
    [navigate],
  );

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    setToken(null);
    setRefreshToken(null);
    setUser(null);
    navigate("/login");
  }, [navigate]);

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
