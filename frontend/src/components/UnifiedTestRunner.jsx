/**
 * Unified Test Runner Component
 *
 * Provides a consistent UI for running both Traditional and Gherkin tests
 * using the autonomous agent API with learning capabilities.
 */

import { useState, useEffect, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Box,
  Button,
  Typography,
  Paper,
  Checkbox,
  FormControlLabel,
  LinearProgress,
  Card,
  CardContent,
  Alert,
  Chip,
  Switch,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Divider,
  CircularProgress,
  ToggleButton,
  ToggleButtonGroup,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Grid,
  Snackbar,
  Tooltip,
  Badge,
  Collapse,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  IconButton,
  InputAdornment,
} from '@mui/material';
import {
  PlayArrow,
  Stop,
  CheckCircle,
  Code,
  HourglassEmpty,
  Psychology,
  AutoAwesome,
  ExpandMore,
  Timer,
  BugReport,
  FolderOpen,
  Science,
  Speed,
  School,
  TrendingDown,
  Memory,
  Refresh,
  Settings,
  ExpandLess,
  Edit as EditIcon,
  Save,
  Close,
  Add,
  Delete,
  Search,
  Clear,
} from '@mui/icons-material';
import axios from 'axios';

// Helper to get auth headers
const getAuthHeaders = () => {
  const token = localStorage.getItem('auth_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
};

// Axios instance with auth
const authAxios = {
  get: (url, config = {}) => axios.get(url, { ...config, headers: { ...config.headers, ...getAuthHeaders() } }),
  post: (url, data, config = {}) => axios.post(url, data, { ...config, headers: { ...config.headers, ...getAuthHeaders() } }),
  put: (url, data, config = {}) => axios.put(url, data, { ...config, headers: { ...config.headers, ...getAuthHeaders() } }),
  delete: (url, config = {}) => axios.delete(url, { ...config, headers: { ...config.headers, ...getAuthHeaders() } }),
};

// Execution mode - always use smart/guided mode (brain optimizes automatically)
const EXECUTION_MODE = 'guided';

export default function UnifiedTestRunner({ projectId: propProjectId }) {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const logsEndRef = useRef(null);

  // Get URL params
  const urlProjectId = searchParams.get('projectId');
  const urlFeatureId = searchParams.get('featureId');

  // Project selection
  const [projects, setProjects] = useState([]);
  const [selectedProjectId, setSelectedProjectId] = useState(propProjectId || urlProjectId || '');
  const [selectedProject, setSelectedProject] = useState(null);
  const [loadingProjects, setLoadingProjects] = useState(true);

  // Test type selection: 'traditional' or 'gherkin'
  const [testType, setTestType] = useState(urlFeatureId ? 'gherkin' : 'traditional');

  // Traditional test state
  const [traditionalSuites, setTraditionalSuites] = useState([]);
  const [selectedTraditionalTests, setSelectedTraditionalTests] = useState([]);

  // Gherkin test state
  const [gherkinFeatures, setGherkinFeatures] = useState([]);
  const [selectedGherkinFeature, setSelectedGherkinFeature] = useState(null);
  const [selectedScenarios, setSelectedScenarios] = useState([]);

  // Execution state
  // Execution mode is fixed to 'guided' - brain optimizes AI usage automatically
  const executionMode = EXECUTION_MODE;
  const [headless, setHeadless] = useState(false);
  const [running, setRunning] = useState(false);
  const [logs, setLogs] = useState([]);
  const [ws, setWs] = useState(null);
  const [statusMessage, setStatusMessage] = useState('');
  const [result, setResult] = useState(null);

  // Learning metrics
  const [learningStats, setLearningStats] = useState(null);
  const [showAdvanced, setShowAdvanced] = useState(false);

  // UI state
  const [logsExpanded, setLogsExpanded] = useState(true);
  const [testSearch, setTestSearch] = useState('');

  // Snackbar
  const [snackbar, setSnackbar] = useState({
    open: false,
    message: '',
    severity: 'success'
  });

  // Gherkin editing state
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editingFeature, setEditingFeature] = useState(null);
  const [editingScenarioIndex, setEditingScenarioIndex] = useState(null);
  const [editedSteps, setEditedSteps] = useState([]);
  const [savingFeature, setSavingFeature] = useState(false);

  const showNotification = (message, severity = 'success') => {
    setSnackbar({ open: true, message, severity });
  };

  const handleCloseSnackbar = () => {
    setSnackbar({ ...snackbar, open: false });
  };

  // Get WebSocket URL dynamically
  const getWebSocketUrl = () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.hostname;
    const port = '8000';
    return `${protocol}//${host}:${port}/api/agent/ws/logs`;
  };

  // Auto-scroll logs
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  // Load projects on mount
  useEffect(() => {
    loadProjects();
    loadLearningStats();

    const handleBeforeUnload = (e) => {
      if (running) {
        navigator.sendBeacon('/api/agent/stop', '');
        e.preventDefault();
        e.returnValue = 'Tests are still running. Are you sure you want to leave?';
        return e.returnValue;
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      if (ws) ws.close();
      if (running) {
        authAxios.post('/api/agent/stop').catch(() => {});
      }
    };
  }, [running]);

  // Load project data when selection changes
  useEffect(() => {
    if (selectedProjectId) {
      loadProjectDetails(selectedProjectId);
      loadGherkinFeatures(selectedProjectId);
      loadTraditionalSuites(selectedProjectId);
    } else {
      setSelectedProject(null);
      setSelectedTraditionalTests([]);
      setGherkinFeatures([]);
      setSelectedGherkinFeature(null);
    }
  }, [selectedProjectId]);

  // Auto-select feature from URL params
  useEffect(() => {
    if (urlFeatureId && gherkinFeatures.length > 0) {
      const feature = gherkinFeatures.find(f => f.id === urlFeatureId);
      if (feature) {
        handleSelectGherkinFeature(feature);
      }
    }
  }, [urlFeatureId, gherkinFeatures]);

  const loadProjects = async () => {
    try {
      const response = await authAxios.get('/api/projects');
      setProjects(response.data);
    } catch (error) {
      console.error('Error loading projects:', error);
      showNotification('Failed to load projects', 'error');
    } finally {
      setLoadingProjects(false);
    }
  };

  const loadProjectDetails = async (projectId) => {
    try {
      const response = await authAxios.get(`/api/projects/${projectId}`);
      setSelectedProject(response.data);
      if (response.data.test_cases) {
        setSelectedTraditionalTests(response.data.test_cases.map((tc) => tc.id));
      }
    } catch (error) {
      console.error('Error loading project:', error);
      showNotification('Failed to load project details', 'error');
    }
  };

  const loadGherkinFeatures = async (projectId) => {
    try {
      const response = await authAxios.get(`/api/projects/${projectId}/gherkin-features`);
      let features = Array.isArray(response.data)
        ? response.data
        : response.data?.features || [];
      setGherkinFeatures(features);
    } catch (error) {
      console.error('Error loading Gherkin features:', error);
      setGherkinFeatures([]);
    }
  };

  const loadTraditionalSuites = async (projectId) => {
    try {
      const response = await authAxios.get(`/api/projects/${projectId}/traditional-suites`);
      let suites = response.data?.suites || [];
      setTraditionalSuites(suites);
    } catch (error) {
      console.error('Error loading traditional suites:', error);
      setTraditionalSuites([]);
    }
  };

  const loadLearningStats = async () => {
    try {
      // Use the new brain stats endpoint for comprehensive metrics
      const response = await authAxios.get('/api/agent/brain/stats');
      // Map to the format expected by the UI
      setLearningStats({
        current_ai_dependency_percent: response.data.knowledge?.ai_dependency_percent || 0,
        total_elements_known: response.data.knowledge?.total_elements || 0,
        patterns_learned: response.data.knowledge?.patterns_learned || 0,
        average_confidence: response.data.knowledge?.average_confidence || 0,
        recommendation: response.data.recommendation,
        health_score: response.data.health?.score || 0,
        health_status: response.data.health?.status || 'training',
        memory: response.data.memory || {},
        decisions: response.data.decisions || {}
      });
    } catch (error) {
      console.error('Error loading learning stats:', error);
      // Fallback to old endpoint if new one fails
      try {
        const fallback = await authAxios.get('/api/agent/metrics/ai-dependency');
        setLearningStats(fallback.data);
      } catch (e) {
        console.error('Fallback also failed:', e);
      }
    }
  };

  // Test selection handlers
  const handleToggleTraditionalTest = (testId) => {
    setSelectedTraditionalTests((prev) =>
      prev.includes(testId) ? prev.filter((id) => id !== testId) : [...prev, testId]
    );
  };

  const handleSelectAllTraditional = () => {
    if (!selectedProject?.test_cases) return;
    const filteredTests = getFilteredTraditionalTests();
    const allSelected = filteredTests.every(tc => selectedTraditionalTests.includes(tc.id));
    if (allSelected) {
      setSelectedTraditionalTests(prev => prev.filter(id => !filteredTests.find(tc => tc.id === id)));
    } else {
      const newSelections = filteredTests.map(tc => tc.id).filter(id => !selectedTraditionalTests.includes(id));
      setSelectedTraditionalTests(prev => [...prev, ...newSelections]);
    }
  };

  const handleSelectGherkinFeature = async (feature) => {
    if (!feature) {
      setSelectedGherkinFeature(null);
      setSelectedScenarios([]);
      return;
    }

    try {
      const response = await authAxios.get(`/api/gherkin/features/${feature.id}`);
      const fullFeature = response.data;
      setSelectedGherkinFeature(fullFeature);
      setGherkinFeatures(prev => prev.map(f =>
        f.id === feature.id ? fullFeature : f
      ));
      if (fullFeature?.scenarios) {
        setSelectedScenarios(fullFeature.scenarios.map((s) => s.name));
      }
    } catch (error) {
      console.error('Error loading feature details:', error);
      setSelectedGherkinFeature(feature);
      if (feature?.scenarios) {
        setSelectedScenarios(feature.scenarios.map((s) => s.name));
      }
    }
  };

  // Filter tests by search
  const getFilteredTraditionalTests = () => {
    if (!selectedProject?.test_cases) return [];
    if (!testSearch) return selectedProject.test_cases;
    const search = testSearch.toLowerCase();
    return selectedProject.test_cases.filter(tc =>
      tc.name.toLowerCase().includes(search)
    );
  };

  const getFilteredGherkinFeatures = () => {
    if (!gherkinFeatures.length) return [];
    if (!testSearch) return gherkinFeatures;
    const search = testSearch.toLowerCase();
    return gherkinFeatures.filter(f =>
      f.name.toLowerCase().includes(search) ||
      (f.description && f.description.toLowerCase().includes(search))
    );
  };

  // Run tests using unified agent API
  const handleRunTests = async () => {
    if (!selectedProjectId || !selectedProject) {
      showNotification('Please select a project first', 'warning');
      return;
    }

    if (testType === 'traditional' && selectedTraditionalTests.length === 0) {
      showNotification('Please select at least one test case', 'warning');
      return;
    }

    if (testType === 'gherkin' && !selectedGherkinFeature) {
      showNotification('Please select a Gherkin feature', 'warning');
      return;
    }

    setRunning(true);
    setLogs([]);
    setResult(null);
    setStatusMessage('Initializing autonomous agent...');
    setLogsExpanded(true);

    const wsUrl = getWebSocketUrl();
    const websocket = new WebSocket(wsUrl);

    websocket.onopen = () => {
      addLog('Connected to autonomous agent');
    };

    websocket.onmessage = (event) => {
      addLog(event.data);
    };

    websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
      addLog('WebSocket connection error');
    };

    websocket.onclose = () => {
      addLog('Disconnected from agent');
    };

    setWs(websocket);

    try {
      const requestBody = {
        project_id: selectedProjectId,
        project_name: selectedProject.name,
        base_url: selectedProject.base_url,
        headless: headless,
        execution_mode: executionMode,
        credentials: {
          username: selectedProject.test_username || selectedProject.test_admin_username || '',
          password: selectedProject.test_password || selectedProject.test_admin_password || '',
          admin_username: selectedProject.test_admin_username || '',
          admin_password: selectedProject.test_admin_password || ''
        }
      };

      if (requestBody.credentials.username) {
        addLog(`Using credentials: ${requestBody.credentials.username.substring(0, 3)}***`);
      } else {
        addLog('WARNING: No credentials configured for this project');
      }

      if (testType === 'traditional') {
        const selectedTestCases = selectedProject.test_cases.filter(
          (tc) => selectedTraditionalTests.includes(tc.id)
        );
        requestBody.test_cases = selectedTestCases;
        addLog(`Running ${selectedTestCases.length} traditional test cases`);
      } else {
        addLog(`Running Gherkin feature: ${selectedGherkinFeature.name}`);
        addLog(`Using AI-powered autonomous executor`);

        setStatusMessage('Executing tests with Smart Mode...');
        addLog('Smart Mode: Brain-optimized execution');
        addLog(`Headless: ${headless}`);
        addLog('');

        const autonomousRequest = {
          feature_id: selectedGherkinFeature.id,
          project_id: selectedProjectId,
          headless: headless,
          scenario_filter: selectedScenarios.length < selectedGherkinFeature.scenarios?.length
            ? selectedScenarios
            : null
        };

        const response = await authAxios.post('/api/gherkin/run-autonomous', autonomousRequest);

        if (response.data) {
          const result = response.data;
          // Now using unified executor - get real learning stats
          const totalScenarios = result.total_scenarios || 0;
          const aiDependency = result.ai_dependency_percent ?? 100;
          const newSelectorsLearned = result.new_selectors_learned ?? 0;

          setResult({
            success: true,
            report_id: `autonomous_${Date.now()}`,
            summary: {
              total: totalScenarios,
              passed: result.passed || 0,
              failed: result.failed || 0,
              pass_rate: totalScenarios > 0
                ? Math.round((result.passed / totalScenarios) * 100)
                : 0,
              duration_seconds: result.total_duration || 0,
              ai_dependency_percent: aiDependency,
              new_selectors_learned: newSelectorsLearned
            },
            results: (result.scenario_results || []).map(sr => ({
              test_id: sr.scenario_name,
              test_name: sr.scenario_name,
              status: sr.status,
              duration_ms: (sr.duration || 0) * 1000,
              error_message: sr.error_message,
              ai_calls: sr.ai_decisions?.length || 0,
              kb_hits: 0
            }))
          });
          setStatusMessage('Test execution completed!');
          addLog('');
          addLog('========== RESULTS ==========');
          addLog(`Total: ${totalScenarios}`);
          addLog(`Passed: ${result.passed || 0}`);
          addLog(`Failed: ${result.failed || 0}`);
          addLog(`Duration: ${(result.total_duration || 0).toFixed(2)}s`);
          addLog(`AI Dependency: ${aiDependency.toFixed(1)}%`);
          addLog(`New Selectors Learned: ${newSelectorsLearned}`);
          addLog('=============================');

          showNotification(
            `Tests completed: ${result.passed || 0} passed, ${result.failed || 0} failed`,
            (result.failed || 0) > 0 ? 'warning' : 'success'
          );
        }
        return;
      }

      setStatusMessage('Executing tests with Smart Mode...');
      addLog('Smart Mode: Brain-optimized execution');
      addLog(`Headless: ${headless}`);
      addLog('');

      const response = await authAxios.post('/api/agent/run', requestBody);

      if (response.data.success) {
        setResult(response.data);
        setStatusMessage('Test execution completed!');
        addLog('');
        addLog('========== RESULTS ==========');
        addLog(`Total: ${response.data.summary.total}`);
        addLog(`Passed: ${response.data.summary.passed}`);
        addLog(`Failed: ${response.data.summary.failed}`);
        addLog(`Pass Rate: ${response.data.summary.pass_rate}%`);
        addLog(`AI Dependency: ${response.data.summary.ai_dependency_percent}%`);
        addLog(`New Selectors Learned: ${response.data.summary.new_selectors_learned}`);
        addLog('=============================');

        showNotification(
          `Tests completed: ${response.data.summary.passed} passed, ${response.data.summary.failed} failed`,
          response.data.summary.failed > 0 ? 'warning' : 'success'
        );

        loadLearningStats();
      } else {
        throw new Error('Execution failed');
      }
    } catch (error) {
      console.error('Test execution error:', error);
      const errorMsg = error.response?.data?.detail || error.message || 'Execution failed';
      addLog('');
      addLog(`ERROR: ${errorMsg}`);
      setStatusMessage(`Execution failed: ${errorMsg}`);
      showNotification('Test execution failed', 'error');
    } finally {
      setRunning(false);
      if (websocket) {
        setTimeout(() => websocket.close(), 1000);
      }
    }
  };

  const handleStopTests = async () => {
    try {
      addLog('[SYSTEM] Requesting stop...');
      setStatusMessage('Stopping test execution...');

      const response = await authAxios.post('/api/agent/stop');

      if (response.data.success) {
        addLog('[SYSTEM] Stop signal sent - finishing current test');
        showNotification('Stop requested - finishing current test', 'info');

        if (response.data.partial_report_id) {
          setResult({
            report_id: response.data.partial_report_id,
            summary: {
              total: 0,
              passed: 0,
              failed: 0,
              pass_rate: 0,
              duration_seconds: 0,
              ai_dependency_percent: 0,
              new_selectors_learned: 0
            },
            partial: true
          });
        }
      } else {
        addLog(`[SYSTEM] ${response.data.message}`);
      }
    } catch (error) {
      console.error('Stop error:', error);
      addLog('[ERROR] Failed to stop execution');
      showNotification('Failed to stop execution', 'error');
    }
  };

  const addLog = (message) => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs((prev) => [...prev, `[${timestamp}] ${message}`]);
  };

  const getLogColor = (log) => {
    if (log.includes('PASSED') || log.includes('passed') || log.includes('completed') || log.includes('SUCCESS'))
      return 'success.light';
    if (log.includes('FAILED') || log.includes('failed') || log.includes('ERROR') || log.includes('error'))
      return 'error.light';
    if (log.includes('WARNING') || log.includes('warning') || log.includes('skipped'))
      return 'warning.light';
    if (log.includes('AI') || log.includes('Learning') || log.includes('Knowledge'))
      return '#bb86fc';
    return 'grey.100';
  };

  // Gherkin editing handlers
  const handleOpenEditDialog = (feature, scenarioIndex) => {
    setEditingFeature(JSON.parse(JSON.stringify(feature)));
    setEditingScenarioIndex(scenarioIndex);
    const scenario = feature.scenarios[scenarioIndex];
    setEditedSteps(scenario.steps ? [...scenario.steps] : []);
    setEditDialogOpen(true);
  };

  const handleCloseEditDialog = () => {
    setEditDialogOpen(false);
    setEditingFeature(null);
    setEditingScenarioIndex(null);
    setEditedSteps([]);
  };

  const handleStepChange = (index, field, value) => {
    const newSteps = [...editedSteps];
    newSteps[index] = { ...newSteps[index], [field]: value };
    setEditedSteps(newSteps);
  };

  const handleAddStep = () => {
    setEditedSteps([...editedSteps, { keyword: 'And', text: '' }]);
  };

  const handleDeleteStep = (index) => {
    setEditedSteps(editedSteps.filter((_, i) => i !== index));
  };

  const handleSaveFeature = async () => {
    if (!editingFeature || editingScenarioIndex === null) return;

    setSavingFeature(true);
    try {
      const updatedFeature = { ...editingFeature };
      updatedFeature.scenarios[editingScenarioIndex].steps = editedSteps;

      await authAxios.put(`/api/gherkin/features/${editingFeature.id}`, updatedFeature);

      setGherkinFeatures(prev => prev.map(f =>
        f.id === editingFeature.id ? updatedFeature : f
      ));

      if (selectedGherkinFeature?.id === editingFeature.id) {
        setSelectedGherkinFeature(updatedFeature);
      }

      showNotification('Feature saved successfully', 'success');
      handleCloseEditDialog();
    } catch (error) {
      console.error('Error saving feature:', error);
      showNotification('Failed to save feature', 'error');
    } finally {
      setSavingFeature(false);
    }
  };

  if (loadingProjects) {
    return <LinearProgress />;
  }

  const filteredTraditionalTests = getFilteredTraditionalTests();
  const filteredGherkinFeatures = getFilteredGherkinFeatures();

  return (
    <Box>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" sx={{ fontWeight: 700, mb: 0.5, display: 'flex', alignItems: 'center', gap: 1 }}>
          <AutoAwesome sx={{ color: '#667eea' }} />
          Autonomous Test Runner
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Self-learning test execution with AI-powered element discovery
        </Typography>
      </Box>

      {/* Learning Stats Banner */}
      {learningStats && (
        <Paper sx={{ p: 2, mb: 3, background: 'linear-gradient(135deg, #667eea15 0%, #764ba215 100%)' }}>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={6} md={2}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Psychology sx={{ color: learningStats.health_status === 'excellent' ? '#2e7d32' :
                                         learningStats.health_status === 'good' ? '#1976d2' : '#667eea' }} />
                <Box>
                  <Typography variant="caption" color="text.secondary">Brain Health</Typography>
                  <Typography variant="h6" sx={{ fontWeight: 700 }}>
                    {learningStats.health_score?.toFixed(0) || 0}%
                  </Typography>
                </Box>
              </Box>
            </Grid>
            <Grid item xs={6} md={2}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <School sx={{ color: '#667eea' }} />
                <Box>
                  <Typography variant="caption" color="text.secondary">AI Dependency</Typography>
                  <Typography variant="h6" sx={{ fontWeight: 700 }}>
                    {learningStats.current_ai_dependency_percent?.toFixed(1) || 0}%
                  </Typography>
                </Box>
              </Box>
            </Grid>
            <Grid item xs={6} md={2}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Memory sx={{ color: '#667eea' }} />
                <Box>
                  <Typography variant="caption" color="text.secondary">Elements Known</Typography>
                  <Typography variant="h6" sx={{ fontWeight: 700 }}>
                    {learningStats.total_elements_known || 0}
                  </Typography>
                </Box>
              </Box>
            </Grid>
            <Grid item xs={6} md={2}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <TrendingDown sx={{ color: '#4caf50' }} />
                <Box>
                  <Typography variant="caption" color="text.secondary">Patterns</Typography>
                  <Typography variant="h6" sx={{ fontWeight: 700 }}>
                    {learningStats.patterns_learned || 0}
                  </Typography>
                </Box>
              </Box>
            </Grid>
            <Grid item xs={6} md={2}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Speed sx={{ color: '#9c27b0' }} />
                <Box>
                  <Typography variant="caption" color="text.secondary">Confidence</Typography>
                  <Typography variant="h6" sx={{ fontWeight: 700 }}>
                    {learningStats.average_confidence?.toFixed(0) || 0}%
                  </Typography>
                </Box>
              </Box>
            </Grid>
            <Grid item xs={6} md={2}>
              <Tooltip title={learningStats.recommendation || 'Brain is learning from each test run'}>
                <Chip
                  icon={<Psychology />}
                  label={learningStats.health_status?.toUpperCase() || 'LEARNING'}
                  color={learningStats.health_status === 'excellent' ? 'success' :
                         learningStats.health_status === 'good' ? 'info' :
                         learningStats.health_status === 'learning' ? 'warning' : 'default'}
                  variant="filled"
                  sx={{ fontWeight: 'bold' }}
                />
              </Tooltip>
            </Grid>
          </Grid>
        </Paper>
      )}

      {/* Project Selection */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <FolderOpen color="primary" />
          <FormControl fullWidth>
            <InputLabel>Select Project</InputLabel>
            <Select
              value={selectedProjectId}
              onChange={(e) => setSelectedProjectId(e.target.value)}
              label="Select Project"
              disabled={running}
            >
              <MenuItem value="">
                <em>-- Select a Project --</em>
              </MenuItem>
              {projects.map((project) => (
                <MenuItem key={project.id} value={project.id}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%' }}>
                    <Typography>{project.name}</Typography>
                    <Chip
                      label={`${project.test_cases?.length || 0} tests`}
                      size="small"
                      sx={{ ml: 'auto' }}
                    />
                  </Box>
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <Tooltip title="Refresh projects">
            <Button onClick={loadProjects} disabled={running}>
              <Refresh />
            </Button>
          </Tooltip>
        </Box>

        {selectedProject && (
          <Box sx={{ mt: 2, display: 'flex', gap: 2, flexWrap: 'wrap' }}>
            <Chip
              icon={<Code />}
              label={`${selectedProject.test_cases?.length || 0} Test Cases`}
              color="primary"
              variant="outlined"
            />
            {selectedProject.base_url && (
              <Chip label={selectedProject.base_url} variant="outlined" />
            )}
            {gherkinFeatures.length > 0 && (
              <Chip
                icon={<Psychology />}
                label={`${gherkinFeatures.length} Gherkin Features`}
                color="secondary"
                variant="outlined"
              />
            )}
          </Box>
        )}
      </Paper>

      {/* No Project Selected */}
      {!selectedProjectId && (
        <Card sx={{ p: 6, textAlign: 'center' }}>
          <Science sx={{ fontSize: 80, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h6" sx={{ mb: 1 }}>
            Select a Project to Run Tests
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Choose a project from the dropdown above to begin autonomous test execution
          </Typography>
          <Button variant="outlined" onClick={() => navigate('/projects')}>
            Go to Projects
          </Button>
        </Card>
      )}

      {/* Test Execution UI */}
      {selectedProjectId && selectedProject && (
        <Grid container spacing={3}>
          {/* Left Panel - Test Selection */}
          <Grid item xs={12} md={7}>
            {/* Test Type Toggle */}
            <Paper sx={{ p: 2, mb: 3 }}>
              <ToggleButtonGroup
                value={testType}
                exclusive
                onChange={(e, newType) => newType && setTestType(newType)}
                fullWidth
                disabled={running}
              >
                <ToggleButton value="traditional" sx={{ py: 1.5 }}>
                  <Code sx={{ mr: 1 }} />
                  Traditional Tests
                  <Badge
                    badgeContent={selectedProject.test_cases?.length || 0}
                    color="primary"
                    sx={{ ml: 2 }}
                  />
                </ToggleButton>
                <ToggleButton value="gherkin" sx={{ py: 1.5 }}>
                  <Psychology sx={{ mr: 1 }} />
                  Gherkin Features
                  <Badge
                    badgeContent={gherkinFeatures.length}
                    color="secondary"
                    sx={{ ml: 2 }}
                  />
                </ToggleButton>
              </ToggleButtonGroup>
            </Paper>

            {/* Traditional Test Selection */}
            {testType === 'traditional' && (
              <Paper sx={{ p: 3 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                  <Typography variant="h6" sx={{ fontWeight: 600 }}>
                    Select Test Cases
                  </Typography>
                  <Button size="small" onClick={handleSelectAllTraditional} disabled={running}>
                    {filteredTraditionalTests.every(tc => selectedTraditionalTests.includes(tc.id))
                      ? 'Deselect All'
                      : 'Select All'}
                  </Button>
                </Box>

                {/* Search Bar */}
                <TextField
                  fullWidth
                  size="small"
                  placeholder="Search test cases..."
                  value={testSearch}
                  onChange={(e) => setTestSearch(e.target.value)}
                  sx={{ mb: 2 }}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <Search color="action" />
                      </InputAdornment>
                    ),
                    endAdornment: testSearch && (
                      <InputAdornment position="end">
                        <IconButton size="small" onClick={() => setTestSearch('')}>
                          <Clear fontSize="small" />
                        </IconButton>
                      </InputAdornment>
                    ),
                  }}
                />

                <Divider sx={{ mb: 2 }} />

                {!selectedProject.test_cases?.length ? (
                  <Alert severity="info">
                    No test cases available. Create test cases first.
                  </Alert>
                ) : filteredTraditionalTests.length === 0 ? (
                  <Alert severity="info">
                    No test cases match your search.
                  </Alert>
                ) : (
                  <List sx={{ maxHeight: 400, overflow: 'auto' }}>
                    {filteredTraditionalTests.map((testCase) => (
                      <ListItem
                        key={testCase.id}
                        sx={{
                          borderRadius: 2,
                          mb: 1,
                          bgcolor: selectedTraditionalTests.includes(testCase.id)
                            ? 'action.selected'
                            : 'transparent',
                        }}
                      >
                        <ListItemIcon>
                          <Checkbox
                            checked={selectedTraditionalTests.includes(testCase.id)}
                            onChange={() => handleToggleTraditionalTest(testCase.id)}
                            disabled={running}
                          />
                        </ListItemIcon>
                        <ListItemText
                          primary={testCase.name}
                          secondary={`${testCase.actions?.length || 0} actions`}
                        />
                        <Chip
                          icon={<Code />}
                          label={testCase.actions?.length || 0}
                          size="small"
                          color="primary"
                        />
                      </ListItem>
                    ))}
                  </List>
                )}
              </Paper>
            )}

            {/* Gherkin Feature Selection */}
            {testType === 'gherkin' && (
              <Paper sx={{ p: 3 }}>
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                  Select Gherkin Feature
                </Typography>

                {/* Search Bar */}
                <TextField
                  fullWidth
                  size="small"
                  placeholder="Search features..."
                  value={testSearch}
                  onChange={(e) => setTestSearch(e.target.value)}
                  sx={{ mb: 2 }}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <Search color="action" />
                      </InputAdornment>
                    ),
                    endAdornment: testSearch && (
                      <InputAdornment position="end">
                        <IconButton size="small" onClick={() => setTestSearch('')}>
                          <Clear fontSize="small" />
                        </IconButton>
                      </InputAdornment>
                    ),
                  }}
                />

                {gherkinFeatures.length === 0 ? (
                  <Alert severity="info" sx={{ mb: 2 }}>
                    No Gherkin features available for this project.
                    <Button
                      size="small"
                      sx={{ ml: 1 }}
                      onClick={() => navigate(`/generate?projectId=${selectedProjectId}`)}
                    >
                      Create with AI
                    </Button>
                  </Alert>
                ) : filteredGherkinFeatures.length === 0 ? (
                  <Alert severity="info">
                    No features match your search.
                  </Alert>
                ) : (
                  <Box>
                    {filteredGherkinFeatures.map((feature) => (
                      <Accordion
                        key={feature.id}
                        expanded={selectedGherkinFeature?.id === feature.id}
                        onChange={() => handleSelectGherkinFeature(
                          selectedGherkinFeature?.id === feature.id ? null : feature
                        )}
                        sx={{
                          mb: 2,
                          border: selectedGherkinFeature?.id === feature.id
                            ? '2px solid #667eea'
                            : 'none'
                        }}
                      >
                        <AccordionSummary expandIcon={<ExpandMore />}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: '100%' }}>
                            <Psychology sx={{ color: '#667eea' }} />
                            <Box sx={{ flex: 1 }}>
                              <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                                {feature.name}
                              </Typography>
                              <Typography variant="caption" color="text.secondary">
                                {feature.scenario_count} scenarios
                              </Typography>
                            </Box>
                            {selectedGherkinFeature?.id === feature.id && (
                              <Chip label="Selected" size="small" color="primary" />
                            )}
                          </Box>
                        </AccordionSummary>
                        <AccordionDetails>
                          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                            {feature.description || 'No description available'}
                          </Typography>
                          {feature.scenarios && (
                            <Box sx={{ maxHeight: 200, overflow: 'auto' }}>
                              {feature.scenarios.map((scenario, idx) => (
                                <Box key={idx} sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                                  <Checkbox
                                    size="small"
                                    checked={selectedScenarios.includes(scenario.name)}
                                    onChange={(e) => {
                                      if (e.target.checked) {
                                        setSelectedScenarios([...selectedScenarios, scenario.name]);
                                      } else {
                                        setSelectedScenarios(selectedScenarios.filter(s => s !== scenario.name));
                                      }
                                    }}
                                    disabled={running}
                                  />
                                  <Typography variant="body2" sx={{ flex: 1 }}>{scenario.name}</Typography>
                                  <Tooltip title="Edit steps">
                                    <IconButton
                                      size="small"
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        handleOpenEditDialog(feature, idx);
                                      }}
                                      disabled={running}
                                      sx={{ ml: 'auto' }}
                                    >
                                      <EditIcon fontSize="small" />
                                    </IconButton>
                                  </Tooltip>
                                </Box>
                              ))}
                            </Box>
                          )}
                        </AccordionDetails>
                      </Accordion>
                    ))}
                  </Box>
                )}
              </Paper>
            )}
          </Grid>

          {/* Right Panel - Execution Controls & Logs */}
          <Grid item xs={12} md={5}>
            {/* Execution Control Card */}
            <Card
              sx={{
                mb: 3,
                background: running
                  ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
                  : 'linear-gradient(135deg, #2e7d32 0%, #4caf50 100%)',
                color: 'white',
              }}
            >
              <CardContent>
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                  Autonomous Execution
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                  <CheckCircle />
                  <Box>
                    <Typography variant="body2" sx={{ opacity: 0.9 }}>
                      {testType === 'traditional' ? 'Selected Tests' : 'Selected Feature'}
                    </Typography>
                    <Typography variant="h4" sx={{ fontWeight: 700 }}>
                      {testType === 'traditional'
                        ? selectedTraditionalTests.length
                        : selectedGherkinFeature ? 1 : 0}
                    </Typography>
                  </Box>
                </Box>
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <Button
                    fullWidth
                    variant="contained"
                    size="large"
                    startIcon={running ? <HourglassEmpty /> : <PlayArrow />}
                    onClick={handleRunTests}
                    disabled={running || (
                      testType === 'traditional'
                        ? selectedTraditionalTests.length === 0
                        : !selectedGherkinFeature
                    )}
                    sx={{
                      bgcolor: 'rgba(255,255,255,0.2)',
                      color: 'white',
                      '&:hover': { bgcolor: 'rgba(255,255,255,0.3)' },
                    }}
                  >
                    {running ? 'Running...' : 'Start Autonomous Run'}
                  </Button>
                  {running && (
                    <Button
                      variant="contained"
                      size="large"
                      startIcon={<Stop />}
                      onClick={handleStopTests}
                      sx={{
                        bgcolor: 'rgba(244,67,54,0.8)',
                        color: 'white',
                        minWidth: '120px',
                        '&:hover': { bgcolor: 'rgba(244,67,54,1)' },
                      }}
                    >
                      Stop
                    </Button>
                  )}
                </Box>
              </CardContent>
            </Card>

            {/* Execution Options */}
            <Paper sx={{ p: 3, mb: 3 }}>
              <Box
                sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }}
                onClick={() => setShowAdvanced(!showAdvanced)}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Settings />
                  <Typography variant="h6" sx={{ fontWeight: 600 }}>
                    Execution Options
                  </Typography>
                </Box>
                {showAdvanced ? <ExpandLess /> : <ExpandMore />}
              </Box>

              <Box sx={{ mt: 2 }}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={headless}
                      onChange={(e) => setHeadless(e.target.checked)}
                      disabled={running}
                    />
                  }
                  label="Headless Mode"
                />
              </Box>

              <Collapse in={showAdvanced}>
                <Box sx={{ mt: 2 }}>
                  <Typography variant="subtitle2" sx={{ mb: 1 }}>Execution Mode</Typography>
                  <Chip
                    icon={<Psychology />}
                    label="Smart Mode"
                    color="primary"
                    variant="filled"
                  />
                  <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                    Brain-optimized: Uses learned knowledge first, AI only when needed
                  </Typography>
                </Box>
              </Collapse>
            </Paper>

            {/* Status Message */}
            {statusMessage && (
              <Alert
                severity={
                  statusMessage.includes('completed') || statusMessage.includes('success') ? 'success' :
                  statusMessage.includes('failed') || statusMessage.includes('error') ? 'error' : 'info'
                }
                sx={{ mb: 3 }}
                icon={running ? <CircularProgress size={20} /> : undefined}
              >
                {statusMessage}
              </Alert>
            )}

            {/* Collapsible Execution Logs */}
            <Paper sx={{ mb: 3 }}>
              <Box
                sx={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  p: 2,
                  cursor: 'pointer',
                  '&:hover': { bgcolor: 'action.hover' },
                }}
                onClick={() => setLogsExpanded(!logsExpanded)}
              >
                <Typography variant="h6" sx={{ fontWeight: 600 }}>
                  Execution Logs
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  {logs.length > 0 && (
                    <Chip label={`${logs.length} lines`} size="small" />
                  )}
                  {logsExpanded ? <ExpandLess /> : <ExpandMore />}
                </Box>
              </Box>

              <Collapse in={logsExpanded}>
                {running && <LinearProgress />}
                <Box
                  sx={{
                    height: 300,
                    overflowY: 'auto',
                    bgcolor: 'grey.900',
                    color: 'grey.100',
                    p: 2,
                    fontFamily: 'monospace',
                    fontSize: '0.75rem',
                  }}
                >
                  {logs.length === 0 ? (
                    <Typography variant="body2" sx={{ color: 'grey.500' }}>
                      Waiting for test execution...
                    </Typography>
                  ) : (
                    logs.map((log, index) => (
                      <Typography
                        key={index}
                        variant="body2"
                        sx={{
                          fontFamily: 'monospace',
                          mb: 0.5,
                          color: getLogColor(log),
                        }}
                      >
                        {log}
                      </Typography>
                    ))
                  )}
                  <div ref={logsEndRef} />
                </Box>
              </Collapse>
            </Paper>

            {/* Results Summary */}
            {result && (
              <Paper
                sx={{
                  p: 3,
                  background: result.summary.failed > 0
                    ? 'linear-gradient(135deg, #ffebee 0%, #fff 100%)'
                    : 'linear-gradient(135deg, #e8f5e9 0%, #fff 100%)',
                  border: '1px solid',
                  borderColor: result.summary.failed > 0 ? 'error.light' : 'success.light',
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                  {result.summary.failed > 0 ? (
                    <BugReport sx={{ color: 'error.main' }} />
                  ) : (
                    <CheckCircle sx={{ color: 'success.main' }} />
                  )}
                  <Typography variant="h6" sx={{ fontWeight: 600 }}>
                    Test Results
                  </Typography>
                  <Chip
                    label={result.summary.failed > 0 ? 'Failed' : 'Passed'}
                    color={result.summary.failed > 0 ? 'error' : 'success'}
                    size="small"
                    sx={{ ml: 'auto' }}
                  />
                </Box>

                <Grid container spacing={1.5}>
                  <Grid item xs={6}>
                    <Box
                      sx={{
                        textAlign: 'center',
                        p: 1.5,
                        bgcolor: 'success.main',
                        borderRadius: 2,
                        color: 'white',
                      }}
                    >
                      <Typography variant="h5" sx={{ fontWeight: 700 }}>
                        {result.summary.passed}
                      </Typography>
                      <Typography variant="caption" sx={{ opacity: 0.9 }}>
                        Passed
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={6}>
                    <Box
                      sx={{
                        textAlign: 'center',
                        p: 1.5,
                        bgcolor: result.summary.failed > 0 ? 'error.main' : 'grey.300',
                        borderRadius: 2,
                        color: result.summary.failed > 0 ? 'white' : 'text.secondary',
                      }}
                    >
                      <Typography variant="h5" sx={{ fontWeight: 700 }}>
                        {result.summary.failed}
                      </Typography>
                      <Typography variant="caption" sx={{ opacity: 0.9 }}>
                        Failed
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={6}>
                    <Box sx={{ textAlign: 'center', p: 1.5, bgcolor: 'grey.100', borderRadius: 2 }}>
                      <Typography variant="h6" sx={{ fontWeight: 700 }}>
                        {result.summary.pass_rate?.toFixed(0) || 0}%
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Pass Rate
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={6}>
                    <Box sx={{ textAlign: 'center', p: 1.5, bgcolor: 'grey.100', borderRadius: 2 }}>
                      <Typography variant="h6" sx={{ fontWeight: 700, color: '#667eea' }}>
                        {result.summary.ai_dependency_percent?.toFixed(0) || 0}%
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        AI Used
                      </Typography>
                    </Box>
                  </Grid>
                </Grid>

                <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
                  <Typography variant="caption" color="text.secondary">
                    Duration: {result.summary.duration_seconds?.toFixed(1) || 0}s
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    • {result.summary.new_selectors_learned || 0} selectors learned
                  </Typography>
                </Box>

                {result.report_id && !result.report_id.startsWith('autonomous_') && (
                  <Button
                    fullWidth
                    variant="contained"
                    sx={{
                      mt: 2,
                      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    }}
                    onClick={() => navigate(`/reports/${result.report_id}`)}
                  >
                    View Full Report
                  </Button>
                )}
              </Paper>
            )}

            {/* AI Capabilities */}
            <Paper sx={{ p: 3, mt: 3 }}>
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                Agent Capabilities
              </Typography>
              <List dense>
                <ListItem>
                  <ListItemIcon>
                    <AutoAwesome sx={{ color: '#667eea' }} />
                  </ListItemIcon>
                  <ListItemText
                    primary="Self-Healing"
                    secondary="Adapts when UI changes"
                  />
                </ListItem>
                <ListItem>
                  <ListItemIcon>
                    <School sx={{ color: '#667eea' }} />
                  </ListItemIcon>
                  <ListItemText
                    primary="Continuous Learning"
                    secondary="Reduces AI dependency over time"
                  />
                </ListItem>
                <ListItem>
                  <ListItemIcon>
                    <BugReport sx={{ color: '#667eea' }} />
                  </ListItemIcon>
                  <ListItemText
                    primary="Smart Recovery"
                    secondary="Handles errors gracefully"
                  />
                </ListItem>
                <ListItem>
                  <ListItemIcon>
                    <Timer sx={{ color: '#667eea' }} />
                  </ListItemIcon>
                  <ListItemText
                    primary="SPA Support"
                    secondary="React, Angular, Vue, and more"
                  />
                </ListItem>
              </List>
            </Paper>
          </Grid>
        </Grid>
      )}

      {/* Edit Gherkin Steps Dialog */}
      <Dialog
        open={editDialogOpen}
        onClose={handleCloseEditDialog}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <EditIcon sx={{ color: '#667eea' }} />
            <Typography variant="h6">
              Edit Steps: {editingFeature?.scenarios?.[editingScenarioIndex]?.name || 'Scenario'}
            </Typography>
          </Box>
          <IconButton onClick={handleCloseEditDialog} size="small">
            <Close />
          </IconButton>
        </DialogTitle>
        <DialogContent dividers>
          <Box sx={{ mb: 2 }}>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Edit the Gherkin steps below. Each step should have a keyword (Given, When, Then, And) and the step text.
            </Typography>
          </Box>
          {editedSteps.map((step, index) => (
            <Box key={index} sx={{ display: 'flex', gap: 1, mb: 2, alignItems: 'flex-start' }}>
              <FormControl size="small" sx={{ minWidth: 100 }}>
                <Select
                  value={step.keyword || 'And'}
                  onChange={(e) => handleStepChange(index, 'keyword', e.target.value)}
                >
                  <MenuItem value="Given">Given</MenuItem>
                  <MenuItem value="When">When</MenuItem>
                  <MenuItem value="Then">Then</MenuItem>
                  <MenuItem value="And">And</MenuItem>
                  <MenuItem value="But">But</MenuItem>
                </Select>
              </FormControl>
              <TextField
                fullWidth
                size="small"
                value={step.text || ''}
                onChange={(e) => handleStepChange(index, 'text', e.target.value)}
                placeholder="Step description..."
                multiline
                maxRows={3}
              />
              <IconButton
                size="small"
                onClick={() => handleDeleteStep(index)}
                color="error"
              >
                <Delete />
              </IconButton>
            </Box>
          ))}
          <Button
            startIcon={<Add />}
            onClick={handleAddStep}
            variant="outlined"
            size="small"
            sx={{ mt: 1 }}
          >
            Add Step
          </Button>
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button onClick={handleCloseEditDialog} disabled={savingFeature}>
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={handleSaveFeature}
            disabled={savingFeature}
            startIcon={savingFeature ? <CircularProgress size={16} /> : <Save />}
            sx={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}
          >
            {savingFeature ? 'Saving...' : 'Save Changes'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={handleCloseSnackbar}
          severity={snackbar.severity}
          variant="filled"
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}
