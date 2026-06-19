import { syncStravaActivities } from "@/services/syncService";

describe("syncService", () => {
  beforeEach(() => {
    global.fetch = jest.fn();
  });

  it("CN-3: chama POST /users/{id}/sync/strava com Bearer", async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        synced_count: 3,
        created_count: 2,
        updated_count: 1,
        skipped_count: 0,
      }),
    });

    const result = await syncStravaActivities("user-1", "jwt");

    expect(result.synced_count).toBe(3);
    const [url, init] = (global.fetch as jest.Mock).mock.calls[0];
    expect(url).toBe("http://localhost:8000/users/user-1/sync/strava");
    expect(init.method).toBe("POST");
    expect(init.headers.get("Authorization")).toBe("Bearer jwt");
  });

  it("CB-1: aceita contagens zeradas", async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        synced_count: 0,
        created_count: 0,
        updated_count: 0,
        skipped_count: 0,
      }),
    });

    const result = await syncStravaActivities("user-1", "jwt");
    expect(result.synced_count).toBe(0);
  });

  it("CE-2: propaga 401", async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: false,
      status: 401,
      statusText: "Unauthorized",
      json: async () => ({ detail: "Invalid or expired token" }),
    });

    await expect(syncStravaActivities("user-1", "jwt")).rejects.toMatchObject({ status: 401 });
  });

  it("CE-6: propaga 502 em falha de sync", async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: false,
      status: 502,
      statusText: "Bad Gateway",
      json: async () => ({ detail: "upstream error" }),
    });

    await expect(syncStravaActivities("user-1", "jwt")).rejects.toMatchObject({ status: 502 });
  });
});
