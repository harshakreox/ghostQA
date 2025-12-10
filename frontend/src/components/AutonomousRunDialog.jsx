import { useState, useEffect, useRef, useCallback } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  LinearProgress,
  Chip,
  Paper,
  Grid,
  IconButton,
  Divider,
  Alert,
  CircularProgress,
  Fade,
  Collapse,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
} from '@mui/material';
import {
  Close,
  PlayArrow,
  Stop,
  CheckCircle,
  Error,
  Warning,
  Schedule,
  Speed,
  AutoAwesome,
  Psychology,
  Explore,
  Assignment,
  BugReport,
  ExpandMore,
  ExpandLess,
} from '@mui/icons-material';
import axios from 'axios';

// Phase icons and colors
const PHASE_CONFIG = {
  initializing: { icon: <Schedule />, color: 'info', label: 'Initializing' },
  discovering: { icon: <Explore />, color: 'info', label: 'Discovering Tests' },
  planning: { icon: <Assignment />, color: 'warning', label: 'Planning Execution' },
  executing: { icon: <PlayArrow />, color: 'primary', label: 'Executing Tests' },
  analyzing: { icon: <Psychology />, color: 'secondary', label: 'Analyzing Results' },
  completed: { icon: <CheckCircle />, color: 'success', label: 'Completed' },
  failed: { icon: <Error />, color: 'error', label: 'Failed' },
  stopped: { icon: <Warning />, color: 'warning', label: 'Stopped' },
};

