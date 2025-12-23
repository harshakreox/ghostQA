import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { useGSAP } from '@gsap/react';
import {
  Box,
  Container,
  Typography,
  Button,
  Chip,
  Avatar,
} from '@mui/material';
import {
  ArrowBack,
  BugReport,
  PlayArrow,
} from '@mui/icons-material';

gsap.registerPlugin(ScrollTrigger);

// ============================================
// FLOWCHART 1: FEATURE FILE GENERATOR
// ============================================

function FeatureGeneratorFlowchart() {
  const containerRef = useRef(null);
  const svgRef = useRef(null);

  // Node definitions with gradient IDs
  const nodes = [
    { id: 'upload', label: 'Upload / Input', sublabel: 'User Story', x: 50, y: 120, gradient: 'gradient1' },
    { id: 'engine', label: 'Eox Test Generator', sublabel: 'Engine', x: 220, y: 120, gradient: 'gradient2' },
    { id: 'generate', label: 'Generate', sublabel: 'Feature File', x: 390, y: 120, gradient: 'gradient1' },
    { id: 'download', label: 'Download', sublabel: '', x: 390, y: 40, gradient: 'gradient3' },
    { id: 'traditional', label: 'Generate Traditional', sublabel: 'Test Case in Excel', x: 220, y: 40, gradient: 'gradient1' },
    { id: 'downloadExcel', label: 'Download', sublabel: '', x: 135, y: 5, gradient: 'gradient3', small: true },
    { id: 'review', label: 'Review and', sublabel: 'Update', x: 560, y: 40, gradient: 'gradient3' },
    { id: 'uploadFeature', label: 'Upload', sublabel: 'Feature File', x: 560, y: 120, gradient: 'gradient4' },
  ];

  // Connection paths
  const connections = [
    { from: 'upload', to: 'engine', color: '#64748b' },
    { from: 'engine', to: 'generate', color: '#64748b' },
    { from: 'engine', to: 'traditional', color: '#64748b', type: 'up' },
    { from: 'traditional', to: 'downloadExcel', color: '#64748b', type: 'upLeft' },
    { from: 'generate', to: 'download', color: '#64748b', type: 'up' },
    { from: 'download', to: 'review', color: '#64748b' },
    { from: 'review', to: 'uploadFeature', color: '#64748b', type: 'down' },
    { from: 'generate', to: 'uploadFeature', color: '#64748b' },
  ];

  useGSAP(() => {
    if (!containerRef.current || !svgRef.current) return;

    // Animate nodes
    const nodeEls = svgRef.current.querySelectorAll('.flow-node');
    gsap.fromTo(nodeEls,
      { opacity: 0, scale: 0.8 },
      {
        opacity: 1,
        scale: 1,
        duration: 0.4,
        stagger: 0.08,
        ease: 'back.out(1.5)',
        scrollTrigger: { trigger: containerRef.current, start: 'top 80%' }
      }
    );

    // Animate lines
    const lines = svgRef.current.querySelectorAll('.flow-line');
    lines.forEach((line, i) => {
      const length = line.getTotalLength();
      gsap.set(line, { strokeDasharray: length, strokeDashoffset: length });
      gsap.to(line, {
        strokeDashoffset: 0,
        duration: 0.6,
        delay: 0.3 + i * 0.1,
        ease: 'power2.out',
        scrollTrigger: { trigger: containerRef.current, start: 'top 80%' }
      });
    });

    // Animate flowing beacon dots
    const dots = svgRef.current.querySelectorAll('.flow-dot');
    const rings = svgRef.current.querySelectorAll('.flow-dot-ring');
    lines.forEach((line, i) => {
      const dot = dots[i];
      const ring = rings[i];
      if (!dot || !ring) return;
      const length = line.getTotalLength();

      // Pulsing ring animation
      gsap.fromTo(ring,
        { attr: { r: 6 }, opacity: 0.8 },
        {
          attr: { r: 16 },
          opacity: 0,
          duration: 1,
          repeat: -1,
          ease: 'power1.out',
        }
      );

      gsap.to({ progress: 0 }, {
        progress: 1,
        duration: 2.5,
        delay: 1 + i * 0.3,
        repeat: -1,
        ease: 'none',
        onUpdate: function () {
          const progress = this.targets()[0].progress;
          const point = line.getPointAtLength(progress * length);
          dot.setAttribute('cx', point.x);
          dot.setAttribute('cy', point.y);
          ring.setAttribute('cx', point.x);
          ring.setAttribute('cy', point.y);
          const opacity = progress < 0.1 ? progress * 10 : progress > 0.9 ? (1 - progress) * 10 : 1;
          dot.setAttribute('opacity', opacity);
        },
      });
    });
  }, []);

  const nodeWidth = 120;
  const nodeHeight = 50;
  const smallNodeWidth = 70;
  const smallNodeHeight = 28;

  const getNodeDimensions = (node) => {
    if (node.small) {
      return { width: smallNodeWidth, height: smallNodeHeight };
    }
    return { width: nodeWidth, height: nodeHeight };
  };

  const getNodeCenter = (id) => {
    const node = nodes.find(n => n.id === id);
    const dims = getNodeDimensions(node);
    return { x: node.x + dims.width / 2, y: node.y + dims.height / 2 };
  };

  const getPath = (conn) => {
    const from = nodes.find(n => n.id === conn.from);
    const to = nodes.find(n => n.id === conn.to);
    const fromDims = getNodeDimensions(from);
    const toDims = getNodeDimensions(to);

    // Calculate box edges
    const fromBox = {
      left: from.x,
      right: from.x + fromDims.width,
      top: from.y,
      bottom: from.y + fromDims.height,
      centerX: from.x + fromDims.width / 2,
      centerY: from.y + fromDims.height / 2,
    };
    const toBox = {
      left: to.x,
      right: to.x + toDims.width,
      top: to.y,
      bottom: to.y + toDims.height,
      centerX: to.x + toDims.width / 2,
      centerY: to.y + toDims.height / 2,
    };

    if (conn.type === 'up') {
      // From top center of 'from' box to bottom center of 'to' box
      const midY = (fromBox.top + toBox.bottom) / 2;
      return `M ${fromBox.centerX} ${fromBox.top} L ${fromBox.centerX} ${midY} L ${toBox.centerX} ${midY} L ${toBox.centerX} ${toBox.bottom}`;
    } else if (conn.type === 'upLeft') {
      // From left center of 'from' box, go left then up to bottom center of 'to' box
      return `M ${fromBox.left} ${fromBox.centerY} L ${toBox.centerX} ${fromBox.centerY} L ${toBox.centerX} ${toBox.bottom}`;
    } else if (conn.type === 'down') {
      // From bottom center of 'from' box to top center of 'to' box
      return `M ${fromBox.centerX} ${fromBox.bottom} L ${toBox.centerX} ${toBox.top}`;
    } else {
      // Default: from right center of 'from' box to left center of 'to' box
      return `M ${fromBox.right} ${fromBox.centerY} L ${toBox.left} ${toBox.centerY}`;
    }
  };

  return (
    <Box ref={containerRef} sx={{ p: 4 }}>
      <Box
        sx={{
          background: 'linear-gradient(135deg, #1e1e2e 0%, #2d2d44 50%, #1e1e2e 100%)',
          borderRadius: 4,
          p: 4,
          position: 'relative',
          border: '1px solid rgba(255,255,255,0.1)',
          boxShadow: '0 20px 40px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.1)',
        }}
      >
        <svg
          ref={svgRef}
          viewBox="0 0 750 200"
          style={{ width: '100%', height: 'auto' }}
        >
          <defs>
            {/* Gradients for nodes */}
            <linearGradient id="gradient1" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#667eea" />
              <stop offset="100%" stopColor="#764ba2" />
            </linearGradient>
            <linearGradient id="gradient2" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#f093fb" />
              <stop offset="100%" stopColor="#f5576c" />
            </linearGradient>
            <linearGradient id="gradient3" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#4facfe" />
              <stop offset="100%" stopColor="#00f2fe" />
            </linearGradient>
            <linearGradient id="gradient4" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#43e97b" />
              <stop offset="100%" stopColor="#38f9d7" />
            </linearGradient>
            <linearGradient id="lineGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#667eea" />
              <stop offset="100%" stopColor="#764ba2" />
            </linearGradient>

            {/* Beacon glow filter for dots */}
            <filter id="glow" x="-200%" y="-200%" width="500%" height="500%">
              <feGaussianBlur in="SourceGraphic" stdDeviation="3" result="blur1" />
              <feGaussianBlur in="SourceGraphic" stdDeviation="6" result="blur2" />
              <feGaussianBlur in="SourceGraphic" stdDeviation="10" result="blur3" />
              <feColorMatrix in="blur3" type="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 0 0 0  0 0 0 1 0" result="yellow3" />
              <feMerge>
                <feMergeNode in="blur3" />
                <feMergeNode in="blur2" />
                <feMergeNode in="blur1" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>

            {/* Shadow filter for nodes */}
            <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="2" dy="3" stdDeviation="3" floodColor="rgba(0,0,0,0.3)" />
            </filter>

            {/* Arrow marker - tip ends exactly at target box */}
            <marker id="arrowhead" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
              <polygon points="0 0, 8 3, 0 6" fill="#ffffff" />
            </marker>
          </defs>

          {/* Nodes - rendered first so lines appear on top */}
          {nodes.map((node) => {
            const dims = getNodeDimensions(node);
            return (
              <g key={node.id} className="flow-node" style={{ opacity: 0 }}>
                <rect
                  x={node.x}
                  y={node.y}
                  width={dims.width}
                  height={dims.height}
                  rx={10}
                  fill={`url(#${node.gradient})`}
                  filter="url(#shadow)"
                />
                <text
                  x={node.x + dims.width / 2}
                  y={node.y + (node.small ? dims.height / 2 + 4 : (node.sublabel ? 20 : 30))}
                  textAnchor="middle"
                  fill="white"
                  fontSize={node.small ? "9" : "11"}
                  fontWeight="600"
                  fontFamily="system-ui, sans-serif"
                  style={{ textShadow: '0 1px 2px rgba(0,0,0,0.3)' }}
                >
                  {node.label}
                </text>
                {node.sublabel && !node.small && (
                  <text
                    x={node.x + dims.width / 2}
                    y={node.y + 36}
                    textAnchor="middle"
                    fill="rgba(255,255,255,0.9)"
                    fontSize="9"
                    fontFamily="system-ui, sans-serif"
                  >
                    {node.sublabel}
                  </text>
                )}
              </g>
            );
          })}

          {/* Connection Lines - rendered after nodes so arrowheads appear on top */}
          {connections.map((conn, i) => (
            <g key={`${conn.from}-${conn.to}`}>
              <path
                className="flow-line"
                d={getPath(conn)}
                fill="none"
                stroke="#ffffff"
                strokeWidth="2"
                strokeLinecap="round"
                markerEnd="url(#arrowhead)"
              />
              {/* Beacon outer ring */}
              <circle className="flow-dot-ring" r="10" fill="none" stroke="#ffdd00" strokeWidth="2" opacity="0" />
              {/* Beacon core dot */}
              <circle className="flow-dot" r="4" fill="#ffdd00" filter="url(#glow)" opacity="0" />
            </g>
          ))}
        </svg>

        {/* Output chips */}
        <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2, mt: 3 }}>
          <Chip
            label="Positive Scenarios"
            size="small"
            sx={{
              background: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)',
              color: 'white',
              fontWeight: 600,
              boxShadow: '0 4px 12px rgba(34, 197, 94, 0.4)',
            }}
          />
          <Chip
            label="Negative Scenarios"
            size="small"
            sx={{
              background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
              color: 'white',
              fontWeight: 600,
              boxShadow: '0 4px 12px rgba(239, 68, 68, 0.4)',
            }}
          />
          <Chip
            label="Edge Cases"
            size="small"
            sx={{
              background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
              color: 'white',
              fontWeight: 600,
              boxShadow: '0 4px 12px rgba(245, 158, 11, 0.4)',
            }}
          />
        </Box>
      </Box>
    </Box>
  );
}

