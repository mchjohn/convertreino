import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { ApiError } from "@/services/apiClient";
import * as authService from "@/services/authService";
import { syncStravaActivities } from "@/services/syncService";
import type { AuthSession } from "@/types/auth";

export type AuthState =
  | { status: "loading" }
  | { status: "unauthenticated"; message?: string }
  | { status: "syncing"; session: AuthSession }
  | { status: "authenticated"; session: AuthSession };

type AuthContextValue = {
  state: AuthState;
  login: () => Promise<void>;
  logout: () => Promise<void>;
  handleUnauthorized: () => Promise<void>;
  completeSync: (session: AuthSession) => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ status: "loading" });

  const logout = useCallback(async () => {
    await authService.clearSession();
    setState({ status: "unauthenticated" });
  }, []);

  const handleUnauthorized = useCallback(async () => {
    await authService.clearSession();
    setState({
      status: "unauthenticated",
      message: "Sua sessão expirou. Conecte-se novamente com o Strava.",
    });
  }, []);

  const completeSync = useCallback((session: AuthSession) => {
    setState({ status: "authenticated", session });
  }, []);

  useEffect(() => {
    let active = true;

    async function restore() {
      const session = await authService.loadSession();
      if (!active) {
        return;
      }
      if (session) {
        setState({ status: "authenticated", session });
      } else {
        setState({ status: "unauthenticated" });
      }
    }

    void restore();
    return () => {
      active = false;
    };
  }, []);

  const login = useCallback(async () => {
    try {
      const session = await authService.startStravaLogin();
      setState({ status: "syncing", session });
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        await handleUnauthorized();
        return;
      }
      const message =
        error instanceof ApiError
          ? (error.detail ?? "Falha ao conectar Strava")
          : error instanceof Error && error.message === "OAuth cancelado"
            ? undefined
            : error instanceof Error
              ? error.message
              : "Falha ao conectar Strava";
      setState({ status: "unauthenticated", message });
    }
  }, [handleUnauthorized]);

  const value = useMemo(
    () => ({
      state,
      login,
      logout,
      handleUnauthorized,
      completeSync,
    }),
    [state, login, logout, handleUnauthorized, completeSync],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}

export async function retrySync(
  session: AuthSession,
  handleUnauthorized: () => Promise<void>,
): Promise<{ warning?: string }> {
  try {
    await syncStravaActivities(session.userId, session.accessToken);
    return {};
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      await handleUnauthorized();
      throw error;
    }
    const warning =
      error instanceof ApiError
        ? error.detail ?? "Falha ao importar atividades."
        : "Sem conexão. Tente novamente.";
    return { warning };
  }
}
