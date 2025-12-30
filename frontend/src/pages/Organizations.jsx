/**
 * Organizations Management Page
 * Super Admin only - manage all organizations
 */
import { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Button,
  TextField,
  Grid,
  Card,
  CardContent,
  CardActions,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  Chip,
  Avatar,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
  ListItemSecondaryAction,
  Divider,
  CircularProgress,
  Tooltip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import {
  Add,
  Business,
  Group,
  Folder,
  Edit,
  Delete,
  Refresh,
  AdminPanelSettings,
  PersonAdd,
  Link as LinkIcon,
  ContentCopy,
} from '@mui/icons-material';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';

const getAuthHeaders = () => {
  const token = localStorage.getItem('auth_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
};

export default function Organizations() {
  const { user, isAdmin } = useAuth();
  const [organizations, setOrganizations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  // Create org dialog
  const [createDialog, setCreateDialog] = useState(false);
  const [newOrg, setNewOrg] = useState({ name: '', description: '' });
  const [creating, setCreating] = useState(false);

  // Manage org dialog (view members, assign admin)
  const [manageDialog, setManageDialog] = useState({ open: false, org: null });
  const [orgMembers, setOrgMembers] = useState([]);
  const [loadingMembers, setLoadingMembers] = useState(false);

  // Add user to org dialog
  const [addUserDialog, setAddUserDialog] = useState({ open: false, org: null });
  const [allUsers, setAllUsers] = useState([]);
  const [selectedUserId, setSelectedUserId] = useState('');
  const [selectedOrgRole, setSelectedOrgRole] = useState('member');
  const [addingUser, setAddingUser] = useState(false);

  // Invite dialog state
  const [inviteDialog, setInviteDialog] = useState({ open: false, org: null });
  const [inviteRole, setInviteRole] = useState('member');
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteExpiry, setInviteExpiry] = useState(48);
  const [creatingInvite, setCreatingInvite] = useState(false);
  const [generatedInvite, setGeneratedInvite] = useState(null);

  useEffect(() => {
    loadOrganizations();
    loadAllUsers();
  }, []);

  const loadOrganizations = async () => {
    try {
      setLoading(true);
      const response = await axios.get('/api/organizations', { headers: getAuthHeaders() });
      setOrganizations(response.data || []);
    } catch (err) {
      console.error('Failed to load organizations:', err);
      setError('Failed to load organizations');
    } finally {
      setLoading(false);
    }
  };

  const loadAllUsers = async () => {
    try {
      const response = await axios.get('/api/auth/users', { headers: getAuthHeaders() });
      setAllUsers(response.data || []);
    } catch (err) {
      console.error('Failed to load users:', err);
    }
  };

  const loadOrgMembers = async (orgId) => {
    try {
      setLoadingMembers(true);
      const response = await axios.get(`/api/organizations/${orgId}/members`, { headers: getAuthHeaders() });
      setOrgMembers(response.data || []);
    } catch (err) {
      console.error('Failed to load org members:', err);
    } finally {
      setLoadingMembers(false);
    }
  };

  const handleCreateOrg = async () => {
    if (!newOrg.name.trim()) {
      setError('Organization name is required');
      return;
    }

    try {
      setCreating(true);
      setError(null);
      await axios.post('/api/organizations', newOrg, { headers: getAuthHeaders() });
      setSuccess('Organization created successfully');
      setCreateDialog(false);
      setNewOrg({ name: '', description: '' });
      loadOrganizations();
    } catch (err) {
      console.error('Failed to create organization:', err);
      setError(err.response?.data?.detail || 'Failed to create organization');
    } finally {
      setCreating(false);
    }
  };

  const handleManageOrg = async (org) => {
    setManageDialog({ open: true, org });
    await loadOrgMembers(org.id);
  };

  const handleAddUserToOrg = async () => {
    if (!selectedUserId || !addUserDialog.org) return;

    try {
      setAddingUser(true);
      setError(null);
      await axios.post(
        `/api/organizations/${addUserDialog.org.id}/members`,
        { user_id: selectedUserId, org_role: selectedOrgRole },
        { headers: getAuthHeaders() }
      );
      setSuccess('User added to organization');
      setAddUserDialog({ open: false, org: null });
      setSelectedUserId('');
      setSelectedOrgRole('member');

      // Refresh members if manage dialog is open
      if (manageDialog.open && manageDialog.org?.id === addUserDialog.org.id) {
        await loadOrgMembers(addUserDialog.org.id);
      }
      loadOrganizations();
    } catch (err) {
      console.error('Failed to add user to org:', err);
      setError(err.response?.data?.detail || 'Failed to add user to organization');
    } finally {
      setAddingUser(false);
    }
  };

  const handleRemoveFromOrg = async (orgId, userId) => {
    if (!confirm('Remove this user from the organization?')) return;

    try {
      await axios.delete(`/api/organizations/${orgId}/members/${userId}`, { headers: getAuthHeaders() });
      setSuccess('User removed from organization');
      await loadOrgMembers(orgId);
      loadOrganizations();
    } catch (err) {
      console.error('Failed to remove user:', err);
      setError(err.response?.data?.detail || 'Failed to remove user');
    }
  };

  const handleUpdateOrgRole = async (orgId, userId, newRole) => {
    try {
      await axios.put(
        `/api/organizations/${orgId}/members/${userId}`,
        { org_role: newRole },
        { headers: getAuthHeaders() }
      );
      setSuccess('Role updated');
      await loadOrgMembers(orgId);
    } catch (err) {
      console.error('Failed to update role:', err);
      setError(err.response?.data?.detail || 'Failed to update role');
    }
  };
  const handleCreateInvite = async () => {
    if (!inviteDialog.org) return;
    try {
      setCreatingInvite(true);
      setError(null);
      const response = await axios.post(
        `/api/organizations/${inviteDialog.org.id}/invites`,
        {
          email: inviteEmail || null,
          org_role: inviteRole,
          expires_in_hours: inviteExpiry,
          max_uses: 1
        },
        { headers: getAuthHeaders() }
      );
      setGeneratedInvite(response.data);
      setSuccess('Invite link generated');
    } catch (err) {
      console.error('Failed to create invite:', err);
      setError(err.response?.data?.detail || 'Failed to create invite');
    } finally {
      setCreatingInvite(false);
    }
  };

  const copyInviteLink = () => {
    if (!generatedInvite) return;
    const fullUrl = `${window.location.origin}${generatedInvite.invite_url}`;
    navigator.clipboard.writeText(fullUrl);
    setSuccess('Invite link copied to clipboard');
  };

  const resetInviteDialog = () => {
    setInviteDialog({ open: false, org: null });
    setInviteRole('member');
    setInviteEmail('');
    setInviteExpiry(48);
    setGeneratedInvite(null);
  };


  // Get users not in the selected org
  const getAvailableUsers = (org) => {
    if (!org) return allUsers;
    const memberIds = orgMembers.map(m => m.user_id);
    return allUsers.filter(u => !memberIds.includes(u.id));
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

  if (!isAdmin) {
    return (
      <Box sx={{ p: 4 }}>
        <Alert severity="error">Access denied. Super Admin only.</Alert>
      </Box>
    );
  }

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
            Organizations
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Manage all organizations in the system (Super Admin)
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Tooltip title="Refresh">
            <IconButton onClick={loadOrganizations}>
              <Refresh />
            </IconButton>
          </Tooltip>
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => setCreateDialog(true)}
            sx={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}
          >
            Create Organization
          </Button>
        </Box>
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

      {/* Organizations Grid */}
      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress />
        </Box>
      ) : organizations.length === 0 ? (
        <Paper sx={{ p: 4, textAlign: 'center', borderRadius: 2 }}>
          <Business sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h6" color="text.secondary">
            No organizations yet
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Create your first organization to get started
          </Typography>
          <Button variant="contained" startIcon={<Add />} onClick={() => setCreateDialog(true)}>
            Create Organization
          </Button>
        </Paper>
      ) : (
        <Grid container spacing={3}>
          {organizations.map((org) => (
            <Grid item xs={12} md={6} lg={4} key={org.id}>
              <Card sx={{ borderRadius: 2, height: '100%', display: 'flex', flexDirection: 'column' }}>
                <CardContent sx={{ flexGrow: 1 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                    <Avatar
                      sx={{
                        width: 48,
                        height: 48,
                        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                      }}
                    >
                      <Business />
                    </Avatar>
                    <Box>
                      <Typography variant="h6" sx={{ fontWeight: 600 }}>
                        {org.name}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {org.slug}
                      </Typography>
                    </Box>
                  </Box>

                  {org.description && (
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                      {org.description}
                    </Typography>
                  )}

                  <Box sx={{ display: 'flex', gap: 2 }}>
                    <Chip
                      icon={<Group sx={{ fontSize: 16 }} />}
                      label={`${org.member_count || 0} members`}
                      size="small"
                      variant="outlined"
                    />
                    <Chip
                      icon={<Folder sx={{ fontSize: 16 }} />}
                      label={`${org.project_count || 0} projects`}
                      size="small"
                      variant="outlined"
                    />
                  </Box>
                </CardContent>
                <Divider />
                <CardActions sx={{ justifyContent: 'space-between', px: 2, flexWrap: 'wrap', gap: 1 }}>
                  <Button
                    size="small"
                    startIcon={<Group />}
                    onClick={() => handleManageOrg(org)}
                  >
                    Members
                  </Button>
                  <Button
                    size="small"
                    startIcon={<LinkIcon />}
                    onClick={() => setInviteDialog({ open: true, org })}
                  >
                    Invite Link
                  </Button>
                  <Button
                    size="small"
                    startIcon={<PersonAdd />}
                    onClick={() => {
                      setAddUserDialog({ open: true, org });
                      loadOrgMembers(org.id);
                    }}
                  >
                    Add User
                  </Button>
                </CardActions>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      {/* Create Organization Dialog */}
      <Dialog open={createDialog} onClose={() => setCreateDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create New Organization</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              label="Organization Name"
              value={newOrg.name}
              onChange={(e) => setNewOrg({ ...newOrg, name: e.target.value })}
              fullWidth
              required
              placeholder="e.g., Acme Corp"
            />
            <TextField
              label="Description"
              value={newOrg.description}
              onChange={(e) => setNewOrg({ ...newOrg, description: e.target.value })}
              fullWidth
              multiline
              rows={3}
              placeholder="Optional description"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialog(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleCreateOrg}
            disabled={creating || !newOrg.name.trim()}
          >
            {creating ? <CircularProgress size={20} /> : 'Create Organization'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Manage Organization Members Dialog */}
      <Dialog
        open={manageDialog.open}
        onClose={() => setManageDialog({ open: false, org: null })}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Avatar sx={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
              <Business />
            </Avatar>
            <Box>
              <Typography variant="h6">{manageDialog.org?.name}</Typography>
              <Typography variant="body2" color="text.secondary">
                Manage organization members
              </Typography>
            </Box>
          </Box>
        </DialogTitle>
        <DialogContent>
          {loadingMembers ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
              <CircularProgress />
            </Box>
          ) : orgMembers.length === 0 ? (
            <Alert severity="info">No members in this organization yet.</Alert>
          ) : (
            <List>
              {orgMembers.map((member, idx) => (
                <Box key={member.id || member.user_id}>
                  {idx > 0 && <Divider />}
                  <ListItem>
                    <ListItemAvatar>
                      <Avatar
                        sx={{
                          background:
                            member.org_role === 'org_admin'
                              ? 'linear-gradient(135deg, #f44336 0%, #e91e63 100%)'
                              : member.org_role === 'manager'
                              ? 'linear-gradient(135deg, #f57c00 0%, #ff9800 100%)'
                              : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                        }}
                      >
                        {member.username?.charAt(0).toUpperCase()}
                      </Avatar>
                    </ListItemAvatar>
                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                            {member.username}
                          </Typography>
                          <Chip
                            size="small"
                            label={orgRoleLabels[member.org_role] || member.org_role}
                            color={orgRoleColors[member.org_role] || 'default'}
                          />
                        </Box>
                      }
                      secondary={member.email}
                    />
                    <ListItemSecondaryAction>
                      <FormControl size="small" sx={{ minWidth: 120, mr: 1 }}>
                        <Select
                          value={member.org_role}
                          onChange={(e) =>
                            handleUpdateOrgRole(manageDialog.org?.id, member.user_id, e.target.value)
                          }
                          size="small"
                        >
                          <MenuItem value="org_admin">Org Admin</MenuItem>
                          <MenuItem value="manager">Manager</MenuItem>
                          <MenuItem value="member">Member</MenuItem>
                        </Select>
                      </FormControl>
                      <IconButton
                        color="error"
                        onClick={() => handleRemoveFromOrg(manageDialog.org?.id, member.user_id)}
                      >
                        <Delete />
                      </IconButton>
                    </ListItemSecondaryAction>
                  </ListItem>
                </Box>
              ))}
            </List>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setManageDialog({ open: false, org: null })}>Close</Button>
          <Button
            variant="contained"
            startIcon={<PersonAdd />}
            onClick={() => {
              setAddUserDialog({ open: true, org: manageDialog.org });
            }}
          >
            Add User
          </Button>
        </DialogActions>
      </Dialog>

      {/* Add User to Organization Dialog */}
      <Dialog
        open={addUserDialog.open}
        onClose={() => setAddUserDialog({ open: false, org: null })}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Add User to {addUserDialog.org?.name}</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <FormControl fullWidth>
              <InputLabel>Select User</InputLabel>
              <Select
                value={selectedUserId}
                label="Select User"
                onChange={(e) => setSelectedUserId(e.target.value)}
              >
                {getAvailableUsers(addUserDialog.org).map((u) => (
                  <MenuItem key={u.id} value={u.id}>
                    {u.username} ({u.email})
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl fullWidth>
              <InputLabel>Organization Role</InputLabel>
              <Select
                value={selectedOrgRole}
                label="Organization Role"
                onChange={(e) => setSelectedOrgRole(e.target.value)}
              >
                <MenuItem value="org_admin">
                  <Box>
                    <Typography variant="body2">Org Admin</Typography>
                    <Typography variant="caption" color="text.secondary">
                      Full organization control
                    </Typography>
                  </Box>
                </MenuItem>
                <MenuItem value="manager">
                  <Box>
                    <Typography variant="body2">Manager</Typography>
                    <Typography variant="caption" color="text.secondary">
                      Can manage projects and assign users
                    </Typography>
                  </Box>
                </MenuItem>
                <MenuItem value="member">
                  <Box>
                    <Typography variant="body2">Member</Typography>
                    <Typography variant="caption" color="text.secondary">
                      Can only access assigned projects
                    </Typography>
                  </Box>
                </MenuItem>
              </Select>
            </FormControl>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAddUserDialog({ open: false, org: null })}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleAddUserToOrg}
            disabled={addingUser || !selectedUserId}
          >
            {addingUser ? <CircularProgress size={20} /> : 'Add to Organization'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Generate Invite Dialog */}
      <Dialog
        open={inviteDialog.open}
        onClose={resetInviteDialog}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <LinkIcon color="primary" />
            <Box>
              <Typography variant="h6">Generate Invite Link</Typography>
              <Typography variant="body2" color="text.secondary">
                {inviteDialog.org?.name}
              </Typography>
            </Box>
          </Box>
        </DialogTitle>
        <DialogContent>
          {!generatedInvite ? (
            <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
              <TextField
                label="Email (Optional)"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                fullWidth
                placeholder="Leave empty for anyone to use"
                helperText="If set, only this email can use the invite"
              />
              <FormControl fullWidth>
                <InputLabel>Role</InputLabel>
                <Select
                  value={inviteRole}
                  label="Role"
                  onChange={(e) => setInviteRole(e.target.value)}
                >
                  <MenuItem value="org_admin">Org Admin</MenuItem>
                  <MenuItem value="manager">Manager</MenuItem>
                  <MenuItem value="member">Member</MenuItem>
                </Select>
              </FormControl>
              <FormControl fullWidth>
                <InputLabel>Expires In</InputLabel>
                <Select
                  value={inviteExpiry}
                  label="Expires In"
                  onChange={(e) => setInviteExpiry(e.target.value)}
                >
                  <MenuItem value={24}>24 hours</MenuItem>
                  <MenuItem value={48}>48 hours</MenuItem>
                  <MenuItem value={72}>72 hours</MenuItem>
                  <MenuItem value={168}>1 week</MenuItem>
                </Select>
              </FormControl>
            </Box>
          ) : (
            <Box sx={{ pt: 2 }}>
              <Alert severity="success" sx={{ mb: 2 }}>
                Invite link generated successfully!
              </Alert>
              <Paper
                variant="outlined"
                sx={{
                  p: 2,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1,
                  bgcolor: 'action.hover',
                }}
              >
                <Typography
                  variant="body2"
                  sx={{
                    flexGrow: 1,
                    fontFamily: 'monospace',
                    wordBreak: 'break-all',
                  }}
                >
                  {window.location.origin}{generatedInvite.invite_url}
                </Typography>
                <Tooltip title="Copy to clipboard">
                  <IconButton onClick={copyInviteLink} color="primary">
                    <ContentCopy />
                  </IconButton>
                </Tooltip>
              </Paper>
              <Box sx={{ mt: 2 }}>
                <Typography variant="body2" color="text.secondary">
                  Role: <strong>{generatedInvite.org_role}</strong>
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Expires: {new Date(generatedInvite.expires_at).toLocaleString()}
                </Typography>
                {generatedInvite.email && (
                  <Typography variant="body2" color="text.secondary">
                    Restricted to: <strong>{generatedInvite.email}</strong>
                  </Typography>
                )}
              </Box>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={resetInviteDialog}>
            {generatedInvite ? 'Close' : 'Cancel'}
          </Button>
          {!generatedInvite && (
            <Button
              variant="contained"
              onClick={handleCreateInvite}
              disabled={creatingInvite}
            >
              {creatingInvite ? <CircularProgress size={20} /> : 'Generate Link'}
            </Button>
          )}
        </DialogActions>
      </Dialog>
    </Box>
  );
}