// ============================================
// FLOWCHART 2: FEATURE FILE EXECUTOR
// ============================================

function FeatureExecutorFlowchart() {
  const containerRef = useRef(null);
  const svgRef = useRef(null);

  // Node definitions
  const nodes = [
    { id: 'create', label: 'Create &', sublabel: 'Configure Project', x: 30, y: 140, gradient: 'gradient1' },
    { id: 'upload', label: 'Upload Feature', sublabel: 'File to the project', x: 180, y: 140, gradient: 'gradient2' },
    { id: 'edit', label: 'Edit Feature', sublabel: '', x: 180, y: 40, gradient: 'gradient1' },
    { id: 'execute', label: 'Execute Feature', sublabel: '', x: 360, y: 140, gradient: 'gradient2' },
    { id: 'browser', label: 'Browser opens', sublabel: 'by Playwright', x: 520, y: 140, gradient: 'gradient1' },
    { id: 'storeDOM', label: 'Store and map DOM', sublabel: 'with Feature steps', x: 680, y: 140, gradient: 'gradient1' },
    { id: 'executeSteps', label: 'Executing Each', sublabel: 'Steps', x: 680, y: 260, gradient: 'gradient1' },
    { id: 'fallback', label: 'Fallback to 6 retries', sublabel: 'policy for RETRY', x: 420, y: 260, gradient: 'gradientYellow' },
    { id: 'report', label: 'Report with the', sublabel: 'Screen Shot', x: 100, y: 260, gradient: 'gradient4' },
    // Small labels
    { id: 'fail1', label: 'Fail', sublabel: '', x: 600, y: 272, gradient: 'gradientRed', small: true },
    { id: 'fail2', label: 'Fail', sublabel: '', x: 310, y: 248, gradient: 'gradientRed', small: true },
    { id: 'pass', label: 'Pass', sublabel: '', x: 310, y: 295, gradient: 'gradientGreen', small: true },
  ];

  // Connection paths
  const connections = [
    { from: 'create', to: 'upload', color: '#94a3b8' },
    { from: 'upload', to: 'edit', color: '#94a3b8', type: 'up' },
    { from: 'upload', to: 'execute', color: '#94a3b8' },
    { from: 'execute', to: 'browser', color: '#94a3b8' },
    { from: 'browser', to: 'storeDOM', color: '#94a3b8' },
    { from: 'storeDOM', to: 'executeSteps', color: '#94a3b8', type: 'down' },
    { from: 'executeSteps', to: 'fail1', color: '#94a3b8', type: 'left' },
    { from: 'executeSteps', to: 'pass', color: '#94a3b8', type: 'downLeftUpLeft' },
    { from: 'fail1', to: 'fallback', color: '#94a3b8', type: 'left' },
    { from: 'fallback', to: 'fail2', color: '#94a3b8', type: 'left' },
    { from: 'fail2', to: 'report', color: '#94a3b8', type: 'left' },
    { from: 'pass', to: 'report', color: '#94a3b8', type: 'left' },
  ];

  useGSAP(() => {
    if (!containerRef.current || !svgRef.current) return;

    const nodeEls = svgRef.current.querySelectorAll('.flow-node');
    gsap.fromTo(nodeEls,
      { opacity: 0, scale: 0.8 },
      {
        opacity: 1,
        scale: 1,
        duration: 0.4,
        stagger: 0.08,
        ease: 'back.out(1.5)',
        scrollTrigger: { trigger: containerRef.current, start: 'top 80%' }
      }
    );

    const lines = svgRef.current.querySelectorAll('.flow-line');
    lines.forEach((line, i) => {
      const length = line.getTotalLength();
      gsap.set(line, { strokeDasharray: length, strokeDashoffset: length });
      gsap.to(line, {
        strokeDashoffset: 0,
        duration: 0.6,
        delay: 0.3 + i * 0.1,
        ease: 'power2.out',
        scrollTrigger: { trigger: containerRef.current, start: 'top 80%' }
      });
    });

    const dots = svgRef.current.querySelectorAll('.flow-dot');
    const rings = svgRef.current.querySelectorAll('.flow-dot-ring');
    lines.forEach((line, i) => {
      const dot = dots[i];
      const ring = rings[i];
      if (!dot || !ring) return;
      const length = line.getTotalLength();

      gsap.fromTo(ring,
        { attr: { r: 6 }, opacity: 0.8 },
        {
          attr: { r: 16 },
          opacity: 0,
          duration: 1,
          repeat: -1,
          ease: 'power1.out',
        }
      );

      gsap.to({ progress: 0 }, {
        progress: 1,
        duration: 2.5,
        delay: 1 + i * 0.3,
        repeat: -1,
        ease: 'none',
        onUpdate: function () {
          const progress = this.targets()[0].progress;
          const point = line.getPointAtLength(progress * length);
          dot.setAttribute('cx', point.x);
          dot.setAttribute('cy', point.y);
          ring.setAttribute('cx', point.x);
          ring.setAttribute('cy', point.y);
          const opacity = progress < 0.1 ? progress * 10 : progress > 0.9 ? (1 - progress) * 10 : 1;
          dot.setAttribute('opacity', opacity);
        },
      });
    });
  }, []);

  const nodeWidth = 120;
  const nodeHeight = 50;
  const smallNodeWidth = 50;
  const smallNodeHeight = 24;

  const getNodeDimensions = (node) => {
    if (node.small) {
      return { width: smallNodeWidth, height: smallNodeHeight };
    }
    return { width: nodeWidth, height: nodeHeight };
  };

  const getPath = (conn) => {
    const from = nodes.find(n => n.id === conn.from);
    const to = nodes.find(n => n.id === conn.to);
    const fromDims = getNodeDimensions(from);
    const toDims = getNodeDimensions(to);

    // Calculate box edges
    const fromBox = {
      left: from.x,
      right: from.x + fromDims.width,
      top: from.y,
      bottom: from.y + fromDims.height,
      centerX: from.x + fromDims.width / 2,
      centerY: from.y + fromDims.height / 2,
    };
    const toBox = {
      left: to.x,
      right: to.x + toDims.width,
      top: to.y,
      bottom: to.y + toDims.height,
      centerX: to.x + toDims.width / 2,
      centerY: to.y + toDims.height / 2,
    };

    if (conn.type === 'up') {
      // From top center of 'from' box to bottom center of 'to' box
      if (Math.abs(fromBox.centerX - toBox.centerX) < 5) {
        return `M ${fromBox.centerX} ${fromBox.top} L ${fromBox.centerX} ${toBox.bottom}`;
      }
      const midY = (fromBox.top + toBox.bottom) / 2;
      return `M ${fromBox.centerX} ${fromBox.top} L ${fromBox.centerX} ${midY} L ${toBox.centerX} ${midY} L ${toBox.centerX} ${toBox.bottom}`;
    } else if (conn.type === 'down') {
      // From bottom center of 'from' box to top center of 'to' box
      if (Math.abs(fromBox.centerX - toBox.centerX) < 5) {
        return `M ${fromBox.centerX} ${fromBox.bottom} L ${fromBox.centerX} ${toBox.top}`;
      }
      const midY = (fromBox.bottom + toBox.top) / 2;
      return `M ${fromBox.centerX} ${fromBox.bottom} L ${fromBox.centerX} ${midY} L ${toBox.centerX} ${midY} L ${toBox.centerX} ${toBox.top}`;
    } else if (conn.type === 'left') {
      // From left center of 'from' box to right center of 'to' box
      if (Math.abs(fromBox.centerY - toBox.centerY) < 5) {
        return `M ${fromBox.left} ${fromBox.centerY} L ${toBox.right} ${toBox.centerY}`;
      }
      const midX = (fromBox.left + toBox.right) / 2;
      return `M ${fromBox.left} ${fromBox.centerY} L ${midX} ${fromBox.centerY} L ${midX} ${toBox.centerY} L ${toBox.right} ${toBox.centerY}`;
    } else if (conn.type === 'leftDown') {
      // From bottom center of 'from' box, down, then left to right center of 'to' box
      return `M ${fromBox.centerX} ${fromBox.bottom} L ${fromBox.centerX} ${toBox.centerY} L ${toBox.right} ${toBox.centerY}`;
    } else if (conn.type === 'downLeftUpLeft') {
      // From bottom of 'from', down, left, up, then left to 'to' box
      const dropY = fromBox.bottom + 30; // Go down 30px
      const riseY = toBox.centerY; // Rise to target's center Y
      const turnX = toBox.right + 40; // Turn point before going to target
      return `M ${fromBox.centerX} ${fromBox.bottom} L ${fromBox.centerX} ${dropY} L ${turnX} ${dropY} L ${turnX} ${riseY} L ${toBox.right} ${riseY}`;
    } else {
      // Default: from right center of 'from' box to left center of 'to' box
      if (Math.abs(fromBox.centerY - toBox.centerY) < 5) {
        return `M ${fromBox.right} ${fromBox.centerY} L ${toBox.left} ${toBox.centerY}`;
      }
      const midX = (fromBox.right + toBox.left) / 2;
      return `M ${fromBox.right} ${fromBox.centerY} L ${midX} ${fromBox.centerY} L ${midX} ${toBox.centerY} L ${toBox.left} ${toBox.centerY}`;
    }
  };

  return (
    <Box ref={containerRef} sx={{ p: 4 }}>
      <Box
        sx={{
          background: 'linear-gradient(135deg, #1e1e2e 0%, #2d2d44 50%, #1e1e2e 100%)',
          borderRadius: 4,
          p: 4,
          position: 'relative',
          border: '1px solid rgba(255,255,255,0.1)',
          boxShadow: '0 20px 40px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.1)',
        }}
      >
        <svg
          ref={svgRef}
          viewBox="0 0 850 360"
          style={{ width: '100%', height: 'auto' }}
        >
          <defs>
            <linearGradient id="exec-gradient1" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#667eea" />
              <stop offset="100%" stopColor="#764ba2" />
            </linearGradient>
            <linearGradient id="exec-gradient2" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#4facfe" />
              <stop offset="100%" stopColor="#00f2fe" />
            </linearGradient>
            <linearGradient id="exec-gradient4" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#43e97b" />
              <stop offset="100%" stopColor="#38f9d7" />
            </linearGradient>
            <linearGradient id="exec-gradientYellow" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#f7971e" />
              <stop offset="100%" stopColor="#ffd200" />
            </linearGradient>
            <linearGradient id="exec-gradientRed" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#ef4444" />
              <stop offset="100%" stopColor="#dc2626" />
            </linearGradient>
            <linearGradient id="exec-gradientGreen" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#22c55e" />
              <stop offset="100%" stopColor="#16a34a" />
            </linearGradient>

            <filter id="exec-glow" x="-200%" y="-200%" width="500%" height="500%">
              <feGaussianBlur in="SourceGraphic" stdDeviation="3" result="blur1" />
              <feGaussianBlur in="SourceGraphic" stdDeviation="6" result="blur2" />
              <feGaussianBlur in="SourceGraphic" stdDeviation="10" result="blur3" />
              <feMerge>
                <feMergeNode in="blur3" />
                <feMergeNode in="blur2" />
                <feMergeNode in="blur1" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>

            <filter id="exec-shadow" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="2" dy="3" stdDeviation="3" floodColor="rgba(0,0,0,0.3)" />
            </filter>

            {/* Arrow marker - tip ends exactly at target box */}
            <marker id="exec-arrowhead" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
              <polygon points="0 0, 8 3, 0 6" fill="#ffffff" />
            </marker>
          </defs>

          {/* Nodes - rendered first so lines appear on top */}
          {nodes.map((node) => {
            const dims = getNodeDimensions(node);
            const gradientId = node.gradient.replace('gradient', 'exec-gradient');
            return (
              <g key={node.id} className="flow-node" style={{ opacity: 0 }}>
                <rect
                  x={node.x}
                  y={node.y}
                  width={dims.width}
                  height={dims.height}
                  rx={10}
                  fill={`url(#${gradientId})`}
                  filter="url(#exec-shadow)"
                />
                <text
                  x={node.x + dims.width / 2}
                  y={node.y + (node.small ? dims.height / 2 + 4 : (node.sublabel ? 20 : 30))}
                  textAnchor="middle"
                  fill="white"
                  fontSize={node.small ? "9" : "10"}
                  fontWeight="600"
                  fontFamily="system-ui, sans-serif"
                >
                  {node.label}
                </text>
                {node.sublabel && !node.small && (
                  <text
                    x={node.x + dims.width / 2}
                    y={node.y + 36}
                    textAnchor="middle"
                    fill="rgba(255,255,255,0.9)"
                    fontSize="9"
                    fontFamily="system-ui, sans-serif"
                  >
                    {node.sublabel}
                  </text>
                )}
              </g>
            );
          })}

          {/* Connection Lines - rendered after nodes so arrowheads appear on top */}
          {connections.map((conn, i) => (
            <g key={`${conn.from}-${conn.to}`}>
              <path
                className="flow-line"
                d={getPath(conn)}
                fill="none"
                stroke="#ffffff"
                strokeWidth="2"
                strokeLinecap="round"
                markerEnd="url(#exec-arrowhead)"
              />
              {/* Beacon outer ring */}
              <circle className="flow-dot-ring" r="10" fill="none" stroke="#ffdd00" strokeWidth="2" opacity="0" />
              {/* Beacon core dot */}
              <circle className="flow-dot" r="4" fill="#ffdd00" filter="url(#exec-glow)" opacity="0" />
            </g>
          ))}
        </svg>
      </Box>
    </Box>
  );
}

