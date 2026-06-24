import {
  createAssistantGiftedMessage,
  createUserGiftedMessage,
  toApiMessages,
  toGiftedMessages,
} from "@/lib/chatMappers";
import { ASSISTANT_GIFTED_ID, USER_GIFTED_ID } from "@/types/giftedChat";

describe("chatMappers", () => {
  it("toGiftedMessages mapeia roles para usuários GiftedChat", () => {
    const messages = toGiftedMessages([
      { role: "user", content: "Oi" },
      { role: "assistant", content: "Olá" },
    ]);

    expect(messages).toHaveLength(2);
    expect(messages[0].user._id).toBe(USER_GIFTED_ID);
    expect(messages[1].user._id).toBe(ASSISTANT_GIFTED_ID);
    expect(messages[0].text).toBe("Oi");
  });

  it("toApiMessages filtra texto vazio e roles desconhecidas", () => {
    const apiMessages = toApiMessages([
      createUserGiftedMessage("  válida  "),
      createUserGiftedMessage("   "),
      createAssistantGiftedMessage("resposta"),
      {
        _id: "x",
        text: "system",
        createdAt: new Date(),
        user: { _id: 99, name: "system" },
      },
    ]);

    expect(apiMessages).toEqual([
      { role: "assistant", content: "resposta" },
      { role: "user", content: "válida" },
    ]);
  });

  it("toApiMessages envia histórico em ordem cronológica (mais antiga primeiro)", () => {
    const apiMessages = toApiMessages([
      createUserGiftedMessage("Quanto pedalei semana passada?"),
      createAssistantGiftedMessage("Você pedaleou 10 km essa semana."),
      createUserGiftedMessage("Quanto pedalei essa semana?"),
    ]);

    expect(apiMessages).toEqual([
      { role: "user", content: "Quanto pedalei essa semana?" },
      { role: "assistant", content: "Você pedaleou 10 km essa semana." },
      { role: "user", content: "Quanto pedalei semana passada?" },
    ]);
  });

  it("CB-3: createAssistantGiftedMessage expõe apenas content como text", () => {
    const message = createAssistantGiftedMessage("Resposta do assistente");
    expect(message.text).toBe("Resposta do assistente");
    expect(message.user._id).toBe(ASSISTANT_GIFTED_ID);
  });
});
