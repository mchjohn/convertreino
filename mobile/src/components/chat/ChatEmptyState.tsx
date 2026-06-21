import { StyleSheet, Text, View } from "react-native";

import { colors, spacing, typography } from "@/theme/tokens";

const DEFAULT_EXAMPLES = [
  "Qual foi minha corrida mais longa?",
  "Quanto corri esta semana?",
];

type ChatEmptyStateProps = {
  title?: string;
  examples?: string[];
};

export function ChatEmptyState({
  title = "Pergunte sobre seus treinos",
  examples = DEFAULT_EXAMPLES,
}: ChatEmptyStateProps) {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>{title}</Text>
      <Text style={styles.hint}>Experimente:</Text>
      {examples.map((example) => (
        <Text key={example} style={styles.example}>
          • {example}
        </Text>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: spacing.lg,
  },
  title: {
    ...typography.title,
    textAlign: "center",
  },
  hint: {
    ...typography.caption,
    marginTop: spacing.md,
    textAlign: "center",
  },
  example: {
    ...typography.body,
    textAlign: "center",
    marginTop: spacing.xs,
  },
});
