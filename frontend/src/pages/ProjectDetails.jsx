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
  alpha,
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
  CreateNewFolder,
  Folder as FolderIcon,
  DriveFileMove,
  Group,
} from '@mui/icons-material';
import axios from 'axios';
import AutonomousRunDialog from '../components/AutonomousRunDialog';
import ProjectMembers from '../components/ProjectMembers';

// Import generic components and hooks
import { StatsCard, EmptyState, ConfirmDialog, SearchBar, FolderNavigation, FolderDialog } from '../components';
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
  const [membersDialogOpen, setMembersDialogOpen] = useState(false);

  // Folder management state
  const [folders, setFolders] = useState([]);
  const [folderTree, setFolderTree] = useState([]);
  const [featuresByFolder, setFeaturesByFolder] = useState({});
  const [rootFeatures, setRootFeatures] = useState([]);
  const [selectedFolderId, setSelectedFolderId] = useState(null);
  const [folderDialogOpen, setFolderDialogOpen] = useState(false);
  const [folderDialogMode, setFolderDialogMode] = useState('create');
  const [editingFolder, setEditingFolder] = useState(null);
  const [movingFeature, setMovingFeature] = useState(null);
  const [folderParentId, setFolderParentId] = useState(null);
  const [foldersLoading, setFoldersLoading] = useState(false);

  useEffect(() => {
    loadProject();
    loadGherkinFeatures();
    loadTraditionalSuites();
    loadFoldersWithFeatures();
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


  // Load folders and features organized by folder
  const loadFoldersWithFeatures = async () => {
    setFoldersLoading(true);
    try {
      const response = await axios.get(`/api/projects/${id}/features-with-folders`);
      setFolderTree(response.data.folder_tree || []);
      setFeaturesByFolder(response.data.features_by_folder || {});
      setRootFeatures(response.data.root_features || []);

      const foldersRes = await axios.get(`/api/projects/${id}/folders`);
      setFolders(foldersRes.data.folders || []);
    } catch (error) {
      console.error('Error loading folders:', error);
      setFolderTree([]);
      setFeaturesByFolder({});
      setRootFeatures([]);
    } finally {
      setFoldersLoading(false);
    }
  };

  // Check if we're in folder view mode
  const inFolderView = selectedFolderId !== null;

  // Get folder path for breadcrumbs
  const getFolderPath = (folderId) => {
    if (!folderId) return [];
    const path = [];
    let currentId = folderId;
    while (currentId) {
      const folder = folders.find(f => f.id === currentId);
      if (folder) {
        path.unshift(folder);
        currentId = folder.parent_folder_id;
      } else {
        break;
      }
    }
    return path;
  };

  const handleCreateFolder = (parentId = null) => {
    setFolderDialogMode('create');
    setFolderParentId(parentId);
    setEditingFolder(null);
    setFolderDialogOpen(true);
  };

  const handleRenameFolder = (folder) => {
    setFolderDialogMode('edit');
    setEditingFolder(folder);
    setFolderDialogOpen(true);
  };

  const handleDeleteFolderAction = async (folder) => {
    if (!window.confirm(`Delete folder "${folder.name}"? Features will be moved to root.`)) {
      return;
    }
    try {
      await axios.delete(`/api/folders/${folder.id}`);
      showNotification(`Folder "${folder.name}" deleted`, 'success');
      await loadFoldersWithFeatures();
      await loadGherkinFeatures();
    } catch (error) {
      console.error('Error deleting folder:', error);
      showNotification('Failed to delete folder', 'error');
    }
  };

  const handleMoveFeature = (feature) => {
    setFolderDialogMode('move-feature');
    setMovingFeature(feature);
    setFolderDialogOpen(true);
  };

  const handleFolderDialogSubmit = async (data) => {
    try {
      if (folderDialogMode === 'create') {
        await axios.post(`/api/projects/${id}/folders`, data);
        showNotification('Folder created', 'success');
      } else if (folderDialogMode === 'edit') {
        await axios.put(`/api/folders/${editingFolder.id}`, data);
        showNotification('Folder updated', 'success');
      } else if (folderDialogMode === 'move-feature') {
        await axios.put(`/api/gherkin/features/${movingFeature.id}/move`, data);
        showNotification('Feature moved', 'success');
      }
      setFolderDialogOpen(false);
      await loadFoldersWithFeatures();
      await loadGherkinFeatures();
    } catch (error) {
      console.error('Error:', error);
      showNotification(error.response?.data?.detail || 'Operation failed', 'error');
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
            startIcon={<Group />}
            onClick={() => setMembersDialogOpen(true)}
          >
            Team
          </Button>
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


      {/* Folder Explorer View - shown when inside a folder */}
      {inFolderView && (
        <Box>
          {/* Breadcrumb Navigation */}
          <Paper sx={{ p: 2, mb: 3, bgcolor: 'grey.50' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <IconButton
                onClick={() => setSelectedFolderId(null)}
                sx={{
                  bgcolor: 'white',
                  boxShadow: 1,
                  '&:hover': { bgcolor: 'grey.100' }
                }}
              >
                <ArrowBack />
              </IconButton>
              <Breadcrumbs separator={<NavigateNext fontSize="small" />} sx={{ flex: 1 }}>
                <Link
                  component="button"
                  variant="body1"
                  onClick={() => setSelectedFolderId(null)}
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 0.5,
                    fontWeight: 500,
                  }}
                  underline="hover"
                >
                  <Code sx={{ fontSize: 20 }} />
                  {project.name}
                </Link>
                <Link
                  component="button"
                  variant="body1"
                  onClick={() => setSelectedFolderId(null)}
                  underline="hover"
                >
                  Features
                </Link>
                {getFolderPath(selectedFolderId).map((folder, index, arr) => (
                  <Link
                    key={folder.id}
                    component="button"
                    variant="body1"
                    onClick={() => setSelectedFolderId(folder.id)}
                    underline={index === arr.length - 1 ? 'none' : 'hover'}
                    sx={{
                      fontWeight: index === arr.length - 1 ? 600 : 400,
                      color: index === arr.length - 1 ? 'text.primary' : 'inherit',
                    }}
                  >
                    {folder.name}
                  </Link>
                ))}
              </Breadcrumbs>
            </Box>
          </Paper>

          {/* Current Folder Info */}
          <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', gap: 2 }}>
            <Box
              sx={{
                width: 56,
                height: 56,
                borderRadius: 3,
                background: 'linear-gradient(135deg, #ffa726 0%, #fb8c00 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'white',
              }}
            >
              <FolderIcon sx={{ fontSize: 32 }} />
            </Box>
            <Box sx={{ flex: 1 }}>
              <Typography variant="h5" sx={{ fontWeight: 700 }}>
                {getFolderPath(selectedFolderId).slice(-1)[0]?.name || 'Folder'}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {(featuresByFolder[selectedFolderId] || []).length} features
                {folders.filter(f => f.parent_folder_id === selectedFolderId).length > 0 &&
                  ` • ${folders.filter(f => f.parent_folder_id === selectedFolderId).length} subfolders`}
              </Typography>
            </Box>
            <Button
              variant="contained"
              startIcon={<CreateNewFolder />}
              onClick={() => handleCreateFolder(selectedFolderId)}
              sx={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}
            >
              New Subfolder
            </Button>
            <Button
              variant="contained"
              startIcon={<Psychology />}
              onClick={() => navigate(`/generate?projectId=${id}&folderId=${selectedFolderId}`)}
            >
              Generate with AI
            </Button>
          </Box>

          {/* Subfolders */}
          {folders.filter(f => f.parent_folder_id === selectedFolderId).length > 0 && (
            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 600, color: 'text.secondary', mb: 1.5, px: 1 }}>
                SUBFOLDERS
              </Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1.5 }}>
                {folders.filter(f => f.parent_folder_id === selectedFolderId).map((folder) => (
                  <Card
                    key={folder.id}
                    variant="outlined"
                    sx={{
                      minWidth: 160,
                      cursor: 'pointer',
                      transition: 'all 0.2s',
                      '&:hover': {
                        borderColor: 'primary.main',
                        transform: 'translateY(-2px)',
                        boxShadow: 2,
                      },
                    }}
                    onClick={() => setSelectedFolderId(folder.id)}
                  >
                    <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <FolderIcon sx={{ color: 'warning.main', fontSize: 28 }} />
                        <Box sx={{ flex: 1, minWidth: 0 }}>
                          <Typography variant="body2" sx={{ fontWeight: 600 }} noWrap>
                            {folder.name}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {(featuresByFolder[folder.id] || []).length} features
                          </Typography>
                        </Box>
                        <IconButton
                          size="small"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleMenuOpen(e, { ...folder, isFolder: true });
                          }}
                        >
                          <MoreVert fontSize="small" />
                        </IconButton>
                      </Box>
                    </CardContent>
                  </Card>
                ))}
              </Box>
            </Box>
          )}

          {/* Features in this folder */}
          <Paper>
            <Box sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 600, color: 'text.secondary' }}>
                FEATURES ({(featuresByFolder[selectedFolderId] || []).length})
              </Typography>
              <Box sx={{ display: 'flex', gap: 1 }}>
                <SearchBar
                  placeholder="Search features..."
                  value={gherkinSearch}
                  onSearch={setGherkinSearch}
                />
                {(featuresByFolder[selectedFolderId] || []).length > 0 && (
                  <Button
                    variant="outlined"
                    size="small"
                    startIcon={<Download />}
                    onClick={(e) => setExportAnchorEl(e.currentTarget)}
                  >
                    Export
                  </Button>
                )}
              </Box>
            </Box>
            <Divider />

            {(() => {
              const folderFeatures = featuresByFolder[selectedFolderId] || [];
              const filtered = folderFeatures.filter(f =>
                f.name.toLowerCase().includes(gherkinSearch.toLowerCase()) ||
                f.description?.toLowerCase().includes(gherkinSearch.toLowerCase())
              );

              if (filtered.length === 0) {
                return (
                  <Box sx={{ p: 6, textAlign: 'center' }}>
                    <Description sx={{ fontSize: 48, color: 'grey.300', mb: 1 }} />
                    <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
                      No features in this folder
                    </Typography>
                    <Button
                      variant="contained"
                      startIcon={<Psychology />}
                      onClick={() => navigate(`/generate?projectId=${id}&folderId=${selectedFolderId}`)}
                    >
                      Generate Features
                    </Button>
                  </Box>
                );
              }

              return (
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
                      {filtered.map((feature) => (
                        <TableRow
                          key={feature.id}
                          sx={{
                            '&:hover': { bgcolor: 'action.hover', cursor: 'pointer' },
                          }}
                          onClick={() => handleViewFeature(feature.id)}
                        >
                          <TableCell>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              <Description sx={{ color: 'success.main', fontSize: 20 }} />
                              <Typography variant="body1" sx={{ fontWeight: 600 }}>
                                {feature.name}
                              </Typography>
                            </Box>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2" color="text.secondary">
                              {feature.description || 'No description'}
                            </Typography>
                          </TableCell>
                          <TableCell align="center">
                            <Chip label={feature.scenario_count} size="small" color="success" />
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
                              <Tooltip title="Move to folder">
                                <IconButton size="small" onClick={() => handleMoveFeature(feature)}>
                                  <DriveFileMove fontSize="small" />
                                </IconButton>
                              </Tooltip>
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
              );
            })()}
          </Paper>
        </Box>
      )}


      {/* Main Dashboard View - hidden when in folder view */}
      {!inFolderView && (
        <>
          {/* Project Info Card */}
          <Card sx={{ mb: 4 }}>
            <CardContent>
              <Grid container spacing={3} alignItems="center">
                <Grid item xs={12} md={6}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
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
                      }}
                    >
                      <LinkIcon />
                    </Box>
                    <Box>
                      <Typography variant="body2" color="text.secondary">
                        Base URL
                      </Typography>
                      <Tooltip title={project.base_url || 'Not set'}>
                        <Typography
                          variant="body1"
                          sx={{
                            fontFamily: 'monospace',
                            fontWeight: 600,
                            maxWidth: 400,
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {project.base_url || 'Not set'}
                        </Typography>
                      </Tooltip>
                    </Box>
                  </Box>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Box sx={{ display: 'flex', justifyContent: { xs: 'flex-start', md: 'flex-end' }, gap: 2 }}>
                    <Chip label="Active" color="success" sx={{ fontWeight: 600 }} />
                    <Chip
                      label={`${totalTestCases} Total Tests`}
                      variant="outlined"
                      sx={{ fontWeight: 600 }}
                    />
                  </Box>
                </Grid>
              </Grid>
            </CardContent>
          </Card>

          {/* Quick Stats Summary */}
          <Paper sx={{ p: 3, mb: 4 }}>
            <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 2, fontWeight: 600 }}>
              QUICK STATS
            </Typography>
            <Grid container spacing={3}>
              <Grid item xs={6} sm={3}>
                <Box sx={{ textAlign: 'center' }}>
                  <Typography variant="h4" sx={{ fontWeight: 700, color: 'primary.main' }}>
                    {totalTestCases}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Total Tests
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={6} sm={3}>
                <Box sx={{ textAlign: 'center' }}>
                  <Typography variant="h4" sx={{ fontWeight: 700, color: '#3b82f6' }}>
                    {project.test_cases?.length || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Action-Based
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={6} sm={3}>
                <Box sx={{ textAlign: 'center' }}>
                  <Typography variant="h4" sx={{ fontWeight: 700, color: '#22c55e' }}>
                    {gherkinFeatures?.length || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Gherkin Features
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={6} sm={3}>
                <Box sx={{ textAlign: 'center' }}>
                  <Typography variant="h4" sx={{ fontWeight: 700, color: '#f59e0b' }}>
                    {traditionalSuites?.length || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Traditional Suites
                  </Typography>
                </Box>
              </Grid>
            </Grid>
          </Paper>

          {/* Test Type Category Cards */}
          <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
            Test Categories
          </Typography>
          <Grid container spacing={3} sx={{ mb: 4 }}>
            {/* Action-Based Test Cases Card */}
            <Grid item xs={12} md={4}>
              <Card
                sx={{
                  height: '100%',
                  cursor: 'pointer',
                  transition: 'all 0.3s ease',
                  position: 'relative',
                  overflow: 'hidden',
                  '&:hover': {
                    transform: 'translateY(-8px)',
                    boxShadow: '0 12px 40px rgba(59, 130, 246, 0.25)',
                  },
                  '&::before': {
                    content: '""',
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    right: 0,
                    height: 6,
                    background: 'linear-gradient(90deg, #3b82f6 0%, #60a5fa 100%)',
                  },
                }}
                onClick={() => navigate(`/projects/${id}/action-based`)}
              >
                <CardContent sx={{ p: 4 }}>
                  <Box
                    sx={{
                      width: 80,
                      height: 80,
                      borderRadius: 3,
                      background: 'linear-gradient(135deg, #3b82f6 0%, #60a5fa 100%)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      mb: 3,
                      boxShadow: '0 8px 24px rgba(59, 130, 246, 0.3)',
                    }}
                  >
                    <Code sx={{ fontSize: 40, color: 'white' }} />
                  </Box>
                  <Typography variant="h5" sx={{ fontWeight: 700, mb: 1 }}>
                    Action-Based
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                    Selenium-style test cases with actions, locators, and step-by-step instructions
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 2 }}>
                    <Chip
                      label={`${project.test_cases?.length || 0} Test Cases`}
                      color="primary"
                      sx={{ fontWeight: 600 }}
                    />
                    <Chip
                      label={`${totalActions} Actions`}
                      variant="outlined"
                      sx={{ fontWeight: 600 }}
                    />
                  </Box>
                </CardContent>
              </Card>
            </Grid>

            {/* Gherkin/BDD Test Cases Card */}
            <Grid item xs={12} md={4}>
              <Card
                sx={{
                  height: '100%',
                  cursor: 'pointer',
                  transition: 'all 0.3s ease',
                  position: 'relative',
                  overflow: 'hidden',
                  '&:hover': {
                    transform: 'translateY(-8px)',
                    boxShadow: '0 12px 40px rgba(34, 197, 94, 0.25)',
                  },
                  '&::before': {
                    content: '""',
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    right: 0,
                    height: 6,
                    background: 'linear-gradient(90deg, #22c55e 0%, #4ade80 100%)',
                  },
                }}
                onClick={() => navigate(`/projects/${id}/gherkin`)}
              >
                <CardContent sx={{ p: 4 }}>
                  <Box
                    sx={{
                      width: 80,
                      height: 80,
                      borderRadius: 3,
                      background: 'linear-gradient(135deg, #22c55e 0%, #4ade80 100%)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      mb: 3,
                      boxShadow: '0 8px 24px rgba(34, 197, 94, 0.3)',
                    }}
                  >
                    <Description sx={{ fontSize: 40, color: 'white' }} />
                  </Box>
                  <Typography variant="h5" sx={{ fontWeight: 700, mb: 1 }}>
                    Gherkin/BDD
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                    Behavior-driven development scenarios with Given-When-Then syntax
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 2 }}>
                    <Chip
                      label={`${gherkinFeatures?.length || 0} Features`}
                      color="success"
                      sx={{ fontWeight: 600 }}
                    />
                    <Chip
                      label={`${totalScenarios} Scenarios`}
                      variant="outlined"
                      sx={{ fontWeight: 600 }}
                    />
                  </Box>
                </CardContent>
              </Card>
            </Grid>

            {/* Traditional Test Cases Card */}
            <Grid item xs={12} md={4}>
              <Card
                sx={{
                  height: '100%',
                  cursor: 'pointer',
                  transition: 'all 0.3s ease',
                  position: 'relative',
                  overflow: 'hidden',
                  '&:hover': {
                    transform: 'translateY(-8px)',
                    boxShadow: '0 12px 40px rgba(245, 158, 11, 0.25)',
                  },
                  '&::before': {
                    content: '""',
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    right: 0,
                    height: 6,
                    background: 'linear-gradient(90deg, #f59e0b 0%, #fbbf24 100%)',
                  },
                }}
                onClick={() => navigate(`/projects/${id}/traditional`)}
              >
                <CardContent sx={{ p: 4 }}>
                  <Box
                    sx={{
                      width: 80,
                      height: 80,
                      borderRadius: 3,
                      background: 'linear-gradient(135deg, #f59e0b 0%, #fbbf24 100%)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      mb: 3,
                      boxShadow: '0 8px 24px rgba(245, 158, 11, 0.3)',
                    }}
                  >
                    <TableChart sx={{ fontSize: 40, color: 'white' }} />
                  </Box>
                  <Typography variant="h5" sx={{ fontWeight: 700, mb: 1 }}>
                    Traditional
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                    Table-format test cases with preconditions, steps, and expected outcomes
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 2 }}>
                    <Chip
                      label={`${traditionalSuites?.length || 0} Suites`}
                      color="warning"
                      sx={{ fontWeight: 600 }}
                    />
                    <Chip
                      label={`${totalTraditionalCases} Test Cases`}
                      variant="outlined"
                      sx={{ fontWeight: 600 }}
                    />
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

</>
      )}

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

      {/* Project Members Dialog */}
      <Dialog
        open={membersDialogOpen}
        onClose={() => setMembersDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Group color="primary" />
            <Typography variant="h6">Team Members</Typography>
          </Box>
        </DialogTitle>
        <DialogContent>
          <ProjectMembers projectId={id} organizationId={project?.organization_id} />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setMembersDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Folder Dialog */}
      <FolderDialog
        open={folderDialogOpen}
        onClose={() => setFolderDialogOpen(false)}
        onSubmit={handleFolderDialogSubmit}
        mode={folderDialogMode}
        folder={editingFolder}
        feature={movingFeature}
        folders={folderTree}
        parentFolderId={folderParentId}
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