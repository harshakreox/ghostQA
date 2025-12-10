import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Button,
  Grid,
  Card,
  CardContent,
  Typography,
  Chip,
  LinearProgress,
  Paper,
  Breadcrumbs,
  Link,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  IconButton,
  List,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  Tabs,
  Tab,
  Snackbar,
} from '@mui/material';
import {
  NavigateNext,
  Save,
  Add,
  Delete,
  CloudQueue,
  Code,
} from '@mui/icons-material';
import axios from 'axios';

// Import generic components and hooks
import { EmptyState, ConfirmDialog } from '../components';
import { useNotification } from '../hooks';

function TabPanel({ children, value, index }) {
  return (
    <div hidden={value !== index}>
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
}

export default function ReleaseEdit() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [release, setRelease] = useState(null);
  const [loading, setLoading] = useState(true);
  const [tabValue, setTabValue] = useState(0);

  // Use notification hook
  const { notification, showNotification, hideNotification } = useNotification();

  // Release details form
  const [releaseForm, setReleaseForm] = useState({
    name: '',
    version: '',
    description: '',
    status: 'draft',
    target_date: '',
  });

  // Environment dialog
  const [envDialogOpen, setEnvDialogOpen] = useState(false);
  const [envForm, setEnvForm] = useState({
    name: '',
    type: 'development',
    base_url: '',
    description: '',
  });

  // Project dialog
  const [projectDialogOpen, setProjectDialogOpen] = useState(false);
  const [availableProjects, setAvailableProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState('');

  // Delete confirmation dialog
  const [deleteDialog, setDeleteDialog] = useState({ open: false, type: '', item: null });

  useEffect(() => {
    loadData();
  }, [id]);

  const loadData = async () => {
    try {
      const [releaseRes, projectsRes] = await Promise.all([
        axios.get(`/api/releases/${id}`),
        axios.get('/api/projects'),
      ]);

      const releaseData = releaseRes.data;
      setRelease(releaseData);
      setReleaseForm({
        name: releaseData.name,
        version: releaseData.version,
        description: releaseData.description || '',
        status: releaseData.status,
        target_date: releaseData.target_date || '',
      });
      setAvailableProjects(projectsRes.data);
    } catch (error) {
      console.error('Error loading data:', error);
      showNotification('Failed to load release data', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveRelease = async () => {
    try {
      await axios.put(`/api/releases/${id}`, releaseForm);
      showNotification('Release updated successfully!', 'success');
      setTimeout(() => navigate(`/releases/${id}`), 1500);
    } catch (error) {
      console.error('Error updating release:', error);
      showNotification('Failed to update release', 'error');
    }
  };

  const handleAddEnvironment = async () => {
    try {
      await axios.post(`/api/releases/${id}/environments`, envForm);
      setEnvDialogOpen(false);
      setEnvForm({ name: '', type: 'development', base_url: '', description: '' });
      showNotification('Environment added successfully', 'success');
      loadData();
    } catch (error) {
      console.error('Error adding environment:', error);
      showNotification('Failed to add environment', 'error');
    }
  };

  const handleDeleteEnvironment = async () => {
    if (!deleteDialog.item) return;

    try {
      await axios.delete(`/api/releases/${id}/environments/${deleteDialog.item.id}`);
      showNotification('Environment deleted successfully', 'success');
      setDeleteDialog({ open: false, type: '', item: null });
      loadData();
    } catch (error) {
      console.error('Error deleting environment:', error);
      showNotification('Failed to delete environment', 'error');
    }
  };

  const handleAddProject = async () => {
    if (!selectedProject) return;

    try {
      await axios.post(`/api/releases/${id}/projects`, {
        project_id: selectedProject,
        test_case_ids: [],
      });
      setProjectDialogOpen(false);
      setSelectedProject('');
      showNotification('Project added successfully', 'success');
      loadData();
    } catch (error) {
      console.error('Error adding project:', error);
      showNotification('Failed to add project', 'error');
    }
  };

  const handleDeleteProject = async () => {
    if (!deleteDialog.item) return;

    try {
      await axios.delete(`/api/releases/${id}/projects/${deleteDialog.item.project_id}`);
      showNotification('Project removed successfully', 'success');
      setDeleteDialog({ open: false, type: '', item: null });
      loadData();
    } catch (error) {
      console.error('Error deleting project:', error);
      showNotification('Failed to remove project', 'error');
    }
  };

  const handleDeleteConfirm = () => {
    if (deleteDialog.type === 'environment') {
      handleDeleteEnvironment();
    } else if (deleteDialog.type === 'project') {
      handleDeleteProject();
    }
  };

  if (loading) {
    return <LinearProgress />;
  }

  if (!release) {
    return (
      <Box sx={{ textAlign: 'center', py: 8 }}>
        <Typography variant="h6">Release not found</Typography>
      </Box>
    );
  }

  return (
    <Box>
      {/* Breadcrumbs */}
      <Breadcrumbs separator={<NavigateNext fontSize="small" />} sx={{ mb: 3 }}>
        <Link component="button" variant="body2" onClick={() => navigate('/releases')}>
          Releases
        </Link>
        <Link component="button" variant="body2" onClick={() => navigate(`/releases/${id}`)}>
          {release.name}
        </Link>
        <Typography color="text.primary">Edit</Typography>
      </Breadcrumbs>

      {/* Header */}
      <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h4" sx={{ fontWeight: 700 }}>
          Edit Release
        </Typography>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button variant="outlined" onClick={() => navigate(`/releases/${id}`)}>
            Cancel
          </Button>
          <Button variant="contained" startIcon={<Save />} onClick={handleSaveRelease}>
            Save Changes
          </Button>
        </Box>
      </Box>

      {/* Tabs */}
      <Paper sx={{ mb: 3 }}>
        <Tabs value={tabValue} onChange={(e, newValue) => setTabValue(newValue)}>
          <Tab label="Release Details" />
          <Tab label="Environments" />
          <Tab label="Projects" />
        </Tabs>
      </Paper>

      {/* Tab 1: Release Details */}
      <TabPanel value={tabValue} index={0}>
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
            Basic Information
          </Typography>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <TextField
                label="Release Name"
                value={releaseForm.name}
                onChange={(e) => setReleaseForm({ ...releaseForm, name: e.target.value })}
                fullWidth
                required
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                label="Version"
                value={releaseForm.version}
                onChange={(e) => setReleaseForm({ ...releaseForm, version: e.target.value })}
                fullWidth
                required
                helperText="Semantic versioning (e.g., 2.1.0)"
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                label="Description"
                value={releaseForm.description}
                onChange={(e) => setReleaseForm({ ...releaseForm, description: e.target.value })}
                fullWidth
                multiline
                rows={4}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>Status</InputLabel>
                <Select
                  value={releaseForm.status}
                  label="Status"
                  onChange={(e) => setReleaseForm({ ...releaseForm, status: e.target.value })}
                >
                  <MenuItem value="draft">Draft</MenuItem>
                  <MenuItem value="in_progress">In Progress</MenuItem>
                  <MenuItem value="testing">Testing</MenuItem>
                  <MenuItem value="ready">Ready</MenuItem>
                  <MenuItem value="deployed">Deployed</MenuItem>
                  <MenuItem value="failed">Failed</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                label="Target Date"
                type="date"
                value={releaseForm.target_date}
                onChange={(e) => setReleaseForm({ ...releaseForm, target_date: e.target.value })}
                fullWidth
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
          </Grid>
        </Paper>
      </TabPanel>

      {/* Tab 2: Environments */}
      <TabPanel value={tabValue} index={1}>
        <Paper sx={{ p: 3 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              Environments
            </Typography>
            <Button variant="contained" startIcon={<Add />} onClick={() => setEnvDialogOpen(true)}>
              Add Environment
            </Button>
          </Box>

          {release.environments?.length === 0 ? (
            <EmptyState
              icon={CloudQueue}
              title="No Environments Configured"
              description="Add environments to define where tests will run"
              actionLabel="Add Environment"
              actionIcon={<Add />}
              onAction={() => setEnvDialogOpen(true)}
              size="medium"
            />
          ) : (
            <List>
              {release.environments?.map((env) => (
                <Card key={env.id} sx={{ mb: 2 }}>
                  <CardContent>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <Box sx={{ flex: 1 }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                          <CloudQueue color="primary" />
                          <Typography variant="h6" sx={{ fontWeight: 600 }}>
                            {env.name}
                          </Typography>
                          <Chip
                            label={env.type}
                            size="small"
                            color={
                              env.type === 'production'
                                ? 'error'
                                : env.type === 'staging'
                                ? 'warning'
                                : env.type === 'development'
                                ? 'info'
                                : 'default'
                            }
                            sx={{ textTransform: 'capitalize' }}
                          />
                        </Box>
                        <Typography variant="body2" color="text.secondary" sx={{ fontFamily: 'monospace', mb: 1 }}>
                          {env.base_url}
                        </Typography>
                        {env.description && (
                          <Typography variant="body2" color="text.secondary">
                            {env.description}
                          </Typography>
                        )}
                      </Box>
                      <IconButton
                        color="error"
                        onClick={() => setDeleteDialog({ open: true, type: 'environment', item: env })}
                      >
                        <Delete />
                      </IconButton>
                    </Box>
                  </CardContent>
                </Card>
              ))}
            </List>
          )}
        </Paper>
      </TabPanel>

      {/* Tab 3: Projects */}
      <TabPanel value={tabValue} index={2}>
        <Paper sx={{ p: 3 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              Projects in Release
            </Typography>
            <Button variant="contained" startIcon={<Add />} onClick={() => setProjectDialogOpen(true)}>
              Add Project
            </Button>
          </Box>

          {release.projects?.length === 0 ? (
            <EmptyState
              icon={Code}
              title="No Projects Added"
              description="Add projects to define what will be tested in this release"
              actionLabel="Add Project"
              actionIcon={<Add />}
              onAction={() => setProjectDialogOpen(true)}
              size="medium"
            />
          ) : (
            <List>
              {release.projects?.map((project) => (
                <Card key={project.project_id} sx={{ mb: 2 }}>
                  <CardContent>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Box sx={{ flex: 1 }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                          <Code color="success" />
                          <Typography variant="h6" sx={{ fontWeight: 600 }}>
                            {project.project_name}
                          </Typography>
                          <Chip
                            label={`${project.test_case_ids?.length || 0} test cases`}
                            size="small"
                            color="primary"
                          />
                        </Box>
                      </Box>
                      <IconButton
                        color="error"
                        onClick={() => setDeleteDialog({ open: true, type: 'project', item: project })}
                      >
                        <Delete />
                      </IconButton>
                    </Box>
                  </CardContent>
                </Card>
              ))}
            </List>
          )}
        </Paper>
      </TabPanel>

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={deleteDialog.open}
        onClose={() => setDeleteDialog({ open: false, type: '', item: null })}
        onConfirm={handleDeleteConfirm}
        title={deleteDialog.type === 'environment' ? 'Delete Environment?' : 'Remove Project?'}
        message={`Are you sure you want to ${deleteDialog.type === 'environment' ? 'delete' : 'remove'} "${
          deleteDialog.item?.name || deleteDialog.item?.project_name
        }"? This action cannot be undone.`}
        confirmLabel={deleteDialog.type === 'environment' ? 'Delete' : 'Remove'}
        type="delete"
      />

      {/* Add Environment Dialog */}
      <Dialog open={envDialogOpen} onClose={() => setEnvDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontWeight: 600 }}>Add Environment</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 2 }}>
            <TextField
              label="Environment Name"
              value={envForm.name}
              onChange={(e) => setEnvForm({ ...envForm, name: e.target.value })}
              fullWidth
              required
              placeholder="Development, Staging, Production"
            />
            <FormControl fullWidth required>
              <InputLabel>Environment Type</InputLabel>
              <Select
                value={envForm.type}
                label="Environment Type"
                onChange={(e) => setEnvForm({ ...envForm, type: e.target.value })}
              >
                <MenuItem value="development">Development</MenuItem>
                <MenuItem value="qa">QA</MenuItem>
                <MenuItem value="uat">UAT</MenuItem>
                <MenuItem value="staging">Staging</MenuItem>
                <MenuItem value="production">Production</MenuItem>
              </Select>
            </FormControl>
            <TextField
              label="Base URL"
              value={envForm.base_url}
              onChange={(e) => setEnvForm({ ...envForm, base_url: e.target.value })}
              fullWidth
              required
              placeholder="https://dev.example.com"
              helperText="The base URL where tests will run"
            />
            <TextField
              label="Description"
              value={envForm.description}
              onChange={(e) => setEnvForm({ ...envForm, description: e.target.value })}
              fullWidth
              multiline
              rows={2}
            />
          </Box>
        </DialogContent>
        <DialogActions sx={{ p: 3 }}>
          <Button onClick={() => setEnvDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleAddEnvironment} disabled={!envForm.name || !envForm.base_url}>
            Add Environment
          </Button>
        </DialogActions>
      </Dialog>

      {/* Add Project Dialog */}
      <Dialog open={projectDialogOpen} onClose={() => setProjectDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontWeight: 600 }}>Add Project to Release</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2 }}>
            <FormControl fullWidth required>
              <InputLabel>Select Project</InputLabel>
              <Select value={selectedProject} label="Select Project" onChange={(e) => setSelectedProject(e.target.value)}>
                {availableProjects
                  .filter((p) => !release.projects?.find((rp) => rp.project_id === p.id))
                  .map((project) => (
                    <MenuItem key={project.id} value={project.id}>
                      {project.name} ({project.test_cases?.length || 0} test cases)
                    </MenuItem>
                  ))}
              </Select>
            </FormControl>
            <Alert severity="info" sx={{ mt: 2 }}>
              All test cases from the selected project will be included in this release.
            </Alert>
          </Box>
        </DialogContent>
        <DialogActions sx={{ p: 3 }}>
          <Button onClick={() => setProjectDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleAddProject} disabled={!selectedProject}>
            Add Project
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar */}
      <Snackbar
        open={notification.open}
        autoHideDuration={4000}
        onClose={hideNotification}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert onClose={hideNotification} severity={notification.severity} variant="filled">
          {notification.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}
