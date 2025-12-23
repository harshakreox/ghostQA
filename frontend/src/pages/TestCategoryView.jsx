import { useState, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
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
  Stack,
  Snackbar,
  Alert,
  Tooltip,
  alpha,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  FormControl,
  Select,
  TextField,
  CircularProgress,
} from '@mui/material';
import {
  ArrowBack,
  Add,
  PlayArrow,
  Edit,
  Delete,
  MoreVert,
  Code,
  NavigateNext,
  Psychology,
  Description,
  Download,
  GetApp,
  Archive,
  TableChart,
  CreateNewFolder,
  Folder as FolderIcon,
  FolderOpen,
  DriveFileMove,  Category,
  Close,
  Visibility,
  ExpandMore,
  Save,
  DragIndicator,
} from '@mui/icons-material';
import axios from 'axios';
import { PageHeader, EmptyState, ConfirmDialog, SearchBar, FolderDialog } from '../components';
import GherkinScenarioCard, { FeatureDisplay } from '../components/GherkinScenarioCard';
import { useNotification, useContextMenu } from '../hooks';
import { downloadFile } from '../utils';

// Category configuration
const CATEGORIES = {
  'action-based': {
    title: 'Action-Based Test Cases',
    icon: Code,
    color: '#3b82f6',
    gradient: 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)',
    description: 'Traditional action-based test cases with step-by-step actions',
  },
  'gherkin': {
    title: 'Gherkin/BDD Features',
    icon: Description,
    color: '#22c55e',
    gradient: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)',
    description: 'Behavior-driven development test scenarios in Gherkin format',
  },
  'traditional': {
    title: 'Traditional Test Cases',
    icon: TableChart,
    color: '#f59e0b',
    gradient: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
    description: 'Traditional table-format test cases with preconditions and expected outcomes',
  },
};

