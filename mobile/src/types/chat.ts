export type ChatRole = "user" | "assistant";

export type ChatMessage = {
  role: ChatRole;
  content: string;
};

export type ChatResponse = {
  message: { role: "assistant"; content: string };
  tool_calls_made: string[];
};
