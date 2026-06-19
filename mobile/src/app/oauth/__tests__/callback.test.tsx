import { render, waitFor } from "@testing-library/react-native";

const mockReplace = jest.fn();
const mockCompleteOAuthLogin = jest.fn();

jest.mock("expo-router", () => ({
  router: {
    replace: (...args: unknown[]) => mockReplace(...args),
  },
  useLocalSearchParams: jest.fn(),
}));

jest.mock("@/app/_layout", () => {
  const React = require("react");
  const { View } = require("react-native");
  return {
    LoadingScreen: () => React.createElement(View, { testID: "loading-screen" }),
  };
});

jest.mock("@/context/AuthContext", () => ({
  useAuth: () => ({
    completeOAuthLogin: mockCompleteOAuthLogin,
  }),
}));

import { useLocalSearchParams } from "expo-router";
import OAuthCallbackScreen from "@/app/oauth/callback";

const mockUseLocalSearchParams = useLocalSearchParams as jest.Mock;

describe("OAuthCallbackScreen", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockCompleteOAuthLogin.mockResolvedValue(undefined);
  });

  it("com code válido chama completeOAuthLogin e redireciona para /", async () => {
    mockUseLocalSearchParams.mockReturnValue({ code: "oauth-code" });

    render(<OAuthCallbackScreen />);

    await waitFor(() => {
      expect(mockCompleteOAuthLogin).toHaveBeenCalledWith("oauth-code");
      expect(mockReplace).toHaveBeenCalledWith("/");
    });
  });

  it("sem code redireciona para / sem chamar troca", async () => {
    mockUseLocalSearchParams.mockReturnValue({});

    render(<OAuthCallbackScreen />);

    await waitFor(() => {
      expect(mockCompleteOAuthLogin).not.toHaveBeenCalled();
      expect(mockReplace).toHaveBeenCalledWith("/");
    });
  });
});
