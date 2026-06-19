import { buildStravaAuthorizationUrl } from "@/lib/stravaAuth";

describe("buildStravaAuthorizationUrl", () => {
  it("CN-2: monta URL com parâmetros obrigatórios", () => {
    const url = buildStravaAuthorizationUrl({
      clientId: "12345",
      redirectUri: "convertreino://oauth/callback",
    });

    expect(url).toContain("https://www.strava.com/oauth/authorize?");
    expect(url).toContain("client_id=12345");
    expect(url).toContain("redirect_uri=convertreino%3A%2F%2Foauth%2Fcallback");
    expect(url).toContain("response_type=code");
    expect(url).toContain("scope=read%2Cactivity%3Aread_all");
    expect(url).toContain("approval_prompt=auto");
  });
});