export default function AutonomousRunDialog({ open, onClose, project }) {
  const [sessionId, setSessionId] = useState(null);
  const [state, setState] = useState(null);
  const [logs, setLogs] = useState([]);
  const [starting, setStarting] = useState(false);
  const [stopping, setStopping] = useState(false);
  const [showLogs, setShowLogs] = useState(true);
  const [error, setError] = useState(null);

  const wsRef = useRef(null);
  const logsEndRef = useRef(null);
  const pollingRef = useRef(null);

  // Auto-scroll logs
  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  // Start the autonomous run when dialog opens
  useEffect(() => {
    if (open && project && !sessionId) {
      startAutonomousRun();
    }

    return () => {
      // Cleanup on unmount
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
      }
    };
  }, [open, project]);

  // Connect to WebSocket for real-time logs
  const connectWebSocket = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/logs`;

    try {
      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          // Only process messages for our session
          if (data.session_id === sessionId) {
            // Add to logs
            if (data.message) {
              setLogs(prev => [...prev.slice(-200), data.message]); // Keep last 200
            }

            // Update state from WebSocket message
            if (data.phase) {
              setState(prev => ({
                ...prev,
                phase: data.phase,
                progress_percent: data.progress || prev?.progress_percent || 0,
                passed: data.passed ?? prev?.passed ?? 0,
                failed: data.failed ?? prev?.failed ?? 0,
                current_test: data.current_test || prev?.current_test || '',
              }));
            }
          }
        } catch (e) {
          // Not JSON, treat as plain log
          setLogs(prev => [...prev.slice(-200), event.data]);
        }
      };

      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      wsRef.current.onclose = () => {
        console.log('WebSocket closed');
      };
    } catch (e) {
      console.error('Failed to connect WebSocket:', e);
    }
  }, [sessionId]);

  // Poll for status updates
  const startPolling = useCallback((sid) => {
    const poll = async () => {
      try {
        const response = await axios.get(`/api/agent/autonomous/session/${sid}`);
        setState(response.data);

        // Check if completed
        if (['completed', 'failed', 'stopped'].includes(response.data.phase)) {
          clearInterval(pollingRef.current);
        }
      } catch (e) {
        if (e.response?.status === 404) {
          clearInterval(pollingRef.current);
        }
      }
    };

    // Poll every 2 seconds
    pollingRef.current = setInterval(poll, 2000);
    poll(); // Initial call
  }, []);

  // Start autonomous run
  const startAutonomousRun = async () => {
    setStarting(true);
    setError(null);
    setLogs([]);
    setState(null);

    try {
      const response = await axios.post(
        `/api/agent/autonomous/run/${project.id}`,
        null,
        { params: { headless: true, execution_mode: 'autonomous' } }
      );

      const sid = response.data.session_id;
      setSessionId(sid);

      // Connect WebSocket
      connectWebSocket();

      // Start polling for status
      startPolling(sid);

      setLogs([`Agent started for project: ${project.name}`]);

    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to start autonomous agent');
      console.error('Start error:', e);
    } finally {
      setStarting(false);
    }
  };

  // Stop the agent
  const handleStop = async () => {
    if (!sessionId) return;

    setStopping(true);
    try {
      await axios.post(`/api/agent/autonomous/session/${sessionId}/stop`);
      setLogs(prev => [...prev, 'Stop requested...']);
    } catch (e) {
      console.error('Stop error:', e);
    } finally {
      setStopping(false);
    }
  };

  // Close dialog
  const handleClose = () => {
    if (wsRef.current) {
      wsRef.current.close();
    }
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
    }
    setSessionId(null);
    setState(null);
    setLogs([]);
    onClose();
  };

  // Get phase config
  const phaseConfig = state?.phase ? PHASE_CONFIG[state.phase] : PHASE_CONFIG.initializing;
  const isRunning = state?.phase && !['completed', 'failed', 'stopped'].includes(state.phase);
  const isComplete = state?.phase === 'completed';
  const isFailed = state?.phase === 'failed';

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: { minHeight: '70vh' }
      }}
    >
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <AutoAwesome sx={{ color: 'primary.main' }} />
            <Box>
              <Typography variant="h6">Autonomous Test Execution</Typography>
              <Typography variant="caption" color="text.secondary">
                {project?.name}
              </Typography>
            </Box>
          </Box>
          <IconButton onClick={handleClose} size="small">
            <Close />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent dividers>
        {/* Error State */}
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
            <Button size="small" onClick={startAutonomousRun} sx={{ ml: 2 }}>
              Retry
            </Button>
          </Alert>
        )}

        {/* Starting State */}
        {starting && (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <CircularProgress size={60} />
            <Typography variant="h6" sx={{ mt: 2 }}>
              Starting Autonomous Agent...
            </Typography>
            <Typography variant="body2" color="text.secondary">
              The agent is initializing and will take over testing
            </Typography>
          </Box>
        )}

        {/* Running/Complete State */}
        {state && !starting && (
          <>
            {/* Phase Header */}
            <Paper
              sx={{
                p: 2,
                mb: 3,
                background: isComplete
                  ? 'linear-gradient(135deg, #4caf50 0%, #81c784 100%)'
                  : isFailed
                  ? 'linear-gradient(135deg, #f44336 0%, #e57373 100%)'
                  : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                color: 'white',
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  {phaseConfig.icon}
                  <Box>
                    <Typography variant="h6">{phaseConfig.label}</Typography>
                    {state.current_test && (
                      <Typography variant="body2" sx={{ opacity: 0.9 }}>
                        {state.current_test}
                      </Typography>
                    )}
                  </Box>
                </Box>
                <Typography variant="h4" sx={{ fontWeight: 700 }}>
                  {Math.round(state.progress_percent || 0)}%
                </Typography>
              </Box>

              <LinearProgress
                variant="determinate"
                value={state.progress_percent || 0}
                sx={{
                  mt: 2,
                  height: 8,
                  borderRadius: 4,
                  backgroundColor: 'rgba(255,255,255,0.3)',
                  '& .MuiLinearProgress-bar': {
                    backgroundColor: 'white',
                  }
                }}
              />
            </Paper>

            {/* Stats Grid */}
            <Grid container spacing={2} sx={{ mb: 3 }}>
              <Grid item xs={3}>
                <Paper sx={{ p: 2, textAlign: 'center' }}>
                  <Typography variant="h4" sx={{ fontWeight: 700 }}>
                    {state.discovered_tests_count || 0}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Discovered
                  </Typography>
                </Paper>
              </Grid>
              <Grid item xs={3}>
                <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'success.lighter' }}>
                  <Typography variant="h4" sx={{ fontWeight: 700, color: 'success.main' }}>
                    {state.passed || 0}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Passed
                  </Typography>
                </Paper>
              </Grid>
              <Grid item xs={3}>
                <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'error.lighter' }}>
                  <Typography variant="h4" sx={{ fontWeight: 700, color: 'error.main' }}>
                    {state.failed || 0}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Failed
                  </Typography>
                </Paper>
              </Grid>
              <Grid item xs={3}>
                <Paper sx={{ p: 2, textAlign: 'center' }}>
                  <Typography variant="h4" sx={{ fontWeight: 700, color: 'text.secondary' }}>
                    {state.skipped || 0}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Skipped
                  </Typography>
                </Paper>
              </Grid>
            </Grid>

            {/* Discovery Info */}
            {(state.total_features > 0 || state.total_traditional_tests > 0) && (
              <Alert severity="info" sx={{ mb: 2 }}>
                <Typography variant="body2">
                  Discovered: {state.total_features} features with {state.total_scenarios} scenarios,
                  {state.total_traditional_tests} traditional tests
                </Typography>
              </Alert>
            )}

            {/* Logs Section */}
            <Box>
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  cursor: 'pointer',
                  mb: 1,
                }}
                onClick={() => setShowLogs(!showLogs)}
              >
                <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                  Execution Log ({logs.length} entries)
                </Typography>
                <IconButton size="small">
                  {showLogs ? <ExpandLess /> : <ExpandMore />}
                </IconButton>
              </Box>

              <Collapse in={showLogs}>
                <Paper
                  sx={{
                    p: 2,
                    maxHeight: 250,
                    overflow: 'auto',
                    bgcolor: '#1e1e1e',
                    fontFamily: 'monospace',
                    fontSize: '0.8rem',
                  }}
                >
                  {logs.length === 0 ? (
                    <Typography sx={{ color: '#888' }}>
                      Waiting for logs...
                    </Typography>
                  ) : (
                    logs.map((log, i) => {
                      const isError = log.includes('ERROR') || log.includes('FAILED');
                      const isPass = log.includes('PASSED') || log.includes('SUCCESS');
                      const isPhase = log.includes('phase') || log.includes('===');

                      return (
                        <Typography
                          key={i}
                          sx={{
                            color: isError ? '#f44336' : isPass ? '#4caf50' : isPhase ? '#90caf9' : '#ddd',
                            whiteSpace: 'pre-wrap',
                            wordBreak: 'break-word',
                            mb: 0.5,
                          }}
                        >
                          {log}
                        </Typography>
                      );
                    })
                  )}
                  <div ref={logsEndRef} />
                </Paper>
              </Collapse>
            </Box>

            {/* Results (when complete) */}
            {isComplete && state.results && state.results.length > 0 && (
              <Box sx={{ mt: 3 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                  Test Results
                </Typography>
                <Paper sx={{ maxHeight: 200, overflow: 'auto' }}>
                  <List dense>
                    {state.results.map((result, i) => (
                      <ListItem key={i}>
                        <ListItemIcon>
                          {result.status === 'passed' ? (
                            <CheckCircle color="success" fontSize="small" />
                          ) : result.status === 'failed' ? (
                            <Error color="error" fontSize="small" />
                          ) : (
                            <Warning color="warning" fontSize="small" />
                          )}
                        </ListItemIcon>
                        <ListItemText
                          primary={result.test_name}
                          secondary={result.error || `${result.duration.toFixed(1)}s`}
                          primaryTypographyProps={{ variant: 'body2' }}
                          secondaryTypographyProps={{
                            variant: 'caption',
                            color: result.error ? 'error' : 'text.secondary'
                          }}
                        />
                      </ListItem>
                    ))}
                  </List>
                </Paper>
              </Box>
            )}
          </>
        )}
      </DialogContent>

      <DialogActions sx={{ px: 3, py: 2 }}>
        {isRunning && (
          <Button
            variant="outlined"
            color="error"
            startIcon={stopping ? <CircularProgress size={16} /> : <Stop />}
            onClick={handleStop}
            disabled={stopping}
          >
            {stopping ? 'Stopping...' : 'Stop Agent'}
          </Button>
        )}

        <Box sx={{ flex: 1 }} />

        {isComplete && (
          <Chip
            icon={<CheckCircle />}
            label={`Completed: ${state.passed} passed, ${state.failed} failed`}
            color={state.failed > 0 ? 'warning' : 'success'}
          />
        )}

        <Button onClick={handleClose}>
          {isComplete || isFailed ? 'Close' : 'Run in Background'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
