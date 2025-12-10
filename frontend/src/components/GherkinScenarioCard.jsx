/**
 * GherkinScenarioCard.jsx
 * 
 * Component to display a single Gherkin scenario with proper formatting
 * Replaces the old action-based accordion display
 */

import React from 'react';
import {
  Box,
  Card,
  CardContent,
  Chip,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Checkbox,
  Stack,
} from '@mui/material';
import { ExpandMore, CheckCircle } from '@mui/icons-material';

// Syntax highlighter (install: npm install react-syntax-highlighter)
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

/**
 * Display a single step with proper formatting
 */
function GherkinStep({ step, index }) {
  // Color coding for different step types
  const keywordColors = {
    Given: '#4CAF50',   // Green
    When: '#2196F3',    // Blue
    Then: '#FF9800',    // Orange
    And: '#9E9E9E',     // Gray
    But: '#9E9E9E',     // Gray
  };

  return (
    <Box sx={{ display: 'flex', mb: 1, fontFamily: 'monospace' }}>
      <Typography
        component="span"
        sx={{
          fontWeight: 700,
          color: keywordColors[step.keyword] || '#fff',
          minWidth: '80px',
          mr: 2,
        }}
      >
        {step.keyword}
      </Typography>
      <Typography component="span" sx={{ color: '#ddd' }}>
        {step.text}
      </Typography>
    </Box>
  );
}

/**
 * Display a complete Gherkin scenario
 */
export default function GherkinScenarioCard({ 
  scenario, 
  index,
  selected = false,
  onToggle,
  showCheckbox = true 
}) {
  
  // Format scenario to Gherkin text for syntax highlighting
  const formatScenarioToGherkin = () => {
    let gherkin = '';
    
    // Add tags
    if (scenario.tags && scenario.tags.length > 0) {
      gherkin += scenario.tags.join(' ') + '\n';
    }
    
    // Add scenario name
    gherkin += `Scenario: ${scenario.name}\n\n`;
    
    // Add steps
    scenario.steps.forEach(step => {
      gherkin += `  ${step.keyword} ${step.text}\n`;
    });
    
    return gherkin;
  };

  return (
    <Accordion>
      <AccordionSummary expandIcon={<ExpandMore />}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: '100%' }}>
          {/* Checkbox */}
          {showCheckbox && (
            <Checkbox
              checked={selected}
              onChange={() => onToggle(index)}
              onClick={(e) => e.stopPropagation()}
            />
          )}

          {/* Scenario Info */}
          <Box sx={{ flex: 1 }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 0.5 }}>
              {scenario.name}
            </Typography>
            
            {/* Tags */}
            <Stack direction="row" spacing={0.5} sx={{ flexWrap: 'wrap', gap: 0.5 }}>
              {scenario.tags.map((tag, idx) => (
                <Chip
                  key={idx}
                  label={tag}
                  size="small"
                  variant="outlined"
                  sx={{
                    fontSize: '0.7rem',
                    height: '20px',
                    borderColor: tag.includes('smoke') ? 'success.main' : 
                                 tag.includes('negative') ? 'error.main' : 
                                 tag.includes('ui') ? 'info.main' : 'default',
                  }}
                />
              ))}
              <Chip 
                label={`${scenario.steps.length} steps`} 
                size="small" 
                variant="outlined"
              />
            </Stack>
          </Box>

          {/* Confidence indicator (if applicable) */}
          {scenario.confidence_score >= 0.9 && (
            <Chip 
              icon={<CheckCircle />} 
              label="High Confidence" 
              color="success" 
              size="small" 
            />
          )}
        </Box>
      </AccordionSummary>

      <AccordionDetails>
        {/* Description if exists */}
        {scenario.description && (
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {scenario.description}
          </Typography>
        )}

        {/* Gherkin Display with Syntax Highlighting */}
        <Box sx={{ mb: 2 }}>
          <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
            Scenario Steps:
          </Typography>
          
          {/* Option 1: Custom styled steps (simpler, no external dependency) */}
          <Box 
            sx={{ 
              bgcolor: '#1e1e1e', 
              p: 2, 
              borderRadius: 1,
              fontFamily: 'Consolas, Monaco, monospace',
              fontSize: '0.9rem',
              overflowX: 'auto'
            }}
          >
            {scenario.steps.map((step, idx) => (
              <GherkinStep key={idx} step={step} index={idx} />
            ))}
          </Box>

          {/* Option 2: Using syntax highlighter (prettier, requires npm package) */}
          {/* Uncomment if you want full syntax highlighting:
          <SyntaxHighlighter 
            language="gherkin" 
            style={vscDarkPlus}
            customStyle={{ 
              borderRadius: '8px',
              fontSize: '0.9rem',
              margin: 0,
            }}
          >
            {formatScenarioToGherkin()}
          </SyntaxHighlighter>
          */}
        </Box>

        {/* Notes if exists */}
        {scenario.notes && (
          <Box sx={{ mt: 2 }}>
            <Typography variant="caption" color="text.secondary">
              <strong>Notes:</strong> {scenario.notes}
            </Typography>
          </Box>
        )}
      </AccordionDetails>
    </Accordion>
  );
}


/**
 * Example usage in AITestGenerator.jsx:
 * 
 * // OLD (action-based):
 * {generatedTests.map((testCase, index) => (
 *   <TestCaseAccordion key={index} testCase={testCase} ... />
 * ))}
 * 
 * // NEW (Gherkin-based):
 * {generatedFeature?.scenarios.map((scenario, index) => (
 *   <GherkinScenarioCard
 *     key={index}
 *     scenario={scenario}
 *     index={index}
 *     selected={selectedScenarios.includes(index)}
 *     onToggle={handleToggleScenario}
 *   />
 * ))}
 */


/**
 * FeatureDisplay Component
 * Shows the complete feature with Background section
 */
export function FeatureDisplay({ feature }) {
  return (
    <Card sx={{ mb: 3 }}>
      <CardContent>
        {/* Feature Header */}
        <Typography variant="h5" sx={{ fontWeight: 700, mb: 1 }}>
          Feature: {feature.name}
        </Typography>
        
        {feature.description && (
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {feature.description}
          </Typography>
        )}

        {/* Background Section */}
        {feature.background && feature.background.length > 0 && (
          <Box sx={{ mt: 3, mb: 3 }}>
            <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
              Background:
            </Typography>
            <Box 
              sx={{ 
                bgcolor: '#1e1e1e', 
                p: 2, 
                borderRadius: 1,
                fontFamily: 'Consolas, Monaco, monospace',
                fontSize: '0.9rem',
              }}
            >
              {feature.background.map((step, idx) => (
                <GherkinStep key={idx} step={step} index={idx} />
              ))}
            </Box>
          </Box>
        )}

        {/* Stats */}
        <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
          <Chip 
            label={`${feature.scenarios.length} Scenarios`} 
            color="primary" 
            size="small" 
          />
          <Chip 
            label={`${feature.scenarios.reduce((sum, s) => sum + s.steps.length, 0)} Total Steps`} 
            variant="outlined" 
            size="small" 
          />
          {feature.background && (
            <Chip 
              label={`${feature.background.length} Background Steps`} 
              variant="outlined" 
              size="small" 
            />
          )}
        </Box>
      </CardContent>
    </Card>
  );
}