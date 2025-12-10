import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Button,
  TextField,
  Typography,
  Paper,
  Grid,
  Breadcrumbs,
  Link,
  LinearProgress,
  Divider,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  InputAdornment,
  IconButton,
  Alert,
  FormGroup,
  FormControlLabel,
  Checkbox,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
} from '@mui/material';
import {
  Save,
  Cancel,
  NavigateNext,
  ExpandMore,
  Key,
  Visibility,
  VisibilityOff,
  Widgets,
  Add,
  Delete,
  Person,
} from '@mui/icons-material';
import axios from 'axios';

export default function ProjectEdit() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [showPasswords, setShowPasswords] = useState({}); // Track visibility per credential
  const [availableFrameworks, setAvailableFrameworks] = useState([]);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    base_url: '',
    credentials: [], // New: Array of credential sets
    auto_test_data: true,
    ui_config: {
      frameworks: [],
      primary_framework: null,
      testing_library: 'playwright',
    },
  });

  useEffect(() => {
    loadProject();
    fetchFrameworks();
  }, [id]);

  const fetchFrameworks = async () => {
    try {
      const response = await axios.get('/api/frameworks');
      setAvailableFrameworks(response.data.frameworks || []);
    } catch (error) {
      console.error('Error fetching frameworks:', error);
    }
  };

  const loadProject = async () => {
    try {
      const response = await axios.get(`/api/projects/${id}`);
      const project = response.data;

      // Handle migration from legacy credentials to new format
      let credentials = project.credentials || [];

      // If no new credentials but legacy fields exist, migrate them
      if (credentials.length === 0) {
        if (project.test_username || project.test_password) {
          credentials.push({
            role_name: 'standard_user',
            username: project.test_username || '',
            password: project.test_password || '',
          });
        }
        if (project.test_admin_username || project.test_admin_password) {
          credentials.push({
            role_name: 'admin',
            username: project.test_admin_username || '',
            password: project.test_admin_password || '',
          });
        }
      }

      setFormData({
        name: project.name,
        description: project.description,
        base_url: project.base_url || '',
        credentials: credentials,
        auto_test_data: project.auto_test_data !== false,
        ui_config: project.ui_config || {
          frameworks: [],
          primary_framework: null,
          testing_library: 'playwright',
        },
      });
    } catch (error) {
      console.error('Error loading project:', error);
    } finally {
      setLoading(false);
    }
  };

  // Handle framework checkbox toggle
  const handleFrameworkToggle = (frameworkId) => {
    const currentFrameworks = formData.ui_config.frameworks;
    let newFrameworks;

    if (currentFrameworks.includes(frameworkId)) {
      newFrameworks = currentFrameworks.filter((f) => f !== frameworkId);
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
      newFrameworks = [...currentFrameworks, frameworkId];
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

  // Credential management functions
  const addCredential = () => {
    const newCredential = {
      role_name: '',
      username: '',
      password: '',
    };
    setFormData({
      ...formData,
      credentials: [...formData.credentials, newCredential],
    });
  };

  const removeCredential = (index) => {
    const newCredentials = formData.credentials.filter((_, i) => i !== index);
    setFormData({
      ...formData,
      credentials: newCredentials,
    });
    // Clean up password visibility state
    const newShowPasswords = { ...showPasswords };
    delete newShowPasswords[index];
    setShowPasswords(newShowPasswords);
  };

  const updateCredential = (index, field, value) => {
    const newCredentials = [...formData.credentials];
    newCredentials[index] = {
      ...newCredentials[index],
      [field]: value,
    };
    setFormData({
      ...formData,
      credentials: newCredentials,
    });
  };

  const togglePasswordVisibility = (index) => {
    setShowPasswords({
      ...showPasswords,
      [index]: !showPasswords[index],
    });
  };

  const handleSave = async () => {
    try {
      await axios.put(`/api/projects/${id}`, formData);
      navigate(`/projects/${id}`);
    } catch (error) {
      console.error('Error updating project:', error);
      alert('Failed to update project');
    }
  };

  if (loading) {
    return <LinearProgress />;
  }

  return (
    <Box>
      {/* Breadcrumbs */}
      <Breadcrumbs separator={<NavigateNext fontSize="small" />} sx={{ mb: 3 }}>
        <Link component="button" variant="body2" onClick={() => navigate('/projects')}>
          Projects
        </Link>
        <Link component="button" variant="body2" onClick={() => navigate(`/projects/${id}`)}>
          {formData.name}
        </Link>
        <Typography color="text.primary">Edit</Typography>
      </Breadcrumbs>

      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" sx={{ fontWeight: 700, mb: 0.5 }}>
          Edit Project
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Update project settings and configuration
        </Typography>
      </Box>

      {/* Form */}
      <Paper sx={{ p: 4 }}>
        <Grid container spacing={3}>
          {/* Basic Settings */}
          <Grid item xs={12}>
            <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
              Basic Settings
            </Typography>
          </Grid>

          <Grid item xs={12}>
            <TextField
              fullWidth
              label="Project Name"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              required
              helperText="A descriptive name for your project"
            />
          </Grid>

          <Grid item xs={12}>
            <TextField
              fullWidth
              multiline
              rows={4}
              label="Description"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              helperText="Describe what this project tests"
            />
          </Grid>

          <Grid item xs={12}>
            <TextField
              fullWidth
              label="Base URL"
              value={formData.base_url}
              onChange={(e) => setFormData({ ...formData, base_url: e.target.value })}
              placeholder="https://example.com"
              helperText="The default URL for your application (used for relative paths)"
            />
          </Grid>

          <Grid item xs={12}>
            <Divider sx={{ my: 2 }} />
          </Grid>

          {/* Test Credentials Section */}
          <Grid item xs={12}>
            <Accordion
              defaultExpanded
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
                  borderBottom: '1px solid',
                  borderColor: 'divider',
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Key sx={{ color: '#667eea' }} />
                  <Box>
                    <Typography variant="h6" sx={{ fontWeight: 600 }}>
                      Test Credentials
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Configure role-based credentials for AI-powered automated testing
                    </Typography>
                  </Box>
                  {formData.credentials.length > 0 && (
                    <Chip
                      label={`${formData.credentials.length} role${formData.credentials.length > 1 ? 's' : ''}`}
                      size="small"
                      color="primary"
                      sx={{ ml: 2 }}
                    />
                  )}
                </Box>
              </AccordionSummary>
              <AccordionDetails sx={{ p: 3 }}>
                <Alert severity="info" sx={{ mb: 3 }}>
                  Define credential sets for different user roles. When generating tests, you can reference credentials by role name
                  (e.g., "I log in as admin" or "I log in as standard_user").
                </Alert>

                {/* Credential Sets */}
                {formData.credentials.map((cred, index) => (
                  <Paper
                    key={index}
                    elevation={0}
                    sx={{
                      p: 2.5,
                      mb: 2,
                      border: '1px solid',
                      borderColor: 'divider',
                      borderRadius: 2,
                      bgcolor: 'grey.50',
                    }}
                  >
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Person sx={{ color: '#667eea' }} />
                        <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                          Credential Set #{index + 1}
                        </Typography>
                        {cred.role_name && (
                          <Chip
                            label={cred.role_name}
                            size="small"
                            color="secondary"
                            variant="outlined"
                          />
                        )}
                      </Box>
                      <IconButton
                        onClick={() => removeCredential(index)}
                        color="error"
                        size="small"
                        title="Remove credential set"
                      >
                        <Delete />
                      </IconButton>
                    </Box>

                    <Grid container spacing={2}>
                      {/* Role Name */}
                      <Grid item xs={12} md={4}>
                        <TextField
                          fullWidth
                          size="small"
                          label="Role Name"
                          value={cred.role_name}
                          onChange={(e) => updateCredential(index, 'role_name', e.target.value)}
                          placeholder="e.g., admin, standard_user, manager"
                          helperText="Unique identifier for this credential set"
                        />
                      </Grid>

                      {/* Username */}
                      <Grid item xs={12} md={4}>
                        <TextField
                          fullWidth
                          size="small"
                          label="Username"
                          value={cred.username}
                          onChange={(e) => updateCredential(index, 'username', e.target.value)}
                          placeholder="user@example.com"
                        />
                      </Grid>

                      {/* Password */}
                      <Grid item xs={12} md={4}>
                        <TextField
                          fullWidth
                          size="small"
                          label="Password"
                          type={showPasswords[index] ? 'text' : 'password'}
                          value={cred.password}
                          onChange={(e) => updateCredential(index, 'password', e.target.value)}
                          placeholder="Enter password"
                          InputProps={{
                            endAdornment: (
                              <InputAdornment position="end">
                                <IconButton
                                  onClick={() => togglePasswordVisibility(index)}
                                  edge="end"
                                  size="small"
                                >
                                  {showPasswords[index] ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
                                </IconButton>
                              </InputAdornment>
                            ),
                          }}
                        />
                      </Grid>
                    </Grid>
                  </Paper>
                ))}

                {/* Add Credential Button */}
                <Button
                  variant="outlined"
                  startIcon={<Add />}
                  onClick={addCredential}
                  sx={{
                    mt: 1,
                    borderStyle: 'dashed',
                    borderColor: '#667eea',
                    color: '#667eea',
                    '&:hover': {
                      borderStyle: 'dashed',
                      borderColor: '#764ba2',
                      bgcolor: 'rgba(102, 126, 234, 0.04)',
                    },
                  }}
                >
                  Add Another Credential Set
                </Button>

                {/* Auto Test Data Toggle */}
                <Box sx={{ mt: 3 }}>
                  <Divider sx={{ mb: 2 }} />
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={formData.auto_test_data}
                        onChange={(e) => setFormData({ ...formData, auto_test_data: e.target.checked })}
                      />
                    }
                    label={
                      <Box>
                        <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                          Enable Auto Test Data Generation
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          Automatically generate realistic test data when no matching credentials are found
                        </Typography>
                      </Box>
                    }
                  />
                </Box>

                {/* How AI Uses These */}
                <Alert severity="success" sx={{ mt: 2 }}>
                  <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5 }}>
                    How AI Uses Role-Based Credentials:
                  </Typography>
                  <Typography variant="body2" component="div">
                    • "I log in as admin" → Uses credentials with role "admin"
                    <br />
                    • "I log in as standard_user" → Uses credentials with role "standard_user"
                    <br />
                    • "I log in as manager" → Uses credentials with role "manager"
                    <br />
                    • Steps referencing "my username/password" → Uses first available credential set
                    <br />
                    • If no matching role found → Falls back to auto-generated data (if enabled)
                  </Typography>
                </Alert>

                {/* Available Roles Summary */}
                {formData.credentials.length > 0 && (
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                      Configured Roles:
                    </Typography>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                      {formData.credentials
                        .filter((c) => c.role_name)
                        .map((cred, index) => (
                          <Chip
                            key={index}
                            label={cred.role_name}
                            size="small"
                            color="primary"
                            variant="outlined"
                          />
                        ))}
                    </Box>
                  </Box>
                )}
              </AccordionDetails>
            </Accordion>
          </Grid>

          {/* UI Framework Configuration Section */}
          <Grid item xs={12}>
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
                  borderBottom: '1px solid',
                  borderColor: 'divider',
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Widgets sx={{ color: '#667eea' }} />
                  <Box>
                    <Typography variant="h6" sx={{ fontWeight: 600 }}>
                      UI Framework Configuration
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Configure frameworks for AI-powered test case generation
                    </Typography>
                  </Box>
                  {formData.ui_config.frameworks.length > 0 && (
                    <Chip
                      label={`${formData.ui_config.frameworks.length} selected`}
                      size="small"
                      color="primary"
                      sx={{ ml: 2 }}
                    />
                  )}
                </Box>
              </AccordionSummary>
              <AccordionDetails sx={{ p: 3 }}>
                <Alert severity="info" sx={{ mb: 3 }}>
                  Select the UI frameworks used in your application. This helps the AI generate more accurate test cases
                  with framework-specific selectors and component knowledge.
                </Alert>

                <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 2 }}>
                  Select frameworks used in your application:
                </Typography>

                <FormGroup sx={{ mb: 3 }}>
                  <Grid container spacing={1}>
                    {availableFrameworks.map((fw) => (
                      <Grid item xs={12} sm={6} md={4} key={fw.id}>
                        <FormControlLabel
                          control={
                            <Checkbox
                              checked={formData.ui_config.frameworks.includes(fw.id)}
                              onChange={() => handleFrameworkToggle(fw.id)}
                            />
                          }
                          label={
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              <Typography variant="body2">{fw.name}</Typography>
                              <Chip label={fw.category} size="small" variant="outlined" sx={{ fontSize: '0.65rem', height: 18 }} />
                            </Box>
                          }
                        />
                      </Grid>
                    ))}
                  </Grid>
                </FormGroup>

                {/* Primary Framework Selection */}
                {formData.ui_config.frameworks.length > 1 && (
                  <Box sx={{ mt: 2 }}>
                    <Divider sx={{ my: 2 }} />
                    <FormControl fullWidth size="small">
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
                  </Box>
                )}

                {formData.ui_config.frameworks.length > 0 && (
                  <Alert severity="success" sx={{ mt: 3 }}>
                    <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5 }}>
                      Selected Frameworks:
                    </Typography>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 1 }}>
                      {formData.ui_config.frameworks.map((fwId) => {
                        const fw = availableFrameworks.find((f) => f.id === fwId);
                        return (
                          <Chip
                            key={fwId}
                            label={fw?.name || fwId}
                            size="small"
                            color={formData.ui_config.primary_framework === fwId ? 'primary' : 'default'}
                          />
                        );
                      })}
                    </Box>
                  </Alert>
                )}
              </AccordionDetails>
            </Accordion>
          </Grid>

          {/* Action Buttons */}
          <Grid item xs={12}>
            <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end', mt: 2 }}>
              <Button variant="outlined" startIcon={<Cancel />} onClick={() => navigate(`/projects/${id}`)}>
                Cancel
              </Button>
              <Button
                variant="contained"
                startIcon={<Save />}
                onClick={handleSave}
                disabled={!formData.name}
                sx={{
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                }}
              >
                Save Changes
              </Button>
            </Box>
          </Grid>
        </Grid>
      </Paper>
    </Box>
  );
}