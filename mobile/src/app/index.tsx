import { SyncScreen } from "@/components/SyncScreen";
import { useAuth } from "@/context/AuthContext";
import LoginScreen from "@/app/(auth)/login";
import ChatScreen from "@/app/(app)/chat";
import { LoadingScreen } from "@/app/_layout";

export default function Index() {
  const { state } = useAuth();

  if (state.status === "loading") {
    return <LoadingScreen />;
  }

  if (state.status === "unauthenticated") {
    return <LoginScreen />;
  }

  if (state.status === "syncing") {
    return <SyncScreen />;
  }

  return <ChatScreen />;
}
