import axios from 'axios';

/**
 * downloadFile - Downloads a file from a blob or URL
 *
 * @param {Blob|string} blobOrUrl - Either a Blob object or a URL string
 * @param {string} filename - The filename for the downloaded file
 *
 * Usage:
 * // From blob:
 * const blob = new Blob([data], { type: 'text/csv' });
 * downloadFile(blob, 'export.csv');
 *
 * // From URL (will fetch first):
 * await downloadFile('/api/export', 'export.csv');
 */
export function downloadFile(blobOrData, filename) {
  let url;
  let shouldRevoke = false;

  if (blobOrData instanceof Blob) {
    url = window.URL.createObjectURL(blobOrData);
    shouldRevoke = true;
  } else if (typeof blobOrData === 'string' && blobOrData.startsWith('data:')) {
    // Data URL
    url = blobOrData;
  } else {
    // Assume it's raw data, create a blob
    url = window.URL.createObjectURL(new Blob([blobOrData]));
    shouldRevoke = true;
  }

  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  if (shouldRevoke) {
    window.URL.revokeObjectURL(url);
  }
}

/**
 * downloadFromEndpoint - Fetches a file from an API endpoint and downloads it
 *
 * @param {string} endpoint - The API endpoint to fetch from
 * @param {string} filename - The filename for the downloaded file
 * @param {Object} options - Optional axios config
 * @returns {Promise<boolean>} - Returns true if successful, false otherwise
 *
 * Usage:
 * const success = await downloadFromEndpoint('/api/export/csv', 'report.csv');
 */
export async function downloadFromEndpoint(endpoint, filename, options = {}) {
  try {
    const response = await axios.get(endpoint, {
      responseType: 'blob',
      ...options,
    });

    downloadFile(response.data, filename);
    return true;
  } catch (error) {
    console.error('Error downloading file:', error);
    return false;
  }
}

/**
 * exportToCSV - Converts an array of objects to CSV and downloads it
 *
 * @param {Array<Object>} data - Array of objects to export
 * @param {string} filename - The filename for the CSV file
 * @param {Array<string>} columns - Optional array of column keys to include (in order)
 * @param {Object} headers - Optional object mapping column keys to display headers
 *
 * Usage:
 * const data = [{ name: 'Test 1', status: 'passed' }, { name: 'Test 2', status: 'failed' }];
 * exportToCSV(data, 'tests.csv');
 *
 * // With custom columns and headers:
 * exportToCSV(data, 'tests.csv', ['name', 'status'], { name: 'Test Name', status: 'Status' });
 */
export function exportToCSV(data, filename, columns = null, headers = null) {
  if (!data || data.length === 0) {
    console.warn('No data to export');
    return false;
  }

  // Determine columns from first object if not provided
  const cols = columns || Object.keys(data[0]);

  // Create header row
  const headerRow = cols.map((col) => {
    const header = headers?.[col] || col;
    return `"${String(header).replace(/"/g, '""')}"`;
  });

  // Create data rows
  const rows = data.map((item) =>
    cols.map((col) => {
      const value = item[col];
      if (value === null || value === undefined) return '""';
      return `"${String(value).replace(/"/g, '""')}"`;
    })
  );

  // Combine header and rows
  const csvContent = [headerRow.join(','), ...rows.map((row) => row.join(','))].join('\n');

  // Create and download
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  downloadFile(blob, filename.endsWith('.csv') ? filename : `${filename}.csv`);
  return true;
}

/**
 * exportToJSON - Exports data as a JSON file
 *
 * @param {any} data - Data to export (will be JSON stringified)
 * @param {string} filename - The filename for the JSON file
 * @param {boolean} pretty - Whether to pretty-print the JSON (default: true)
 *
 * Usage:
 * exportToJSON(myData, 'export.json');
 */
export function exportToJSON(data, filename, pretty = true) {
  const jsonString = pretty ? JSON.stringify(data, null, 2) : JSON.stringify(data);
  const blob = new Blob([jsonString], { type: 'application/json' });
  downloadFile(blob, filename.endsWith('.json') ? filename : `${filename}.json`);
  return true;
}

/**
 * formatFileSize - Formats bytes into human-readable file size
 *
 * @param {number} bytes - File size in bytes
 * @param {number} decimals - Number of decimal places (default: 2)
 * @returns {string} - Formatted file size string
 *
 * Usage:
 * formatFileSize(1024); // "1 KB"
 * formatFileSize(1234567); // "1.18 MB"
 */
export function formatFileSize(bytes, decimals = 2) {
  if (bytes === 0) return '0 Bytes';

  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return parseFloat((bytes / Math.pow(k, i)).toFixed(decimals)) + ' ' + sizes[i];
}

/**
 * getFileExtension - Extracts the file extension from a filename
 *
 * @param {string} filename - The filename
 * @returns {string} - The file extension (lowercase, without dot)
 *
 * Usage:
 * getFileExtension('report.pdf'); // "pdf"
 */
export function getFileExtension(filename) {
  return filename.slice(((filename.lastIndexOf('.') - 1) >>> 0) + 2).toLowerCase();
}
