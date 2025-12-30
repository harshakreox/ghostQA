import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Box,
  Drawer,
  AppBar,
  Toolbar,
  List,
  Typography,
  Divider,
  IconButton,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Avatar,
  Chip,
  Tooltip,
  Menu,
  MenuItem,
  Badge,
  Snackbar,
  Alert,
  alpha,
} from '@mui/material';
import {
  Menu as MenuIcon,
  Dashboard as DashboardIcon,
  FolderOpen as ProjectsIcon,
  Assessment as ReportsIcon,
  Code as CodeIcon,
  Science as ScienceIcon,
  ChevronLeft as ChevronLeftIcon,
  ChevronRight as ChevronRightIcon,
  Logout as LogoutIcon,
  AccessTime as TimeIcon,
  Settings as SettingsIcon,
  AdminPanelSettings as AdminIcon,
  PlayArrow as PlayIcon,
  Business as BusinessIcon,
  CorporateFare as OrganizationsIcon,
} from '@mui/icons-material';
import { useAuth } from '../context/AuthContext';
import { useOrganization } from '../context/OrganizationContext';

const drawerWidth = 280;
const collapsedDrawerWidth = 72;

// All menu items with role requirements
const allMenuItems = [
  { text: 'Dashboard', icon: <DashboardIcon />, path: '/dashboard', roles: ['admin'], description: 'Overview & insights' },
  { text: 'Projects', icon: <ProjectsIcon />, path: '/projects', roles: ['admin', 'user'], description: 'Manage test projects' },
  { text: 'Test Lab', icon: <ScienceIcon />, path: '/test-lab', roles: ['admin'], description: 'Run & execute tests' },
  { text: 'AI Generator', icon: <CodeIcon />, path: '/generate', roles: ['admin', 'user'], description: 'Generate test cases' },
  { text: 'Reports', icon: <ReportsIcon />, path: '/reports', roles: ['admin'], description: 'Test results & analytics' },
  { text: 'Organizations', icon: <OrganizationsIcon />, path: '/organizations', roles: ['admin'], description: 'Manage all organizations (Super Admin)' },
  { text: 'Settings', icon: <SettingsIcon />, path: '/settings', roles: ['admin'], description: 'Users & configuration' },
];

