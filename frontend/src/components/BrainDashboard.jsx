/**
 * BrainDashboard Component
 *
 * Displays comprehensive brain/learning statistics including:
 * - Health score with visual indicator
 * - Knowledge metrics (elements, patterns, confidence)
 * - Memory stats (page, error, workflow memories)
 * - Decision breakdown (knowledge vs heuristic vs AI)
 * - Token usage and savings
 * - Learning trend chart
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Grid,
  LinearProgress,
  Chip,
  Tooltip,
  IconButton,
  Collapse,
  Divider,
  CircularProgress,
  Alert
} from '@mui/material';
import {
  Psychology as BrainIcon,
  Memory as MemoryIcon,
  Timeline as TrendIcon,
  Lightbulb as LightbulbIcon,
  Speed as SpeedIcon,
  Storage as StorageIcon,
  AutoFixHigh as AIIcon,
  CheckCircle as CheckIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell
} from 'recharts';
import axios from 'axios';

// Health status colors
const STATUS_COLORS = {
  excellent: '#2e7d32',  // Green
  good: '#1976d2',       // Blue
  learning: '#ed6c02',   // Orange
  training: '#9c27b0'    // Purple
};

// Pie chart colors for decisions
const DECISION_COLORS = ['#2e7d32', '#1976d2', '#ed6c02'];

const StatCard = ({ icon: Icon, title, value, subtitle, color = 'primary', progress }) => (
  <Paper
    sx={{
      p: 2,
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      background: `linear-gradient(135deg, ${color}08 0%, ${color}15 100%)`,
      borderLeft: `4px solid ${color}`
    }}
  >
    <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
      <Icon sx={{ color, mr: 1, fontSize: 24 }} />
      <Typography variant="body2" color="text.secondary">
        {title}
      </Typography>
    </Box>
    <Typography variant="h4" sx={{ fontWeight: 'bold', color }}>
      {value}
    </Typography>
    {subtitle && (
      <Typography variant="caption" color="text.secondary">
        {subtitle}
      </Typography>
    )}
    {progress !== undefined && (
      <LinearProgress
        variant="determinate"
        value={progress}
        sx={{
          mt: 1,
          height: 6,
          borderRadius: 3,
          backgroundColor: `${color}20`,
          '& .MuiLinearProgress-bar': {
            backgroundColor: color,
            borderRadius: 3
          }
        }}
      />
    )}
  </Paper>
);

const HealthIndicator = ({ score, status, message }) => {
  const color = STATUS_COLORS[status] || STATUS_COLORS.training;

  return (
    <Paper
      sx={{
        p: 3,
        background: `linear-gradient(135deg, ${color}10 0%, ${color}20 100%)`,
        border: `2px solid ${color}40`,
        borderRadius: 2
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <Box
            sx={{
              position: 'relative',
              display: 'inline-flex',
              mr: 2
            }}
          >
            <CircularProgress
              variant="determinate"
              value={score}
              size={80}
              thickness={4}
              sx={{ color }}
            />
            <Box
              sx={{
                top: 0,
                left: 0,
                bottom: 0,
                right: 0,
                position: 'absolute',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <BrainIcon sx={{ fontSize: 32, color }} />
            </Box>
          </Box>
          <Box>
            <Typography variant="h5" sx={{ fontWeight: 'bold', color }}>
              Brain Health: {score}%
            </Typography>
            <Chip
              label={status.toUpperCase()}
              size="small"
              sx={{
                backgroundColor: color,
                color: 'white',
                fontWeight: 'bold',
                mt: 0.5
              }}
            />
          </Box>
        </Box>
        <Typography
          variant="body2"
          color="text.secondary"
          sx={{ maxWidth: 300, textAlign: 'right' }}
        >
          {message}
        </Typography>
      </Box>
    </Paper>
  );
};

const DecisionPieChart = ({ decisions }) => {
  const data = [
    { name: 'Knowledge', value: decisions.knowledge_based || 0 },
    { name: 'Heuristic', value: decisions.heuristic_based || 0 },
    { name: 'AI Fallback', value: decisions.ai_fallback || 0 }
  ].filter(d => d.value > 0);

  if (data.length === 0) {
    return (
      <Box sx={{ textAlign: 'center', py: 3 }}>
        <Typography variant="body2" color="text.secondary">
          No decisions recorded yet
        </Typography>
      </Box>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={150}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          innerRadius={40}
          outerRadius={60}
          paddingAngle={5}
          dataKey="value"
        >
          {data.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={DECISION_COLORS[index % DECISION_COLORS.length]} />
          ))}
        </Pie>
        <RechartsTooltip />
      </PieChart>
    </ResponsiveContainer>
  );
};

const LearningTrendChart = ({ history }) => {
  if (!history || history.length === 0) {
    return (
      <Box sx={{ textAlign: 'center', py: 3 }}>
        <Typography variant="body2" color="text.secondary">
          Not enough data for trend chart
        </Typography>
      </Box>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <AreaChart data={history}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="label" tick={{ fontSize: 12 }} />
        <YAxis tick={{ fontSize: 12 }} />
        <RechartsTooltip />
        <Area
          type="monotone"
          dataKey="elements_known"
          stackId="1"
          stroke="#2e7d32"
          fill="#2e7d3240"
          name="Elements Known"
        />
        <Area
          type="monotone"
          dataKey="patterns_learned"
          stackId="2"
          stroke="#1976d2"
          fill="#1976d240"
          name="Patterns"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
};

const BrainDashboard = ({ compact = false, showChart = true }) => {
  const [stats, setStats] = useState(null);
  const [history, setHistory] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expanded, setExpanded] = useState(!compact);

  const fetchStats = async () => {
    try {
      setLoading(true);
      setError(null);

      const [statsRes, historyRes] = await Promise.all([
        axios.get('/api/agent/brain/stats'),
        showChart ? axios.get('/api/agent/brain/history') : Promise.resolve({ data: null })
      ]);

      setStats(statsRes.data);
      if (historyRes.data) {
        setHistory(historyRes.data.history);
      }
    } catch (err) {
      console.error('Failed to fetch brain stats:', err);
      setError('Failed to load brain statistics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
    // Refresh every 30 seconds
    const interval = setInterval(fetchStats, 30000);
    return () => clearInterval(interval);
  }, [showChart]);

  if (loading && !stats) {
    return (
      <Paper sx={{ p: 3, textAlign: 'center' }}>
        <CircularProgress size={40} />
        <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
          Loading brain statistics...
        </Typography>
      </Paper>
    );
  }

  if (error && !stats) {
    return (
      <Alert severity="warning" sx={{ mb: 2 }}>
        {error}
      </Alert>
    );
  }

  if (!stats) return null;

  const { health, knowledge, memory, decisions, tokens, recommendation } = stats;

  // Compact mode - just show health and key metrics
  if (compact && !expanded) {
    return (
      <Paper
        sx={{
          p: 2,
          background: `linear-gradient(135deg, ${STATUS_COLORS[health.status]}08 0%, ${STATUS_COLORS[health.status]}15 100%)`,
          cursor: 'pointer'
        }}
        onClick={() => setExpanded(true)}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <BrainIcon sx={{ color: STATUS_COLORS[health.status], fontSize: 28 }} />
            <Box>
              <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
                Brain: {health.score}% {health.status}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {knowledge.total_elements} elements | {knowledge.ai_dependency_percent}% AI
              </Typography>
            </Box>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Chip
              icon={knowledge.ai_dependency_percent < 30 ? <TrendingDownIcon /> : <TrendingUpIcon />}
              label={`${knowledge.ai_dependency_percent}% AI Dependency`}
              size="small"
              color={knowledge.ai_dependency_percent < 30 ? 'success' : 'warning'}
              variant="outlined"
            />
            <IconButton size="small">
              <ExpandMoreIcon />
            </IconButton>
          </Box>
        </Box>
      </Paper>
    );
  }

  return (
    <Paper sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <BrainIcon sx={{ color: STATUS_COLORS[health.status], fontSize: 28 }} />
          <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
            Brain Dashboard
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Tooltip title="Refresh stats">
            <IconButton onClick={fetchStats} disabled={loading}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
          {compact && (
            <IconButton onClick={() => setExpanded(false)}>
              <ExpandLessIcon />
            </IconButton>
          )}
        </Box>
      </Box>

      {/* Health Indicator */}
      <HealthIndicator
        score={health.score}
        status={health.status}
        message={health.message}
      />

      {/* Recommendation */}
      {recommendation && (
        <Alert
          severity="info"
          icon={<LightbulbIcon />}
          sx={{ mt: 2, mb: 3 }}
        >
          {recommendation}
        </Alert>
      )}

      {/* Stats Grid */}
      <Grid container spacing={2} sx={{ mt: 1 }}>
        {/* Knowledge Stats */}
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            icon={StorageIcon}
            title="Elements Known"
            value={knowledge.total_elements}
            subtitle="Stored in knowledge base"
            color="#2e7d32"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            icon={TrendIcon}
            title="Patterns Learned"
            value={knowledge.patterns_learned}
            subtitle="Action patterns"
            color="#1976d2"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            icon={CheckIcon}
            title="Avg Confidence"
            value={`${knowledge.average_confidence}%`}
            subtitle="Selector reliability"
            color="#9c27b0"
            progress={knowledge.average_confidence}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            icon={AIIcon}
            title="AI Dependency"
            value={`${knowledge.ai_dependency_percent}%`}
            subtitle={knowledge.ai_dependency_percent < 30 ? 'Low - Excellent!' : 'Reducing...'}
            color={knowledge.ai_dependency_percent < 30 ? '#2e7d32' : '#ed6c02'}
            progress={100 - knowledge.ai_dependency_percent}
          />
        </Grid>
      </Grid>

      {/* Memory & Decisions */}
      <Grid container spacing={3} sx={{ mt: 2 }}>
        {/* Memory Stats */}
        <Grid item xs={12} md={6}>
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Typography variant="subtitle2" sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
              <MemoryIcon fontSize="small" />
              Memory Systems
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={6}>
                <Typography variant="h5" sx={{ fontWeight: 'bold' }}>
                  {memory.page_memories}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Page Memories
                </Typography>
              </Grid>
              <Grid item xs={6}>
                <Typography variant="h5" sx={{ fontWeight: 'bold' }}>
                  {memory.error_patterns}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Error Patterns
                </Typography>
              </Grid>
              <Grid item xs={6}>
                <Typography variant="h5" sx={{ fontWeight: 'bold' }}>
                  {memory.workflow_patterns}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Workflow Patterns
                </Typography>
              </Grid>
              <Grid item xs={6}>
                <Typography variant="h5" sx={{ fontWeight: 'bold' }}>
                  {memory.action_patterns}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Action Patterns
                </Typography>
              </Grid>
            </Grid>
          </Paper>
        </Grid>

        {/* Decision Breakdown */}
        <Grid item xs={12} md={6}>
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Typography variant="subtitle2" sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
              <SpeedIcon fontSize="small" />
              Decision Sources ({decisions.total_decisions} total)
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <DecisionPieChart decisions={decisions} />
              <Box sx={{ ml: 2 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                  <Box sx={{ width: 12, height: 12, borderRadius: '50%', bgcolor: DECISION_COLORS[0] }} />
                  <Typography variant="body2">Knowledge: {decisions.knowledge_based}</Typography>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                  <Box sx={{ width: 12, height: 12, borderRadius: '50%', bgcolor: DECISION_COLORS[1] }} />
                  <Typography variant="body2">Heuristic: {decisions.heuristic_based}</Typography>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Box sx={{ width: 12, height: 12, borderRadius: '50%', bgcolor: DECISION_COLORS[2] }} />
                  <Typography variant="body2">AI Fallback: {decisions.ai_fallback}</Typography>
                </Box>
              </Box>
            </Box>
          </Paper>
        </Grid>
      </Grid>

      {/* Learning Trend Chart */}
      {showChart && history && history.length > 0 && (
        <Paper variant="outlined" sx={{ p: 2, mt: 3 }}>
          <Typography variant="subtitle2" sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
            <TrendIcon fontSize="small" />
            Learning Progress
          </Typography>
          <LearningTrendChart history={history} />
        </Paper>
      )}

      {/* Token Usage */}
      <Paper variant="outlined" sx={{ p: 2, mt: 3 }}>
        <Typography variant="subtitle2" sx={{ mb: 2 }}>
          Token Usage
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={4}>
            <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
              {tokens.total_used.toLocaleString()}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Tokens Used
            </Typography>
          </Grid>
          <Grid item xs={4}>
            <Typography variant="h6" sx={{ fontWeight: 'bold', color: '#2e7d32' }}>
              {tokens.daily_remaining.toLocaleString()}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Daily Remaining
            </Typography>
          </Grid>
          <Grid item xs={4}>
            <Typography variant="h6" sx={{ fontWeight: 'bold', color: '#1976d2' }}>
              {tokens.saved_by_cache.toLocaleString()}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Saved by Cache
            </Typography>
          </Grid>
        </Grid>
      </Paper>
    </Paper>
  );
};

export default BrainDashboard;
