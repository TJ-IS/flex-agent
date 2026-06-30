import { Box, Typography } from "@mui/material";
import { terminalColors } from "../theme";
import type { TodoItem } from "../types";

const ICONS: Record<TodoItem["status"], string> = {
  pending: "○",
  in_progress: "●",
  completed: "✓",
};

const COLORS: Record<TodoItem["status"], string> = {
  pending: terminalColors.gray,
  in_progress: terminalColors.yellow,
  completed: terminalColors.green,
};

interface TodosProps {
  title: string;
  items: TodoItem[];
}

export function Todos({ title, items }: TodosProps) {
  if (!items.length) return null;

  return (
    <Box sx={{ my: 1 }}>
      <Typography
        sx={{
          color: terminalColors.magenta,
          fontWeight: 700,
          mb: 0.5,
        }}
      >
        {title}
      </Typography>
      {items.map((item, index) => (
        <Typography
          key={`${item.content}-${index}`}
          sx={{
            color: COLORS[item.status],
            pl: 1,
            whiteSpace: "pre-wrap",
          }}
        >
          {`  ${ICONS[item.status]} ${item.content}`}
        </Typography>
      ))}
    </Box>
  );
}
