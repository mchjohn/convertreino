import { fireEvent, render, waitFor } from "@testing-library/react-native";

jest.mock("@/context/AuthContext", () => ({
  useAuth: jest.fn(),
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

import ChatScreen from "@/app/(app)/chat";
import { useAuth } from "@/context/AuthContext";

const mockUseAuth = useAuth as jest.Mock;

function renderChat() {
  return render(<ChatScreen />);
}

describe("ChatScreen", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    global.fetch = jest.fn();
    mockUseAuth.mockReturnValue({
      state: {
        status: "authenticated",
        session: {
          userId: "user-1",
          accessToken: "jwt",
          expiresAt: Date.now() + 60_000,
        },
      },
      login: jest.fn(),
      logout: jest.fn(),
      handleUnauthorized: jest.fn(),
      completeSync: jest.fn(),
    });
  });

  it("CN-4: renderiza GiftedChat autenticado", () => {
    const { getByTestId } = renderChat();
    expect(getByTestId("gifted-chat")).toBeTruthy();
  });

  it("CN-4: isTyping durante request", async () => {
    let resolveFetch: (value: unknown) => void = () => {};
    (global.fetch as jest.Mock).mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveFetch = resolve;
        }),
    );

    const { getByTestId } = renderChat();
    fireEvent.press(getByTestId("send-trigger"));

    await waitFor(() => {
      expect(getByTestId("is-typing").props.children).toBe("true");
    });

    resolveFetch({
      ok: true,
      status: 200,
      json: async () => ({
        message: { role: "assistant", content: "ok" },
        tool_calls_made: [],
      }),
    });

    await waitFor(() => {
      expect(getByTestId("is-typing").props.children).toBe("false");
    });
  });
});
