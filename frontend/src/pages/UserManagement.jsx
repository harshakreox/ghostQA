/**
 * User Management Page
 * Admin-only page for managing users
 */
import { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Switch,
  FormControlLabel,
  Alert,
  Snackbar,
  Avatar,
  Tooltip,
  CircularProgress,
  InputAdornment,
} from '@mui/material';
import {
  Add,
  Edit,
  Delete,
  Person,
  AdminPanelSettings,
  Lock,
  Email,
  Visibility,
  VisibilityOff,
  Refresh,
  Search,
  Clear,
} from '@mui/icons-material';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';

export default function UserManagement() {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  // Dialog states
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [resetPasswordDialogOpen, setResetPasswordDialogOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);

  // Form states
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    role: 'user',
    is_active: true,
  });
  const [showPassword, setShowPassword] = useState(false);
  const [formError, setFormError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // Snackbar
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    setLoading(true);
    try {
      const response = await axios.get('/api/auth/users');
      setUsers(response.data);
    } catch (error) {
      console.error('Error loading users:', error);
      showNotification('Failed to load users', 'error');
    } finally {
      setLoading(false);
    }
  };

  const showNotification = (message, severity = 'success') => {
    setSnackbar({ open: true, message, severity });
  };

  const handleCloseSnackbar = () => {
    setSnackbar({ ...snackbar, open: false });
  };

  // Create User
  const handleOpenCreateDialog = () => {
    setFormData({
      username: '',
      email: '',
      password: '',
      role: 'user',
      is_active: true,
    });
    setFormError('');
    setCreateDialogOpen(true);
  };

  const handleCreateUser = async () => {
    setFormError('');
    if (!formData.username || !formData.email || !formData.password) {
      setFormError('All fields are required');
      return;
    }
    if (formData.password.length < 6) {
      setFormError('Password must be at least 6 characters');
      return;
    }

    setSubmitting(true);
    try {
      await axios.post('/api/auth/users', {
        username: formData.username,
        email: formData.email,
        password: formData.password,
        role: formData.role,
      });
      showNotification('User created successfully');
      setCreateDialogOpen(false);
      loadUsers();
    } catch (error) {
      setFormError(error.response?.data?.detail || 'Failed to create user');
    } finally {
      setSubmitting(false);
    }
  };

  // Edit User
  const handleOpenEditDialog = (user) => {
    setSelectedUser(user);
    setFormData({
      username: user.username,
      email: user.email,
      password: '',
      role: user.role,
      is_active: user.is_active,
    });
    setFormError('');
    setEditDialogOpen(true);
  };

  const handleUpdateUser = async () => {
    setFormError('');
    setSubmitting(true);
    try {
      await axios.put(`/api/auth/users/${selectedUser.id}`, {
        email: formData.email,
        role: formData.role,
        is_active: formData.is_active,
      });
      showNotification('User updated successfully');
      setEditDialogOpen(false);
      loadUsers();
    } catch (error) {
      setFormError(error.response?.data?.detail || 'Failed to update user');
    } finally {
      setSubmitting(false);
    }
  };

  // Delete User
  const handleOpenDeleteDialog = (user) => {
    setSelectedUser(user);
    setDeleteDialogOpen(true);
  };

  const handleDeleteUser = async () => {
    setSubmitting(true);
    try {
      await axios.delete(`/api/auth/users/${selectedUser.id}`);
      showNotification('User deleted successfully');
      setDeleteDialogOpen(false);
      loadUsers();
    } catch (error) {
      showNotification(error.response?.data?.detail || 'Failed to delete user', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  // Reset Password
  const handleOpenResetPasswordDialog = (user) => {
    setSelectedUser(user);
    setResetPasswordDialogOpen(true);
  };

  const handleResetPassword = async () => {
    setSubmitting(true);
    try {
      const response = await axios.post(`/api/auth/users/${selectedUser.id}/reset-password`);
      showNotification(`Password reset to: ${response.data.temporary_password}`, 'info');
      setResetPasswordDialogOpen(false);
    } catch (error) {
      showNotification(error.response?.data?.detail || 'Failed to reset password', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  // Filter users by search
  const filteredUsers = users.filter(user =>
    user.username.toLowerCase().includes(searchQuery.toLowerCase()) ||
    user.email.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 700, mb: 0.5 }}>
            User Management
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Manage users and their roles
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant="outlined"
            startIcon={<Refresh />}
            onClick={loadUsers}
            disabled={loading}
          >
            Refresh
          </Button>
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={handleOpenCreateDialog}
            sx={{
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            }}
          >
            Add User
          </Button>
        </Box>
      </Box>

      {/* Search */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <TextField
          fullWidth
          size="small"
          placeholder="Search users..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <Search color="action" />
              </InputAdornment>
            ),
            endAdornment: searchQuery && (
              <InputAdornment position="end">
                <IconButton size="small" onClick={() => setSearchQuery('')}>
                  <Clear fontSize="small" />
                </IconButton>
              </InputAdornment>
            ),
          }}
        />
      </Paper>

      {/* Users Table */}
      <TableContainer component={Paper}>
        {loading && <CircularProgress sx={{ m: 2 }} />}
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>User</TableCell>
              <TableCell>Email</TableCell>
              <TableCell>Role</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Created</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredUsers.map((user) => (
              <TableRow key={user.id} hover>
                <TableCell>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                    <Avatar
                      sx={{
                        width: 36,
                        height: 36,
                        background: user.role === 'admin'
                          ? 'linear-gradient(135deg, #f57c00 0%, #ff9800 100%)'
                          : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                      }}
                    >
                      {user.username.charAt(0).toUpperCase()}
                    </Avatar>
                    <Box>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        {user.username}
                      </Typography>
                      {user.id === currentUser?.id && (
                        <Typography variant="caption" color="text.secondary">
                          (You)
                        </Typography>
                      )}
                    </Box>
                  </Box>
                </TableCell>
                <TableCell>{user.email}</TableCell>
                <TableCell>
                  <Chip
                    icon={user.role === 'admin' ? <AdminPanelSettings /> : <Person />}
                    label={user.role === 'admin' ? 'Admin' : 'User'}
                    size="small"
                    color={user.role === 'admin' ? 'warning' : 'primary'}
                    variant="outlined"
                  />
                </TableCell>
                <TableCell>
                  <Chip
                    label={user.is_active ? 'Active' : 'Inactive'}
                    size="small"
                    color={user.is_active ? 'success' : 'default'}
                  />
                </TableCell>
                <TableCell>
                  {new Date(user.created_at).toLocaleDateString()}
                </TableCell>
                <TableCell align="right">
                  <Tooltip title="Edit">
                    <IconButton
                      size="small"
                      onClick={() => handleOpenEditDialog(user)}
                    >
                      <Edit fontSize="small" />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Reset Password">
                    <IconButton
                      size="small"
                      onClick={() => handleOpenResetPasswordDialog(user)}
                    >
                      <Lock fontSize="small" />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Delete">
                    <IconButton
                      size="small"
                      onClick={() => handleOpenDeleteDialog(user)}
                      disabled={user.id === currentUser?.id}
                      color="error"
                    >
                      <Delete fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </TableCell>
              </TableRow>
            ))}
            {filteredUsers.length === 0 && !loading && (
              <TableRow>
                <TableCell colSpan={6} align="center" sx={{ py: 4 }}>
                  <Typography color="text.secondary">
                    {searchQuery ? 'No users match your search' : 'No users found'}
                  </Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Create User Dialog */}
      <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create New User</DialogTitle>
        <DialogContent>
          {formError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {formError}
            </Alert>
          )}
          <TextField
            fullWidth
            label="Username"
            value={formData.username}
            onChange={(e) => setFormData({ ...formData, username: e.target.value })}
            margin="normal"
            required
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Person color="action" />
                </InputAdornment>
              ),
            }}
          />
          <TextField
            fullWidth
            label="Email"
            type="email"
            value={formData.email}
            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
            margin="normal"
            required
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Email color="action" />
                </InputAdornment>
              ),
            }}
          />
          <TextField
            fullWidth
            label="Password"
            type={showPassword ? 'text' : 'password'}
            value={formData.password}
            onChange={(e) => setFormData({ ...formData, password: e.target.value })}
            margin="normal"
            required
            helperText="At least 6 characters"
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Lock color="action" />
                </InputAdornment>
              ),
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton onClick={() => setShowPassword(!showPassword)} edge="end">
                    {showPassword ? <VisibilityOff /> : <Visibility />}
                  </IconButton>
                </InputAdornment>
              ),
            }}
          />
          <FormControl fullWidth margin="normal">
            <InputLabel>Role</InputLabel>
            <Select
              value={formData.role}
              onChange={(e) => setFormData({ ...formData, role: e.target.value })}
              label="Role"
            >
              <MenuItem value="user">User</MenuItem>
              <MenuItem value="admin">Admin</MenuItem>
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button onClick={() => setCreateDialogOpen(false)} disabled={submitting}>
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={handleCreateUser}
            disabled={submitting}
            sx={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}
          >
            {submitting ? <CircularProgress size={20} /> : 'Create User'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Edit User Dialog */}
      <Dialog open={editDialogOpen} onClose={() => setEditDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Edit User: {selectedUser?.username}</DialogTitle>
        <DialogContent>
          {formError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {formError}
            </Alert>
          )}
          <TextField
            fullWidth
            label="Username"
            value={formData.username}
            disabled
            margin="normal"
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Person color="action" />
                </InputAdornment>
              ),
            }}
          />
          <TextField
            fullWidth
            label="Email"
            type="email"
            value={formData.email}
            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
            margin="normal"
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Email color="action" />
                </InputAdornment>
              ),
            }}
          />
          <FormControl fullWidth margin="normal">
            <InputLabel>Role</InputLabel>
            <Select
              value={formData.role}
              onChange={(e) => setFormData({ ...formData, role: e.target.value })}
              label="Role"
              disabled={selectedUser?.id === currentUser?.id}
            >
              <MenuItem value="user">User</MenuItem>
              <MenuItem value="admin">Admin</MenuItem>
            </Select>
          </FormControl>
          <FormControlLabel
            control={
              <Switch
                checked={formData.is_active}
                onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                disabled={selectedUser?.id === currentUser?.id}
              />
            }
            label="Active"
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button onClick={() => setEditDialogOpen(false)} disabled={submitting}>
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={handleUpdateUser}
            disabled={submitting}
            sx={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}
          >
            {submitting ? <CircularProgress size={20} /> : 'Save Changes'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete User Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Delete User</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete user <strong>{selectedUser?.username}</strong>?
          </Typography>
          <Typography variant="body2" color="error" sx={{ mt: 1 }}>
            This action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button onClick={() => setDeleteDialogOpen(false)} disabled={submitting}>
            Cancel
          </Button>
          <Button
            variant="contained"
            color="error"
            onClick={handleDeleteUser}
            disabled={submitting}
          >
            {submitting ? <CircularProgress size={20} /> : 'Delete User'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Reset Password Dialog */}
      <Dialog open={resetPasswordDialogOpen} onClose={() => setResetPasswordDialogOpen(false)}>
        <DialogTitle>Reset Password</DialogTitle>
        <DialogContent>
          <Typography>
            Reset password for user <strong>{selectedUser?.username}</strong>?
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            A temporary password will be generated. The user should change it after logging in.
          </Typography>
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button onClick={() => setResetPasswordDialogOpen(false)} disabled={submitting}>
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={handleResetPassword}
            disabled={submitting}
            sx={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}
          >
            {submitting ? <CircularProgress size={20} /> : 'Reset Password'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert onClose={handleCloseSnackbar} severity={snackbar.severity} variant="filled">
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}
