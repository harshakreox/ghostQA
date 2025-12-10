import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Button,
  TextField,
  Typography,
  Paper,
  IconButton,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Grid,
  Card,
  CardContent,
  Divider,
  Breadcrumbs,
  Link,
  Chip,
} from '@mui/material';
import {
  Add,
  Delete,
  ArrowUpward,
  ArrowDownward,
  Save,
  NavigateNext,
  PlayArrow,
} from '@mui/icons-material';
import axios from 'axios';

const ACTION_TYPES = [
  { value: 'navigate', label: 'Navigate to URL' },
  { value: 'click', label: 'Click Element' },
  { value: 'type', label: 'Type Text' },
  { value: 'select', label: 'Select Option' },
  { value: 'check', label: 'Check Checkbox' },
  { value: 'uncheck', label: 'Uncheck Checkbox' },
  { value: 'hover', label: 'Hover Over Element' },
  { value: 'wait', label: 'Wait' },
  { value: 'assert_text', label: 'Assert Text' },
  { value: 'assert_url', label: 'Assert URL' },
  { value: 'assert_visible', label: 'Assert Visible' },
  { value: 'screenshot', label: 'Take Screenshot' },
];

const SELECTOR_TYPES = [
  { value: 'css', label: 'CSS Selector' },
  { value: 'xpath', label: 'XPath' },
  { value: 'text', label: 'Text Content' },
  { value: 'id', label: 'ID' },
  { value: 'class', label: 'Class' },
  { value: 'placeholder', label: 'Placeholder' },
];

