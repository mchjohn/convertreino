import { STRAVA_AUTHORIZE_URL, STRAVA_SCOPE } from "@/config/env";

export function buildStravaAuthorizationUrl(params: {
  clientId: string;
  redirectUri: string;
  scope?: string;
}): string {
  const query = new URLSearchParams({
    client_id: params.clientId,
    redirect_uri: params.redirectUri,
    response_type: "code",
    scope: params.scope ?? STRAVA_SCOPE,
    approval_prompt: "auto",
  });

  return `${STRAVA_AUTHORIZE_URL}?${query.toString()}`;
}
