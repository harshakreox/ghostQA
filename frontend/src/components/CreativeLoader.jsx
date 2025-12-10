import React, { useState, useEffect } from 'react';
import { Box, Typography, LinearProgress, Card, CardContent, Fade, Zoom, Divider } from '@mui/material';
import {
  Psychology,
  Lightbulb,
  Speed,
  CheckCircle,
  AutoAwesome,
  Science,
  Insights,
  EmojiObjects,
  Code,
  BugReport,
  FindInPage,
  Create,
  Biotech,
} from '@mui/icons-material';

const loadingMessages = [
  // Stage 1: Analysis (0-20%)
  { text: "🔍 Reading your requirements...", icon: <FindInPage />, stage: 1 },
  { text: "📖 Understanding the context...", icon: <Psychology />, stage: 1 },
  { text: "🤔 Hmm, interesting requirements...", icon: <Lightbulb />, stage: 1 },
  
  // Stage 2: Thinking (20-50%)
  { text: "💭 Thinking through scenarios...", icon: <Psychology />, stage: 2 },
  { text: "🎯 Identifying test cases...", icon: <Insights />, stage: 2 },
  { text: "🔬 Analyzing edge cases...", icon: <Biotech />, stage: 2 },
  { text: "✨ This is getting interesting...", icon: <AutoAwesome />, stage: 2 },
  
  // Stage 3: Creating (50-80%)
  { text: "✍️ Crafting test scenarios...", icon: <Create />, stage: 3 },
  { text: "🧪 Designing test cases...", icon: <Science />, stage: 3 },
  { text: "💡 Adding clever assertions...", icon: <EmojiObjects />, stage: 3 },
  { text: "📝 Writing test steps...", icon: <Code />, stage: 3 },
  
  // Stage 4: Finalizing (80-100%)
  { text: "🎨 Polishing the tests...", icon: <CheckCircle />, stage: 4 },
  { text: "⚡ Optimizing coverage...", icon: <Speed />, stage: 4 },
  { text: "🔍 Double-checking everything...", icon: <BugReport />, stage: 4 },
  { text: "✅ Almost done...", icon: <CheckCircle />, stage: 4 },
];

const funFacts = [
  "💡 AI can write test cases 50x faster than manual writing!",
  "🚀 Good test coverage can reduce bugs by up to 80%!",
  "🎯 Edge cases are where 70% of bugs hide!",
  "✨ Automated tests run 24/7 without coffee breaks!",
  "🧪 Every test case makes your app more reliable!",
  "💪 Well-tested code is confident code!",
  "🎉 You're about to save hours of manual work!",
  "🤖 AI + QA = Quality Assurance 2.0!",
  "⚡ Fast generation doesn't mean less quality!",
  "🔥 Your app deserves comprehensive testing!",
];

