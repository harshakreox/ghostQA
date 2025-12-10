/**
 * Force Change Password Dialog
 * Shown when a user's password was reset by admin and they must change it
 */
import { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Alert,
  Box,
  Typography,
  InputAdornment,
  IconButton,
  CircularProgress,
} from '@mui/material';
import { Lock, Visibility, VisibilityOff, Warning } from '@mui/icons-material';
import { useAuth } from '../context/AuthContext';

export default function ForceChangePasswordDialog() {
  const { mustChangePassword, forceChangePassword, logout } = useAuth();
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  console.log('[ForceChangePasswordDialog] mustChangePassword:', mustChangePassword);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!newPassword || !confirmPassword) {
      setError('Please fill in all fields');
      return;
    }

    if (newPassword.length < 6) {
      setError('Password must be at least 6 characters');
      return;
    }

    if (newPassword !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    setLoading(true);
    const result = await forceChangePassword(newPassword);

    if (!result.success) {
      setError(result.error);
    }
    setLoading(false);
  };

  const handleLogout = () => {
    logout();
  };

  const inputStyles = {
    '& .MuiOutlinedInput-root': {
      borderRadius: 2,
      backgroundColor: '#f8f9fa',
      '&:hover': {
        backgroundColor: '#f1f3f4',
      },
      '&.Mui-focused': {
        backgroundColor: '#fff',
      },
    },
  };

  return (
    <Dialog
      open={mustChangePassword}
      maxWidth="sm"
      fullWidth
      disableEscapeKeyDown
      PaperProps={{
        sx: { borderRadius: 3 }
      }}
    >
      <DialogTitle sx={{ pb: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <Box
            sx={{
              width: 40,
              height: 40,
              borderRadius: 2,
              background: 'linear-gradient(135deg, #ff9800 0%, #f57c00 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Warning sx={{ color: 'white', fontSize: 22 }} />
          </Box>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            Password Change Required
          </Typography>
        </Box>
      </DialogTitle>

      <form onSubmit={handleSubmit}>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Your password has been reset by an administrator. Please create a new password to continue.
          </Typography>

          {error && (
            <Alert severity="error" sx={{ mb: 2, borderRadius: 2 }}>
              {error}
            </Alert>
          )}

          <TextField
            fullWidth
            placeholder="New Password"
            type={showPassword ? 'text' : 'password'}
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            required
            sx={{ mb: 2, ...inputStyles }}
            autoComplete="new-password"
            helperText="At least 6 characters"
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Lock sx={{ color: 'text.disabled', fontSize: 20 }} />
                </InputAdornment>
              ),
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton
                    onClick={() => setShowPassword(!showPassword)}
                    edge="end"
                    size="small"
                  >
                    {showPassword ? (
                      <VisibilityOff sx={{ fontSize: 20 }} />
                    ) : (
                      <Visibility sx={{ fontSize: 20 }} />
                    )}
                  </IconButton>
                </InputAdornment>
              ),
            }}
          />

          <TextField
            fullWidth
            placeholder="Confirm New Password"
            type={showPassword ? 'text' : 'password'}
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
            sx={{ ...inputStyles }}
            autoComplete="new-password"
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Lock sx={{ color: 'text.disabled', fontSize: 20 }} />
                </InputAdornment>
              ),
            }}
          />
        </DialogContent>

        <DialogActions sx={{ px: 3, pb: 3, pt: 1 }}>
          <Button
            onClick={handleLogout}
            color="inherit"
            disabled={loading}
          >
            Logout
          </Button>
          <Button
            type="submit"
            variant="contained"
            disabled={loading}
            sx={{
              px: 3,
              borderRadius: 2,
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              '&:hover': {
                background: 'linear-gradient(135deg, #5a6fd6 0%, #6a4190 100%)',
              },
            }}
          >
            {loading ? <CircularProgress size={24} color="inherit" /> : 'Change Password'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}
