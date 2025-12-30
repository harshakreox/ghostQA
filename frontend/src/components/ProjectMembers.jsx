/**
 * Project Members Management Component
 * Used within project settings to manage project-level permissions
 */
import { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Avatar,
  Chip,
  Divider,
  Alert,
  Skeleton,
  Tooltip,
} from '@mui/material';
import {
  Add,
  Delete,
  Edit,
  Person,
  PersonAdd,
} from '@mui/icons-material';
import axios from 'axios';
import { useOrganization } from '../context/OrganizationContext';

// Helper to get auth headers
const getAuthHeaders = () => {
  const token = localStorage.getItem('auth_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
};

const roleLabels = {
  owner: 'Owner',
  editor: 'Editor',
  viewer: 'Viewer',
};

const roleColors = {
  owner: 'error',
  editor: 'primary',
  viewer: 'default',
};

const roleDescriptions = {
  owner: 'Full project control, can delete and manage members',
  editor: 'Can modify test cases and run tests',
  viewer: 'Read-only access to project',
};

export default function ProjectMembers({ projectId, organizationId }) {
  const { canManageProjectMembers, isOrgAdmin } = useOrganization();
  const [members, setMembers] = useState([]);
  const [orgMembers, setOrgMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Dialog states
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [selectedMember, setSelectedMember] = useState(null);
  const [selectedUserId, setSelectedUserId] = useState('');
  const [selectedRole, setSelectedRole] = useState('viewer');

  const canManage = canManageProjectMembers(projectId);

  useEffect(() => {
    loadMembers();
    if (canManage) {
      loadOrgMembers();
    }
  }, [projectId, organizationId, canManage]);

  const loadMembers = async () => {
    try {
      const response = await axios.get(
        `/api/organizations/${organizationId}/projects/${projectId}/members`,
        { headers: getAuthHeaders() }
      );
      setMembers(response.data || []);
    } catch (err) {
      console.error('Failed to load project members:', err);
      setError('Failed to load project members');
    } finally {
      setLoading(false);
    }
  };

  const loadOrgMembers = async () => {
    try {
      const response = await axios.get(
        `/api/organizations/${organizationId}/members`,
        { headers: getAuthHeaders() }
      );
      setOrgMembers(response.data || []);
    } catch (err) {
      console.error('Failed to load org members:', err);
    }
  };

  const handleAddMember = async () => {
    if (!selectedUserId) return;

    try {
      await axios.post(
        `/api/organizations/${organizationId}/projects/${projectId}/members`,
        { user_id: selectedUserId, project_role: selectedRole },
        { headers: getAuthHeaders() }
      );
      setAddDialogOpen(false);
      setSelectedUserId('');
      setSelectedRole('viewer');
      loadMembers();
    } catch (err) {
      console.error('Failed to add member:', err);
      setError(err.response?.data?.detail || 'Failed to add member');
    }
  };

  const handleUpdateRole = async () => {
    if (!selectedMember) return;

    try {
      await axios.put(
        `/api/organizations/${organizationId}/projects/${projectId}/members/${selectedMember.user_id}`,
        { project_role: selectedRole },
        { headers: getAuthHeaders() }
      );
      setEditDialogOpen(false);
      setSelectedMember(null);
      loadMembers();
    } catch (err) {
      console.error('Failed to update role:', err);
      setError(err.response?.data?.detail || 'Failed to update role');
    }
  };

  const handleRemoveMember = async (userId) => {
    if (!confirm('Are you sure you want to remove this member from the project?')) return;

    try {
      await axios.delete(
        `/api/organizations/${organizationId}/projects/${projectId}/members/${userId}`,
        { headers: getAuthHeaders() }
      );
      loadMembers();
    } catch (err) {
      console.error('Failed to remove member:', err);
      setError(err.response?.data?.detail || 'Failed to remove member');
    }
  };

  // Filter out users who are already project members
  const availableOrgMembers = orgMembers.filter(
    om => !members.some(m => m.user_id === om.user_id)
  );

  if (loading) {
    return (
      <Paper sx={{ p: 3 }}>
        <Skeleton variant="text" width="40%" height={32} />
        <Skeleton variant="rectangular" height={60} sx={{ mt: 2 }} />
        <Skeleton variant="rectangular" height={60} sx={{ mt: 1 }} />
        <Skeleton variant="rectangular" height={60} sx={{ mt: 1 }} />
      </Paper>
    );
  }

  return (
    <Paper sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6" sx={{ fontWeight: 600 }}>
          Project Members
        </Typography>
        {canManage && (
          <Button
            variant="contained"
            startIcon={<PersonAdd />}
            onClick={() => setAddDialogOpen(true)}
            disabled={availableOrgMembers.length === 0}
            size="small"
          >
            Add Member
          </Button>
        )}
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {members.length === 0 ? (
        <Alert severity="info">
          No members assigned to this project yet.
        </Alert>
      ) : (
        <List>
          {members.map((member, idx) => (
            <Box key={member.id}>
              {idx > 0 && <Divider />}
              <ListItem sx={{ py: 1.5 }}>
                <Avatar
                  sx={{
                    mr: 2,
                    width: 36,
                    height: 36,
                    bgcolor: member.project_role === 'owner'
                      ? 'error.main'
                      : member.project_role === 'editor'
                        ? 'primary.main'
                        : 'grey.500',
                  }}
                >
                  {member.username?.charAt(0).toUpperCase()}
                </Avatar>
                <ListItemText
                  primary={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant="subtitle2">{member.username}</Typography>
                      <Chip
                        label={roleLabels[member.project_role]}
                        size="small"
                        color={roleColors[member.project_role]}
                        sx={{ height: 20, fontSize: '0.7rem' }}
                      />
                    </Box>
                  }
                  secondary={member.email}
                />
                {canManage && (
                  <ListItemSecondaryAction>
                    <Tooltip title="Change Role">
                      <IconButton
                        size="small"
                        onClick={() => {
                          setSelectedMember(member);
                          setSelectedRole(member.project_role);
                          setEditDialogOpen(true);
                        }}
                      >
                        <Edit fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Remove from Project">
                      <IconButton
                        size="small"
                        color="error"
                        onClick={() => handleRemoveMember(member.user_id)}
                      >
                        <Delete fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </ListItemSecondaryAction>
                )}
              </ListItem>
            </Box>
          ))}
        </List>
      )}

      {/* Add Member Dialog */}
      <Dialog open={addDialogOpen} onClose={() => setAddDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Add Project Member</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <FormControl fullWidth>
              <InputLabel>Select User</InputLabel>
              <Select
                value={selectedUserId}
                label="Select User"
                onChange={(e) => setSelectedUserId(e.target.value)}
              >
                {availableOrgMembers.map((om) => (
                  <MenuItem key={om.user_id} value={om.user_id}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Avatar sx={{ width: 24, height: 24, fontSize: '0.75rem' }}>
                        {om.username?.charAt(0).toUpperCase()}
                      </Avatar>
                      <span>{om.username}</span>
                      <Chip size="small" label={om.org_role} sx={{ height: 18, fontSize: '0.65rem' }} />
                    </Box>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <FormControl fullWidth>
              <InputLabel>Role</InputLabel>
              <Select
                value={selectedRole}
                label="Role"
                onChange={(e) => setSelectedRole(e.target.value)}
              >
                {Object.entries(roleLabels).map(([value, label]) => (
                  <MenuItem key={value} value={value}>
                    <Box>
                      <Typography variant="body2">{label}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {roleDescriptions[value]}
                      </Typography>
                    </Box>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAddDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleAddMember} disabled={!selectedUserId}>
            Add Member
          </Button>
        </DialogActions>
      </Dialog>

      {/* Edit Role Dialog */}
      <Dialog open={editDialogOpen} onClose={() => setEditDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Change Member Role</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2 }}>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Changing role for: <strong>{selectedMember?.username}</strong>
            </Typography>
            <FormControl fullWidth>
              <InputLabel>Role</InputLabel>
              <Select
                value={selectedRole}
                label="Role"
                onChange={(e) => setSelectedRole(e.target.value)}
              >
                {Object.entries(roleLabels).map(([value, label]) => (
                  <MenuItem key={value} value={value}>
                    <Box>
                      <Typography variant="body2">{label}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {roleDescriptions[value]}
                      </Typography>
                    </Box>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleUpdateRole}>
            Update Role
          </Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
}
