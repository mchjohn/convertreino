import { Bubble, type BubbleProps, type IMessage } from "react-native-gifted-chat";

import { chatColors, colors, radius } from "@/theme/tokens";

export function ChatBubble(props: BubbleProps<IMessage>) {
  return (
    <Bubble
      {...props}
      wrapperStyle={{
        right: {
          backgroundColor: colors.primary,
          borderRadius: radius.chatUserBubble,
          marginVertical: 6,
        },
        left: {
          backgroundColor: chatColors.surface,
          borderWidth: 1,
          borderColor: chatColors.border,
          borderRadius: radius.chatAssistantBubble,
          marginVertical: 6,
        },
      }}
      textStyle={{
        right: { color: colors.onPrimary },
        left: { color: chatColors.text },
      }}
    />
  );
}
