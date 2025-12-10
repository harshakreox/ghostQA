import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Button,
  Typography,
  Paper,
  Grid,
  Chip,
  LinearProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Breadcrumbs,
  Link,
} from '@mui/material';
import {
  ExpandMore,
  CheckCircle,
  Error,
  Schedule,
  NavigateNext,
  HourglassEmpty,
  Description,
  Code,
  Assessment,
} from '@mui/icons-material';
import axios from 'axios';
import { format } from 'date-fns';

// Import generic components
import { StatsCard, EmptyState } from '../components';

export default function ReportDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadReport();
  }, [id]);

  const loadReport = async () => {
    try {
      const response = await axios.get(`/api/reports/${id}`);
      setReport(response.data);
    } catch (error) {
      console.error('Error loading report:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <LinearProgress />;
  }

  if (!report) {
    return (
      <Box sx={{ py: 8 }}>
        <EmptyState
          icon={Assessment}
          title="Report Not Found"
          description="The report you're looking for doesn't exist or has been deleted"
          actionLabel="Back to Reports"
          onAction={() => navigate('/reports')}
          size="large"
        />
      </Box>
    );
  }

  const passRate = report.total_tests > 0 ? Math.round((report.passed / report.total_tests) * 100) : 0;

  const getStatusIcon = (status) => {
    const statusLower = status?.toLowerCase();
    switch (statusLower) {
      case 'passed':
      case 'pass':
        return <CheckCircle color="success" />;
      case 'failed':
      case 'fail':
      case 'error':
        return <Error color="error" />;
      default:
        return <HourglassEmpty color="warning" />;
    }
  };

  return (
    <Box>
      {/* Breadcrumbs */}
      <Breadcrumbs separator={<NavigateNext fontSize="small" />} sx={{ mb: 3 }}>
        <Link component="button" variant="body2" onClick={() => navigate('/reports')}>
          Reports
        </Link>
        <Typography color="text.primary">{report.project_name}</Typography>
      </Breadcrumbs>

      {/* Header */}
      <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 700, mb: 0.5 }}>
            {report.project_name}
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Schedule fontSize="small" sx={{ color: 'text.secondary' }} />
            <Typography variant="body2" color="text.secondary">
              {format(new Date(report.executed_at), 'MMMM dd, yyyy HH:mm:ss')}
            </Typography>
          </Box>
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button variant="outlined" onClick={() => navigate('/reports')}>
            Back to Reports
          </Button>
          <Button
            variant="contained"
            href={`/api/reports/${report.id}/html`}
            target="_blank"
            startIcon={<Description />}
            sx={{
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            }}
          >
            View HTML Report
          </Button>
        </Box>
      </Box>

      {/* Summary Cards - Using StatsCard component */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={3}>
          <StatsCard label="Total Tests" value={report.total_tests} icon={<Code />} color="primary" />
        </Grid>

        <Grid item xs={12} md={3}>
          <StatsCard label="Passed" value={report.passed} icon={<CheckCircle />} color="success" />
        </Grid>

        <Grid item xs={12} md={3}>
          <StatsCard label="Failed" value={report.failed} icon={<Error />} color="error" />
        </Grid>

        <Grid item xs={12} md={3}>
          <StatsCard label="Duration" value={`${report.duration?.toFixed(1) || 0}s`} icon={<Schedule />} color="primary" />
        </Grid>
      </Grid>

      {/* Pass Rate */}
      <Paper sx={{ p: 3, mb: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            Overall Pass Rate
          </Typography>
          <Typography
            variant="h6"
            sx={{
              fontWeight: 700,
              color: passRate === 100 ? 'success.main' : passRate >= 70 ? 'warning.main' : 'error.main',
            }}
          >
            {passRate}%
          </Typography>
        </Box>
        <LinearProgress
          variant="determinate"
          value={passRate}
          color={passRate === 100 ? 'success' : passRate >= 70 ? 'warning' : 'error'}
          sx={{ height: 12, borderRadius: 2 }}
        />
      </Paper>

      {/* Test Results */}
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
          Test Results Details
        </Typography>

        {report.results?.length === 0 ? (
          <EmptyState icon={Assessment} title="No Test Results" description="No test results available for this report" size="medium" />
        ) : (
          report.results?.map((result, index) => (
            <Accordion
              key={index}
              sx={{
                mb: 2,
                '&:before': { display: 'none' },
                boxShadow: 1,
              }}
            >
              <AccordionSummary
                expandIcon={<ExpandMore />}
                sx={{
                  '&.Mui-expanded': {
                    bgcolor: result.status?.toLowerCase() === 'passed' ? 'success.light' : 'error.light',
                    color: result.status?.toLowerCase() === 'passed' ? 'success.contrastText' : 'error.contrastText',
                  },
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: '100%' }}>
                  {getStatusIcon(result.status)}
                  <Box sx={{ flex: 1 }}>
                    <Typography variant="body1" sx={{ fontWeight: 600 }}>
                      {result.test_case_name}
                    </Typography>
                    <Typography variant="caption" sx={{ opacity: 0.8 }}>
                      Duration: {result.duration?.toFixed(2) || 0}s
                    </Typography>
                  </Box>
                  <Chip
                    label={result.status?.toUpperCase()}
                    color={result.status?.toLowerCase() === 'passed' ? 'success' : 'error'}
                    size="small"
                    sx={{ fontWeight: 600 }}
                  />
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                {/* Test Logs */}
                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                    Execution Logs
                  </Typography>
                  {result.logs?.length > 0 ? (
                    <List dense>
                      {result.logs.map((log, logIndex) => {
                        // Determine icon based on log content
                        const logLower = log.toLowerCase();
                        const isSuccess = log.startsWith('✓') ||
                                         log.startsWith('✔') ||
                                         logLower.includes('passed') ||
                                         logLower.includes('success') ||
                                         logLower.includes('completed') ||
                                         logLower.includes('[pass]');
                        const isError = log.startsWith('✗') ||
                                       log.startsWith('✘') ||
                                       logLower.includes('failed') ||
                                       logLower.includes('error') ||
                                       logLower.includes('[fail]');

                        return (
                          <ListItem key={logIndex}>
                            <ListItemIcon sx={{ minWidth: 32 }}>
                              {isSuccess ? (
                                <CheckCircle fontSize="small" color="success" />
                              ) : isError ? (
                                <Error fontSize="small" color="error" />
                              ) : (
                                <HourglassEmpty fontSize="small" color="action" />
                              )}
                            </ListItemIcon>
                            <ListItemText
                              primary={log}
                              primaryTypographyProps={{
                                variant: 'body2',
                                fontFamily: 'monospace',
                              }}
                            />
                          </ListItem>
                        );
                      })}
                    </List>
                  ) : (
                    <Typography variant="body2" color="text.secondary">
                      No logs available
                    </Typography>
                  )}
                </Box>

                {/* Error Message */}
                {result.error_message && (
                  <Box>
                    <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1, color: 'error.main' }}>
                      Error Details
                    </Typography>
                    <Paper
                      sx={{
                        p: 2,
                        bgcolor: 'error.light',
                        color: 'error.contrastText',
                        fontFamily: 'monospace',
                        fontSize: '0.875rem',
                      }}
                    >
                      {result.error_message}
                    </Paper>
                  </Box>
                )}

                {/* Screenshot */}
                {result.screenshot_path && (
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                      Screenshot
                    </Typography>
                    <Box
                      component="img"
                      src={`/api/reports/${id}/screenshot/${result.screenshot_path.split('/').pop()}`}
                      alt="Test failure screenshot"
                      sx={{
                        maxWidth: '100%',
                        border: '1px solid',
                        borderColor: 'divider',
                        borderRadius: 1,
                      }}
                    />
                  </Box>
                )}
              </AccordionDetails>
            </Accordion>
          ))
        )}
      </Paper>
    </Box>
  );
}
