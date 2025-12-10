import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Button,
  Box,
  Typography,
} from '@mui/material';
import { Warning, Delete, Info } from '@mui/icons-material';

/**
 * ConfirmDialog - A reusable confirmation dialog component
 *
 * @param {boolean} open - Whether the dialog is open
 * @param {function} onClose - Callback when dialog is closed (cancelled)
 * @param {function} onConfirm - Callback when action is confirmed
 * @param {string} title - Dialog title
 * @param {string} message - Dialog message/description
 * @param {string} confirmLabel - Label for confirm button (default: 'Confirm')
 * @param {string} cancelLabel - Label for cancel button (default: 'Cancel')
 * @param {string} type - Type of dialog: 'delete', 'warning', 'info' (affects styling)
 * @param {boolean} loading - Whether the confirm action is loading
 */
export default function ConfirmDialog({
  open,
  onClose,
  onConfirm,
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  type = 'warning',
  loading = false,
}) {
  const typeConfig = {
    delete: {
      icon: <Delete sx={{ fontSize: 48 }} />,
      color: 'error',
      iconBg: 'error.light',
      iconColor: 'error.main',
    },
    warning: {
      icon: <Warning sx={{ fontSize: 48 }} />,
      color: 'warning',
      iconBg: 'warning.light',
      iconColor: 'warning.main',
    },
    info: {
      icon: <Info sx={{ fontSize: 48 }} />,
      color: 'primary',
      iconBg: 'primary.light',
      iconColor: 'primary.main',
    },
  };

  const config = typeConfig[type] || typeConfig.warning;

  return (
    <Dialog
      open={open}
      onClose={loading ? undefined : onClose}
      maxWidth="xs"
      fullWidth
      PaperProps={{
        sx: { borderRadius: 2 },
      }}
    >
      <DialogTitle sx={{ pb: 1 }}>
        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', pt: 2 }}>
          <Box
            sx={{
              width: 72,
              height: 72,
              borderRadius: '50%',
              bgcolor: config.iconBg,
              color: config.iconColor,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              mb: 2,
            }}
          >
            {config.icon}
          </Box>
          <Typography variant="h6" sx={{ fontWeight: 600, textAlign: 'center' }}>
            {title}
          </Typography>
        </Box>
      </DialogTitle>
      <DialogContent>
        <DialogContentText sx={{ textAlign: 'center' }}>{message}</DialogContentText>
      </DialogContent>
      <DialogActions sx={{ p: 3, pt: 1, justifyContent: 'center', gap: 2 }}>
        <Button onClick={onClose} disabled={loading} variant="outlined" sx={{ minWidth: 100 }}>
          {cancelLabel}
        </Button>
        <Button
          onClick={onConfirm}
          color={config.color}
          variant="contained"
          disabled={loading}
          sx={{ minWidth: 100 }}
        >
          {loading ? 'Processing...' : confirmLabel}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
