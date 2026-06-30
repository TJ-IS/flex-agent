import { Box, Typography } from "@mui/material";
import { terminalColors } from "../theme";
import type { TimelineEntry, StepRecord } from "../types";
import { StepLine } from "./StepLine";

interface TimelineProps {
  entry: TimelineEntry;
  step?: StepRecord;
}

export function Timeline({ entry, step }: TimelineProps) {
  if (entry.kind === "user") {
    return (
      <Typography
        sx={{
          color: terminalColors.cyan,
          fontWeight: 700,
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
          mb: 0.5,
        }}
      >
        {`> ${entry.text}`}
      </Typography>
    );
  }

  if (entry.kind === "assistant") {
    return (
      <Typography
        sx={{
          color: terminalColors.text,
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
          mb: 0.5,
        }}
      >
        {entry.text}
      </Typography>
    );
  }

  if (entry.kind === "system") {
    return (
      <Typography
        sx={{
          color: terminalColors.gray,
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
          mb: 0.5,
        }}
      >
        {entry.text}
      </Typography>
    );
  }

  if (entry.kind === "error") {
    return (
      <Typography
        sx={{
          color: terminalColors.yellow,
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
          mb: 0.5,
        }}
      >
        {`error: ${entry.text}`}
      </Typography>
    );
  }

  if (entry.kind === "step" && step) {
    return (
      <Box sx={{ mb: 0.5 }}>
        <StepLine step={step} />
      </Box>
    );
  }

  return (
    <Typography
      sx={{
        color: terminalColors.text,
        whiteSpace: "pre-wrap",
        mb: 0.5,
      }}
    >
      {entry.text}
    </Typography>
  );
}
