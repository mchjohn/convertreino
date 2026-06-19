import { fireEvent, render, waitFor } from "@testing-library/react-native";

import LoginScreen from "@/app/(auth)/login";
import { AuthProvider } from "@/context/AuthContext";
import * as authService from "@/services/authService";

jest.mock("@/services/authService", () => ({
  loadSession: jest.fn(),
  clearSession: jest.fn(),
  isSessionValid: jest.fn(),
  startStravaLogin: jest.fn(),
}));

describe("LoginScreen", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (authService.loadSession as jest.Mock).mockResolvedValue(null);
  });

  it("CN-1: exibe botão Conectar com Strava", async () => {
    const { findByText } = render(
      <AuthProvider>
        <LoginScreen />
      </AuthProvider>,
    );

    expect(await findByText("Conectar com Strava")).toBeTruthy();
    expect(await findByText("ConverTreino")).toBeTruthy();
  });

  it("CN-2: aciona login ao tocar no botão", async () => {
    (authService.startStravaLogin as jest.Mock).mockResolvedValue({
      userId: "user-1",
      accessToken: "jwt",
      expiresAt: Date.now() + 60_000,
    });

    const { findByText } = render(
      <AuthProvider>
        <LoginScreen />
      </AuthProvider>,
    );

    fireEvent.press(await findByText("Conectar com Strava"));

    await waitFor(() => {
      expect(authService.startStravaLogin).toHaveBeenCalled();
    });
  });
});
