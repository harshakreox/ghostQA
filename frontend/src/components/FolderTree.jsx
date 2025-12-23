import { useState } from 'react';
import {
  Box,
  Typography,
  IconButton,
  Collapse,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Chip,
  Menu,
  MenuItem,
  ListItemSecondaryAction,
  Tooltip,
  CircularProgress,
} from '@mui/material';
import {
  Folder as FolderIcon,
  FolderOpen as FolderOpenIcon,
  ExpandMore,
  ChevronRight,
  Description,
  MoreVert,
  Add,
  Edit,
  Delete,
  DriveFileMove,
  CreateNewFolder,
} from '@mui/icons-material';

// Recursive folder item component
function FolderItem({
  folder,
  level = 0,
  selectedFolderId,
  onSelectFolder,
  onCreateSubfolder,
  onRenameFolder,
  onDeleteFolder,
  featuresInFolder = [],
  onFeatureClick,
  onMoveFeature,
  expandedFolders,
  toggleFolderExpand,
}) {
  const [menuAnchor, setMenuAnchor] = useState(null);
  const [featureMenuAnchor, setFeatureMenuAnchor] = useState(null);
  const [selectedFeatureForMenu, setSelectedFeatureForMenu] = useState(null);

  const isExpanded = expandedFolders.includes(folder.id);
  const isSelected = selectedFolderId === folder.id;
  const hasChildren = folder.children && folder.children.length > 0;
  const hasFeatures = featuresInFolder.length > 0;

  const handleFolderClick = () => {
    onSelectFolder(folder.id);
    if (hasChildren || hasFeatures) {
      toggleFolderExpand(folder.id);
    }
  };

  const handleMenuOpen = (e) => {
    e.stopPropagation();
    setMenuAnchor(e.currentTarget);
  };

  const handleMenuClose = () => {
    setMenuAnchor(null);
  };

  const handleFeatureMenuOpen = (e, feature) => {
    e.stopPropagation();
    setSelectedFeatureForMenu(feature);
    setFeatureMenuAnchor(e.currentTarget);
  };

  const handleFeatureMenuClose = () => {
    setFeatureMenuAnchor(null);
    setSelectedFeatureForMenu(null);
  };

  return (
    <>
      <ListItem
        disablePadding
        sx={{ display: 'block' }}
      >
        <ListItemButton
          onClick={handleFolderClick}
          selected={isSelected}
          sx={{
            pl: 2 + level * 2,
            borderRadius: 1,
            mb: 0.5,
            '&.Mui-selected': {
              bgcolor: 'primary.light',
              '&:hover': {
                bgcolor: 'primary.light',
              },
            },
          }}
        >
          <ListItemIcon sx={{ minWidth: 36 }}>
            {(hasChildren || hasFeatures) ? (
              isExpanded ? <FolderOpenIcon color="primary" /> : <FolderIcon color="primary" />
            ) : (
              <FolderIcon sx={{ color: 'grey.400' }} />
            )}
          </ListItemIcon>
          <ListItemText
            primary={folder.name}
            primaryTypographyProps={{
              fontWeight: isSelected ? 600 : 400,
              fontSize: '0.9rem',
            }}
          />
          {(hasChildren || hasFeatures) && (
            <Box sx={{ mr: 1 }}>
              {isExpanded ? <ExpandMore fontSize="small" /> : <ChevronRight fontSize="small" />}
            </Box>
          )}
          <IconButton
            size="small"
            onClick={handleMenuOpen}
            sx={{ opacity: 0.6, '&:hover': { opacity: 1 } }}
          >
            <MoreVert fontSize="small" />
          </IconButton>
        </ListItemButton>
      </ListItem>

      {/* Folder Menu */}
      <Menu
        anchorEl={menuAnchor}
        open={Boolean(menuAnchor)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={() => {
          onCreateSubfolder(folder.id);
          handleMenuClose();
        }}>
          <ListItemIcon><CreateNewFolder fontSize="small" /></ListItemIcon>
          <ListItemText>New Subfolder</ListItemText>
        </MenuItem>
        <MenuItem onClick={() => {
          onRenameFolder(folder);
          handleMenuClose();
        }}>
          <ListItemIcon><Edit fontSize="small" /></ListItemIcon>
          <ListItemText>Rename</ListItemText>
        </MenuItem>
        <MenuItem onClick={() => {
          onDeleteFolder(folder);
          handleMenuClose();
        }} sx={{ color: 'error.main' }}>
          <ListItemIcon><Delete fontSize="small" color="error" /></ListItemIcon>
          <ListItemText>Delete</ListItemText>
        </MenuItem>
      </Menu>

      {/* Expanded content: subfolders and features */}
      <Collapse in={isExpanded} timeout="auto" unmountOnExit>
        <List component="div" disablePadding>
          {/* Subfolders */}
          {folder.children?.map((child) => (
            <FolderItem
              key={child.id}
              folder={child}
              level={level + 1}
              selectedFolderId={selectedFolderId}
              onSelectFolder={onSelectFolder}
              onCreateSubfolder={onCreateSubfolder}
              onRenameFolder={onRenameFolder}
              onDeleteFolder={onDeleteFolder}
              featuresInFolder={[]} // Features are passed separately per folder
              onFeatureClick={onFeatureClick}
              onMoveFeature={onMoveFeature}
              expandedFolders={expandedFolders}
              toggleFolderExpand={toggleFolderExpand}
            />
          ))}

          {/* Features in this folder */}
          {featuresInFolder.map((feature) => (
            <ListItem
              key={feature.id}
              disablePadding
              sx={{ display: 'block' }}
            >
              <ListItemButton
                onClick={() => onFeatureClick(feature.id)}
                sx={{
                  pl: 4 + level * 2,
                  borderRadius: 1,
                  mb: 0.5,
                  '&:hover': {
                    bgcolor: 'action.hover',
                  },
                }}
              >
                <ListItemIcon sx={{ minWidth: 36 }}>
                  <Description sx={{ color: 'success.main', fontSize: 20 }} />
                </ListItemIcon>
                <ListItemText
                  primary={feature.name}
                  secondary={`${feature.scenario_count} scenarios`}
                  primaryTypographyProps={{ fontSize: '0.85rem' }}
                  secondaryTypographyProps={{ fontSize: '0.75rem' }}
                />
                <IconButton
                  size="small"
                  onClick={(e) => handleFeatureMenuOpen(e, feature)}
                  sx={{ opacity: 0.6, '&:hover': { opacity: 1 } }}
                >
                  <MoreVert fontSize="small" />
                </IconButton>
              </ListItemButton>
            </ListItem>
          ))}
        </List>
      </Collapse>

      {/* Feature Menu */}
      <Menu
        anchorEl={featureMenuAnchor}
        open={Boolean(featureMenuAnchor)}
        onClose={handleFeatureMenuClose}
      >
        <MenuItem onClick={() => {
          onMoveFeature(selectedFeatureForMenu);
          handleFeatureMenuClose();
        }}>
          <ListItemIcon><DriveFileMove fontSize="small" /></ListItemIcon>
          <ListItemText>Move to Folder</ListItemText>
        </MenuItem>
      </Menu>
    </>
  );
}

export default function FolderTree({
  folders = [],
  features = [],
  featuresByFolder = {},
  rootFeatures = [],
  selectedFolderId,
  onSelectFolder,
  onCreateFolder,
  onCreateSubfolder,
  onRenameFolder,
  onDeleteFolder,
  onFeatureClick,
  onMoveFeature,
  loading = false,
}) {
  const [expandedFolders, setExpandedFolders] = useState([]);

  const toggleFolderExpand = (folderId) => {
    setExpandedFolders((prev) =>
      prev.includes(folderId)
        ? prev.filter((id) => id !== folderId)
        : [...prev, folderId]
    );
  };

  const handleSelectRoot = () => {
    onSelectFolder(null);
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
        <CircularProgress size={24} />
      </Box>
    );
  }

  return (
    <Box>
      {/* Header with Create Folder button */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, px: 1 }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 600, color: 'text.secondary' }}>
          FOLDERS
        </Typography>
        <Tooltip title="Create Folder">
          <IconButton size="small" onClick={() => onCreateFolder()}>
            <Add fontSize="small" />
          </IconButton>
        </Tooltip>
      </Box>

      <List component="nav" dense>
        {/* Root level (All Features) */}
        <ListItem disablePadding>
          <ListItemButton
            onClick={handleSelectRoot}
            selected={selectedFolderId === null}
            sx={{
              borderRadius: 1,
              mb: 0.5,
              '&.Mui-selected': {
                bgcolor: 'primary.light',
              },
            }}
          >
            <ListItemIcon sx={{ minWidth: 36 }}>
              <FolderOpenIcon color="primary" />
            </ListItemIcon>
            <ListItemText
              primary="All Features"
              primaryTypographyProps={{
                fontWeight: selectedFolderId === null ? 600 : 400,
                fontSize: '0.9rem',
              }}
            />
            <Chip
              label={features.length}
              size="small"
              sx={{ height: 20, fontSize: '0.7rem' }}
            />
          </ListItemButton>
        </ListItem>

        {/* Root features (not in any folder) */}
        {selectedFolderId === null && rootFeatures.length > 0 && (
          <Collapse in={true}>
            <List component="div" disablePadding>
              {rootFeatures.map((feature) => (
                <ListItem key={feature.id} disablePadding>
                  <ListItemButton
                    onClick={() => onFeatureClick(feature.id)}
                    sx={{ pl: 4, borderRadius: 1, mb: 0.5 }}
                  >
                    <ListItemIcon sx={{ minWidth: 36 }}>
                      <Description sx={{ color: 'success.main', fontSize: 20 }} />
                    </ListItemIcon>
                    <ListItemText
                      primary={feature.name}
                      secondary={`${feature.scenario_count} scenarios`}
                      primaryTypographyProps={{ fontSize: '0.85rem' }}
                      secondaryTypographyProps={{ fontSize: '0.75rem' }}
                    />
                    <IconButton
                      size="small"
                      onClick={(e) => {
                        e.stopPropagation();
                        onMoveFeature(feature);
                      }}
                      sx={{ opacity: 0.6, '&:hover': { opacity: 1 } }}
                    >
                      <DriveFileMove fontSize="small" />
                    </IconButton>
                  </ListItemButton>
                </ListItem>
              ))}
            </List>
          </Collapse>
        )}

        {/* Folder tree */}
        {folders.map((folder) => (
          <FolderItem
            key={folder.id}
            folder={folder}
            level={0}
            selectedFolderId={selectedFolderId}
            onSelectFolder={onSelectFolder}
            onCreateSubfolder={onCreateSubfolder}
            onRenameFolder={onRenameFolder}
            onDeleteFolder={onDeleteFolder}
            featuresInFolder={featuresByFolder[folder.id] || []}
            onFeatureClick={onFeatureClick}
            onMoveFeature={onMoveFeature}
            expandedFolders={expandedFolders}
            toggleFolderExpand={toggleFolderExpand}
          />
        ))}

        {/* Empty state */}
        {folders.length === 0 && rootFeatures.length === 0 && (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <FolderIcon sx={{ fontSize: 48, color: 'grey.300', mb: 1 }} />
            <Typography variant="body2" color="text.secondary">
              No folders yet
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Create folders to organize your features
            </Typography>
          </Box>
        )}
      </List>
    </Box>
  );
}
