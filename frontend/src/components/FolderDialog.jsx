import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Box,
  Typography,
  CircularProgress,
} from '@mui/material';
import { CreateNewFolder, Edit } from '@mui/icons-material';

export default function FolderDialog({
  open,
  onClose,
  onSubmit,
  mode = 'create', // 'create' | 'edit' | 'move-feature'
  folder = null, // For edit mode
  feature = null, // For move-feature mode
  folders = [], // Available folders for parent selection
  parentFolderId = null, // Pre-selected parent folder
  loading = false,
}) {
  const [name, setName] = useState('');
  const [selectedParentId, setSelectedParentId] = useState(null);
  const [selectedFolderId, setSelectedFolderId] = useState(null);

  useEffect(() => {
    if (mode === 'create') {
      setName('');
      setSelectedParentId(parentFolderId);
    } else if (mode === 'edit' && folder) {
      setName(folder.name);
      setSelectedParentId(folder.parent_folder_id || null);
    } else if (mode === 'move-feature' && feature) {
      setSelectedFolderId(feature.folder_id || null);
    }
  }, [mode, folder, feature, parentFolderId, open]);

  const handleSubmit = () => {
    if (mode === 'create') {
      onSubmit({ name, parent_folder_id: selectedParentId });
    } else if (mode === 'edit') {
      onSubmit({ name, parent_folder_id: selectedParentId });
    } else if (mode === 'move-feature') {
      onSubmit({ folder_id: selectedFolderId });
    }
  };

  const getTitle = () => {
    switch (mode) {
      case 'create':
        return 'Create New Folder';
      case 'edit':
        return 'Rename Folder';
      case 'move-feature':
        return 'Move Feature to Folder';
      default:
        return 'Folder';
    }
  };

  const getIcon = () => {
    switch (mode) {
      case 'create':
        return <CreateNewFolder sx={{ mr: 1 }} />;
      case 'edit':
        return <Edit sx={{ mr: 1 }} />;
      default:
        return null;
    }
  };

  // Flatten folder tree for select dropdown
  const flattenFolders = (folderList, level = 0, result = []) => {
    for (const f of folderList) {
      // Skip the folder being edited to prevent circular reference
      if (mode === 'edit' && folder && f.id === folder.id) continue;

      result.push({
        ...f,
        level,
        displayName: '\u00A0\u00A0'.repeat(level) + f.name,
      });
      if (f.children && f.children.length > 0) {
        flattenFolders(f.children, level + 1, result);
      }
    }
    return result;
  };

  const flatFolders = flattenFolders(folders);

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          {getIcon()}
          {getTitle()}
        </Box>
      </DialogTitle>

      <DialogContent>
        {mode === 'move-feature' ? (
          <Box sx={{ mt: 2 }}>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Select a folder to move "{feature?.name}" to:
            </Typography>
            <FormControl fullWidth>
              <InputLabel>Target Folder</InputLabel>
              <Select
                value={selectedFolderId || ''}
                onChange={(e) => setSelectedFolderId(e.target.value || null)}
                label="Target Folder"
              >
                <MenuItem value="">
                  <em>Root (No Folder)</em>
                </MenuItem>
                {flatFolders.map((f) => (
                  <MenuItem key={f.id} value={f.id}>
                    {f.displayName}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>
        ) : (
          <Box sx={{ mt: 2 }}>
            <TextField
              autoFocus
              fullWidth
              label="Folder Name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Login Tests, Sprint 5, Regression"
              sx={{ mb: 3 }}
            />

            {mode === 'create' && folders.length > 0 && (
              <FormControl fullWidth>
                <InputLabel>Parent Folder (Optional)</InputLabel>
                <Select
                  value={selectedParentId || ''}
                  onChange={(e) => setSelectedParentId(e.target.value || null)}
                  label="Parent Folder (Optional)"
                >
                  <MenuItem value="">
                    <em>Root Level</em>
                  </MenuItem>
                  {flatFolders.map((f) => (
                    <MenuItem key={f.id} value={f.id}>
                      {f.displayName}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            )}
          </Box>
        )}
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose} disabled={loading}>
          Cancel
        </Button>
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={loading || (mode !== 'move-feature' && !name.trim())}
          startIcon={loading ? <CircularProgress size={16} /> : null}
        >
          {loading ? 'Saving...' : mode === 'move-feature' ? 'Move' : mode === 'edit' ? 'Save' : 'Create'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
