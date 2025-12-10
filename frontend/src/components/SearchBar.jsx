import { useState, useEffect } from 'react';
import {
  TextField,
  InputAdornment,
  IconButton,
  Box,
  Chip,
  Collapse,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import { Search, Clear, FilterList } from '@mui/icons-material';

/**
 * SearchBar - A reusable search bar component with optional filters
 *
 * @param {string} placeholder - Placeholder text for the search input
 * @param {function} onSearch - Callback when search value changes
 * @param {string} value - Controlled value for the search input
 * @param {Array} filters - Optional array of filter configs: { key, label, options: [{ value, label }] }
 * @param {object} filterValues - Current filter values object
 * @param {function} onFilterChange - Callback when filter changes
 * @param {boolean} showFilters - Whether to show filter options
 * @param {string} size - Size of the input: 'small' or 'medium'
 * @param {number|string} minWidth - Minimum width for the search bar
 */
export default function SearchBar({
  placeholder = 'Search...',
  onSearch,
  value = '',
  filters = [],
  filterValues = {},
  onFilterChange,
  showFilters = false,
  size = 'small',
  minWidth = 220,
}) {
  const [localValue, setLocalValue] = useState(value);
  const [filtersExpanded, setFiltersExpanded] = useState(false);

  useEffect(() => {
    setLocalValue(value);
  }, [value]);

  const handleChange = (e) => {
    const newValue = e.target.value;
    setLocalValue(newValue);
    onSearch?.(newValue);
  };

  const handleClear = () => {
    setLocalValue('');
    onSearch?.('');
  };

  const handleFilterChange = (key, value) => {
    onFilterChange?.({ ...filterValues, [key]: value });
  };

  const activeFilterCount = Object.values(filterValues).filter(v => v && v !== 'all').length;

  return (
    <Box sx={{ minWidth, width: 'auto' }}>
      <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
        <TextField
          size={size}
          placeholder={placeholder}
          value={localValue}
          onChange={handleChange}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <Search color="action" />
              </InputAdornment>
            ),
            endAdornment: localValue && (
              <InputAdornment position="end">
                <IconButton size="small" onClick={handleClear}>
                  <Clear fontSize="small" />
                </IconButton>
              </InputAdornment>
            ),
          }}
          sx={{
            '& .MuiOutlinedInput-root': {
              borderRadius: 2,
              bgcolor: 'background.paper',
            },
          }}
        />
        {showFilters && filters.length > 0 && (
          <IconButton
            onClick={() => setFiltersExpanded(!filtersExpanded)}
            sx={{
              bgcolor: activeFilterCount > 0 ? 'primary.light' : 'transparent',
              '&:hover': { bgcolor: activeFilterCount > 0 ? 'primary.light' : 'action.hover' },
            }}
          >
            <FilterList color={activeFilterCount > 0 ? 'primary' : 'action'} />
            {activeFilterCount > 0 && (
              <Chip
                size="small"
                label={activeFilterCount}
                color="primary"
                sx={{
                  position: 'absolute',
                  top: -4,
                  right: -4,
                  height: 18,
                  minWidth: 18,
                  fontSize: '0.7rem',
                }}
              />
            )}
          </IconButton>
        )}
      </Box>

      {showFilters && filters.length > 0 && (
        <Collapse in={filtersExpanded}>
          <Box sx={{ display: 'flex', gap: 2, mt: 2, flexWrap: 'wrap' }}>
            {filters.map((filter) => (
              <FormControl key={filter.key} size="small" sx={{ minWidth: 150 }}>
                <InputLabel>{filter.label}</InputLabel>
                <Select
                  value={filterValues[filter.key] || 'all'}
                  label={filter.label}
                  onChange={(e) => handleFilterChange(filter.key, e.target.value)}
                >
                  <MenuItem value="all">All</MenuItem>
                  {filter.options.map((opt) => (
                    <MenuItem key={opt.value} value={opt.value}>
                      {opt.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            ))}
          </Box>
        </Collapse>
      )}
    </Box>
  );
}
