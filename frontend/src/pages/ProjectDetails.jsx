import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  Box,
  Button,
  Card,
  CardContent,
  Typography,
  Grid,
  Chip,
  IconButton,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  LinearProgress,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Breadcrumbs,
  Link,
  Divider,
  Tabs,
  Tab,
  Stack,
  Snackbar,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  TextField,
  Select,
  FormControl,
  CircularProgress,
  Tooltip,
} from '@mui/material';
import {
  ArrowBack,
  Add,
  PlayArrow,
  Edit,
  Delete,
  MoreVert,
  Code,
  Check,
  NavigateNext,
  Psychology,
  Description,
  Download,
  GetApp,
  Archive,
  ExpandMore,
  Close,
  TableChart,
  Save,
  DragIndicator,
  Link as LinkIcon,
  SmartToy as SmartToyIcon,
} from '@mui/icons-material';
import axios from 'axios';
import AutonomousRunDialog from '../components/AutonomousRunDialog';

// Import generic components and hooks
import { StatsCard, EmptyState, ConfirmDialog, SearchBar } from '../components';
import { useNotification, useContextMenu } from '../hooks';
import { downloadFile } from '../utils';

function TabPanel({ children, value, index }) {
  return (
    <div hidden={value !== index}>
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
}

export default function ProjectDetails() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { isAdmin } = useAuth();
  const [project, setProject] = useState(null);
  const [gherkinFeatures, setGherkinFeatures] = useState([]);
  const [traditionalSuites, setTraditionalSuites] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tabValue, setTabValue] = useState(0);
  const [exportAnchorEl, setExportAnchorEl] = useState(null);
  const [traditionalExportAnchorEl, setTraditionalExportAnchorEl] = useState(null);

  // Search state for filtering
  const [actionSearch, setActionSearch] = useState('');
  const [gherkinSearch, setGherkinSearch] = useState('');
  const [traditionalSearch, setTraditionalSearch] = useState('');

  // Use custom hooks
  const { notification, showNotification, hideNotification } = useNotification();
  const { anchorEl, selectedItem: selectedTestCase, isOpen: menuOpen, openMenu: handleMenuOpen, closeMenu: handleMenuClose } = useContextMenu();

  // Feature detail dialog state
  const [featureDetailDialog, setFeatureDetailDialog] = useState(false);
  const [selectedFeature, setSelectedFeature] = useState(null);

  // Traditional suite detail dialog state
  const [suiteDetailDialog, setSuiteDetailDialog] = useState(false);
  const [selectedSuite, setSelectedSuite] = useState(null);

  // Delete confirmation dialog
  const [deleteDialog, setDeleteDialog] = useState({ open: false, type: '', item: null });

  // Gherkin step editing state
  const [editingScenarioIndex, setEditingScenarioIndex] = useState(null);
  const [editedSteps, setEditedSteps] = useState([]);
  const [savingFeature, setSavingFeature] = useState(false);
  const [draggedStepIndex, setDraggedStepIndex] = useState(null);
  
  // Autonomous Run dialog state
  const [autonomousRunOpen, setAutonomousRunOpen] = useState(false);

  useEffect(() => {
    loadProject();
    loadGherkinFeatures();
    loadTraditionalSuites();
  }, [id]);

  const loadProject = async () => {
    try {
      const response = await axios.get(`/api/projects/${id}`);
      setProject(response.data);
    } catch (error) {
      console.error('Error loading project:', error);
      showNotification('Failed to load project', 'error');
    } finally {
      setLoading(false);
    }
  };

  const loadGherkinFeatures = async () => {
    try {
      const response = await axios.get(`/api/projects/${id}/gherkin-features`);
      setGherkinFeatures(response.data.features || []);
    } catch (error) {
      console.error('Error loading Gherkin features:', error);
      setGherkinFeatures([]);
    }
  };

  const loadTraditionalSuites = async () => {
    try {
      const response = await axios.get(`/api/projects/${id}/traditional-suites`);
      setTraditionalSuites(response.data.suites || []);
    } catch (error) {
      console.error('Error loading Traditional suites:', error);
      setTraditionalSuites([]);
    }
  };

  // Load traditional suite details
  const handleViewSuite = async (suiteId) => {
    try {
      const response = await axios.get(`/api/traditional/suites/${suiteId}`);
      setSelectedSuite(response.data);
      setSuiteDetailDialog(true);
    } catch (error) {
      console.error('Error loading suite:', error);
      showNotification('Failed to load suite details', 'error');
    }
  };

  const handleCloseSuiteDetail = () => {
    setSuiteDetailDialog(false);
    setSelectedSuite(null);
  };

  const handleDeleteTraditionalSuite = async () => {
    if (!deleteDialog.item) return;

    try {
      await axios.delete(`/api/traditional/suites/${deleteDialog.item.id}`);
      showNotification(`Test suite "${deleteDialog.item.name}" deleted successfully`, 'success');
      await loadTraditionalSuites();
      setDeleteDialog({ open: false, type: '', item: null });
    } catch (error) {
      console.error('Error deleting suite:', error);
      showNotification(error.response?.data?.detail || 'Failed to delete test suite', 'error');
    }
  };

  const handleExportTraditionalProject = async (format) => {
    setTraditionalExportAnchorEl(null);

    try {
      const response = await axios.get(
        `/api/projects/${id}/traditional-suites/export?format=${format}`,
        { responseType: 'blob' }
      );

      const filename = format === 'json'
        ? `${project.name.replace(/\s+/g, '_')}_traditional_suites.json`
        : format === 'zip'
        ? `${project.name.replace(/\s+/g, '_')}_traditional_suites.zip`
        : `${project.name.replace(/\s+/g, '_')}_all_test_cases.csv`;

      downloadFile(response.data, filename);
      showNotification(`Exported ${traditionalSuites.length} suite(s) successfully!`, 'success');
    } catch (error) {
      console.error('Error exporting suites:', error);
      showNotification('Failed to export test suites', 'error');
    }
  };

  const handleExportSingleSuite = async (suiteId, suiteName, format = 'csv') => {
    try {
      const endpoint = format === 'json'
        ? `/api/traditional/suites/${suiteId}/export/json`
        : `/api/traditional/suites/${suiteId}/export/csv`;

      const response = await axios.get(endpoint, { responseType: 'blob' });

      const filename = format === 'json'
        ? `${suiteName.replace(/\s+/g, '_')}.json`
        : `${suiteName.replace(/\s+/g, '_')}.csv`;

      downloadFile(response.data, filename);
      showNotification(`Exported ${suiteName} successfully`, 'success');
    } catch (error) {
      console.error('Error exporting suite:', error);
      showNotification('Failed to export test suite', 'error');
    }
  };

  // Load feature details
  const handleViewFeature = async (featureId) => {
    try {
      const response = await axios.get(`/api/gherkin/features/${featureId}`);
      setSelectedFeature(response.data);
      setFeatureDetailDialog(true);
    } catch (error) {
      console.error('Error loading feature:', error);
      showNotification('Failed to load feature details', 'error');
    }
  };

  // ADDED: Close feature detail dialog
  const handleCloseFeatureDetail = () => {
    setFeatureDetailDialog(false);
    setSelectedFeature(null);
    setEditingScenarioIndex(null);
    setEditedSteps([]);
  };

  const handleDeleteTestCase = async () => {
    if (!deleteDialog.item) return;

    try {
      await axios.delete(`/api/projects/${id}/test-cases/${deleteDialog.item.id}`);
      showNotification('Test case deleted successfully', 'success');
      await loadProject();
      setDeleteDialog({ open: false, type: '', item: null });
    } catch (error) {
      console.error('Error deleting test case:', error);
      showNotification(error.response?.data?.detail || 'Failed to delete test case', 'error');
    }
  };

  const handleDeleteGherkinFeature = async () => {
    if (!deleteDialog.item) return;

    try {
      await axios.delete(`/api/gherkin/features/${deleteDialog.item.id}`);
      showNotification(`Feature "${deleteDialog.item.name}" deleted successfully`, 'success');
      await loadGherkinFeatures();
      setDeleteDialog({ open: false, type: '', item: null });
    } catch (error) {
      console.error('Error deleting feature:', error);
      showNotification(error.response?.data?.detail || 'Failed to delete feature', 'error');
    }
  };

  // Handle delete confirmation
  const handleDeleteConfirm = async () => {
    if (deleteDialog.type === 'testcase') {
      await handleDeleteTestCase();
    } else if (deleteDialog.type === 'feature') {
      await handleDeleteGherkinFeature();
    } else if (deleteDialog.type === 'suite') {
      await handleDeleteTraditionalSuite();
    }
  };

  const handleExportProject = async (format) => {
    setExportAnchorEl(null);

    try {
      const response = await axios.get(
        `/api/projects/${id}/gherkin-features/export?format=${format}`,
        { responseType: 'blob' }
      );

      const filename = format === 'json'
        ? `${project.name.replace(/\s+/g, '_')}_features.json`
        : `${project.name.replace(/\s+/g, '_')}_features.zip`;

      downloadFile(response.data, filename);
      showNotification(`Exported ${gherkinFeatures.length} feature(s) successfully!`, 'success');
    } catch (error) {
      console.error('Error exporting features:', error);
      showNotification('Failed to export features', 'error');
    }
  };

  const handleExportSingleFeature = async (featureId, featureName, format = 'feature') => {
    try {
      const endpoint = format === 'json'
        ? `/api/gherkin/features/${featureId}/export/json`
        : `/api/gherkin/features/${featureId}/export`;

      const response = await axios.get(endpoint, { responseType: 'blob' });

      const filename = format === 'json'
        ? `${featureName.replace(/\s+/g, '_')}.json`
        : `${featureName.replace(/\s+/g, '_')}.feature`;

      downloadFile(response.data, filename);
      showNotification(`Exported ${featureName} successfully`, 'success');
    } catch (error) {
      console.error('Error exporting feature:', error);
      showNotification('Failed to export feature', 'error');
    }
  };

  // Gherkin step editing handlers
  const handleStartEditScenario = (scenarioIndex) => {
    const scenario = selectedFeature.scenarios[scenarioIndex];
    setEditingScenarioIndex(scenarioIndex);
    setEditedSteps(scenario.steps ? scenario.steps.map(s => ({
      keyword: s.keyword?.value || s.keyword || 'And',
      text: s.text || ''
    })) : []);
  };

  const handleCancelEdit = () => {
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

  // Drag and drop handlers for step reordering
  const handleDragStart = (e, index) => {
    setDraggedStepIndex(index);
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/html', e.target.outerHTML);
  };

  const handleDragOver = (e, index) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleDrop = (e, dropIndex) => {
    e.preventDefault();
    if (draggedStepIndex === null || draggedStepIndex === dropIndex) return;

    const newSteps = [...editedSteps];
    const [draggedStep] = newSteps.splice(draggedStepIndex, 1);
    newSteps.splice(dropIndex, 0, draggedStep);
    setEditedSteps(newSteps);
    setDraggedStepIndex(null);
  };

  const handleDragEnd = () => {
    setDraggedStepIndex(null);
  };

  const handleSaveScenario = async () => {
    if (!selectedFeature || editingScenarioIndex === null) return;

    setSavingFeature(true);
    try {
      // Create updated feature with edited scenario
      const updatedFeature = {
        ...selectedFeature,
        scenarios: selectedFeature.scenarios.map((s, idx) =>
          idx === editingScenarioIndex
            ? { ...s, steps: editedSteps }
            : s
        )
      };

      // Call API to save
      await axios.put(`/api/gherkin/features/${selectedFeature.id}`, updatedFeature);

      // Update selected feature
      setSelectedFeature(updatedFeature);

      // Update feature list
      await loadGherkinFeatures();

      showNotification('Scenario saved successfully', 'success');
      handleCancelEdit();
    } catch (error) {
      console.error('Error saving scenario:', error);
      showNotification('Failed to save scenario', 'error');
    } finally {
      setSavingFeature(false);
    }
  };

  if (loading) {
    return <LinearProgress />;
  }

  if (!project) {
    return (
      <Box sx={{ textAlign: 'center', py: 8 }}>
        <Typography variant="h6">Project not found</Typography>
      </Box>
    );
  }

  const totalTestCases = (project.test_cases?.length || 0) + (gherkinFeatures?.length || 0) + (traditionalSuites?.length || 0);
  const totalActions = project.test_cases?.reduce((sum, tc) => sum + tc.actions.length, 0) || 0;
  const totalScenarios = gherkinFeatures?.reduce((sum, f) => sum + f.scenario_count, 0) || 0;
  const totalTraditionalCases = traditionalSuites?.reduce((sum, s) => sum + s.test_case_count, 0) || 0;

  // Filter test cases based on search
  const filteredActionTestCases = project?.test_cases?.filter(tc =>
    tc.name.toLowerCase().includes(actionSearch.toLowerCase()) ||
    tc.description?.toLowerCase().includes(actionSearch.toLowerCase())
  ) || [];

  const filteredGherkinFeatures = gherkinFeatures?.filter(f =>
    f.name.toLowerCase().includes(gherkinSearch.toLowerCase()) ||
    f.description?.toLowerCase().includes(gherkinSearch.toLowerCase())
  ) || [];

  const filteredTraditionalSuites = traditionalSuites?.filter(s =>
    s.name.toLowerCase().includes(traditionalSearch.toLowerCase()) ||
    s.description?.toLowerCase().includes(traditionalSearch.toLowerCase())
  ) || [];

  return (
    <Box>
      {/* Breadcrumbs */}
      <Breadcrumbs separator={<NavigateNext fontSize="small" />} sx={{ mb: 3 }}>
        <Link
          component="button"
          variant="body2"
          onClick={() => navigate('/projects')}
          sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}
        >
          Projects
        </Link>
        <Typography color="text.primary">{project.name}</Typography>
      </Breadcrumbs>

      {/* Header */}
      <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
            <Box
              sx={{
                width: 56,
                height: 56,
                borderRadius: 3,
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'white',
              }}
            >
              <Code sx={{ fontSize: 32 }} />
            </Box>
            <Box>
              <Typography variant="h4" sx={{ fontWeight: 700 }}>
                {project.name}
              </Typography>
              <Typography variant="body1" color="text.secondary">
                {project.description}
              </Typography>
            </Box>
          </Box>
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="outlined"
            startIcon={<Edit />}
            onClick={() => navigate(`/projects/${id}/edit`)}
          >
            Edit Project
          </Button>
          {isAdmin && (
            <>
              <Button
                variant="contained"
                startIcon={<SmartToyIcon />}
                onClick={() => setAutonomousRunOpen(true)}
                sx={{
                  background: 'linear-gradient(135deg, #4caf50 0%, #81c784 100%)',
                  boxShadow: '0px 4px 12px rgba(76, 175, 80, 0.4)',
                }}
              >
                Autonomous Run
              </Button>
              <Button
                variant="contained"
                startIcon={<PlayArrow />}
                onClick={() => navigate(`/projects/${id}/run`)}
                sx={{
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  boxShadow: '0px 4px 12px rgba(102, 126, 234, 0.4)',
                }}
              >
                Run Tests
              </Button>
            </>
          )}
          <Button
            variant="contained"
            startIcon={<Psychology />}
            onClick={() => navigate(`/generate?projectId=${id}`)}
            sx={{
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            }}
          >
            Generate with AI
          </Button>
        </Box>
      </Box>

      {/* Stats Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={2.4}>
          <StatsCard
            label="Total Test Cases"
            value={totalTestCases}
            icon={<Code />}
            color="primary"
            onClick={() => setTabValue(0)}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={2.4}>
          <StatsCard
            label="Action-Based"
            value={project.test_cases?.length || 0}
            subtext={`${totalActions} actions`}
            icon={<Code />}
            color="info"
            onClick={() => setTabValue(0)}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={2.4}>
          <StatsCard
            label="Gherkin (BDD)"
            value={gherkinFeatures?.length || 0}
            subtext={`${totalScenarios} scenarios`}
            icon={<Description />}
            color="success"
            onClick={() => setTabValue(1)}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={2.4}>
          <StatsCard
            label="Traditional"
            value={traditionalSuites?.length || 0}
            subtext={`${totalTraditionalCases} test cases`}
            icon={<TableChart />}
            color="warning"
            onClick={() => setTabValue(2)}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={2.4}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 0.5 }}>
                    Base URL
                  </Typography>
                  <Tooltip title={project.base_url || 'Not set'}>
                    <Typography
                      variant="body2"
                      sx={{
                        fontFamily: 'monospace',
                        fontWeight: 600,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {project.base_url || 'Not set'}
                    </Typography>
                  </Tooltip>
                  <Chip label="Active" color="success" size="small" sx={{ fontWeight: 600, mt: 1 }} />
                </Box>
                <Box
                  sx={{
                    width: 48,
                    height: 48,
                    borderRadius: 2,
                    bgcolor: 'grey.100',
                    color: 'grey.600',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                    ml: 1,
                  }}
                >
                  <LinkIcon />
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Test Cases Tabs */}
      <Paper>
        <Tabs value={tabValue} onChange={(e, newValue) => setTabValue(newValue)}>
          <Tab
            label={`Action-Based (${project.test_cases?.length || 0})`}
            icon={<Code />}
            iconPosition="start"
          />
          <Tab
            label={`Gherkin (${gherkinFeatures?.length || 0})`}
            icon={<Description />}
            iconPosition="start"
          />
          <Tab
            label={`Traditional (${traditionalSuites?.length || 0})`}
            icon={<TableChart />}
            iconPosition="start"
          />
        </Tabs>

        {/* Action-Based Test Cases Tab */}
        <TabPanel value={tabValue} index={0}>
          <Box sx={{ p: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              Action-Based Test Cases
            </Typography>
            <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
              <SearchBar
                placeholder="Search test cases..."
                value={actionSearch}
                onSearch={setActionSearch}
              />
              <Button
                variant="contained"
                startIcon={<Add />}
                onClick={() => navigate(`/projects/${id}/test-cases/new`)}
                sx={{ whiteSpace: 'nowrap' }}
              >
                Add Test Case
              </Button>
            </Box>
          </Box>
          <Divider />

          {filteredActionTestCases.length === 0 ? (
            <Box sx={{ p: 8, textAlign: 'center' }}>
              <Code sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
              <Typography variant="h6" sx={{ mb: 1 }}>
                No Action-Based Test Cases Yet
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Create traditional action-based test cases
              </Typography>
              <Button
                variant="contained"
                startIcon={<Add />}
                onClick={() => navigate(`/projects/${id}/test-cases/new`)}
              >
                Create Test Case
              </Button>
            </Box>
          ) : (
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600 }}>Name</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Description</TableCell>
                    <TableCell sx={{ fontWeight: 600 }} align="center">Actions</TableCell>
                    <TableCell sx={{ fontWeight: 600 }} align="center">Status</TableCell>
                    <TableCell sx={{ fontWeight: 600 }} align="right">Menu</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredActionTestCases.map((testCase) => (
                    <TableRow
                      key={testCase.id}
                      sx={{
                        '&:hover': {
                          backgroundColor: 'action.hover',
                          cursor: 'pointer',
                        },
                      }}
                      onClick={() => navigate(`/projects/${id}/test-cases/${testCase.id}/edit`)}
                    >
                      <TableCell>
                        <Typography variant="body1" sx={{ fontWeight: 600 }}>
                          {testCase.name}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" color="text.secondary">
                          {testCase.description}
                        </Typography>
                      </TableCell>
                      <TableCell align="center">
                        <Chip
                          label={testCase.actions.length}
                          size="small"
                          color="primary"
                          sx={{ fontWeight: 600 }}
                        />
                      </TableCell>
                      <TableCell align="center">
                        <Chip
                          label="Ready"
                          size="small"
                          color="success"
                          variant="outlined"
                          sx={{ fontWeight: 600 }}
                        />
                      </TableCell>
                      <TableCell align="right" onClick={(e) => e.stopPropagation()}>
                        <IconButton onClick={(e) => handleMenuOpen(e, testCase)}>
                          <MoreVert />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </TabPanel>

        {/* Gherkin Features Tab */}
        <TabPanel value={tabValue} index={1}>
          <Box sx={{ p: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              Gherkin Features (BDD)
            </Typography>
            <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
              <SearchBar
                placeholder="Search features..."
                value={gherkinSearch}
                onSearch={setGherkinSearch}
              />
              {gherkinFeatures?.length > 0 && (
                <>
                  <Button
                    variant="outlined"
                    startIcon={<Download />}
                    onClick={(e) => setExportAnchorEl(e.currentTarget)}
                  >
                    Export All
                  </Button>
                  <Menu
                    anchorEl={exportAnchorEl}
                    open={Boolean(exportAnchorEl)}
                    onClose={() => setExportAnchorEl(null)}
                  >
                    <MenuItem onClick={() => handleExportProject('zip')}>
                      <ListItemIcon>
                        <Archive fontSize="small" />
                      </ListItemIcon>
                      <ListItemText>
                        Export as ZIP (.feature files)
                      </ListItemText>
                    </MenuItem>
                    <MenuItem onClick={() => handleExportProject('json')}>
                      <ListItemIcon>
                        <GetApp fontSize="small" />
                      </ListItemIcon>
                      <ListItemText>
                        Export as JSON
                      </ListItemText>
                    </MenuItem>
                  </Menu>
                </>
              )}
              <Button
                variant="contained"
                startIcon={<Psychology />}
                onClick={() => navigate(`/generate?projectId=${id}`)}
              >
                Generate with AI
              </Button>
            </Box>
          </Box>
          <Divider />

          {filteredGherkinFeatures.length === 0 ? (
            <Box sx={{ p: 8, textAlign: 'center' }}>
              <Description sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
              <Typography variant="h6" sx={{ mb: 1 }}>
                No Gherkin Features Yet
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Generate BDD test scenarios using AI
              </Typography>
              <Button
                variant="contained"
                startIcon={<Psychology />}
                onClick={() => navigate(`/generate?projectId=${id}`)}
              >
                Generate with AI
              </Button>
            </Box>
          ) : (
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600 }}>Feature Name</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Description</TableCell>
                    <TableCell sx={{ fontWeight: 600 }} align="center">Scenarios</TableCell>
                    <TableCell sx={{ fontWeight: 600 }} align="center">Created</TableCell>
                    <TableCell sx={{ fontWeight: 600 }} align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredGherkinFeatures.map((feature) => (
                    <TableRow
                      key={feature.id}
                      sx={{
                        '&:hover': {
                          backgroundColor: 'action.hover',
                          cursor: 'pointer',
                        },
                      }}
                      onClick={() => handleViewFeature(feature.id)}
                    >
                      <TableCell>
                        <Typography variant="body1" sx={{ fontWeight: 600 }}>
                          {feature.name}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" color="text.secondary">
                          {feature.description || 'No description'}
                        </Typography>
                      </TableCell>
                      <TableCell align="center">
                        <Chip
                          label={feature.scenario_count}
                          size="small"
                          color="success"
                          sx={{ fontWeight: 600 }}
                        />
                      </TableCell>
                      <TableCell align="center">
                        <Typography variant="body2" color="text.secondary">
                          {new Date(feature.created_at).toLocaleDateString()}
                        </Typography>
                      </TableCell>
                      <TableCell align="right" onClick={(e) => e.stopPropagation()}>
                        <Stack direction="row" spacing={1} justifyContent="flex-end">
                          {isAdmin && (
                            <Button
                              size="small"
                              startIcon={<PlayArrow />}
                              onClick={() => navigate(`/run-tests?projectId=${id}&featureId=${feature.id}`)}
                            >
                              Run
                            </Button>
                          )}
                          <Button
                            size="small"
                            startIcon={<Download />}
                            onClick={() => handleExportSingleFeature(feature.id, feature.name, 'feature')}
                          >
                            Export
                          </Button>
                          <IconButton
                            size="small"
                            onClick={(e) => handleMenuOpen(e, { ...feature, isGherkin: true })}
                          >
                            <MoreVert />
                          </IconButton>
                        </Stack>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </TabPanel>

        {/* Traditional Test Suites Tab */}
        <TabPanel value={tabValue} index={2}>
          <Box sx={{ p: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              Traditional Test Suites
            </Typography>
            <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
              <SearchBar
                placeholder="Search suites..."
                value={traditionalSearch}
                onSearch={setTraditionalSearch}
              />
              {traditionalSuites?.length > 0 && (
                <>
                  <Button
                    variant="outlined"
                    startIcon={<Download />}
                    onClick={(e) => setTraditionalExportAnchorEl(e.currentTarget)}
                  >
                    Export All
                  </Button>
                  <Menu
                    anchorEl={traditionalExportAnchorEl}
                    open={Boolean(traditionalExportAnchorEl)}
                    onClose={() => setTraditionalExportAnchorEl(null)}
                  >
                    <MenuItem onClick={() => handleExportTraditionalProject('csv')}>
                      <ListItemIcon>
                        <Download fontSize="small" />
                      </ListItemIcon>
                      <ListItemText>
                        Export as CSV (all test cases)
                      </ListItemText>
                    </MenuItem>
                    <MenuItem onClick={() => handleExportTraditionalProject('zip')}>
                      <ListItemIcon>
                        <Archive fontSize="small" />
                      </ListItemIcon>
                      <ListItemText>
                        Export as ZIP (CSV files)
                      </ListItemText>
                    </MenuItem>
                    <MenuItem onClick={() => handleExportTraditionalProject('json')}>
                      <ListItemIcon>
                        <GetApp fontSize="small" />
                      </ListItemIcon>
                      <ListItemText>
                        Export as JSON
                      </ListItemText>
                    </MenuItem>
                  </Menu>
                </>
              )}
              <Button
                variant="contained"
                startIcon={<Psychology />}
                onClick={() => navigate(`/generate?projectId=${id}`)}
              >
                Generate with AI
              </Button>
            </Box>
          </Box>
          <Divider />

          {filteredTraditionalSuites.length === 0 ? (
            <Box sx={{ p: 8, textAlign: 'center' }}>
              <TableChart sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
              <Typography variant="h6" sx={{ mb: 1 }}>
                No Traditional Test Suites Yet
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Generate traditional table format test cases using AI
              </Typography>
              <Button
                variant="contained"
                startIcon={<Psychology />}
                onClick={() => navigate(`/generate?projectId=${id}`)}
              >
                Generate with AI
              </Button>
            </Box>
          ) : (
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600 }}>Suite Name</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Description</TableCell>
                    <TableCell sx={{ fontWeight: 600 }} align="center">Test Cases</TableCell>
                    <TableCell sx={{ fontWeight: 600 }} align="center">Created</TableCell>
                    <TableCell sx={{ fontWeight: 600 }} align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredTraditionalSuites.map((suite) => (
                    <TableRow
                      key={suite.id}
                      sx={{
                        '&:hover': {
                          backgroundColor: 'action.hover',
                          cursor: 'pointer',
                        },
                      }}
                      onClick={() => handleViewSuite(suite.id)}
                    >
                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <TableChart sx={{ color: 'warning.main', fontSize: 20 }} />
                          <Typography variant="body1" sx={{ fontWeight: 600 }}>
                            {suite.name}
                          </Typography>
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" color="text.secondary">
                          {suite.description || 'No description'}
                        </Typography>
                      </TableCell>
                      <TableCell align="center">
                        <Chip
                          label={suite.test_case_count}
                          size="small"
                          color="warning"
                          sx={{ fontWeight: 600 }}
                        />
                      </TableCell>
                      <TableCell align="center">
                        <Typography variant="body2" color="text.secondary">
                          {new Date(suite.created_at).toLocaleDateString()}
                        </Typography>
                      </TableCell>
                      <TableCell align="right" onClick={(e) => e.stopPropagation()}>
                        <Stack direction="row" spacing={1} justifyContent="flex-end">
                          <Button
                            size="small"
                            startIcon={<Download />}
                            onClick={() => handleExportSingleSuite(suite.id, suite.name, 'csv')}
                          >
                            CSV
                          </Button>
                          <IconButton
                            size="small"
                            onClick={(e) => handleMenuOpen(e, { ...suite, isTraditional: true })}
                          >
                            <MoreVert />
                          </IconButton>
                        </Stack>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </TabPanel>
      </Paper>

      {/* Context Menu */}
      <Menu anchorEl={anchorEl} open={menuOpen} onClose={handleMenuClose}>
        {selectedTestCase?.isTraditional ? (
          <>
            <MenuItem onClick={() => {
              handleViewSuite(selectedTestCase.id);
              handleMenuClose();
            }}>
              <ListItemIcon>
                <TableChart fontSize="small" />
              </ListItemIcon>
              <ListItemText>View Details</ListItemText>
            </MenuItem>
            <Divider />
            <MenuItem onClick={() => {
              handleExportSingleSuite(selectedTestCase.id, selectedTestCase.name, 'csv');
              handleMenuClose();
            }}>
              <ListItemIcon>
                <Download fontSize="small" />
              </ListItemIcon>
              <ListItemText>Export as CSV</ListItemText>
            </MenuItem>
            <MenuItem onClick={() => {
              handleExportSingleSuite(selectedTestCase.id, selectedTestCase.name, 'json');
              handleMenuClose();
            }}>
              <ListItemIcon>
                <GetApp fontSize="small" />
              </ListItemIcon>
              <ListItemText>Export as JSON</ListItemText>
            </MenuItem>
            <Divider />
            <MenuItem
              onClick={() => {
                setDeleteDialog({ open: true, type: 'suite', item: selectedTestCase });
                handleMenuClose();
              }}
            >
              <ListItemIcon>
                <Delete fontSize="small" color="error" />
              </ListItemIcon>
              <ListItemText sx={{ color: 'error.main' }}>Delete Suite</ListItemText>
            </MenuItem>
          </>
        ) : selectedTestCase?.isGherkin ? (
          <>
            <MenuItem onClick={() => {
              handleViewFeature(selectedTestCase.id);
              handleMenuClose();
            }}>
              <ListItemIcon>
                <Description fontSize="small" />
              </ListItemIcon>
              <ListItemText>View Details</ListItemText>
            </MenuItem>
            <Divider />
            <MenuItem onClick={() => {
              handleExportSingleFeature(selectedTestCase.id, selectedTestCase.name, 'feature');
              handleMenuClose();
            }}>
              <ListItemIcon>
                <Download fontSize="small" />
              </ListItemIcon>
              <ListItemText>Export as .feature</ListItemText>
            </MenuItem>
            <MenuItem onClick={() => {
              handleExportSingleFeature(selectedTestCase.id, selectedTestCase.name, 'json');
              handleMenuClose();
            }}>
              <ListItemIcon>
                <GetApp fontSize="small" />
              </ListItemIcon>
              <ListItemText>Export as JSON</ListItemText>
            </MenuItem>
            <Divider />
            <MenuItem
              onClick={() => {
                setDeleteDialog({ open: true, type: 'feature', item: selectedTestCase });
                handleMenuClose();
              }}
            >
              <ListItemIcon>
                <Delete fontSize="small" color="error" />
              </ListItemIcon>
              <ListItemText sx={{ color: 'error.main' }}>Delete Feature</ListItemText>
            </MenuItem>
          </>
        ) : (
          <>
            <MenuItem
              onClick={() => {
                navigate(`/projects/${id}/test-cases/${selectedTestCase?.id}/edit`);
                handleMenuClose();
              }}
            >
              <ListItemIcon>
                <Edit fontSize="small" />
              </ListItemIcon>
              <ListItemText>Edit</ListItemText>
            </MenuItem>
            <MenuItem
              onClick={() => {
                setDeleteDialog({ open: true, type: 'testcase', item: selectedTestCase });
                handleMenuClose();
              }}
            >
              <ListItemIcon>
                <Delete fontSize="small" color="error" />
              </ListItemIcon>
              <ListItemText sx={{ color: 'error.main' }}>Delete</ListItemText>
            </MenuItem>
          </>
        )}
      </Menu>

      {/* Feature Detail Dialog - NEW */}
      <Dialog
        open={featureDetailDialog}
        onClose={handleCloseFeatureDetail}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Box>
              <Typography variant="h5" sx={{ fontWeight: 700 }}>
                {selectedFeature?.name}
              </Typography>
              {selectedFeature?.description && (
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                  {selectedFeature.description}
                </Typography>
              )}
            </Box>
            <IconButton onClick={handleCloseFeatureDetail} size="small">
              <Close />
            </IconButton>
          </Box>
        </DialogTitle>
        
        <DialogContent dividers>
          {selectedFeature && (
            <Box>
              {/* Stats */}
              <Grid container spacing={2} sx={{ mb: 3 }}>
                <Grid item xs={4}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="body2" color="text.secondary">
                        Total Scenarios
                      </Typography>
                      <Typography variant="h4" sx={{ fontWeight: 700 }}>
                        {selectedFeature.scenarios?.length || 0}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={4}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="body2" color="text.secondary">
                        Total Steps
                      </Typography>
                      <Typography variant="h4" sx={{ fontWeight: 700 }}>
                        {selectedFeature.scenarios?.reduce((sum, s) => sum + (s.steps?.length || 0), 0) || 0}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={4}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="body2" color="text.secondary">
                        Created
                      </Typography>
                      <Typography variant="body1" sx={{ fontWeight: 600 }}>
                        {new Date(selectedFeature.created_at).toLocaleDateString()}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>

              {/* Background Steps */}
              {selectedFeature.background && selectedFeature.background.length > 0 && (
                <Box sx={{ mb: 3 }}>
                  <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                    Background
                  </Typography>
                  <Paper sx={{ p: 2, bgcolor: '#f5f5f5' }}>
                    {selectedFeature.background.map((step, idx) => (
                      <Typography 
                        key={idx} 
                        variant="body2" 
                        sx={{ 
                          fontFamily: 'monospace',
                          mb: 0.5,
                          color: step.keyword?.value === 'Given' ? 'green' : 
                                 step.keyword?.value === 'And' ? 'purple' : 'inherit'
                        }}
                      >
                        <strong>{step.keyword?.value || step.keyword}</strong> {step.text}
                      </Typography>
                    ))}
                  </Paper>
                </Box>
              )}

              {/* Scenarios */}
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                Scenarios
              </Typography>
              
              {selectedFeature.scenarios?.map((scenario, index) => (
                <Accordion key={index} defaultExpanded={index === 0}>
                  <AccordionSummary expandIcon={<ExpandMore />}>
                    <Box sx={{ width: '100%' }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
                        <Typography variant="subtitle1" sx={{ fontWeight: 600, flex: 1 }}>
                          {scenario.name}
                        </Typography>
                        <Chip
                          label={`${scenario.steps?.length || 0} steps`}
                          size="small"
                          color="primary"
                        />
                        <Tooltip title="Edit steps">
                          <IconButton
                            size="small"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleStartEditScenario(index);
                            }}
                            sx={{ ml: 1 }}
                          >
                            <Edit fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </Box>
                      {scenario.tags && scenario.tags.length > 0 && (
                        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                          {scenario.tags.map((tag, i) => {
                            const tagColor = 
                              tag.includes('@smoke') ? 'success' :
                              tag.includes('@negative') ? 'error' :
                              tag.includes('@positive') ? 'success' :
                              tag.includes('@edge') ? 'warning' :
                              tag.includes('@workflow') ? 'info' :
                              'default';
                            
                            return (
                              <Chip 
                                key={i} 
                                label={tag} 
                                size="small" 
                                color={tagColor}
                                variant="outlined"
                              />
                            );
                          })}
                        </Box>
                      )}
                    </Box>
                  </AccordionSummary>
                  <AccordionDetails>
                    {scenario.description && (
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        {scenario.description}
                      </Typography>
                    )}
                    
                    {/* Steps */}
                    {editingScenarioIndex === index ? (
                      /* Edit Mode */
                      <Paper sx={{ p: 2, bgcolor: '#fff3e0' }}>
                        <Typography variant="subtitle2" sx={{ mb: 2, fontWeight: 600, color: '#e65100' }}>
                          Editing Steps
                        </Typography>
                        {editedSteps.map((step, i) => (
                          <Box
                            key={i}
                            draggable
                            onDragStart={(e) => handleDragStart(e, i)}
                            onDragOver={(e) => handleDragOver(e, i)}
                            onDrop={(e) => handleDrop(e, i)}
                            onDragEnd={handleDragEnd}
                            sx={{
                              display: 'flex',
                              gap: 1,
                              mb: 1.5,
                              alignItems: 'flex-start',
                              p: 1,
                              borderRadius: 1,
                              bgcolor: draggedStepIndex === i ? 'rgba(102, 126, 234, 0.1)' : 'transparent',
                              border: draggedStepIndex === i ? '2px dashed #667eea' : '2px solid transparent',
                              cursor: 'grab',
                              '&:hover': { bgcolor: 'rgba(0,0,0,0.02)' },
                              transition: 'all 0.2s ease'
                            }}
                          >
                            <Box sx={{ display: 'flex', alignItems: 'center', color: 'text.secondary', cursor: 'grab' }}>
                              <DragIndicator fontSize="small" />
                            </Box>
                            <FormControl size="small" sx={{ minWidth: 90 }}>
                              <Select
                                value={step.keyword || 'And'}
                                onChange={(e) => handleStepChange(i, 'keyword', e.target.value)}
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
                              onChange={(e) => handleStepChange(i, 'text', e.target.value)}
                              placeholder="Step description..."
                            />
                            <IconButton
                              size="small"
                              onClick={() => handleDeleteStep(i)}
                              color="error"
                            >
                              <Delete fontSize="small" />
                            </IconButton>
                          </Box>
                        ))}
                        <Box sx={{ display: 'flex', gap: 1, mt: 2 }}>
                          <Button
                            size="small"
                            startIcon={<Add />}
                            onClick={handleAddStep}
                            variant="outlined"
                          >
                            Add Step
                          </Button>
                          <Box sx={{ flex: 1 }} />
                          <Button
                            size="small"
                            onClick={handleCancelEdit}
                          >
                            Cancel
                          </Button>
                          <Button
                            size="small"
                            variant="contained"
                            startIcon={savingFeature ? <CircularProgress size={14} /> : <Save />}
                            onClick={handleSaveScenario}
                            disabled={savingFeature}
                            sx={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}
                          >
                            {savingFeature ? 'Saving...' : 'Save'}
                          </Button>
                        </Box>
                      </Paper>
                    ) : (
                      /* View Mode */
                      <Paper sx={{ p: 2, bgcolor: '#f5f5f5' }}>
                        {scenario.steps?.map((step, i) => {
                          const keyword = step.keyword?.value || step.keyword || 'Step';
                          const stepColor =
                            keyword === 'Given' ? 'green' :
                            keyword === 'When' ? 'blue' :
                            keyword === 'Then' ? 'orange' :
                            keyword === 'And' ? 'purple' :
                            keyword === 'But' ? 'red' :
                            'inherit';

                          return (
                            <Typography
                              key={i}
                              variant="body2"
                              sx={{
                                fontFamily: 'monospace',
                                mb: 0.5,
                                pl: 2
                              }}
                            >
                              <strong style={{ color: stepColor }}>{keyword}</strong> {step.text}
                            </Typography>
                          );
                        })}
                      </Paper>
                    )}

                    {/* Examples Table */}
                    {scenario.examples && scenario.examples.length > 0 && (
                      <Box sx={{ mt: 2 }}>
                        <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                          Examples:
                        </Typography>
                        <TableContainer component={Paper} variant="outlined">
                          <Table size="small">
                            <TableHead>
                              <TableRow>
                                {Object.keys(scenario.examples[0] || {}).map((header, i) => (
                                  <TableCell key={i} sx={{ fontWeight: 600 }}>
                                    {header}
                                  </TableCell>
                                ))}
                              </TableRow>
                            </TableHead>
                            <TableBody>
                              {scenario.examples.map((example, i) => (
                                <TableRow key={i}>
                                  {Object.values(example).map((value, j) => (
                                    <TableCell key={j}>{value}</TableCell>
                                  ))}
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </TableContainer>
                      </Box>
                    )}
                  </AccordionDetails>
                </Accordion>
              ))}
            </Box>
          )}
        </DialogContent>
        
        <DialogActions>
          <Button onClick={handleCloseFeatureDetail}>
            Close
          </Button>
          {isAdmin && (
            <Button
              variant="outlined"
              startIcon={<PlayArrow />}
              onClick={() => {
                handleCloseFeatureDetail();
                navigate(`/run-tests?projectId=${id}&featureId=${selectedFeature.id}`);
              }}
            >
              Run Feature
            </Button>
          )}
          <Button
            variant="contained"
            startIcon={<Download />}
            onClick={() => {
              handleExportSingleFeature(selectedFeature.id, selectedFeature.name, 'feature');
            }}
          >
            Export
          </Button>
        </DialogActions>
      </Dialog>

      {/* Traditional Suite Detail Dialog */}
      <Dialog
        open={suiteDetailDialog}
        onClose={handleCloseSuiteDetail}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <TableChart sx={{ color: 'warning.main' }} />
              <Box>
                <Typography variant="h5" sx={{ fontWeight: 700 }}>
                  {selectedSuite?.name}
                </Typography>
                {selectedSuite?.description && (
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                    {selectedSuite.description}
                  </Typography>
                )}
              </Box>
            </Box>
            <IconButton onClick={handleCloseSuiteDetail} size="small">
              <Close />
            </IconButton>
          </Box>
        </DialogTitle>

        <DialogContent dividers>
          {selectedSuite && (
            <Box>
              {/* Stats */}
              <Grid container spacing={2} sx={{ mb: 3 }}>
                <Grid item xs={4}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="body2" color="text.secondary">
                        Total Test Cases
                      </Typography>
                      <Typography variant="h4" sx={{ fontWeight: 700 }}>
                        {selectedSuite.test_cases?.length || 0}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={4}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="body2" color="text.secondary">
                        Format
                      </Typography>
                      <Typography variant="h4" sx={{ fontWeight: 700 }}>
                        Table
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={4}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="body2" color="text.secondary">
                        Created
                      </Typography>
                      <Typography variant="body1" sx={{ fontWeight: 600 }}>
                        {selectedSuite.created_at && new Date(selectedSuite.created_at).toLocaleDateString()}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>

              {/* Test Cases Table */}
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                Test Cases
              </Typography>

              <TableContainer component={Paper} variant="outlined">
                <Table size="small">
                  <TableHead>
                    <TableRow sx={{ bgcolor: '#f5f5f5' }}>
                      <TableCell sx={{ fontWeight: 600, minWidth: 80 }}>TC No</TableCell>
                      <TableCell sx={{ fontWeight: 600, minWidth: 180 }}>Scenario Name</TableCell>
                      <TableCell sx={{ fontWeight: 600, minWidth: 180 }}>Precondition</TableCell>
                      <TableCell sx={{ fontWeight: 600, minWidth: 200 }}>Steps</TableCell>
                      <TableCell sx={{ fontWeight: 600, minWidth: 180 }}>Expected Outcome</TableCell>
                      <TableCell sx={{ fontWeight: 600, minWidth: 150 }}>Post Condition</TableCell>
                      <TableCell sx={{ fontWeight: 600, minWidth: 100 }}>Tags</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {selectedSuite.test_cases?.map((tc, index) => (
                      <TableRow key={index} sx={{ '&:hover': { bgcolor: 'action.hover' } }}>
                        <TableCell>
                          <Chip
                            label={`TC${String(tc.test_case_no).padStart(3, '0')}`}
                            size="small"
                            color="primary"
                          />
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" sx={{ fontWeight: 600 }}>
                            {tc.scenario_name}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" sx={{ whiteSpace: 'pre-line', fontSize: '0.8rem' }}>
                            {tc.precondition}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" sx={{ whiteSpace: 'pre-line', fontSize: '0.8rem' }}>
                            {tc.steps}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" sx={{ whiteSpace: 'pre-line', fontSize: '0.8rem' }}>
                            {tc.expected_outcome}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" sx={{ whiteSpace: 'pre-line', fontSize: '0.8rem' }}>
                            {tc.post_condition}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                            {tc.tags?.map((tag, i) => {
                              const tagColor =
                                tag.includes('@smoke') ? 'success' :
                                tag.includes('@negative') ? 'error' :
                                tag.includes('@positive') ? 'success' :
                                tag.includes('@edge') ? 'warning' :
                                'default';
                              return (
                                <Chip
                                  key={i}
                                  label={tag}
                                  size="small"
                                  color={tagColor}
                                  variant="outlined"
                                />
                              );
                            })}
                          </Box>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </Box>
          )}
        </DialogContent>

        <DialogActions>
          <Button onClick={handleCloseSuiteDetail}>
            Close
          </Button>
          <Button
            variant="outlined"
            startIcon={<Download />}
            onClick={() => {
              handleExportSingleSuite(selectedSuite.id, selectedSuite.name, 'csv');
            }}
          >
            Export CSV
          </Button>
          <Button
            variant="contained"
            startIcon={<GetApp />}
            onClick={() => {
              handleExportSingleSuite(selectedSuite.id, selectedSuite.name, 'json');
            }}
          >
            Export JSON
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={deleteDialog.open}
        onClose={() => setDeleteDialog({ open: false, type: '', item: null })}
        onConfirm={handleDeleteConfirm}
        title={
          deleteDialog.type === 'testcase' ? 'Delete Test Case?' :
          deleteDialog.type === 'feature' ? 'Delete Feature?' :
          deleteDialog.type === 'suite' ? 'Delete Test Suite?' : 'Delete?'
        }
        message={`Are you sure you want to delete "${deleteDialog.item?.name}"? This action cannot be undone.`}
        confirmLabel="Delete"
        type="delete"
      />

      {/* Snackbar */}
      {/* Autonomous Run Dialog */}
      <AutonomousRunDialog
        open={autonomousRunOpen}
        onClose={() => setAutonomousRunOpen(false)}
        project={project}
      />

      <Snackbar
        open={notification.open}
        autoHideDuration={6000}
        onClose={hideNotification}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert onClose={hideNotification} severity={notification.severity} sx={{ width: '100%' }}>
          {notification.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}