import { apiFetch, ApiError } from "@/services/apiClient";

describe("apiClient", () => {
  beforeEach(() => {
    global.fetch = jest.fn();
  });

  it("CN-4: envia Authorization Bearer quando accessToken é fornecido", async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ ok: true }),
    });

    await apiFetch("/chat/messages", {
      method: "POST",
      accessToken: "jwt-token",
      body: JSON.stringify({ messages: [] }),
    });

    const [, init] = (global.fetch as jest.Mock).mock.calls[0];
    expect(init.headers.get("Authorization")).toBe("Bearer jwt-token");
    expect(init.headers.get("Content-Type")).toBe("application/json");
  });

  it("CE-3: lança ApiError com detail em resposta não ok", async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: false,
      status: 502,
      statusText: "Bad Gateway",
      json: async () => ({ detail: "LLM provider unavailable" }),
    });

    await expect(apiFetch("/chat/messages")).rejects.toMatchObject({
      status: 502,
      detail: "LLM provider unavailable",
    });
  });

  it("CE-5: lança ApiError de rede quando fetch falha", async () => {
    (global.fetch as jest.Mock).mockRejectedValue(new Error("network"));

    await expect(apiFetch("/health")).rejects.toBeInstanceOf(ApiError);
    await expect(apiFetch("/health")).rejects.toMatchObject({
      message: "Sem conexão. Tente novamente.",
      status: 0,
    });
  });
});
