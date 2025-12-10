import { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Grid,
  Chip,
  Alert,
  LinearProgress,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Switch,
  FormControlLabel,
  Divider,
  Stack,
  CircularProgress,
  Fade,
  Collapse,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from '@mui/material';
import {
  PlayArrow,
  Stop,
  Pause,
  PlayCircle,
  Refresh,
  Settings,
  Timeline,
  Storage,
  Speed,
  CheckCircle,
  Error,
  Warning,
  Schedule,
  Queue,
  Memory,
  AutoAwesome,
  Rocket,
  BugReport,
  ExpandMore,
  ExpandLess,
  Add,
  CloudSync,
} from '@mui/icons-material';
import axios from 'axios';

// Status indicator component
function StatusIndicator({ status, size = 'medium' }) {
  const getStatusColor = () => {
    if (status === 'running') return '#4caf50';
    if (status === 'paused') return '#ff9800';
    return '#9e9e9e';
  };

  const getStatusText = () => {
    if (status === 'running') return 'RUNNING';
    if (status === 'paused') return 'PAUSED';
    return 'STOPPED';
  };

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
      <Box
        sx={{
          width: size === 'large' ? 16 : 12,
          height: size === 'large' ? 16 : 12,
          borderRadius: '50%',
          backgroundColor: getStatusColor(),
          boxShadow: status === 'running' ? `0 0 10px ${getStatusColor()}` : 'none',
          animation: status === 'running' ? 'pulse 2s infinite' : 'none',
          '@keyframes pulse': {
            '0%': { opacity: 1 },
            '50%': { opacity: 0.5 },
            '100%': { opacity: 1 },
          },
        }}
      />
      <Typography
        variant={size === 'large' ? 'h6' : 'body2'}
        sx={{ fontWeight: 600, color: getStatusColor() }}
      >
        {getStatusText()}
      </Typography>
    </Box>
  );
}

