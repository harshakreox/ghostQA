/**
 * Register Page - handles both invite-based and direct registration
 */
import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams, Link as RouterLink } from 'react-router-dom';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Alert,
  CircularProgress,
  Divider,
  Chip,
} from '@mui/material';
import {
  PersonAdd,
  Business,
  CheckCircle,
  Error as ErrorIcon,
} from '@mui/icons-material';
import axios from 'axios';

export default function Register() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const inviteToken = searchParams.get('invite');

  // Form state
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  // Invite state
  const [inviteValid, setInviteValid] = useState(null);
  const [inviteInfo, setInviteInfo] = useState(null);
  const [validatingInvite, setValidatingInvite] = useState(false);

  // Submission state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  // Validate invite token on mount
  useEffect(() => {
    if (inviteToken) {
      validateInvite();
    }
  }, [inviteToken]);

  const validateInvite = async () => {
    try {
      setValidatingInvite(true);
      setError(null);
      const response = await axios.get(`/api/organizations/invites/validate/${inviteToken}`);
      setInviteInfo(response.data);
      setInviteValid(response.data.valid);

      // Pre-fill email if invite is for specific email
      if (response.data.email_required) {
        setEmail(response.data.email_required);
      }
    } catch (err) {
      console.error('Failed to validate invite:', err);
      setInviteValid(false);
      setError('Failed to validate invite link');
    } finally {
      setValidatingInvite(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    // Validate form
    if (!username || !email || !password) {
      setError('Please fill in all required fields');
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (password.length < 6) {
      setError('Password must be at least 6 characters');
      return;
    }

    try {
      setLoading(true);

      if (inviteToken && inviteValid) {
        // Register with invite
        await axios.post('/api/auth/register-with-invite', {
          token: inviteToken,
          username,
          email,
          password,
        });
      } else {
        // Regular registration (if allowed)
        await axios.post('/api/auth/register', {
          username,
          email,
          password,
        });
      }

      setSuccess(true);

      // Redirect to login after 2 seconds
      setTimeout(() => {
        navigate('/login', {
          state: { message: 'Registration successful! Please log in.' }
        });
      }, 2000);
    } catch (err) {
      console.error('Registration failed:', err);
      setError(err.response?.data?.detail || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  // Show loading while validating invite
  if (inviteToken && validatingInvite) {
    return (
      <Box
        sx={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        }}
      >
        <Paper sx={{ p: 4, textAlign: 'center', borderRadius: 2 }}>
          <CircularProgress sx={{ mb: 2 }} />
          <Typography>Validating invite link...</Typography>
        </Paper>
      </Box>
    );
  }

  // Show error if invite is invalid
  if (inviteToken && inviteValid === false) {
    return (
      <Box
        sx={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        }}
      >
        <Paper sx={{ p: 4, maxWidth: 400, textAlign: 'center', borderRadius: 2 }}>
          <ErrorIcon sx={{ fontSize: 64, color: 'error.main', mb: 2 }} />
          <Typography variant="h5" sx={{ fontWeight: 600, mb: 2 }}>
            Invalid Invite Link
          </Typography>
          <Typography color="text.secondary" sx={{ mb: 3 }}>
            {inviteInfo?.message || 'This invite link is invalid or has expired.'}
          </Typography>
          <Button
            variant="contained"
            component={RouterLink}
            to="/login"
          >
            Go to Login
          </Button>
        </Paper>
      </Box>
    );
  }

  // Show success message
  if (success) {
    return (
      <Box
        sx={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        }}
      >
        <Paper sx={{ p: 4, maxWidth: 400, textAlign: 'center', borderRadius: 2 }}>
          <CheckCircle sx={{ fontSize: 64, color: 'success.main', mb: 2 }} />
          <Typography variant="h5" sx={{ fontWeight: 600, mb: 2 }}>
            Registration Successful!
          </Typography>
          <Typography color="text.secondary">
            Redirecting to login...
          </Typography>
          <CircularProgress size={24} sx={{ mt: 2 }} />
        </Paper>
      </Box>
    );
  }

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        py: 4,
      }}
    >
      <Paper
        sx={{
          p: 4,
          width: '100%',
          maxWidth: 450,
          borderRadius: 2,
          mx: 2,
        }}
      >
        {/* Header */}
        <Box sx={{ textAlign: 'center', mb: 4 }}>
          <Box
            sx={{
              width: 64,
              height: 64,
              borderRadius: 3,
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              mx: 'auto',
              mb: 2,
            }}
          >
            <PersonAdd sx={{ fontSize: 32, color: 'white' }} />
          </Box>
          <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
            Create Account
          </Typography>

          {/* Show organization info if invite */}
          {inviteToken && inviteValid && inviteInfo && (
            <Box sx={{ mt: 2 }}>
              <Chip
                icon={<Business />}
                label={`Joining: ${inviteInfo.organization_name}`}
                color="primary"
                variant="outlined"
              />
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                You'll join as: <strong>{inviteInfo.org_role}</strong>
              </Typography>
            </Box>
          )}
        </Box>

        {/* Error Alert */}
        {error && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
        )}

        {/* Registration Form */}
        <form onSubmit={handleSubmit}>
          <TextField
            label="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            fullWidth
            required
            sx={{ mb: 2 }}
            autoFocus
          />
          <TextField
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            fullWidth
            required
            sx={{ mb: 2 }}
            disabled={inviteInfo?.email_required}
            helperText={inviteInfo?.email_required ? 'Email is set by invite' : ''}
          />
          <TextField
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            fullWidth
            required
            sx={{ mb: 2 }}
            helperText="At least 6 characters"
          />
          <TextField
            label="Confirm Password"
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            fullWidth
            required
            sx={{ mb: 3 }}
          />

          <Button
            type="submit"
            variant="contained"
            fullWidth
            size="large"
            disabled={loading}
            sx={{
              py: 1.5,
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            }}
          >
            {loading ? <CircularProgress size={24} color="inherit" /> : 'Create Account'}
          </Button>
        </form>

        <Divider sx={{ my: 3 }} />

        <Typography variant="body2" color="text.secondary" textAlign="center">
          Already have an account?{' '}
          <Button
            component={RouterLink}
            to="/login"
            size="small"
            sx={{ textTransform: 'none' }}
          >
            Sign in
          </Button>
        </Typography>
      </Paper>
    </Box>
  );
}
