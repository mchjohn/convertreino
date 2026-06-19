import { apiFetch } from "@/services/apiClient";
import type { SyncResult } from "@/types/sync";

export async function syncStravaActivities(
  userId: string,
  accessToken: string,
): Promise<SyncResult> {
  return apiFetch<SyncResult>(`/users/${userId}/sync/strava`, {
    method: "POST",
    accessToken,
  });
}
