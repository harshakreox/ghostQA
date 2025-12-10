import { useState, useCallback } from 'react';

/**
 * useNotification - Custom hook for managing snackbar/toast notifications
 *
 * @returns {Object} - { notification, showNotification, hideNotification, NotificationComponent }
 *
 * Usage:
 * const { notification, showNotification, hideNotification } = useNotification();
 *
 * showNotification('Success!', 'success');
 * showNotification('Error occurred', 'error');
 *
 * // In JSX:
 * <Snackbar
 *   open={notification.open}
 *   autoHideDuration={4000}
 *   onClose={hideNotification}
 *   anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
 * >
 *   <Alert onClose={hideNotification} severity={notification.severity} variant="filled">
 *     {notification.message}
 *   </Alert>
 * </Snackbar>
 */
export default function useNotification() {
  const [notification, setNotification] = useState({
    open: false,
    message: '',
    severity: 'success', // 'success' | 'error' | 'warning' | 'info'
  });

  const showNotification = useCallback((message, severity = 'success') => {
    setNotification({
      open: true,
      message,
      severity,
    });
  }, []);

  const hideNotification = useCallback(() => {
    setNotification((prev) => ({
      ...prev,
      open: false,
    }));
  }, []);

  const showSuccess = useCallback((message) => showNotification(message, 'success'), [showNotification]);
  const showError = useCallback((message) => showNotification(message, 'error'), [showNotification]);
  const showWarning = useCallback((message) => showNotification(message, 'warning'), [showNotification]);
  const showInfo = useCallback((message) => showNotification(message, 'info'), [showNotification]);

  return {
    notification,
    showNotification,
    hideNotification,
    showSuccess,
    showError,
    showWarning,
    showInfo,
  };
}
