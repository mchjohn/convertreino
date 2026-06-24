export const colors = {
  primary: "#FC4C02",
  secondary: "#0A0908",
  tertiary: "#F2F4F3",
  onPrimary: "#FFFFFF",
  inputBackground: "#FFFFFF",
  error: "#B91C1C",
  errorSurface: "#FEF2F2",
  errorBorder: "#FECACA",
  muted: "#6B7280",
  border: "#E5E7EB",
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
} as const;

export const radius = {
  button: 8,
  input: 8,
  bubble: 16,
  chatUserBubble: 24,
  chatAssistantBubble: 18,
  chatInput: 28,
} as const;

export const chatColors = {
  background: "#000000",
  surface: "#1C1C1E",
  border: "#333333",
  text: "#FFFFFF",
  placeholder: "#8E8E93",
  errorSurface: "#2C1515",
  errorBorder: "#7F1D1D",
  errorText: "#FCA5A5",
} as const;

export const typography = {
  display: { fontSize: 32, fontWeight: "700" as const, color: colors.secondary },
  title: { fontSize: 20, fontWeight: "600" as const, color: colors.secondary },
  body: { fontSize: 16, fontWeight: "400" as const, color: colors.muted },
  bodyStrong: { fontSize: 16, fontWeight: "400" as const, color: colors.secondary },
  label: { fontSize: 16, fontWeight: "600" as const, color: colors.onPrimary },
  caption: { fontSize: 14, fontWeight: "400" as const, color: colors.muted },
  captionError: { fontSize: 14, fontWeight: "400" as const, color: colors.error },
} as const;

export const touchTarget = {
  minHeight: 44,
  minWidth: 44,
} as const;
