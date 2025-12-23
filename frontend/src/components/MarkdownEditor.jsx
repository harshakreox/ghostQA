import MDEditor from '@uiw/react-md-editor';
import { Box, Typography } from '@mui/material';

export default function MarkdownEditor({
  value,
  onChange,
  height = 400,
  placeholder = 'Enter your content here...',
  label,
  helperText,
  minLength,
}) {
  return (
    <Box sx={{ mb: 2 }}>
      {label && (
        <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
          {label}
        </Typography>
      )}
      <Box
        data-color-mode="light"
        sx={{
          border: '1px solid',
          borderColor: 'divider',
          borderRadius: 2,
          overflow: 'hidden',
          '& .w-md-editor': {
            boxShadow: 'none !important',
          }
        }}
      >
        <MDEditor
          value={value}
          onChange={onChange}
          height={height}
          preview="edit"
          textareaProps={{
            placeholder,
          }}
        />
      </Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 0.5 }}>
        {helperText && (
          <Typography variant="caption" color="text.secondary">
            {helperText}
          </Typography>
        )}
        {minLength !== undefined && (
          <Typography
            variant="caption"
            color={value?.length >= minLength ? 'success.main' : 'text.secondary'}
            sx={{ ml: 'auto' }}
          >
            {value?.length || 0} / {minLength} characters
          </Typography>
        )}
      </Box>
    </Box>
  );
}
