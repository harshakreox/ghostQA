import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box, Button, Typography, Paper, Checkbox, FormControlLabel, LinearProgress,
  Card, CardContent, Alert, Chip, Switch, List, ListItem, ListItemIcon, ListItemText,
  ListItemSecondaryAction, Divider, CircularProgress, Tabs, Tab, FormControl, InputLabel,
  Select, MenuItem, Grid, Snackbar, IconButton, Collapse, Tooltip, Stack,
} from '@mui/material';
import {
  PlayArrow, Code, Psychology, AutoAwesome, ExpandMore, ExpandLess, BugReport,
  Science, Terminal, CheckBox, CheckBoxOutlineBlank, Speed, Visibility, VisibilityOff,
} from '@mui/icons-material';
import axios from 'axios';
import { SearchBar } from '../components';

export default function TestRunner() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState(0);
  const [projects, setProjects] = useState([]);
  const [selectedProjectId, setSelectedProjectId] = useState('');
  const [selectedProject, setSelectedProject] = useState(null);
  const [loadingProjects, setLoadingProjects] = useState(true);
  const [selectedTests, setSelectedTests] = useState([]);
  const [headless, setHeadless] = useState(false);
  const [running, setRunning] = useState(false);
  const [logs, setLogs] = useState([]);
  const [ws, setWs] = useState(null);
  const [statusMessage, setStatusMessage] = useState('');
  const [logsExpanded, setLogsExpanded] = useState(false);
  const [testSearch, setTestSearch] = useState('');
  const [gherkinFeatures, setGherkinFeatures] = useState([]);
  const [aiRunning, setAiRunning] = useState(false);
  const [aiHeadless, setAiHeadless] = useState(false);
  const [aiError, setAiError] = useState(null);
  const [aiLogs, setAiLogs] = useState([]);
  const [aiStatusMessage, setAiStatusMessage] = useState('');
  const [aiLogsExpanded, setAiLogsExpanded] = useState(false);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });

  const showNotification = (message, severity = 'success') => setSnackbar({ open: true, message, severity });
  const handleCloseSnackbar = () => setSnackbar({ ...snackbar, open: false });
  const getWebSocketUrl = () => `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.hostname}:8000/ws/logs`;

  useEffect(() => { loadProjects(); return () => { if (ws) ws.close(); }; }, []);
  useEffect(() => {
    if (selectedProjectId) { loadProjectDetails(selectedProjectId); loadGherkinFeatures(selectedProjectId); }
    else { setSelectedProject(null); setSelectedTests([]); setGherkinFeatures([]); }
  }, [selectedProjectId]);

  const loadProjects = async () => {
    try { setProjects((await axios.get('/api/projects')).data); }
    catch { showNotification('Failed to load projects', 'error'); }
    finally { setLoadingProjects(false); }
  };

  const loadProjectDetails = async (projectId) => {
    try {
      const response = await axios.get(`/api/projects/${projectId}`);
      setSelectedProject(response.data);
      setSelectedTests(response.data.test_cases.map((tc) => tc.id));
    } catch { showNotification('Failed to load project', 'error'); }
  };

  const loadGherkinFeatures = async (projectId) => {
    try {
      const response = await axios.get(`/api/projects/${projectId}/gherkin-features`);
      setGherkinFeatures(Array.isArray(response.data) ? response.data : response.data?.features || []);
    } catch { setGherkinFeatures([]); }
  };

  const handleToggleTest = (testId) => setSelectedTests((prev) => prev.includes(testId) ? prev.filter((id) => id !== testId) : [...prev, testId]);

  const handleSelectAll = () => {
    if (!selectedProject) return;
    const filteredIds = getFilteredTests().map(tc => tc.id);
    const allSelected = filteredIds.every(id => selectedTests.includes(id));
    setSelectedTests(prev => allSelected ? prev.filter(id => !filteredIds.includes(id)) : [...new Set([...prev, ...filteredIds])]);
  };

  const getFilteredTests = () => selectedProject?.test_cases?.filter(tc => tc.name.toLowerCase().includes(testSearch.toLowerCase()) || tc.description?.toLowerCase().includes(testSearch.toLowerCase())) || [];

  const pollForReport = async (reportId, maxAttempts = 60) => {
    setStatusMessage('Running tests...'); setLogsExpanded(true);
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      try {
        if ((await axios.get(`/api/reports/${reportId}`)).data) {
          setStatusMessage('Done!'); setRunning(false); if (ws) ws.close();
          setTimeout(() => navigate(`/reports/${reportId}`), 1000); return;
        }
      } catch { setStatusMessage(`Running... (${attempt * 2}s)`); await new Promise(r => setTimeout(r, 2000)); }
    }
    setStatusMessage('Timeout'); setRunning(false); if (ws) ws.close();
  };

  const handleRunTests = async () => {
    if (!selectedProjectId || selectedTests.length === 0) { showNotification('Select tests', 'warning'); return; }
    setRunning(true); setLogs([]); setStatusMessage('Starting...'); setLogsExpanded(true);
    const websocket = new WebSocket(getWebSocketUrl());
    websocket.onopen = () => setLogs(prev => [...prev, 'Connected...']);
    websocket.onmessage = (e) => setLogs(prev => [...prev, e.data]);
    websocket.onerror = () => setLogs(prev => [...prev, 'Connection error']);
    setWs(websocket);
    try {
      const response = await axios.post('/api/run-tests', { project_id: selectedProjectId, test_case_ids: selectedTests, headless });
      await pollForReport(response.data.report_id);
    } catch { setStatusMessage('Error'); showNotification('Failed', 'error'); setRunning(false); websocket.close(); }
  };

  const addAiLog = (msg) => setAiLogs(prev => [...prev, `[${new Date().toLocaleTimeString()}] ${msg}`]);

  const handleRunAiTest = async (feature) => {
    if (!selectedProjectId) return;
    setAiRunning(true); setAiError(null); setAiLogs([]); setAiStatusMessage('Starting unified executor...'); setAiLogsExpanded(true);
    try {
      addAiLog(`Feature: ${feature.name}`);
      addAiLog('Using unified executor with learning...');
      const response = await axios.post('/api/gherkin/run-autonomous', { feature_id: feature.id, project_id: selectedProjectId, headless: aiHeadless });
      const result = response.data.result || response.data;
      const aiDependency = response.data.ai_dependency_percent ?? 100;
      const newLearned = response.data.new_selectors_learned ?? 0;
      addAiLog(`Passed: ${result.passed}, Failed: ${result.failed}`);
      addAiLog(`AI Dependency: ${aiDependency.toFixed(1)}% | Learned: ${newLearned}`);
      setAiStatusMessage('Done!'); showNotification(`Tests: ${result.passed} passed, ${result.failed} failed`, 'success');
    } catch (error) {
      const errorMsg = error.response?.data?.detail || 'Execution failed';
      addAiLog('ERROR: ' + errorMsg); setAiError(errorMsg); setAiStatusMessage('Failed');
    } finally { setAiRunning(false); }
  };

  if (loadingProjects) return <LinearProgress />;
  const filteredTests = getFilteredTests();
  const totalTests = selectedProject?.test_cases?.length || 0;
  const totalActions = selectedProject?.test_cases?.reduce((s, tc) => s + tc.actions.length, 0) || 0;

  return (
    <Box>
      {/* Compact Header */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <Box sx={{ width: 40, height: 40, borderRadius: 2, background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white' }}><PlayArrow /></Box>
            <Box>
              <Typography variant="h6" sx={{ fontWeight: 700, lineHeight: 1.2 }}>Test Runner</Typography>
              <Typography variant="caption" color="text.secondary">Execute tests</Typography>
            </Box>
          </Box>
          <Divider orientation="vertical" flexItem sx={{ mx: 1 }} />
          <FormControl size="small" sx={{ minWidth: 250 }}>
            <InputLabel>Project</InputLabel>
            <Select value={selectedProjectId} onChange={(e) => setSelectedProjectId(e.target.value)} label="Project" disabled={running || aiRunning}>
              <MenuItem value=""><em>Select...</em></MenuItem>
              {projects.map((p) => <MenuItem key={p.id} value={p.id}>{p.name}</MenuItem>)}
            </Select>
          </FormControl>
          {selectedProject && (
            <Stack direction="row" spacing={1}>
              <Chip icon={<Code />} label={`${totalTests} Tests`} size="small" color="primary" variant="outlined" />
              <Chip label={`${totalActions} Actions`} size="small" variant="outlined" />
              {gherkinFeatures.length > 0 && <Chip icon={<Psychology />} label={`${gherkinFeatures.length} AI`} size="small" color="secondary" variant="outlined" />}
            </Stack>
          )}
        </Box>
      </Paper>

      {!selectedProjectId && (
        <Paper sx={{ p: 6, textAlign: 'center' }}>
          <Science sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h6" sx={{ mb: 1 }}>Select a Project</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>Choose from the dropdown above</Typography>
          <Button variant="outlined" size="small" onClick={() => navigate('/projects')}>Manage Projects</Button>
        </Paper>
      )}

      {selectedProjectId && selectedProject && (
        <>
          <Tabs value={activeTab} onChange={(e, v) => setActiveTab(v)} sx={{ mb: 2, '& .MuiTab-root': { textTransform: 'none', fontWeight: 600 } }}>
            <Tab icon={<Code />} iconPosition="start" label={`Traditional (${totalTests})`} />
            <Tab icon={<Psychology />} iconPosition="start" label={<Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>AI ({gherkinFeatures.length})<Chip label="BETA" size="small" sx={{ height: 18, fontSize: '0.6rem', bgcolor: '#667eea', color: 'white' }} /></Box>} />
          </Tabs>

          {activeTab === 0 && (
            <Grid container spacing={2}>
              <Grid item xs={12} md={8}>
                <Paper sx={{ p: 2 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2, gap: 2 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>Test Cases</Typography>
                      <Chip label={`${selectedTests.length}/${totalTests}`} size="small" color={selectedTests.length > 0 ? 'primary' : 'default'} />
                    </Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <SearchBar placeholder="Filter..." value={testSearch} onSearch={setTestSearch} minWidth={180} />
                      <Tooltip title="Select all"><IconButton size="small" onClick={handleSelectAll} disabled={running}>{filteredTests.every(tc => selectedTests.includes(tc.id)) ? <CheckBox color="primary" /> : <CheckBoxOutlineBlank />}</IconButton></Tooltip>
                    </Box>
                  </Box>
                  {totalTests === 0 ? (
                    <Alert severity="info">No tests. <Button size="small" onClick={() => navigate(`/projects/${selectedProjectId}`)}>Create</Button></Alert>
                  ) : (
                    <List dense sx={{ maxHeight: 320, overflow: 'auto', bgcolor: 'grey.50', borderRadius: 1 }}>
                      {filteredTests.map((tc) => (
                        <ListItem key={tc.id} dense button onClick={() => handleToggleTest(tc.id)} disabled={running} sx={{ borderRadius: 1, mb: 0.5, bgcolor: selectedTests.includes(tc.id) ? 'primary.50' : 'white', border: '1px solid', borderColor: selectedTests.includes(tc.id) ? 'primary.200' : 'transparent' }}>
                          <ListItemIcon sx={{ minWidth: 36 }}><Checkbox edge="start" checked={selectedTests.includes(tc.id)} size="small" /></ListItemIcon>
                          <ListItemText primary={tc.name} secondary={`${tc.actions.length} actions`} primaryTypographyProps={{ variant: 'body2', fontWeight: 500 }} secondaryTypographyProps={{ variant: 'caption' }} />
                          <ListItemSecondaryAction><Chip label={tc.actions.length} size="small" sx={{ height: 20, fontSize: '0.7rem' }} /></ListItemSecondaryAction>
                        </ListItem>
                      ))}
                    </List>
                  )}
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mt: 2, pt: 2, borderTop: '1px solid', borderColor: 'divider' }}>
                    <FormControlLabel control={<Switch size="small" checked={headless} onChange={(e) => setHeadless(e.target.checked)} disabled={running} />} label={<Typography variant="body2">Headless</Typography>} />
                    <Tooltip title="Logs"><IconButton size="small" onClick={() => setLogsExpanded(!logsExpanded)}><Terminal fontSize="small" />{logsExpanded ? <ExpandLess fontSize="small" /> : <ExpandMore fontSize="small" />}</IconButton></Tooltip>
                  </Box>
                </Paper>
                <Collapse in={logsExpanded}>
                  <Paper sx={{ mt: 2, p: 2 }}>
                    <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>Logs</Typography>
                    {running && <LinearProgress sx={{ mb: 1 }} />}
                    <Box sx={{ height: 180, overflowY: 'auto', bgcolor: 'grey.900', color: 'grey.100', p: 1.5, borderRadius: 1, fontFamily: 'monospace', fontSize: '0.7rem' }}>
                      {logs.length === 0 ? <Typography variant="caption" sx={{ color: 'grey.500' }}>Waiting...</Typography> : logs.map((log, i) => <Box key={i} sx={{ color: log.includes('PASSED') ? 'success.light' : log.includes('FAILED') ? 'error.light' : 'grey.100' }}>{log}</Box>)}
                    </Box>
                  </Paper>
                </Collapse>
              </Grid>
              <Grid item xs={12} md={4}>
                <Card sx={{ background: running ? 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)' : selectedTests.length > 0 ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' : 'linear-gradient(135deg, #6b7280 0%, #4b5563 100%)', color: 'white' }}>
                  <CardContent>
                    <Box sx={{ textAlign: 'center', mb: 2 }}>
                      <Typography variant="h3" sx={{ fontWeight: 700 }}>{selectedTests.length}</Typography>
                      <Typography variant="body2" sx={{ opacity: 0.9 }}>selected</Typography>
                    </Box>
                    <Button fullWidth variant="contained" size="large" startIcon={running ? <CircularProgress size={20} color="inherit" /> : <PlayArrow />} onClick={handleRunTests} disabled={running || selectedTests.length === 0} sx={{ bgcolor: 'rgba(255,255,255,0.2)', color: 'white', fontWeight: 600, py: 1.5, '&:hover': { bgcolor: 'rgba(255,255,255,0.3)' } }}>{running ? 'Running...' : 'Run Tests'}</Button>
                    {statusMessage && <Alert severity="info" sx={{ mt: 2, bgcolor: 'rgba(255,255,255,0.15)', color: 'white', '& .MuiAlert-icon': { color: 'white' } }}><Typography variant="caption">{statusMessage}</Typography></Alert>}
                  </CardContent>
                </Card>
                <Paper sx={{ mt: 2, p: 2 }}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1.5 }}>Config</Typography>
                  <Stack spacing={1}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}><Typography variant="body2" color="text.secondary">Browser</Typography><Chip icon={headless ? <VisibilityOff /> : <Visibility />} label={headless ? 'Headless' : 'Visible'} size="small" variant="outlined" /></Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}><Typography variant="body2" color="text.secondary">Actions</Typography><Typography variant="body2" sx={{ fontWeight: 600 }}>{selectedProject.test_cases.filter(tc => selectedTests.includes(tc.id)).reduce((s, tc) => s + tc.actions.length, 0)}</Typography></Box>
                  </Stack>
                </Paper>
              </Grid>
            </Grid>
          )}

          {activeTab === 1 && (
            <Grid container spacing={2}>
              <Grid item xs={12} md={8}>
                <Paper sx={{ p: 2 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                    <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>Gherkin Features</Typography>
                    <FormControlLabel control={<Switch size="small" checked={aiHeadless} onChange={(e) => setAiHeadless(e.target.checked)} disabled={aiRunning} />} label={<Typography variant="body2">Headless</Typography>} />
                  </Box>
                  {gherkinFeatures.length === 0 ? (
                    <Alert severity="info">No features. <Button size="small" onClick={() => navigate(`/generate?projectId=${selectedProjectId}`)}>Generate</Button></Alert>
                  ) : (
                    <Stack spacing={1}>
                      {gherkinFeatures.map((f) => (
                        <Paper key={f.id} variant="outlined" sx={{ p: 2, display: 'flex', alignItems: 'center', gap: 2, '&:hover': { borderColor: 'primary.main', bgcolor: 'primary.50' } }}>
                          <Psychology sx={{ color: '#667eea', fontSize: 28 }} />
                          <Box sx={{ flex: 1 }}>
                            <Typography variant="body1" sx={{ fontWeight: 600 }}>{f.name}</Typography>
                            <Typography variant="caption" color="text.secondary">{f.scenario_count} scenarios</Typography>
                          </Box>
                          <Button variant="contained" size="small" startIcon={aiRunning ? <CircularProgress size={14} color="inherit" /> : <AutoAwesome />} onClick={() => handleRunAiTest(f)} disabled={aiRunning} sx={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', whiteSpace: 'nowrap' }}>{aiRunning ? 'Running' : 'Run AI'}</Button>
                        </Paper>
                      ))}
                    </Stack>
                  )}
                  <Box sx={{ mt: 2, pt: 2, borderTop: '1px solid', borderColor: 'divider', display: 'flex', justifyContent: 'flex-end' }}>
                    <Tooltip title="Logs"><IconButton size="small" onClick={() => setAiLogsExpanded(!aiLogsExpanded)}><Terminal fontSize="small" />{aiLogsExpanded ? <ExpandLess fontSize="small" /> : <ExpandMore fontSize="small" />}</IconButton></Tooltip>
                  </Box>
                </Paper>
                <Collapse in={aiLogsExpanded}>
                  <Paper sx={{ mt: 2, p: 2 }}>
                    <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>AI Logs</Typography>
                    {aiRunning && <LinearProgress sx={{ mb: 1 }} />}
                    <Box sx={{ height: 180, overflowY: 'auto', bgcolor: 'grey.900', color: 'grey.100', p: 1.5, borderRadius: 1, fontFamily: 'monospace', fontSize: '0.7rem' }}>
                      {aiLogs.length === 0 ? <Typography variant="caption" sx={{ color: 'grey.500' }}>Waiting...</Typography> : aiLogs.map((log, i) => <Box key={i} sx={{ color: log.includes('Passed') ? 'success.light' : log.includes('ERROR') ? 'error.light' : 'grey.100' }}>{log}</Box>)}
                    </Box>
                  </Paper>
                </Collapse>
              </Grid>
              <Grid item xs={12} md={4}>
                <Card sx={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', color: 'white', mb: 2 }}>
                  <CardContent>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                      <Psychology sx={{ fontSize: 36 }} />
                      <Box><Typography variant="h6" sx={{ fontWeight: 600 }}>AI-Powered</Typography><Typography variant="caption" sx={{ opacity: 0.9 }}>Autonomous execution</Typography></Box>
                    </Box>
                    <Typography variant="body2" sx={{ opacity: 0.9 }}>AI interprets Gherkin steps automatically.</Typography>
                  </CardContent>
                </Card>
                {aiError && <Alert severity="error" sx={{ mb: 2 }}>{aiError}</Alert>}
                {aiStatusMessage && <Alert severity="info" sx={{ mb: 2 }}>{aiStatusMessage}</Alert>}
                <Paper sx={{ p: 2 }}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1.5 }}>AI Capabilities</Typography>
                  <Stack spacing={1}>
                    {[{ icon: <AutoAwesome />, title: 'Natural Language' }, { icon: <BugReport />, title: 'Self-healing' }, { icon: <Speed />, title: 'Smart Waits' }].map((item, i) => (
                      <Box key={i} sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}><Box sx={{ color: '#667eea' }}>{item.icon}</Box><Typography variant="body2" sx={{ fontWeight: 500 }}>{item.title}</Typography></Box>
                    ))}
                  </Stack>
                </Paper>
              </Grid>
            </Grid>
          )}
        </>
      )}

      <Snackbar open={snackbar.open} autoHideDuration={4000} onClose={handleCloseSnackbar} anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}>
        <Alert onClose={handleCloseSnackbar} severity={snackbar.severity} variant="filled">{snackbar.message}</Alert>
      </Snackbar>
    </Box>
  );
}
