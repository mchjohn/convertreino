import { ActivityIndicator, StyleSheet, View } from "react-native";
import { Slot } from "expo-router";
import { KeyboardProvider } from "react-native-keyboard-controller";
import {
  SafeAreaProvider,
  useSafeAreaInsets,
} from "react-native-safe-area-context";

import { AuthProvider } from "@/context/AuthContext";
import { screenSafePadding } from "@/theme/safeArea";
import { colors } from "@/theme/tokens";

export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <AuthProvider>
        <KeyboardProvider>
          <Slot />
        </KeyboardProvider>
      </AuthProvider>
    </SafeAreaProvider>
  );
}

export const styles = StyleSheet.create({
  loading: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.tertiary,
  },
});

export function LoadingScreen() {
  const insets = useSafeAreaInsets();

  return (
    <View style={[styles.loading, screenSafePadding(insets)]}>
      <ActivityIndicator size="large" color={colors.primary} />
    </View>
  );
}
