process.env.EXPO_PUBLIC_API_BASE_URL = "http://localhost:8000";
process.env.EXPO_PUBLIC_STRAVA_CLIENT_ID = "test-client-id";
process.env.EXPO_PUBLIC_STRAVA_REDIRECT_URI = "convertreino://oauth/callback";

import "@testing-library/jest-native/extend-expect";

jest.mock("expo-secure-store", () => ({
  getItemAsync: jest.fn(),
  setItemAsync: jest.fn(),
  deleteItemAsync: jest.fn(),
}));

jest.mock("expo-web-browser", () => ({
  maybeCompleteAuthSession: jest.fn(),
  openAuthSessionAsync: jest.fn(),
}));

jest.mock("expo-linking", () => ({
  parse: jest.fn(),
}));

jest.mock("react-native-safe-area-context", () => {
  const React = require("react");
  const { View } = require("react-native");
  return {
    SafeAreaProvider: ({ children }: { children: React.ReactNode }) =>
      React.createElement(View, null, children),
    useSafeAreaInsets: () => ({ top: 0, bottom: 0, left: 0, right: 0 }),
  };
});

jest.mock("react-native-gifted-chat", () => {
  const React = require("react");
  const { View, Text } = require("react-native");
  const GiftedChat = ({
    messages,
    onSend,
    isTyping,
    renderChatEmpty,
  }: {
    messages: unknown[];
    onSend: (m: unknown[]) => void;
    isTyping?: boolean;
    renderChatEmpty?: () => React.ReactNode;
  }) =>
    React.createElement(
      View,
      { testID: "gifted-chat" },
      messages.length === 0 && renderChatEmpty ? renderChatEmpty() : null,
      React.createElement(Text, { testID: "message-count" }, String(messages.length)),
      React.createElement(Text, { testID: "is-typing" }, String(Boolean(isTyping))),
      React.createElement(
        Text,
        {
          testID: "send-trigger",
          onPress: () => onSend([{ _id: "1", text: "Olá", user: { _id: 1 } }]),
        },
        "send",
      ),
    );
  GiftedChat.append = (current: unknown[] = [], next: unknown[] = []) => [...next, ...current];
  const Bubble = ({ children }: { children?: React.ReactNode }) =>
    React.createElement(View, { testID: "bubble" }, children);
  return { GiftedChat, Bubble };
});
