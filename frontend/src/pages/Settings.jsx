import { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Tabs,
  Tab,
  Grid,
  Card,
  CardContent,
  Button,
  TextField,
  Switch,
  FormControlLabel,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
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
  Person,
  Group,
  Security,
  Business,
  Add,
  Edit,
  Delete,
  AdminPanelSettings,
  SupervisorAccount,
  PersonOutline,
  Refresh,
} from '@mui/icons-material';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { useOrganization } from '../context/OrganizationContext';

// Helper to get auth headers
const getAuthHeaders = () => {
  const token = localStorage.getItem('auth_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
};

const orgRoleLabels = {
  org_admin: 'Org Admin',
  manager: 'Manager',
  member: 'Member',
};

const orgRoleColors = {
  org_admin: 'error',
  manager: 'warning',
  member: 'primary',
};

const orgRoleDescriptions = {
  org_admin: 'Full organization control, can manage all users and projects',
  manager: 'Can create projects and assign users to projects',
  member: 'Can only access assigned projects',
};

function TabPanel({ children, value, index }) {
  return (
    <Box hidden={value !== index} sx={{ py: 3 }}>
      {value === index && children}
    </Box>
  );
}

export default function Settings() {
  const { user, isAdmin } = useAuth();
  const { organization, orgRole, isOrgAdmin, refresh: refreshOrg } = useOrganization();
  const [tabValue, setTabValue] = useState(0);

  // Organization members state
  const [orgMembers, setOrgMembers] = useState([]);
  const [loadingMembers, setLoadingMembers] = useState(true);

  // User management state (for system admins)
  const [users, setUsers] = useState([]);
  const [loadingUsers, setLoadingUsers] = useState(true);

  // Dialog states
  const [userDialog, setUserDialog] = useState({ open: false, user: null });
  const [deleteDialog, setDeleteDialog] = useState({ open: false, user: null });
  const [roleDialog, setRoleDialog] = useState({ open: false, member: null });
  const [selectedOrgRole, setSelectedOrgRole] = useState('member');
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  // New user form
  const [newUser, setNewUser] = useState({
    username: '',
    email: '',
    password: '',
    role: 'user',
    org_role: 'member',
  });

  useEffect(() => {
    if (isAdmin) {
      loadUsers();
    }
    if (organization?.id) {
      loadOrgMembers();
    }
  }, [isAdmin, organization?.id]);

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

  const loadOrgMembers = async () => {
    if (!organization?.id) return;
    try {
      setLoadingMembers(true);
      const response = await axios.get(
        `/api/organizations/${organization.id}/members`,
        { headers: getAuthHeaders() }
      );
      setOrgMembers(response.data || []);
    } catch (error) {
      console.error('Failed to load org members:', error);
    } finally {
      setLoadingMembers(false);
    }
  };

  const handleCreateUser = async () => {
    try {
      setActionLoading(true);
      setError(null);
      await axios.post('/api/auth/register', newUser, { headers: getAuthHeaders() });
      setUserDialog({ open: false, user: null });
      setNewUser({ username: '', email: '', password: '', role: 'user', org_role: 'member' });
      setSuccess('User created successfully');
      loadUsers();
      loadOrgMembers();
    } catch (error) {
      console.error('Failed to create user:', error);
      setError(error.response?.data?.detail || 'Failed to create user');
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
      loadOrgMembers();
    } catch (error) {
      console.error('Failed to delete user:', error);
      setError(error.response?.data?.detail || 'Failed to delete user');
    } finally {
      setActionLoading(false);
    }
  };

  const handleUpdateOrgRole = async () => {
    if (!roleDialog.member || !organization?.id) return;
    try {
      setActionLoading(true);
      setError(null);
      await axios.put(
        `/api/organizations/${organization.id}/members/${roleDialog.member.user_id}`,
        { org_role: selectedOrgRole },
        { headers: getAuthHeaders() }
      );
      setRoleDialog({ open: false, member: null });
      setSuccess('Organization role updated successfully');
      loadOrgMembers();
      refreshOrg();
    } catch (error) {
      console.error('Failed to update org role:', error);
      setError(error.response?.data?.detail || 'Failed to update organization role');
    } finally {
      setActionLoading(false);
    }
  };

  const handleRemoveFromOrg = async (userId) => {
    if (!organization?.id) return;
    if (!confirm('Are you sure you want to remove this member from the organization?')) return;

    try {
      setError(null);
      await axios.delete(
        `/api/organizations/${organization.id}/members/${userId}`,
        { headers: getAuthHeaders() }
      );
      setSuccess('Member removed from organization');
      loadOrgMembers();
    } catch (error) {
      console.error('Failed to remove member:', error);
      setError(error.response?.data?.detail || 'Failed to remove member');
    }
  };

  // Determine which tabs to show
  const tabs = [];
  if (isOrgAdmin) {
    tabs.push({ icon: <Business />, label: 'Organization', key: 'org' });
  }
  tabs.push({ icon: <Group />, label: 'Members', key: 'members' });
  tabs.push({ icon: <Person />, label: 'Profile', key: 'profile' });
  tabs.push({ icon: <Security />, label: 'Security', key: 'security' });

  const getCurrentTabKey = () => tabs[tabValue]?.key || 'members';

  return (
    <Box>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
          Settings
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Manage organization, users, and system configuration
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

      {/* Tabs */}
      <Paper sx={{ borderRadius: 2, mb: 3 }}>
        <Tabs
          value={tabValue}
          onChange={(e, v) => setTabValue(v)}
          sx={{ borderBottom: 1, borderColor: 'divider', px: 2 }}
        >
          {tabs.map((tab) => (
            <Tab key={tab.key} icon={tab.icon} iconPosition="start" label={tab.label} />
          ))}
        </Tabs>
      </Paper>

      {/* Organization Tab (Org Admin only) */}
      {getCurrentTabKey() === 'org' && (
        <TabPanel value={tabValue} index={tabs.findIndex(t => t.key === 'org')}>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 3, borderRadius: 2 }}>
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
                  Organization Details
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 3, mb: 3 }}>
                  <Avatar sx={{ width: 64, height: 64, fontSize: '1.5rem', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
                    <Business />
                  </Avatar>
                  <Box>
                    <Typography variant="h5" sx={{ fontWeight: 600 }}>
                      {organization?.name || 'Default Organization'}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {organization?.slug || 'default'}
                    </Typography>
                  </Box>
                </Box>
                <Divider sx={{ my: 2 }} />
                <List dense>
                  <ListItem>
                    <ListItemText primary="Organization ID" secondary={organization?.id || 'N/A'} />
                  </ListItem>
                  <ListItem>
                    <ListItemText
                      primary="Your Role"
                      secondary={<Chip size="small" label={orgRoleLabels[orgRole] || orgRole} color={orgRoleColors[orgRole] || 'default'} />}
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText primary="Total Members" secondary={orgMembers.length} />
                  </ListItem>
                </List>
              </Paper>
            </Grid>
            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 3, borderRadius: 2 }}>
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>Quick Stats</Typography>
                <Grid container spacing={2}>
                  <Grid item xs={6}>
                    <Card variant="outlined">
                      <CardContent sx={{ textAlign: 'center' }}>
                        <Typography variant="h4" color="primary" sx={{ fontWeight: 700 }}>
                          {orgMembers.filter(m => m.org_role === 'org_admin').length}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">Admins</Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                  <Grid item xs={6}>
                    <Card variant="outlined">
                      <CardContent sx={{ textAlign: 'center' }}>
                        <Typography variant="h4" color="warning.main" sx={{ fontWeight: 700 }}>
                          {orgMembers.filter(m => m.org_role === 'manager').length}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">Managers</Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                  <Grid item xs={6}>
                    <Card variant="outlined">
                      <CardContent sx={{ textAlign: 'center' }}>
                        <Typography variant="h4" color="info.main" sx={{ fontWeight: 700 }}>
                          {orgMembers.filter(m => m.org_role === 'member').length}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">Members</Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                  <Grid item xs={6}>
                    <Card variant="outlined">
                      <CardContent sx={{ textAlign: 'center' }}>
                        <Typography variant="h4" color="success.main" sx={{ fontWeight: 700 }}>{orgMembers.length}</Typography>
                        <Typography variant="body2" color="text.secondary">Total</Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                </Grid>
              </Paper>
            </Grid>
          </Grid>
        </TabPanel>
      )}

      {/* Members Tab */}
      {getCurrentTabKey() === 'members' && (
        <TabPanel value={tabValue} index={tabs.findIndex(t => t.key === 'members')}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              {isOrgAdmin ? 'Organization Members' : 'Team Members'}
            </Typography>
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Tooltip title="Refresh">
                <IconButton onClick={() => { loadOrgMembers(); loadUsers(); }}>
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
            {loadingMembers ? (
              <Box sx={{ p: 2 }}>
                {[1, 2, 3].map(i => (
                  <Skeleton key={i} variant="rectangular" height={72} sx={{ mb: 1, borderRadius: 1 }} />
                ))}
              </Box>
            ) : orgMembers.length === 0 ? (
              <Alert severity="info" sx={{ m: 2 }}>
                No members found in this organization.
              </Alert>
            ) : (
              <List>
                {orgMembers.map((member, idx) => (
                  <Box key={member.id || member.user_id}>
                    {idx > 0 && <Divider />}
                    <ListItem sx={{ py: 2 }}>
                      <Avatar
                        sx={{
                          mr: 2,
                          background: member.org_role === 'org_admin'
                            ? 'linear-gradient(135deg, #f44336 0%, #e91e63 100%)'
                            : member.org_role === 'manager'
                              ? 'linear-gradient(135deg, #f57c00 0%, #ff9800 100%)'
                              : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                        }}
                      >
                        {member.username?.charAt(0).toUpperCase()}
                      </Avatar>
                      <ListItemText
                        primary={
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                            <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                              {member.username}
                            </Typography>
                            <Chip
                              size="small"
                              icon={
                                member.org_role === 'org_admin' ? <AdminPanelSettings sx={{ fontSize: 14 }} /> :
                                member.org_role === 'manager' ? <SupervisorAccount sx={{ fontSize: 14 }} /> :
                                <PersonOutline sx={{ fontSize: 14 }} />
                              }
                              label={orgRoleLabels[member.org_role] || member.org_role}
                              color={orgRoleColors[member.org_role] || 'default'}
                              sx={{ height: 24, fontSize: '0.75rem' }}
                            />
                            {member.user_id === user?.id && (
                              <Chip size="small" label="You" variant="outlined" sx={{ height: 20, fontSize: '0.7rem' }} />
                            )}
                          </Box>
                        }
                        secondary={<Typography variant="body2" color="text.secondary">{member.email}</Typography>}
                      />
                      {isOrgAdmin && member.user_id !== user?.id && (
                        <ListItemSecondaryAction>
                          <Tooltip title="Change Role">
                            <IconButton onClick={() => { setSelectedOrgRole(member.org_role); setRoleDialog({ open: true, member }); }}>
                              <Edit />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Remove from Organization">
                            <IconButton color="error" onClick={() => handleRemoveFromOrg(member.user_id)}>
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
        </TabPanel>
      )}

      {/* Profile Tab */}
      {getCurrentTabKey() === 'profile' && (
        <TabPanel value={tabValue} index={tabs.findIndex(t => t.key === 'profile')}>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 3, borderRadius: 2 }}>
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>Your Profile</Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 3, mb: 4 }}>
                  <Avatar
                    sx={{
                      width: 80,
                      height: 80,
                      fontSize: '2rem',
                      background: isAdmin
                        ? 'linear-gradient(135deg, #f57c00 0%, #ff9800 100%)'
                        : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    }}
                  >
                    {user?.username?.charAt(0).toUpperCase()}
                  </Avatar>
                  <Box>
                    <Typography variant="h5" sx={{ fontWeight: 600 }}>{user?.username}</Typography>
                    <Typography variant="body2" color="text.secondary">{user?.email}</Typography>
                    <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
                      <Chip size="small" label={isAdmin ? 'System Admin' : 'User'} color={isAdmin ? 'warning' : 'primary'} />
                      {orgRole && (
                        <Chip size="small" label={orgRoleLabels[orgRole] || orgRole} color={orgRoleColors[orgRole] || 'default'} variant="outlined" />
                      )}
                    </Box>
                  </Box>
                </Box>
                <Divider sx={{ my: 3 }} />
                <List dense>
                  <ListItem>
                    <ListItemText primary="Organization" secondary={organization?.name || 'Default Organization'} />
                  </ListItem>
                  <ListItem>
                    <ListItemText primary="Organization Role" secondary={orgRoleLabels[orgRole] || 'Member'} />
                  </ListItem>
                </List>
              </Paper>
            </Grid>
          </Grid>
        </TabPanel>
      )}

      {/* Security Tab */}
      {getCurrentTabKey() === 'security' && (
        <TabPanel value={tabValue} index={tabs.findIndex(t => t.key === 'security')}>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 3, borderRadius: 2 }}>
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>Security Settings</Typography>
                <List>
                  <ListItem>
                    <ListItemText primary="Session Timeout" secondary="Sessions expire after 2 hours of inactivity" />
                  </ListItem>
                  <Divider />
                  <ListItem>
                    <ListItemText primary="Password Requirements" secondary="Minimum 6 characters required" />
                  </ListItem>
                  <Divider />
                  <ListItem>
                    <ListItemText primary="Authentication" secondary="JWT-based authentication with secure token storage" />
                  </ListItem>
                </List>
              </Paper>
            </Grid>
          </Grid>
        </TabPanel>
      )}

      {/* Add User Dialog */}
      <Dialog open={userDialog.open} onClose={() => setUserDialog({ open: false, user: null })} maxWidth="sm" fullWidth>
        <DialogTitle>Add New User</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField label="Username" value={newUser.username} onChange={(e) => setNewUser({ ...newUser, username: e.target.value })} fullWidth />
            <TextField label="Email" type="email" value={newUser.email} onChange={(e) => setNewUser({ ...newUser, email: e.target.value })} fullWidth />
            <TextField label="Password" type="password" value={newUser.password} onChange={(e) => setNewUser({ ...newUser, password: e.target.value })} fullWidth helperText="User will be required to change password on first login" />
            <FormControl fullWidth>
              <InputLabel>Organization Role</InputLabel>
              <Select value={newUser.org_role} label="Organization Role" onChange={(e) => setNewUser({ ...newUser, org_role: e.target.value })}>
                {Object.entries(orgRoleLabels).map(([value, label]) => (
                  <MenuItem key={value} value={value}>
                    <Box>
                      <Typography variant="body2">{label}</Typography>
                      <Typography variant="caption" color="text.secondary">{orgRoleDescriptions[value]}</Typography>
                    </Box>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControlLabel
              control={<Switch checked={newUser.role === 'admin'} onChange={(e) => setNewUser({ ...newUser, role: e.target.checked ? 'admin' : 'user' })} />}
              label="System Administrator (has access to all system features)"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setUserDialog({ open: false, user: null })}>Cancel</Button>
          <Button variant="contained" onClick={handleCreateUser} disabled={actionLoading || !newUser.username || !newUser.email || !newUser.password}>
            {actionLoading ? <CircularProgress size={20} /> : 'Create User'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Change Org Role Dialog */}
      <Dialog open={roleDialog.open} onClose={() => setRoleDialog({ open: false, member: null })} maxWidth="sm" fullWidth>
        <DialogTitle>Change Organization Role</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2 }}>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Changing role for: <strong>{roleDialog.member?.username}</strong>
            </Typography>
            <FormControl fullWidth>
              <InputLabel>Organization Role</InputLabel>
              <Select value={selectedOrgRole} label="Organization Role" onChange={(e) => setSelectedOrgRole(e.target.value)}>
                {Object.entries(orgRoleLabels).map(([value, label]) => (
                  <MenuItem key={value} value={value}>
                    <Box>
                      <Typography variant="body2">{label}</Typography>
                      <Typography variant="caption" color="text.secondary">{orgRoleDescriptions[value]}</Typography>
                    </Box>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRoleDialog({ open: false, member: null })}>Cancel</Button>
          <Button variant="contained" onClick={handleUpdateOrgRole} disabled={actionLoading}>
            {actionLoading ? <CircularProgress size={20} /> : 'Update Role'}
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
    </Box>
  );
}
