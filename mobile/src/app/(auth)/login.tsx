import { useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { useAuth } from "@/context/AuthContext";
import { screenSafePadding } from "@/theme/safeArea";
import {
  colors,
  radius,
  spacing,
  touchTarget,
  typography,
} from "@/theme/tokens";

export default function LoginScreen() {
  const { state, login } = useAuth();
  const insets = useSafeAreaInsets();
  const [loading, setLoading] = useState(false);

  const message = state.status === "unauthenticated" ? state.message : undefined;

  async function handleLogin() {
    setLoading(true);
    try {
      await login();
    } finally {
      setLoading(false);
    }
  }

  return (
    <View style={[styles.container, screenSafePadding(insets)]}>
      <Text style={styles.title}>ConverTreino</Text>
      <Text style={styles.subtitle}>
        Conecte sua conta Strava para conversar sobre seus treinos.
      </Text>
      {message ? (
        <Text accessibilityRole="alert" style={styles.error}>
          {message}
        </Text>
      ) : null}
      <Pressable
        accessibilityLabel="Conectar com Strava"
        style={[styles.button, loading && styles.buttonDisabled]}
        onPress={() => void handleLogin()}
        disabled={loading}
      >
        {loading ? (
          <ActivityIndicator color={colors.onPrimary} />
        ) : (
          <Text style={styles.buttonText}>Conectar com Strava</Text>
        )}
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: spacing.lg,
    backgroundColor: colors.tertiary,
  },
  title: {
    ...typography.display,
    marginBottom: spacing.sm,
  },
  subtitle: {
    ...typography.body,
    textAlign: "center",
    marginBottom: spacing.lg,
  },
  error: {
    ...typography.captionError,
    textAlign: "center",
    marginBottom: spacing.md,
  },
  button: {
    backgroundColor: colors.primary,
    paddingHorizontal: spacing.lg,
    paddingVertical: 14,
    borderRadius: radius.button,
    minWidth: 220,
    minHeight: touchTarget.minHeight,
    alignItems: "center",
    justifyContent: "center",
  },
  buttonDisabled: {
    opacity: 0.7,
  },
  buttonText: {
    ...typography.label,
  },
});
