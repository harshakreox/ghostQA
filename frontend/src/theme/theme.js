import { createTheme } from "@mui/material/styles";

// Enterprise-grade color palette
const theme = createTheme({
  palette: {
    mode: "light",
    primary: {
      main: "#1976d2", // Professional blue
      light: "#42a5f5",
      dark: "#1565c0",
      contrastText: "#fff",
    },
    secondary: {
      main: "#9c27b0", // Purple accent
      light: "#ba68c8",
      dark: "#7b1fa2",
      contrastText: "#fff",
    },
    success: {
      main: "#2e7d32",
      light: "#4caf50",
      dark: "#1b5e20",
    },
    error: {
      main: "#d32f2f",
      light: "#ef5350",
      dark: "#c62828",
    },
    warning: {
      main: "#ed6c02",
      light: "#ff9800",
      dark: "#e65100",
    },
    info: {
      main: "#0288d1",
      light: "#03a9f4",
      dark: "#01579b",
    },
    background: {
      default: "#f5f5f5",
      paper: "#ffffff",
    },
    text: {
      primary: "#212121",
      secondary: "#757575",
    },
  },
  typography: {
    fontFamily: [
      "-apple-system",
      "BlinkMacSystemFont",
      '"Segoe UI"',
      "Roboto",
      '"Helvetica Neue"',
      "Arial",
      "sans-serif",
    ].join(","),
    h1: {
      fontSize: "2.5rem",
      fontWeight: 600,
      lineHeight: 1.2,
    },
    h2: {
      fontSize: "2rem",
      fontWeight: 600,
      lineHeight: 1.3,
    },
    h3: {
      fontSize: "1.75rem",
      fontWeight: 600,
      lineHeight: 1.4,
    },
    h4: {
      fontSize: "1.5rem",
      fontWeight: 600,
      lineHeight: 1.4,
    },
    h5: {
      fontSize: "1.25rem",
      fontWeight: 600,
      lineHeight: 1.5,
    },
    h6: {
      fontSize: "1rem",
      fontWeight: 600,
      lineHeight: 1.6,
    },
    button: {
      textTransform: "none",
      fontWeight: 600,
    },
  },
  shape: {
    borderRadius: 8,
  },
  shadows: [
    "none",
    "0px 2px 4px rgba(0,0,0,0.05)",
    "0px 4px 8px rgba(0,0,0,0.08)",
    "0px 6px 12px rgba(0,0,0,0.1)",
    "0px 8px 16px rgba(0,0,0,0.12)",
    "0px 10px 20px rgba(0,0,0,0.14)",
    "0px 12px 24px rgba(0,0,0,0.16)",
    "0px 14px 28px rgba(0,0,0,0.18)",
    "0px 16px 32px rgba(0,0,0,0.2)",
    "0px 18px 36px rgba(0,0,0,0.22)",
    "0px 20px 40px rgba(0,0,0,0.24)",
    "0px 22px 44px rgba(0,0,0,0.26)",
    "0px 24px 48px rgba(0,0,0,0.28)",
    "0px 26px 52px rgba(0,0,0,0.3)",
    "0px 28px 56px rgba(0,0,0,0.32)",
    "0px 30px 60px rgba(0,0,0,0.34)",
    "0px 32px 64px rgba(0,0,0,0.36)",
    "0px 34px 68px rgba(0,0,0,0.38)",
    "0px 36px 72px rgba(0,0,0,0.4)",
    "0px 38px 76px rgba(0,0,0,0.42)",
    "0px 40px 80px rgba(0,0,0,0.44)",
    "0px 42px 84px rgba(0,0,0,0.46)",
    "0px 44px 88px rgba(0,0,0,0.48)",
    "0px 46px 92px rgba(0,0,0,0.5)",
    "0px 48px 96px rgba(0,0,0,0.52)",
  ],
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          padding: "10px 24px",
          fontSize: "0.95rem",
          boxShadow: "none",
          "&:hover": {
            boxShadow: "0px 4px 8px rgba(0,0,0,0.12)",
          },
        },
        contained: {
          boxShadow: "0px 2px 4px rgba(0,0,0,0.1)",
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          boxShadow: "0px 4px 12px rgba(0,0,0,0.08)",
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: 12,
        },
        elevation1: {
          boxShadow: "0px 2px 8px rgba(0,0,0,0.06)",
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          boxShadow: "0px 2px 8px rgba(0,0,0,0.08)",
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        head: {
          fontWeight: 600,
          backgroundColor: "#fafafa",
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 6,
          fontWeight: 500,
        },
      },
    },
  },
});

export default theme;