export default function TestCaseEditor() {
  const { id, testCaseId } = useParams();
  const navigate = useNavigate();
  const [project, setProject] = useState(null);
  const [testCase, setTestCase] = useState({
    name: '',
    description: '',
    actions: [],
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, [id, testCaseId]);

  const loadData = async () => {
    try {
      const projectRes = await axios.get(`/api/projects/${id}`);
      setProject(projectRes.data);

      if (testCaseId) {
        const testCaseRes = await axios.get(`/api/projects/${id}/test-cases/${testCaseId}`);
        setTestCase(testCaseRes.data);
      }
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddAction = () => {
    setTestCase({
      ...testCase,
      actions: [
        ...testCase.actions,
        {
          action: 'click',
          selector_type: 'css',
          selector: '',
          value: '',
          description: '',
          wait_before: 0,
          wait_after: 500,
        },
      ],
    });
  };

  const handleUpdateAction = (index, field, value) => {
    const newActions = [...testCase.actions];
    newActions[index] = { ...newActions[index], [field]: value };
    setTestCase({ ...testCase, actions: newActions });
  };

  const handleDeleteAction = (index) => {
    const newActions = testCase.actions.filter((_, i) => i !== index);
    setTestCase({ ...testCase, actions: newActions });
  };

  const handleMoveAction = (index, direction) => {
    const newActions = [...testCase.actions];
    const newIndex = direction === 'up' ? index - 1 : index + 1;
    if (newIndex >= 0 && newIndex < newActions.length) {
      [newActions[index], newActions[newIndex]] = [newActions[newIndex], newActions[index]];
      setTestCase({ ...testCase, actions: newActions });
    }
  };

  const handleSave = async () => {
    try {
      if (testCaseId) {
        await axios.put(`/api/projects/${id}/test-cases/${testCaseId}`, testCase);
      } else {
        await axios.post(`/api/projects/${id}/test-cases`, testCase);
      }
      navigate(`/projects/${id}`);
    } catch (error) {
      console.error('Error saving test case:', error);
    }
  };

  if (loading) {
    return <Typography>Loading...</Typography>;
  }

  return (
    <Box>
      {/* Breadcrumbs */}
      <Breadcrumbs separator={<NavigateNext fontSize="small" />} sx={{ mb: 3 }}>
        <Link component="button" variant="body2" onClick={() => navigate('/projects')}>
          Projects
        </Link>
        <Link component="button" variant="body2" onClick={() => navigate(`/projects/${id}`)}>
          {project?.name}
        </Link>
        <Typography color="text.primary">
          {testCaseId ? 'Edit Test Case' : 'New Test Case'}
        </Typography>
      </Breadcrumbs>

      {/* Header */}
      <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 700, mb: 0.5 }}>
            {testCaseId ? 'Edit Test Case' : 'Create Test Case'}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Define automated test steps for your application
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button variant="outlined" onClick={() => navigate(`/projects/${id}`)}>
            Cancel
          </Button>
          <Button
            variant="contained"
            startIcon={<Save />}
            onClick={handleSave}
            disabled={!testCase.name || testCase.actions.length === 0}
            sx={{
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            }}
          >
            Save Test Case
          </Button>
        </Box>
      </Box>

      <Grid container spacing={3}>
        {/* Test Case Info */}
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
              Test Case Information
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Test Case Name"
                  value={testCase.name}
                  onChange={(e) => setTestCase({ ...testCase, name: e.target.value })}
                  required
                  placeholder="e.g., Login Flow Test"
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <Chip
                  icon={<PlayArrow />}
                  label={`${testCase.actions.length} Actions`}
                  color="primary"
                  sx={{ fontWeight: 600 }}
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  multiline
                  rows={3}
                  label="Description"
                  value={testCase.description}
                  onChange={(e) => setTestCase({ ...testCase, description: e.target.value })}
                  placeholder="Describe what this test case validates..."
                />
              </Grid>
            </Grid>
          </Paper>
        </Grid>

        {/* Actions */}
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                Test Actions
              </Typography>
              <Button variant="contained" startIcon={<Add />} onClick={handleAddAction}>
                Add Action
              </Button>
            </Box>

            {testCase.actions.length === 0 ? (
              <Box sx={{ textAlign: 'center', py: 6 }}>
                <PlayArrow sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
                <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
                  No actions yet. Add your first action to start building the test.
                </Typography>
                <Button variant="outlined" startIcon={<Add />} onClick={handleAddAction}>
                  Add First Action
                </Button>
              </Box>
            ) : (
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {testCase.actions.map((action, index) => (
                  <Card key={index} variant="outlined">
                    <CardContent>
                      <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2 }}>
                        {/* Step Number */}
                        <Box
                          sx={{
                            minWidth: 40,
                            height: 40,
                            borderRadius: '50%',
                            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                            color: 'white',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontWeight: 700,
                          }}
                        >
                          {index + 1}
                        </Box>

                        {/* Action Fields */}
                        <Grid container spacing={2} sx={{ flex: 1 }}>
                          <Grid item xs={12} md={3}>
                            <FormControl fullWidth size="small">
                              <InputLabel>Action Type</InputLabel>
                              <Select
                                value={action.action}
                                label="Action Type"
                                onChange={(e) => handleUpdateAction(index, 'action', e.target.value)}
                              >
                                {ACTION_TYPES.map((type) => (
                                  <MenuItem key={type.value} value={type.value}>
                                    {type.label}
                                  </MenuItem>
                                ))}
                              </Select>
                            </FormControl>
                          </Grid>

                          {action.action !== 'wait' && action.action !== 'screenshot' && (
                            <>
                              <Grid item xs={12} md={2}>
                                <FormControl fullWidth size="small">
                                  <InputLabel>Selector Type</InputLabel>
                                  <Select
                                    value={action.selector_type || 'css'}
                                    label="Selector Type"
                                    onChange={(e) =>
                                      handleUpdateAction(index, 'selector_type', e.target.value)
                                    }
                                  >
                                    {SELECTOR_TYPES.map((type) => (
                                      <MenuItem key={type.value} value={type.value}>
                                        {type.label}
                                      </MenuItem>
                                    ))}
                                  </Select>
                                </FormControl>
                              </Grid>

                              <Grid item xs={12} md={3}>
                                <TextField
                                  fullWidth
                                  size="small"
                                  label="Selector"
                                  value={action.selector || ''}
                                  onChange={(e) => handleUpdateAction(index, 'selector', e.target.value)}
                                  placeholder="#button-id"
                                />
                              </Grid>
                            </>
                          )}

                          <Grid item xs={12} md={4}>
                            <TextField
                              fullWidth
                              size="small"
                              label={
                                action.action === 'wait'
                                  ? 'Duration (ms)'
                                  : action.action === 'screenshot'
                                  ? 'Filename'
                                  : 'Value'
                              }
                              value={action.value || ''}
                              onChange={(e) => handleUpdateAction(index, 'value', e.target.value)}
                              placeholder={
                                action.action === 'wait'
                                  ? '1000'
                                  : action.action === 'navigate'
                                  ? 'https://example.com'
                                  : 'Value to input'
                              }
                            />
                          </Grid>
                        </Grid>

                        {/* Action Buttons */}
                        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                          <IconButton
                            size="small"
                            onClick={() => handleMoveAction(index, 'up')}
                            disabled={index === 0}
                          >
                            <ArrowUpward fontSize="small" />
                          </IconButton>
                          <IconButton
                            size="small"
                            onClick={() => handleMoveAction(index, 'down')}
                            disabled={index === testCase.actions.length - 1}
                          >
                            <ArrowDownward fontSize="small" />
                          </IconButton>
                          <IconButton
                            size="small"
                            color="error"
                            onClick={() => handleDeleteAction(index)}
                          >
                            <Delete fontSize="small" />
                          </IconButton>
                        </Box>
                      </Box>

                      {/* Description */}
                      <TextField
                        fullWidth
                        size="small"
                        label="Step Description"
                        value={action.description || ''}
                        onChange={(e) => handleUpdateAction(index, 'description', e.target.value)}
                        placeholder="Describe this step..."
                        sx={{ mt: 2 }}
                      />
                    </CardContent>
                  </Card>
                ))}
              </Box>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}