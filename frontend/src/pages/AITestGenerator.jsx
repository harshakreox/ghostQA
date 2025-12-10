import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Box,
  Button,
  Card,
  CardContent,
  Typography,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  LinearProgress,
  Chip,
  Paper,
  Tabs,
  Tab,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Grid,
  Tooltip,
  Stack,
  FormControlLabel,
  Checkbox,
  Fade,
  Snackbar,
  ToggleButton,
  ToggleButtonGroup,
  TableContainer,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  IconButton,
  CircularProgress,
} from '@mui/material';
import {
  CloudUpload,
  ContentPaste,
  AutoAwesome,
  CheckCircle,
  Add,
  Psychology,
  Description,
  AddCircleOutline,
  Download,
  GetApp,
  TableChart,
  Code,
  Refresh,
  Widgets,
} from '@mui/icons-material';
import axios from 'axios';
import CreativeLoader from '../components/CreativeLoader';

// Import hooks and utilities
import { useNotification } from '../hooks';
import { downloadFile } from '../utils';

function TabPanel({ children, value, index }) {
  return (
    <div hidden={value !== index}>
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
}

export default function AITestGenerator() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const preselectedProjectId = searchParams.get('projectId');

  const [tabValue, setTabValue] = useState(0);
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState(preselectedProjectId || '');
  
  // Input state
  const [brdText, setBrdText] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [additionalContext, setAdditionalContext] = useState('');

  // Data Dictionary state
  const [dataDictFile, setDataDictFile] = useState(null);
  const [formName, setFormName] = useState('');
  const [dataDictPreview, setDataDictPreview] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  
  // Generation state - GHERKIN
  const [generating, setGenerating] = useState(false);
  const [generated, setGenerated] = useState(false);
  const [generatedFeature, setGeneratedFeature] = useState(null);
  const [selectedScenarios, setSelectedScenarios] = useState([]);
  const [brdSummary, setBrdSummary] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  
  // NEW: End-to-End checkbox state
  const [isEndToEnd, setIsEndToEnd] = useState(false);

  // NEW: Format type state (gherkin or traditional)
  const [formatType, setFormatType] = useState('gherkin');

  // NEW: Traditional test suite state
  const [generatedTestSuite, setGeneratedTestSuite] = useState(null);
  const [selectedTestCases, setSelectedTestCases] = useState([]);

  // API key check
  const [apiKeyConfigured, setApiKeyConfigured] = useState(false);
  const [checkingAPI, setCheckingAPI] = useState(true);
  const [apiService, setApiService] = useState(null);
  const [apiModel, setApiModel] = useState(null);
  const [availableModels, setAvailableModels] = useState([]);

  // Create project state
  const [showCreateProjectDialog, setShowCreateProjectDialog] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');
  const [newProjectDescription, setNewProjectDescription] = useState('');
  const [creatingProject, setCreatingProject] = useState(false);

  // Use notification hook
  const { notification, showNotification, hideNotification } = useNotification();

  // Loading state for adding to project
  const [addingToProject, setAddingToProject] = useState(false);

  useEffect(() => {
    loadProjects();
    checkApiKey();
  }, []);

  const loadProjects = async () => {
    try {
      const response = await axios.get('/api/projects');
      setProjects(response.data);
    } catch (error) {
      console.error('Error loading projects:', error);
    }
  };

  const checkApiKey = async () => {
    setCheckingAPI(true);
    try {
      const response = await axios.get('/api/ai/check-api-key');
      setApiKeyConfigured(response.data.configured);
      setApiService(response.data.service);
      setApiModel(response.data.model);
      setAvailableModels(response.data.available_models || []);
    } catch (error) {
      console.error('Error checking API key:', error);
      setApiKeyConfigured(false);
    } finally {
      setCheckingAPI(false);
    }
  };

  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    if (file) {
      setSelectedFile(file);
      setTabValue(0);
    }
  };

  const handleGenerateFromText = async () => {
    if (!brdText || brdText.trim().length < 50) {
      showNotification('Please provide at least 50 characters of BRD content', 'warning');
      return;
    }

    setGenerating(true);

    try {
      const endpoint = formatType === 'traditional'
        ? '/api/traditional/generate-from-text'
        : '/api/gherkin/generate-from-text';

      const response = await axios.post(endpoint, {
        brd_content: brdText,
        project_id: selectedProject || null,
        project_context: additionalContext || null,
        end_to_end: isEndToEnd,
      });

      if (formatType === 'traditional') {
        handleTraditionalGenerationSuccess(response.data);
      } else {
        handleGenerationSuccess(response.data);
      }
    } catch (error) {
      console.error('Error generating test cases:', error);
      showNotification(error.response?.data?.detail || 'Failed to generate test cases', 'error');
    } finally {
      setGenerating(false);
    }
  };

  const handleGenerateFromFile = async () => {
    if (!selectedFile) {
      showNotification('Please select a file', 'warning');
      return;
    }

    setGenerating(true);

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      if (selectedProject) formData.append('project_id', selectedProject);
      if (additionalContext) formData.append('project_context', additionalContext);
      formData.append('end_to_end', isEndToEnd);

      const endpoint = formatType === 'traditional'
        ? '/api/traditional/generate-from-file'
        : '/api/gherkin/generate-from-file';

      const response = await axios.post(endpoint, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      if (formatType === 'traditional') {
        handleTraditionalGenerationSuccess(response.data);
      } else {
        handleGenerationSuccess(response.data);
      }
    } catch (error) {
      console.error('Error generating test cases:', error);
      showNotification(error.response?.data?.detail || 'Failed to generate test cases', 'error');
    } finally {
      setGenerating(false);
    }
  };

  const handleDataDictFileSelect = async (event) => {
    const file = event.target.files[0];
    if (file) {
      setDataDictFile(file);
      setDataDictPreview(null);

      // Auto-preview the file
      setPreviewLoading(true);
      try {
        const formData = new FormData();
        formData.append('file', file);

        const response = await axios.post('/api/data-dictionary/preview', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });

        setDataDictPreview(response.data);
      } catch (error) {
        console.error('Error previewing file:', error);
        setDataDictPreview({
          success: false,
          error: error.response?.data?.detail || 'Failed to parse file'
        });
      } finally {
        setPreviewLoading(false);
      }
    }
  };

  const handleGenerateFromDataDict = async () => {
    if (!dataDictFile) {
      showNotification('Please select a data dictionary file', 'warning');
      return;
    }

    setGenerating(true);

    try {
      const formData = new FormData();
      formData.append('file', dataDictFile);
      if (selectedProject) formData.append('project_id', selectedProject);
      if (formName) formData.append('form_name', formName);
      formData.append('output_format', formatType);

      const response = await axios.post('/api/data-dictionary/generate', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      if (formatType === 'traditional') {
        handleTraditionalGenerationSuccess({
          test_suite: response.data.test_suite,
          brd_summary: response.data.summary,
          suggestions: response.data.suggestions,
        });
      } else {
        handleGenerationSuccess({
          feature: response.data.feature,
          brd_summary: response.data.summary,
          suggestions: response.data.suggestions,
        });
      }

      // Show warnings if any scenarios might be missing
      const { field_count, scenario_count, warnings } = response.data;
      if (warnings && warnings.length > 0) {
        showNotification(
          `Generated ${scenario_count} scenarios for ${field_count} fields. ${warnings[0]}`,
          'warning'
        );
      } else {
        showNotification(
          `Generated ${scenario_count || 'validation'} scenarios for ${field_count || 'all'} fields!`,
          'success'
        );
      }
    } catch (error) {
      console.error('Error generating from data dictionary:', error);
      showNotification(error.response?.data?.detail || 'Failed to generate validation scenarios', 'error');
    } finally {
      setGenerating(false);
    }
  };

  const handleDownloadTemplate = async () => {
    try {
      const response = await axios.get('/api/data-dictionary/template', { responseType: 'blob' });
      downloadFile(response.data, 'data_dictionary_template.csv');
      showNotification('Template downloaded!', 'success');
    } catch (error) {
      console.error('Error downloading template:', error);
      showNotification('Failed to download template', 'error');
    }
  };

  const handleGenerationSuccess = (data) => {
    console.log('🔍 Generation Response:', data);

    if (data.feature && Array.isArray(data.feature.scenarios)) {
      setGeneratedFeature(data.feature);
      setBrdSummary(data.brd_summary || '');
      setSuggestions(data.suggestions || []);
      setSelectedScenarios(data.feature.scenarios.map((_, idx) => idx));
      setGenerated(true);
      showNotification(`Generated ${data.feature.scenarios.length} scenarios successfully!`, 'success');
    } else {
      console.error('Invalid feature data:', data);
      showNotification('Failed to parse generated scenarios. Please try again.', 'error');
    }
  };

  const handleTraditionalGenerationSuccess = (data) => {
    console.log('🔍 Traditional Generation Response:', data);

    if (data.test_suite && Array.isArray(data.test_suite.test_cases)) {
      setGeneratedTestSuite(data.test_suite);
      setBrdSummary(data.brd_summary || '');
      setSuggestions(data.suggestions || []);
      setSelectedTestCases(data.test_suite.test_cases.map((_, idx) => idx));
      setGenerated(true);
      showNotification(`Generated ${data.test_suite.test_cases.length} test cases successfully!`, 'success');
    } else {
      console.error('Invalid test suite data:', data);
      showNotification('Failed to parse generated test cases. Please try again.', 'error');
    }
  };

  const handleToggleScenario = (index) => {
    setSelectedScenarios((prev) =>
      prev.includes(index) ? prev.filter((i) => i !== index) : [...prev, index]
    );
  };

  const handleToggleTestCase = (index) => {
    setSelectedTestCases((prev) =>
      prev.includes(index) ? prev.filter((i) => i !== index) : [...prev, index]
    );
  };

  const handleCreateProject = async () => {
    if (!newProjectName.trim()) {
      showNotification('Please enter a project name', 'warning');
      return;
    }

    setCreatingProject(true);

    try {
      const response = await axios.post('/api/projects', {
        name: newProjectName,
        description: newProjectDescription || '',
      });

      const newProject = response.data;

      setProjects([...projects, newProject]);
      setSelectedProject(newProject.id);

      setShowCreateProjectDialog(false);
      setNewProjectName('');
      setNewProjectDescription('');

      showNotification('Project created successfully!', 'success');
    } catch (error) {
      console.error('Error creating project:', error);
      showNotification(error.response?.data?.detail || 'Failed to create project', 'error');
    } finally {
      setCreatingProject(false);
    }
  };

  const handleAddToProject = async () => {
    if (!selectedProject) {
      showNotification('Please select a project', 'warning');
      return;
    }

    // Check based on format type
    if (formatType === 'traditional') {
      if (selectedTestCases.length === 0) {
        showNotification('Please select at least one test case', 'warning');
        return;
      }

      if (!generatedTestSuite || !generatedTestSuite.id) {
        showNotification('No test suite to add', 'error');
        return;
      }

      setAddingToProject(true);

      try {
        await axios.post('/api/traditional/link-to-project', {
          suite_id: generatedTestSuite.id,
          project_id: selectedProject
        });

        showNotification(`Successfully linked test suite with ${selectedTestCases.length} test cases to project!`, 'success');

        setTimeout(() => {
          navigate(`/projects/${selectedProject}`);
        }, 1000);
      } catch (error) {
        console.error('Error adding test suite to project:', error);
        showNotification(error.response?.data?.detail || 'Failed to add test suite to project', 'error');
      } finally {
        setAddingToProject(false);
      }
    } else {
      // Gherkin format
      if (selectedScenarios.length === 0) {
        showNotification('Please select at least one scenario', 'warning');
        return;
      }

      if (!generatedFeature || !generatedFeature.id) {
        showNotification('No feature to add', 'error');
        return;
      }

      setAddingToProject(true);

      try {
        await axios.post('/api/gherkin/link-to-project', {
          feature_id: generatedFeature.id,
          project_id: selectedProject
        });

        showNotification(`Successfully linked feature with ${selectedScenarios.length} scenarios to project!`, 'success');

        setTimeout(() => {
          navigate(`/projects/${selectedProject}`);
        }, 1000);
      } catch (error) {
        console.error('Error adding feature to project:', error);
        showNotification(error.response?.data?.detail || 'Failed to add feature to project', 'error');
      } finally {
        setAddingToProject(false);
      }
    }
  };

  const handleReset = () => {
    setGenerated(false);
    setGeneratedFeature(null);
    setSelectedScenarios([]);
    setGeneratedTestSuite(null);
    setSelectedTestCases([]);
    setBrdSummary('');
    setSuggestions([]);
    setBrdText('');
    setSelectedFile(null);
    setDataDictFile(null);
    setFormName('');
    setDataDictPreview(null);
    setIsEndToEnd(false);
  };

  const handleExportFeature = async (format) => {
    if (formatType === 'traditional') {
      // Export Traditional test suite
      if (!generatedTestSuite) {
        showNotification('No test suite to export', 'warning');
        return;
      }

      try {
        const endpoint = format === 'json'
          ? `/api/traditional/suites/${generatedTestSuite.id}/export/json`
          : `/api/traditional/suites/${generatedTestSuite.id}/export/csv`;

        const response = await axios.get(endpoint, { responseType: 'blob' });

        const filename = format === 'json'
          ? `${generatedTestSuite.name.replace(/\s+/g, '_')}.json`
          : `${generatedTestSuite.name.replace(/\s+/g, '_')}.csv`;

        downloadFile(response.data, filename);
        showNotification(`Exported ${filename} successfully!`, 'success');
      } catch (error) {
        console.error('Error exporting test suite:', error);
        showNotification('Failed to export test suite', 'error');
      }
    } else {
      // Export Gherkin feature
      if (!generatedFeature) {
        showNotification('No feature to export', 'warning');
        return;
      }

      try {
        const endpoint = format === 'json'
          ? `/api/gherkin/features/${generatedFeature.id}/export/json`
          : `/api/gherkin/features/${generatedFeature.id}/export`;

        const response = await axios.get(endpoint, { responseType: 'blob' });

        const filename = format === 'json'
          ? `${generatedFeature.name.replace(/\s+/g, '_')}.json`
          : `${generatedFeature.name.replace(/\s+/g, '_')}.feature`;

        downloadFile(response.data, filename);
        showNotification(`Exported ${filename} successfully!`, 'success');
      } catch (error) {
        console.error('Error exporting feature:', error);
        showNotification('Failed to export feature', 'error');
      }
    }
  };

  if (checkingAPI) {
    return (
      <Box>
        <Typography variant="h4" sx={{ fontWeight: 700, mb: 3 }}>
          AI Test Case Generator
        </Typography>
        <Card>
          <CardContent sx={{ textAlign: 'center', py: 8 }}>
            <LinearProgress sx={{ mb: 3 }} />
            <Typography variant="h6" color="text.secondary">
              Checking AI Service...
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              Detecting available LLM (Ollama, Anthropic, etc.)
            </Typography>
          </CardContent>
        </Card>
      </Box>
    );
  }

  if (!apiKeyConfigured) {
    return (
      <Box>
        <Typography variant="h4" sx={{ fontWeight: 700, mb: 3 }}>
          AI Test Case Generator
        </Typography>
        <Alert severity="error">
          <Typography variant="h6" sx={{ mb: 1 }}>
            No AI Service Configured
          </Typography>
          <Typography variant="body2" sx={{ mb: 2 }}>
            No AI service was detected. Please set up one of the following:
          </Typography>
          
          <Typography variant="subtitle2" sx={{ fontWeight: 600, mt: 2, mb: 1 }}>
            Option 1: Ollama (Recommended - FREE)
          </Typography>
          <ol style={{ margin: 0, paddingLeft: 20 }}>
            <li>Install from: https://ollama.ai</li>
            <li>Run: <code>ollama pull llama3.1</code></li>
            <li>Run: <code>ollama serve</code></li>
            <li>Refresh this page</li>
          </ol>

          <Typography variant="subtitle2" sx={{ fontWeight: 600, mt: 2, mb: 1 }}>
            Option 2: Anthropic Claude (Paid)
          </Typography>
          <ol style={{ margin: 0, paddingLeft: 20 }}>
            <li>Get API key from: https://console.anthropic.com/</li>
            <li>Set: <code>setx ANTHROPIC_API_KEY "sk-ant-..."</code></li>
            <li>Restart backend</li>
          </ol>

          <Button 
            variant="contained" 
            onClick={checkApiKey}
            sx={{ mt: 3 }}
          >
            Check Again
          </Button>
        </Alert>
      </Box>
    );
  }

  if (!generated) {
    return (
      <Box>
        {/* Header */}
        <Box sx={{ mb: 4 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
            <Psychology sx={{ fontSize: 40, color: 'primary.main' }} />
            <Typography variant="h4" sx={{ fontWeight: 700 }}>
              AI Test Case Generator (BDD/Gherkin)
            </Typography>
            {apiService && (
              <Tooltip
                title={
                  availableModels.length > 1
                    ? `Available models: ${availableModels.join(', ')}`
                    : ''
                }
                arrow
              >
                <Chip
                  label={`Using ${apiService}: ${apiModel}`}
                  color="success"
                  size="small"
                  icon={<CheckCircle />}
                />
              </Tooltip>
            )}
            <Tooltip title="Refresh AI service status" arrow>
              <IconButton
                onClick={checkApiKey}
                disabled={checkingAPI}
                size="small"
                sx={{
                  bgcolor: 'action.hover',
                  '&:hover': { bgcolor: 'action.selected' },
                }}
              >
                {checkingAPI ? (
                  <CircularProgress size={18} />
                ) : (
                  <Refresh fontSize="small" />
                )}
              </IconButton>
            </Tooltip>
          </Box>
          <Typography variant="body2" color="text.secondary">
            Upload or paste your BRD document and let AI generate BDD test scenarios in Gherkin format
          </Typography>
        </Box>

        {/* Project Selection */}
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                Target Project (Optional)
              </Typography>
              <Button
                startIcon={<AddCircleOutline />}
                size="small"
                onClick={() => setShowCreateProjectDialog(true)}
              >
                Create New Project
              </Button>
            </Box>
            <FormControl fullWidth>
              <InputLabel>Select Project</InputLabel>
              <Select
                value={selectedProject}
                label="Select Project"
                onChange={(e) => setSelectedProject(e.target.value)}
              >
                <MenuItem value="">
                  <em>None - I'll add to project later</em>
                </MenuItem>
                {projects.map((project) => (
                  <MenuItem key={project.id} value={project.id}>
                    {project.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {/* Display selected project's UI frameworks */}
            {selectedProject && (() => {
              const project = projects.find((p) => p.id === selectedProject);
              const frameworks = project?.ui_config?.frameworks || [];
              const primaryFramework = project?.ui_config?.primary_framework;

              if (frameworks.length > 0) {
                return (
                  <Alert
                    severity="info"
                    icon={<Widgets />}
                    sx={{ mt: 2 }}
                  >
                    <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 0.5 }}>
                      UI Frameworks Configured:
                    </Typography>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 1 }}>
                      {frameworks.map((fw) => (
                        <Chip
                          key={fw}
                          label={fw}
                          size="small"
                          color={primaryFramework === fw ? 'primary' : 'default'}
                          variant={primaryFramework === fw ? 'filled' : 'outlined'}
                        />
                      ))}
                    </Box>
                    <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                      AI will use framework-specific selectors and component knowledge for test generation.
                    </Typography>
                  </Alert>
                );
              }
              return null;
            })()}

            <TextField
              label="Additional Context (Optional)"
              value={additionalContext}
              onChange={(e) => setAdditionalContext(e.target.value)}
              fullWidth
              multiline
              rows={2}
              sx={{ mt: 2 }}
              placeholder="E.g., This is an e-commerce application, focus on checkout flow..."
            />
          </CardContent>
        </Card>

        {/* Format Selection */}
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
              Output Format
            </Typography>
            <ToggleButtonGroup
              value={formatType}
              exclusive
              onChange={(e, newFormat) => newFormat && setFormatType(newFormat)}
              aria-label="test case format"
              fullWidth
            >
              <ToggleButton value="gherkin" aria-label="gherkin format">
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Code />
                  <Box sx={{ textAlign: 'left' }}>
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                      Gherkin (BDD)
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Given-When-Then format
                    </Typography>
                  </Box>
                </Box>
              </ToggleButton>
              <ToggleButton value="traditional" aria-label="traditional format">
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <TableChart />
                  <Box sx={{ textAlign: 'left' }}>
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                      Traditional Table
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Steps, Expected, Post-condition
                    </Typography>
                  </Box>
                </Box>
              </ToggleButton>
            </ToggleButtonGroup>
          </CardContent>
        </Card>

        {/* Input Methods */}
        <Paper sx={{ mb: 3 }}>
          <Tabs value={tabValue} onChange={(e, newValue) => setTabValue(newValue)}>
            <Tab icon={<CloudUpload />} label="Upload File" />
            <Tab icon={<ContentPaste />} label="Paste Text" />
            <Tab icon={<TableChart />} label="Data Dictionary" />
          </Tabs>
        </Paper>

        {/* File Upload Tab */}
        <TabPanel value={tabValue} index={0}>
          <Card>
            <CardContent>
              <Box
                sx={{
                  border: '2px dashed',
                  borderColor: 'divider',
                  borderRadius: 2,
                  p: 4,
                  textAlign: 'center',
                  cursor: 'pointer',
                  '&:hover': {
                    borderColor: 'primary.main',
                    bgcolor: 'action.hover',
                  },
                }}
                onClick={() => document.getElementById('file-input').click()}
              >
                <input
                  id="file-input"
                  type="file"
                  accept=".txt,.pdf,.docx"
                  style={{ display: 'none' }}
                  onChange={handleFileSelect}
                />
                <Description sx={{ fontSize: 60, color: 'text.secondary', mb: 2 }} />
                <Typography variant="h6" sx={{ mb: 1 }}>
                  {selectedFile ? selectedFile.name : 'Click to upload BRD document'}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Supported formats: PDF, DOCX, TXT
                </Typography>
                {selectedFile && (
                  <Chip
                    label={`${(selectedFile.size / 1024).toFixed(2)} KB`}
                    color="primary"
                    sx={{ mt: 2 }}
                  />
                )}
              </Box>

              {/* NEW: E2E Checkbox */}
              <Box sx={{ mt: 3, mb: 2 }}>
                <Tooltip 
                  title="Generate comprehensive end-to-end test scenarios covering complete user journeys from start to finish"
                  arrow
                  placement="top"
                >
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={isEndToEnd}
                        onChange={(e) => setIsEndToEnd(e.target.checked)}
                        sx={{
                          color: '#667eea',
                          '&.Mui-checked': {
                            color: '#667eea',
                          },
                        }}
                      />
                    }
                    label={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography variant="body1">
                          End-to-End Feature File
                        </Typography>
                        <Chip
                          label="Comprehensive"
                          size="small"
                          sx={{
                            bgcolor: isEndToEnd ? '#667eea' : 'default',
                            color: isEndToEnd ? 'white' : 'default',
                            fontSize: '0.7rem',
                            height: '20px',
                          }}
                        />
                      </Box>
                    }
                  />
                </Tooltip>
              </Box>

              {/* Info about E2E mode */}
              {isEndToEnd && (
                <Fade in={isEndToEnd}>
                  <Alert 
                    severity="info" 
                    sx={{ mb: 2 }}
                    icon={<Psychology />}
                  >
                    <Typography variant="body2">
                      <strong>End-to-End Mode Active:</strong> Generating 15-25 comprehensive scenarios 
                      covering complete user journeys, including navigation, happy paths, edge cases, 
                      and error handling in a single cohesive feature file.
                    </Typography>
                  </Alert>
                </Fade>
              )}

              <Button
                variant="contained"
                size="large"
                fullWidth
                startIcon={generating ? null : <AutoAwesome />}
                onClick={handleGenerateFromFile}
                disabled={!selectedFile || generating}
                sx={{ mt: 2 }}
              >
                {generating ? 'Generating BDD Scenarios...' : 'Generate with AI'}
              </Button>
            </CardContent>
          </Card>
        </TabPanel>

        {/* Text Paste Tab */}
        <TabPanel value={tabValue} index={1}>
          <Card>
            <CardContent>
              <TextField
                label="Paste BRD Content"
                value={brdText}
                onChange={(e) => setBrdText(e.target.value)}
                fullWidth
                multiline
                rows={15}
                placeholder="Paste your Business Requirements Document here...

Example:
Feature: User Login
The system shall allow users to authenticate using email and password.
- Users must enter a valid email address
- Password must be at least 8 characters
- System shall display error messages for invalid credentials
- After successful login, user is redirected to dashboard
..."
                sx={{ mb: 2 }}
              />
              <Typography variant="caption" color="text.secondary">
                Characters: {brdText.length} (minimum 50)
              </Typography>

              {/* NEW: E2E Checkbox */}
              <Box sx={{ mt: 2, mb: 2 }}>
                <Tooltip 
                  title="Generate comprehensive end-to-end test scenarios covering complete user journeys from start to finish"
                  arrow
                  placement="top"
                >
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={isEndToEnd}
                        onChange={(e) => setIsEndToEnd(e.target.checked)}
                        sx={{
                          color: '#667eea',
                          '&.Mui-checked': {
                            color: '#667eea',
                          },
                        }}
                      />
                    }
                    label={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography variant="body1">
                          End-to-End Feature File
                        </Typography>
                        <Chip
                          label="Comprehensive"
                          size="small"
                          sx={{
                            bgcolor: isEndToEnd ? '#667eea' : 'default',
                            color: isEndToEnd ? 'white' : 'default',
                            fontSize: '0.7rem',
                            height: '20px',
                          }}
                        />
                      </Box>
                    }
                  />
                </Tooltip>
              </Box>

              {/* Info about E2E mode */}
              {isEndToEnd && (
                <Fade in={isEndToEnd}>
                  <Alert 
                    severity="info" 
                    sx={{ mb: 2 }}
                    icon={<Psychology />}
                  >
                    <Typography variant="body2">
                      <strong>End-to-End Mode Active:</strong> Generating 15-25 comprehensive scenarios 
                      covering complete user journeys, including navigation, happy paths, edge cases, 
                      and error handling in a single cohesive feature file.
                    </Typography>
                  </Alert>
                </Fade>
              )}

              <Button
                variant="contained"
                size="large"
                fullWidth
                startIcon={generating ? null : <AutoAwesome />}
                onClick={handleGenerateFromText}
                disabled={brdText.length < 50 || generating}
              >
                {generating ? 'Generating BDD Scenarios...' : 'Generate with AI'}
              </Button>
            </CardContent>
          </Card>
        </TabPanel>

        {/* Data Dictionary Tab */}
        <TabPanel value={tabValue} index={2}>
          <Card>
            <CardContent>
              <Alert severity="info" sx={{ mb: 3 }}>
                <Typography variant="body2">
                  <strong>Data Dictionary Validation:</strong> Upload a CSV or Excel file containing field definitions
                  (field name, data type, required, min/max length, allowed values, etc.) to generate comprehensive
                  validation test scenarios automatically.
                </Typography>
              </Alert>

              <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
                <Button
                  variant="outlined"
                  startIcon={<GetApp />}
                  onClick={handleDownloadTemplate}
                  size="small"
                >
                  Download Template
                </Button>
              </Box>

              <TextField
                label="Form/Page Name (Optional)"
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
                fullWidth
                sx={{ mb: 3 }}
                placeholder="e.g., User Registration Form, Checkout Page"
                helperText="Name of the form or page these fields belong to"
              />

              <Box
                sx={{
                  border: '2px dashed',
                  borderColor: dataDictFile ? 'primary.main' : 'divider',
                  borderRadius: 2,
                  p: 4,
                  textAlign: 'center',
                  cursor: 'pointer',
                  bgcolor: dataDictFile ? 'action.selected' : 'transparent',
                  '&:hover': {
                    borderColor: 'primary.main',
                    bgcolor: 'action.hover',
                  },
                }}
                onClick={() => document.getElementById('data-dict-input').click()}
              >
                <input
                  id="data-dict-input"
                  type="file"
                  accept=".csv,.xlsx,.xls"
                  style={{ display: 'none' }}
                  onChange={handleDataDictFileSelect}
                />
                <TableChart sx={{ fontSize: 60, color: dataDictFile ? 'primary.main' : 'text.secondary', mb: 2 }} />
                <Typography variant="h6" sx={{ mb: 1 }}>
                  {dataDictFile ? dataDictFile.name : 'Click to upload Data Dictionary'}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Supported formats: CSV, Excel (.xlsx, .xls)
                </Typography>
                {dataDictFile && (
                  <Chip
                    label={`${(dataDictFile.size / 1024).toFixed(2)} KB`}
                    color="primary"
                    sx={{ mt: 2 }}
                  />
                )}
              </Box>

              {/* Preview Loading */}
              {previewLoading && (
                <Box sx={{ mt: 3, textAlign: 'center' }}>
                  <CircularProgress size={24} sx={{ mr: 1 }} />
                  <Typography variant="body2" color="text.secondary">
                    Analyzing file...
                  </Typography>
                </Box>
              )}

              {/* Preview Results */}
              {dataDictPreview && !previewLoading && (
                <Box sx={{ mt: 3 }}>
                  {dataDictPreview.success ? (
                    <Alert severity="success">
                      <Typography variant="body2" sx={{ fontWeight: 600, mb: 1 }}>
                        {dataDictPreview.message}
                      </Typography>
                      <Typography variant="body2" sx={{ mb: 1 }}>
                        <strong>Columns detected:</strong>
                      </Typography>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mb: 2 }}>
                        {dataDictPreview.columns.map((col, idx) => (
                          <Chip
                            key={idx}
                            label={col}
                            size="small"
                            variant="outlined"
                            color="primary"
                          />
                        ))}
                      </Box>
                      {dataDictPreview.preview_rows && dataDictPreview.preview_rows.length > 0 && (
                        <Typography variant="caption" color="text.secondary">
                          Sample: {dataDictPreview.preview_rows[0][dataDictPreview.columns[0]] || 'N/A'}
                          {dataDictPreview.rows_count > 1 && ` (and ${dataDictPreview.rows_count - 1} more rows)`}
                        </Typography>
                      )}
                    </Alert>
                  ) : (
                    <Alert severity="error">
                      <Typography variant="body2" sx={{ fontWeight: 600, mb: 1 }}>
                        Failed to parse file:
                      </Typography>
                      <Typography variant="body2">
                        {dataDictPreview.error}
                      </Typography>
                      <Typography variant="caption" sx={{ mt: 1, display: 'block' }}>
                        Tip: Make sure your file has a header row in the first row.
                      </Typography>
                    </Alert>
                  )}
                </Box>
              )}

              {/* Info about how it works */}
              {!dataDictFile && (
                <Alert severity="info" sx={{ mt: 3 }}>
                  <Typography variant="body2" sx={{ fontWeight: 600, mb: 1 }}>
                    How It Works:
                  </Typography>
                  <Typography variant="body2" component="div">
                    1. Upload your data dictionary (any format/template)
                    <br />
                    2. AI will analyze your column headers automatically
                    <br />
                    3. AI identifies field names, data types, validation rules, etc.
                    <br />
                    4. Comprehensive validation test scenarios are generated
                    <br /><br />
                    <strong>Works with any column names</strong> - no specific format required!
                  </Typography>
                </Alert>
              )}

              <Button
                variant="contained"
                size="large"
                fullWidth
                startIcon={generating ? null : <AutoAwesome />}
                onClick={handleGenerateFromDataDict}
                disabled={!dataDictFile || generating || (dataDictPreview && !dataDictPreview.success)}
                sx={{ mt: 3 }}
              >
                {generating ? 'AI is Analyzing & Generating Scenarios...' : `Generate Validation Tests${dataDictPreview?.success ? ` (${dataDictPreview.rows_count} entries)` : ''}`}
              </Button>
            </CardContent>
          </Card>
        </TabPanel>

        {generating && (
          <Box sx={{ mt: 3 }}>
            <CreativeLoader aiService={apiService} aiModel={apiModel} />
          </Box>
        )}

        {/* Create Project Dialog */}
        <Dialog 
          open={showCreateProjectDialog} 
          onClose={() => !creatingProject && setShowCreateProjectDialog(false)}
          maxWidth="sm"
          fullWidth
        >
          <DialogTitle>Create New Project</DialogTitle>
          <DialogContent>
            <TextField
              autoFocus
              margin="dense"
              label="Project Name"
              type="text"
              fullWidth
              variant="outlined"
              value={newProjectName}
              onChange={(e) => setNewProjectName(e.target.value)}
              disabled={creatingProject}
              sx={{ mb: 2, mt: 1 }}
              placeholder="e.g., E-commerce Checkout Tests"
            />
            <TextField
              margin="dense"
              label="Description (Optional)"
              type="text"
              fullWidth
              variant="outlined"
              multiline
              rows={3}
              value={newProjectDescription}
              onChange={(e) => setNewProjectDescription(e.target.value)}
              disabled={creatingProject}
              placeholder="Brief description of what this project will test..."
            />
          </DialogContent>
          <DialogActions>
            <Button 
              onClick={() => {
                setShowCreateProjectDialog(false);
                setNewProjectName('');
                setNewProjectDescription('');
              }}
              disabled={creatingProject}
            >
              Cancel
            </Button>
            <Button 
              onClick={handleCreateProject}
              variant="contained"
              disabled={!newProjectName.trim() || creatingProject}
            >
              {creatingProject ? 'Creating...' : 'Create Project'}
            </Button>
          </DialogActions>
        </Dialog>
      </Box>
    );
  }

  // ============ GENERATED RESULTS VIEW ============
  // Determine counts based on format
  const itemCount = formatType === 'traditional'
    ? selectedTestCases.length
    : selectedScenarios.length;
  const totalItems = formatType === 'traditional'
    ? (generatedTestSuite?.test_cases?.length || 0)
    : (generatedFeature?.scenarios?.length || 0);

  return (
    <Box>
      {/* Header - Clean Layout */}
      <Card sx={{ mb: 3, p: 2.5 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 2 }}>
          {/* Left Side - Title and Info */}
          <Box sx={{ flex: 1, minWidth: 300 }}>
            <Typography variant="h5" sx={{ fontWeight: 700, mb: 1 }}>
              {formatType === 'traditional' ? 'Generated Test Cases' : 'Generated BDD Scenarios'}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              {formatType === 'traditional'
                ? 'Review and select test cases to add to your project'
                : 'Review and select scenarios to add to your project'}
            </Typography>
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
              {apiService && (
                <Chip
                  label={`${apiService}: ${apiModel}`}
                  color="success"
                  size="small"
                  icon={<CheckCircle />}
                />
              )}
              <Chip
                label={formatType === 'traditional' ? 'Traditional' : 'Gherkin'}
                color={formatType === 'traditional' ? 'warning' : 'info'}
                size="small"
                variant="outlined"
                icon={formatType === 'traditional' ? <TableChart /> : <Code />}
              />
              {isEndToEnd && (
                <Chip label="E2E" color="primary" size="small" variant="outlined" />
              )}
            </Box>
          </Box>

          {/* Right Side - Actions */}
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5, alignItems: 'flex-end' }}>
            {/* Primary Action */}
            <Button
              variant="contained"
              startIcon={<Add />}
              onClick={handleAddToProject}
              disabled={itemCount === 0 || !selectedProject || addingToProject}
              sx={{
                minWidth: 180,
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                '&:hover': {
                  background: 'linear-gradient(135deg, #5a6fd6 0%, #6a4190 100%)',
                },
              }}
            >
              {addingToProject ? 'Adding...' : `Add ${itemCount} to Project`}
            </Button>

            {/* Secondary Actions Row */}
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Tooltip title={formatType === 'traditional' ? 'Export as CSV' : 'Export as .feature file'}>
                <Button
                  variant="outlined"
                  size="small"
                  startIcon={<Download />}
                  onClick={() => handleExportFeature(formatType === 'traditional' ? 'csv' : 'feature')}
                  sx={{ borderColor: '#e0e0e0', color: 'text.secondary' }}
                >
                  {formatType === 'traditional' ? '.csv' : '.feature'}
                </Button>
              </Tooltip>
              <Tooltip title="Export as JSON">
                <Button
                  variant="outlined"
                  size="small"
                  startIcon={<GetApp />}
                  onClick={() => handleExportFeature('json')}
                  sx={{ borderColor: '#e0e0e0', color: 'text.secondary' }}
                >
                  .json
                </Button>
              </Tooltip>
              <Tooltip title="Start over with new generation">
                <Button
                  variant="outlined"
                  size="small"
                  startIcon={<Refresh />}
                  onClick={handleReset}
                  sx={{ borderColor: '#e0e0e0', color: 'text.secondary' }}
                >
                  Reset
                </Button>
              </Tooltip>
            </Box>
          </Box>
        </Box>
      </Card>

      {/* Project Selection in Results View */}
      {!selectedProject && (
        <Card sx={{ mb: 3, border: '1px solid', borderColor: 'info.light', bgcolor: 'info.lighter' }}>
          <CardContent sx={{ py: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
              <Typography variant="body2" sx={{ fontWeight: 500, color: 'info.dark' }}>
                Select a project to save:
              </Typography>
              <FormControl size="small" sx={{ minWidth: 250 }}>
                <Select
                  value={selectedProject}
                  displayEmpty
                  onChange={(e) => setSelectedProject(e.target.value)}
                  sx={{ bgcolor: 'white' }}
                >
                  <MenuItem value="" disabled>
                    <em>Choose project...</em>
                  </MenuItem>
                  {projects.map((project) => (
                    <MenuItem key={project.id} value={project.id}>
                      {project.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <Button
                size="small"
                startIcon={<AddCircleOutline />}
                onClick={() => setShowCreateProjectDialog(true)}
              >
                New Project
              </Button>
            </Box>
          </CardContent>
        </Card>
      )}

      {/* Feature/Test Suite Info */}
      {formatType === 'traditional' ? (
        generatedTestSuite && (
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
                <TableChart sx={{ color: 'warning.main' }} />
                <Typography variant="h5" sx={{ fontWeight: 700 }}>
                  {generatedTestSuite.name}
                </Typography>
                {isEndToEnd && (
                  <Chip label="End-to-End" color="primary" size="small" />
                )}
              </Box>
              {generatedTestSuite.description && (
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  {generatedTestSuite.description}
                </Typography>
              )}
            </CardContent>
          </Card>
        )
      ) : (
        generatedFeature && (
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
                <Typography variant="h5" sx={{ fontWeight: 700 }}>
                  Feature: {generatedFeature.name}
                </Typography>
                {isEndToEnd && (
                  <Chip label="End-to-End" color="primary" size="small" />
                )}
              </Box>
              {generatedFeature.description && (
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  {generatedFeature.description}
                </Typography>
              )}

              {/* Background Steps */}
              {generatedFeature.background && generatedFeature.background.length > 0 && (
                <Box sx={{ mt: 2, mb: 2 }}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                    Background:
                  </Typography>
                  <Box
                    sx={{
                      bgcolor: '#1e1e1e',
                      p: 2,
                      borderRadius: 1,
                      fontFamily: 'monospace',
                      fontSize: '0.9rem',
                    }}
                  >
                    {generatedFeature.background.map((step, idx) => (
                      <Box key={idx} sx={{ color: '#ddd', mb: 0.5 }}>
                        <Typography component="span" sx={{ color: '#4CAF50', mr: 2 }}>
                          {step.keyword?.value || step.keyword}
                        </Typography>
                        <Typography component="span">
                          {step.text}
                        </Typography>
                      </Box>
                    ))}
                  </Box>
                </Box>
              )}
            </CardContent>
          </Card>
        )
      )}

      {/* BRD Summary */}
      {brdSummary && (
        <Alert severity="info" icon={<Psychology />} sx={{ mb: 3 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 0.5 }}>
            AI Understanding:
          </Typography>
          <Typography variant="body2">{brdSummary}</Typography>
        </Alert>
      )}

      {/* Stats */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="body2" color="text.secondary">
                {formatType === 'traditional' ? 'Test Cases Generated' : 'Scenarios Generated'}
              </Typography>
              <Typography variant="h4" sx={{ fontWeight: 700 }}>
                {totalItems}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="body2" color="text.secondary">
                Selected
              </Typography>
              <Typography variant="h4" sx={{ fontWeight: 700, color: 'primary.main' }}>
                {itemCount}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="body2" color="text.secondary">
                {formatType === 'traditional' ? 'Format' : 'Total Steps'}
              </Typography>
              <Typography variant="h4" sx={{ fontWeight: 700 }}>
                {formatType === 'traditional'
                  ? 'Table'
                  : (generatedFeature?.scenarios?.reduce((sum, s) => sum + (s.steps?.length || 0), 0) || 0)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Test Cases/Scenarios List */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            {formatType === 'traditional'
              ? `Test Cases (${totalItems})`
              : `Scenarios (${totalItems})`}
          </Typography>
          <Button
            size="small"
            onClick={() => {
              if (formatType === 'traditional') {
                setSelectedTestCases(
                  selectedTestCases.length === totalItems
                    ? []
                    : generatedTestSuite?.test_cases?.map((_, idx) => idx) || []
                );
              } else {
                setSelectedScenarios(
                  selectedScenarios.length === totalItems
                    ? []
                    : generatedFeature?.scenarios?.map((_, idx) => idx) || []
                );
              }
            }}
          >
            {itemCount === totalItems ? 'Deselect All' : 'Select All'}
          </Button>
        </Box>

        {/* TRADITIONAL TABLE FORMAT */}
        {formatType === 'traditional' ? (
          generatedTestSuite?.test_cases && generatedTestSuite.test_cases.length > 0 ? (
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow sx={{ bgcolor: '#f5f5f5' }}>
                    <TableCell padding="checkbox" sx={{ fontWeight: 600 }}></TableCell>
                    <TableCell sx={{ fontWeight: 600, minWidth: 80 }}>TC No</TableCell>
                    <TableCell sx={{ fontWeight: 600, minWidth: 200 }}>Scenario Name</TableCell>
                    <TableCell sx={{ fontWeight: 600, minWidth: 200 }}>Precondition</TableCell>
                    <TableCell sx={{ fontWeight: 600, minWidth: 250 }}>Steps</TableCell>
                    <TableCell sx={{ fontWeight: 600, minWidth: 200 }}>Expected Outcome</TableCell>
                    <TableCell sx={{ fontWeight: 600, minWidth: 150 }}>Post Condition</TableCell>
                    <TableCell sx={{ fontWeight: 600, minWidth: 120 }}>Tags</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {generatedTestSuite.test_cases.map((tc, index) => (
                    <TableRow
                      key={index}
                      sx={{
                        '&:hover': { bgcolor: 'action.hover' },
                        bgcolor: selectedTestCases.includes(index) ? 'action.selected' : 'inherit',
                        cursor: 'pointer',
                      }}
                      onClick={() => handleToggleTestCase(index)}
                    >
                      <TableCell padding="checkbox">
                        <input
                          type="checkbox"
                          checked={selectedTestCases.includes(index)}
                          onChange={() => handleToggleTestCase(index)}
                          style={{ width: 18, height: 18, cursor: 'pointer' }}
                        />
                      </TableCell>
                      <TableCell>
                        <Chip label={`TC${String(tc.test_case_no).padStart(3, '0')}`} size="small" color="primary" />
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>
                          {tc.scenario_name}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" sx={{ whiteSpace: 'pre-line', fontSize: '0.8rem' }}>
                          {tc.precondition}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" sx={{ whiteSpace: 'pre-line', fontSize: '0.8rem' }}>
                          {tc.steps}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" sx={{ whiteSpace: 'pre-line', fontSize: '0.8rem' }}>
                          {tc.expected_outcome}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" sx={{ whiteSpace: 'pre-line', fontSize: '0.8rem' }}>
                          {tc.post_condition}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                          {tc.tags?.map((tag, i) => {
                            const tagColor =
                              tag.includes('@smoke') ? 'success' :
                              tag.includes('@negative') ? 'error' :
                              tag.includes('@positive') ? 'success' :
                              tag.includes('@edge') ? 'warning' :
                              'default';
                            return (
                              <Chip key={i} label={tag} size="small" color={tagColor} variant="outlined" />
                            );
                          })}
                        </Box>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          ) : (
            <Box sx={{ p: 4, textAlign: 'center' }}>
              <Typography variant="body1" color="text.secondary">
                No test cases to display. Please try generating again.
              </Typography>
            </Box>
          )
        ) : (
          /* GHERKIN SCENARIO FORMAT */
          generatedFeature?.scenarios && Array.isArray(generatedFeature.scenarios) && generatedFeature.scenarios.length > 0 ? (
            generatedFeature.scenarios.map((scenario, index) => (
              <Card key={index} sx={{ mb: 2 }}>
                <CardContent>
                  {/* Checkbox and Title */}
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                    <input
                      type="checkbox"
                      checked={selectedScenarios.includes(index)}
                      onChange={() => handleToggleScenario(index)}
                      style={{ width: 18, height: 18, cursor: 'pointer' }}
                    />
                    <Typography variant="h6" sx={{ fontWeight: 600 }}>
                      {scenario.name || `Scenario ${index + 1}`}
                    </Typography>
                  </Box>

                  {/* Tags */}
                  {scenario.tags && scenario.tags.length > 0 && (
                    <Box sx={{ mb: 2, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                      {scenario.tags.map((tag, i) => {
                        const tagColor =
                          tag.includes('@smoke') ? 'success' :
                          tag.includes('@negative') ? 'error' :
                          tag.includes('@positive') ? 'success' :
                          tag.includes('@edge') ? 'warning' :
                          tag.includes('@workflow') ? 'info' :
                          'default';

                        return (
                          <Chip
                            key={i}
                            label={tag}
                            size="small"
                            color={tagColor}
                            variant="outlined"
                          />
                        );
                      })}
                    </Box>
                  )}

                  {/* Description */}
                  {scenario.description && (
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                      {scenario.description}
                    </Typography>
                  )}

                  {/* Steps */}
                  <Box sx={{ bgcolor: '#f5f5f5', p: 2, borderRadius: 1 }}>
                    {scenario.steps && scenario.steps.length > 0 ? (
                      scenario.steps.map((step, i) => {
                        const keyword = step.keyword?.value || step.keyword || 'Step';
                        const stepColor =
                          keyword === 'Given' ? 'green' :
                          keyword === 'When' ? 'blue' :
                          keyword === 'Then' ? 'orange' :
                          keyword === 'And' ? 'purple' :
                          keyword === 'But' ? 'red' :
                          'inherit';

                        return (
                          <Typography
                            key={i}
                            variant="body2"
                            sx={{
                              fontFamily: 'monospace',
                              mb: 0.5,
                              pl: 2
                            }}
                          >
                            <strong style={{ color: stepColor }}>{keyword}</strong> {step.text}
                          </Typography>
                        );
                      })
                    ) : (
                      <Typography variant="body2" color="text.secondary">
                        No steps defined
                      </Typography>
                    )}
                  </Box>

                  {/* Examples Table (if exists) */}
                  {scenario.examples && scenario.examples.length > 0 && (
                    <Box sx={{ mt: 2 }}>
                      <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                        Examples:
                      </Typography>
                      <Box sx={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
                          <thead>
                            <tr style={{ borderBottom: '2px solid #ddd' }}>
                              {Object.keys(scenario.examples[0] || {}).map((header, i) => (
                                <th key={i} style={{ padding: '8px', textAlign: 'left', fontWeight: 600 }}>
                                  {header}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {scenario.examples.map((example, i) => (
                              <tr key={i} style={{ borderBottom: '1px solid #eee' }}>
                                {Object.values(example).map((value, j) => (
                                  <td key={j} style={{ padding: '8px' }}>{value}</td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </Box>
                    </Box>
                  )}
                </CardContent>
              </Card>
            ))
          ) : (
            <Box sx={{ p: 4, textAlign: 'center' }}>
              <Typography variant="body1" color="text.secondary">
                No scenarios to display. Please try generating again.
              </Typography>
            </Box>
          )
        )}
      </Paper>

      {/* AI Suggestions */}
      {suggestions && suggestions.length > 0 && (
        <Alert severity="success" icon={<AutoAwesome />}>
          <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
            AI Suggestions for Additional Testing:
          </Typography>
          <ul style={{ margin: 0, paddingLeft: 20 }}>
            {suggestions.map((suggestion, idx) => (
              <li key={idx}>
                <Typography variant="body2">{suggestion}</Typography>
              </li>
            ))}
          </ul>
        </Alert>
      )}

      {/* Create Project Dialog in Results View */}
      <Dialog 
        open={showCreateProjectDialog} 
        onClose={() => !creatingProject && setShowCreateProjectDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Create New Project</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Project Name"
            type="text"
            fullWidth
            variant="outlined"
            value={newProjectName}
            onChange={(e) => setNewProjectName(e.target.value)}
            disabled={creatingProject}
            sx={{ mb: 2, mt: 1 }}
            placeholder="e.g., E-commerce Checkout Tests"
          />
          <TextField
            margin="dense"
            label="Description (Optional)"
            type="text"
            fullWidth
            variant="outlined"
            multiline
            rows={3}
            value={newProjectDescription}
            onChange={(e) => setNewProjectDescription(e.target.value)}
            disabled={creatingProject}
            placeholder="Brief description of what this project will test..."
          />
        </DialogContent>
        <DialogActions>
          <Button 
            onClick={() => {
              setShowCreateProjectDialog(false);
              setNewProjectName('');
              setNewProjectDescription('');
            }}
            disabled={creatingProject}
          >
            Cancel
          </Button>
          <Button 
            onClick={handleCreateProject}
            variant="contained"
            disabled={!newProjectName.trim() || creatingProject}
          >
            {creatingProject ? 'Creating...' : 'Create Project'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar for notifications - Using hook state */}
      <Snackbar
        open={notification.open}
        autoHideDuration={4000}
        onClose={hideNotification}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={hideNotification}
          severity={notification.severity}
          variant="filled"
          sx={{ width: '100%' }}
        >
          {notification.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}