export default function Layout({ children }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(true);
  const [anchorEl, setAnchorEl] = useState(null);
  const [timeRemaining, setTimeRemaining] = useState(null);
  const [welcomeToast, setWelcomeToast] = useState({ open: false, name: '' });
  const navigate = useNavigate();
  const location = useLocation();
  const { user, isAdmin, logout, getTimeUntilExpiry, refreshSession } = useAuth();
  const { isOrgAdmin, isManager, orgRole } = useOrganization();

  // Filter menu items based on user role
  const menuItems = allMenuItems.filter(item =>
    item.roles.includes(user?.role || 'user')
  );

  // Show welcome toast when user logs in
  useEffect(() => {
    if (location.state?.welcomeUser) {
      setWelcomeToast({ open: true, name: location.state.welcomeUser });
      // Clear the state so it doesn't show again on refresh
      window.history.replaceState({}, document.title);
    }
  }, [location.state]);

  // Update time remaining every minute
  useEffect(() => {
    const updateTime = () => {
      const remaining = getTimeUntilExpiry();
      setTimeRemaining(remaining);
    };

    updateTime();
    const interval = setInterval(updateTime, 60000);
    return () => clearInterval(interval);
  }, [getTimeUntilExpiry]);

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const handleCollapseToggle = () => {
    setCollapsed(!collapsed);
  };

  const handleUserMenuOpen = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleUserMenuClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = () => {
    handleUserMenuClose();
    logout();
    navigate('/login');
  };

  const handleRefreshSession = async () => {
    await refreshSession();
    handleUserMenuClose();
  };

  const formatTimeRemaining = (ms) => {
    if (!ms || ms <= 0) return '0m';
    const minutes = Math.floor(ms / 60000);
    if (minutes < 60) return `${minutes}m`;
    const hours = Math.floor(minutes / 60);
    return `${hours}h ${minutes % 60}m`;
  };

  const currentDrawerWidth = collapsed ? collapsedDrawerWidth : drawerWidth;
  const isSessionExpiringSoon = timeRemaining && timeRemaining < 5 * 60 * 1000; // Less than 5 minutes

  const drawer = (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Toolbar sx={{ px: collapsed ? 1.5 : 3, py: 2.5, justifyContent: collapsed ? 'center' : 'flex-start' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <Avatar
            sx={{
              width: 40,
              height: 40,
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            }}
          >
            <CodeIcon />
          </Avatar>
          {!collapsed && (
            <Box>
              <Typography variant="h6" sx={{ fontWeight: 700, lineHeight: 1.2 }}>
                GhostQA
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Enterprise Edition
              </Typography>
            </Box>
          )}
        </Box>
      </Toolbar>

      <Divider />

      <List sx={{ px: collapsed ? 1 : 2, py: 2 }}>
        {menuItems.map((item) => {
          const isActive = location.pathname === item.path;
          return (
            <ListItem key={item.text} disablePadding sx={{ mb: 0.5 }}>
              <Tooltip title={collapsed ? item.text : ''} placement="right" arrow>
                <ListItemButton
                  onClick={() => navigate(item.path)}
                  selected={isActive}
                  sx={{
                    borderRadius: 2,
                    justifyContent: collapsed ? 'center' : 'flex-start',
                    px: collapsed ? 1.5 : 2,
                    '&.Mui-selected': {
                      backgroundColor: 'primary.main',
                      color: 'white',
                      '&:hover': {
                        backgroundColor: 'primary.dark',
                      },
                      '& .MuiListItemIcon-root': {
                        color: 'white',
                      },
                    },
                  }}
                >
                  <ListItemIcon
                    sx={{
                      color: isActive ? 'inherit' : 'text.secondary',
                      minWidth: collapsed ? 'auto' : 40,
                      mr: collapsed ? 0 : 1,
                    }}
                  >
                    {item.icon}
                  </ListItemIcon>
                  {!collapsed && (
                    <ListItemText
                      primary={item.text}
                      primaryTypographyProps={{
                        fontWeight: isActive ? 600 : 500,
                      }}
                    />
                  )}
                </ListItemButton>
              </Tooltip>
            </ListItem>
          );
        })}
      </List>

      <Box sx={{ flexGrow: 1 }} />

      {/* Collapse Toggle Button */}
      <Box sx={{ px: collapsed ? 1 : 2, pb: 1 }}>
        <ListItemButton
          onClick={handleCollapseToggle}
          sx={{
            borderRadius: 2,
            justifyContent: collapsed ? 'center' : 'flex-start',
            bgcolor: 'action.hover',
            '&:hover': {
              bgcolor: 'action.selected',
            },
          }}
        >
          <ListItemIcon sx={{ minWidth: collapsed ? 'auto' : 40, mr: collapsed ? 0 : 1 }}>
            {collapsed ? <ChevronRightIcon /> : <ChevronLeftIcon />}
          </ListItemIcon>
          {!collapsed && (
            <ListItemText
              primary="Collapse"
              primaryTypographyProps={{ fontWeight: 500, fontSize: '0.875rem' }}
            />
          )}
        </ListItemButton>
      </Box>

      {!collapsed && (<Box sx={{ p: 2, pt: 1, borderTop: '1px solid', borderColor: 'divider', textAlign: 'center' }}>
        <Typography variant="body2" color="text.secondary">
          Logged in as <strong>{user?.username}</strong>
        </Typography>
      </Box>
      )}
    </Box>
  );

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <AppBar
        position="fixed"
        sx={{
          width: { sm: `calc(100% - ${currentDrawerWidth}px)` },
          ml: { sm: `${currentDrawerWidth}px` },
          backgroundColor: 'white',
          color: 'text.primary',
          transition: 'width 0.2s ease, margin-left 0.2s ease',
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { sm: 'none' } }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1, fontWeight: 600 }}>
            {menuItems.find(item => item.path === location.pathname)?.text || 'Test Automation'}
          </Typography>

          {/* Session Timer */}
          {timeRemaining && (
            <Tooltip title={isSessionExpiringSoon ? 'Session expiring soon! Click your profile to refresh.' : 'Session time remaining'}>
              <Chip
                icon={<TimeIcon />}
                label={formatTimeRemaining(timeRemaining)}
                size="small"
                color={isSessionExpiringSoon ? 'warning' : 'default'}
                variant="outlined"
                sx={{ mr: 2 }}
              />
            </Tooltip>
          )}

          {/* User Info & Menu */}
          <Tooltip title={user?.username || 'User'}>
            <IconButton onClick={handleUserMenuOpen} sx={{ ml: 1 }}>
              <Badge
                overlap="circular"
                anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
                badgeContent={
                  isAdmin ? (
                    <Avatar sx={{ width: 16, height: 16, bgcolor: 'warning.main' }}>
                      <AdminIcon sx={{ fontSize: 10 }} />
                    </Avatar>
                  ) : null
                }
              >
                <Avatar
                  sx={{
                    width: 36,
                    height: 36,
                    background: isAdmin
                      ? 'linear-gradient(135deg, #f57c00 0%, #ff9800 100%)'
                      : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  }}
                >
                  {user?.username?.charAt(0).toUpperCase() || 'U'}
                </Avatar>
              </Badge>
            </IconButton>
          </Tooltip>

          <Menu
            anchorEl={anchorEl}
            open={Boolean(anchorEl)}
            onClose={handleUserMenuClose}
            anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
            transformOrigin={{ vertical: 'top', horizontal: 'right' }}
          >
            <Box sx={{ px: 2, py: 1.5, minWidth: 200 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                {user?.username}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {user?.email}
              </Typography>
              <Chip
                label={isAdmin ? 'Admin' : 'User'}
                size="small"
                color={isAdmin ? 'warning' : 'primary'}
                sx={{ mt: 0.5, display: 'block', width: 'fit-content' }}
              />
            </Box>
            <Divider />
            <MenuItem onClick={handleRefreshSession}>
              <ListItemIcon>
                <TimeIcon fontSize="small" />
              </ListItemIcon>
              <ListItemText primary="Extend Session" />
            </MenuItem>
            <MenuItem onClick={handleLogout}>
              <ListItemIcon>
                <LogoutIcon fontSize="small" />
              </ListItemIcon>
              <ListItemText primary="Logout" />
            </MenuItem>
          </Menu>

          <Chip
            icon={<PlayIcon />}
            label="Ready"
            color="success"
            size="small"
            sx={{ fontWeight: 600, ml: 2 }}
          />
        </Toolbar>
      </AppBar>

      <Box
        component="nav"
        sx={{ width: { sm: currentDrawerWidth }, flexShrink: { sm: 0 }, transition: 'width 0.2s ease' }}
      >
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{ keepMounted: true }}
          sx={{
            display: { xs: 'block', sm: 'none' },
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: drawerWidth,
            },
          }}
        >
          {drawer}
        </Drawer>
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', sm: 'block' },
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: currentDrawerWidth,
              borderRight: '1px solid',
              borderColor: 'divider',
              transition: 'width 0.2s ease',
              overflowX: 'hidden',
            },
          }}
          open
        >
          {drawer}
        </Drawer>
      </Box>

      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: { sm: `calc(100% - ${currentDrawerWidth}px)` },
          mt: 8,
          backgroundColor: 'background.default',
          minHeight: '100vh',
          transition: 'width 0.2s ease',
        }}
      >
        {children}
      </Box>

      {/* Welcome Toast */}
      <Snackbar
        open={welcomeToast.open}
        autoHideDuration={4000}
        onClose={() => setWelcomeToast({ open: false, name: '' })}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert
          onClose={() => setWelcomeToast({ open: false, name: '' })}
          severity="success"
          variant="filled"
          sx={{ width: '100%' }}
        >
          Welcome back, {welcomeToast.name}!
        </Alert>
      </Snackbar>
    </Box>
  );
}
