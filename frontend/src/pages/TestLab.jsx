/**
 * Test Lab - Unified interface for running and generating tests
 * Combines the functionality of TestRunner and AITestGenerator into a single,
 * user-friendly wizard-style interface.
 */

import { useState, useEffect, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Box,
  Button,
  Typography,
  Paper,
  Grid,
  Card,
  CardContent,
  CardActionArea,
  Stepper,
  Step,
  StepLabel,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Alert,
  LinearProgress,
  Divider,
  IconButton,
  Tooltip,
  alpha,
  Fade,
  Collapse,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Checkbox,
  TextField,
  InputAdornment,
  Switch,
  FormControlLabel,
} from '@mui/material';
import {
  Science,
  PlayArrow,
  AutoAwesome,
  FolderOpen,
  CheckCircle,
  RadioButtonUnchecked,
  ArrowBack,
  ArrowForward,
  Refresh,
  Search,
  ExpandMore,
  ExpandLess,
  Description,
  Code,
  BugReport,
  Speed,
  CloudUpload,
  Stop,
} from '@mui/icons-material';
import axios from 'axios';

const steps = ['Select Project', 'Choose Tests', 'Run Tests'];

// Helper to get auth headers
const getAuthHeaders = () => {
  const token = localStorage.getItem('auth_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
};

export default function TestLab() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  // Stepper state
  const [activeStep, setActiveStep] = useState(0);

  // Project selection
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState(null);
  const [loadingProjects, setLoadingProjects] = useState(true);

  // Test selection
  const [testMode, setTestMode] = useState(null); // 'existing' or 'generate'
  const [features, setFeatures] = useState([]);
  const [selectedFeature, setSelectedFeature] = useState(null);
  const [selectedScenarios, setSelectedScenarios] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedFeatures, setExpandedFeatures] = useState({});
  const [traditionalSuites, setTraditionalSuites] = useState([]);
  const [actionTests, setActionTests] = useState([]);
  const [loadingTests, setLoadingTests] = useState(false);

  // Execution state
  const [running, setRunning] = useState(false);
  const [logs, setLogs] = useState([]);
  const [result, setResult] = useState(null);
  const [headless, setHeadless] = useState(false);
  
  // WebSocket for live logs
  const wsRef = useRef(null);
  const logsEndRef = useRef(null);

  // Auto-scroll logs
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  // WebSocket connection for live logs
  useEffect(() => {
    if (running) {
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${wsProtocol}//${window.location.hostname}:8000/ws/logs`;
      
      wsRef.current = new WebSocket(wsUrl);
      
      wsRef.current.onopen = () => {
        console.log('WebSocket connected for live logs');
        setLogs(prev => [...prev, '[Connected] Live log stream started...']);
      };
      
      wsRef.current.onmessage = (event) => {
        const message = event.data;
        setLogs(prev => [...prev, message]);
      };
      
      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
      
      wsRef.current.onclose = () => {
        console.log('WebSocket closed');
      };
      
      return () => {
        if (wsRef.current) {
          wsRef.current.close();
        }
      };
    }
  }, [running]);

  // Load projects on mount
  useEffect(() => {
    loadProjects();
  }, []);

  // Check URL params for pre-selected project
  useEffect(() => {
    const projectId = searchParams.get('projectId');
    if (projectId && projects.length > 0) {
      const project = projects.find(p => p.id === projectId);
      if (project) {
        setSelectedProject(project);
        setActiveStep(1);
      }
    }
  }, [searchParams, projects]);

  const loadProjects = async () => {
    try {
      const response = await axios.get('/api/projects', { headers: getAuthHeaders() });
      setProjects(response.data || []);
    } catch (error) {
      console.error('Failed to load projects:', error);
    } finally {
      setLoadingProjects(false);
    }
  };

  const loadFeatures = async (projectId) => {
    setLoadingTests(true);
    try {
      // Load all test types in parallel
      const [featuresRes, suitesRes] = await Promise.all([
        axios.get(`/api/projects/${projectId}/gherkin-features`, { headers: getAuthHeaders() }).catch(() => ({ data: { features: [] } })),
        axios.get(`/api/projects/${projectId}/traditional-suites`, { headers: getAuthHeaders() }).catch(() => ({ data: { suites: [] } }))
      ]);

      // Gherkin features
      const featureData = Array.isArray(featuresRes.data) ? featuresRes.data : featuresRes.data?.features || [];
      setFeatures(featureData);

      // Traditional suites
      const suitesData = Array.isArray(suitesRes.data) ? suitesRes.data : suitesRes.data?.suites || [];
      setTraditionalSuites(suitesData);

      // Action-based tests from project
      const project = projects.find(p => p.id === projectId);
      setActionTests(project?.test_cases || []);

    } catch (error) {
      console.error('Failed to load tests:', error);
      setFeatures([]);
      setTraditionalSuites([]);
      setActionTests([]);
    } finally {
      setLoadingTests(false);
    }
  };

  const handleProjectSelect = (project) => {
    setSelectedProject(project);
    loadFeatures(project.id);
    setActiveStep(1);
  };

  const handleNext = () => {
    if (activeStep === 1 && selectedScenarios.length === 0) {
      return; // Don't proceed without selected tests
    }
    setActiveStep((prev) => Math.min(prev + 1, steps.length - 1));
  };

  const handleBack = () => {
    setActiveStep((prev) => Math.max(prev - 1, 0));
  };

  const toggleFeatureExpand = (featureId) => {
    setExpandedFeatures(prev => ({
      ...prev,
      [featureId]: !prev[featureId]
    }));
  };

  const handleScenarioToggle = (scenarioId) => {
    setSelectedScenarios(prev =>
      prev.includes(scenarioId)
        ? prev.filter(id => id !== scenarioId)
        : [...prev, scenarioId]
    );
  };

  const handleSelectAllFromFeature = (feature) => {
    const scenarioIds = feature.scenarios?.map(s => s.id || s.name) || [];
    const allSelected = scenarioIds.every(id => selectedScenarios.includes(id));

    if (allSelected) {
      setSelectedScenarios(prev => prev.filter(id => !scenarioIds.includes(id)));
    } else {
      setSelectedScenarios(prev => [...new Set([...prev, ...scenarioIds])]);
    }
  };

  const handleStopExecution = async (force = false) => {
    try {
      const response = await axios.post('/api/execution/stop', null, {
        params: { force },
        headers: getAuthHeaders()
      });
      setLogs(prev => [...prev, `[STOP] ${response.data.message}`]);
      if (force) {
        setRunning(false);
      }
    } catch (error) {
      console.error('Failed to stop execution:', error);
      setLogs(prev => [...prev, `[ERROR] Failed to stop: ${error.message}`]);
    }
  };

  const handleRunTests = async () => {
    if (!selectedProject || selectedScenarios.length === 0) return;

    setRunning(true);
    setLogs([]);
    setResult(null);
    setActiveStep(2);

    try {
      // Find the feature that contains our selected scenarios
      const feature = features.find(f =>
        f.scenarios?.some(s => selectedScenarios.includes(s.id || s.name))
      );

      if (!feature) {
        throw new Error('No feature found for selected scenarios');
      }

      // Get scenario names for filtering
      const scenarioNames = feature.scenarios
        ?.filter(s => selectedScenarios.includes(s.id || s.name))
        .map(s => s.name) || [];

      const response = await axios.post('/api/gherkin/run-autonomous', {
        feature_id: feature.id,
        project_id: selectedProject.id,
        headless: headless,
        scenario_filter: scenarioNames
      }, { headers: getAuthHeaders() });

      if (response.data?.report_id) {
        // Poll for results
        pollForResults(response.data.report_id);
      } else if (response.data?.status === 'completed') {
        // Direct result
        setResult(response.data);
        setRunning(false);
      }
    } catch (error) {
      console.error('Failed to run tests:', error);
      setLogs(prev => [...prev, `Error: ${error.message}`]);
      setRunning(false);
    }
  };

  const pollForResults = async (reportId, attempts = 0) => {
    if (attempts > 120) {
      setLogs(prev => [...prev, 'Timeout waiting for results']);
      setRunning(false);
      return;
    }

    try {
      const response = await axios.get(`/api/reports/${reportId}`, { headers: getAuthHeaders() });
      if (response.data) {
        setResult(response.data);
        setRunning(false);
        return;
      }
    } catch (error) {
      // Report not ready yet
    }

    setTimeout(() => pollForResults(reportId, attempts + 1), 2000);
  };

  const renderProjectSelection = () => (
    <Fade in={activeStep === 0}>
      <Box>
        <Typography variant="h5" sx={{ fontWeight: 600, mb: 1 }}>
          Select a Project
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
          Choose a project to run tests against
        </Typography>

        {loadingProjects ? (
          <LinearProgress />
        ) : projects.length === 0 ? (
          <Alert severity="info" sx={{ borderRadius: 2 }}>
            No projects found. Create a project first to run tests.
            <Button size="small" onClick={() => navigate('/projects')} sx={{ ml: 2 }}>
              Go to Projects
            </Button>
          </Alert>
        ) : (
          <Grid container spacing={2}>
            {projects.map((project) => (
              <Grid item xs={12} sm={6} md={4} key={project.id}>
                <Card
                  sx={{
                    height: '100%',
                    border: selectedProject?.id === project.id ? '2px solid' : '1px solid',
                    borderColor: selectedProject?.id === project.id ? 'primary.main' : 'divider',
                    transition: 'all 0.2s',
                    '&:hover': {
                      borderColor: 'primary.main',
                      transform: 'translateY(-2px)',
                      boxShadow: 2,
                    },
                  }}
                >
                  <CardActionArea onClick={() => handleProjectSelect(project)} sx={{ height: '100%', p: 2 }}>
                    <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2 }}>
                      <Box
                        sx={{
                          width: 48,
                          height: 48,
                          borderRadius: 2,
                          backgroundColor: alpha('#667eea', 0.1),
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                        }}
                      >
                        <FolderOpen sx={{ color: '#667eea' }} />
                      </Box>
                      <Box sx={{ flex: 1 }}>
                        <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                          {project.name}
                        </Typography>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                          {project.description || 'No description'}
                        </Typography>
                        <Chip
                          size="small"
                          label={`${project.test_cases?.length || 0} tests`}
                          sx={{ height: 22 }}
                        />
                      </Box>
                      {selectedProject?.id === project.id && (
                        <CheckCircle color="primary" />
                      )}
                    </Box>
                  </CardActionArea>
                </Card>
              </Grid>
            ))}
          </Grid>
        )}
      </Box>
    </Fade>
  );

  const renderTestSelection = () => (
    <Fade in={activeStep === 1}>
      <Box>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
          <Box>
            <Typography variant="h5" sx={{ fontWeight: 600, mb: 0.5 }}>
              Choose Tests to Run
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Project: <strong>{selectedProject?.name}</strong>
            </Typography>
          </Box>
          <Chip
            label={`${selectedScenarios.length} selected`}
            color={selectedScenarios.length > 0 ? 'primary' : 'default'}
          />
        </Box>

        {/* Search */}
        <TextField
          fullWidth
          placeholder="Search tests..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          sx={{ mb: 3 }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <Search color="action" />
              </InputAdornment>
            ),
          }}
        />

        {/* Features List */}
        {features.length === 0 ? (
          <Alert severity="info" sx={{ borderRadius: 2 }}>
            No test features found for this project. Generate tests first using the AI Generator.
            <Button size="small" onClick={() => navigate(`/generate?projectId=${selectedProject?.id}`)} sx={{ ml: 2 }}>
              Generate Tests
            </Button>
          </Alert>
        ) : (
          <List sx={{ bgcolor: 'background.paper', borderRadius: 2, border: '1px solid', borderColor: 'divider' }}>
            {features.map((feature, idx) => {
              const isExpanded = expandedFeatures[feature.id || idx];
              const scenarios = feature.scenarios || [];
              const filteredScenarios = scenarios.filter(s =>
                s.name?.toLowerCase().includes(searchQuery.toLowerCase())
              );
              const selectedCount = scenarios.filter(s =>
                selectedScenarios.includes(s.id || s.name)
              ).length;

              return (
                <Box key={feature.id || idx}>
                  {idx > 0 && <Divider />}
                  <ListItem
                    sx={{ py: 2 }}
                    secondaryAction={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Chip
                          size="small"
                          label={`${selectedCount}/${scenarios.length}`}
                          color={selectedCount > 0 ? 'primary' : 'default'}
                          variant={selectedCount > 0 ? 'filled' : 'outlined'}
                        />
                        <IconButton onClick={() => toggleFeatureExpand(feature.id || idx)}>
                          {isExpanded ? <ExpandLess /> : <ExpandMore />}
                        </IconButton>
                      </Box>
                    }
                  >
                    <ListItemIcon>
                      <Checkbox
                        edge="start"
                        checked={selectedCount === scenarios.length && scenarios.length > 0}
                        indeterminate={selectedCount > 0 && selectedCount < scenarios.length}
                        onChange={() => handleSelectAllFromFeature(feature)}
                      />
                    </ListItemIcon>
                    <ListItemText
                      primary={feature.name || feature.feature_name || 'Unnamed Feature'}
                      secondary={`${scenarios.length} scenarios`}
                      primaryTypographyProps={{ fontWeight: 600 }}
                    />
                  </ListItem>
                  <Collapse in={isExpanded}>
                    <List sx={{ pl: 4, bgcolor: alpha('#000', 0.02) }}>
                      {filteredScenarios.map((scenario, sIdx) => (
                        <ListItem key={scenario.id || sIdx} dense>
                          <ListItemIcon>
                            <Checkbox
                              edge="start"
                              checked={selectedScenarios.includes(scenario.id || scenario.name)}
                              onChange={() => handleScenarioToggle(scenario.id || scenario.name)}
                            />
                          </ListItemIcon>
                          <ListItemText
                            primary={scenario.name}
                            secondary={`${scenario.steps?.length || 0} steps`}
                          />
                        </ListItem>
                      ))}
                    </List>
                  </Collapse>
                </Box>
              );
            })}
          </List>
        )}
      </Box>
    </Fade>
  );

  const renderExecution = () => (
    <Fade in={activeStep === 2}>
      <Box>
        <Typography variant="h5" sx={{ fontWeight: 600, mb: 3 }}>
          {running ? 'Running Tests...' : result ? 'Test Results' : 'Ready to Run'}
        </Typography>

        {running && (
          <Box sx={{ mb: 4 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
              <Box sx={{ flex: 1, mr: 2 }}>
                <LinearProgress sx={{ borderRadius: 1 }} />
              </Box>
              <Box sx={{ display: 'flex', gap: 1 }}>
                <Button
                  variant="outlined"
                  color="warning"
                  size="small"
                  startIcon={<Stop />}
                  onClick={() => handleStopExecution(false)}
                >
                  Stop After Current
                </Button>
                <Button
                  variant="contained"
                  color="error"
                  size="small"
                  startIcon={<Stop />}
                  onClick={() => handleStopExecution(true)}
                >
                  Force Stop
                </Button>
              </Box>
            </Box>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Executing {selectedScenarios.length} test(s)...
            </Typography>
            
            {/* Live Logs */}
            <Paper 
              sx={{ 
                p: 2, 
                bgcolor: '#1a1a2e', 
                borderRadius: 2,
                maxHeight: 300,
                overflow: 'auto',
                fontFamily: 'monospace',
              }}
            >
              <Typography variant="caption" sx={{ color: '#888', mb: 1, display: 'block' }}>
                Live Execution Logs
              </Typography>
              {logs.map((log, idx) => (
                <Typography 
                  key={idx} 
                  variant="body2" 
                  sx={{ 
                    color: log.includes('Error') || log.includes('FAIL') ? '#ef4444' : 
                           log.includes('PASS') || log.includes('Success') ? '#22c55e' : 
                           log.includes('[') ? '#667eea' : '#e0e0e0',
                    fontSize: '0.8rem',
                    lineHeight: 1.6,
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                  }}
                >
                  {log}
                </Typography>
              ))}
              <div ref={logsEndRef} />
            </Paper>
          </Box>
        )}

        {result && (
          <Grid container spacing={3} sx={{ mb: 4 }}>
            <Grid item xs={12} sm={4}>
              <Paper sx={{ p: 3, textAlign: 'center', bgcolor: alpha('#22c55e', 0.1), borderRadius: 2 }}>
                <Typography variant="h3" sx={{ fontWeight: 700, color: '#22c55e' }}>
                  {result.passed || 0}
                </Typography>
                <Typography variant="body2" color="text.secondary">Passed</Typography>
              </Paper>
            </Grid>
            <Grid item xs={12} sm={4}>
              <Paper sx={{ p: 3, textAlign: 'center', bgcolor: alpha('#ef4444', 0.1), borderRadius: 2 }}>
                <Typography variant="h3" sx={{ fontWeight: 700, color: '#ef4444' }}>
                  {result.failed || 0}
                </Typography>
                <Typography variant="body2" color="text.secondary">Failed</Typography>
              </Paper>
            </Grid>
            <Grid item xs={12} sm={4}>
              <Paper sx={{ p: 3, textAlign: 'center', bgcolor: alpha('#667eea', 0.1), borderRadius: 2 }}>
                <Typography variant="h3" sx={{ fontWeight: 700, color: '#667eea' }}>
                  {((result.passed / (result.total_tests || 1)) * 100).toFixed(0)}%
                </Typography>
                <Typography variant="body2" color="text.secondary">Pass Rate</Typography>
              </Paper>
            </Grid>
          </Grid>
        )}

        {result && (
          <Box sx={{ display: 'flex', gap: 2 }}>
            <Button
              variant="contained"
              onClick={() => navigate(`/reports/${result.id}`)}
              startIcon={<Description />}
            >
              View Full Report
            </Button>
            <Button
              variant="outlined"
              onClick={() => {
                setActiveStep(1);
                setResult(null);
              }}
              startIcon={<Refresh />}
            >
              Run More Tests
            </Button>
          </Box>
        )}

        {!running && !result && (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <Science sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
            <Typography variant="h6" sx={{ mb: 1 }}>Ready to execute {selectedScenarios.length} test(s)</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Click "Run Tests" to start the autonomous test execution
            </Typography>
            
            {/* Headless Toggle */}
            <Box sx={{ mb: 3, display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 2 }}>
              <FormControlLabel
                control={
                  <Switch
                    checked={!headless}
                    onChange={(e) => setHeadless(!e.target.checked)}
                    color="primary"
                  />
                }
                label={
                  <Typography variant="body2" color="text.secondary">
                    {headless ? 'Browser Hidden (Headless)' : 'Browser Visible'}
                  </Typography>
                }
              />
            </Box>
            
            <Button
              variant="contained"
              size="large"
              startIcon={<PlayArrow />}
              onClick={handleRunTests}
              sx={{
                px: 4,
                py: 1.5,
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              }}
            >
              Run Tests
            </Button>
          </Box>
        )}
      </Box>
    </Fade>
  );

  return (
    <Box>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
          Test Lab
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Run existing tests or generate new ones with AI
        </Typography>
      </Box>

      {/* Stepper */}
      <Paper sx={{ p: 3, mb: 4, borderRadius: 2 }}>
        <Stepper activeStep={activeStep} alternativeLabel>
          {steps.map((label, index) => (
            <Step key={label} completed={index < activeStep}>
              <StepLabel>{label}</StepLabel>
            </Step>
          ))}
        </Stepper>
      </Paper>

      {/* Content */}
      <Paper sx={{ p: 4, borderRadius: 2, minHeight: 400 }}>
        {activeStep === 0 && renderProjectSelection()}
        {activeStep === 1 && renderTestSelection()}
        {activeStep === 2 && renderExecution()}
      </Paper>

      {/* Navigation Buttons */}
      {!running && (
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 3 }}>
          <Button
            variant="outlined"
            onClick={handleBack}
            startIcon={<ArrowBack />}
            disabled={activeStep === 0}
          >
            Back
          </Button>
          {activeStep < 2 && (
            <Button
              variant="contained"
              onClick={activeStep === 1 ? handleRunTests : handleNext}
              endIcon={activeStep === 1 ? <PlayArrow /> : <ArrowForward />}
              disabled={activeStep === 0 ? !selectedProject : selectedScenarios.length === 0}
              sx={{
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              }}
            >
              {activeStep === 1 ? 'Run Tests' : 'Next'}
            </Button>
          )}
        </Box>
      )}
    </Box>
  );
}
