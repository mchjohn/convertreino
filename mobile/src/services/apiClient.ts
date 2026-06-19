import { API_BASE_URL } from "@/config/env";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly detail?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit & { accessToken?: string } = {},
): Promise<T> {
  const { accessToken, headers: initHeaders, body, ...rest } = options;
  const headers = new Headers(initHeaders);

  if (body !== undefined && body !== null) {
    headers.set("Content-Type", "application/json");
  }
  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...rest,
      body,
      headers,
    });
  } catch {
    throw new ApiError("Sem conexão. Tente novamente.", 0);
  }

  if (!response.ok) {
    let detail: string | undefined;
    try {
      const errorBody = (await response.json()) as { detail?: string | string[] };
      if (typeof errorBody.detail === "string") {
        detail = errorBody.detail;
      } else if (Array.isArray(errorBody.detail)) {
        detail = errorBody.detail.join(", ");
      }
    } catch {
      detail = undefined;
    }
    throw new ApiError(detail ?? response.statusText, response.status, detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}
