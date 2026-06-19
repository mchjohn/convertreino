import type { ExpoConfig } from "expo/config";

const config: ExpoConfig = {
  name: "ConverTreino",
  slug: "convertreino",
  version: "1.0.0",
  orientation: "portrait",
  scheme: "convertreino",
  userInterfaceStyle: "automatic",
  ios: {
    supportsTablet: true,
    bundleIdentifier: "com.convertreino.mobile"
  },
  android: {
    adaptiveIcon: {
      backgroundColor: "#E6F4FE",
    },
    package: "com.convertreino.mobile"
  },
  plugins: ["expo-router", "expo-secure-store"],
  experiments: {
    typedRoutes: true,
  },
  extra: {
    eas: {
      projectId: "6a0dcd69-0253-49d8-8fe9-748cee0019f2"
    }
  }
};

export default config;
