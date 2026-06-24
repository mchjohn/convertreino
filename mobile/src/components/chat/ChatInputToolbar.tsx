import { StyleSheet, Text, View } from "react-native";
import {
  Composer,
  InputToolbar,
  Send,
  type ComposerProps,
  type IMessage,
  type InputToolbarProps,
  type SendProps,
} from "react-native-gifted-chat";

import { chatColors, colors, radius, spacing } from "@/theme/tokens";

const PLACEHOLDER = "Pergunte sobre seus treinos";

export function ChatInputToolbar(props: InputToolbarProps<IMessage>) {
  return (
    <InputToolbar
      {...props}
      containerStyle={styles.toolbarContainer}
      primaryStyle={styles.toolbarPrimary}
      renderComposer={renderComposer}
      renderSend={renderSend}
    />
  );
}

function renderComposer(props: ComposerProps) {
  return (
    <Composer
      {...props}
      textInputProps={{
        ...props.textInputProps,
        placeholder: PLACEHOLDER,
        placeholderTextColor: chatColors.placeholder,
        style: [styles.composer, props.textInputProps?.style],
      }}
    />
  );
}

function renderSend(props: SendProps<IMessage>) {
  return (
    <Send {...props} containerStyle={styles.sendContainer}>
      <View style={styles.sendButton}>
        <Text style={styles.sendIcon}>↑</Text>
      </View>
    </Send>
  );
}

const styles = StyleSheet.create({
  toolbarContainer: {
    backgroundColor: chatColors.background,
    borderTopWidth: 0,
    paddingHorizontal: spacing.md,
    paddingTop: spacing.sm,
    paddingBottom: spacing.sm,
  },
  toolbarPrimary: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: chatColors.surface,
    borderWidth: 1,
    borderColor: chatColors.border,
    borderRadius: radius.chatInput,
    paddingLeft: spacing.md,
    paddingRight: spacing.xs,
    minHeight: 52,
  },
  composer: {
    backgroundColor: "transparent",
    borderWidth: 0,
    color: chatColors.text,
    marginTop: 0,
    marginBottom: 0,
    paddingTop: spacing.sm,
    paddingBottom: spacing.sm,
    paddingHorizontal: 0,
    lineHeight: 22,
  },
  sendContainer: {
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 0,
    marginLeft: spacing.xs,
  },
  sendButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
  },
  sendIcon: {
    color: colors.onPrimary,
    fontSize: 20,
    fontWeight: "700",
    lineHeight: 22,
    marginTop: -2,
  },
});
