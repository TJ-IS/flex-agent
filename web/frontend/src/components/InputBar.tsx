import { useRef } from "react";
import { Box, Button, Stack, TextField } from "@mui/material";
import { terminalColors } from "../theme";

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
}

export function InputBar({ value, onChange, onSubmit, disabled }: InputBarProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  return (
    <Box
      sx={{
        borderTop: `1px solid ${terminalColors.border}`,
        bgcolor: terminalColors.panel,
        p: 1.5,
      }}
    >
      <Stack direction="row" spacing={1} alignItems="flex-start">
        <TypographyPrompt />
        <TextField
          inputRef={inputRef}
          fullWidth
          multiline
          maxRows={6}
          size="small"
          value={value}
          disabled={disabled}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              onSubmit();
            }
          }}
          placeholder="输入 open coding 任务或 slash 命令…"
          variant="standard"
          InputProps={{
            disableUnderline: true,
            sx: {
              color: terminalColors.text,
              fontFamily: "inherit",
              fontSize: "inherit",
            },
          }}
        />
        <Button
          variant="outlined"
          size="small"
          disabled={disabled}
          onClick={onSubmit}
          sx={{ minWidth: 64, borderColor: terminalColors.border }}
        >
          发送
        </Button>
      </Stack>
      <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap sx={{ mt: 1 }}>
        {SLASH_COMMANDS.map((cmd) => (
          <Button
            key={cmd}
            size="small"
            variant="text"
            disabled={disabled}
            onClick={() => {
              onChange(cmd);
              inputRef.current?.focus();
            }}
            sx={{
              color: terminalColors.gray,
              minWidth: "auto",
              px: 0.75,
              fontSize: "0.7rem",
            }}
          >
            {cmd}
          </Button>
        ))}
      </Stack>
    </Box>
  );
}

function TypographyPrompt() {
  return (
    <Box
      component="span"
      sx={{
        color: terminalColors.cyan,
        fontWeight: 700,
        pt: 0.75,
        userSelect: "none",
      }}
    >
      {"> "}
    </Box>
  );
}
