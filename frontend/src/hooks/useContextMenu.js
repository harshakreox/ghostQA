import { useState, useCallback } from 'react';

/**
 * useContextMenu - Custom hook for managing context menu / action menu state
 *
 * @returns {Object} - { anchorEl, selectedItem, isOpen, openMenu, closeMenu }
 *
 * Usage:
 * const { anchorEl, selectedItem, isOpen, openMenu, closeMenu } = useContextMenu();
 *
 * // In JSX - Button to open menu:
 * <IconButton onClick={(e) => openMenu(e, item)}>
 *   <MoreVert />
 * </IconButton>
 *
 * // The Menu component:
 * <Menu anchorEl={anchorEl} open={isOpen} onClose={closeMenu}>
 *   <MenuItem onClick={() => { handleAction(selectedItem); closeMenu(); }}>
 *     Action
 *   </MenuItem>
 * </Menu>
 */
export default function useContextMenu() {
  const [anchorEl, setAnchorEl] = useState(null);
  const [selectedItem, setSelectedItem] = useState(null);

  const openMenu = useCallback((event, item = null) => {
    event.stopPropagation();
    setAnchorEl(event.currentTarget);
    setSelectedItem(item);
  }, []);

  const closeMenu = useCallback(() => {
    setAnchorEl(null);
    // Don't clear selectedItem immediately to allow access during menu item click handlers
    setTimeout(() => setSelectedItem(null), 100);
  }, []);

  const isOpen = Boolean(anchorEl);

  return {
    anchorEl,
    selectedItem,
    isOpen,
    openMenu,
    closeMenu,
  };
}

/**
 * useDialog - Custom hook for managing dialog open/close state
 *
 * @param {any} initialData - Initial data for the dialog
 * @returns {Object} - { isOpen, data, openDialog, closeDialog }
 *
 * Usage:
 * const { isOpen, data, openDialog, closeDialog } = useDialog();
 *
 * // Open with data:
 * openDialog({ id: 1, name: 'Item' });
 *
 * // Open without data:
 * openDialog();
 *
 * // In JSX:
 * <Dialog open={isOpen} onClose={closeDialog}>
 *   {data && <span>{data.name}</span>}
 * </Dialog>
 */
export function useDialog(initialData = null) {
  const [isOpen, setIsOpen] = useState(false);
  const [data, setData] = useState(initialData);

  const openDialog = useCallback((dialogData = null) => {
    setData(dialogData);
    setIsOpen(true);
  }, []);

  const closeDialog = useCallback(() => {
    setIsOpen(false);
    // Delay clearing data to allow exit animations
    setTimeout(() => setData(null), 200);
  }, []);

  return {
    isOpen,
    data,
    openDialog,
    closeDialog,
    setData,
  };
}
