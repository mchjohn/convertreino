import type { ExpoConfig } from "expo/config";

const config: ExpoConfig = {
  name: "ConverTreino",
  slug: "mobile",
  version: "1.0.0",
  orientation: "portrait",
  scheme: "convertreino",
  userInterfaceStyle: "automatic",
  ios: {
    supportsTablet: true,
  },
  android: {
    adaptiveIcon: {
      backgroundColor: "#E6F4FE",
    },
  },
  plugins: ["expo-router", "expo-secure-store"],
  experiments: {
    typedRoutes: true,
  },
};

export default config;
