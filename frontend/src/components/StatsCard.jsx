import { Card, CardContent, Box, Typography, Avatar, LinearProgress } from '@mui/material';

/**
 * StatsCard - A reusable statistics card component
 *
 * @param {string} label - The label/title for the stat
 * @param {string|number} value - The main value to display
 * @param {string} subtext - Optional subtext below the value
 * @param {React.ReactNode} icon - Icon component to display
 * @param {string} color - Color theme: 'primary', 'success', 'error', 'warning', 'info'
 * @param {boolean} gradient - Whether to use gradient background
 * @param {number} progress - Optional progress value (0-100) to show a progress bar
 * @param {function} onClick - Optional click handler
 */
export default function StatsCard({
  label,
  value,
  subtext,
  icon,
  color = 'primary',
  gradient = false,
  progress,
  onClick,
}) {
  const gradientStyles = gradient
    ? {
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        color: 'white',
      }
    : {};

  const avatarStyles = gradient
    ? { bgcolor: 'rgba(255,255,255,0.2)', width: 56, height: 56 }
    : { bgcolor: `${color}.light`, color: `${color}.main`, width: 56, height: 56 };

  const valueColor = gradient ? 'inherit' : `${color}.main`;

  return (
    <Card
      sx={{
        height: '100%',
        cursor: onClick ? 'pointer' : 'default',
        '&:hover': onClick ? { boxShadow: 6, transform: 'translateY(-2px)' } : {},
        transition: 'all 0.2s',
        ...gradientStyles,
      }}
      onClick={onClick}
    >
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <Box>
            <Typography
              variant="h3"
              sx={{
                fontWeight: 700,
                mb: 1,
                color: valueColor,
              }}
            >
              {value}
            </Typography>
            <Typography
              variant="body2"
              sx={{ opacity: gradient ? 0.9 : 1 }}
              color={gradient ? 'inherit' : 'text.secondary'}
            >
              {label}
            </Typography>
            {subtext && (
              <Typography
                variant="caption"
                sx={{ opacity: gradient ? 0.8 : 1, mt: 0.5, display: 'block' }}
                color={gradient ? 'inherit' : 'text.secondary'}
              >
                {subtext}
              </Typography>
            )}
          </Box>
          {icon && <Avatar sx={avatarStyles}>{icon}</Avatar>}
        </Box>
        {progress !== undefined && (
          <LinearProgress
            variant="determinate"
            value={progress}
            sx={{ mt: 2, height: 8, borderRadius: 1 }}
            color={color}
          />
        )}
      </CardContent>
    </Card>
  );
}
