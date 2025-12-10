import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Chip,
  LinearProgress,
  IconButton,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
} from '@mui/material';
import {
  Add,
  Refresh,
  MoreVert,
  Visibility,
  Edit,
  Delete,
  Rocket,
  CheckCircle,
  Schedule,
} from '@mui/icons-material';
import axios from 'axios';
import { format } from 'date-fns';

// Import generic components and hooks
import { PageHeader, EmptyState, ConfirmDialog, SearchBar } from '../components';
import { useApiData, useContextMenu } from '../hooks';

const STATUS_COLORS = {
  draft: 'default',
  in_progress: 'info',
  testing: 'warning',
  ready: 'success',
  deployed: 'success',
  failed: 'error',
};

const STATUS_LABELS = {
  draft: 'Draft',
  in_progress: 'In Progress',
  testing: 'Testing',
  ready: 'Ready',
  deployed: 'Deployed',
  failed: 'Failed',
};

export default function Releases() {
  const navigate = useNavigate();

  // Use custom hooks
  const { data: releases = [], loading, refetch } = useApiData('/api/releases', {
    initialData: [],
    transform: (data) => data.sort((a, b) => new Date(b.created_at) - new Date(a.created_at)),
  });
  const { anchorEl, selectedItem: selectedRelease, isOpen, openMenu, closeMenu } = useContextMenu();

  // Search state
  const [searchQuery, setSearchQuery] = useState('');

  // Dialog states
  const [openDialog, setOpenDialog] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    version: '',
    description: '',
    target_date: '',
  });

  const handleCreateRelease = async () => {
    try {
      await axios.post('/api/releases', formData);
      setOpenDialog(false);
      setFormData({ name: '', version: '', description: '', target_date: '' });
      refetch();
    } catch (error) {
      console.error('Error creating release:', error);
    }
  };

  const handleDeleteClick = () => {
    closeMenu();
    setDeleteDialogOpen(true);
  };

  const handleDeleteRelease = async () => {
    if (!selectedRelease?.id) return;

    try {
      await axios.delete(`/api/releases/${selectedRelease.id}`);
      refetch();
      setDeleteDialogOpen(false);
    } catch (error) {
      console.error('Error deleting release:', error);
    }
  };

  if (loading) {
    return <LinearProgress />;
  }

  // Filter releases based on search
  const filteredReleases = releases.filter(release =>
    release.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    release.version?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    release.description?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <Box>
      {/* Page Header - Using generic component */}
      <PageHeader
        title="Releases"
        subtitle="Manage release versions, environments, and deployment testing"
        actions={[
          {
            label: 'Refresh',
            icon: <Refresh />,
            onClick: refetch,
            variant: 'outlined',
          },
          {
            label: 'New Release',
            icon: <Add />,
            onClick: () => setOpenDialog(true),
            variant: 'contained',
            gradient: true,
          },
        ]}
      />

      {/* Search Bar */}
      {releases.length > 0 && (
        <Box sx={{ mb: 3, maxWidth: 400 }}>
          <SearchBar
            placeholder="Search releases..."
            value={searchQuery}
            onSearch={setSearchQuery}
          />
        </Box>
      )}

      {/* Empty State - Using generic component */}
      {filteredReleases.length === 0 && searchQuery ? (
        <Card sx={{ p: 4, textAlign: 'center' }}>
          <Typography variant="h6" color="text.secondary">
            No releases found matching "{searchQuery}"
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            Try a different search term
          </Typography>
        </Card>
      ) : releases.length === 0 ? (
        <Card sx={{ p: 4 }}>
          <EmptyState
            icon={Rocket}
            title="No Releases Yet"
            description="Create your first release to track testing across environments"
            actionLabel="Create Release"
            actionIcon={<Add />}
            onAction={() => setOpenDialog(true)}
            size="large"
          />
        </Card>
      ) : (
        <Grid container spacing={3}>
          {filteredReleases.map((release) => (
            <Grid item xs={12} md={6} lg={4} key={release.id}>
              <Card
                sx={{
                  height: '100%',
                  cursor: 'pointer',
                  '&:hover': {
                    boxShadow: 6,
                    transform: 'translateY(-4px)',
                  },
                  transition: 'all 0.2s',
                }}
                onClick={() => navigate(`/releases/${release.id}`)}
              >
                <CardContent>
                  {/* Header */}
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                    <Box sx={{ flex: 1 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                        <Rocket sx={{ color: 'primary.main' }} />
                        <Typography variant="h6" sx={{ fontWeight: 600 }}>
                          {release.name}
                        </Typography>
                      </Box>
                      <Chip
                        label={`v${release.version}`}
                        size="small"
                        sx={{ fontWeight: 600, fontFamily: 'monospace' }}
                      />
                    </Box>
                    <IconButton
                      size="small"
                      onClick={(e) => {
                        e.stopPropagation();
                        openMenu(e, release);
                      }}
                    >
                      <MoreVert />
                    </IconButton>
                  </Box>

                  {/* Description */}
                  {release.description && (
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                      {release.description}
                    </Typography>
                  )}

                  {/* Status */}
                  <Box sx={{ mb: 2 }}>
                    <Chip
                      label={STATUS_LABELS[release.status]}
                      color={STATUS_COLORS[release.status]}
                      size="small"
                      sx={{ fontWeight: 600 }}
                    />
                    {release.deployment_ready && (
                      <Chip
                        icon={<CheckCircle />}
                        label="Ready to Deploy"
                        color="success"
                        size="small"
                        sx={{ ml: 1, fontWeight: 600 }}
                      />
                    )}
                  </Box>

                  {/* Stats */}
                  <Grid container spacing={2} sx={{ mb: 2 }}>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">
                        Environments
                      </Typography>
                      <Typography variant="h6" sx={{ fontWeight: 700 }}>
                        {release.environments?.length || 0}
                      </Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">
                        Projects
                      </Typography>
                      <Typography variant="h6" sx={{ fontWeight: 700 }}>
                        {release.projects?.length || 0}
                      </Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">
                        Iterations
                      </Typography>
                      <Typography variant="h6" sx={{ fontWeight: 700 }}>
                        {release.total_iterations || 0}
                      </Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">
                        Pass Rate
                      </Typography>
                      <Typography
                        variant="h6"
                        sx={{
                          fontWeight: 700,
                          color:
                            (release.overall_pass_rate || 0) >= 95
                              ? 'success.main'
                              : (release.overall_pass_rate || 0) >= 70
                              ? 'warning.main'
                              : 'error.main',
                        }}
                      >
                        {(release.overall_pass_rate || 0).toFixed(0)}%
                      </Typography>
                    </Grid>
                  </Grid>

                  {/* Pass Rate Progress */}
                  {release.iterations?.length > 0 && (
                    <Box sx={{ mb: 2 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                        <Typography variant="caption" color="text.secondary">
                          Overall Progress
                        </Typography>
                        <Typography variant="caption" sx={{ fontWeight: 600 }}>
                          {(release.overall_pass_rate || 0).toFixed(1)}%
                        </Typography>
                      </Box>
                      <LinearProgress
                        variant="determinate"
                        value={release.overall_pass_rate || 0}
                        color={
                          (release.overall_pass_rate || 0) >= 95
                            ? 'success'
                            : (release.overall_pass_rate || 0) >= 70
                            ? 'warning'
                            : 'error'
                        }
                        sx={{ height: 8, borderRadius: 1 }}
                      />
                    </Box>
                  )}

                  {/* Target Date */}
                  {release.target_date && (
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 2 }}>
                      <Schedule fontSize="small" sx={{ color: 'text.secondary' }} />
                      <Typography variant="caption" color="text.secondary">
                        Target: {format(new Date(release.target_date), 'MMM dd, yyyy')}
                      </Typography>
                    </Box>
                  )}
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      {/* Release Menu */}
      <Menu anchorEl={anchorEl} open={isOpen} onClose={closeMenu}>
        <MenuItem
          onClick={() => {
            navigate(`/releases/${selectedRelease?.id}`);
            closeMenu();
          }}
        >
          <ListItemIcon>
            <Visibility fontSize="small" />
          </ListItemIcon>
          <ListItemText>View Dashboard</ListItemText>
        </MenuItem>
        <MenuItem
          onClick={() => {
            navigate(`/releases/${selectedRelease?.id}/edit`);
            closeMenu();
          }}
        >
          <ListItemIcon>
            <Edit fontSize="small" />
          </ListItemIcon>
          <ListItemText>Edit Release</ListItemText>
        </MenuItem>
        <MenuItem onClick={handleDeleteClick}>
          <ListItemIcon>
            <Delete fontSize="small" color="error" />
          </ListItemIcon>
          <ListItemText sx={{ color: 'error.main' }}>Delete Release</ListItemText>
        </MenuItem>
      </Menu>

      {/* Delete Confirmation Dialog - Using generic component */}
      <ConfirmDialog
        open={deleteDialogOpen}
        onClose={() => setDeleteDialogOpen(false)}
        onConfirm={handleDeleteRelease}
        title="Delete Release?"
        message={`Are you sure you want to delete "${selectedRelease?.name}"? This action cannot be undone.`}
        confirmLabel="Delete"
        type="delete"
      />

      {/* Create Release Dialog */}
      <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontWeight: 600 }}>Create New Release</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 2 }}>
            <TextField
              label="Release Name"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              fullWidth
              required
              placeholder="Sprint 42, Q4 Release, etc."
            />
            <TextField
              label="Version"
              value={formData.version}
              onChange={(e) => setFormData({ ...formData, version: e.target.value })}
              fullWidth
              required
              placeholder="2.1.0"
              helperText="Semantic versioning (e.g., 2.1.0)"
            />
            <TextField
              label="Description"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              fullWidth
              multiline
              rows={3}
              placeholder="What's included in this release..."
            />
            <TextField
              label="Target Date"
              type="date"
              value={formData.target_date}
              onChange={(e) => setFormData({ ...formData, target_date: e.target.value })}
              fullWidth
              InputLabelProps={{ shrink: true }}
              helperText="Optional deployment target date"
            />
          </Box>
        </DialogContent>
        <DialogActions sx={{ p: 3 }}>
          <Button onClick={() => setOpenDialog(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleCreateRelease} disabled={!formData.name || !formData.version}>
            Create Release
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
