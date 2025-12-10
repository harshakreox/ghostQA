import { Box, Typography, Button } from '@mui/material';

/**
 * PageHeader - A reusable page header component with title, subtitle, and action buttons
 *
 * @param {string} title - The main page title
 * @param {string} subtitle - Optional subtitle/description
 * @param {Array} actions - Array of action button configs: { label, icon, onClick, variant, color, gradient }
 * @param {React.ReactNode} children - Optional additional content to render in the header
 */
export default function PageHeader({ title, subtitle, actions = [], children }) {
  return (
    <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
      <Box>
        <Typography variant="h4" sx={{ fontWeight: 700, mb: subtitle ? 0.5 : 0 }}>
          {title}
        </Typography>
        {subtitle && (
          <Typography variant="body2" color="text.secondary">
            {subtitle}
          </Typography>
        )}
        {children}
      </Box>
      {actions.length > 0 && (
        <Box sx={{ display: 'flex', gap: 2 }}>
          {actions.map((action, index) => (
            <Button
              key={index}
              variant={action.variant || 'outlined'}
              color={action.color || 'primary'}
              startIcon={action.icon}
              onClick={action.onClick}
              disabled={action.disabled}
              sx={
                action.gradient
                  ? {
                      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                      boxShadow: '0px 4px 12px rgba(102, 126, 234, 0.4)',
                      color: 'white',
                      '&:hover': {
                        background: 'linear-gradient(135deg, #5a6fd6 0%, #6a4190 100%)',
                      },
                    }
                  : {}
              }
            >
              {action.label}
            </Button>
          ))}
        </Box>
      )}
    </Box>
  );
}