export default function CreativeLoader({ aiService = 'AI', aiModel = 'Model' }) {
  const [currentMessageIndex, setCurrentMessageIndex] = useState(0);
  const [progress, setProgress] = useState(0);
  const [currentFact, setCurrentFact] = useState(0);
  const [stage, setStage] = useState(1);

  // Update stage based on progress
  useEffect(() => {
    if (progress < 20) setStage(1);
    else if (progress < 50) setStage(2);
    else if (progress < 80) setStage(3);
    else setStage(4);
  }, [progress]);

  // Rotate messages based on stage
  useEffect(() => {
    const messageInterval = setInterval(() => {
      setCurrentMessageIndex((prev) => {
        // Get messages for current stage
        const stageMessages = loadingMessages
          .map((msg, idx) => ({ ...msg, originalIndex: idx }))
          .filter(msg => msg.stage === stage);
        
        if (stageMessages.length === 0) return prev;
        
        // Find current position in stage messages
        const currentInStage = stageMessages.findIndex(m => m.originalIndex === prev);
        const nextInStage = (currentInStage + 1) % stageMessages.length;
        
        return stageMessages[nextInStage].originalIndex;
      });
    }, 3500); // Change every 3.5 seconds

    return () => clearInterval(messageInterval);
  }, [stage]);

  // Rotate fun facts
  useEffect(() => {
    const factInterval = setInterval(() => {
      setCurrentFact((prev) => (prev + 1) % funFacts.length);
    }, 6000); // Change every 6 seconds

    return () => clearInterval(factInterval);
  }, []);

  // Simulate realistic progress
  useEffect(() => {
    const progressInterval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 95) return 95; // Stop at 95% until done
        
        // Slow down as we get closer to 100%
        let increment;
        if (prev < 30) increment = Math.random() * 8; // Fast start
        else if (prev < 60) increment = Math.random() * 5; // Medium
        else if (prev < 85) increment = Math.random() * 3; // Slower
        else increment = Math.random() * 1; // Very slow near end
        
        return Math.min(prev + increment, 95);
      });
    }, 800);

    return () => clearInterval(progressInterval);
  }, []);

  const currentMessage = loadingMessages[currentMessageIndex];

  return (
    <Box
      sx={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.7)',
        backdropFilter: 'blur(8px)',
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 2,
      }}
    >
      <Card 
        sx={{ 
          maxWidth: 650, 
          width: '100%',
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          color: 'white',
          boxShadow: '0 20px 60px rgba(102, 126, 234, 0.6)',
        }}
      >
        <CardContent sx={{ p: 4 }}>
          {/* Header */}
          <Box sx={{ textAlign: 'center', mb: 1 }}>
            <Typography variant="h5" sx={{ fontWeight: 700, mb: 0.5 }}>
              GhostQA Test Generator
            </Typography>
            <Typography variant="caption" sx={{ opacity: 0.9 }}>
              Creating magic for you...
            </Typography>
          </Box>

          <Divider sx={{ my: 2, borderColor: 'rgba(255,255,255,0.2)' }} />

        {/* Main Animation Area */}
        <Box sx={{ textAlign: 'center', mb: 0.5, mt:6, minHeight: 140 }}>
          <Zoom in={true} key={currentMessageIndex} timeout={600}>
            <Box>
              {/* Beacon Container with Ripple Effects */}
              <Box
                sx={{
                  position: 'relative',
                  display: 'inline-block',
                  mb: 2,
                }}
              >
                {/* Outer Ripple 1 */}
                <Box
                  sx={{
                    position: 'absolute',
                    top: '50%',
                    left: '50%',
                    transform: 'translate(-50%, -50%)',
                    width: 90,
                    height: 90,
                    borderRadius: '50%',
                    border: '2px solid rgba(255, 255, 255, 0.5)',
                    animation: 'ripple 2s ease-out infinite',
                    '@keyframes ripple': {
                      '0%': { 
                        transform: 'translate(-50%, -50%) scale(1)',
                        opacity: 1,
                      },
                      '100%': { 
                        transform: 'translate(-50%, -50%) scale(2)',
                        opacity: 0,
                      },
                    },
                  }}
                />
                
                {/* Outer Ripple 2 (delayed) */}
                <Box
                  sx={{
                    position: 'absolute',
                    top: '50%',
                    left: '50%',
                    transform: 'translate(-50%, -50%)',
                    width: 90,
                    height: 90,
                    borderRadius: '50%',
                    border: '2px solid rgba(255, 255, 255, 0.5)',
                    animation: 'ripple 2s ease-out infinite 1s',
                  }}
                />
                
                {/* Main Beacon (pulsating) */}
                <Box
                  sx={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    width: 90,
                    height: 90,
                    borderRadius: '50%',
                    background: 'rgba(255, 255, 255, 0.25)',
                    position: 'relative',
                    animation: 'pulse 4s ease-in-out infinite',
                    '@keyframes pulse': {
                      '0%, 100%': { 
                        transform: 'scale(2)',
                        boxShadow: '0 0 0 0 rgba(255, 255, 255, 0.7)',
                      },
                      '50%': { 
                        transform: 'scale(1.1)',
                        boxShadow: '0 0 20px 10px rgba(255, 255, 255, 0)',
                      },
                    },
                  }}
                >
                  <Box
                    sx={{ alignItems: 'center', justifyContent: 'center',
                      animation: 'iconPulse 2s ease-in-out infinite',
                      '@keyframes iconPulse': {
                        '0%, 100%': { 
                          transform: 'scale(0.5)',
                          opacity: 1,
                        },
                        '50%': { 
                          transform: 'scale(1)',
                          opacity: 0.9,
                        },
                      },
                    }}
                  >
                    {React.cloneElement(currentMessage.icon, { sx: { fontSize: 45, color: 'white' } })}
                  </Box>
                </Box>
              </Box>


            </Box>
          </Zoom>
        </Box>

        {/* Progress Bar */}
        <Box sx={{ mb: 3, alignItems: 'center', textAlign: 'center' }}>
              <Typography 
                variant="h5" 
                sx={{ 
                  fontWeight: 600,
                  textShadow: '0 2px 8px rgba(0,0,0,0.3)',
                }}
              >
                {currentMessage.text}
              </Typography>
              
              {/* Stage indicator */}
              <Typography variant="caption" sx={{ opacity: 0.8 }}>
                Stage {stage} of 4
              </Typography>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
            <Typography variant="caption" sx={{ opacity: 0.9 }}>
              Progress
            </Typography>
            <Typography variant="caption" sx={{ opacity: 0.9, fontWeight: 600 }}>
              {Math.round(progress)}%
            </Typography>
          </Box>
          <LinearProgress 
            variant="determinate" 
            value={progress}
            sx={{
              height: 10,
              borderRadius: 5,
              backgroundColor: 'rgba(255, 255, 255, 0.25)',
              '& .MuiLinearProgress-bar': {
                borderRadius: 5,
                background: 'linear-gradient(90deg, #43e97b 0%, #38ef7d 100%)',
                boxShadow: '0 2px 10px rgba(67, 233, 123, 0.5)',
              },
            }}
          />
        </Box>

        {/* AI Service Info */}
        <Box 
          sx={{ 
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            p: 2,
            borderRadius: 2,
            background: 'rgba(255, 255, 255, 0.15)',
            backdropFilter: 'blur(10px)',
            mb: 3,
          }}
        >
          <Box>
            <Typography variant="body2" sx={{ opacity: 0.8, fontSize: '0.75rem' }}>
              POWERED BY
            </Typography>
            <Typography variant="body1" sx={{ fontWeight: 700 }}>
              {aiService}
            </Typography>
          </Box>
          <Box sx={{ textAlign: 'right' }}>
            <Typography variant="body2" sx={{ opacity: 0.8, fontSize: '0.75rem' }}>
              MODEL
            </Typography>
            <Typography variant="body1" sx={{ fontWeight: 600 }}>
              {aiModel}
            </Typography>
          </Box>
        </Box>

        {/* Fun Facts (rotating) */}
        <Fade in={true} key={currentFact} timeout={1000}>
          <Box 
            sx={{ 
              textAlign: 'center',
              p: 2,
              borderRadius: 2,
              background: 'rgba(255, 255, 255, 0.1)',
              border: '1px solid rgba(255, 255, 255, 0.2)',
            }}
          >
            <Typography variant="body2" sx={{ opacity: 0.95, fontStyle: 'italic', lineHeight: 1.6 }}>
              {funFacts[currentFact]}
            </Typography>
          </Box>
        </Fade>

        {/* Animated Dots */}
        <Box sx={{ textAlign: 'center', mt: 3 }}>
          <Box
            sx={{
              display: 'inline-flex',
              gap: 1,
            }}
          >
            {[0, 1, 2].map((i) => (
              <Box
                key={i}
                sx={{
                  width: 8,
                  height: 8,
                  borderRadius: '50%',
                  backgroundColor: 'white',
                  animation: `blink 1.4s infinite ${i * 0.2}s`,
                  '@keyframes blink': {
                    '0%, 20%': { opacity: 1, transform: 'scale(1)' },
                    '50%': { opacity: 0.3, transform: 'scale(0.8)' },
                    '100%': { opacity: 1, transform: 'scale(1)' },
                  },
                }}
              />
            ))}
          </Box>
        </Box>
      </CardContent>
    </Card>
    </Box>
  );
}