function requireEnv(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value;
}

export const API_BASE_URL = requireEnv("EXPO_PUBLIC_API_BASE_URL");
export const STRAVA_CLIENT_ID = requireEnv("EXPO_PUBLIC_STRAVA_CLIENT_ID");
export const STRAVA_REDIRECT_URI = requireEnv("EXPO_PUBLIC_STRAVA_REDIRECT_URI");
export const STRAVA_SCOPE = "read,activity:read_all";
export const STRAVA_AUTHORIZE_URL = "https://www.strava.com/oauth/authorize";
