import { useRef } from "react";
import { Box, Button, CircularProgress, InputAdornment, Stack, TextField } from "@mui/material";
import { useI18n } from "../i18n/LanguageContext";
import { terminalColors, fontSizes, toolbarButtonSx } from "../theme";

const SLASH_COMMANDS = [
  "/help",
  "/status",
  "/tree",
  "/export",
  "/eval:open",
  "/eval:axial",
  "/clear",
];

interface InputBarProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
  busy?: boolean;
  onInterrupt?: () => void;
}

export function InputBar({
  value,
  onChange,
  onSubmit,
  disabled,
  busy,
  onInterrupt,
}: InputBarProps) {
  const { t } = useI18n();
  const inputRef = useRef<HTMLInputElement>(null);
  const inputDisabled = disabled || busy;

  return (
    <Box
      sx={{
        borderTop: `1px solid ${terminalColors.border}`,
        bgcolor: terminalColors.panel,
        p: 1.5,
        opacity: busy ? 0.85 : 1,
        transition: "opacity 200ms ease",
      }}
    >
      <Stack direction="row" spacing={1} alignItems="flex-end">
        <TextField
          inputRef={inputRef}
          fullWidth
          multiline
          maxRows={6}
          size="small"
          value={value}
          disabled={inputDisabled}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey && !inputDisabled) {
              event.preventDefault();
              onSubmit();
            }
          }}
          placeholder={busy ? t("input.placeholderBusy") : t("input.placeholderIdle")}
          variant="standard"
          InputProps={{
            disableUnderline: true,
            startAdornment: (
              <InputAdornment position="start" disablePointerEvents>
                <Box
                  component="span"
                  sx={{
                    color: terminalColors.cyan,
                    fontWeight: 700,
                    userSelect: "none",
                  }}
                >
                  {">"}
                </Box>
              </InputAdornment>
            ),
            sx: {
              color: terminalColors.text,
              fontFamily: "inherit",
              fontSize: "inherit",
            },
          }}
        />
        {busy ? (
          <Button
            variant="outlined"
            size="small"
            onClick={onInterrupt}
            sx={{
              ...toolbarButtonSx,
              minWidth: 72,
              gap: 0.75,
              color: terminalColors.yellow,
              borderColor: "rgba(210, 153, 34, 0.55)",
              "&:hover": {
                borderColor: terminalColors.yellow,
                bgcolor: "rgba(210, 153, 34, 0.08)",
              },
            }}
          >
            <CircularProgress size={14} color="inherit" />
            {t("input.stop")}
          </Button>
        ) : (
          <Button
            variant="outlined"
            size="small"
            disabled={disabled}
            onClick={onSubmit}
            sx={{ ...toolbarButtonSx, minWidth: 64 }}
          >
            {t("input.send")}
          </Button>
        )}
      </Stack>
      <Stack
        direction="row"
        spacing={0.5}
        flexWrap="wrap"
        useFlexGap
        sx={{
          mt: 1,
          opacity: busy ? 0.5 : 1,
          transition: "opacity 200ms ease",
        }}
      >
        {SLASH_COMMANDS.map((cmd) => (
          <Button
            key={cmd}
            size="small"
            variant="text"
            disabled={inputDisabled}
            onClick={() => {
              onChange(cmd);
              inputRef.current?.focus();
            }}
            sx={{
              color: terminalColors.gray,
              minWidth: "auto",
              px: 0.75,
              fontSize: fontSizes.xs,
            }}
          >
            {cmd}
          </Button>
        ))}
      </Stack>
    </Box>
  );
}