// Stat card component
function StatCard({ title, value, icon, color = 'primary', subtitle }) {
  return (
    <Card sx={{ height: '100%' }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
          <Box>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              {title}
            </Typography>
            <Typography variant="h4" sx={{ fontWeight: 700, color: `${color}.main` }}>
              {value}
            </Typography>
            {subtitle && (
              <Typography variant="caption" color="text.secondary">
                {subtitle}
              </Typography>
            )}
          </Box>
          <Box
            sx={{
              p: 1,
              borderRadius: 2,
              backgroundColor: `${color}.lighter`,
              color: `${color}.main`,
            }}
          >
            {icon}
          </Box>
        </Box>
      </CardContent>
    </Card>
  );
}

export default function OrchestratorControlPanel() {
  // State
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [history, setHistory] = useState([]);
  const [config, setConfig] = useState(null);
  const [projects, setProjects] = useState([]);
  const [showConfigDialog, setShowConfigDialog] = useState(false);
  const [showQueueDialog, setShowQueueDialog] = useState(false);
  const [selectedProject, setSelectedProject] = useState('');
  const [queuePriority, setQueuePriority] = useState('normal');
  const [notification, setNotification] = useState({ open: false, message: '', severity: 'info' });
  const [historyExpanded, setHistoryExpanded] = useState(true);

  // Fetch status
  const fetchStatus = useCallback(async () => {
    try {
      const response = await axios.get('/api/orchestrator/status');
      setStatus(response.data);
    } catch (error) {
      console.error('Error fetching status:', error);
      setStatus({ statistics: { is_running: false, is_paused: false } });
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch history
  const fetchHistory = useCallback(async () => {
    try {
      const response = await axios.get('/api/orchestrator/history?limit=20');
      setHistory(response.data.history || []);
    } catch (error) {
      console.error('Error fetching history:', error);
    }
  }, []);

  // Fetch config
  const fetchConfig = useCallback(async () => {
    try {
      const response = await axios.get('/api/orchestrator/config');
      setConfig(response.data.config);
    } catch (error) {
      console.error('Error fetching config:', error);
    }
  }, []);

  // Fetch projects
  const fetchProjects = useCallback(async () => {
    try {
      const response = await axios.get('/api/projects');
      setProjects(response.data);
    } catch (error) {
      console.error('Error fetching projects:', error);
    }
  }, []);

  // Initial load
  useEffect(() => {
    fetchStatus();
    fetchHistory();
    fetchConfig();
    fetchProjects();

    // Poll status every 5 seconds
    const interval = setInterval(() => {
      fetchStatus();
      fetchHistory();
    }, 5000);

    return () => clearInterval(interval);
  }, [fetchStatus, fetchHistory, fetchConfig, fetchProjects]);

  // Show notification
  const showNotification = (message, severity = 'info') => {
    setNotification({ open: true, message, severity });
  };

  // Control actions
  const handleStart = async () => {
    setActionLoading(true);
    try {
      await axios.post('/api/orchestrator/start');
      showNotification('Autonomous orchestrator started!', 'success');
      fetchStatus();
    } catch (error) {
      showNotification(error.response?.data?.detail || 'Failed to start', 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const handleStop = async () => {
    setActionLoading(true);
    try {
      await axios.post('/api/orchestrator/stop');
      showNotification('Orchestrator stopped', 'info');
      fetchStatus();
    } catch (error) {
      showNotification(error.response?.data?.detail || 'Failed to stop', 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const handlePause = async () => {
    setActionLoading(true);
    try {
      await axios.post('/api/orchestrator/pause');
      showNotification('Orchestrator paused', 'warning');
      fetchStatus();
    } catch (error) {
      showNotification(error.response?.data?.detail || 'Failed to pause', 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const handleResume = async () => {
    setActionLoading(true);
    try {
      await axios.post('/api/orchestrator/resume');
      showNotification('Orchestrator resumed', 'success');
      fetchStatus();
    } catch (error) {
      showNotification(error.response?.data?.detail || 'Failed to resume', 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const handleTriggerRegression = async () => {
    setActionLoading(true);
    try {
      const response = await axios.post('/api/orchestrator/queue/regression');
      showNotification(`Regression tests queued! Queue size: ${response.data.queue_size}`, 'success');
      fetchStatus();
    } catch (error) {
      showNotification(error.response?.data?.detail || 'Failed to trigger regression', 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const handleQueueProject = async () => {
    if (!selectedProject) {
      showNotification('Please select a project', 'warning');
      return;
    }

    setActionLoading(true);
    try {
      const response = await axios.post('/api/orchestrator/queue/project', {
        project_id: selectedProject,
        priority: queuePriority,
      });
      showNotification(`Queued ${response.data.test_ids?.length || 0} tests!`, 'success');
      setShowQueueDialog(false);
      fetchStatus();
    } catch (error) {
      showNotification(error.response?.data?.detail || 'Failed to queue project', 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const handleSaveConfig = async () => {
    setActionLoading(true);
    try {
      await axios.put('/api/orchestrator/config', config);
      showNotification('Configuration saved!', 'success');
      setShowConfigDialog(false);
    } catch (error) {
      showNotification(error.response?.data?.detail || 'Failed to save config', 'error');
    } finally {
      setActionLoading(false);
    }
  };

  // Format uptime
  const formatUptime = (seconds) => {
    if (!seconds) return '0s';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    if (hours > 0) return `${hours}h ${minutes}m`;
    if (minutes > 0) return `${minutes}m ${secs}s`;
    return `${secs}s`;
  };

  // Get orchestrator state
  const isRunning = status?.statistics?.is_running || false;
  const isPaused = status?.statistics?.is_paused || false;
  const orchestratorState = isRunning ? (isPaused ? 'paused' : 'running') : 'stopped';

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 400 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
          <AutoAwesome sx={{ fontSize: 40, color: 'primary.main' }} />
          <Box>
            <Typography variant="h4" sx={{ fontWeight: 700 }}>
              Autonomous Orchestrator
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Control Panel for Autonomous Test Execution
            </Typography>
          </Box>
          <Box sx={{ ml: 'auto' }}>
            <StatusIndicator status={orchestratorState} size="large" />
          </Box>
        </Box>
      </Box>

      {/* Main Control Panel */}
      <Card sx={{ mb: 3, background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
        <CardContent sx={{ py: 4 }}>
          <Grid container spacing={3} alignItems="center">
            {/* Control Buttons */}
            <Grid item xs={12} md={6}>
              <Typography variant="h6" sx={{ color: 'white', mb: 2, fontWeight: 600 }}>
                Orchestrator Controls
              </Typography>
              <Stack direction="row" spacing={2} flexWrap="wrap" useFlexGap>
                {!isRunning ? (
                  <Button
                    variant="contained"
                    size="large"
                    startIcon={<PlayArrow />}
                    onClick={handleStart}
                    disabled={actionLoading}
                    sx={{
                      bgcolor: 'white',
                      color: 'primary.main',
                      '&:hover': { bgcolor: 'grey.100' },
                      fontWeight: 600,
                      px: 4,
                    }}
                  >
                    START
                  </Button>
                ) : (
                  <>
                    <Button
                      variant="contained"
                      size="large"
                      startIcon={<Stop />}
                      onClick={handleStop}
                      disabled={actionLoading}
                      sx={{
                        bgcolor: '#f44336',
                        '&:hover': { bgcolor: '#d32f2f' },
                        fontWeight: 600,
                      }}
                    >
                      STOP
                    </Button>
                    {!isPaused ? (
                      <Button
                        variant="contained"
                        size="large"
                        startIcon={<Pause />}
                        onClick={handlePause}
                        disabled={actionLoading}
                        sx={{
                          bgcolor: '#ff9800',
                          '&:hover': { bgcolor: '#f57c00' },
                          fontWeight: 600,
                        }}
                      >
                        PAUSE
                      </Button>
                    ) : (
                      <Button
                        variant="contained"
                        size="large"
                        startIcon={<PlayCircle />}
                        onClick={handleResume}
                        disabled={actionLoading}
                        sx={{
                          bgcolor: '#4caf50',
                          '&:hover': { bgcolor: '#388e3c' },
                          fontWeight: 600,
                        }}
                      >
                        RESUME
                      </Button>
                    )}
                  </>
                )}
                <Button
                  variant="outlined"
                  size="large"
                  startIcon={<Refresh />}
                  onClick={fetchStatus}
                  sx={{ borderColor: 'white', color: 'white' }}
                >
                  Refresh
                </Button>
              </Stack>
            </Grid>

            {/* Quick Actions */}
            <Grid item xs={12} md={6}>
              <Typography variant="h6" sx={{ color: 'white', mb: 2, fontWeight: 600 }}>
                Quick Actions
              </Typography>
              <Stack direction="row" spacing={2} flexWrap="wrap" useFlexGap>
                <Button
                  variant="outlined"
                  startIcon={<Rocket />}
                  onClick={handleTriggerRegression}
                  disabled={!isRunning || actionLoading}
                  sx={{ borderColor: 'white', color: 'white' }}
                >
                  Run Regression
                </Button>
                <Button
                  variant="outlined"
                  startIcon={<Add />}
                  onClick={() => setShowQueueDialog(true)}
                  disabled={!isRunning || actionLoading}
                  sx={{ borderColor: 'white', color: 'white' }}
                >
                  Queue Project
                </Button>
                <Button
                  variant="outlined"
                  startIcon={<Settings />}
                  onClick={() => setShowConfigDialog(true)}
                  sx={{ borderColor: 'white', color: 'white' }}
                >
                  Settings
                </Button>
              </Stack>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Statistics Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={6} md={3}>
          <StatCard
            title="Total Executed"
            value={status?.statistics?.total_executed || 0}
            icon={<BugReport />}
            color="primary"
          />
        </Grid>
        <Grid item xs={6} md={3}>
          <StatCard
            title="Passed"
            value={status?.statistics?.total_passed || 0}
            icon={<CheckCircle />}
            color="success"
          />
        </Grid>
        <Grid item xs={6} md={3}>
          <StatCard
            title="Failed"
            value={status?.statistics?.total_failed || 0}
            icon={<Error />}
            color="error"
          />
        </Grid>
        <Grid item xs={6} md={3}>
          <StatCard
            title="Queue Size"
            value={status?.queue?.total || 0}
            icon={<Queue />}
            color="warning"
            subtitle={status?.queue?.current_execution ? 'Currently executing...' : 'Idle'}
          />
        </Grid>
      </Grid>

      {/* Additional Stats Row */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={6} md={3}>
          <StatCard
            title="Uptime"
            value={formatUptime(status?.statistics?.uptime_seconds)}
            icon={<Schedule />}
            color="info"
          />
        </Grid>
        <Grid item xs={6} md={3}>
          <StatCard
            title="Known Features"
            value={status?.statistics?.known_features || 0}
            icon={<Storage />}
            color="secondary"
          />
        </Grid>
        <Grid item xs={6} md={3}>
          <StatCard
            title="Retried"
            value={status?.statistics?.total_retried || 0}
            icon={<CloudSync />}
            color="warning"
          />
        </Grid>
        <Grid item xs={6} md={3}>
          <StatCard
            title="Total Queued"
            value={status?.statistics?.total_queued || 0}
            icon={<Timeline />}
            color="primary"
          />
        </Grid>
      </Grid>

      {/* Queue Priority Breakdown */}
      {status?.queue?.by_priority && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
              Queue by Priority
            </Typography>
            <Grid container spacing={2}>
              {Object.entries(status.queue.by_priority).map(([priority, count]) => (
                <Grid item xs={6} sm={4} md={2} key={priority}>
                  <Paper
                    sx={{
                      p: 2,
                      textAlign: 'center',
                      bgcolor: count > 0 ? 'primary.lighter' : 'grey.100',
                    }}
                  >
                    <Typography variant="h5" sx={{ fontWeight: 700 }}>
                      {count}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {priority}
                    </Typography>
                  </Paper>
                </Grid>
              ))}
            </Grid>
          </CardContent>
        </Card>
      )}

      {/* Execution History */}
      <Card>
        <CardContent>
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              mb: 2,
              cursor: 'pointer',
            }}
            onClick={() => setHistoryExpanded(!historyExpanded)}
          >
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              Recent Executions
            </Typography>
            <IconButton size="small">
              {historyExpanded ? <ExpandLess /> : <ExpandMore />}
            </IconButton>
          </Box>

          <Collapse in={historyExpanded}>
            {history.length > 0 ? (
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Feature/Test</TableCell>
                      <TableCell>Project</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell>Started</TableCell>
                      <TableCell>Completed</TableCell>
                      <TableCell>Retries</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {history.map((execution) => (
                      <TableRow key={execution.id}>
                        <TableCell>
                          <Typography variant="body2" sx={{ fontWeight: 500 }}>
                            {execution.feature_name || execution.id}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" color="text.secondary">
                            {execution.project_name}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={execution.status}
                            size="small"
                            color={
                              execution.status === 'completed'
                                ? 'success'
                                : execution.status === 'failed'
                                ? 'error'
                                : execution.status === 'running'
                                ? 'primary'
                                : 'default'
                            }
                          />
                        </TableCell>
                        <TableCell>
                          <Typography variant="caption">
                            {execution.started_at
                              ? new Date(execution.started_at).toLocaleTimeString()
                              : '-'}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="caption">
                            {execution.completed_at
                              ? new Date(execution.completed_at).toLocaleTimeString()
                              : '-'}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          {execution.retry_count > 0 && (
                            <Chip
                              label={execution.retry_count}
                              size="small"
                              color="warning"
                              variant="outlined"
                            />
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            ) : (
              <Alert severity="info">
                No execution history yet. Start the orchestrator to begin autonomous testing.
              </Alert>
            )}
          </Collapse>
        </CardContent>
      </Card>

      {/* Queue Project Dialog */}
      <Dialog open={showQueueDialog} onClose={() => setShowQueueDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Queue Project for Testing</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2 }}>
            <FormControl fullWidth sx={{ mb: 3 }}>
              <InputLabel>Select Project</InputLabel>
              <Select
                value={selectedProject}
                label="Select Project"
                onChange={(e) => setSelectedProject(e.target.value)}
              >
                {projects.map((project) => (
                  <MenuItem key={project.id} value={project.id}>
                    {project.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl fullWidth>
              <InputLabel>Priority</InputLabel>
              <Select
                value={queuePriority}
                label="Priority"
                onChange={(e) => setQueuePriority(e.target.value)}
              >
                <MenuItem value="critical">Critical</MenuItem>
                <MenuItem value="high">High</MenuItem>
                <MenuItem value="normal">Normal</MenuItem>
                <MenuItem value="low">Low</MenuItem>
                <MenuItem value="background">Background</MenuItem>
              </Select>
            </FormControl>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowQueueDialog(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleQueueProject}
            disabled={!selectedProject || actionLoading}
          >
            Queue Tests
          </Button>
        </DialogActions>
      </Dialog>

      {/* Configuration Dialog */}
      <Dialog
        open={showConfigDialog}
        onClose={() => setShowConfigDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Orchestrator Configuration</DialogTitle>
        <DialogContent>
          {config && (
            <Box sx={{ pt: 2 }}>
              <FormControlLabel
                control={
                  <Switch
                    checked={config.auto_discover_new_features}
                    onChange={(e) =>
                      setConfig({ ...config, auto_discover_new_features: e.target.checked })
                    }
                  />
                }
                label="Auto-discover new features"
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={config.continuous_regression_enabled}
                    onChange={(e) =>
                      setConfig({ ...config, continuous_regression_enabled: e.target.checked })
                    }
                  />
                }
                label="Enable continuous regression"
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={config.headless_mode}
                    onChange={(e) => setConfig({ ...config, headless_mode: e.target.checked })}
                  />
                }
                label="Headless browser mode"
              />

              <Divider sx={{ my: 2 }} />

              <TextField
                label="Poll Interval (seconds)"
                type="number"
                value={config.poll_interval_seconds}
                onChange={(e) =>
                  setConfig({ ...config, poll_interval_seconds: parseInt(e.target.value) })
                }
                fullWidth
                sx={{ mb: 2 }}
              />
              <TextField
                label="Discovery Interval (seconds)"
                type="number"
                value={config.discovery_interval_seconds}
                onChange={(e) =>
                  setConfig({ ...config, discovery_interval_seconds: parseInt(e.target.value) })
                }
                fullWidth
                sx={{ mb: 2 }}
              />
              <TextField
                label="Regression Interval (hours)"
                type="number"
                value={config.regression_interval_hours}
                onChange={(e) =>
                  setConfig({ ...config, regression_interval_hours: parseInt(e.target.value) })
                }
                fullWidth
                sx={{ mb: 2 }}
              />

              <FormControl fullWidth>
                <InputLabel>Execution Mode</InputLabel>
                <Select
                  value={config.execution_mode}
                  label="Execution Mode"
                  onChange={(e) => setConfig({ ...config, execution_mode: e.target.value })}
                >
                  <MenuItem value="autonomous">Autonomous (AI-powered)</MenuItem>
                  <MenuItem value="guided">Guided</MenuItem>
                  <MenuItem value="strict">Strict</MenuItem>
                </Select>
              </FormControl>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowConfigDialog(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleSaveConfig} disabled={actionLoading}>
            Save Configuration
          </Button>
        </DialogActions>
      </Dialog>

      {/* Notification Snackbar */}
      <Fade in={notification.open}>
        <Alert
          severity={notification.severity}
          onClose={() => setNotification({ ...notification, open: false })}
          sx={{
            position: 'fixed',
            bottom: 24,
            right: 24,
            zIndex: 9999,
            boxShadow: 3,
          }}
        >
          {notification.message}
        </Alert>
      </Fade>
    </Box>
  );
}
