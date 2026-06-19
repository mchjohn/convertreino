import { useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";

import { useAuth } from "@/context/AuthContext";

export default function LoginScreen() {
  const { state, login } = useAuth();
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
    <View style={styles.container}>
      <Text style={styles.title}>ConverTreino</Text>
      <Text style={styles.subtitle}>Conecte sua conta Strava para conversar sobre seus treinos.</Text>
      {message ? <Text style={styles.error}>{message}</Text> : null}
      <Pressable
        style={[styles.button, loading && styles.buttonDisabled]}
        onPress={() => void handleLogin()}
        disabled={loading}
      >
        {loading ? (
          <ActivityIndicator color="#ffffff" />
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
    padding: 24,
    backgroundColor: "#ffffff",
  },
  title: {
    fontSize: 32,
    fontWeight: "700",
    color: "#111827",
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: "#6b7280",
    textAlign: "center",
    marginBottom: 24,
  },
  error: {
    color: "#b91c1c",
    marginBottom: 16,
    textAlign: "center",
  },
  button: {
    backgroundColor: "#fc4c02",
    paddingHorizontal: 24,
    paddingVertical: 14,
    borderRadius: 8,
    minWidth: 220,
    alignItems: "center",
  },
  buttonDisabled: {
    opacity: 0.7,
  },
  buttonText: {
    color: "#ffffff",
    fontSize: 16,
    fontWeight: "600",
  },
});
