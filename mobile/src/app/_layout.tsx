import { ActivityIndicator, StyleSheet, View } from "react-native";
import { Slot } from "expo-router";
import { KeyboardProvider } from "react-native-keyboard-controller";
import { SafeAreaProvider } from "react-native-safe-area-context";

import { AuthProvider } from "@/context/AuthContext";

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
    backgroundColor: "#ffffff",
  },
});

export function LoadingScreen() {
  return (
    <View style={styles.loading}>
      <ActivityIndicator size="large" color="#fc4c02" />
    </View>
  );
}
