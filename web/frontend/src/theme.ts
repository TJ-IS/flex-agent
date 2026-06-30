import { createTheme } from "@mui/material/styles";

export const terminalColors = {
  bg: "#0d1117",
  text: "#c9d1d9",
  cyan: "#39c5cf",
  green: "#3fb950",
  yellow: "#d29922",
  red: "#f85149",
  gray: "#8b949e",
  magenta: "#bc8cff",
  border: "#21262d",
  panel: "#161b22",
};

export const monoFont =
  '"JetBrains Mono", "Fira Code", "SF Mono", Menlo, Monaco, Consolas, monospace';

export const theme = createTheme({
  palette: {
    mode: "dark",
    primary: { main: terminalColors.cyan },
    secondary: { main: terminalColors.magenta },
    background: {
      default: terminalColors.bg,
      paper: terminalColors.panel,
    },
    text: {
      primary: terminalColors.text,
      secondary: terminalColors.gray,
    },
    error: { main: terminalColors.red },
    warning: { main: terminalColors.yellow },
    success: { main: terminalColors.green },
  },
  typography: {
    fontFamily: monoFont,
    fontSize: 13,
  },
  shape: { borderRadius: 4 },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          backgroundColor: terminalColors.bg,
          margin: 0,
        },
        "#root": {
          minHeight: "100vh",
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: "none",
          fontFamily: monoFont,
          fontSize: "0.75rem",
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          fontFamily: monoFont,
        },
      },
    },
  },
});
