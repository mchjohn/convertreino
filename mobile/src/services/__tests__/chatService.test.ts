import { sendChatMessage } from "@/services/chatService";

describe("chatService", () => {
  beforeEach(() => {
    global.fetch = jest.fn();
  });

  it("CN-4: envia histórico para POST /chat/messages", async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        message: { role: "assistant", content: "Sua corrida mais longa foi 10 km." },
        tool_calls_made: ["get_longest_run"],
      }),
    });

    const response = await sendChatMessage("jwt", [
      { role: "user", content: "Qual minha corrida mais longa?" },
    ]);

    expect(response.message.content).toContain("10 km");
    const [url, init] = (global.fetch as jest.Mock).mock.calls[0];
    expect(url).toBe("http://localhost:8000/chat/messages");
    expect(init.headers.get("Authorization")).toBe("Bearer jwt");
    expect(JSON.parse(init.body)).toEqual({
      messages: [{ role: "user", content: "Qual minha corrida mais longa?" }],
    });
  });

  it("CN-5: preserva histórico multi-turn no body", async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        message: { role: "assistant", content: "ok" },
        tool_calls_made: [],
      }),
    });

    await sendChatMessage("jwt", [
      { role: "user", content: "Oi" },
      { role: "assistant", content: "Olá" },
      { role: "user", content: "E agora?" },
    ]);

    const body = JSON.parse((global.fetch as jest.Mock).mock.calls[0][1].body);
    expect(body.messages).toHaveLength(3);
    expect(body.messages.at(-1)).toEqual({ role: "user", content: "E agora?" });
  });

  it("CE-3: propaga erro 502", async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: false,
      status: 502,
      statusText: "Bad Gateway",
      json: async () => ({ detail: "LLM provider unavailable" }),
    });

    await expect(sendChatMessage("jwt", [{ role: "user", content: "oi" }])).rejects.toMatchObject({
      status: 502,
    });
  });

  it("CE-5: propaga erro de rede", async () => {
    (global.fetch as jest.Mock).mockRejectedValue(new Error("offline"));
    await expect(sendChatMessage("jwt", [{ role: "user", content: "oi" }])).rejects.toMatchObject({
      status: 0,
    });
  });
});
