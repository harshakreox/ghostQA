import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
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
  Breadcrumbs,
  Link,
  Chip,
  Switch,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Divider,
  CircularProgress,
  Tabs,
  Tab,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Snackbar,
} from '@mui/material';
import {
  PlayArrow,
  Stop,
  CheckCircle,
  NavigateNext,
  Code,
  HourglassEmpty,
  Psychology,
  AutoAwesome,
  ExpandMore,
  Timer,
  BugReport,
  School,
  Memory,
  TrendingDown,
} from '@mui/icons-material';
import axios from 'axios';

export default function RunTests() {
  const { id } = useParams();
  const navigate = useNavigate();
  
  // Tab state
  const [activeTab, setActiveTab] = useState(0); // 0 = Traditional, 1 = AI
  
  // Traditional test state
  const [project, setProject] = useState(null);
  const [selectedTests, setSelectedTests] = useState([]);
  const [headless, setHeadless] = useState(false);
  const [running, setRunning] = useState(false);
  const [logs, setLogs] = useState([]);
  const [ws, setWs] = useState(null);
  const [statusMessage, setStatusMessage] = useState('');
  
  // AI test state
  const [gherkinFeatures, setGherkinFeatures] = useState([]);
  const [selectedFeature, setSelectedFeature] = useState(null);
  const [aiRunning, setAiRunning] = useState(false);
  const [aiHeadless, setAiHeadless] = useState(false);
  const [aiResult, setAiResult] = useState(null);
  const [showAiResults, setShowAiResults] = useState(false);
  const [aiError, setAiError] = useState(null);
  const [aiLogs, setAiLogs] = useState([]);
  const [aiStatusMessage, setAiStatusMessage] = useState('');
  const [learningStats, setLearningStats] = useState(null);

  // Snackbar state for notifications
  const [snackbar, setSnackbar] = useState({
    open: false,
    message: '',
    severity: 'success'
  });

  const showNotification = (message, severity = 'success') => {
    setSnackbar({ open: true, message, severity });
  };

  const handleCloseSnackbar = () => {
    setSnackbar({ ...snackbar, open: false });
  };

  // Get WebSocket URL dynamically based on current host
  const getWebSocketUrl = () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.hostname;
    const port = '8000'; // Backend port
    return `${protocol}//${host}:${port}/ws/logs`;
  };

  useEffect(() => {
    loadProject();
    loadGherkinFeatures();
    loadLearningStats();
    return () => {
      if (ws) ws.close();
    };
  }, [id]);

  const loadLearningStats = async () => {
    try {
      const response = await axios.get('/api/agent/metrics/ai-dependency');
      setLearningStats(response.data);
    } catch (error) {
      console.error('Error loading learning stats:', error);
    }
  };

  const loadProject = async () => {
    try {
      const response = await axios.get(`/api/projects/${id}`);
      setProject(response.data);
      // Select all tests by default
      setSelectedTests(response.data.test_cases.map((tc) => tc.id));
    } catch (error) {
      console.error('Error loading project:', error);
    }
  };

  const loadGherkinFeatures = async () => {
    try {
      console.log('🔍 Loading Gherkin features for project:', id);
      const response = await axios.get(`/api/projects/${id}/gherkin-features`);
      console.log('📦 API Response:', response.data);
      console.log('📦 Response type:', typeof response.data);
      console.log('📦 Is Array?', Array.isArray(response.data));
      
      // Handle both formats: direct array OR object with features property
      let features;
      if (Array.isArray(response.data)) {
        features = response.data;
      } else if (response.data && Array.isArray(response.data.features)) {
        // Backend returning {features: [...]}
        features = response.data.features;
        console.log('📦 Extracted features from object wrapper');
      } else {
        features = [];
      }
      
      console.log('✅ Processed features:', features);
      console.log('✅ Feature count:', features.length);
      
      setGherkinFeatures(features);
    } catch (error) {
      console.error('❌ Error loading Gherkin features:', error);
      console.error('❌ Error details:', error.response?.data);
      setGherkinFeatures([]);
    }
  };

  // ==================== TRADITIONAL TEST HANDLERS ====================
  
  const handleToggleTest = (testId) => {
    setSelectedTests((prev) =>
      prev.includes(testId) ? prev.filter((id) => id !== testId) : [...prev, testId]
    );
  };

  const handleSelectAll = () => {
    if (selectedTests.length === project.test_cases.length) {
      setSelectedTests([]);
    } else {
      setSelectedTests(project.test_cases.map((tc) => tc.id));
    }
  };

  const pollForReport = async (reportId, maxAttempts = 60) => {
    setStatusMessage('⏳ Waiting for test execution to complete...');
    
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      try {
        const response = await axios.get(`/api/reports/${reportId}`);
        if (response.data) {
          setStatusMessage('✅ Tests completed! Navigating to report...');
          setRunning(false);
          if (ws) ws.close();
          
          setTimeout(() => {
            navigate(`/reports/${reportId}`);
          }, 1000);
          return;
        }
      } catch (error) {
        setStatusMessage(`⏳ Tests running... (${attempt * 2}s elapsed)`);
        await new Promise(resolve => setTimeout(resolve, 2000));
      }
    }
    
    setStatusMessage('⚠️ Timeout: Tests took longer than expected. Check backend logs.');
    setRunning(false);
    if (ws) ws.close();
  };

  const handleRunTests = async () => {
    if (selectedTests.length === 0) {
      showNotification('Please select at least one test case', 'warning');
      return;
    }

    setRunning(true);
    setLogs([]);
    setStatusMessage('🚀 Starting test execution...');

    const wsUrl = getWebSocketUrl();
    const websocket = new WebSocket(wsUrl);

    websocket.onopen = () => {
      console.log('WebSocket connected');
      setLogs((prev) => [...prev, '🔗 Connected to test runner...']);
    };

    websocket.onmessage = (event) => {
      setLogs((prev) => [...prev, event.data]);
    };

    websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
      setLogs((prev) => [...prev, '⚠️ WebSocket connection error']);
    };

    websocket.onclose = (event) => {
      console.log('WebSocket closed:', event.code, event.reason);
      if (!event.wasClean) {
        setLogs((prev) => [...prev, '⚠️ Connection closed unexpectedly']);
      }
    };

    setWs(websocket);

    try {
      const response = await axios.post('/api/run-tests', {
        project_id: id,
        test_case_ids: selectedTests,
        headless: headless,
      });

      const reportId = response.data.report_id;
      setStatusMessage('✅ Test execution started! Waiting for completion...');

      await pollForReport(reportId);

    } catch (error) {
      console.error('Error running tests:', error);
      setStatusMessage('❌ Error starting tests. Check backend logs.');
      showNotification('Failed to start tests. Check backend logs.', 'error');
      setRunning(false);
      if (websocket) websocket.close();
    }
  };

  // ==================== AI TEST HANDLERS ====================
  
  const addAiLog = (message) => {
    const timestamp = new Date().toLocaleTimeString();
    const logMessage = `[${timestamp}] ${message}`;
    setAiLogs(prev => [...prev, logMessage]);
    console.log(logMessage);
  };
  
  const handleRunAiTest = async (feature) => {
    setAiRunning(true);
    setAiError(null);
    setAiResult(null);
    setSelectedFeature(feature);
    setAiLogs([]);
    setAiStatusMessage('Starting AI test execution...');

    try {
      addAiLog('Initializing AI test execution');
      addAiLog(`Feature: ${feature.name}`);
      addAiLog(`Scenarios: ${feature.scenario_count}`);
      addAiLog(`Mode: ${aiHeadless ? 'Headless' : 'Visible Browser'}`);
      addAiLog('');

      setAiStatusMessage('AI is analyzing the feature...');
      addAiLog('Connecting to autonomous agent...');

      // Use the unified agent API which has proper execution tracking
      const response = await axios.post('/api/agent/run', {
        project_id: id,
        project_name: project?.name || 'Test Project',
        base_url: project?.base_url || '',
        headless: aiHeadless,
        execution_mode: 'guided',
        feature_id: feature.id,  // The agent will load and convert this feature
      });

      addAiLog('AI execution completed!');
      addAiLog('');
      addAiLog(`Results:`);
      addAiLog(`   Total Tests: ${response.data.summary.total}`);
      addAiLog(`   Passed: ${response.data.summary.passed}`);
      addAiLog(`   Failed: ${response.data.summary.failed}`);
      addAiLog(`   Pass Rate: ${response.data.summary.pass_rate}%`);
      addAiLog(`   AI Dependency: ${response.data.summary.ai_dependency_percent}%`);
      addAiLog(`   Duration: ${response.data.summary.duration_seconds?.toFixed(2)}s`);

      setAiStatusMessage('AI test execution completed!');

      // Convert response to expected format
      setAiResult({
        total_scenarios: response.data.summary.total,
        passed: response.data.summary.passed,
        failed: response.data.summary.failed,
        total_duration: response.data.summary.duration_seconds || 0,
        ai_dependency_percent: response.data.summary.ai_dependency_percent,
        scenario_results: response.data.results?.map(r => ({
          scenario_name: r.test_name,
          status: r.status,
          duration: (r.duration_ms || 0) / 1000,
          error_message: r.error_message,
        })) || []
      });
      setShowAiResults(true);

    } catch (error) {
      console.error('AI test execution error:', error);
      const errorMsg = error.response?.data?.detail || error.message || 'AI execution failed';
      addAiLog('');
      addAiLog('ERROR: ' + errorMsg);
      setAiError(errorMsg);
      setAiStatusMessage('AI execution failed');
    } finally {
      setAiRunning(false);
    }
  };

  const handleStopAiTest = async () => {
    try {
      addAiLog('[SYSTEM] Requesting stop...');
      setAiStatusMessage('Stopping test execution...');

      const response = await axios.post('/api/agent/stop');

      if (response.data.success) {
        addAiLog('[SYSTEM] Stop signal sent - finishing current test');
        showNotification('Stop requested - finishing current test', 'info');
      } else {
        addAiLog(`[SYSTEM] ${response.data.message}`);
        showNotification(response.data.message, 'warning');
      }
    } catch (error) {
      console.error('Stop error:', error);
      addAiLog('[ERROR] Failed to stop execution');
      showNotification('Failed to stop execution', 'error');
    }
  };

  const handleCloseAiResults = () => {
    setShowAiResults(false);
    setAiResult(null);
    setSelectedFeature(null);
  };

  // ==================== RENDER ====================

  if (!project) {
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
          {project.name}
        </Link>
        <Typography color="text.primary">Run Tests</Typography>
      </Breadcrumbs>

      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" sx={{ fontWeight: 700, mb: 0.5 }}>
          Run Tests
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Choose between traditional test execution or AI-powered autonomous testing
        </Typography>
      </Box>

      {/* Tabs */}
      <Paper sx={{ mb: 3 }}>
        <Tabs 
          value={activeTab} 
          onChange={(e, newValue) => setActiveTab(newValue)}
          sx={{
            borderBottom: 1,
            borderColor: 'divider',
            '& .MuiTab-root': {
              textTransform: 'none',
              fontWeight: 600,
              fontSize: '1rem',
            }
          }}
        >
          <Tab 
            icon={<Code />} 
            iconPosition="start" 
            label="Traditional Tests"
            sx={{ minHeight: 64 }}
          />
          <Tab 
            icon={<Psychology />} 
            iconPosition="start" 
            label={
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                AI Tests
                <Chip 
                  label="BETA" 
                  size="small" 
                  sx={{ 
                    height: 20, 
                    fontSize: '0.65rem',
                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    color: 'white'
                  }} 
                />
              </Box>
            }
            sx={{ minHeight: 64 }}
          />
        </Tabs>
      </Paper>

      {/* Tab Panels */}
      {activeTab === 0 && (
        <TraditionalTestPanel
          project={project}
          selectedTests={selectedTests}
          handleToggleTest={handleToggleTest}
          handleSelectAll={handleSelectAll}
          headless={headless}
          setHeadless={setHeadless}
          running={running}
          handleRunTests={handleRunTests}
          statusMessage={statusMessage}
          logs={logs}
        />
      )}

      {activeTab === 1 && (
        <AiTestPanel
          gherkinFeatures={gherkinFeatures}
          aiHeadless={aiHeadless}
          setAiHeadless={setAiHeadless}
          aiRunning={aiRunning}
          handleRunAiTest={handleRunAiTest}
          handleStopAiTest={handleStopAiTest}
          aiError={aiError}
          aiLogs={aiLogs}
          aiStatusMessage={aiStatusMessage}
          learningStats={learningStats}
        />
      )}

      {/* AI Results Dialog */}
      <AiResultsDialog
        open={showAiResults}
        onClose={handleCloseAiResults}
        result={aiResult}
        featureName={selectedFeature?.name}
      />

      {/* Snackbar for notifications */}
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

// ==================== TRADITIONAL TEST PANEL ====================

function TraditionalTestPanel({ 
  project, 
  selectedTests, 
  handleToggleTest, 
  handleSelectAll, 
  headless, 
  setHeadless, 
  running, 
  handleRunTests, 
  statusMessage, 
  logs 
}) {
  return (
    <Box sx={{ display: 'flex', gap: 3 }}>
      {/* Left Panel - Test Selection */}
      <Box sx={{ flex: 1 }}>
        <Paper sx={{ p: 3, mb: 3 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              Select Test Cases
            </Typography>
            <Button size="small" onClick={handleSelectAll} disabled={running}>
              {selectedTests.length === project.test_cases.length ? 'Deselect All' : 'Select All'}
            </Button>
          </Box>
          <Divider sx={{ mb: 2 }} />

          {project.test_cases.length === 0 ? (
            <Alert severity="info">
              No test cases available. Create test cases first.
            </Alert>
          ) : (
            <List>
              {project.test_cases.map((testCase) => (
                <ListItem
                  key={testCase.id}
                  sx={{
                    borderRadius: 2,
                    mb: 1,
                    bgcolor: selectedTests.includes(testCase.id) ? 'action.selected' : 'transparent',
                    '&:hover': {
                      bgcolor: 'action.hover',
                    },
                  }}
                >
                  <ListItemIcon>
                    <Checkbox
                      checked={selectedTests.includes(testCase.id)}
                      onChange={() => handleToggleTest(testCase.id)}
                      disabled={running}
                    />
                  </ListItemIcon>
                  <ListItemText
                    primary={testCase.name}
                    secondary={`${testCase.actions.length} actions`}
                    primaryTypographyProps={{ fontWeight: 600 }}
                  />
                  <Chip
                    icon={<Code />}
                    label={testCase.actions.length}
                    size="small"
                    color="primary"
                  />
                </ListItem>
              ))}
            </List>
          )}
        </Paper>

        {/* Options */}
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
            Run Options
          </Typography>
          <FormControlLabel
            control={
              <Switch checked={headless} onChange={(e) => setHeadless(e.target.checked)} disabled={running} />
            }
            label="Headless Mode (Run in background)"
          />
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
            Headless mode runs tests faster without opening browser windows
          </Typography>
        </Paper>
      </Box>

      {/* Right Panel - Run Control & Logs */}
      <Box sx={{ width: 400 }}>
        {/* Run Control */}
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
              Test Execution
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
              <CheckCircle />
              <Box>
                <Typography variant="body2" sx={{ opacity: 0.9 }}>
                  Selected Tests
                </Typography>
                <Typography variant="h4" sx={{ fontWeight: 700 }}>
                  {selectedTests.length}
                </Typography>
              </Box>
            </Box>
            <Button
              fullWidth
              variant="contained"
              size="large"
              startIcon={running ? <HourglassEmpty /> : <PlayArrow />}
              onClick={handleRunTests}
              disabled={running || selectedTests.length === 0}
              sx={{
                bgcolor: 'rgba(255,255,255,0.2)',
                color: 'white',
                '&:hover': {
                  bgcolor: 'rgba(255,255,255,0.3)',
                },
                '&:disabled': {
                  bgcolor: 'rgba(255,255,255,0.1)',
                  color: 'rgba(255,255,255,0.5)',
                },
              }}
            >
              {running ? 'Running Tests...' : 'Start Test Run'}
            </Button>
          </CardContent>
        </Card>

        {/* Status Message */}
        {statusMessage && (
          <Alert 
            severity={
              statusMessage.includes('✅') ? 'success' :
              statusMessage.includes('❌') ? 'error' :
              statusMessage.includes('⚠️') ? 'warning' : 'info'
            }
            sx={{ mb: 3 }}
            icon={running ? <CircularProgress size={20} /> : undefined}
          >
            {statusMessage}
          </Alert>
        )}

        {/* Real-time Logs */}
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
            Execution Logs
          </Typography>
          {running && <LinearProgress sx={{ mb: 2 }} />}
          <Box
            sx={{
              height: 400,
              overflowY: 'auto',
              bgcolor: 'grey.900',
              color: 'grey.100',
              p: 2,
              borderRadius: 1,
              fontFamily: 'monospace',
              fontSize: '0.75rem',
            }}
          >
            {logs.length === 0 ? (
              <Typography variant="body2" sx={{ color: 'grey.500' }}>
                {running ? 'Connecting to test runner...' : 'Waiting for test execution...'}
              </Typography>
            ) : (
              logs.map((log, index) => (
                <Typography
                  key={index}
                  variant="body2"
                  sx={{
                    fontFamily: 'monospace',
                    mb: 0.5,
                    color: log.includes('✓') || log.includes('PASSED') || log.includes('✅')
                      ? 'success.light'
                      : log.includes('✗') || log.includes('FAILED') || log.includes('❌')
                      ? 'error.light'
                      : log.includes('⚠️')
                      ? 'warning.light'
                      : 'grey.100',
                  }}
                >
                  {log}
                </Typography>
              ))
            )}
          </Box>
        </Paper>
      </Box>
    </Box>
  );
}

// ==================== AI TEST PANEL ====================

function AiTestPanel({
  gherkinFeatures,
  aiHeadless,
  setAiHeadless,
  aiRunning,
  handleRunAiTest,
  handleStopAiTest,
  aiError,
  aiLogs,
  aiStatusMessage,
  learningStats
}) {
  // Ensure gherkinFeatures is always an array
  const features = Array.isArray(gherkinFeatures) ? gherkinFeatures : [];

  return (
    <Box sx={{ display: 'flex', gap: 3 }}>
      {/* Left Panel - Feature Selection */}
      <Box sx={{ flex: 1 }}>
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
            Gherkin Features
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Select a feature to execute with AI-powered autonomous testing
          </Typography>

          {features.length === 0 ? (
            <Alert severity="info" sx={{ mb: 2 }}>
              No Gherkin features available. Create BDD features using the AI Test Generator first.
              <Typography variant="caption" sx={{ display: 'block', mt: 1 }}>
                Check browser console (F12) for loading details.
              </Typography>
            </Alert>
          ) : (
            <Box>
              {features.map((feature) => (
                <Accordion 
                  key={feature.id}
                  sx={{ 
                    mb: 2,
                    '&:before': { display: 'none' },
                    boxShadow: 1
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
                      <Chip 
                        label={`${feature.scenario_count} scenarios`}
                        size="small"
                        color="primary"
                        variant="outlined"
                      />
                    </Box>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                      {feature.description || 'No description available'}
                    </Typography>
                    
                    <Divider sx={{ my: 2 }} />
                    
                    <Box sx={{ display: 'flex', gap: 1 }}>
                      <Button
                        fullWidth
                        variant="contained"
                        size="large"
                        startIcon={aiRunning ? <CircularProgress size={20} color="inherit" /> : <AutoAwesome />}
                        onClick={() => handleRunAiTest(feature)}
                        disabled={aiRunning}
                        sx={{
                          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                          color: 'white',
                          textTransform: 'none',
                          py: 1.5,
                          '&:hover': {
                            background: 'linear-gradient(135deg, #5568d3 0%, #65408a 100%)',
                          },
                          '&:disabled': {
                            background: 'linear-gradient(135deg, #999 0%, #666 100%)',
                            color: 'rgba(255,255,255,0.5)',
                          }
                        }}
                      >
                        {aiRunning ? 'AI Running...' : 'Run with AI'}
                      </Button>
                      {aiRunning && (
                        <Button
                          variant="contained"
                          size="large"
                          startIcon={<Stop />}
                          onClick={handleStopAiTest}
                          sx={{
                            bgcolor: 'error.main',
                            color: 'white',
                            minWidth: 100,
                            '&:hover': { bgcolor: 'error.dark' },
                          }}
                        >
                          Stop
                        </Button>
                      )}
                    </Box>
                  </AccordionDetails>
                </Accordion>
              ))}
            </Box>
          )}
        </Paper>
      </Box>

      {/* Right Panel - AI Info & Options */}
      <Box sx={{ width: 400 }}>
        {/* AI Info Card */}
        <Card
          sx={{
            mb: 3,
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            color: 'white',
          }}
        >
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
              <Psychology sx={{ fontSize: 40 }} />
              <Box>
                <Typography variant="h6" sx={{ fontWeight: 600 }}>
                  AI-Powered Testing
                </Typography>
                <Typography variant="body2" sx={{ opacity: 0.9 }}>
                  Autonomous test execution
                </Typography>
              </Box>
            </Box>
            
            <Alert 
              severity="info" 
              sx={{ 
                bgcolor: 'rgba(255,255,255,0.15)',
                color: 'white',
                '& .MuiAlert-icon': { color: 'white' }
              }}
            >
              AI interprets Gherkin steps and executes tests automatically - no step definitions needed!
            </Alert>
          </CardContent>
        </Card>

        {/* Learning Stats */}
        {learningStats && (
          <Paper sx={{ p: 2, mb: 3, background: 'linear-gradient(135deg, #667eea15 0%, #764ba215 100%)' }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 2 }}>
              AI Learning Status
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flex: 1, minWidth: 120 }}>
                <School sx={{ color: '#667eea', fontSize: 20 }} />
                <Box>
                  <Typography variant="caption" color="text.secondary">AI Dependency</Typography>
                  <Typography variant="body2" sx={{ fontWeight: 700 }}>
                    {learningStats.current_ai_dependency_percent?.toFixed(1) || 0}%
                  </Typography>
                </Box>
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flex: 1, minWidth: 120 }}>
                <Memory sx={{ color: '#667eea', fontSize: 20 }} />
                <Box>
                  <Typography variant="caption" color="text.secondary">Elements Known</Typography>
                  <Typography variant="body2" sx={{ fontWeight: 700 }}>
                    {learningStats.total_elements_known || 0}
                  </Typography>
                </Box>
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flex: 1, minWidth: 120 }}>
                <TrendingDown sx={{ color: '#4caf50', fontSize: 20 }} />
                <Box>
                  <Typography variant="caption" color="text.secondary">Patterns</Typography>
                  <Typography variant="body2" sx={{ fontWeight: 700 }}>
                    {learningStats.patterns_learned || 0}
                  </Typography>
                </Box>
              </Box>
            </Box>
            {learningStats.recommendation && (
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1.5 }}>
                {learningStats.recommendation}
              </Typography>
            )}
          </Paper>
        )}

        {/* AI Options */}
        <Paper sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
            AI Execution Options
          </Typography>
          <FormControlLabel
            control={
              <Switch 
                checked={aiHeadless} 
                onChange={(e) => setAiHeadless(e.target.checked)} 
                disabled={aiRunning} 
              />
            }
            label="Headless Mode"
          />
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
            Run AI tests in background (recommended for faster execution)
          </Typography>
        </Paper>

        {/* Error Display */}
        {aiError && (
          <Alert severity="error" sx={{ mb: 3 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 0.5 }}>
              AI Execution Failed
            </Typography>
            <Typography variant="body2">
              {aiError}
            </Typography>
          </Alert>
        )}

        {/* Status Message */}
        {aiStatusMessage && (
          <Alert 
            severity={
              aiStatusMessage.includes('✅') ? 'success' :
              aiStatusMessage.includes('❌') ? 'error' :
              aiStatusMessage.includes('⚠️') ? 'warning' : 'info'
            }
            sx={{ mb: 3 }}
            icon={aiRunning ? <CircularProgress size={20} /> : undefined}
          >
            {aiStatusMessage}
          </Alert>
        )}

        {/* Real-time AI Execution Logs */}
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
            AI Execution Logs
          </Typography>
          {aiRunning && <LinearProgress sx={{ mb: 2 }} />}
          <Box
            sx={{
              height: 400,
              overflowY: 'auto',
              bgcolor: 'grey.900',
              color: 'grey.100',
              p: 2,
              borderRadius: 1,
              fontFamily: 'monospace',
              fontSize: '0.75rem',
            }}
          >
            {aiLogs.length === 0 ? (
              <Typography variant="body2" sx={{ color: 'grey.500' }}>
                {aiRunning ? 'Initializing AI test execution...' : 'Waiting for AI test execution...'}
              </Typography>
            ) : (
              aiLogs.map((log, index) => (
                <Typography
                  key={index}
                  variant="body2"
                  sx={{
                    fontFamily: 'monospace',
                    mb: 0.5,
                    color: log.includes('✅') || log.includes('PASSED')
                      ? 'success.light'
                      : log.includes('❌') || log.includes('FAILED') || log.includes('ERROR')
                      ? 'error.light'
                      : log.includes('⚠️')
                      ? 'warning.light'
                      : log.includes('🤖') || log.includes('AI')
                      ? '#bb86fc'
                      : 'grey.100',
                  }}
                >
                  {log}
                </Typography>
              ))
            )}
          </Box>
        </Paper>

        {/* AI Features Info */}
        <Paper sx={{ p: 3, mt: 3 }}>
          <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
            ✨ AI Capabilities
          </Typography>
          <List dense>
            <ListItem>
              <ListItemIcon>
                <AutoAwesome sx={{ color: '#667eea' }} />
              </ListItemIcon>
              <ListItemText 
                primary="Interprets natural language"
                secondary="AI understands Gherkin steps"
              />
            </ListItem>
            <ListItem>
              <ListItemIcon>
                <BugReport sx={{ color: '#667eea' }} />
              </ListItemIcon>
              <ListItemText 
                primary="Self-healing selectors"
                secondary="Finds elements automatically"
              />
            </ListItem>
            <ListItem>
              <ListItemIcon>
                <Timer sx={{ color: '#667eea' }} />
              </ListItemIcon>
              <ListItemText 
                primary="Smart waiting"
                secondary="Adapts to page load times"
              />
            </ListItem>
          </List>
        </Paper>
      </Box>
    </Box>
  );
}

