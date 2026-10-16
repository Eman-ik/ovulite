import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { getRoleLandingPath } from "@/lib/roleRoutes";

export interface User {
  user_id: number;
  organization_id: number | null;
  username: string;
  role: string | null;
  full_name: string | null;
  email: string | null;
  active: boolean;
  created_at: string;
  /** Temporary password: the API refuses everything but the change-password flow. */
  must_change_password?: boolean;
}

export interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  loginFromGoogle: (accessToken: string, refreshToken: string) => Promise<void>;
  logout: () => void;
  /** Adopt a token pair the API handed back mid-session (password change). */
  applyTokens: (accessToken: string, refreshToken: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const TOKEN_KEY = "ovulite_token";
const REFRESH_TOKEN_KEY = "ovulite_refresh_token";
const TOKEN_REFRESH_INTERVAL = 25 * 60 * 1000; // 25 minutes (5 min before 30 min expiry)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY));
  const [refreshToken, setRefreshToken] = useState<string | null>(() => localStorage.getItem(REFRESH_TOKEN_KEY));
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  const loadUser = useCallback(async (accessToken: string) => {
    try {
      // Add 5 second timeout for loading user
      const loadUserPromise = api.get<User>("/auth/me", {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      
      const timeoutPromise = new Promise((_, reject) =>
        setTimeout(() => reject(new Error("User load timeout")), 5000)
      );
      
      const res = await Promise.race([loadUserPromise, timeoutPromise]) as Awaited<typeof loadUserPromise>;
      setUser(res.data);
    } catch (error) {
      console.error("[AuthContext] Failed to load user:", error);
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

      // Refresh tokens rotate and are single-use: the one just sent is now
      // revoked. Storing the new one is not optional — keeping the old one
      // would replay a dead token at the next refresh, which the backend
      // reads as a stolen token and responds to by ending every session.
      const rotated = res.data.refresh_token;
      if (rotated) {
        localStorage.setItem(REFRESH_TOKEN_KEY, rotated);
        setRefreshToken(rotated);
      }
      console.log("[AuthContext] Token refreshed successfully");
      return true;
    } catch (error) {
      console.error("[AuthContext] Token refresh failed:", error);
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(REFRESH_TOKEN_KEY);
      setToken(null);
      setRefreshToken(null);
      setUser(null);
      return false;
    }
  }, []);

  useEffect(() => {
    if (!token || !refreshToken) return;

    console.log("[AuthContext] Setting up automatic token refresh (every 25 min)");
    const interval = setInterval(() => {
      refreshAccessToken();
    }, TOKEN_REFRESH_INTERVAL);

    return () => clearInterval(interval);
  }, [token, refreshToken, refreshAccessToken]);

  useEffect(() => {
    if (token) {
      loadUser(token).finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const onUnauthorized = async () => {
      console.log("[AuthContext] Received 401 - attempting token refresh");
      const refreshed = await refreshAccessToken();
      if (!refreshed) {
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
      const params = new URLSearchParams();
      params.append("username", username);
      params.append("password", password);

      console.log("[AuthContext] Attempting login for user:", username);
      try {
        const res = await api.post<{ access_token: string; refresh_token: string; token_type: string }>(
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

        console.log("[AuthContext] Fetching user profile with token...");
        const userRes = await api.get<User>("/auth/me", {
          headers: { Authorization: `Bearer ${accessToken}` },
        });
        console.log("[AuthContext] Got user profile:", userRes.data.username);
        setUser(userRes.data);

        // On a temporary password the API answers nothing but the
        // change-password flow, so landing on a dashboard would just render a
        // screen of failed requests.
        if (userRes.data.must_change_password) {
          navigate("/change-password");
          return;
        }
        navigate(getRoleLandingPath());
      } catch (error) {
        console.error("[AuthContext] Login failed:", error);
        throw error;
      }
    },
    [navigate],
  );

  const applyTokens = useCallback(async (accessToken: string, refreshTokenValue: string) => {
    // Used after /auth/change-password, which revokes the token the caller
    // was holding and hands back a replacement pair. Without adopting them,
    // changing your own password logs you straight out.
    localStorage.setItem(TOKEN_KEY, accessToken);
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshTokenValue);
    setToken(accessToken);
    setRefreshToken(refreshTokenValue);
    const res = await api.get<User>("/auth/me", {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    setUser(res.data);
  }, []);

  const loginFromGoogle = useCallback(
    async (accessToken: string, refreshTokenValue: string) => {
      localStorage.setItem(TOKEN_KEY, accessToken);
      localStorage.setItem(REFRESH_TOKEN_KEY, refreshTokenValue);
      setToken(accessToken);
      setRefreshToken(refreshTokenValue);

      const userRes = await api.get<User>("/auth/me", {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      setUser(userRes.data);
      navigate(getRoleLandingPath());
    },
    [navigate],
  );



  const logout = useCallback(() => {
    const currentToken = localStorage.getItem(TOKEN_KEY);
    const currentRefreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
    if (currentToken) {
      // Best-effort: revoke the token server-side so it can't be reused if
      // leaked, but don't block clearing local state if the request fails
      // (e.g. offline logout).
      //
      // The refresh token goes with it. Revoking only the access token left
      // the refresh token valid for days, so "log out" did not end the
      // session — anyone holding it could mint a new access token.
      api
        .post(
          "/auth/logout",
          currentRefreshToken ? { refresh_token: currentRefreshToken } : null,
          { headers: { Authorization: `Bearer ${currentToken}` } },
        )
        .catch((error) => console.error("[AuthContext] Server-side logout failed:", error));
    }
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    setToken(null);
    setRefreshToken(null);
    setUser(null);
    navigate("/login");
  }, [navigate]);

  return (
    <AuthContext.Provider
      value={{ user, token, isLoading, login, loginFromGoogle, logout, applyTokens }}
    >
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
