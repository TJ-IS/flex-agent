import { Box, Typography } from "@mui/material";
import { useI18n } from "../i18n/LanguageContext";
import { fontSizes, terminalColors } from "../theme";

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
  const { t } = useI18n();
  const label = activityLabels[activityMode] ?? activityLabels.thinking ?? t("stream.running");
  const frame = FRAMES[frameIndex % FRAMES.length];

  return (
    <Box sx={{ mb: 1 }}>
      <Typography
        sx={{
          color: terminalColors.gray,
          fontSize: fontSizes.sm,
          mb: 0.5,
          display: "flex",
          alignItems: "center",
          gap: 0.75,
        }}
      >
        <Box component="span" sx={{ color: terminalColors.cyan }}>
          {frame}
        </Box>
        {label}
      </Typography>
      {text ? (
        <Typography
          component="div"
          sx={{
            color: terminalColors.text,
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
            pl: 1,
            borderLeft: `2px solid ${terminalColors.cyan}`,
            fontSize: fontSizes.md,
          }}
        >
          {text}
          <Box
            component="span"
            sx={{
              color: terminalColors.cyan,
              animation: "blink 1s step-end infinite",
              ml: 0.25,
            }}
          >
            ▍
          </Box>
        </Typography>
      ) : null}
    </Box>
  );
}
