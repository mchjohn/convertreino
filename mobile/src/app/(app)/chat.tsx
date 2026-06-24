import { useCallback, useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import { GiftedChat, type IMessage } from "react-native-gifted-chat";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { StatusBar } from "expo-status-bar";
import "dayjs/locale/pt-br";

import { ChatBubble } from "@/components/chat/ChatBubble";
import { ChatEmptyState } from "@/components/chat/ChatEmptyState";
import { ChatInputToolbar } from "@/components/chat/ChatInputToolbar";
import { useAuth } from "@/context/AuthContext";
import {
  createAssistantGiftedMessage,
  toApiMessages,
} from "@/lib/chatMappers";
import { ApiError } from "@/services/apiClient";
import { sendChatMessage } from "@/services/chatService";
import { giftedChatUsers } from "@/types/giftedChat";
import { chatColors, spacing, typography } from "@/theme/tokens";

export default function ChatScreen() {
  const { state, handleUnauthorized } = useAuth();
  const insets = useSafeAreaInsets();
  const keyboardVerticalOffset = insets.top;
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
    <View
      style={[
        styles.container,
        {
          paddingTop: insets.top,
          paddingBottom: insets.bottom,
        },
      ]}
    >
      <StatusBar style="light" />
      {errorBanner ? (
        <View accessibilityRole="alert" style={styles.banner}>
          <Text style={styles.bannerText}>{errorBanner}</Text>
        </View>
      ) : null}
      <GiftedChat
        messages={messages}
        onSend={(outgoing) => void handleSend(outgoing)}
        user={giftedChatUsers.user}
        isTyping={isLoading}
        locale="pt-br"
        isSendButtonAlwaysVisible
        renderAvatar={() => null}
        renderTime={() => null}
        renderChatEmpty={() => <ChatEmptyState />}
        renderBubble={(props) => <ChatBubble {...props} />}
        renderInputToolbar={(props) => <ChatInputToolbar {...props} />}
        messagesContainerStyle={styles.messagesContainer}
        listProps={{ contentContainerStyle: styles.listContent }}
        keyboardAvoidingViewProps={{ keyboardVerticalOffset }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: chatColors.background,
  },
  banner: {
    backgroundColor: chatColors.errorSurface,
    borderBottomColor: chatColors.errorBorder,
    borderBottomWidth: 1,
    paddingHorizontal: spacing.md,
    paddingVertical: 10,
  },
  bannerText: {
    ...typography.caption,
    color: chatColors.errorText,
    textAlign: "center",
  },
  messagesContainer: {
    backgroundColor: chatColors.background,
    paddingHorizontal: spacing.md,
    paddingTop: spacing.sm,
  },
  listContent: {
    flexGrow: 1,
  },
});