// ============================================
// FLOWCHART 3: END-TO-END FLOW WITH SELF-HEALING
// ============================================

function EndToEndFlowchart() {
  const containerRef = useRef(null);
  const svgRef = useRef(null);

  // Define sections for background boxes
  // GREEN SECTION centered at top, BLUE SECTION below it on the left
  const sections = {
    selfHealing: { x: 180, y: 35, width: 790, height: 330 },
    featureGenerator: { x: 30, y: 420, width: 420, height: 260 },
  };

  // Node dimensions
  const nodeWidth = 105;
  const nodeHeight = 50;
  const smallNodeWidth = 70;
  const smallNodeHeight = 32;

  // LAYOUT: Green section centered at top, Blue section below on left, Main flow at bottom
  const nodes = [
    // === GREEN SECTION: Self-Healing Engine (CENTERED AT TOP) ===
    // Top Row - y=60, 6 items with 135px spacing (30px gaps)
    { id: 'knowledgeBase', label: 'Knowledge', sublabel: 'Base', x: 200, y: 60, gradient: 'gradient1' },
    { id: 'frameworkRules', label: 'Framework', sublabel: 'Rules', x: 335, y: 60, gradient: 'gradient1' },
    { id: 'imageAnalyser', label: 'Image', sublabel: 'Analyser', x: 470, y: 60, gradient: 'gradient1' },
    { id: 'heuristic', label: 'Heuristic', sublabel: '', x: 605, y: 60, gradient: 'gradient1' },
    { id: 'aiDecision', label: 'AI', sublabel: 'Decision', x: 740, y: 60, gradient: 'gradient1' },
    { id: 'fallback', label: 'Fallback', sublabel: '', x: 875, y: 69, gradient: 'gradientRed', small: true },

    // Middle Row - y=175, 4 items with 150px spacing (45px gaps)
    { id: 'tierPipeline', label: '6 Tier', sublabel: 'Pipeline', x: 260, y: 175, gradient: 'gradient1' },
    { id: 'playwrightAction', label: 'Playwright', sublabel: 'Action', x: 410, y: 175, gradient: 'gradient1' },
    { id: 'selfHealing', label: 'Self', sublabel: 'Healing', x: 560, y: 175, gradient: 'gradient1' },
    { id: 'knowledgeUpdate', label: 'Knowledge', sublabel: 'Update', x: 710, y: 175, gradient: 'gradientGreen' },

    // Bottom Row - y=290, 4 items with 150px spacing (45px gaps)
    { id: 'selectorService', label: 'Selector', sublabel: 'Service', x: 260, y: 290, gradient: 'gradient1' },
    { id: 'actionExecuter', label: 'Action', sublabel: 'Executer', x: 410, y: 290, gradient: 'gradient1' },
    { id: 'recoveryHandler', label: 'Recovery', sublabel: 'Handler', x: 560, y: 290, gradient: 'gradient1' },
    { id: 'learningEngine', label: 'Learning', sublabel: 'Engine', x: 710, y: 290, gradient: 'gradientGreen' },

    // === BLUE SECTION: Feature Generator (BELOW GREEN, LEFT SIDE) ===
    // Row 1 - Top (download excel) - y=450
    { id: 'downloadExcel', label: 'Download', sublabel: '', x: 100, y: 450, gradient: 'gradient1', small: true },
    // Row 2 - Middle (traditional + download) - y=530
    { id: 'generateTraditional', label: 'Traditional', sublabel: 'Test Case', x: 120, y: 530, gradient: 'gradient1' },
    { id: 'downloadFeature', label: 'Download', sublabel: '', x: 310, y: 535, gradient: 'gradient1', small: true },
    // Row 3 - Bottom (upload, eox, generate) - y=610
    { id: 'uploadStory', label: 'Upload', sublabel: 'User Story', x: 50, y: 610, gradient: 'gradient1' },
    { id: 'eoxEngine', label: 'Eox Test', sublabel: 'Generator', x: 170, y: 610, gradient: 'gradient1' },
    { id: 'generateFeature', label: 'Generate', sublabel: 'Feature File', x: 290, y: 610, gradient: 'gradient1' },

    // Outside blue box - Review & Update
    { id: 'reviewUpdate', label: 'Review', sublabel: 'Update', x: 430, y: 530, gradient: 'gradientGray' },

    // === MAIN FLOW: Bottom Row (120px spacing) ===
    { id: 'uploadFeature', label: 'Upload', sublabel: 'Feature File', x: 430, y: 610, gradient: 'gradient1' },
    { id: 'eoxExecutor', label: 'Eox Auto', sublabel: 'Executor', x: 550, y: 610, gradient: 'gradient1' },
    { id: 'executingSteps', label: 'Executing', sublabel: 'Each Steps', x: 670, y: 610, gradient: 'gradient1' },
    { id: 'testComplete', label: 'Test Exec', sublabel: 'Completed', x: 790, y: 610, gradient: 'gradient1' },
    { id: 'generateReport', label: 'Generate', sublabel: 'Final Report', x: 910, y: 610, gradient: 'gradient1' },
    { id: 'reportFrontend', label: 'Report in', sublabel: 'Frontend', x: 1030, y: 610, gradient: 'gradient1' },
  ];

  // Connection definitions with types
  const connections = [
    // Left section connections
    { from: 'uploadStory', to: 'eoxEngine', color: 'gray' },
    { from: 'eoxEngine', to: 'generateFeature', color: 'gray' },
    { from: 'eoxEngine', to: 'generateTraditional', type: 'up', color: 'gray' },
    { from: 'generateTraditional', to: 'downloadExcel', type: 'up', color: 'gray' },
    { from: 'generateFeature', to: 'downloadFeature', type: 'up', color: 'gray' },
    { from: 'downloadFeature', to: 'reviewUpdate', color: 'gray' },
    { from: 'reviewUpdate', to: 'uploadFeature', type: 'curveDown', color: 'gray' },
    { from: 'generateFeature', to: 'uploadFeature', color: 'gray' },

    // Main flow connections
    { from: 'uploadFeature', to: 'eoxExecutor', color: 'gray' },
    { from: 'eoxExecutor', to: 'executingSteps', color: 'gray' },
    { from: 'executingSteps', to: 'testComplete', color: 'gray' },
    { from: 'testComplete', to: 'generateReport', color: 'gray' },
    { from: 'generateReport', to: 'reportFrontend', color: 'gray' },

    // Connection from executingSteps up to self-healing section
    { from: 'executingSteps', to: 'selectorService', type: 'upToGreen', color: 'gray' },

    // Green section top row (left to right) - RED arrows
    { from: 'knowledgeBase', to: 'frameworkRules', color: 'red' },
    { from: 'frameworkRules', to: 'imageAnalyser', color: 'red' },
    { from: 'imageAnalyser', to: 'heuristic', color: 'red' },
    { from: 'heuristic', to: 'aiDecision', color: 'red' },
    { from: 'aiDecision', to: 'fallback', color: 'red' },

    // Green section middle row (right to left) - GREEN arrows
    { from: 'knowledgeUpdate', to: 'selfHealing', type: 'left', color: 'green' },
    { from: 'selfHealing', to: 'playwrightAction', type: 'left', color: 'green' },
    { from: 'playwrightAction', to: 'tierPipeline', type: 'left', color: 'green' },

    // Green section bottom row (right to left) - GREEN arrows
    { from: 'learningEngine', to: 'recoveryHandler', type: 'left', color: 'green' },
    { from: 'recoveryHandler', to: 'actionExecuter', type: 'left', color: 'green' },
    { from: 'actionExecuter', to: 'selectorService', type: 'left', color: 'green' },

    // Vertical connections inside green section - GREEN
    { from: 'imageAnalyser', to: 'selfHealing', type: 'down', color: 'green' },
    { from: 'knowledgeUpdate', to: 'learningEngine', type: 'down', color: 'green' },
    { from: 'tierPipeline', to: 'selectorService', type: 'down', color: 'green' },
    { from: 'tierPipeline', to: 'knowledgeBase', type: 'upLeft', color: 'green' },

    // Fallback blue curved line going around
    { from: 'fallback', to: 'selectorService', type: 'fallbackCurve', color: 'blue' },

    // From selectorService back down to testComplete
    { from: 'selectorService', to: 'testComplete', type: 'downToMain', color: 'gray' },
  ];

  useGSAP(() => {
    if (!containerRef.current || !svgRef.current) return;

    const nodeEls = svgRef.current.querySelectorAll('.flow-node');
    gsap.fromTo(nodeEls,
      { opacity: 0, scale: 0.8 },
      {
        opacity: 1,
        scale: 1,
        duration: 0.4,
        stagger: 0.05,
        ease: 'back.out(1.5)',
        scrollTrigger: { trigger: containerRef.current, start: 'top 80%' }
      }
    );

    const lines = svgRef.current.querySelectorAll('.flow-line');
    lines.forEach((line, i) => {
      const length = line.getTotalLength();
      gsap.set(line, { strokeDasharray: length, strokeDashoffset: length });
      gsap.to(line, {
        strokeDashoffset: 0,
        duration: 0.5,
        delay: 0.2 + i * 0.05,
        ease: 'power2.out',
        scrollTrigger: { trigger: containerRef.current, start: 'top 80%' }
      });
    });

    const dots = svgRef.current.querySelectorAll('.flow-dot');
    const rings = svgRef.current.querySelectorAll('.flow-dot-ring');
    lines.forEach((line, i) => {
      const dot = dots[i];
      const ring = rings[i];
      if (!dot || !ring) return;
      const length = line.getTotalLength();

      gsap.fromTo(ring,
        { attr: { r: 6 }, opacity: 0.8 },
        { attr: { r: 16 }, opacity: 0, duration: 1, repeat: -1, ease: 'power1.out' }
      );

      gsap.to({ progress: 0 }, {
        progress: 1,
        duration: 2.5,
        delay: 1 + i * 0.2,
        repeat: -1,
        ease: 'none',
        onUpdate: function () {
          const progress = this.targets()[0].progress;
          const point = line.getPointAtLength(progress * length);
          dot.setAttribute('cx', point.x);
          dot.setAttribute('cy', point.y);
          ring.setAttribute('cx', point.x);
          ring.setAttribute('cy', point.y);
          const opacity = progress < 0.1 ? progress * 10 : progress > 0.9 ? (1 - progress) * 10 : 1;
          dot.setAttribute('opacity', opacity);
        },
      });
    });
  }, []);

  const getNodeDimensions = (node) => {
    if (node.small) {
      return { width: smallNodeWidth, height: smallNodeHeight };
    }
    return { width: nodeWidth, height: nodeHeight };
  };

  const getPath = (conn) => {
    const from = nodes.find(n => n.id === conn.from);
    const to = nodes.find(n => n.id === conn.to);
    const fromDims = getNodeDimensions(from);
    const toDims = getNodeDimensions(to);

    const fromBox = {
      left: from.x,
      right: from.x + fromDims.width,
      top: from.y,
      bottom: from.y + fromDims.height,
      centerX: from.x + fromDims.width / 2,
      centerY: from.y + fromDims.height / 2,
    };
    const toBox = {
      left: to.x,
      right: to.x + toDims.width,
      top: to.y,
      bottom: to.y + toDims.height,
      centerX: to.x + toDims.width / 2,
      centerY: to.y + toDims.height / 2,
    };

    switch (conn.type) {
      case 'up': {
        // From top of source to bottom of target (orthogonal L-path)
        const startX = fromBox.centerX;
        const startY = fromBox.top;
        const endX = toBox.centerX;
        const endY = toBox.bottom;
        // Always use L-shaped path: go up first, then horizontal
        const midY = endY + 20; // Stop 20px below target
        return `M ${startX} ${startY} L ${startX} ${midY} L ${endX} ${midY} L ${endX} ${endY}`;
      }
      case 'down': {
        // From bottom of source to top of target
        const startX = fromBox.centerX;
        const startY = fromBox.bottom;
        const endX = toBox.centerX;
        const endY = toBox.top;
        if (Math.abs(startX - endX) < 15) {
          return `M ${startX} ${startY} L ${endX} ${endY}`;
        }
        const midY = startY + 25;
        return `M ${startX} ${startY} L ${startX} ${midY} L ${endX} ${midY} L ${endX} ${endY}`;
      }
      case 'left': {
        // From left of source to right of target (going leftward)
        if (Math.abs(fromBox.centerY - toBox.centerY) < 10) {
          return `M ${fromBox.left} ${fromBox.centerY} L ${toBox.right} ${toBox.centerY}`;
        }
        const midX = (fromBox.left + toBox.right) / 2;
        return `M ${fromBox.left} ${fromBox.centerY} L ${midX} ${fromBox.centerY} L ${midX} ${toBox.centerY} L ${toBox.right} ${toBox.centerY}`;
      }
      case 'curveDown': {
        // From bottom of reviewUpdate, go down to top of uploadFeature
        // Since they share similar x, just a slight curve
        const midY = fromBox.bottom + 20;
        return `M ${fromBox.centerX} ${fromBox.bottom} L ${fromBox.centerX} ${midY} L ${toBox.centerX} ${midY} L ${toBox.centerX} ${toBox.top}`;
      }
      case 'upToGreen': {
        // From top of executingSteps up to bottom of selectorService
        const turnY = toBox.bottom + 80;
        const entryX = toBox.centerX + 30; // Offset right to separate from other line
        return `M ${fromBox.centerX} ${fromBox.top} L ${fromBox.centerX} ${turnY} L ${entryX} ${turnY} L ${entryX} ${toBox.bottom}`;
      }
      case 'downToMain': {
        // From left of selectorService down to top of testComplete
        const turnX = fromBox.left - 50;
        const turnY = toBox.top - 40;
        return `M ${fromBox.left} ${fromBox.centerY} L ${turnX} ${fromBox.centerY} L ${turnX} ${turnY} L ${toBox.centerX} ${turnY} L ${toBox.centerX} ${toBox.top}`;
      }
      case 'upLeft': {
        // From left of tierPipeline, go left then up to bottom of knowledgeBase
        const turnX = fromBox.left - 50;
        const turnY = toBox.bottom + 40;
        return `M ${fromBox.left} ${fromBox.centerY} L ${turnX} ${fromBox.centerY} L ${turnX} ${turnY} L ${toBox.centerX} ${turnY} L ${toBox.centerX} ${toBox.bottom}`;
      }
      case 'fallbackCurve': {
        // Blue line from fallback, going down around the green section to selectorService
        const rightEdge = sections.selfHealing.x + sections.selfHealing.width + 30;
        const bottomEdge = sections.selfHealing.y + sections.selfHealing.height + 30;
        const turnX = toBox.left - 40;
        const entryY = toBox.centerY + 15; // Offset down from center to separate from downToMain line
        return `M ${fromBox.centerX} ${fromBox.bottom} L ${fromBox.centerX} ${fromBox.bottom + 30} L ${rightEdge} ${fromBox.bottom + 30} L ${rightEdge} ${bottomEdge} L ${turnX} ${bottomEdge} L ${turnX} ${entryY} L ${toBox.left} ${entryY}`;
      }
      default: {
        // Default: right to left horizontal
        if (Math.abs(fromBox.centerY - toBox.centerY) < 10) {
          return `M ${fromBox.right} ${fromBox.centerY} L ${toBox.left} ${toBox.centerY}`;
        }
        const midX = (fromBox.right + toBox.left) / 2;
        return `M ${fromBox.right} ${fromBox.centerY} L ${midX} ${fromBox.centerY} L ${midX} ${toBox.centerY} L ${toBox.left} ${toBox.centerY}`;
      }
    }
  };

  const getStrokeColor = (color) => {
    switch(color) {
      case 'red': return '#ef4444';
      case 'green': return '#22c55e';
      case 'blue': return '#3b82f6';
      default: return '#ffffff';
    }
  };

  return (
    <Box ref={containerRef} sx={{ p: 4 }}>
      <Box
        sx={{
          background: 'linear-gradient(135deg, #1e1e2e 0%, #2d2d44 50%, #1e1e2e 100%)',
          borderRadius: 4,
          p: 4,
          position: 'relative',
          border: '1px solid rgba(255,255,255,0.1)',
          boxShadow: '0 20px 40px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.1)',
          overflowX: 'auto',
        }}
      >
        <svg
          ref={svgRef}
          viewBox="0 0 1180 700"
          style={{ width: '100%', minWidth: '1050px', height: 'auto' }}
        >
          <defs>
            <linearGradient id="e2e-gradient1" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#0ea5e9" />
              <stop offset="100%" stopColor="#0284c7" />
            </linearGradient>
            <linearGradient id="e2e-gradientGray" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#64748b" />
              <stop offset="100%" stopColor="#475569" />
            </linearGradient>
            <linearGradient id="e2e-gradientGreen" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#22c55e" />
              <stop offset="100%" stopColor="#16a34a" />
            </linearGradient>
            <linearGradient id="e2e-gradientRed" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#ef4444" />
              <stop offset="100%" stopColor="#dc2626" />
            </linearGradient>

            <filter id="e2e-glow" x="-200%" y="-200%" width="500%" height="500%">
              <feGaussianBlur in="SourceGraphic" stdDeviation="3" result="blur1" />
              <feGaussianBlur in="SourceGraphic" stdDeviation="6" result="blur2" />
              <feMerge>
                <feMergeNode in="blur2" />
                <feMergeNode in="blur1" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>

            <filter id="e2e-shadow" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="2" dy="3" stdDeviation="3" floodColor="rgba(0,0,0,0.3)" />
            </filter>

            <marker id="e2e-arrow-white" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
              <polygon points="0 0, 10 3.5, 0 7" fill="#ffffff" />
            </marker>
            <marker id="e2e-arrow-red" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
              <polygon points="0 0, 10 3.5, 0 7" fill="#ef4444" />
            </marker>
            <marker id="e2e-arrow-green" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
              <polygon points="0 0, 10 3.5, 0 7" fill="#22c55e" />
            </marker>
            <marker id="e2e-arrow-blue" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
              <polygon points="0 0, 10 3.5, 0 7" fill="#3b82f6" />
            </marker>
          </defs>

          {/* Background Sections */}
          {/* Left section - Feature Generator */}
          <rect
            x={sections.featureGenerator.x}
            y={sections.featureGenerator.y}
            width={sections.featureGenerator.width}
            height={sections.featureGenerator.height}
            rx="15"
            fill="rgba(59, 130, 246, 0.1)"
            stroke="rgba(59, 130, 246, 0.3)"
            strokeWidth="1"
          />

          {/* Green section - Self-Healing Engine */}
          <rect
            x={sections.selfHealing.x}
            y={sections.selfHealing.y}
            width={sections.selfHealing.width}
            height={sections.selfHealing.height}
            rx="15"
            fill="rgba(34, 197, 94, 0.1)"
            stroke="rgba(34, 197, 94, 0.3)"
            strokeWidth="1"
          />

          {/* Nodes - rendered first */}
          {nodes.map((node) => {
            const dims = getNodeDimensions(node);
            const gradientId = `e2e-${node.gradient}`;
            return (
              <g key={node.id} className="flow-node" style={{ opacity: 0 }}>
                <rect
                  x={node.x}
                  y={node.y}
                  width={dims.width}
                  height={dims.height}
                  rx={8}
                  fill={`url(#${gradientId})`}
                  filter="url(#e2e-shadow)"
                />
                <text
                  x={node.x + dims.width / 2}
                  y={node.y + (node.small ? dims.height / 2 + 5 : (node.sublabel ? 21 : dims.height / 2 + 5))}
                  textAnchor="middle"
                  fill="white"
                  fontSize={node.small ? "10" : "12"}
                  fontWeight="600"
                  fontFamily="system-ui, sans-serif"
                >
                  {node.label}
                </text>
                {node.sublabel && !node.small && (
                  <text
                    x={node.x + dims.width / 2}
                    y={node.y + 37}
                    textAnchor="middle"
                    fill="rgba(255,255,255,0.9)"
                    fontSize="10"
                    fontFamily="system-ui, sans-serif"
                  >
                    {node.sublabel}
                  </text>
                )}
              </g>
            );
          })}

          {/* Connection Lines - rendered after nodes */}
          {connections.map((conn, i) => {
            const arrowId = conn.color === 'red' ? 'e2e-arrow-red' :
                           conn.color === 'green' ? 'e2e-arrow-green' :
                           conn.color === 'blue' ? 'e2e-arrow-blue' : 'e2e-arrow-white';
            return (
              <g key={`${conn.from}-${conn.to}-${i}`}>
                <path
                  className="flow-line"
                  d={getPath(conn)}
                  fill="none"
                  stroke={getStrokeColor(conn.color)}
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  markerEnd={`url(#${arrowId})`}
                />
                <circle className="flow-dot-ring" r="10" fill="none" stroke="#ffdd00" strokeWidth="2" opacity="0" />
                <circle className="flow-dot" r="4" fill="#ffdd00" filter="url(#e2e-glow)" opacity="0" />
              </g>
            );
          })}
        </svg>
      </Box>
    </Box>
  );
}

