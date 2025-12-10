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
  Divider,
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
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Alert,
} from '@mui/material';
import {
  NavigateNext,
  Edit,
  PlayArrow,
  Add,
  TrendingUp,
  CheckCircle,
  Error as ErrorIcon,
  Warning,
  Code,
  Rocket,
  CloudQueue,
  Speed,
} from '@mui/icons-material';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import axios from 'axios';
import { format } from 'date-fns';

const ENV_TYPE_COLORS = {
  development: 'info',
  staging: 'warning',
  production: 'error',
  qa: 'secondary',
  uat: 'primary',
};

export default function ReleaseDashboard() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [release, setRelease] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [runDialogOpen, setRunDialogOpen] = useState(false);
  const [selectedEnv, setSelectedEnv] = useState('');
  const [runNotes, setRunNotes] = useState('');
  const [running, setRunning] = useState(false);

  useEffect(() => {
    loadData();
  }, [id]);

  const loadData = async () => {
    try {
      const [releaseRes, metricsRes] = await Promise.all([
        axios.get(`/api/releases/${id}`),
        axios.get(`/api/releases/${id}/metrics`),
      ]);
      setRelease(releaseRes.data);
      setMetrics(metricsRes.data);
    } catch (error) {
      console.error('Error loading release:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleRunTests = async () => {
    if (!selectedEnv) return;
    
    setRunning(true);
    try {
      await axios.post(`/api/releases/${id}/run`, {
        release_id: id,
        environment_id: selectedEnv,
        headless: true,
        notes: runNotes,
      });
      
      setRunDialogOpen(false);
      setSelectedEnv('');
      setRunNotes('');
      
      // Reload data after a short delay
      setTimeout(() => {
        loadData();
      }, 2000);
    } catch (error) {
      console.error('Error running tests:', error);
      alert('Failed to start test run. Check console for details.');
    } finally {
      setRunning(false);
    }
  };

  if (loading) {
    return <LinearProgress />;
  }

  if (!release || !metrics) {
    return (
      <Box sx={{ textAlign: 'center', py: 8 }}>
        <Typography variant="h6">Release not found</Typography>
      </Box>
    );
  }

  // Prepare trend chart data
  const trendData = metrics.pass_rate_trend.map((rate, index) => ({
    iteration: `Run ${index + 1}`,
    passRate: rate,
    date: metrics.iteration_dates[index] ? format(new Date(metrics.iteration_dates[index]), 'MMM dd') : '',
  }));

  return (
    <Box>
      {/* Breadcrumbs */}
      <Breadcrumbs separator={<NavigateNext fontSize="small" />} sx={{ mb: 3 }}>
        <Link component="button" variant="body2" onClick={() => navigate('/releases')}>
          Releases
        </Link>
        <Typography color="text.primary">{release.name}</Typography>
      </Breadcrumbs>

      {/* Header */}
      <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Box
            sx={{
              width: 64,
              height: 64,
              borderRadius: 3,
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'white',
            }}
          >
            <Rocket sx={{ fontSize: 36 }} />
          </Box>
          <Box>
            <Typography variant="h4" sx={{ fontWeight: 700 }}>
              {release.name}
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5 }}>
              <Chip label={`v${release.version}`} size="small" sx={{ fontWeight: 600, fontFamily: 'monospace' }} />
              <Chip label={release.status} color={release.deployment_ready ? 'success' : 'default'} size="small" />
              {release.deployment_ready && (
                <Chip icon={<CheckCircle />} label="Deployment Ready" color="success" size="small" />
              )}
            </Box>
          </Box>
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button variant="outlined" startIcon={<Edit />} onClick={() => navigate(`/releases/${id}/edit`)}>
            Edit Release
          </Button>
          <Button
            variant="contained"
            startIcon={<PlayArrow />}
            onClick={() => setRunDialogOpen(true)}
            disabled={release.environments.length === 0 || release.projects.length === 0}
            sx={{
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            }}
          >
            Run Tests
          </Button>
        </Box>
      </Box>

      {/* Description */}
      {release.description && (
        <Alert severity="info" sx={{ mb: 3 }}>
          {release.description}
        </Alert>
      )}

      {/* Summary Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    Environments
                  </Typography>
                  <Typography variant="h4" sx={{ fontWeight: 700 }}>
                    {metrics.total_environments}
                  </Typography>
                </Box>
                <CloudQueue sx={{ fontSize: 48, color: 'primary.light' }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    Projects
                  </Typography>
                  <Typography variant="h4" sx={{ fontWeight: 700 }}>
                    {metrics.total_projects}
                  </Typography>
                </Box>
                <Code sx={{ fontSize: 48, color: 'success.light' }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    Total Iterations
                  </Typography>
                  <Typography variant="h4" sx={{ fontWeight: 700 }}>
                    {metrics.total_iterations}
                  </Typography>
                </Box>
                <Speed sx={{ fontSize: 48, color: 'warning.light' }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card sx={{ bgcolor: metrics.overall_pass_rate >= 95 ? 'success.light' : 'error.light' }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography variant="body2" sx={{ mb: 1, opacity: 0.9 }}>
                    Overall Pass Rate
                  </Typography>
                  <Typography variant="h4" sx={{ fontWeight: 700 }}>
                    {metrics.overall_pass_rate.toFixed(1)}%
                  </Typography>
                </Box>
                <TrendingUp sx={{ fontSize: 48, opacity: 0.8 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Pass Rate Trend */}
      {trendData.length > 0 && (
        <Paper sx={{ p: 3, mb: 4 }}>
          <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
            Pass Rate Trend
          </Typography>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={trendData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="iteration" />
              <YAxis domain={[0, 100]} />
              <Tooltip formatter={(value) => `${value.toFixed(1)}%`} />
              <Legend />
              <Line
                type="monotone"
                dataKey="passRate"
                stroke="#2e7d32"
                strokeWidth={3}
                name="Pass Rate %"
                dot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </Paper>
      )}

      {/* Environment Status */}
      <Paper sx={{ p: 3, mb: 4 }}>
        <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
          Environment Status
        </Typography>
        
        {release.environments.length === 0 ? (
          <Alert severity="warning" action={
            <Button size="small" onClick={() => navigate(`/releases/${id}/edit`)}>
              Add Environment
            </Button>
          }>
            No environments configured yet. Add environments to start testing.
          </Alert>
        ) : (
          <Grid container spacing={2}>
            {release.environments.map((env) => {
              const envStats = metrics.environment_stats[env.id];
              const isReady = metrics.ready_environments.includes(env.name);
              
              return (
                <Grid item xs={12} md={6} key={env.id}>
                  <Card variant="outlined" sx={{ bgcolor: isReady ? 'success.lighter' : 'background.paper' }}>
                    <CardContent>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                        <Box>
                          <Typography variant="h6" sx={{ fontWeight: 600, mb: 0.5 }}>
                            {env.name}
                          </Typography>
                          <Chip
                            label={env.type}
                            color={ENV_TYPE_COLORS[env.type]}
                            size="small"
                            sx={{ textTransform: 'capitalize' }}
                          />
                        </Box>
                        {isReady ? (
                          <Chip icon={<CheckCircle />} label="Ready" color="success" size="small" />
                        ) : envStats ? (
                          <Chip icon={<Warning />} label="Blocked" color="warning" size="small" />
                        ) : (
                          <Chip label="Not Tested" color="default" size="small" />
                        )}
                      </Box>
                      
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 2, fontFamily: 'monospace', fontSize: '0.875rem' }}>
                        {env.base_url}
                      </Typography>
                      
                      {envStats ? (
                        <>
                          <Grid container spacing={2}>
                            <Grid item xs={6}>
                              <Typography variant="caption" color="text.secondary">
                                Iterations
                              </Typography>
                              <Typography variant="body1" sx={{ fontWeight: 600 }}>
                                {envStats.total_iterations}
                              </Typography>
                            </Grid>
                            <Grid item xs={6}>
                              <Typography variant="caption" color="text.secondary">
                                Latest Pass Rate
                              </Typography>
                              <Typography variant="body1" sx={{ fontWeight: 600, color: envStats.latest_pass_rate >= 95 ? 'success.main' : 'warning.main' }}>
                                {envStats.latest_pass_rate.toFixed(1)}%
                              </Typography>
                            </Grid>
                          </Grid>
                          <LinearProgress
                            variant="determinate"
                            value={envStats.latest_pass_rate}
                            color={envStats.latest_pass_rate >= 95 ? 'success' : 'warning'}
                            sx={{ mt: 2, height: 8, borderRadius: 1 }}
                          />
                        </>
                      ) : (
                        <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic' }}>
                          No test runs yet
                        </Typography>
                      )}
                    </CardContent>
                  </Card>
                </Grid>
              );
            })}
          </Grid>
        )}
      </Paper>

      {/* Projects Included */}
      <Paper sx={{ p: 3, mb: 4 }}>
        <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
          Projects in Release
        </Typography>
        
        {release.projects.length === 0 ? (
          <Alert severity="warning" action={
            <Button size="small" onClick={() => navigate(`/releases/${id}/edit`)}>
              Add Projects
            </Button>
          }>
            No projects added yet. Add projects to define test scope.
          </Alert>
        ) : (
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 600 }}>Project Name</TableCell>
                  <TableCell sx={{ fontWeight: 600 }} align="center">Test Cases</TableCell>
                  <TableCell sx={{ fontWeight: 600 }} align="center">Status</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {release.projects.map((project) => (
                  <TableRow key={project.project_id}>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Code />
                        <Typography variant="body1" sx={{ fontWeight: 600 }}>
                          {project.project_name}
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell align="center">
                      <Chip
                        label={project.test_case_ids.length}
                        size="small"
                        color="primary"
                        sx={{ fontWeight: 600 }}
                      />
                    </TableCell>
                    <TableCell align="center">
                      <Chip label="Included" color="success" size="small" variant="outlined" />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Paper>

      {/* Recent Iterations */}
      {release.iterations.length > 0 && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
            Recent Test Runs
          </Typography>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 600 }}>Environment</TableCell>
                  <TableCell sx={{ fontWeight: 600 }} align="center">Iteration</TableCell>
                  <TableCell sx={{ fontWeight: 600 }} align="center">Pass Rate</TableCell>
                  <TableCell sx={{ fontWeight: 600 }} align="center">Results</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Executed</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {release.iterations.slice(-10).reverse().map((iteration) => {
                  const env = release.environments.find(e => e.id === iteration.environment_id);
                  return (
                    <TableRow key={iteration.id}>
                      <TableCell>
                        <Chip
                          label={env?.name || 'Unknown'}
                          color={ENV_TYPE_COLORS[env?.type] || 'default'}
                          size="small"
                        />
                      </TableCell>
                      <TableCell align="center">
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>
                          Run #{iteration.iteration_number}
                        </Typography>
                      </TableCell>
                      <TableCell align="center">
                        <Typography
                          variant="body1"
                          sx={{
                            fontWeight: 700,
                            color: iteration.pass_rate >= 95 ? 'success.main' : iteration.pass_rate >= 70 ? 'warning.main' : 'error.main',
                          }}
                        >
                          {iteration.pass_rate.toFixed(1)}%
                        </Typography>
                      </TableCell>
                      <TableCell align="center">
                        <Box sx={{ display: 'flex', justifyContent: 'center', gap: 1 }}>
                          <Chip icon={<CheckCircle />} label={iteration.passed} color="success" size="small" />
                          {iteration.failed > 0 && (
                            <Chip icon={<ErrorIcon />} label={iteration.failed} color="error" size="small" />
                          )}
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" color="text.secondary">
                          {format(new Date(iteration.executed_at), 'MMM dd, yyyy HH:mm')}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>
      )}

      {/* Run Tests Dialog */}
      <Dialog open={runDialogOpen} onClose={() => setRunDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontWeight: 600 }}>Run Release Tests</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 2 }}>
            <FormControl fullWidth required>
              <InputLabel>Environment</InputLabel>
              <Select
                value={selectedEnv}
                label="Environment"
                onChange={(e) => setSelectedEnv(e.target.value)}
              >
                {release.environments.map((env) => (
                  <MenuItem key={env.id} value={env.id}>
                    {env.name} ({env.type})
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            
            <TextField
              label="Notes (Optional)"
              value={runNotes}
              onChange={(e) => setRunNotes(e.target.value)}
              fullWidth
              multiline
              rows={3}
              placeholder="Add notes about this test run..."
            />
            
            <Alert severity="info">
              This will run all {metrics.total_test_cases} test cases across {release.projects.length} projects in the selected environment.
            </Alert>
          </Box>
        </DialogContent>
        <DialogActions sx={{ p: 3 }}>
          <Button onClick={() => setRunDialogOpen(false)} disabled={running}>
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={handleRunTests}
            disabled={!selectedEnv || running}
            startIcon={running ? null : <PlayArrow />}
          >
            {running ? 'Starting...' : 'Run Tests'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}