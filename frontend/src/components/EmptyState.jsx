import React from 'react';
import { Box, Typography, Button } from '@mui/material';
import { InboxOutlined } from '@mui/icons-material';

/**
 * EmptyState - A reusable empty state placeholder component
 *
 * @param {React.ReactNode} icon - Icon component to display (defaults to InboxOutlined)
 * @param {string} title - The main title text
 * @param {string} description - Optional description text
 * @param {string} actionLabel - Optional action button label
 * @param {React.ReactNode} actionIcon - Optional action button icon
 * @param {function} onAction - Optional action button click handler
 * @param {string} size - Size variant: 'small', 'medium', 'large'
 */
export default function EmptyState({
  icon,
  title,
  description,
  actionLabel,
  actionIcon,
  onAction,
  size = 'medium',
}) {
  const sizeConfig = {
    small: { iconSize: 48, py: 4, titleVariant: 'body1', descVariant: 'body2' },
    medium: { iconSize: 64, py: 6, titleVariant: 'h6', descVariant: 'body2' },
    large: { iconSize: 80, py: 8, titleVariant: 'h5', descVariant: 'body1' },
  };

  const config = sizeConfig[size] || sizeConfig.medium;
  const IconComponent = icon || InboxOutlined;

  // Check if it's a valid React component (function or memo/forwardRef object)
  const isReactComponent = typeof IconComponent === 'function' ||
    (typeof IconComponent === 'object' && IconComponent !== null && IconComponent.$$typeof);

  return (
    <Box sx={{ textAlign: 'center', py: config.py }}>
      <Box
        sx={{
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          mb: 2,
        }}
      >
        {isReactComponent ? (
          <IconComponent sx={{ fontSize: config.iconSize, color: 'text.secondary' }} />
        ) : (
          <Box sx={{ fontSize: config.iconSize, color: 'text.secondary' }}>{IconComponent}</Box>
        )}
      </Box>
      <Typography variant={config.titleVariant} sx={{ mb: 1, fontWeight: 600 }}>
        {title}
      </Typography>
      {description && (
        <Typography variant={config.descVariant} color="text.secondary" sx={{ mb: actionLabel ? 3 : 0 }}>
          {description}
        </Typography>
      )}
      {actionLabel && onAction && (
        <Button
          variant="contained"
          startIcon={actionIcon}
          onClick={onAction}
          sx={{
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            boxShadow: '0px 4px 12px rgba(102, 126, 234, 0.4)',
          }}
        >
          {actionLabel}
        </Button>
      )}
    </Box>
  );
}
