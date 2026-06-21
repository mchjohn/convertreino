import { useCallback, useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import { Bubble, GiftedChat, type IMessage } from "react-native-gifted-chat";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import "dayjs/locale/pt-br";

import { ChatEmptyState } from "@/components/chat/ChatEmptyState";
import { useAuth } from "@/context/AuthContext";
import {
  createAssistantGiftedMessage,
  toApiMessages,
} from "@/lib/chatMappers";
import { ApiError } from "@/services/apiClient";
import { sendChatMessage } from "@/services/chatService";
import { giftedChatUsers } from "@/types/giftedChat";
import { colors, radius, spacing, typography } from "@/theme/tokens";

export default function ChatScreen() {
  const { state, handleUnauthorized } = useAuth();
  const insets = useSafeAreaInsets();
  const keyboardVerticalOffset = insets.top + spacing.md;
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
          paddingTop: insets.top + spacing.md,
          paddingBottom: insets.bottom + spacing.md,
        },
      ]}
    >
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
        isSendButtonAlwaysVisible={false}
        renderAvatar={() => null}
        renderTime={() => null}
        renderChatEmpty={() => <ChatEmptyState />}
        messagesContainerStyle={styles.messagesContainer}
        textInputProps={{
          placeholder: "Pergunte sobre seus treinos...",
          placeholderTextColor: colors.muted,
          style: styles.textInput,
        }}
        renderBubble={(props) => (
          <Bubble
            {...props}
            wrapperStyle={{
              right: {
                backgroundColor: colors.primary,
                borderRadius: radius.bubble,
              },
              left: {
                backgroundColor: colors.tertiary,
                borderWidth: 1,
                borderColor: colors.border,
                borderRadius: radius.bubble,
              },
            }}
            textStyle={{
              right: { color: colors.onPrimary },
              left: { color: colors.secondary },
            }}
          />
        )}
        keyboardAvoidingViewProps={{ keyboardVerticalOffset }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.tertiary,
  },
  banner: {
    backgroundColor: colors.errorSurface,
    borderBottomColor: colors.errorBorder,
    borderBottomWidth: 1,
    paddingHorizontal: spacing.md,
    paddingVertical: 10,
  },
  bannerText: {
    ...typography.captionError,
    textAlign: "center",
  },
  messagesContainer: {
    backgroundColor: colors.tertiary,
    paddingTop: spacing.sm,
  },
  textInput: {
    backgroundColor: colors.inputBackground,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.input,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    color: colors.secondary,
  },
});
