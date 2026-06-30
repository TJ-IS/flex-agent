import { Typography } from "@mui/material";
import { terminalColors } from "../theme";

const FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏";

interface StreamingLineProps {
  text: string;
  activityMode: string;
  activityLabels: Record<string, string>;
  frameIndex: number;
}

export function StreamingLine({
  text,
  activityMode,
  activityLabels,
  frameIndex,
}: StreamingLineProps) {
  if (text) {
    return (
      <Typography
        sx={{
          color: terminalColors.text,
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
          mb: 0.5,
        }}
      >
        {text}
      </Typography>
    );
  }

  const label = activityLabels[activityMode] ?? activityLabels.thinking ?? "running";
  const frame = FRAMES[frameIndex % FRAMES.length];

  return (
    <Typography
      sx={{
        color: terminalColors.gray,
        mb: 0.5,
      }}
    >
      {`${frame} ${label}...`}
    </Typography>
  );
}
