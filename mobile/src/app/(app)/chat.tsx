import { useCallback, useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import { GiftedChat, type IMessage } from "react-native-gifted-chat";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import "dayjs/locale/pt-br";

import { useAuth } from "@/context/AuthContext";
import {
  createAssistantGiftedMessage,
  toApiMessages,
} from "@/lib/chatMappers";
import { ApiError } from "@/services/apiClient";
import { sendChatMessage } from "@/services/chatService";
import { giftedChatUsers } from "@/types/giftedChat";

export default function ChatScreen() {
  const { state, handleUnauthorized } = useAuth();
  const insets = useSafeAreaInsets();
  const headerHeight = insets.top;
  const safeAreaBottom = insets.bottom;
  const [messages, setMessages] = useState<IMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);

  const handleSend = useCallback(
    async (outgoing: IMessage[] = []) => {
      if (state.status !== "authenticated") {
        return;
      }

      const latest = outgoing[0];
      if (!latest?.text?.trim()) {
        return;
      }

      setErrorBanner(null);
      const updatedMessages = GiftedChat.append(messages, outgoing);
      setMessages(updatedMessages);
      setIsLoading(true);

      try {
        const history = toApiMessages(updatedMessages);
        const response = await sendChatMessage(state.session.accessToken, history);
        const assistantMessage = createAssistantGiftedMessage(response.message.content);
        setMessages((previous) => GiftedChat.append(previous, [assistantMessage]));
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          await handleUnauthorized();
          return;
        }
        const llmLimitMessage =
          "Limite do serviço de IA atingido. Tente novamente mais tarde.";
        const message =
          error instanceof ApiError
            ? error.status === 502
              ? error.detail === "LLM quota exceeded" ||
                error.detail === "LLM rate limit exceeded"
                ? llmLimitMessage
                : "Serviço temporariamente indisponível. Tente novamente."
              : error.status === 422
                ? "Não foi possível enviar a mensagem."
                : (error.detail ?? error.message)
            : "Sem conexão. Tente novamente.";
        setErrorBanner(message);
      } finally {
        setIsLoading(false);
      }
    },
    [state, messages, handleUnauthorized],
  );

  if (state.status !== "authenticated") {
    return null;
  }

  return (
    <View style={[styles.container, { paddingBottom: safeAreaBottom + 16 }]}>
      {errorBanner ? (
        <View style={styles.banner}>
          <Text style={styles.bannerText}>{errorBanner}</Text>
        </View>
      ) : null}
      <GiftedChat
        messages={messages}
        onSend={(outgoing) => void handleSend(outgoing)}
        user={giftedChatUsers.user}
        isTyping={isLoading}
        renderAvatar={() => null}
        locale="pt-br"
        textInputProps={{ placeholder: "Pergunte sobre seus treinos..." }}
        keyboardAvoidingViewProps={{ keyboardVerticalOffset: headerHeight }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#ffffff",
  },
  banner: {
    backgroundColor: "#fef2f2",
    borderBottomColor: "#fecaca",
    borderBottomWidth: 1,
    paddingHorizontal: 16,
    paddingVertical: 10,
  },
  bannerText: {
    color: "#b91c1c",
    textAlign: "center",
  },
});
