import * as SecureStore from "expo-secure-store";
import * as WebBrowser from "expo-web-browser";
import * as Linking from "expo-linking";

import {
  STRAVA_CLIENT_ID,
  STRAVA_REDIRECT_URI,
} from "@/config/env";
import { buildStravaAuthorizationUrl } from "@/lib/stravaAuth";
import type { AuthSession, TokenResponse } from "@/types/auth";
import { apiFetch } from "@/services/apiClient";

WebBrowser.maybeCompleteAuthSession();

const SESSION_KEY = "convertreino.auth.session";

function sessionFromTokenResponse(response: TokenResponse): AuthSession {
  return {
    userId: response.user_id,
    accessToken: response.access_token,
    expiresAt: Date.now() + response.expires_in * 1000,
  };
}

export function isSessionValid(session: AuthSession): boolean {
  return session.expiresAt > Date.now();
}

export async function loadSession(): Promise<AuthSession | null> {
  const raw = await SecureStore.getItemAsync(SESSION_KEY);
  if (!raw) {
    return null;
  }

  const session = JSON.parse(raw) as AuthSession;
  if (!isSessionValid(session)) {
    await SecureStore.deleteItemAsync(SESSION_KEY);
    return null;
  }

  return session;
}

export async function clearSession(): Promise<void> {
  await SecureStore.deleteItemAsync(SESSION_KEY);
}

async function persistSession(session: AuthSession): Promise<void> {
  await SecureStore.setItemAsync(SESSION_KEY, JSON.stringify(session));
}

async function exchangeCodeForSession(code: string): Promise<AuthSession> {
  const response = await apiFetch<TokenResponse>("/auth/strava/token", {
    method: "POST",
    body: JSON.stringify({ code }),
  });
  const session = sessionFromTokenResponse(response);
  await persistSession(session);
  return session;
}

export async function startStravaLogin(): Promise<AuthSession> {
  const authUrl = buildStravaAuthorizationUrl({
    clientId: STRAVA_CLIENT_ID,
    redirectUri: STRAVA_REDIRECT_URI,
  });

  const result = await WebBrowser.openAuthSessionAsync(authUrl, STRAVA_REDIRECT_URI);

  if (result.type !== "success") {
    throw new Error("OAuth cancelado");
  }

  const parsed = Linking.parse(result.url);
  const code = parsed.queryParams?.code;
  if (!code || Array.isArray(code)) {
    throw new Error("Falha ao conectar Strava");
  }

  return exchangeCodeForSession(code);
}
