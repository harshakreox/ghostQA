import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Button,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Chip,
  LinearProgress,
  Paper,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  InputAdornment,
  Alert,
  FormGroup,
  FormControlLabel,
  Checkbox,
  FormControl,
  InputLabel,
  Select,
} from '@mui/material';
import {
  Add,
  MoreVert,
  Edit,
  Delete,
  PlayArrow,
  FolderOpen,
  Code,
  ExpandMore,
  Key,
  Visibility,
  VisibilityOff,
  Widgets,
} from '@mui/icons-material';
import axios from 'axios';

// Import generic components and hooks
import { PageHeader, EmptyState, ConfirmDialog, SearchBar } from '../components';
import { useApiData, useContextMenu } from '../hooks';
import { useAuth } from '../context/AuthContext';

// Helper to get auth headers
const getAuthHeaders = () => {
  const token = localStorage.getItem('auth_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
};

export default function Projects() {
  const navigate = useNavigate();
  const { isAdmin } = useAuth();

  // Use custom hooks
  const { data: projects = [], loading, refetch } = useApiData('/api/projects', { initialData: [] });
  const { anchorEl, selectedItem: selectedProject, isOpen, openMenu, closeMenu } = useContextMenu();

  // Search state
  const [searchQuery, setSearchQuery] = useState('');

  // Dialog states
  const [openDialog, setOpenDialog] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [projectToDelete, setProjectToDelete] = useState(null);

  // Available UI frameworks
  const [availableFrameworks, setAvailableFrameworks] = useState([]);

  // Form states
  const [showPassword, setShowPassword] = useState(false);
  const [showAdminPassword, setShowAdminPassword] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    base_url: '',
    test_username: '',
    test_password: '',
    test_admin_username: '',
    test_admin_password: '',
    ui_config: {
      frameworks: [],
      primary_framework: null,
      testing_library: 'playwright',
    },
  });

  // Fetch available frameworks
  useEffect(() => {
    const fetchFrameworks = async () => {
      try {
        const response = await axios.get('/api/frameworks');
        setAvailableFrameworks(response.data.frameworks || []);
      } catch (error) {
        console.error('Error fetching frameworks:', error);
      }
    };
    fetchFrameworks();
  }, []);

  // Handle framework checkbox toggle
  const handleFrameworkToggle = (frameworkId) => {
    const currentFrameworks = formData.ui_config.frameworks;
    let newFrameworks;

    if (currentFrameworks.includes(frameworkId)) {
      // Remove framework
      newFrameworks = currentFrameworks.filter((f) => f !== frameworkId);
      // If removed framework was primary, reset primary
      const newPrimary =
        formData.ui_config.primary_framework === frameworkId ? null : formData.ui_config.primary_framework;
      setFormData({
        ...formData,
        ui_config: {
          ...formData.ui_config,
          frameworks: newFrameworks,
          primary_framework: newPrimary,
        },
      });
    } else {
      // Add framework
      newFrameworks = [...currentFrameworks, frameworkId];
      // If this is the first framework, set it as primary
      const newPrimary = newFrameworks.length === 1 ? frameworkId : formData.ui_config.primary_framework;
      setFormData({
        ...formData,
        ui_config: {
          ...formData.ui_config,
          frameworks: newFrameworks,
          primary_framework: newPrimary,
        },
      });
    }
  };

  // Handle primary framework change
  const handlePrimaryFrameworkChange = (event) => {
    setFormData({
      ...formData,
      ui_config: {
        ...formData.ui_config,
        primary_framework: event.target.value,
      },
    });
  };

  const handleCreateProject = async () => {
    try {
      await axios.post('/api/projects', formData, {
        headers: getAuthHeaders()
      });
      setOpenDialog(false);
      setFormData({
        name: '',
        description: '',
        base_url: '',
        test_username: '',
        test_password: '',
        test_admin_username: '',
        test_admin_password: '',
        ui_config: {
          frameworks: [],
          primary_framework: null,
          testing_library: 'playwright',
        },
      });
      refetch();
    } catch (error) {
      console.error('Error creating project:', error);
    }
  };

  const handleDeleteClick = () => {
    setProjectToDelete(selectedProject);
    closeMenu();
    setDeleteDialogOpen(true);
  };

  const handleDeleteProject = async () => {
    if (!projectToDelete?.id) return;

    setDeleteLoading(true);
    try {
      await axios.delete(`/api/projects/${projectToDelete.id}`, {
        headers: getAuthHeaders()
      });
      refetch();
      setDeleteDialogOpen(false);
      setProjectToDelete(null);
    } catch (error) {
      console.error('Error deleting project:', error);
      alert(error.response?.data?.detail || 'Failed to delete project');
    } finally {
      setDeleteLoading(false);
    }
  };

  if (loading) {
    return <LinearProgress />;
  }

  // Filter projects based on search
  const filteredProjects = projects.filter(project =>
    project.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    project.description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    project.base_url?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <Box>
      {/* Page Header - Using generic component */}
      <PageHeader
        title="Projects"
        subtitle="Manage your test automation projects"
        actions={[
          {
            label: 'New Project',
            icon: <Add />,
            onClick: () => setOpenDialog(true),
            variant: 'contained',
            gradient: true,
          },
        ]}
      />

      {/* Search Bar */}
      {projects.length > 0 && (
        <Box sx={{ mb: 3, maxWidth: 400 }}>
          <SearchBar
            placeholder="Search projects..."
            value={searchQuery}
            onSearch={setSearchQuery}
          />
        </Box>
      )}

      {filteredProjects.length === 0 && searchQuery ? (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography variant="h6" color="text.secondary">
            No projects found matching "{searchQuery}"
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            Try a different search term
          </Typography>
        </Paper>
      ) : projects.length === 0 ? (
        <Paper sx={{ p: 4 }}>
          <EmptyState
            icon={FolderOpen}
            title="No Projects Yet"
            description="Create your first project to start automating tests"
            actionLabel="Create Project"
            actionIcon={<Add />}
            onAction={() => setOpenDialog(true)}
            size="large"
          />
        </Paper>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell sx={{ fontWeight: 600 }}>Project Name</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Description</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Base URL</TableCell>
                <TableCell sx={{ fontWeight: 600 }} align="center">
                  Test Cases
                </TableCell>
                <TableCell sx={{ fontWeight: 600 }} align="center">
                  Status
                </TableCell>
                <TableCell sx={{ fontWeight: 600 }} align="right">
                  Actions
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredProjects.map((project) => (
                <TableRow
                  key={project.id}
                  sx={{
                    '&:hover': {
                      backgroundColor: 'action.hover',
                      cursor: 'pointer',
                    },
                  }}
                  onClick={() => navigate(`/projects/${project.id}`)}
                >
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                      <Box
                        sx={{
                          width: 40,
                          height: 40,
                          borderRadius: 2,
                          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          color: 'white',
                        }}
                      >
                        <Code />
                      </Box>
                      <Typography variant="body1" sx={{ fontWeight: 600 }}>
                        {project.name}
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" color="text.secondary">
                      {project.description}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" color="text.secondary" sx={{ fontFamily: 'monospace' }}>
                      {project.base_url || 'Not set'}
                    </Typography>
                  </TableCell>
                  <TableCell align="center">
                    <Chip
                      label={project.test_cases?.length || 0}
                      size="small"
                      color="primary"
                      sx={{ fontWeight: 600 }}
                    />
                  </TableCell>
                  <TableCell align="center">
                    <Chip label="Active" size="small" color="success" sx={{ fontWeight: 600 }} />
                  </TableCell>
                  <TableCell align="right" onClick={(e) => e.stopPropagation()}>
                    <IconButton onClick={(e) => openMenu(e, project)}>
                      <MoreVert />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Project Menu */}
      <Menu anchorEl={anchorEl} open={isOpen} onClose={closeMenu}>
        <MenuItem
          onClick={() => {
            navigate(`/projects/${selectedProject?.id}`);
            closeMenu();
          }}
        >
          <ListItemIcon>
            <FolderOpen fontSize="small" />
          </ListItemIcon>
          <ListItemText>Open Project</ListItemText>
        </MenuItem>
        {isAdmin && (
          <MenuItem
            onClick={() => {
              navigate(`/projects/${selectedProject?.id}/run`);
              closeMenu();
            }}
          >
            <ListItemIcon>
              <PlayArrow fontSize="small" />
            </ListItemIcon>
            <ListItemText>Run Tests</ListItemText>
          </MenuItem>
        )}
        <MenuItem
          onClick={() => {
            navigate(`/projects/${selectedProject?.id}/edit`);
            closeMenu();
          }}
        >
          <ListItemIcon>
            <Edit fontSize="small" />
          </ListItemIcon>
          <ListItemText>Edit</ListItemText>
        </MenuItem>
        <MenuItem onClick={handleDeleteClick}>
          <ListItemIcon>
            <Delete fontSize="small" color="error" />
          </ListItemIcon>
          <ListItemText sx={{ color: 'error.main' }}>Delete</ListItemText>
        </MenuItem>
      </Menu>

      {/* Delete Confirmation Dialog - Using generic component */}
      <ConfirmDialog
        open={deleteDialogOpen}
        onClose={() => {
          setDeleteDialogOpen(false);
          setProjectToDelete(null);
        }}
        onConfirm={handleDeleteProject}
        title="Delete Project?"
        message={`Are you sure you want to delete "${projectToDelete?.name}"? This action cannot be undone.`}
        confirmLabel="Delete"
        type="delete"
        loading={deleteLoading}
      />

      {/* Create Project Dialog */}
      <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle sx={{ fontWeight: 600 }}>Create New Project</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 2 }}>
            {/* Basic Settings */}
            <TextField
              label="Project Name"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              fullWidth
              required
            />
            <TextField
              label="Description"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              fullWidth
              multiline
              rows={3}
            />
            <TextField
              label="Base URL"
              value={formData.base_url}
              onChange={(e) => setFormData({ ...formData, base_url: e.target.value })}
              fullWidth
              placeholder="https://example.com"
            />

            {/* Test Credentials */}
            <Accordion
              sx={{
                mt: 2,
                boxShadow: 0,
                border: '1px solid',
                borderColor: 'divider',
                '&:before': { display: 'none' },
              }}
            >
              <AccordionSummary
                expandIcon={<ExpandMore />}
                sx={{
                  bgcolor: 'grey.50',
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Key sx={{ color: '#667eea', fontSize: 20 }} />
                  <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                    Test Credentials (Optional)
                  </Typography>
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                <Alert severity="info" sx={{ mb: 2, fontSize: '0.75rem' }}>
                  Configure credentials for AI-powered automated testing
                </Alert>

                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  {/* Regular User */}
                  <TextField
                    label="Test Username"
                    value={formData.test_username}
                    onChange={(e) => setFormData({ ...formData, test_username: e.target.value })}
                    fullWidth
                    size="small"
                    placeholder="testuser@example.com"
                  />
                  <TextField
                    label="Test Password"
                    type={showPassword ? 'text' : 'password'}
                    value={formData.test_password}
                    onChange={(e) => setFormData({ ...formData, test_password: e.target.value })}
                    fullWidth
                    size="small"
                    placeholder="Enter test password"
                    InputProps={{
                      endAdornment: (
                        <InputAdornment position="end">
                          <IconButton onClick={() => setShowPassword(!showPassword)} edge="end" size="small">
                            {showPassword ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
                          </IconButton>
                        </InputAdornment>
                      ),
                    }}
                  />

                  {/* Admin User */}
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
                    Admin Credentials (Optional)
                  </Typography>
                  <TextField
                    label="Admin Username"
                    value={formData.test_admin_username}
                    onChange={(e) => setFormData({ ...formData, test_admin_username: e.target.value })}
                    fullWidth
                    size="small"
                    placeholder="admin@example.com"
                  />
                  <TextField
                    label="Admin Password"
                    type={showAdminPassword ? 'text' : 'password'}
                    value={formData.test_admin_password}
                    onChange={(e) => setFormData({ ...formData, test_admin_password: e.target.value })}
                    fullWidth
                    size="small"
                    placeholder="Enter admin password"
                    InputProps={{
                      endAdornment: (
                        <InputAdornment position="end">
                          <IconButton onClick={() => setShowAdminPassword(!showAdminPassword)} edge="end" size="small">
                            {showAdminPassword ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
                          </IconButton>
                        </InputAdornment>
                      ),
                    }}
                  />
                </Box>
              </AccordionDetails>
            </Accordion>

            {/* UI Framework Configuration */}
            <Accordion
              sx={{
                boxShadow: 0,
                border: '1px solid',
                borderColor: 'divider',
                '&:before': { display: 'none' },
              }}
            >
              <AccordionSummary
                expandIcon={<ExpandMore />}
                sx={{
                  bgcolor: 'grey.50',
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Widgets sx={{ color: '#667eea', fontSize: 20 }} />
                  <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                    UI Framework Configuration (Optional)
                  </Typography>
                  {formData.ui_config.frameworks.length > 0 && (
                    <Chip
                      label={`${formData.ui_config.frameworks.length} selected`}
                      size="small"
                      color="primary"
                      sx={{ ml: 1 }}
                    />
                  )}
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                <Alert severity="info" sx={{ mb: 2, fontSize: '0.75rem' }}>
                  Select the UI frameworks used in your application. This helps the AI generate more accurate test
                  cases with framework-specific selectors and component knowledge.
                </Alert>

                <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
                  Select frameworks used in your application:
                </Typography>

                <FormGroup sx={{ mb: 2 }}>
                  {availableFrameworks.map((fw) => (
                    <FormControlLabel
                      key={fw.id}
                      control={
                        <Checkbox
                          checked={formData.ui_config.frameworks.includes(fw.id)}
                          onChange={() => handleFrameworkToggle(fw.id)}
                          size="small"
                        />
                      }
                      label={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Typography variant="body2">{fw.name}</Typography>
                          <Chip
                            label={fw.category}
                            size="small"
                            variant="outlined"
                            sx={{ fontSize: '0.65rem', height: 18 }}
                          />
                        </Box>
                      }
                    />
                  ))}
                </FormGroup>

                {/* Primary Framework Selection - only show if multiple frameworks selected */}
                {formData.ui_config.frameworks.length > 1 && (
                  <FormControl fullWidth size="small" sx={{ mt: 2 }}>
                    <InputLabel>Primary Component Library</InputLabel>
                    <Select
                      value={formData.ui_config.primary_framework || ''}
                      label="Primary Component Library"
                      onChange={handlePrimaryFrameworkChange}
                    >
                      {formData.ui_config.frameworks.map((fwId) => {
                        const fw = availableFrameworks.find((f) => f.id === fwId);
                        return (
                          <MenuItem key={fwId} value={fwId}>
                            {fw?.name || fwId}
                          </MenuItem>
                        );
                      })}
                    </Select>
                    <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5 }}>
                      The primary library will be given more weight in test case generation
                    </Typography>
                  </FormControl>
                )}
              </AccordionDetails>
            </Accordion>
          </Box>
        </DialogContent>
        <DialogActions sx={{ p: 3 }}>
          <Button onClick={() => setOpenDialog(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleCreateProject} disabled={!formData.name}>
            Create Project
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