// ============================================
// MAIN PAGE COMPONENT
// ============================================

export default function HowItWorks() {
  const navigate = useNavigate();
  const [isScrolled, setIsScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => setIsScrolled(window.scrollY > 50);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <Box sx={{ minHeight: '100vh', background: '#0a0a1a' }}>
      {/* Navigation */}
      <Box
        sx={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          zIndex: 999,
          py: 2,
          px: { xs: 2, md: 4 },
          background: isScrolled ? 'rgba(10,10,26,0.95)' : 'transparent',
          backdropFilter: isScrolled ? 'blur(20px)' : 'none',
          borderBottom: isScrolled ? '1px solid rgba(255,255,255,0.05)' : 'none',
          transition: 'all 0.3s ease',
        }}
      >
        <Container maxWidth="lg">
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Box onClick={() => navigate('/')} sx={{ display: 'flex', alignItems: 'center', gap: 1.5, cursor: 'pointer' }}>
              <Avatar sx={{ width: 40, height: 40, background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
                <BugReport sx={{ fontSize: 22 }} />
              </Avatar>
              <Typography variant="h6" sx={{ fontWeight: 700, color: 'white' }}>GhostQA</Typography>
            </Box>
            <Box sx={{ display: 'flex', gap: 2 }}>
              <Button startIcon={<ArrowBack />} onClick={() => navigate('/')} sx={{ color: 'rgba(255,255,255,0.8)' }}>Back</Button>
              <Button variant="contained" onClick={() => navigate('/login')} sx={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', px: 3 }}>
                Get Started
              </Button>
            </Box>
          </Box>
        </Container>
      </Box>

      {/* Hero */}
      <Box sx={{ pt: 14, pb: 4 }}>
        <Container maxWidth="lg">
          <Box sx={{ textAlign: 'center', mb: 4 }}>
            <Chip label="Architecture Overview" sx={{ mb: 2, background: 'rgba(102,126,234,0.15)', color: '#a5b4fc' }} />
            <Typography variant="h3" sx={{ fontWeight: 800, color: 'white', mb: 1 }}>
              How GhostQA Works
            </Typography>
            <Typography sx={{ color: 'rgba(255,255,255,0.6)' }}>
              From user story to automated tests
            </Typography>
          </Box>
        </Container>
      </Box>

      {/* Flowchart 1: Feature File Generator */}
      <Box sx={{ py: 4 }}>
        <Container maxWidth="lg">
          <Box sx={{ mb: 3 }}>
            <Chip label="Step 1" sx={{ mb: 1, background: 'rgba(59,130,246,0.2)', color: '#60a5fa' }} />
            <Typography variant="h5" sx={{ color: 'white', fontWeight: 700 }}>
              Feature File Generator
            </Typography>
          </Box>
          <FeatureGeneratorFlowchart />
        </Container>
      </Box>

      {/* Flowchart 2: Feature File Executor */}
      <Box sx={{ py: 4 }}>
        <Container maxWidth="lg">
          <Box sx={{ mb: 3 }}>
            <Chip label="Step 2" sx={{ mb: 1, background: 'rgba(79,172,254,0.2)', color: '#4facfe' }} />
            <Typography variant="h5" sx={{ color: 'white', fontWeight: 700 }}>
              Feature File Executor
            </Typography>
          </Box>
          <FeatureExecutorFlowchart />
        </Container>
      </Box>

      {/* Flowchart 3: End-to-End Flow */}
      <Box sx={{ py: 4 }}>
        <Container maxWidth="xl">
          <Box sx={{ mb: 3 }}>
            <Chip label="Complete Flow" sx={{ mb: 1, background: 'rgba(34,197,94,0.2)', color: '#22c55e' }} />
            <Typography variant="h5" sx={{ color: 'white', fontWeight: 700 }}>
              End-to-End Architecture with Self-Healing Engine
            </Typography>
            <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.6)', mt: 1 }}>
              Complete flow from user story to automated test execution with intelligent self-healing capabilities
            </Typography>
          </Box>
          <EndToEndFlowchart />
        </Container>
      </Box>

      {/* CTA */}
      <Box sx={{ py: 8 }}>
        <Container maxWidth="md">
          <Box sx={{ textAlign: 'center', p: 4, borderRadius: 3, background: 'rgba(102,126,234,0.1)', border: '1px solid rgba(102,126,234,0.2)' }}>
            <Typography variant="h5" sx={{ color: 'white', fontWeight: 700, mb: 2 }}>Ready to Get Started?</Typography>
            <Button variant="contained" startIcon={<PlayArrow />} onClick={() => navigate('/login')} sx={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
              Start Free
            </Button>
          </Box>
        </Container>
      </Box>
    </Box>
  );
}
