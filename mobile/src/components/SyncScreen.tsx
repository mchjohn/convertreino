import { useEffect, useState } from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from "react-native";

import { retrySync, useAuth } from "@/context/AuthContext";

export function SyncScreen() {
  const { state, handleUnauthorized, completeSync } = useAuth();
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
    <View style={styles.container}>
      {!error ? (
        <>
          <ActivityIndicator size="large" color="#fc4c02" />
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
            <Text style={styles.buttonText}>{retrying ? "Tentando..." : "Tentar novamente"}</Text>
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
    padding: 24,
    backgroundColor: "#ffffff",
  },
  title: {
    marginTop: 16,
    fontSize: 18,
    fontWeight: "600",
    color: "#111827",
    textAlign: "center",
  },
  message: {
    marginTop: 8,
    fontSize: 14,
    color: "#6b7280",
    textAlign: "center",
  },
  button: {
    marginTop: 24,
    backgroundColor: "#fc4c02",
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 8,
  },
  buttonText: {
    color: "#ffffff",
    fontWeight: "600",
  },
  secondaryButton: {
    marginTop: 12,
    paddingHorizontal: 20,
    paddingVertical: 12,
  },
  secondaryButtonText: {
    color: "#374151",
    fontWeight: "500",
  },
});