// ==================== AI RESULTS DIALOG ====================

function AiResultsDialog({ open, onClose, result, featureName }) {
  if (!result) return null;

  const getStatusColor = (status) => {
    switch (status) {
      case 'passed': return '#4caf50';
      case 'failed': return '#f44336';
      case 'skipped': return '#ff9800';
      default: return '#757575';
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Psychology sx={{ color: '#667eea' }} />
          <Typography variant="h6">AI Test Results</Typography>
        </Box>
      </DialogTitle>
      <DialogContent>
        <Typography variant="h6" gutterBottom>
          {featureName}
        </Typography>
        
        {/* Summary Stats */}
        <Box sx={{ display: 'flex', gap: 3, my: 3, p: 2, bgcolor: 'grey.50', borderRadius: 2 }}>
          <Box>
            <Typography variant="caption" color="text.secondary">Total</Typography>
            <Typography variant="h6" sx={{ fontWeight: 700 }}>
              {result.total_scenarios}
            </Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary">Passed</Typography>
            <Typography variant="h6" sx={{ fontWeight: 700, color: 'success.main' }}>
              {result.passed}
            </Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary">Failed</Typography>
            <Typography variant="h6" sx={{ fontWeight: 700, color: 'error.main' }}>
              {result.failed}
            </Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary">Duration</Typography>
            <Typography variant="h6" sx={{ fontWeight: 700 }}>
              {result.total_duration.toFixed(2)}s
            </Typography>
          </Box>
        </Box>

        {/* Scenario Results */}
        <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
          Scenario Results
        </Typography>
        {result.scenario_results.map((scenario, idx) => (
          <Accordion key={idx} sx={{ mb: 1 }}>
            <AccordionSummary expandIcon={<ExpandMore />}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: '100%' }}>
                <Box 
                  sx={{ 
                    width: 8, 
                    height: 8, 
                    borderRadius: '50%', 
                    bgcolor: getStatusColor(scenario.status) 
                  }} 
                />
                <Typography sx={{ flex: 1, fontWeight: 600 }}>
                  {scenario.scenario_name}
                </Typography>
                <Chip 
                  label={scenario.status.toUpperCase()} 
                  size="small"
                  sx={{ 
                    bgcolor: getStatusColor(scenario.status),
                    color: 'white',
                    fontWeight: 600
                  }}
                />
                <Typography variant="caption" color="text.secondary">
                  {scenario.duration.toFixed(2)}s
                </Typography>
              </Box>
            </AccordionSummary>
            <AccordionDetails>
              {scenario.error_message && (
                <Alert severity="error" sx={{ mb: 2 }}>
                  <Typography variant="body2">
                    <strong>Error:</strong> {scenario.error_message}
                  </Typography>
                  {scenario.failed_step && (
                    <Typography variant="caption" sx={{ display: 'block', mt: 1 }}>
                      Failed at: {scenario.failed_step}
                    </Typography>
                  )}
                </Alert>
              )}

              {/* AI Decisions */}
              {scenario.ai_decisions && scenario.ai_decisions.length > 0 && (
                <Box>
                  <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                    🤖 AI Decisions:
                  </Typography>
                  {scenario.ai_decisions.map((decision, didx) => (
                    <Box 
                      key={didx} 
                      sx={{ 
                        ml: 2, 
                        mb: 1,
                        p: 1.5,
                        bgcolor: 'grey.50',
                        borderRadius: 1,
                        borderLeft: 3,
                        borderColor: '#667eea'
                      }}
                    >
                      <Typography variant="caption" sx={{ fontWeight: 600, display: 'block' }}>
                        {decision.step}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {decision.decision.reasoning}
                      </Typography>
                    </Box>
                  ))}
                </Box>
              )}

              {/* Logs */}
              {scenario.logs && scenario.logs.length > 0 && (
                <Box sx={{ mt: 2 }}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                    Execution Logs:
                  </Typography>
                  <Box 
                    sx={{ 
                      bgcolor: 'grey.900', 
                      color: 'grey.100',
                      p: 1.5,
                      borderRadius: 1,
                      fontFamily: 'monospace',
                      fontSize: '0.75rem',
                      maxHeight: 200,
                      overflowY: 'auto'
                    }}
                  >
                    {scenario.logs.map((log, lidx) => (
                      <Typography 
                        key={lidx} 
                        variant="body2" 
                        sx={{ 
                          fontFamily: 'monospace',
                          fontSize: '0.75rem',
                          mb: 0.5
                        }}
                      >
                        {log}
                      </Typography>
                    ))}
                  </Box>
                </Box>
              )}
            </AccordionDetails>
          </Accordion>
        ))}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
}