import { useEffect, useRef } from "react";
import { router, useLocalSearchParams } from "expo-router";

import { LoadingScreen } from "@/app/_layout";
import { useAuth } from "@/context/AuthContext";

export default function OAuthCallbackScreen() {
  const { code } = useLocalSearchParams<{ code?: string }>();
  const { completeOAuthLogin } = useAuth();
  const handled = useRef(false);

  useEffect(() => {
    if (handled.current) {
      return;
    }
    handled.current = true;

    async function handleCallback() {
      if (!code || Array.isArray(code)) {
        router.replace("/");
        return;
      }

      await completeOAuthLogin(code);
      router.replace("/");
    }

    void handleCallback();
  }, [code, completeOAuthLogin]);

  return <LoadingScreen />;
}
