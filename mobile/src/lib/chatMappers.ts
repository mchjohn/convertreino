import type { IMessage } from "react-native-gifted-chat";

import type { ChatMessage } from "@/types/chat";
import {
  ASSISTANT_GIFTED_ID,
  USER_GIFTED_ID,
  giftedChatUsers,
} from "@/types/giftedChat";

let messageCounter = 0;

function nextMessageId(): string {
  messageCounter += 1;
  return `msg-${messageCounter}-${Date.now()}`;
}

export function createUserGiftedMessage(text: string): IMessage {
  return {
    _id: nextMessageId(),
    text,
    createdAt: new Date(),
    user: giftedChatUsers.user,
  };
}

export function createAssistantGiftedMessage(text: string): IMessage {
  return {
    _id: nextMessageId(),
    text,
    createdAt: new Date(),
    user: giftedChatUsers.assistant,
  };
}

export function toGiftedMessages(messages: ChatMessage[]): IMessage[] {
  return messages.map((message) => {
    if (message.role === "user") {
      return createUserGiftedMessage(message.content);
    }
    return createAssistantGiftedMessage(message.content);
  });
}

function giftedRole(message: IMessage): ChatMessage["role"] | null {
  const userId = message.user?._id;
  if (userId === USER_GIFTED_ID) {
    return "user";
  }
  if (userId === ASSISTANT_GIFTED_ID) {
    return "assistant";
  }
  return null;
}

export function toApiMessages(gifted: IMessage[]): ChatMessage[] {
  return gifted
    .map((message) => {
      const role = giftedRole(message);
      if (role === null) {
        return null;
      }
      const content = message.text?.trim() ?? "";
      if (!content) {
        return null;
      }
      return { role, content };
    })
    .filter((message): message is ChatMessage => message !== null);
}
