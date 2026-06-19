import * as Linking from "expo-linking";
import * as SecureStore from "expo-secure-store";
import * as WebBrowser from "expo-web-browser";

import {
  clearSession,
  isSessionValid,
  loadSession,
  startStravaLogin,
} from "@/services/authService";
import type { AuthSession } from "@/types/auth";

describe("authService", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    global.fetch = jest.fn();
  });

  const validSession: AuthSession = {
    userId: "user-1",
    accessToken: "jwt",
    expiresAt: Date.now() + 60_000,
  };

  it("CN-1: loadSession retorna null sem sessão persistida", async () => {
    (SecureStore.getItemAsync as jest.Mock).mockResolvedValue(null);
    await expect(loadSession()).resolves.toBeNull();
  });

  it("CN-6: loadSession restaura sessão válida", async () => {
    (SecureStore.getItemAsync as jest.Mock).mockResolvedValue(JSON.stringify(validSession));
    await expect(loadSession()).resolves.toEqual(validSession);
  });

  it("CN-6: loadSession descarta sessão expirada", async () => {
    const expired = { ...validSession, expiresAt: Date.now() - 1 };
    (SecureStore.getItemAsync as jest.Mock).mockResolvedValue(JSON.stringify(expired));
    await expect(loadSession()).resolves.toBeNull();
    expect(SecureStore.deleteItemAsync).toHaveBeenCalled();
  });

  it("CN-2: startStravaLogin persiste sessão após OAuth", async () => {
    (WebBrowser.openAuthSessionAsync as jest.Mock).mockResolvedValue({
      type: "success",
      url: "convertreino://oauth/callback?code=oauth-code",
    });
    (Linking.parse as jest.Mock).mockReturnValue({ queryParams: { code: "oauth-code" } });
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        user_id: "user-1",
        access_token: "jwt",
        token_type: "bearer",
        expires_in: 3600,
      }),
    });

    const session = await startStravaLogin();

    expect(session.userId).toBe("user-1");
    expect(session.accessToken).toBe("jwt");
    expect(SecureStore.setItemAsync).toHaveBeenCalled();
    expect(global.fetch).toHaveBeenCalledWith(
      "http://localhost:8000/auth/strava/token",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("CB-2: startStravaLogin cancelado não persiste sessão", async () => {
    (WebBrowser.openAuthSessionAsync as jest.Mock).mockResolvedValue({ type: "cancel" });
    await expect(startStravaLogin()).rejects.toThrow("OAuth cancelado");
    expect(SecureStore.setItemAsync).not.toHaveBeenCalled();
  });

  it("CE-1: startStravaLogin propaga erro da troca de code", async () => {
    (WebBrowser.openAuthSessionAsync as jest.Mock).mockResolvedValue({
      type: "success",
      url: "convertreino://oauth/callback?code=bad",
    });
    (Linking.parse as jest.Mock).mockReturnValue({ queryParams: { code: "bad" } });
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: false,
      status: 400,
      statusText: "Bad Request",
      json: async () => ({ detail: "invalid code" }),
    });

    await expect(startStravaLogin()).rejects.toMatchObject({ status: 400 });
    expect(SecureStore.setItemAsync).not.toHaveBeenCalled();
  });

  it("isSessionValid retorna false para sessão expirada", () => {
    expect(isSessionValid({ ...validSession, expiresAt: Date.now() - 1 })).toBe(false);
    expect(isSessionValid(validSession)).toBe(true);
  });

  it("clearSession remove entrada do SecureStore", async () => {
    await clearSession();
    expect(SecureStore.deleteItemAsync).toHaveBeenCalledWith("convertreino.auth.session");
  });
});
