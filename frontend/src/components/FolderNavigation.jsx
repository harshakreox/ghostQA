import { useState } from 'react';
import {
  Box,
  Typography,
  Button,
  Card,
  CardActionArea,
  CardContent,
  IconButton,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Chip,
  Breadcrumbs,
  Link,
  Tooltip,
  Divider,
  Paper,
  Grid,
  alpha,
} from '@mui/material';
import {
  Folder as FolderIcon,
  FolderOpen as FolderOpenIcon,
  CreateNewFolder,
  Add,
  Edit,
  Delete,
  MoreVert,
  NavigateNext,
  Home,
  ArrowBack,
} from '@mui/icons-material';

function FolderCard({ folder, featureCount, onClick, onMenuClick, isSelected }) {
  return (
    <Card
      variant="outlined"
      sx={{
        minWidth: 140,
        maxWidth: 180,
        transition: 'all 0.2s ease',
        border: isSelected ? 2 : 1,
        borderColor: isSelected ? 'primary.main' : 'divider',
        bgcolor: isSelected ? alpha('#667eea', 0.08) : 'background.paper',
        '&:hover': {
          borderColor: 'primary.main',
          transform: 'translateY(-2px)',
          boxShadow: 2,
        },
      }}
    >
      <CardActionArea onClick={onClick}>
        <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <FolderIcon sx={{ color: isSelected ? 'primary.main' : 'warning.main', fontSize: 28 }} />
            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Typography
                variant="body2"
                sx={{
                  fontWeight: 600,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
              >
                {folder.name}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {featureCount} feature{featureCount !== 1 ? 's' : ''}
              </Typography>
            </Box>
            <IconButton
              size="small"
              onClick={(e) => {
                e.stopPropagation();
                onMenuClick(e, folder);
              }}
              sx={{ ml: 'auto' }}
            >
              <MoreVert fontSize="small" />
            </IconButton>
          </Box>
        </CardContent>
      </CardActionArea>
    </Card>
  );
}

export default function FolderNavigation({
  folders = [],
  featuresByFolder = {},
  rootFeaturesCount = 0,
  selectedFolderId,
  folderPath = [],
  onSelectFolder,
  onCreateFolder,
  onRenameFolder,
  onDeleteFolder,
  loading = false,
}) {
  const [menuAnchor, setMenuAnchor] = useState(null);
  const [menuFolder, setMenuFolder] = useState(null);

  const handleMenuOpen = (e, folder) => {
    setMenuAnchor(e.currentTarget);
    setMenuFolder(folder);
  };

  const handleMenuClose = () => {
    setMenuAnchor(null);
    setMenuFolder(null);
  };

  // Get current folder's subfolders
  const currentFolders = selectedFolderId
    ? folders.filter(f => f.parent_folder_id === selectedFolderId)
    : folders.filter(f => !f.parent_folder_id);

  // Get feature count for a folder
  const getFeatureCount = (folderId) => {
    return (featuresByFolder[folderId] || []).length;
  };

  // Calculate total features (for "All" view)
  const totalFeatures = Object.values(featuresByFolder).reduce((sum, arr) => sum + arr.length, 0) + rootFeaturesCount;

  return (
    <Box sx={{ mb: 3 }}>
      {/* Breadcrumb Navigation */}
      {selectedFolderId && (
        <Box sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
          <IconButton size="small" onClick={() => onSelectFolder(null)}>
            <ArrowBack fontSize="small" />
          </IconButton>
          <Breadcrumbs separator={<NavigateNext fontSize="small" />}>
            <Link
              component="button"
              variant="body2"
              onClick={() => onSelectFolder(null)}
              sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}
              underline="hover"
            >
              <Home fontSize="small" />
              All Features
            </Link>
            {folderPath.map((folder, index) => (
              <Link
                key={folder.id}
                component="button"
                variant="body2"
                onClick={() => onSelectFolder(folder.id)}
                underline={index === folderPath.length - 1 ? 'none' : 'hover'}
                color={index === folderPath.length - 1 ? 'text.primary' : 'inherit'}
                sx={{ fontWeight: index === folderPath.length - 1 ? 600 : 400 }}
              >
                {folder.name}
              </Link>
            ))}
          </Breadcrumbs>
        </Box>
      )}

      {/* Folder Cards Row */}
      <Paper
        variant="outlined"
        sx={{
          p: 2,
          bgcolor: 'grey.50',
          borderRadius: 2,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <FolderOpenIcon sx={{ color: 'primary.main' }} />
            <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
              {selectedFolderId ? 'Subfolders' : 'Folders'}
            </Typography>
            {!selectedFolderId && (
              <Chip
                label={`${totalFeatures} total features`}
                size="small"
                variant="outlined"
                sx={{ ml: 1 }}
              />
            )}
          </Box>
          <Button
            variant="contained"
            size="small"
            startIcon={<CreateNewFolder />}
            onClick={() => onCreateFolder(selectedFolderId)}
            sx={{
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              textTransform: 'none',
            }}
          >
            New Folder
          </Button>
        </Box>

        {/* Folders Grid */}
        {currentFolders.length > 0 ? (
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1.5 }}>
            {/* All/Root Features Card (only at root level) */}
            {!selectedFolderId && (
              <Card
                variant="outlined"
                sx={{
                  minWidth: 140,
                  maxWidth: 180,
                  borderColor: selectedFolderId === null ? 'primary.main' : 'divider',
                  border: 2,
                  borderStyle: 'dashed',
                  bgcolor: alpha('#667eea', 0.04),
                }}
              >
                <CardActionArea onClick={() => onSelectFolder(null)}>
                  <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Home sx={{ color: 'primary.main', fontSize: 28 }} />
                      <Box>
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>
                          Uncategorized
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {rootFeaturesCount} feature{rootFeaturesCount !== 1 ? 's' : ''}
                        </Typography>
                      </Box>
                    </Box>
                  </CardContent>
                </CardActionArea>
              </Card>
            )}

            {/* Folder Cards */}
            {currentFolders.map((folder) => (
              <FolderCard
                key={folder.id}
                folder={folder}
                featureCount={getFeatureCount(folder.id)}
                onClick={() => onSelectFolder(folder.id)}
                onMenuClick={handleMenuOpen}
                isSelected={selectedFolderId === folder.id}
              />
            ))}
          </Box>
        ) : (
          <Box sx={{ textAlign: 'center', py: 3 }}>
            <FolderIcon sx={{ fontSize: 40, color: 'grey.300', mb: 1 }} />
            <Typography variant="body2" color="text.secondary">
              {selectedFolderId ? 'No subfolders' : 'No folders yet'}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Click "New Folder" to create one
            </Typography>
          </Box>
        )}
      </Paper>

      {/* Folder Context Menu */}
      <Menu
        anchorEl={menuAnchor}
        open={Boolean(menuAnchor)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={() => {
          onCreateFolder(menuFolder?.id);
          handleMenuClose();
        }}>
          <ListItemIcon><CreateNewFolder fontSize="small" /></ListItemIcon>
          <ListItemText>New Subfolder</ListItemText>
        </MenuItem>
        <MenuItem onClick={() => {
          onRenameFolder(menuFolder);
          handleMenuClose();
        }}>
          <ListItemIcon><Edit fontSize="small" /></ListItemIcon>
          <ListItemText>Rename</ListItemText>
        </MenuItem>
        <Divider />
        <MenuItem onClick={() => {
          onDeleteFolder(menuFolder);
          handleMenuClose();
        }} sx={{ color: 'error.main' }}>
          <ListItemIcon><Delete fontSize="small" color="error" /></ListItemIcon>
          <ListItemText>Delete</ListItemText>
        </MenuItem>
      </Menu>
    </Box>
  );
}
