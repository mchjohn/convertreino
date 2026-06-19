import { apiFetch } from "@/services/apiClient";
import type { ChatMessage, ChatResponse } from "@/types/chat";

export async function sendChatMessage(
  accessToken: string,
  messages: ChatMessage[],
): Promise<ChatResponse> {
  return apiFetch<ChatResponse>("/chat/messages", {
    method: "POST",
    accessToken,
    body: JSON.stringify({ messages }),
  });
}
