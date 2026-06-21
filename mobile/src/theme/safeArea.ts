import { spacing } from "./tokens";

export function screenSafePadding(insets: { top: number; bottom: number }) {
  return {
    paddingTop: insets.top + spacing.md,
    paddingBottom: insets.bottom + spacing.md,
  };
}
