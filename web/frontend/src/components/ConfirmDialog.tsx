import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
} from "@mui/material";
import { useI18n } from "../i18n/LanguageContext";

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  confirmColor?: "primary" | "error" | "warning";
  onConfirm: () => void;
  onClose: () => void;
}

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel,
  cancelLabel,
  confirmColor = "primary",
  onConfirm,
  onClose,
}: ConfirmDialogProps) {
  const { t } = useI18n();
  const resolvedConfirm = confirmLabel ?? t("confirm.confirm");
  const resolvedCancel = cancelLabel ?? t("confirm.cancel");
  return (
    <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
      <DialogTitle>{title}</DialogTitle>
      <DialogContent>
        <DialogContentText sx={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
          {message}
        </DialogContentText>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} color="inherit">
          {resolvedCancel}
        </Button>
        <Button
          onClick={() => {
            onConfirm();
            onClose();
          }}
          color={confirmColor}
          variant="contained"
        >
          {resolvedConfirm}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
