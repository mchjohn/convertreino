import { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { retrySync, useAuth } from "@/context/AuthContext";
import { screenSafePadding } from "@/theme/safeArea";
import {
  colors,
  radius,
  spacing,
  touchTarget,
  typography,
} from "@/theme/tokens";

export function SyncScreen() {
  const { state, handleUnauthorized, completeSync } = useAuth();
  const insets = useSafeAreaInsets();
  const [error, setError] = useState<string | null>(null);
  const [retrying, setRetrying] = useState(false);

  useEffect(() => {
    if (state.status !== "syncing") {
      return;
    }

    let active = true;

    async function sync() {
      const result = await retrySync(state.session, handleUnauthorized);
      if (!active) {
        return;
      }
      if (result.warning) {
        setError(result.warning);
        return;
      }
      completeSync(state.session);
    }

    void sync();
    return () => {
      active = false;
    };
  }, [state, handleUnauthorized, completeSync]);

  if (state.status !== "syncing") {
    return null;
  }

  async function handleRetry() {
    setRetrying(true);
    setError(null);
    const result = await retrySync(state.session, handleUnauthorized);
    setRetrying(false);
    if (!result.warning) {
      completeSync(state.session);
      return;
    }
    setError(result.warning);
  }

  function handleContinue() {
    completeSync(state.session);
  }

  return (
    <View style={[styles.container, screenSafePadding(insets)]}>
      {!error ? (
        <>
          <ActivityIndicator size="large" color={colors.primary} />
          <Text style={styles.title}>Importando atividades...</Text>
        </>
      ) : (
        <>
          <Text style={styles.title}>Falha na importação</Text>
          <Text style={styles.message}>{error}</Text>
          <Pressable
            style={styles.button}
            onPress={() => void handleRetry()}
            disabled={retrying}
          >
            {retrying ? (
              <ActivityIndicator color={colors.onPrimary} />
            ) : (
              <Text style={styles.buttonText}>Tentar novamente</Text>
            )}
          </Pressable>
          <Pressable style={styles.secondaryButton} onPress={handleContinue}>
            <Text style={styles.secondaryButtonText}>Continuar mesmo assim</Text>
          </Pressable>
        </>
      )}
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
    ...typography.title,
    marginTop: spacing.md,
    textAlign: "center",
  },
  message: {
    ...typography.body,
    marginTop: spacing.sm,
    textAlign: "center",
  },
  button: {
    marginTop: spacing.lg,
    backgroundColor: colors.primary,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    borderRadius: radius.button,
    minHeight: touchTarget.minHeight,
    minWidth: touchTarget.minWidth,
    alignItems: "center",
    justifyContent: "center",
  },
  buttonText: {
    ...typography.label,
  },
  secondaryButton: {
    marginTop: spacing.sm + spacing.xs,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    minHeight: touchTarget.minHeight,
    justifyContent: "center",
  },
  secondaryButtonText: {
    ...typography.bodyStrong,
    fontWeight: "500",
  },
});
