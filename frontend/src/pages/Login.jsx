/**
 * Login Page
 * Clean, modern login page with option to register
 */
import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Box,
  TextField,
  Button,
  Typography,
  Alert,
  CircularProgress,
  InputAdornment,
  IconButton,
  Paper,
  Link,
  Fade,
} from '@mui/material';
import {
  Person,
  Lock,
  Email,
  Visibility,
  VisibilityOff,
  BugReport,
  ArrowForward,
} from '@mui/icons-material';
import { useAuth } from '../context/AuthContext';

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, register } = useAuth();

  const [isLogin, setIsLogin] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  // Separate form fields for Login
  const [loginUsername, setLoginUsername] = useState('');
  const [loginPassword, setLoginPassword] = useState('');

  // Separate form fields for Register
  const [registerUsername, setRegisterUsername] = useState('');
  const [registerEmail, setRegisterEmail] = useState('');
  const [registerPassword, setRegisterPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  const from = location.state?.from?.pathname || '/';

  const toggleMode = () => {
    setIsLogin(!isLogin);
    setError('');
    setShowPassword(false);
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');

    if (!loginUsername || !loginPassword) {
      setError('Please enter username and password');
      return;
    }

    setLoading(true);

    const result = await login(loginUsername, loginPassword);

    if (result.success) {
      const destination = result.user?.role === 'user' ? '/projects' : (from === '/' ? '/' : from);
      navigate(destination, { replace: true, state: { welcomeUser: loginUsername } });
    } else {
      setError(result.error);
    }
    setLoading(false);
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setError('');

    if (!registerUsername || !registerEmail || !registerPassword) {
      setError('All fields are required');
      return;
    }
    if (registerPassword !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }
    if (registerPassword.length < 6) {
      setError('Password must be at least 6 characters');
      return;
    }

    setLoading(true);
    const result = await register(registerUsername, registerEmail, registerPassword);

    if (result.success) {
      navigate('/projects', { replace: true, state: { welcomeUser: registerUsername } });
    } else {
      setError(result.error);
    }
    setLoading(false);
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
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: '#f5f5f5',
        p: 2,
      }}
    >
      <Fade in timeout={500}>
        <Paper
          elevation={0}
          sx={{
            maxWidth: 420,
            width: '100%',
            borderRadius: 4,
            overflow: 'hidden',
            border: '1px solid',
            borderColor: 'divider',
          }}
        >
          {/* Header */}
          <Box sx={{ p: 4, pb: 3, textAlign: 'center' }}>
            <Box
              sx={{
                width: 56,
                height: 56,
                borderRadius: 3,
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                mx: 'auto',
                mb: 2,
                boxShadow: '0 4px 14px rgba(102, 126, 234, 0.4)',
              }}
            >
              <BugReport sx={{ fontSize: 28, color: 'white' }} />
            </Box>
            <Typography variant="h5" sx={{ fontWeight: 700, color: '#1a1a2e', mb: 0.5 }}>
              {isLogin ? 'Welcome back' : 'Create account'}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {isLogin ? 'Sign in to GhostQA' : 'Get started with GhostQA'}
            </Typography>
          </Box>

          {/* Form */}
          <Box sx={{ px: 4, pb: 4 }}>
            {error && (
              <Alert
                severity="error"
                sx={{
                  mb: 2.5,
                  borderRadius: 2,
                  '& .MuiAlert-icon': { alignItems: 'center' }
                }}
              >
                {error}
              </Alert>
            )}

            {isLogin ? (
              <form onSubmit={handleLogin}>
                <TextField
                  fullWidth
                  placeholder="Username"
                  value={loginUsername}
                  onChange={(e) => setLoginUsername(e.target.value)}
                  required
                  sx={{ mb: 2, ...inputStyles }}
                  autoComplete="username"
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <Person sx={{ color: 'text.disabled', fontSize: 20 }} />
                      </InputAdornment>
                    ),
                  }}
                />
                <TextField
                  fullWidth
                  placeholder="Password"
                  type={showPassword ? 'text' : 'password'}
                  value={loginPassword}
                  onChange={(e) => setLoginPassword(e.target.value)}
                  required
                  sx={{ mb: 3, ...inputStyles }}
                  autoComplete="current-password"
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
                <Button
                  type="submit"
                  fullWidth
                  variant="contained"
                  size="large"
                  disabled={loading}
                  endIcon={!loading && <ArrowForward />}
                  sx={{
                    py: 1.5,
                    borderRadius: 2,
                    textTransform: 'none',
                    fontSize: '1rem',
                    fontWeight: 600,
                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    boxShadow: '0 4px 14px rgba(102, 126, 234, 0.4)',
                    '&:hover': {
                      background: 'linear-gradient(135deg, #5a6fd6 0%, #6a4190 100%)',
                      boxShadow: '0 6px 20px rgba(102, 126, 234, 0.5)',
                    },
                  }}
                >
                  {loading ? <CircularProgress size={24} color="inherit" /> : 'Sign in'}
                </Button>
              </form>
            ) : (
              <form onSubmit={handleRegister}>
                <TextField
                  fullWidth
                  placeholder="Username"
                  value={registerUsername}
                  onChange={(e) => setRegisterUsername(e.target.value)}
                  required
                  sx={{ mb: 2, ...inputStyles }}
                  autoComplete="username"
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <Person sx={{ color: 'text.disabled', fontSize: 20 }} />
                      </InputAdornment>
                    ),
                  }}
                />
                <TextField
                  fullWidth
                  placeholder="Email"
                  type="email"
                  value={registerEmail}
                  onChange={(e) => setRegisterEmail(e.target.value)}
                  required
                  sx={{ mb: 2, ...inputStyles }}
                  autoComplete="email"
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <Email sx={{ color: 'text.disabled', fontSize: 20 }} />
                      </InputAdornment>
                    ),
                  }}
                />
                <TextField
                  fullWidth
                  placeholder="Password"
                  type={showPassword ? 'text' : 'password'}
                  value={registerPassword}
                  onChange={(e) => setRegisterPassword(e.target.value)}
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
                  placeholder="Confirm Password"
                  type={showPassword ? 'text' : 'password'}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  sx={{ mb: 3, ...inputStyles }}
                  autoComplete="new-password"
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <Lock sx={{ color: 'text.disabled', fontSize: 20 }} />
                      </InputAdornment>
                    ),
                  }}
                />
                <Button
                  type="submit"
                  fullWidth
                  variant="contained"
                  size="large"
                  disabled={loading}
                  endIcon={!loading && <ArrowForward />}
                  sx={{
                    py: 1.5,
                    borderRadius: 2,
                    textTransform: 'none',
                    fontSize: '1rem',
                    fontWeight: 600,
                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    boxShadow: '0 4px 14px rgba(102, 126, 234, 0.4)',
                    '&:hover': {
                      background: 'linear-gradient(135deg, #5a6fd6 0%, #6a4190 100%)',
                      boxShadow: '0 6px 20px rgba(102, 126, 234, 0.5)',
                    },
                  }}
                >
                  {loading ? <CircularProgress size={24} color="inherit" /> : 'Create account'}
                </Button>
              </form>
            )}

            {/* Toggle */}
            <Box sx={{ mt: 3, textAlign: 'center' }}>
              <Typography variant="body2" color="text.secondary">
                {isLogin ? "Don't have an account? " : 'Already have an account? '}
                <Link
                  component="button"
                  type="button"
                  variant="body2"
                  onClick={toggleMode}
                  sx={{
                    fontWeight: 600,
                    color: '#667eea',
                    textDecoration: 'none',
                    '&:hover': {
                      textDecoration: 'underline',
                    },
                  }}
                >
                  {isLogin ? 'Sign up' : 'Sign in'}
                </Link>
              </Typography>
            </Box>

            {/* Demo credentials hint */}
            {/* {isLogin && (
              <Box
                sx={{
                  mt: 3,
                  p: 2,
                  borderRadius: 2,
                  backgroundColor: '#f8f9fa',
                  textAlign: 'center',
                }}
              >
                <Typography variant="caption" color="text.secondary">
                  Demo: <strong>admin</strong> / <strong>admin123</strong>
                </Typography>
              </Box>
            )} */}
          </Box>
        </Paper>
      </Fade>
    </Box>
  );
}
