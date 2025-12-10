import { useNavigate } from 'react-router-dom';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  LinearProgress,
  Chip,
  Paper,
} from '@mui/material';
import {
  TrendingUp,
  CheckCircle,
  Error,
  Schedule,
  PlayArrow,
  Add,
  Refresh,
} from '@mui/icons-material';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts';

// Import generic components and hooks
import { StatsCard, PageHeader, EmptyState } from '../components';
import { useApiData } from '../hooks';

const COLORS = ['#2e7d32', '#d32f2f', '#ed6c02'];

export default function Dashboard() {
  const navigate = useNavigate();

  // Fetch projects and reports separately
  const { data: projects = [], loading: loadingProjects } = useApiData('/api/projects', {
    initialData: [],
  });

  const { data: reports = [], loading: loadingReports, refetch: refetchReports } = useApiData('/api/reports', {
    initialData: [],
  });

  const loading = loadingProjects || loadingReports;

  // Calculate stats
  const totalTests = projects.reduce((sum, p) => sum + (p.test_cases?.length || 0), 0);
  const passedTests = reports.reduce((sum, r) => sum + (r.passed || 0), 0);
  const totalTestRuns = reports.reduce((sum, r) => sum + (r.total_tests || 0), 0);
  const passRate = totalTestRuns > 0 ? Math.round((passedTests / totalTestRuns) * 100) : 0;

  const recentReports = reports.slice(0, 5);

  const chartData = recentReports.map((report) => ({
    name: report.project_name?.substring(0, 10) || 'Unknown',
    Passed: report.passed || 0,
    Failed: report.failed || 0,
    Skipped: report.skipped || 0,
  }));

  const pieData = [
    { name: 'Passed', value: recentReports.reduce((sum, r) => sum + (r.passed || 0), 0) },
    { name: 'Failed', value: recentReports.reduce((sum, r) => sum + (r.failed || 0), 0) },
    { name: 'Skipped', value: recentReports.reduce((sum, r) => sum + (r.skipped || 0), 0) },
  ];

  if (loading) {
    return <LinearProgress />;
  }

  return (
    <Box>
      {/* Page Header - Using generic component */}
      <PageHeader
        title="Dashboard"
        subtitle="Welcome back! Here's your testing overview"
        actions={[
          {
            label: 'Refresh',
            icon: <Refresh />,
            onClick: refetchReports,
            variant: 'outlined',
          },
          {
            label: 'New Project',
            icon: <Add />,
            onClick: () => navigate('/projects'),
            variant: 'contained',
            gradient: true,
          },
        ]}
      />

      {/* Metrics Cards - Using StatsCard component */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <StatsCard
            label="Total Projects"
            value={projects.length}
            icon={<TrendingUp />}
            gradient
          />
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <StatsCard
            label="Test Cases"
            value={totalTests}
            icon={<CheckCircle />}
            color="success"
          />
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <StatsCard
            label="Test Runs"
            value={reports.length}
            icon={<PlayArrow />}
            color="primary"
          />
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <StatsCard
            label="Pass Rate"
            value={`${passRate}%`}
            icon={<TrendingUp />}
            color="success"
            progress={passRate}
          />
        </Grid>
      </Grid>

      {/* Charts */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
              Recent Test Results
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis
                  dataKey="name"
                  tick={{ fontSize: 12 }}
                  interval={0}
                  angle={-45}
                  textAnchor="end"
                  height={80}
                />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'rgba(255, 255, 255, 0.95)',
                    border: '1px solid #ccc',
                    borderRadius: '4px',
                  }}
                />
                <Bar dataKey="Passed" fill="#2e7d32" radius={[8, 8, 0, 0]} />
                <Bar dataKey="Failed" fill="#d32f2f" radius={[8, 8, 0, 0]} />
                <Bar dataKey="Skipped" fill="#ed6c02" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
              Test Distribution
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="45%"
                  outerRadius={70}
                  fill="#8884d8"
                  dataKey="value"
                  label={false}
                >
                  {pieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(value) => `${value} tests`}
                  contentStyle={{
                    backgroundColor: 'rgba(255, 255, 255, 0.95)',
                    border: '1px solid #ccc',
                    borderRadius: '4px',
                  }}
                />
                <Legend
                  verticalAlign="bottom"
                  height={36}
                  iconType="circle"
                  formatter={(value, entry) => `${value}: ${entry.payload.value}`}
                />
              </PieChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>
      </Grid>

      {/* Recent Reports */}
      <Paper sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            Recent Test Runs
          </Typography>
          <Typography
            variant="body2"
            color="primary"
            sx={{ cursor: 'pointer', '&:hover': { textDecoration: 'underline' } }}
            onClick={() => navigate('/reports')}
          >
            View All
          </Typography>
        </Box>

        {recentReports.length === 0 ? (
          <EmptyState
            icon={Schedule}
            title="No test runs yet"
            description="Start by creating a project and running tests."
            size="medium"
          />
        ) : (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {recentReports.map((report) => (
              <Card
                key={report.id}
                sx={{
                  cursor: 'pointer',
                  '&:hover': { boxShadow: 4 },
                  transition: 'all 0.2s',
                }}
                onClick={() => navigate(`/reports/${report.id}`)}
              >
                <CardContent>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Box sx={{ flex: 1 }}>
                      <Typography variant="h6" sx={{ fontWeight: 600, mb: 0.5 }}>
                        {report.project_name}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {new Date(report.executed_at).toLocaleString()}
                      </Typography>
                    </Box>
                    <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                      <Chip
                        icon={<CheckCircle />}
                        label={`${report.passed || 0} Passed`}
                        color="success"
                        size="small"
                      />
                      {(report.failed || 0) > 0 && (
                        <Chip
                          icon={<Error />}
                          label={`${report.failed} Failed`}
                          color="error"
                          size="small"
                        />
                      )}
                      <Typography variant="body2" color="text.secondary" sx={{ ml: 2 }}>
                        {report.duration?.toFixed(1)}s
                      </Typography>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            ))}
          </Box>
        )}
      </Paper>
    </Box>
  );
}
