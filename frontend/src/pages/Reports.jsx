import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Chip,
  LinearProgress,
  IconButton,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Snackbar,
  Alert,
} from '@mui/material';
import {
  Refresh,
  MoreVert,
  Visibility,
  Delete,
  CheckCircle,
  Error,
  Assessment,
  Schedule,
  FolderOpen,
} from '@mui/icons-material';
import { format } from 'date-fns';

// Import generic components and hooks
import { PageHeader, EmptyState, ConfirmDialog, SearchBar } from '../components';
import { useApiData, useContextMenu, useNotification } from '../hooks';

export default function Reports() {
  const navigate = useNavigate();

  // Use custom hooks
  const {
    data: reports = [],
    loading,
    refetch,
    setData: setReports,
  } = useApiData('/api/reports', {
    initialData: [],
    transform: (data) => data.sort((a, b) => new Date(b.executed_at) - new Date(a.executed_at)),
  });

  const { anchorEl, selectedItem: selectedReport, isOpen, openMenu, closeMenu } = useContextMenu();
  const { notification, showNotification, hideNotification } = useNotification();

  // Search state
  const [searchQuery, setSearchQuery] = useState('');

  // Dialog states
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [reportToDelete, setReportToDelete] = useState(null);

  const handleDeleteClick = (report) => {
    setReportToDelete(report);
    setDeleteDialogOpen(true);
    closeMenu();
  };

  const handleDeleteConfirm = async () => {
    if (!reportToDelete) return;

    setDeleting(true);
    try {
      await fetch(`/api/reports/${reportToDelete.id}`, { method: 'DELETE' });
      setReports(reports.filter((r) => r.id !== reportToDelete.id));
      showNotification('Report deleted successfully', 'success');
    } catch (error) {
      console.error('Error deleting report:', error);
      showNotification('Failed to delete report', 'error');
    } finally {
      setDeleting(false);
      setDeleteDialogOpen(false);
      setReportToDelete(null);
    }
  };

  const getPassRate = (report) => {
    return report.total_tests > 0 ? Math.round((report.passed / report.total_tests) * 100) : 0;
  };

  const getStatusColor = (passRate) => {
    if (passRate === 100) return 'success';
    if (passRate >= 70) return 'warning';
    return 'error';
  };

  if (loading) {
    return <LinearProgress />;
  }

  // Filter reports based on search
  const filteredReports = reports.filter(report =>
    report.project_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    report.test_case_name?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <Box>
      {/* Page Header - Using generic component */}
      <PageHeader
        title="Test Reports"
        subtitle="View and analyze test execution results"
        actions={[
          {
            label: 'Refresh',
            icon: <Refresh />,
            onClick: refetch,
            variant: 'outlined',
          },
        ]}
      />

      {/* Search Bar */}
      {reports.length > 0 && (
        <Box sx={{ mb: 3, maxWidth: 400 }}>
          <SearchBar
            placeholder="Search reports..."
            value={searchQuery}
            onSearch={setSearchQuery}
          />
        </Box>
      )}

      {filteredReports.length === 0 && searchQuery ? (
        <Card sx={{ p: 4, textAlign: 'center' }}>
          <Typography variant="h6" color="text.secondary">
            No reports found matching "{searchQuery}"
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            Try a different search term
          </Typography>
        </Card>
      ) : reports.length === 0 ? (
        <Card sx={{ p: 4 }}>
          <EmptyState
            icon={Assessment}
            title="No Test Reports Yet"
            description="Run your first test to generate reports"
            actionLabel="Go to Projects"
            actionIcon={<FolderOpen />}
            onAction={() => navigate('/projects')}
            size="large"
          />
        </Card>
      ) : (
        <Grid container spacing={3}>
          {filteredReports.map((report) => {
            const passRate = getPassRate(report);
            const statusColor = getStatusColor(passRate);

            return (
              <Grid item xs={12} md={6} lg={4} key={report.id}>
                <Card
                  sx={{
                    height: '100%',
                    cursor: 'pointer',
                    '&:hover': {
                      boxShadow: 6,
                      transform: 'translateY(-4px)',
                    },
                    transition: 'all 0.2s',
                  }}
                  onClick={() => navigate(`/reports/${report.id}`)}
                >
                  <CardContent>
                    {/* Header */}
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                      <Box sx={{ flex: 1 }}>
                        <Typography variant="h6" sx={{ fontWeight: 600, mb: 0.5 }}>
                          {report.project_name}
                        </Typography>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                          <Schedule fontSize="small" sx={{ color: 'text.secondary' }} />
                          <Typography variant="caption" color="text.secondary">
                            {format(new Date(report.executed_at), 'MMM dd, yyyy HH:mm')}
                          </Typography>
                        </Box>
                      </Box>
                      <IconButton
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation();
                          openMenu(e, report);
                        }}
                      >
                        <MoreVert />
                      </IconButton>
                    </Box>

                    {/* Pass Rate */}
                    <Box sx={{ mb: 2 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>
                          Pass Rate
                        </Typography>
                        <Typography variant="body2" color={`${statusColor}.main`} sx={{ fontWeight: 700 }}>
                          {passRate}%
                        </Typography>
                      </Box>
                      <LinearProgress
                        variant="determinate"
                        value={passRate}
                        color={statusColor}
                        sx={{ height: 8, borderRadius: 1 }}
                      />
                    </Box>

                    {/* Stats */}
                    <Box sx={{ display: 'flex', gap: 1, mb: 2, flexWrap: 'wrap' }}>
                      <Chip
                        icon={<CheckCircle />}
                        label={`${report.passed} Passed`}
                        color="success"
                        size="small"
                        sx={{ fontWeight: 600 }}
                      />
                      {report.failed > 0 && (
                        <Chip
                          icon={<Error />}
                          label={`${report.failed} Failed`}
                          color="error"
                          size="small"
                          sx={{ fontWeight: 600 }}
                        />
                      )}
                      {report.skipped > 0 && (
                        <Chip label={`${report.skipped} Skipped`} size="small" sx={{ fontWeight: 600 }} />
                      )}
                    </Box>

                    {/* Duration */}
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Typography variant="body2" color="text.secondary">
                        Duration
                      </Typography>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        {report.duration?.toFixed(1)}s
                      </Typography>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            );
          })}
        </Grid>
      )}

      {/* Report Menu */}
      <Menu anchorEl={anchorEl} open={isOpen} onClose={closeMenu}>
        <MenuItem
          onClick={() => {
            navigate(`/reports/${selectedReport?.id}`);
            closeMenu();
          }}
        >
          <ListItemIcon>
            <Visibility fontSize="small" />
          </ListItemIcon>
          <ListItemText>View Details</ListItemText>
        </MenuItem>
        <MenuItem onClick={() => handleDeleteClick(selectedReport)}>
          <ListItemIcon>
            <Delete fontSize="small" color="error" />
          </ListItemIcon>
          <ListItemText sx={{ color: 'error.main' }}>Delete Report</ListItemText>
        </MenuItem>
      </Menu>

      {/* Delete Confirmation Dialog - Using generic component */}
      <ConfirmDialog
        open={deleteDialogOpen}
        onClose={() => {
          setDeleteDialogOpen(false);
          setReportToDelete(null);
        }}
        onConfirm={handleDeleteConfirm}
        title="Delete Report?"
        message={`Are you sure you want to delete the report for "${reportToDelete?.project_name}"? This action cannot be undone.`}
        confirmLabel="Delete"
        type="delete"
        loading={deleting}
      />

      {/* Snackbar for notifications - Using hook state */}
      <Snackbar
        open={notification.open}
        autoHideDuration={4000}
        onClose={hideNotification}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert onClose={hideNotification} severity={notification.severity} variant="filled" sx={{ width: '100%' }}>
          {notification.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}
