import type { IMessage } from "react-native-gifted-chat";

export const USER_GIFTED_ID = 1;
export const ASSISTANT_GIFTED_ID = 2;

export const giftedChatUsers = {
  user: { _id: USER_GIFTED_ID, name: "Você" },
  assistant: { _id: ASSISTANT_GIFTED_ID, name: "ConverTreino" },
} as const;

export type GiftedChatUser = (typeof giftedChatUsers)[keyof typeof giftedChatUsers];

export type GiftedChatMessage = IMessage;