export default function TestCategoryView() {
  const { id: projectId, category } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { isAdmin } = useAuth();

  const categoryConfig = CATEGORIES[category];
  const CategoryIcon = categoryConfig?.icon || Code;

  // Core state
  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  // Items state (test cases, features, or suites based on category)
  const [items, setItems] = useState([]);

  // Folder state
  const [folders, setFolders] = useState([]);
  const [currentFolderId, setCurrentFolderId] = useState(searchParams.get('folderId') || null);
  const [folderPath, setFolderPath] = useState([]);
  const [folderDialogOpen, setFolderDialogOpen] = useState(false);
  const [folderDialogMode, setFolderDialogMode] = useState('create');
  const [editingFolder, setEditingFolder] = useState(null);
  const [parentFolderId, setParentFolderId] = useState(null);
  const [movingItem, setMovingItem] = useState(null);

  // Context menu and notifications
  const { notification, showNotification, hideNotification } = useNotification();
  const { anchorEl, selectedItem, isOpen: menuOpen, openMenu, closeMenu } = useContextMenu();

  // Delete dialog
  const [deleteDialog, setDeleteDialog] = useState({ open: false, item: null, type: '' });

  // Export menu
  const [exportAnchorEl, setExportAnchorEl] = useState(null);

  // Detail view dialog
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);
  const [selectedDetailItem, setSelectedDetailItem] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  // Gherkin scenario editing state
  const [editingScenarioIndex, setEditingScenarioIndex] = useState(null);
  const [editedSteps, setEditedSteps] = useState([]);
  const [savingFeature, setSavingFeature] = useState(false);
  const [draggedStepIndex, setDraggedStepIndex] = useState(null);

  useEffect(() => {
    loadProject();
    loadItems();
    loadFolders();
  }, [projectId, category]);

  useEffect(() => {
    // Update folder path when current folder changes
    if (currentFolderId) {
      buildFolderPath(currentFolderId);
    } else {
      setFolderPath([]);
    }
  }, [currentFolderId, folders]);

  const loadProject = async () => {
    try {
      const response = await axios.get(`/api/projects/${projectId}`);
      setProject(response.data);
    } catch (error) {
      console.error('Error loading project:', error);
      showNotification('Failed to load project', 'error');
    }
  };

  const loadItems = async () => {
    setLoading(true);
    try {
      let response;
      if (category === 'action-based') {
        response = await axios.get(`/api/projects/${projectId}`);
        setItems(response.data.test_cases || []);
      } else if (category === 'gherkin') {
        response = await axios.get(`/api/projects/${projectId}/gherkin-features`);
        setItems(response.data.features || []);
      } else if (category === 'traditional') {
        response = await axios.get(`/api/projects/${projectId}/traditional-suites`);
        setItems(response.data.suites || []);
      }
    } catch (error) {
      console.error('Error loading items:', error);
      setItems([]);
    } finally {
      setLoading(false);
    }
  };

  const loadFolders = async () => {
    try {
      // Load folders for the current category
      const response = await axios.get(`/api/projects/${projectId}/folders?category=${category}`);
      setFolders(response.data.folders || []);
    } catch (error) {
      console.error('Error loading folders:', error);
      setFolders([]);
    }
  };

  const buildFolderPath = (folderId) => {
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
    setFolderPath(path);
  };

  // Get subfolders for current folder
  const getSubfolders = () => {
    return folders.filter(f => f.parent_folder_id === currentFolderId);
  };

  // Get items for current folder
  const getItemsInFolder = () => {
    if (currentFolderId) {
      return items.filter(item => item.folder_id === currentFolderId);
    }
    // Root level - show items without folder_id (uncategorized)
    return items.filter(item => !item.folder_id);
  };

  // Filter items by search
  const getFilteredItems = () => {
    const folderItems = getItemsInFolder();
    if (!searchQuery) return folderItems;

    return folderItems.filter(item => {
      const name = item.name || item.scenario_name || '';
      const desc = item.description || '';
      return name.toLowerCase().includes(searchQuery.toLowerCase()) ||
             desc.toLowerCase().includes(searchQuery.toLowerCase());
    });
  };

  // Folder actions
  const handleCreateFolder = (parentId = null) => {
    setFolderDialogMode('create');
    setParentFolderId(parentId || currentFolderId);
    setEditingFolder(null);
    setFolderDialogOpen(true);
  };

  const handleRenameFolder = (folder) => {
    setFolderDialogMode('edit');
    setEditingFolder(folder);
    setFolderDialogOpen(true);
  };

  const handleDeleteFolder = async (folder) => {
    if (!window.confirm(`Delete folder "${folder.name}"? Items will be moved to parent folder.`)) {
      return;
    }
    try {
      await axios.delete(`/api/folders/${folder.id}`);
      showNotification(`Folder "${folder.name}" deleted`, 'success');
      await loadFolders();
      await loadItems();
      if (currentFolderId === folder.id) {
        setCurrentFolderId(folder.parent_folder_id || null);
      }
    } catch (error) {
      console.error('Error deleting folder:', error);
      showNotification('Failed to delete folder', 'error');
    }
  };

  const handleMoveItem = (item) => {
    setFolderDialogMode('move-feature');
    setMovingItem(item);
    setFolderDialogOpen(true);
  };

  const handleFolderDialogSubmit = async (data) => {
    try {
      if (folderDialogMode === 'create') {
        // Add category to the folder creation request
        await axios.post(`/api/projects/${projectId}/folders`, { ...data, category });
        showNotification('Folder created', 'success');
      } else if (folderDialogMode === 'edit') {
        await axios.put(`/api/folders/${editingFolder.id}`, data);
        showNotification('Folder updated', 'success');
      } else if (folderDialogMode === 'move-feature') {
        // Use category-specific move endpoint
        let moveEndpoint;
        if (category === 'gherkin') {
          moveEndpoint = `/api/gherkin/features/${movingItem.id}/move`;
        } else if (category === 'action-based') {
          moveEndpoint = `/api/projects/${projectId}/test-cases/${movingItem.id}/move`;
        } else if (category === 'traditional') {
          moveEndpoint = `/api/traditional/suites/${movingItem.id}/move`;
        }
        await axios.put(moveEndpoint, data);
        showNotification('Item moved', 'success');
      }
      setFolderDialogOpen(false);
      await loadFolders();
      await loadItems();
    } catch (error) {
      console.error('Error:', error);
      showNotification(error.response?.data?.detail || 'Operation failed', 'error');
    }
  };

  // Delete item
  const handleDeleteItem = async () => {
    if (!deleteDialog.item) return;

    try {
      if (category === 'action-based') {
        await axios.delete(`/api/projects/${projectId}/test-cases/${deleteDialog.item.id}`);
      } else if (category === 'gherkin') {
        await axios.delete(`/api/gherkin/features/${deleteDialog.item.id}`);
      } else if (category === 'traditional') {
        await axios.delete(`/api/traditional/suites/${deleteDialog.item.id}`);
      }
      showNotification('Deleted successfully', 'success');
      await loadItems();
      setDeleteDialog({ open: false, item: null, type: '' });
    } catch (error) {
      console.error('Error deleting:', error);
      showNotification('Failed to delete', 'error');
    }
  };

  // Export functions
  const handleExportAll = async (format) => {
    setExportAnchorEl(null);
    try {
      let endpoint, filename;
      if (category === 'gherkin') {
        endpoint = `/api/projects/${projectId}/gherkin-features/export?format=${format}`;
        filename = format === 'json'
          ? `${project?.name || 'features'}_features.json`
          : `${project?.name || 'features'}_features.zip`;
      } else if (category === 'traditional') {
        endpoint = `/api/projects/${projectId}/traditional-suites/export?format=${format}`;
        filename = format === 'json'
          ? `${project?.name || 'suites'}_traditional_suites.json`
          : format === 'csv'
          ? `${project?.name || 'suites'}_all_test_cases.csv`
          : `${project?.name || 'suites'}_traditional_suites.zip`;
      }

      if (endpoint) {
        const response = await axios.get(endpoint, { responseType: 'blob' });
        downloadFile(response.data, filename);
        showNotification('Exported successfully', 'success');
      }
    } catch (error) {
      console.error('Error exporting:', error);
      showNotification('Failed to export', 'error');
    }
  };

  const handleExportSingle = async (item, format) => {
    try {
      let endpoint, filename;
      if (category === 'gherkin') {
        endpoint = format === 'json'
          ? `/api/gherkin/features/${item.id}/export/json`
          : `/api/gherkin/features/${item.id}/export`;
        filename = format === 'json'
          ? `${item.name.replace(/\s+/g, '_')}.json`
          : `${item.name.replace(/\s+/g, '_')}.feature`;
      } else if (category === 'traditional') {
        endpoint = format === 'json'
          ? `/api/traditional/suites/${item.id}/export/json`
          : `/api/traditional/suites/${item.id}/export/csv`;
        filename = format === 'json'
          ? `${item.name.replace(/\s+/g, '_')}.json`
          : `${item.name.replace(/\s+/g, '_')}.csv`;
      }

      if (endpoint) {
        const response = await axios.get(endpoint, { responseType: 'blob' });
        downloadFile(response.data, filename);
        showNotification('Exported successfully', 'success');
      }
    } catch (error) {
      console.error('Error exporting:', error);
      showNotification('Failed to export', 'error');
    }
  };

  // Navigate into folder
  const handleFolderClick = (folder) => {
    setCurrentFolderId(folder.id);
  };

  // Gherkin step editing handlers
  const handleStartEditScenario = (scenarioIndex) => {
    const scenario = selectedDetailItem.scenarios[scenarioIndex];
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
    if (!selectedDetailItem || editingScenarioIndex === null) return;
    setSavingFeature(true);
    try {
      const updatedFeature = {
        ...selectedDetailItem,
        scenarios: selectedDetailItem.scenarios.map((s, idx) =>
          idx === editingScenarioIndex ? { ...s, steps: editedSteps } : s
        )
      };
      await axios.put(`/api/gherkin/features/${selectedDetailItem.id}`, updatedFeature);
      setSelectedDetailItem(updatedFeature);
      await loadItems();
      showNotification('Scenario saved successfully', 'success');
      handleCancelEdit();
    } catch (error) {
      console.error('Error saving scenario:', error);
      showNotification('Failed to save scenario', 'error');
    } finally {
      setSavingFeature(false);
    }
  };

  const handleCloseDetailDialog = () => {
    setDetailDialogOpen(false);
    setSelectedDetailItem(null);
    setEditingScenarioIndex(null);
    setEditedSteps([]);
  };

  // Load full item details for dialog
  const loadItemDetails = async (item) => {
    setLoadingDetail(true);
    try {
      let response;
      if (category === 'gherkin') {
        response = await axios.get(`/api/gherkin/features/${item.id}`);
        setSelectedDetailItem(response.data);
      } else if (category === 'traditional') {
        response = await axios.get(`/api/traditional/suites/${item.id}`);
        setSelectedDetailItem(response.data);
      }
    } catch (error) {
      console.error('Error loading item details:', error);
      showNotification('Failed to load details', 'error');
    } finally {
      setLoadingDetail(false);
    }
  };

  // Navigate to item detail
  const handleItemClick = (item) => {
    if (category === 'action-based') {
      navigate(`/projects/${projectId}/test-cases/${item.id}/edit`);
    } else if (category === 'gherkin' || category === 'traditional') {
      // Open detail dialog
      setSelectedDetailItem(item);
      setDetailDialogOpen(true);
      loadItemDetails(item);
    }
  };

  if (!categoryConfig) {
    return (
      <Box sx={{ textAlign: 'center', py: 8 }}>
        <Typography variant="h6">Invalid category</Typography>
        <Button onClick={() => navigate(`/projects/${projectId}`)} sx={{ mt: 2 }}>
          Back to Project
        </Button>
      </Box>
    );
  }

  if (loading) {
    return <LinearProgress />;
  }

  const filteredItems = getFilteredItems();
  const subfolders = getSubfolders();

  return (
    <Box>
      {/* Breadcrumbs */}
      <Breadcrumbs separator={<NavigateNext fontSize="small" />} sx={{ mb: 3 }}>
        <Link
          component="button"
          variant="body2"
          onClick={() => navigate('/projects')}
        >
          Projects
        </Link>
        <Link
          component="button"
          variant="body2"
          onClick={() => navigate(`/projects/${projectId}`)}
        >
          {project?.name || 'Project'}
        </Link>
        <Link
          component="button"
          variant="body2"
          onClick={() => setCurrentFolderId(null)}
          sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}
        >
          <CategoryIcon sx={{ fontSize: 16 }} />
          {categoryConfig.title}
        </Link>
        {folderPath.map((folder, index) => (
          <Link
            key={folder.id}
            component="button"
            variant="body2"
            onClick={() => setCurrentFolderId(folder.id)}
            sx={{
              fontWeight: index === folderPath.length - 1 ? 600 : 400,
              color: index === folderPath.length - 1 ? 'text.primary' : 'inherit',
            }}
          >
            {folder.name}
          </Link>
        ))}
      </Breadcrumbs>

      {/* Header */}
      <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Box
            sx={{
              width: 56,
              height: 56,
              borderRadius: 3,
              background: currentFolderId
                ? 'linear-gradient(135deg, #ffa726 0%, #fb8c00 100%)'
                : categoryConfig.gradient,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'white',
            }}
          >
            {currentFolderId ? <FolderIcon sx={{ fontSize: 32 }} /> : <CategoryIcon sx={{ fontSize: 32 }} />}
          </Box>
          <Box>
            <Typography variant="h4" sx={{ fontWeight: 700 }}>
              {currentFolderId
                ? folderPath[folderPath.length - 1]?.name || 'Folder'
                : categoryConfig.title}
            </Typography>
            <Typography variant="body1" color="text.secondary">
              {currentFolderId
                ? `${filteredItems.length} items • ${subfolders.length} subfolders`
                : categoryConfig.description}
            </Typography>
          </Box>
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="outlined"
            startIcon={<CreateNewFolder />}
            onClick={() => handleCreateFolder()}
          >
            New Folder
          </Button>
          <Button
            variant="contained"
            startIcon={<Psychology />}
            onClick={() => navigate(`/generate?projectId=${projectId}&category=${category}${currentFolderId ? `&folderId=${currentFolderId}` : ''}`)}
            sx={{ background: categoryConfig.gradient }}
          >
            Generate with AI
          </Button>
          {category === 'action-based' && (
            <Button
              variant="contained"
              startIcon={<Add />}
              onClick={() => navigate(`/projects/${projectId}/test-cases/new`)}
            >
              Add Test Case
            </Button>
          )}
        </Box>
      </Box>

      {/* Uncategorized Folder Card (always shown at root) */}
      {!currentFolderId && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="overline" sx={{ color: 'text.secondary', fontWeight: 600, mb: 1, display: 'block' }}>
            Default Folder
          </Typography>
          <Card
            variant="outlined"
            sx={{
              maxWidth: 280,
              cursor: 'pointer',
              bgcolor: alpha('#9ca3af', 0.1),
              borderColor: alpha('#9ca3af', 0.3),
              transition: 'all 0.2s',
              '&:hover': {
                borderColor: 'primary.main',
                transform: 'translateY(-2px)',
                boxShadow: 2,
              },
            }}
          >
            <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                <FolderOpen sx={{ color: 'grey.500', fontSize: 32 }} />
                <Box>
                  <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                    Uncategorized
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {items.filter(i => !i.folder_id).length} items
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Box>
      )}

      {/* Subfolders */}
      {subfolders.length > 0 && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="overline" sx={{ color: 'text.secondary', fontWeight: 600, mb: 1, display: 'block' }}>
            Folders
          </Typography>
          <Grid container spacing={2}>
            {subfolders.map((folder) => (
              <Grid item key={folder.id}>
                <Card
                  variant="outlined"
                  sx={{
                    minWidth: 200,
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    '&:hover': {
                      borderColor: 'primary.main',
                      transform: 'translateY(-2px)',
                      boxShadow: 2,
                    },
                  }}
                  onClick={() => handleFolderClick(folder)}
                >
                  <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                      <FolderIcon sx={{ color: 'warning.main', fontSize: 32 }} />
                      <Box sx={{ flex: 1, minWidth: 0 }}>
                        <Typography variant="subtitle1" sx={{ fontWeight: 600 }} noWrap>
                          {folder.name}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {items.filter(i => i.folder_id === folder.id).length} items
                          {folders.filter(f => f.parent_folder_id === folder.id).length > 0 &&
                            ` • ${folders.filter(f => f.parent_folder_id === folder.id).length} subfolders`}
                        </Typography>
                      </Box>
                      <IconButton
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation();
                          openMenu(e, { ...folder, isFolder: true });
                        }}
                      >
                        <MoreVert fontSize="small" />
                      </IconButton>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Box>
      )}

      {/* Items List */}
      <Paper>
        <Box sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            {category === 'action-based' ? 'Test Cases' : category === 'gherkin' ? 'Features' : 'Test Suites'}
            <Chip label={filteredItems.length} size="small" sx={{ ml: 1 }} />
          </Typography>
          <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
            <SearchBar
              placeholder={`Search ${category === 'gherkin' ? 'features' : 'test cases'}...`}
              value={searchQuery}
              onSearch={setSearchQuery}
            />
            {(category === 'gherkin' || category === 'traditional') && items.length > 0 && (
              <>
                <Button
                  variant="outlined"
                  size="small"
                  startIcon={<Download />}
                  onClick={(e) => setExportAnchorEl(e.currentTarget)}
                >
                  Export
                </Button>
                <Menu
                  anchorEl={exportAnchorEl}
                  open={Boolean(exportAnchorEl)}
                  onClose={() => setExportAnchorEl(null)}
                >
                  {category === 'gherkin' && (
                    <>
                      <MenuItem onClick={() => handleExportAll('zip')}>
                        <ListItemIcon><Archive fontSize="small" /></ListItemIcon>
                        <ListItemText>Export as ZIP (.feature)</ListItemText>
                      </MenuItem>
                      <MenuItem onClick={() => handleExportAll('json')}>
                        <ListItemIcon><GetApp fontSize="small" /></ListItemIcon>
                        <ListItemText>Export as JSON</ListItemText>
                      </MenuItem>
                    </>
                  )}
                  {category === 'traditional' && (
                    <>
                      <MenuItem onClick={() => handleExportAll('csv')}>
                        <ListItemIcon><Download fontSize="small" /></ListItemIcon>
                        <ListItemText>Export as CSV</ListItemText>
                      </MenuItem>
                      <MenuItem onClick={() => handleExportAll('zip')}>
                        <ListItemIcon><Archive fontSize="small" /></ListItemIcon>
                        <ListItemText>Export as ZIP</ListItemText>
                      </MenuItem>
                      <MenuItem onClick={() => handleExportAll('json')}>
                        <ListItemIcon><GetApp fontSize="small" /></ListItemIcon>
                        <ListItemText>Export as JSON</ListItemText>
                      </MenuItem>
                    </>
                  )}
                </Menu>
              </>
            )}
          </Box>
        </Box>
        <Divider />

        {filteredItems.length === 0 ? (
          <Box sx={{ p: 6 }}>
            <EmptyState
              icon={CategoryIcon}
              title={`No ${category === 'gherkin' ? 'Features' : 'Test Cases'} Yet`}
              description={`Generate ${category === 'gherkin' ? 'BDD test scenarios' : 'test cases'} using AI`}
              actionLabel="Generate with AI"
              actionIcon={<Psychology />}
              onAction={() => navigate(`/generate?projectId=${projectId}&category=${category}`)}
            />
          </Box>
        ) : (
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 600 }}>Name</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Description</TableCell>
                  <TableCell sx={{ fontWeight: 600 }} align="center">
                    {category === 'action-based' ? 'Actions' : category === 'gherkin' ? 'Scenarios' : 'Test Cases'}
                  </TableCell>
                  <TableCell sx={{ fontWeight: 600 }} align="center">Folder</TableCell>
                  <TableCell sx={{ fontWeight: 600 }} align="center">Created</TableCell>
                  <TableCell sx={{ fontWeight: 600 }} align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filteredItems.map((item) => (
                  <TableRow
                    key={item.id}
                    sx={{
                      '&:hover': { bgcolor: 'action.hover', cursor: 'pointer' },
                    }}
                    onClick={() => handleItemClick(item)}
                  >
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <CategoryIcon sx={{ color: categoryConfig.color, fontSize: 20 }} />
                        <Typography variant="body1" sx={{ fontWeight: 600 }}>
                          {item.name}
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" color="text.secondary">
                        {item.description || 'No description'}
                      </Typography>
                    </TableCell>
                    <TableCell align="center">
                      <Chip
                        label={
                          category === 'action-based'
                            ? item.actions?.length || 0
                            : category === 'gherkin'
                            ? item.scenario_count || 0
                            : item.test_case_count || 0
                        }
                        size="small"
                        sx={{ bgcolor: alpha(categoryConfig.color, 0.1), color: categoryConfig.color, fontWeight: 600 }}
                      />
                    </TableCell>
                    <TableCell align="center">
                      {item.folder_id ? (
                        <Chip
                          label={folders.find(f => f.id === item.folder_id)?.name || 'Unknown'}
                          size="small"
                          variant="outlined"
                          icon={<FolderIcon sx={{ fontSize: 14 }} />}
                        />
                      ) : (
                        <Typography variant="caption" color="text.secondary">Uncategorized</Typography>
                      )}
                    </TableCell>
                    <TableCell align="center">
                      <Typography variant="body2" color="text.secondary">
                        {item.created_at ? new Date(item.created_at).toLocaleDateString() : '-'}
                      </Typography>
                    </TableCell>
                    <TableCell align="right" onClick={(e) => e.stopPropagation()}>
                      <Stack direction="row" spacing={1} justifyContent="flex-end">
                        {isAdmin && category !== 'traditional' && (
                          <Button
                            size="small"
                            startIcon={<PlayArrow />}
                            onClick={() => {
                              if (category === 'gherkin') {
                                navigate(`/run-tests?projectId=${projectId}&featureId=${item.id}`);
                              }
                            }}
                          >
                            Run
                          </Button>
                        )}
                        <Tooltip title="Move to folder">
                          <IconButton size="small" onClick={() => handleMoveItem(item)}>
                            <DriveFileMove fontSize="small" />
                          </IconButton>
                        </Tooltip>
                        {(category === 'gherkin' || category === 'traditional') && (
                          <Button
                            size="small"
                            startIcon={<Download />}
                            onClick={() => handleExportSingle(item, category === 'gherkin' ? 'feature' : 'csv')}
                          >
                            Export
                          </Button>
                        )}
                        <IconButton size="small" onClick={(e) => openMenu(e, item)}>
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
      </Paper>

      {/* Context Menu */}
      <Menu anchorEl={anchorEl} open={menuOpen} onClose={closeMenu}>
        {selectedItem?.isFolder ? (
          <>
            <MenuItem onClick={() => { handleRenameFolder(selectedItem); closeMenu(); }}>
              <ListItemIcon><Edit fontSize="small" /></ListItemIcon>
              <ListItemText>Rename</ListItemText>
            </MenuItem>
            <MenuItem onClick={() => { handleDeleteFolder(selectedItem); closeMenu(); }}>
              <ListItemIcon><Delete fontSize="small" color="error" /></ListItemIcon>
              <ListItemText sx={{ color: 'error.main' }}>Delete</ListItemText>
            </MenuItem>
          </>
        ) : (
          <>
            {category === 'action-based' && (
              <MenuItem onClick={() => { navigate(`/projects/${projectId}/test-cases/${selectedItem?.id}/edit`); closeMenu(); }}>
                <ListItemIcon><Edit fontSize="small" /></ListItemIcon>
                <ListItemText>Edit</ListItemText>
              </MenuItem>
            )}
            {category === 'gherkin' && (
              <>
                <MenuItem onClick={() => { handleExportSingle(selectedItem, 'feature'); closeMenu(); }}>
                  <ListItemIcon><Download fontSize="small" /></ListItemIcon>
                  <ListItemText>Export as .feature</ListItemText>
                </MenuItem>
                <MenuItem onClick={() => { handleExportSingle(selectedItem, 'json'); closeMenu(); }}>
                  <ListItemIcon><GetApp fontSize="small" /></ListItemIcon>
                  <ListItemText>Export as JSON</ListItemText>
                </MenuItem>
              </>
            )}
            {category === 'traditional' && (
              <>
                <MenuItem onClick={() => { handleExportSingle(selectedItem, 'csv'); closeMenu(); }}>
                  <ListItemIcon><Download fontSize="small" /></ListItemIcon>
                  <ListItemText>Export as CSV</ListItemText>
                </MenuItem>
                <MenuItem onClick={() => { handleExportSingle(selectedItem, 'json'); closeMenu(); }}>
                  <ListItemIcon><GetApp fontSize="small" /></ListItemIcon>
                  <ListItemText>Export as JSON</ListItemText>
                </MenuItem>
              </>
            )}
            <Divider />
            <MenuItem onClick={() => { setDeleteDialog({ open: true, item: selectedItem, type: category }); closeMenu(); }}>
              <ListItemIcon><Delete fontSize="small" color="error" /></ListItemIcon>
              <ListItemText sx={{ color: 'error.main' }}>Delete</ListItemText>
            </MenuItem>
          </>
        )}
      </Menu>

      {/* Delete Confirmation */}
      <ConfirmDialog
        open={deleteDialog.open}
        onClose={() => setDeleteDialog({ open: false, item: null, type: '' })}
        onConfirm={handleDeleteItem}
        title={`Delete ${category === 'gherkin' ? 'Feature' : 'Test Case'}?`}
        message={`Are you sure you want to delete "${deleteDialog.item?.name}"? This action cannot be undone.`}
        confirmLabel="Delete"
        type="delete"
      />

      {/* Folder Dialog */}
      <FolderDialog
          open={folderDialogOpen}
          onClose={() => setFolderDialogOpen(false)}
          onSubmit={handleFolderDialogSubmit}
          mode={folderDialogMode}
          folder={editingFolder}
          feature={movingItem}
          folders={folders}
          parentFolderId={parentFolderId}
        />

      {/* Notification */}
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

      {/* Detail View Dialog for Features/Suites */}
      <Dialog
        open={detailDialogOpen}
        onClose={handleCloseDetailDialog}
        maxWidth="lg"
        fullWidth
        PaperProps={{
          sx: { minHeight: '70vh' }
        }}
      >
        <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <CategoryIcon sx={{ color: categoryConfig.color }} />
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              {selectedDetailItem?.name || 'Loading...'}
            </Typography>
          </Box>
          <IconButton onClick={() => setDetailDialogOpen(false)}>
            <Close />
          </IconButton>
        </DialogTitle>
        <DialogContent dividers>
          {loadingDetail ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
              <LinearProgress sx={{ width: '50%' }} />
            </Box>
          ) : selectedDetailItem && category === 'gherkin' ? (
            <Box>
              {/* Feature Display */}
              <FeatureDisplay feature={selectedDetailItem} />

              {/* Scenarios */}
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 2, mt: 3 }}>
                Scenarios ({selectedDetailItem.scenarios?.length || 0})
              </Typography>
              {selectedDetailItem.scenarios?.map((scenario, index) => (
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
                          color="success"
                        />
                        <Tooltip title="Edit steps">
                          <IconButton
                            size="small"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleStartEditScenario(index);
                            }}
                          >
                            <Edit fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </Box>
                      {scenario.tags && scenario.tags.length > 0 && (
                        <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                          {scenario.tags.map((tag, i) => (
                            <Chip key={i} label={tag} size="small" variant="outlined" />
                          ))}
                        </Box>
                      )}
                    </Box>
                  </AccordionSummary>
                  <AccordionDetails>
                    {editingScenarioIndex === index ? (
                      /* Edit Mode */
                      <Paper sx={{ p: 2, bgcolor: '#fff3e0' }}>
                        <Typography variant="subtitle2" sx={{ mb: 2, fontWeight: 600, color: '#e65100' }}>
                          Editing Steps - Drag to reorder
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
                            }}
                          >
                            <DragIndicator sx={{ color: 'text.secondary', cursor: 'grab', mt: 1 }} fontSize="small" />
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
                            <IconButton size="small" onClick={() => handleDeleteStep(i)} color="error">
                              <Delete fontSize="small" />
                            </IconButton>
                          </Box>
                        ))}
                        <Box sx={{ display: 'flex', gap: 1, mt: 2 }}>
                          <Button size="small" startIcon={<Add />} onClick={handleAddStep} variant="outlined">
                            Add Step
                          </Button>
                          <Box sx={{ flex: 1 }} />
                          <Button size="small" onClick={handleCancelEdit}>Cancel</Button>
                          <Button
                            size="small"
                            variant="contained"
                            startIcon={savingFeature ? <CircularProgress size={14} /> : <Save />}
                            onClick={handleSaveScenario}
                            disabled={savingFeature}
                            sx={{ background: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)' }}
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
                          const stepColor = keyword === 'Given' ? 'green' : keyword === 'When' ? 'blue' : keyword === 'Then' ? 'orange' : keyword === 'And' ? 'purple' : 'inherit';
                          return (
                            <Typography key={i} variant="body2" sx={{ fontFamily: 'monospace', mb: 0.5, pl: 2 }}>
                              <strong style={{ color: stepColor }}>{keyword}</strong> {step.text}
                            </Typography>
                          );
                        })}
                      </Paper>
                    )}
                  </AccordionDetails>
                </Accordion>
              ))}
            </Box>
          ) : selectedDetailItem && category === 'traditional' ? (
            <Box>
              {/* Suite Info */}
              <Card sx={{ mb: 3 }}>
                <CardContent>
                  <Typography variant="h5" sx={{ fontWeight: 700, mb: 1 }}>
                    Test Suite: {selectedDetailItem.name}
                  </Typography>
                  {selectedDetailItem.description && (
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                      {selectedDetailItem.description}
                    </Typography>
                  )}
                  <Box sx={{ display: 'flex', gap: 2 }}>
                    <Chip
                      label={`${selectedDetailItem.test_cases?.length || 0} Test Cases`}
                      color="primary"
                      size="small"
                    />
                    <Chip
                      label={`Created: ${selectedDetailItem.created_at ? new Date(selectedDetailItem.created_at).toLocaleDateString() : 'N/A'}`}
                      variant="outlined"
                      size="small"
                    />
                  </Box>
                </CardContent>
              </Card>

              {/* Test Cases Table */}
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                Test Cases
              </Typography>
              <TableContainer component={Paper} variant="outlined">
                <Table size="small">
                  <TableHead>
                    <TableRow sx={{ bgcolor: 'grey.50' }}>
                      <TableCell sx={{ fontWeight: 600 }}>#</TableCell>
                      <TableCell sx={{ fontWeight: 600 }}>Name</TableCell>
                      <TableCell sx={{ fontWeight: 600 }}>Preconditions</TableCell>
                      <TableCell sx={{ fontWeight: 600 }}>Steps</TableCell>
                      <TableCell sx={{ fontWeight: 600 }}>Expected Result</TableCell>
                      <TableCell sx={{ fontWeight: 600 }}>Priority</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {selectedDetailItem.test_cases?.map((tc, idx) => (
                      <TableRow key={idx} sx={{ '&:hover': { bgcolor: 'action.hover' } }}>
                        <TableCell sx={{ fontWeight: 500 }}>{idx + 1}</TableCell>
                        <TableCell sx={{ fontWeight: 500 }}>{tc.name}</TableCell>
                        <TableCell sx={{ whiteSpace: 'pre-wrap', maxWidth: 200 }}>
                          {tc.preconditions || '-'}
                        </TableCell>
                        <TableCell sx={{ whiteSpace: 'pre-wrap', maxWidth: 250 }}>
                          {tc.steps}
                        </TableCell>
                        <TableCell sx={{ whiteSpace: 'pre-wrap', maxWidth: 200 }}>
                          {tc.expected_result}
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={tc.priority || 'Medium'}
                            size="small"
                            color={tc.priority === 'High' ? 'error' : tc.priority === 'Low' ? 'default' : 'warning'}
                          />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </Box>
          ) : (
            <Typography color="text.secondary">No details available</Typography>
          )}
        </DialogContent>
        <DialogActions sx={{ px: 3, py: 2 }}>
          {category === 'gherkin' && selectedDetailItem && (
            <>
              <Button
                startIcon={<Download />}
                onClick={() => handleExportSingle(selectedDetailItem, 'feature')}
              >
                Export as .feature
              </Button>
              <Button
                startIcon={<GetApp />}
                onClick={() => handleExportSingle(selectedDetailItem, 'json')}
              >
                Export as JSON
              </Button>
            </>
          )}
          {category === 'traditional' && selectedDetailItem && (
            <>
              <Button
                startIcon={<Download />}
                onClick={() => handleExportSingle(selectedDetailItem, 'csv')}
              >
                Export as CSV
              </Button>
              <Button
                startIcon={<GetApp />}
                onClick={() => handleExportSingle(selectedDetailItem, 'json')}
              >
                Export as JSON
              </Button>
            </>
          )}
          <Button onClick={() => setDetailDialogOpen(false)}>
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
