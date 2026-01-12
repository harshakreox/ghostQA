import { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Button,
  TextField,
  Switch,
  FormControlLabel,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Chip,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Avatar,
  Tooltip,
  Skeleton,
  CircularProgress,
} from '@mui/material';
import {
  Lock,
  Add,
  Edit,
  Delete,
  AdminPanelSettings,
  PersonOutline,
  Refresh,
} from '@mui/icons-material';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';

// Helper to get auth headers
const getAuthHeaders = () => {
  const token = localStorage.getItem('auth_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
};

export default function Settings() {
  const { user, isAdmin } = useAuth();

  // User management state
  const [users, setUsers] = useState([]);
  const [loadingUsers, setLoadingUsers] = useState(true);

  // Dialog states
  const [userDialog, setUserDialog] = useState({ open: false, user: null });
  const [deleteDialog, setDeleteDialog] = useState({ open: false, user: null });
  const [resetDialog, setResetDialog] = useState({ open: false, user: null });
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  // Form data for add/edit user
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    role: 'user',
  });

  // Determine if we are editing
  const isEditing = userDialog.open && userDialog.user !== null;

  useEffect(() => {
    if (isAdmin) {
      loadUsers();
    }
  }, [isAdmin]);

  // Populate form when editing a user
  useEffect(() => {
    if (userDialog.open && userDialog.user) {
      setFormData({
        username: userDialog.user.username || '',
        email: userDialog.user.email || '',
        password: '',
        role: userDialog.user.role || 'user',
      });
    } else if (userDialog.open) {
      setFormData({ username: '', email: '', password: '', role: 'user' });
    }
  }, [userDialog.open, userDialog.user]);

  const loadUsers = async () => {
    try {
      setLoadingUsers(true);
      const response = await axios.get('/api/auth/users', { headers: getAuthHeaders() });
      setUsers(response.data || []);
    } catch (error) {
      console.error('Failed to load users:', error);
    } finally {
      setLoadingUsers(false);
    }
  };

  const handleSaveUser = async () => {
    try {
      setActionLoading(true);
      setError(null);

      if (isEditing) {
        // Update existing user
        const updateData = {
          email: formData.email,
          role: formData.role,
        };
        await axios.put(`/api/auth/users/${userDialog.user.id}`, updateData, { headers: getAuthHeaders() });
        setSuccess('User updated successfully');
      } else {
        // Create new user
        await axios.post('/api/auth/users', formData, { headers: getAuthHeaders() });
        setSuccess('User created successfully');
      }

      setUserDialog({ open: false, user: null });
      setFormData({ username: '', email: '', password: '', role: 'user' });
      loadUsers();
    } catch (error) {
      console.error('Failed to save user:', error);
      setError(error.response?.data?.detail || 'Failed to save user');
    } finally {
      setActionLoading(false);
    }
  };

  const handleDeleteUser = async () => {
    if (!deleteDialog.user) return;
    try {
      setActionLoading(true);
      setError(null);
      await axios.delete(`/api/auth/users/${deleteDialog.user.id}`, { headers: getAuthHeaders() });
      setDeleteDialog({ open: false, user: null });
      setSuccess('User deleted successfully');
      loadUsers();
    } catch (error) {
      console.error('Failed to delete user:', error);
      setError(error.response?.data?.detail || 'Failed to delete user');
    } finally {
      setActionLoading(false);
    }
  };
  const handleResetPassword = async () => {
    if (!resetDialog.user) return;
    try {
      setActionLoading(true);
      setError(null);
      const response = await axios.post(`/api/auth/users/${resetDialog.user.id}/reset-password`, {}, { headers: getAuthHeaders() });
      setResetDialog({ open: false, user: null });
      setSuccess(`Password reset! Temporary password: ${response.data.temporary_password}`);
    } catch (error) {
      console.error("Failed to reset password:", error);
      setError(error.response?.data?.detail || "Failed to reset password");
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <Box>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
          Settings
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Manage users and system configuration
        </Typography>
      </Box>

      {/* Alerts */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      {success && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      )}


      {/* User Management Section */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h6" sx={{ fontWeight: 600 }}>
          User Management
        </Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Tooltip title="Refresh">
            <IconButton onClick={() => { loadUsers() }}>
              <Refresh />
            </IconButton>
          </Tooltip>
          {isAdmin && (
            <Button
              variant="contained"
              startIcon={<Add />}
              onClick={() => setUserDialog({ open: true, user: null })}
              sx={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}
            >
              Add User
            </Button>
          )}
        </Box>
      </Box>

          <Paper sx={{ borderRadius: 2 }}>
            {loadingUsers ? (
              <Box sx={{ p: 2 }}>
                {[1, 2, 3].map(i => (
                  <Skeleton key={i} variant="rectangular" height={72} sx={{ mb: 1, borderRadius: 1 }} />
                ))}
              </Box>
            ) : users.length === 0 ? (
              <Alert severity="info" sx={{ m: 2 }}>
                No users found.
              </Alert>
            ) : (
              <List>
                {users.map((u, idx) => (
                  <Box key={u.id}>
                    {idx > 0 && <Divider />}
                    <ListItem sx={{ py: 2 }}>
                      <Avatar
                        sx={{
                          mr: 2,
                          background: u.role === 'admin'
                            ? 'linear-gradient(135deg, #f44336 0%, #e91e63 100%)'
                            : u.role === 'admin'
                              ? 'linear-gradient(135deg, #f57c00 0%, #ff9800 100%)'
                              : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                        }}
                      >
                        {u.username?.charAt(0).toUpperCase()}
                      </Avatar>
                      <ListItemText
                        primary={
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                            <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                              {u.username}
                            </Typography>
                            <Chip
                              size="small"
                              icon={
                                u.role === 'admin' ? <AdminPanelSettings sx={{ fontSize: 14 }} /> :
                                u.role === 'admin' ? <SupervisorAccount sx={{ fontSize: 14 }} /> :
                                <PersonOutline sx={{ fontSize: 14 }} />
                              }
                              label={u.role === 'admin' ? 'Admin' : 'User'}
                              color={u.role === 'admin' ? 'warning' : 'primary'}
                              sx={{ height: 24, fontSize: '0.75rem' }}
                            />
                            {u.id === user?.id && (
                              <Chip size="small" label="You" variant="outlined" sx={{ height: 20, fontSize: '0.7rem' }} />
                            )}
                          </Box>
                        }
                        secondary={<Typography variant="body2" color="text.secondary">{u.email}</Typography>}
                      />
                      {isAdmin && u.id !== user?.id && (
                        <ListItemSecondaryAction>
                          <Tooltip title="Edit User">
                            <IconButton onClick={() => setUserDialog({ open: true, user: { ...u } })}>
                              <Edit />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Reset Password">
                            <IconButton onClick={() => setResetDialog({ open: true, user: u })}>
                              <Lock />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Delete User">
                            <IconButton color="error" onClick={() => setDeleteDialog({ open: true, user: u })}>
                              <Delete />
                            </IconButton>
                          </Tooltip>
                        </ListItemSecondaryAction>
                      )}
                    </ListItem>
                  </Box>
                ))}
              </List>
            )}
      </Paper>

      {/* Add/Edit User Dialog */}
      <Dialog open={userDialog.open} onClose={() => setUserDialog({ open: false, user: null })} maxWidth="sm" fullWidth>
        <DialogTitle>{isEditing ? 'Edit User' : 'Add New User'}</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              label="Username"
              value={formData.username}
              onChange={(e) => setFormData({ ...formData, username: e.target.value })}
              fullWidth
              disabled={isEditing}
              helperText={isEditing ? "Username cannot be changed" : ""}
            />
            <TextField
              label="Email"
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              fullWidth
            />
            {!isEditing && (
              <TextField
                label="Password"
                type="password"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                fullWidth
                helperText="User will be required to change password on first login"
              />
            )}
            <FormControlLabel
              control={
                <Switch
                  checked={formData.role === 'admin'}
                  onChange={(e) => setFormData({ ...formData, role: e.target.checked ? 'admin' : 'user' })}
                />
              }
              label="System Administrator (has access to all system features)"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setUserDialog({ open: false, user: null })}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleSaveUser}
            disabled={actionLoading || !formData.username || !formData.email || (!isEditing && !formData.password)}
          >
            {actionLoading ? <CircularProgress size={20} /> : (isEditing ? 'Save Changes' : 'Create User')}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialog.open} onClose={() => setDeleteDialog({ open: false, user: null })}>
        <DialogTitle>Delete User</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete user <strong>{deleteDialog.user?.username}</strong>?
            This action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialog({ open: false, user: null })}>Cancel</Button>
          <Button variant="contained" color="error" onClick={handleDeleteUser} disabled={actionLoading}>
            {actionLoading ? <CircularProgress size={20} /> : 'Delete'}
          </Button>
        </DialogActions>
      </Dialog>
      {/* Reset Password Dialog */}
      <Dialog open={resetDialog.open} onClose={() => setResetDialog({ open: false, user: null })}>
        <DialogTitle>Reset Password</DialogTitle>
        <DialogContent>
          <Typography>
            Reset password for user <strong>{resetDialog.user?.username}</strong>?
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            A temporary password will be generated. The user will be required to change it on next login.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setResetDialog({ open: false, user: null })}>Cancel</Button>
          <Button variant="contained" onClick={handleResetPassword} disabled={actionLoading}>
            {actionLoading ? <CircularProgress size={20} /> : 'Reset Password'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
