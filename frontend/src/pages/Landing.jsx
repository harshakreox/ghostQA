import { useState, useEffect, useRef, useLayoutEffect, useMemo, Suspense } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, useScroll, useInView } from 'framer-motion';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { MotionPathPlugin } from 'gsap/MotionPathPlugin';
import { useGSAP } from '@gsap/react';
import {
  Box,
  Container,
  Typography,
  Button,
  Grid,
  Card,
  CardContent,
  Avatar,
  Chip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  TextField,
  IconButton,
} from '@mui/material';
import {
  BugReport,
  Psychology,
  TableChart,
  CloudUpload,
  AutoAwesome,
  CheckCircle,
  ArrowForward,
  Speed,
  Code,
  RocketLaunch,
  ExpandMore,
  Description,
  DataObject,
  PlayArrow,
  Assessment,
  Group,
  Timer,
  Storage,
  CloudDownload,
  Bolt,
  SmartToy,
  AccountTree,
  SettingsSuggest,
  Layers,
  School,
  EmojiEvents,
  KeyboardDoubleArrowRight,
  Star,
  Send,
  PlayCircle,
  GitHub,
  Check,
  Close,
} from '@mui/icons-material';

// Register GSAP plugins
gsap.registerPlugin(ScrollTrigger, MotionPathPlugin);

// ============================================
// GSAP CUSTOM HOOKS & COMPONENTS
// ============================================

// Magnetic Button Effect
function MagneticButton({ children, strength = 0.3 }) {
  const buttonRef = useRef(null);

  useEffect(() => {
    const button = buttonRef.current;
    if (!button) return;

    const handleMouseMove = (e) => {
      const rect = button.getBoundingClientRect();
      const x = e.clientX - rect.left - rect.width / 2;
      const y = e.clientY - rect.top - rect.height / 2;

      gsap.to(button, {
        x: x * strength,
        y: y * strength,
        duration: 0.3,
        ease: 'power2.out',
      });
    };

    const handleMouseLeave = () => {
      gsap.to(button, {
        x: 0,
        y: 0,
        duration: 0.5,
        ease: 'elastic.out(1, 0.3)',
      });
    };

    button.addEventListener('mousemove', handleMouseMove);
    button.addEventListener('mouseleave', handleMouseLeave);

    return () => {
      button.removeEventListener('mousemove', handleMouseMove);
      button.removeEventListener('mouseleave', handleMouseLeave);
    };
  }, [strength]);

  return (
    <div ref={buttonRef} style={{ display: 'inline-block' }}>
      {children}
    </div>
  );
}

// Split Text Reveal Animation
function SplitTextReveal({ children, delay = 0 }) {
  const textRef = useRef(null);

  useGSAP(() => {
    if (!textRef.current) return;

    const text = textRef.current;
    const chars = text.innerText.split('');
    text.innerHTML = chars
      .map((char) => `<span class="split-char" style="display: inline-block; opacity: 0;">${char === ' ' ? '&nbsp;' : char}</span>`)
      .join('');

    gsap.to(text.querySelectorAll('.split-char'), {
      opacity: 1,
      y: 0,
      duration: 0.05,
      stagger: 0.03,
      delay: delay,
      ease: 'power2.out',
      scrollTrigger: {
        trigger: text,
        start: 'top 85%',
      },
    });
  }, [delay]);

  return <span ref={textRef}>{children}</span>;
}

// GSAP Counter Animation
function GSAPCounter({ end, suffix = '', duration = 2 }) {
  const counterRef = useRef(null);
  const [hasAnimated, setHasAnimated] = useState(false);

  useGSAP(() => {
    if (!counterRef.current || hasAnimated) return;

    const counter = { value: 0 };

    ScrollTrigger.create({
      trigger: counterRef.current,
      start: 'top 80%',
      onEnter: () => {
        if (!hasAnimated) {
          setHasAnimated(true);
          gsap.to(counter, {
            value: end,
            duration: duration,
            ease: 'power2.out',
            onUpdate: () => {
              if (counterRef.current) {
                counterRef.current.textContent = Math.floor(counter.value) + suffix;
              }
            },
          });
        }
      },
    });
  }, [end, suffix, duration, hasAnimated]);

  return <span ref={counterRef}>0{suffix}</span>;
}

// Parallax Container
function ParallaxSection({ children, speed = 0.5 }) {
  const sectionRef = useRef(null);

  useGSAP(() => {
    if (!sectionRef.current) return;

    gsap.to(sectionRef.current, {
      yPercent: speed * 100,
      ease: 'none',
      scrollTrigger: {
        trigger: sectionRef.current,
        start: 'top bottom',
        end: 'bottom top',
        scrub: true,
      },
    });
  }, [speed]);

  return <div ref={sectionRef}>{children}</div>;
}

// Stagger Reveal for Cards
function StaggerReveal({ children, staggerDelay = 0.1 }) {
  const containerRef = useRef(null);

  useGSAP(() => {
    if (!containerRef.current) return;

    const items = containerRef.current.children;

    gsap.fromTo(
      items,
      { opacity: 0, y: 60, scale: 0.95 },
      {
        opacity: 1,
        y: 0,
        scale: 1,
        duration: 0.8,
        stagger: staggerDelay,
        ease: 'power3.out',
        scrollTrigger: {
          trigger: containerRef.current,
          start: 'top 75%',
        },
      }
    );
  }, [staggerDelay]);

  return <div ref={containerRef}>{children}</div>;
}

// GSAP Typing Effect for Code
function GSAPTypingCode({ code, onComplete }) {
  const codeRef = useRef(null);

  useGSAP(() => {
    if (!codeRef.current) return;

    const chars = code.split('');
    codeRef.current.textContent = '';

    const tl = gsap.timeline({
      scrollTrigger: {
        trigger: codeRef.current,
        start: 'top 70%',
      },
    });

    chars.forEach((char, i) => {
      tl.to(codeRef.current, {
        duration: 0.02,
        onComplete: () => {
          codeRef.current.textContent += char;
        },
      });
    });

    if (onComplete) {
      tl.call(onComplete);
    }
  }, [code, onComplete]);

  return <span ref={codeRef}></span>;
}

// Smooth Typing Effect (like before, but with GSAP timing)
function SmoothTyping({ texts, typingSpeed = 100, deletingSpeed = 50, pauseDuration = 2500 }) {
  const [displayText, setDisplayText] = useState('');
  const [textIndex, setTextIndex] = useState(0);
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    const currentText = texts[textIndex];

    const timeout = setTimeout(() => {
      if (!isDeleting) {
        if (displayText.length < currentText.length) {
          setDisplayText(currentText.slice(0, displayText.length + 1));
        } else {
          setTimeout(() => setIsDeleting(true), pauseDuration);
        }
      } else {
        if (displayText.length > 0) {
          setDisplayText(displayText.slice(0, -1));
        } else {
          setIsDeleting(false);
          setTextIndex((prev) => (prev + 1) % texts.length);
        }
      }
    }, isDeleting ? deletingSpeed : typingSpeed);

    return () => clearTimeout(timeout);
  }, [displayText, isDeleting, textIndex, texts, typingSpeed, deletingSpeed, pauseDuration]);

  return (
    <span>
      {displayText}
      <span style={{
        animation: 'blink 1s step-end infinite',
        marginLeft: 2
      }}>|</span>
      <style>{`
        @keyframes blink {
          0%, 100% { opacity: 1; }
          50% { opacity: 0; }
        }
      `}</style>
    </span>
  );
}

// Floating Particles with GSAP
function GSAPParticles() {
  const containerRef = useRef(null);

  useGSAP(() => {
    if (!containerRef.current) return;

    const particles = containerRef.current.querySelectorAll('.gsap-particle');

    particles.forEach((particle, i) => {
      const randomX = gsap.utils.random(-50, 50);
      const randomY = gsap.utils.random(-50, 50);
      const randomDuration = gsap.utils.random(3, 6);
      const randomDelay = gsap.utils.random(0, 2);

      gsap.to(particle, {
        x: randomX,
        y: randomY,
        duration: randomDuration,
        delay: randomDelay,
        repeat: -1,
        yoyo: true,
        ease: 'sine.inOut',
      });

      // Pulsing glow effect
      gsap.to(particle, {
        opacity: gsap.utils.random(0.3, 0.8),
        scale: gsap.utils.random(0.8, 1.5),
        duration: gsap.utils.random(2, 4),
        repeat: -1,
        yoyo: true,
        ease: 'sine.inOut',
      });
    });
  }, []);

  const particles = Array.from({ length: 40 }, (_, i) => ({
    id: i,
    x: Math.random() * 100,
    y: Math.random() * 100,
    size: Math.random() * 4 + 2,
  }));

  return (
    <Box ref={containerRef} sx={{ position: 'absolute', inset: 0, overflow: 'hidden', pointerEvents: 'none' }}>
      {particles.map((p) => (
        <Box
          key={p.id}
          className="gsap-particle"
          sx={{
            position: 'absolute',
            left: `${p.x}%`,
            top: `${p.y}%`,
            width: p.size,
            height: p.size,
            borderRadius: '50%',
            background: 'radial-gradient(circle, rgba(102,126,234,0.6) 0%, transparent 70%)',
            filter: 'blur(1px)',
          }}
        />
      ))}
    </Box>
  );
}

// Scroll reveal section (enhanced with GSAP)
function RevealSection({ children, direction = 'up', delay = 0 }) {
  const ref = useRef(null);

  useGSAP(() => {
    if (!ref.current) return;

    const xFrom = direction === 'left' ? -80 : direction === 'right' ? 80 : 0;
    const yFrom = direction === 'up' ? 80 : direction === 'down' ? -80 : 0;

    gsap.fromTo(
      ref.current,
      { opacity: 0, x: xFrom, y: yFrom },
      {
        opacity: 1,
        x: 0,
        y: 0,
        duration: 1,
        delay: delay,
        ease: 'power3.out',
        scrollTrigger: {
          trigger: ref.current,
          start: 'top 80%',
        },
      }
    );
  }, [direction, delay]);

  return <div ref={ref}>{children}</div>;
}

// Gradient border card
function GradientCard({ children, gradient = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }) {
  const cardRef = useRef(null);

  useGSAP(() => {
    if (!cardRef.current) return;

    const card = cardRef.current;

    card.addEventListener('mouseenter', () => {
      gsap.to(card, {
        scale: 1.02,
        duration: 0.3,
        ease: 'power2.out',
      });
    });

    card.addEventListener('mouseleave', () => {
      gsap.to(card, {
        scale: 1,
        duration: 0.3,
        ease: 'power2.out',
      });
    });
  }, []);

  return (
    <Box
      ref={cardRef}
      sx={{
        position: 'relative',
        borderRadius: 3,
        p: '2px',
        background: gradient,
        '&::before': {
          content: '""',
          position: 'absolute',
          inset: 0,
          borderRadius: 'inherit',
          padding: '2px',
          background: gradient,
          mask: 'linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0)',
          maskComposite: 'xor',
          WebkitMaskComposite: 'xor',
        },
      }}
    >
      <Box sx={{ background: '#0a0a1a', borderRadius: 'inherit', height: '100%' }}>
        {children}
      </Box>
    </Box>
  );
}

// Code terminal with GSAP
function CodeTerminal() {
  const terminalRef = useRef(null);
  const scanLineRef = useRef(null);

  const inputCode = `Feature: User Login
  As a registered user
  I want to log into my account
  So that I can access my dashboard`;

  const outputCode = `@login @smoke @regression
Feature: User Login Authentication

  Background:
    Given the application is running
    And the database is connected

  @positive @P1
  Scenario: Successful login
    Given I navigate to "/login"
    When I enter "user@email.com" in email
    And I enter "Pass123!" in password
    And I click "Sign In" button
    Then I see "/dashboard"
    And I see "Welcome, User"`;

  useGSAP(() => {
    if (!scanLineRef.current) return;

    gsap.to(scanLineRef.current, {
      top: '90%',
      duration: 2,
      repeat: -1,
      yoyo: true,
      ease: 'sine.inOut',
    });
  }, []);

  return (
    <Box ref={terminalRef} sx={{ position: 'relative' }}>
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <RevealSection direction="left">
            <Box
              sx={{
                background: 'linear-gradient(145deg, #1a1a2e 0%, #16162a 100%)',
                borderRadius: 3,
                overflow: 'hidden',
                border: '1px solid rgba(102,126,234,0.2)',
                boxShadow: '0 20px 60px rgba(0,0,0,0.4)',
              }}
            >
              <Box sx={{ px: 2, py: 1.5, background: 'rgba(0,0,0,0.3)', display: 'flex', alignItems: 'center', gap: 1 }}>
                <Box sx={{ width: 12, height: 12, borderRadius: '50%', background: '#ff5f57' }} />
                <Box sx={{ width: 12, height: 12, borderRadius: '50%', background: '#febc2e' }} />
                <Box sx={{ width: 12, height: 12, borderRadius: '50%', background: '#28c840' }} />
                <Typography variant="caption" sx={{ ml: 2, color: 'rgba(255,255,255,0.5)' }}>requirements.txt</Typography>
              </Box>
              <Box sx={{ p: 2.5, fontFamily: 'monospace', fontSize: '0.8rem', color: '#a5b4fc', minHeight: 250, whiteSpace: 'pre-wrap' }}>
                {inputCode}
              </Box>
            </Box>
          </RevealSection>
        </Grid>

        <Grid item xs={12} md={6}>
          <RevealSection direction="right" delay={0.2}>
            <Box
              sx={{
                background: 'linear-gradient(145deg, #1a1a2e 0%, #16162a 100%)',
                borderRadius: 3,
                overflow: 'hidden',
                border: '1px solid rgba(74,222,128,0.2)',
                position: 'relative',
                boxShadow: '0 20px 60px rgba(0,0,0,0.4)',
              }}
            >
              <Box sx={{ px: 2, py: 1.5, background: 'rgba(0,0,0,0.3)', display: 'flex', alignItems: 'center', gap: 1 }}>
                <Box sx={{ width: 12, height: 12, borderRadius: '50%', background: '#ff5f57' }} />
                <Box sx={{ width: 12, height: 12, borderRadius: '50%', background: '#febc2e' }} />
                <Box sx={{ width: 12, height: 12, borderRadius: '50%', background: '#28c840' }} />
                <Typography variant="caption" sx={{ ml: 2, color: 'rgba(255,255,255,0.5)' }}>login.feature</Typography>
                <Chip label="AI Generated" size="small" sx={{ ml: 'auto', background: 'rgba(74,222,128,0.2)', color: '#4ade80', height: 20, fontSize: '0.65rem' }} />
              </Box>
              <Box sx={{ p: 2.5, fontFamily: 'monospace', fontSize: '0.72rem', color: '#4ade80', minHeight: 250, whiteSpace: 'pre-wrap', overflow: 'hidden' }}>
                <GSAPTypingCode code={outputCode} />
              </Box>

              {/* Scanning line */}
              <Box
                ref={scanLineRef}
                sx={{
                  position: 'absolute',
                  left: 0,
                  right: 0,
                  top: '10%',
                  height: 2,
                  background: 'linear-gradient(90deg, transparent, #4ade80, transparent)',
                  opacity: 0.6,
                }}
              />
            </Box>
          </RevealSection>
        </Grid>
      </Grid>

      {/* Center AI badge */}
      <Box
        sx={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          display: { xs: 'none', md: 'flex' },
          zIndex: 10,
        }}
      >
        <MagneticButton strength={0.4}>
          <Avatar
            sx={{
              width: 60,
              height: 60,
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              boxShadow: '0 8px 32px rgba(102,126,234,0.5)',
              cursor: 'pointer',
            }}
          >
            <AutoAwesome />
          </Avatar>
        </MagneticButton>
      </Box>
    </Box>
  );
}

// Integration logos marquee (keeping for future use)
function IntegrationMarquee() {
  const integrations = [
    { name: 'Selenium', color: '#43B02A' },
    { name: 'Playwright', color: '#2EAD33' },
    { name: 'Cypress', color: '#17202C' },
    { name: 'Jest', color: '#C21325' },
    { name: 'Jenkins', color: '#D24939' },
    { name: 'GitHub Actions', color: '#2088FF' },
    { name: 'GitLab CI', color: '#FC6D26' },
    { name: 'Docker', color: '#2496ED' },
    { name: 'Kubernetes', color: '#326CE5' },
    { name: 'AWS', color: '#FF9900' },
    { name: 'Azure', color: '#0078D4' },
    { name: 'Jira', color: '#0052CC' },
  ];

  return (
    <Box sx={{ overflow: 'hidden', py: 4 }}>
      <motion.div
        style={{ display: 'flex', gap: 32, width: 'max-content' }}
        animate={{ x: ['0%', '-50%'] }}
        transition={{ duration: 30, repeat: Infinity, ease: 'linear' }}
      >
        {[...integrations, ...integrations].map((int, i) => (
          <Box
            key={i}
            sx={{
              px: 4,
              py: 2,
              background: 'rgba(255,255,255,0.03)',
              borderRadius: 2,
              border: '1px solid rgba(255,255,255,0.06)',
              display: 'flex',
              alignItems: 'center',
              gap: 1.5,
              minWidth: 160,
            }}
          >
            <Box sx={{ width: 32, height: 32, borderRadius: 1, background: `${int.color}20`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Code sx={{ fontSize: 18, color: int.color }} />
            </Box>
            <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.7)', fontWeight: 500 }}>{int.name}</Typography>
          </Box>
        ))}
      </motion.div>
    </Box>
  );
}

// Testimonial card (keeping for future use)
function TestimonialCard({ testimonial, index }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5, delay: index * 0.15 }}
    >
      <Card
        sx={{
          height: '100%',
          background: 'linear-gradient(145deg, rgba(30,30,60,0.6) 0%, rgba(20,20,40,0.8) 100%)',
          border: '1px solid rgba(102,126,234,0.1)',
          borderRadius: 4,
        }}
      >
        <CardContent sx={{ p: 4 }}>
          <Box sx={{ display: 'flex', gap: 0.5, mb: 3 }}>
            {[...Array(5)].map((_, i) => (
              <Star key={i} sx={{ fontSize: 18, color: '#fbbf24' }} />
            ))}
          </Box>
          <Typography variant="body1" sx={{ color: 'rgba(255,255,255,0.8)', mb: 3, lineHeight: 1.8, fontStyle: 'italic' }}>
            "{testimonial.quote}"
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Avatar sx={{ width: 48, height: 48, background: testimonial.gradient, fontWeight: 600 }}>
              {testimonial.name.charAt(0)}
            </Avatar>
            <Box>
              <Typography variant="subtitle2" sx={{ color: 'white', fontWeight: 600 }}>{testimonial.name}</Typography>
              <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)' }}>{testimonial.role} at {testimonial.company}</Typography>
            </Box>
          </Box>
        </CardContent>
      </Card>
    </motion.div>
  );
}

// Pricing card (keeping for future use)
function PricingCard({ plan, featured = false }) {
  return (
    <Card
      sx={{
        height: '100%',
        background: featured
          ? 'linear-gradient(145deg, rgba(102,126,234,0.15) 0%, rgba(118,75,162,0.15) 100%)'
          : 'linear-gradient(145deg, rgba(30,30,60,0.6) 0%, rgba(20,20,40,0.8) 100%)',
        border: featured ? '2px solid rgba(102,126,234,0.4)' : '1px solid rgba(255,255,255,0.08)',
        borderRadius: 4,
        position: 'relative',
        overflow: 'visible',
      }}
    >
      {featured && (
        <Chip
          label="Most Popular"
          sx={{
            position: 'absolute',
            top: -14,
            left: '50%',
            transform: 'translateX(-50%)',
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            color: 'white',
            fontWeight: 600,
          }}
        />
      )}
      <CardContent sx={{ p: 4 }}>
        <Typography variant="h5" sx={{ color: 'white', fontWeight: 700, mb: 1 }}>{plan.name}</Typography>
        <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.5)', mb: 3 }}>{plan.description}</Typography>
        <Box sx={{ display: 'flex', alignItems: 'baseline', mb: 3 }}>
          <Typography variant="h3" sx={{ color: 'white', fontWeight: 800 }}>{plan.price}</Typography>
          {plan.period && <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.5)', ml: 1 }}>/{plan.period}</Typography>}
        </Box>
        <Button
          fullWidth
          variant={featured ? 'contained' : 'outlined'}
          sx={{
            py: 1.5, mb: 3, borderRadius: 2, fontWeight: 600,
            ...(featured ? {
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            } : {
              borderColor: 'rgba(255,255,255,0.2)',
              color: 'white',
            }),
          }}
        >
          {plan.cta}
        </Button>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
          {plan.features.map((feature, i) => (
            <Box key={i} sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
              {feature.included ? <CheckCircle sx={{ fontSize: 18, color: '#4ade80' }} /> : <Close sx={{ fontSize: 18, color: 'rgba(255,255,255,0.2)' }} />}
              <Typography variant="body2" sx={{ color: feature.included ? 'rgba(255,255,255,0.8)' : 'rgba(255,255,255,0.3)' }}>{feature.text}</Typography>
            </Box>
          ))}
        </Box>
      </CardContent>
    </Card>
  );
}

// ============================================
// GSAP ANIMATED ARCHITECTURE FLOWCHART
// ============================================

// Main SVG Flowchart Component
function AnimatedFlowchart() {
  const svgRef = useRef(null);
  const containerRef = useRef(null);
  const [activeNode, setActiveNode] = useState(0);

  // Line refs for particle animation
  const lineRefs = useRef({});
  const dotRefs = useRef({});

  // Node data with positions (percentages for responsiveness)
  const nodes = [
    { id: 'requirements', label: 'Requirements', color: '#667eea', x: 8, y: 50, icon: '📝' },
    { id: 'ai', label: 'AI Engine', color: '#f093fb', x: 28, y: 25, icon: '🤖' },
    { id: 'knowledge', label: 'Knowledge Base', color: '#4facfe', x: 28, y: 75, icon: '🧠' },
    { id: 'generator', label: 'Test Generator', color: '#fbbf24', x: 50, y: 50, icon: '⚙️' },
    { id: 'executor', label: 'Test Executor', color: '#4ade80', x: 72, y: 50, icon: '▶️' },
    { id: 'learning', label: 'Learning Engine', color: '#f472b6', x: 92, y: 50, icon: '📊' },
  ];

  // Connection definitions
  const connections = [
    { from: 'requirements', to: 'ai', id: 'conn1' },
    { from: 'requirements', to: 'knowledge', id: 'conn2' },
    { from: 'ai', to: 'generator', id: 'conn3' },
    { from: 'knowledge', to: 'generator', id: 'conn4' },
    { from: 'generator', to: 'executor', id: 'conn5' },
    { from: 'executor', to: 'learning', id: 'conn6' },
    { from: 'learning', to: 'knowledge', id: 'conn7', feedback: true },
  ];

  // Get node by id
  const getNode = (id) => nodes.find(n => n.id === id);

  // Animate nodes cycling
  useEffect(() => {
    const interval = setInterval(() => {
      setActiveNode((prev) => (prev + 1) % nodes.length);
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  // Setup GSAP animations for flowing dots
  useGSAP(() => {
    if (!svgRef.current) return;

    // Animate each connection's dots
    connections.forEach((conn, connIndex) => {
      const lineEl = svgRef.current.querySelector(`#line-${conn.id}`);
      if (!lineEl) return;

      const totalLength = lineEl.getTotalLength();
      const fromNode = getNode(conn.from);

      // Create 3 dots per connection with staggered timing
      [0, 1, 2].forEach((dotIndex) => {
        const dotEl = svgRef.current.querySelector(`#dot-${conn.id}-${dotIndex}`);
        if (!dotEl) return;

        const delay = connIndex * 0.3 + dotIndex * 0.8;
        const duration = conn.feedback ? 3.5 : 2;

        // Infinite animation
        gsap.to({ progress: 0 }, {
          progress: 1,
          duration: duration,
          delay: delay,
          repeat: -1,
          ease: 'none',
          onUpdate: function() {
            const progress = this.targets()[0].progress;
            const point = lineEl.getPointAtLength(progress * totalLength);
            dotEl.setAttribute('cx', point.x);
            dotEl.setAttribute('cy', point.y);
            // Fade at ends
            const opacity = progress < 0.1 ? progress * 10 : progress > 0.9 ? (1 - progress) * 10 : 1;
            dotEl.setAttribute('opacity', opacity);
          }
        });
      });
    });

    // Draw lines animation on scroll
    const lines = svgRef.current.querySelectorAll('.flow-line');
    lines.forEach((line, i) => {
      const length = line.getTotalLength();
      gsap.set(line, { strokeDasharray: length, strokeDashoffset: length });

      gsap.to(line, {
        strokeDashoffset: 0,
        duration: 1,
        delay: i * 0.15,
        ease: 'power2.out',
        scrollTrigger: {
          trigger: containerRef.current,
          start: 'top 80%',
        }
      });
    });

    // Node entrance animation
    const nodeGroups = svgRef.current.querySelectorAll('.node-group');
    nodeGroups.forEach((node, i) => {
      gsap.fromTo(node,
        { opacity: 0, scale: 0.5, transformOrigin: 'center center' },
        {
          opacity: 1,
          scale: 1,
          duration: 0.5,
          delay: 0.8 + i * 0.1,
          ease: 'back.out(1.7)',
          scrollTrigger: {
            trigger: containerRef.current,
            start: 'top 80%',
          }
        }
      );
    });

  }, []);

  return (
    <>
      <Box
        ref={containerRef}
        sx={{
          position: 'relative',
          width: '100%',
          height: { xs: 380, md: 420 },
          borderRadius: 4,
          overflow: 'hidden',
          background: 'linear-gradient(135deg, rgba(10,10,25,1) 0%, rgba(20,20,40,1) 100%)',
          border: '1px solid rgba(102,126,234,0.25)',
          boxShadow: '0 0 40px rgba(102,126,234,0.1), inset 0 0 60px rgba(102,126,234,0.03)',
        }}
      >
        {/* Subtle grid background */}
        <Box
          sx={{
            position: 'absolute',
            inset: 0,
            backgroundImage: `
              linear-gradient(rgba(102,126,234,0.04) 1px, transparent 1px),
              linear-gradient(90deg, rgba(102,126,234,0.04) 1px, transparent 1px)
            `,
            backgroundSize: '30px 30px',
            opacity: 0.5,
          }}
        />

        {/* SVG Flowchart */}
        <svg
          ref={svgRef}
          viewBox="0 0 1000 400"
          style={{
            width: '100%',
            height: '100%',
            position: 'absolute',
            inset: 0,
          }}
          preserveAspectRatio="xMidYMid meet"
        >
        <defs>
          {/* Glow filter for dots */}
          <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>

          {/* Stronger glow for active nodes */}
          <filter id="nodeGlow" x="-100%" y="-100%" width="300%" height="300%">
            <feGaussianBlur stdDeviation="8" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>

          {/* Gradient for feedback loop */}
          <linearGradient id="feedbackGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#f472b6" />
            <stop offset="100%" stopColor="#4facfe" />
          </linearGradient>
        </defs>

        {/* Connection Lines */}
        {connections.map((conn) => {
          const from = getNode(conn.from);
          const to = getNode(conn.to);
          const x1 = from.x * 10;
          const y1 = from.y * 4;
          const x2 = to.x * 10;
          const y2 = to.y * 4;

          // Feedback loop goes around the bottom
          if (conn.feedback) {
            const path = `M ${x1} ${y1} L ${x1} 360 L ${x2} 360 L ${x2} ${y2}`;
            return (
              <g key={conn.id}>
                {/* Glow line */}
                <path
                  d={path}
                  fill="none"
                  stroke="url(#feedbackGradient)"
                  strokeWidth="6"
                  opacity="0.15"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                {/* Main line */}
                <path
                  id={`line-${conn.id}`}
                  className="flow-line"
                  d={path}
                  fill="none"
                  stroke="url(#feedbackGradient)"
                  strokeWidth="2"
                  opacity="0.6"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                {/* Flowing dots */}
                {[0, 1, 2].map((i) => (
                  <circle
                    key={i}
                    id={`dot-${conn.id}-${i}`}
                    r="5"
                    fill="#f472b6"
                    filter="url(#glow)"
                    opacity="0"
                  />
                ))}
              </g>
            );
          }

          return (
            <g key={conn.id}>
              {/* Glow line */}
              <line
                x1={x1} y1={y1}
                x2={x2} y2={y2}
                stroke={from.color}
                strokeWidth="6"
                opacity="0.1"
                strokeLinecap="round"
              />
              {/* Main line */}
              <line
                id={`line-${conn.id}`}
                className="flow-line"
                x1={x1} y1={y1}
                x2={x2} y2={y2}
                stroke={from.color}
                strokeWidth="2"
                opacity="0.5"
                strokeLinecap="round"
              />
              {/* Flowing dots */}
              {[0, 1, 2].map((i) => (
                <circle
                  key={i}
                  id={`dot-${conn.id}-${i}`}
                  r="4"
                  fill={from.color}
                  filter="url(#glow)"
                  opacity="0"
                />
              ))}
            </g>
          );
        })}

        {/* Nodes */}
        {nodes.map((node, index) => {
          const cx = node.x * 10;
          const cy = node.y * 4;
          const isActive = activeNode === index;

          return (
            <g key={node.id} className="node-group" style={{ opacity: 0 }}>
              {/* Beacon ripple effect - same as CreativeLoader */}
              {isActive && (
                <>
                  {/* Ripple 1 */}
                  <circle
                    cx={cx}
                    cy={cy}
                    r="28"
                    fill="none"
                    stroke={node.color}
                    strokeWidth="2"
                    opacity="0"
                  >
                    <animate
                      attributeName="r"
                      from="28"
                      to="56"
                      dur="2s"
                      calcMode="spline"
                      keySplines="0 0.2 0.8 1"
                      repeatCount="indefinite"
                    />
                    <animate
                      attributeName="opacity"
                      from="0.7"
                      to="0"
                      dur="2s"
                      calcMode="spline"
                      keySplines="0 0.2 0.8 1"
                      repeatCount="indefinite"
                    />
                  </circle>
                  {/* Ripple 2 - delayed */}
                  <circle
                    cx={cx}
                    cy={cy}
                    r="28"
                    fill="none"
                    stroke={node.color}
                    strokeWidth="2"
                    opacity="0"
                  >
                    <animate
                      attributeName="r"
                      from="28"
                      to="56"
                      dur="2s"
                      begin="1s"
                      calcMode="spline"
                      keySplines="0 0.2 0.8 1"
                      repeatCount="indefinite"
                    />
                    <animate
                      attributeName="opacity"
                      from="0.7"
                      to="0"
                      dur="2s"
                      begin="1s"
                      calcMode="spline"
                      keySplines="0 0.2 0.8 1"
                      repeatCount="indefinite"
                    />
                  </circle>
                </>
              )}

              {/* Outer glow ring */}
              <circle
                cx={cx}
                cy={cy}
                r={isActive ? 38 : 32}
                fill="none"
                stroke={node.color}
                strokeWidth="1"
                opacity={isActive ? 0.5 : 0.15}
                filter={isActive ? "url(#nodeGlow)" : undefined}
              />

              {/* Background circle */}
              <circle
                cx={cx}
                cy={cy}
                r="28"
                fill="rgba(15,15,35,0.95)"
                stroke={node.color}
                strokeWidth={isActive ? 2.5 : 2}
                filter={isActive ? "url(#nodeGlow)" : undefined}
              />

              {/* Inner gradient */}
              <circle
                cx={cx}
                cy={cy}
                r="24"
                fill={`url(#grad-${node.id})`}
                opacity={isActive ? 0.5 : 0.3}
              />

              {/* Icon */}
              <text
                x={cx}
                y={cy}
                textAnchor="middle"
                dominantBaseline="central"
                fontSize="20"
                style={{ pointerEvents: 'none' }}
              >
                {node.icon}
              </text>

              {/* Label */}
              <text
                x={cx}
                y={cy + 48}
                textAnchor="middle"
                fill={isActive ? "rgba(255,255,255,1)" : "rgba(255,255,255,0.8)"}
                fontSize="12"
                fontWeight={isActive ? "600" : "500"}
                fontFamily="system-ui, -apple-system, sans-serif"
              >
                {node.label}
              </text>

              {/* Gradient definition for this node */}
              <defs>
                <radialGradient id={`grad-${node.id}`} cx="30%" cy="30%">
                  <stop offset="0%" stopColor={node.color} stopOpacity="0.5" />
                  <stop offset="100%" stopColor={node.color} stopOpacity="0" />
                </radialGradient>
              </defs>
            </g>
          );
        })}
        </svg>
      </Box>

      {/* Live indicator - positioned below the flowchart */}
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          mt: 2,
        }}
      >
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 1.5,
            px: 2.5,
            py: 0.75,
            background: 'rgba(10,10,30,0.8)',
            borderRadius: 2,
            border: '1px solid rgba(102,126,234,0.3)',
          }}
        >
          <Box
            sx={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              background: 'linear-gradient(135deg, #4ade80 0%, #22c55e 100%)',
              boxShadow: '0 0 8px #4ade80',
              animation: 'pulse 2s ease-in-out infinite',
              '@keyframes pulse': {
                '0%, 100%': { transform: 'scale(1)', opacity: 1 },
                '50%': { transform: 'scale(1.3)', opacity: 0.7 },
              },
            }}
          />
          <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.7)', fontWeight: 500, fontSize: '0.7rem' }}>
            Live AI Pipeline
          </Typography>
        </Box>
      </Box>
    </>
  );
}

// Detailed flow step cards
function FlowStepCard({ step, index, isActive }) {
  const cardRef = useRef(null);

  useGSAP(() => {
    if (!cardRef.current) return;

    gsap.fromTo(
      cardRef.current,
      { opacity: 0, y: 40, scale: 0.95 },
      {
        opacity: 1,
        y: 0,
        scale: 1,
        duration: 0.6,
        delay: index * 0.1,
        ease: 'power3.out',
        scrollTrigger: {
          trigger: cardRef.current,
          start: 'top 85%',
        },
      }
    );
  }, [index]);

  return (
    <Box
      ref={cardRef}
      sx={{
        p: 3,
        borderRadius: 3,
        background: isActive
          ? `linear-gradient(135deg, ${step.color}15 0%, ${step.color}08 100%)`
          : 'rgba(255,255,255,0.02)',
        border: `1px solid ${isActive ? step.color + '40' : 'rgba(255,255,255,0.05)'}`,
        transition: 'all 0.4s ease',
        cursor: 'pointer',
        '&:hover': {
          background: `linear-gradient(135deg, ${step.color}20 0%, ${step.color}10 100%)`,
          borderColor: step.color + '60',
          transform: 'translateY(-4px)',
        },
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
        <Box
          sx={{
            width: 48,
            height: 48,
            borderRadius: 2,
            background: `linear-gradient(135deg, ${step.color}30 0%, ${step.color}10 100%)`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '1.5rem',
            boxShadow: `0 4px 15px ${step.color}20`,
          }}
        >
          {step.icon}
        </Box>
        <Box>
          <Typography variant="h6" sx={{ color: 'white', fontWeight: 600, fontSize: '1rem' }}>
            {step.title}
          </Typography>
          <Typography variant="caption" sx={{ color: step.color }}>
            {step.tech}
          </Typography>
        </Box>
      </Box>
      <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.6)', lineHeight: 1.7 }}>
        {step.description}
      </Typography>
      <Box sx={{ mt: 2, display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
        {step.features.map((feature, i) => (
          <Chip
            key={i}
            label={feature}
            size="small"
            sx={{
              background: `${step.color}15`,
              color: step.color,
              fontSize: '0.65rem',
              height: 22,
            }}
          />
        ))}
      </Box>
    </Box>
  );
}

// Feature row with alternating layout
function FeatureRow({ feature, index, reversed = false }) {
  const rowRef = useRef(null);

  useGSAP(() => {
    if (!rowRef.current) return;

    const elements = rowRef.current.querySelectorAll('.feature-animate');

    gsap.fromTo(
      elements,
      { opacity: 0, x: reversed ? 50 : -50 },
      {
        opacity: 1,
        x: 0,
        duration: 0.8,
        stagger: 0.1,
        ease: 'power3.out',
        scrollTrigger: {
          trigger: rowRef.current,
          start: 'top 75%',
        },
      }
    );
  }, [reversed]);

  return (
    <Grid ref={rowRef} container spacing={6} alignItems="center" sx={{ mb: { xs: 8, md: 12 } }}>
      <Grid item xs={12} md={6} order={{ xs: 1, md: reversed ? 2 : 1 }}>
        <Box className="feature-animate">
          <Chip
            label={feature.tag}
            size="small"
            sx={{ mb: 2, background: `${feature.color}20`, color: feature.color, fontWeight: 600 }}
          />
          <Typography variant="h3" sx={{ color: 'white', fontWeight: 700, mb: 2, fontSize: { xs: '1.75rem', md: '2.25rem' } }}>
            {feature.title}
          </Typography>
          <Typography variant="body1" sx={{ color: 'rgba(255,255,255,0.6)', mb: 3, lineHeight: 1.8 }}>
            {feature.description}
          </Typography>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
            {feature.points.map((point, i) => (
              <Box key={i} className="feature-animate" sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                <Box
                  sx={{
                    width: 24,
                    height: 24,
                    borderRadius: '50%',
                    background: `${feature.color}20`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <CheckCircle sx={{ fontSize: 14, color: feature.color }} />
                </Box>
                <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.75)' }}>{point}</Typography>
              </Box>
            ))}
          </Box>
        </Box>
      </Grid>
      <Grid item xs={12} md={6} order={{ xs: 2, md: reversed ? 1 : 2 }}>
        <Box className="feature-animate">
          <GradientCard gradient={feature.gradient}>
            <Box sx={{ p: 4, display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 300 }}>
              <MagneticButton strength={0.2}>
                <Avatar
                  sx={{
                    width: 120,
                    height: 120,
                    background: feature.gradient,
                    boxShadow: `0 20px 60px ${feature.color}40`,
                    cursor: 'pointer',
                  }}
                >
                  {feature.icon}
                </Avatar>
              </MagneticButton>
            </Box>
          </GradientCard>
        </Box>
      </Grid>
    </Grid>
  );
}

// ============================================
// MAIN LANDING COMPONENT
// ============================================

export default function Landing() {
  const navigate = useNavigate();
  const { scrollYProgress } = useScroll();
  const [isScrolled, setIsScrolled] = useState(false);
  const mainRef = useRef(null);
  const heroRef = useRef(null);
  const orbRef1 = useRef(null);
  const orbRef2 = useRef(null);

  const handleGetStarted = () => navigate('/login');

  // Scroll detection for sticky nav
  useEffect(() => {
    const handleScroll = () => setIsScrolled(window.scrollY > 50);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // GSAP Parallax on orbs
  useGSAP(() => {
    if (orbRef1.current) {
      gsap.to(orbRef1.current, {
        y: 200,
        ease: 'none',
        scrollTrigger: {
          trigger: heroRef.current,
          start: 'top top',
          end: 'bottom top',
          scrub: 1,
        },
      });
    }

    if (orbRef2.current) {
      gsap.to(orbRef2.current, {
        y: 150,
        x: -50,
        ease: 'none',
        scrollTrigger: {
          trigger: heroRef.current,
          start: 'top top',
          end: 'bottom top',
          scrub: 1,
        },
      });
    }
  }, []);

  // Hero text animation
  useGSAP(() => {
    if (!heroRef.current) return;

    const tl = gsap.timeline({ delay: 0.5 });

    tl.fromTo(
      '.hero-chip',
      { opacity: 0, y: 20 },
      { opacity: 1, y: 0, duration: 0.6, ease: 'power3.out' }
    )
      .fromTo(
        '.hero-title',
        { opacity: 0, y: 40 },
        { opacity: 1, y: 0, duration: 0.8, ease: 'power3.out' },
        '-=0.3'
      )
      .fromTo(
        '.hero-subtitle',
        { opacity: 0, y: 30 },
        { opacity: 1, y: 0, duration: 0.6, ease: 'power3.out' },
        '-=0.4'
      )
      .fromTo(
        '.hero-buttons',
        { opacity: 0, y: 20 },
        { opacity: 1, y: 0, duration: 0.6, ease: 'power3.out' },
        '-=0.3'
      )
      .fromTo(
        '.hero-features',
        { opacity: 0 },
        { opacity: 1, duration: 0.5 },
        '-=0.2'
      )
      .fromTo(
        '.hero-code',
        { opacity: 0, scale: 0.9, x: 50 },
        { opacity: 1, scale: 1, x: 0, duration: 0.8, ease: 'power3.out' },
        '-=0.6'
      );
  }, []);

  // Data
  const testimonials = [
    {
      quote: "GhostQA reduced our test creation time by 90%. What used to take days now takes minutes.",
      name: "Sarah Chen",
      role: "QA Lead",
      company: "TechCorp",
      gradient: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    },
    {
      quote: "The self-learning feature is incredible. It gets faster with every run.",
      name: "Michael Rodriguez",
      role: "Engineering Manager",
      company: "StartupXYZ",
      gradient: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
    },
    {
      quote: "Finally, a tool that lets manual testers write automated tests without coding.",
      name: "Emily Watson",
      role: "Director of QA",
      company: "Enterprise Inc",
      gradient: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
    },
  ];

  const pricingPlans = [
    {
      name: 'Free',
      description: 'Perfect for trying out GhostQA',
      price: '$0',
      period: 'forever',
      cta: 'Get Started',
      features: [
        { text: '50 test cases/month', included: true },
        { text: 'Gherkin BDD output', included: true },
        { text: 'Basic AI models', included: true },
        { text: '1 project', included: true },
        { text: 'Community support', included: true },
        { text: 'Self-learning AI', included: false },
        { text: 'Priority support', included: false },
      ],
    },
    {
      name: 'Pro',
      description: 'For professional QA teams',
      price: '$49',
      period: 'month',
      cta: 'Start Free Trial',
      features: [
        { text: 'Unlimited test cases', included: true },
        { text: 'All output formats', included: true },
        { text: 'Advanced AI (Claude, GPT)', included: true },
        { text: 'Unlimited projects', included: true },
        { text: 'Self-learning AI', included: true },
        { text: 'Priority support', included: true },
        { text: 'Custom integrations', included: true },
      ],
    },
    {
      name: 'Enterprise',
      description: 'For large organizations',
      price: 'Custom',
      period: null,
      cta: 'Contact Sales',
      features: [
        { text: 'Everything in Pro', included: true },
        { text: 'On-premise deployment', included: true },
        { text: 'SSO & SAML', included: true },
        { text: 'Dedicated support', included: true },
        { text: 'Custom AI training', included: true },
        { text: 'SLA guarantee', included: true },
        { text: 'Audit logs', included: true },
      ],
    },
  ];

  const detailedFeatures = [
    {
      tag: 'AI-Powered',
      title: 'Intelligent Test Generation',
      description: 'Transform plain English requirements into comprehensive test cases. Our AI understands context, edge cases, and generates tests that actually matter.',
      points: ['Supports BRD, User Stories, PRDs', 'Generates positive & negative scenarios', 'Automatic edge case detection', 'Multiple output formats'],
      icon: <Psychology sx={{ fontSize: 56 }} />,
      color: '#667eea',
      gradient: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    },
    {
      tag: 'Self-Learning',
      title: 'AI That Gets Smarter',
      description: 'Our unique self-learning system remembers element patterns from your application, reducing AI calls from 45% to under 5% over time.',
      points: ['2000x faster element lookups', 'Works offline after learning', 'Automatic pattern recognition', 'Semantic similarity matching'],
      icon: <SmartToy sx={{ fontSize: 56 }} />,
      color: '#f093fb',
      gradient: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
    },
    {
      tag: 'No-Code',
      title: 'Execute Without Coding',
      description: 'Run Gherkin tests without writing step definitions. GhostQA understands natural language steps and automates browser interactions.',
      points: ['Zero step definition files', 'Natural language processing', 'Multi-browser support', 'Parallel execution'],
      icon: <PlayArrow sx={{ fontSize: 56 }} />,
      color: '#4facfe',
      gradient: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
    },
    {
      tag: 'Frameworks',
      title: 'Built-in UI Intelligence',
      description: 'Pre-trained patterns for Material UI, Ant Design, Bootstrap and more. GhostQA knows how to interact with modern UI components out of the box.',
      points: ['Material UI v5 support', 'Ant Design components', 'Bootstrap widgets', 'Custom component training'],
      icon: <Layers sx={{ fontSize: 56 }} />,
      color: '#fbbf24',
      gradient: 'linear-gradient(135deg, #fbbf24 0%, #f97316 100%)',
    },
  ];

  const faqs = [
    { q: 'What AI models are supported?', a: 'GhostQA supports Anthropic Claude (3.5 Sonnet, Opus), OpenAI GPT-4, and local Ollama models for offline/private deployments.' },
    { q: 'Do I need coding skills?', a: 'No coding required! Generate tests from plain English requirements and run them without writing step definitions.' },
    { q: 'How does self-learning work?', a: 'Our AI learns element patterns from every test execution, reducing AI API calls from ~45% to under 5% over time.' },
    { q: 'Can I use it on-premise?', a: 'Yes! Enterprise plans include on-premise deployment. Use Ollama for fully offline AI processing.' },
    { q: 'What output formats are supported?', a: 'Gherkin BDD (.feature), Traditional test tables (.csv), JSON, and ZIP archives.' },
  ];

  const stats = [
    { value: 95, suffix: '%', label: 'Time Saved', icon: <Timer /> },
    { value: 500, suffix: '+', label: 'Tests/Hour', icon: <Speed /> },
    { value: 2000, suffix: 'x', label: 'Faster AI', icon: <Bolt /> },
    { value: 10, suffix: 'k+', label: 'Tests Generated', icon: <Assessment /> },
  ];

  const typingTexts = ['Test Cases', 'BDD Scenarios', 'E2E Tests', 'API Tests'];

  return (
    <Box ref={mainRef} sx={{ minHeight: '100vh', background: '#0a0a1a', overflow: 'hidden' }}>
      {/* Scroll Progress - GSAP enhanced */}
      <motion.div
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          height: 3,
          background: 'linear-gradient(90deg, #667eea, #764ba2, #f093fb)',
          transformOrigin: '0%',
          scaleX: scrollYProgress,
          zIndex: 1000,
        }}
      />

      {/* Sticky Navigation */}
      <Box
        sx={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          zIndex: 999,
          py: 2,
          px: { xs: 2, md: 4 },
          background: isScrolled ? 'rgba(10,10,26,0.9)' : 'transparent',
          backdropFilter: isScrolled ? 'blur(20px)' : 'none',
          borderBottom: isScrolled ? '1px solid rgba(255,255,255,0.05)' : 'none',
          transition: 'all 0.3s ease',
        }}
      >
        <Container maxWidth="lg">
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <MagneticButton strength={0.3}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, cursor: 'pointer' }}>
                <Avatar
                  sx={{
                    width: 40,
                    height: 40,
                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    boxShadow: '0 4px 20px rgba(102,126,234,0.4)',
                  }}
                >
                  <BugReport sx={{ fontSize: 22 }} />
                </Avatar>
                <Typography variant="h6" sx={{ fontWeight: 700, color: 'white', letterSpacing: '-0.5px' }}>
                  GhostQA
                </Typography>
              </Box>
            </MagneticButton>

            <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
              <Button
                variant="text"
                onClick={() => navigate('/how-it-works')}
                sx={{ color: 'rgba(255,255,255,0.8)', fontWeight: 500, '&:hover': { color: 'white', background: 'rgba(255,255,255,0.05)' } }}
              >
                How it Works
              </Button>
              <Button
                variant="text"
                onClick={handleGetStarted}
                sx={{ color: 'rgba(255,255,255,0.8)', fontWeight: 500, '&:hover': { color: 'white', background: 'rgba(255,255,255,0.05)' } }}
              >
                Login
              </Button>
              <MagneticButton strength={0.2}>
                <Button
                  variant="contained"
                  onClick={handleGetStarted}
                  sx={{
                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    boxShadow: '0 4px 15px rgba(102,126,234,0.4)',
                    px: 3,
                    fontWeight: 600,
                    '&:hover': { boxShadow: '0 8px 30px rgba(102,126,234,0.5)' },
                  }}
                >
                  Get Started
                </Button>
              </MagneticButton>
            </Box>
          </Box>
        </Container>
      </Box>

      {/* Hero Section */}
      <Box
        ref={heroRef}
        sx={{
          minHeight: '100vh',
          position: 'relative',
          display: 'flex',
          alignItems: 'center',
          pt: 10,
        }}
      >
        <GSAPParticles />

        {/* Parallax Gradient orbs */}
        <Box
          ref={orbRef1}
          sx={{
            position: 'absolute',
            width: 600,
            height: 600,
            borderRadius: '50%',
            background: 'radial-gradient(circle, rgba(102,126,234,0.2) 0%, transparent 70%)',
            filter: 'blur(60px)',
            left: '-10%',
            top: '10%',
            pointerEvents: 'none',
          }}
        />
        <Box
          ref={orbRef2}
          sx={{
            position: 'absolute',
            width: 400,
            height: 400,
            borderRadius: '50%',
            background: 'radial-gradient(circle, rgba(240,147,251,0.15) 0%, transparent 70%)',
            filter: 'blur(60px)',
            right: '-5%',
            bottom: '20%',
            pointerEvents: 'none',
          }}
        />

        <Container maxWidth="lg" sx={{ position: 'relative', zIndex: 5 }}>
          <Grid container spacing={4} alignItems="center">
            <Grid item xs={12} md={7}>
              <Chip
                className="hero-chip"
                label="Powered by Claude AI & Ollama"
                icon={<AutoAwesome sx={{ color: '#a5b4fc !important', fontSize: 16 }} />}
                sx={{
                  mb: 3,
                  opacity: 0,
                  background: 'rgba(102,126,234,0.15)',
                  color: '#a5b4fc',
                  border: '1px solid rgba(102,126,234,0.25)',
                  fontSize: '0.85rem',
                }}
              />

              <Typography
                className="hero-title"
                variant="h1"
                sx={{
                  fontWeight: 800,
                  fontSize: { xs: '2.5rem', sm: '3.5rem', md: '4rem' },
                  color: 'white',
                  mb: 2,
                  lineHeight: 1.1,
                  opacity: 0,
                }}
              >
                Generate{' '}
                <Box
                  component="span"
                  sx={{
                    background: 'linear-gradient(135deg, #667eea 0%, #a5b4fc 100%)',
                    backgroundClip: 'text',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                    display: 'inline-block',
                    minWidth: { xs: 150, md: 220 },
                  }}
                >
                  <SmoothTyping texts={typingTexts} typingSpeed={100} deletingSpeed={50} pauseDuration={2500} />
                </Box>
                <br />
                From Plain English
              </Typography>

              <Typography
                className="hero-subtitle"
                variant="h6"
                sx={{
                  color: 'rgba(255,255,255,0.6)',
                  mb: 4,
                  maxWidth: 500,
                  lineHeight: 1.7,
                  fontWeight: 400,
                  opacity: 0,
                }}
              >
                Transform BRDs and requirements into comprehensive Gherkin BDD scenarios instantly.
                Self-learning AI that gets smarter with every test run.
              </Typography>

              <Box className="hero-buttons" sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', mb: 4, opacity: 0 }}>
                <MagneticButton strength={0.3}>
                  <Button
                    variant="contained"
                    size="large"
                    endIcon={<ArrowForward />}
                    onClick={handleGetStarted}
                    sx={{
                      py: 1.75,
                      px: 4,
                      fontSize: '1rem',
                      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                      boxShadow: '0 8px 30px rgba(102,126,234,0.4)',
                      '&:hover': { boxShadow: '0 12px 40px rgba(102,126,234,0.5)' },
                    }}
                  >
                    Start Free
                  </Button>
                </MagneticButton>
                <MagneticButton strength={0.3}>
                  <Button
                    variant="outlined"
                    size="large"
                    startIcon={<PlayCircle />}
                    sx={{
                      py: 1.75,
                      px: 4,
                      fontSize: '1rem',
                      borderColor: 'rgba(255,255,255,0.2)',
                      color: 'white',
                      '&:hover': { borderColor: 'rgba(102,126,234,0.5)', background: 'rgba(102,126,234,0.1)' },
                    }}
                  >
                    Watch Demo
                  </Button>
                </MagneticButton>
              </Box>

              <Box className="hero-features" sx={{ display: 'flex', gap: 4, flexWrap: 'wrap', opacity: 0 }}>
                {['No coding required', 'Works offline', 'Free forever plan'].map((text, i) => (
                  <Box key={i} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <CheckCircle sx={{ color: '#4ade80', fontSize: 18 }} />
                    <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.7)' }}>{text}</Typography>
                  </Box>
                ))}
              </Box>
            </Grid>

            <Grid item xs={12} md={5} sx={{ display: { xs: 'none', md: 'block' } }}>
              <Box className="hero-code" sx={{ position: 'relative', opacity: 0 }}>
                <Box
                  sx={{
                    background: 'linear-gradient(145deg, #1a1a2e 0%, #16162a 100%)',
                    borderRadius: 3,
                    p: 3,
                    border: '1px solid rgba(102,126,234,0.2)',
                    boxShadow: '0 20px 60px rgba(0,0,0,0.5)',
                  }}
                >
                  <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
                    <Box sx={{ width: 10, height: 10, borderRadius: '50%', background: '#ff5f57' }} />
                    <Box sx={{ width: 10, height: 10, borderRadius: '50%', background: '#febc2e' }} />
                    <Box sx={{ width: 10, height: 10, borderRadius: '50%', background: '#28c840' }} />
                  </Box>
                  <Typography sx={{ fontFamily: 'monospace', fontSize: '0.8rem', color: '#a5b4fc' }}>
                    <span style={{ color: '#c084fc' }}>Feature:</span> User Authentication<br />
                    <br />
                    <span style={{ color: '#fbbf24' }}>@smoke</span> <span style={{ color: '#fbbf24' }}>@regression</span><br />
                    <span style={{ color: '#c084fc' }}>Scenario:</span> Successful login<br />
                    {'  '}<span style={{ color: '#4ade80' }}>Given</span> I am on the login page<br />
                    {'  '}<span style={{ color: '#4ade80' }}>When</span> I enter valid credentials<br />
                    {'  '}<span style={{ color: '#4ade80' }}>Then</span> I should see dashboard
                  </Typography>
                </Box>

                <MagneticButton strength={0.5}>
                  <Chip
                    icon={<AutoAwesome sx={{ color: 'white !important' }} />}
                    label="AI Generated"
                    sx={{
                      position: 'absolute',
                      top: -15,
                      right: -15,
                      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                      color: 'white',
                      fontWeight: 600,
                      boxShadow: '0 8px 25px rgba(102,126,234,0.4)',
                      cursor: 'pointer',
                    }}
                  />
                </MagneticButton>
              </Box>
            </Grid>
          </Grid>
        </Container>

        {/* Scroll indicator */}
        <Box sx={{ position: 'absolute', bottom: 40, left: '50%', transform: 'translateX(-50%)' }}>
          <motion.div
            animate={{ y: [0, 10, 0] }}
            transition={{ duration: 2, repeat: Infinity }}
          >
            <Box
              sx={{
                width: 24,
                height: 40,
                border: '2px solid rgba(255,255,255,0.2)',
                borderRadius: 12,
                display: 'flex',
                justifyContent: 'center',
                pt: 1,
              }}
            >
              <motion.div animate={{ y: [0, 12, 0], opacity: [1, 0, 1] }} transition={{ duration: 2, repeat: Infinity }}>
                <Box sx={{ width: 4, height: 8, background: 'rgba(255,255,255,0.4)', borderRadius: 2 }} />
              </motion.div>
            </Box>
          </motion.div>
        </Box>
      </Box>

      {/* Stats Section with GSAP counters */}
      <Box sx={{ py: 10, background: 'linear-gradient(180deg, #0a0a1a 0%, #0f0f24 100%)', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
        <Container maxWidth="lg">
          <RevealSection>
            <Box sx={{ textAlign: 'center', mb: 6 }}>
              <Typography variant="h3" sx={{ color: 'white', fontWeight: 700, mb: 2, fontSize: { xs: '1.75rem', md: '2.5rem' } }}>
                Trusted by QA Teams Worldwide
              </Typography>
              <Typography variant="body1" sx={{ color: 'rgba(255,255,255,0.5)', maxWidth: 500, mx: 'auto' }}>
                Delivering measurable results for test automation
              </Typography>
            </Box>
          </RevealSection>

          <StaggerReveal staggerDelay={0.15}>
            {stats.map((stat, index) => (
              <Box
                key={index}
                sx={{
                  display: 'inline-block',
                  width: { xs: '50%', md: '25%' },
                  p: 2,
                }}
              >
                <Box
                  sx={{
                    textAlign: 'center',
                    p: 3,
                    borderRadius: 3,
                    background: 'rgba(255,255,255,0.02)',
                    border: '1px solid rgba(255,255,255,0.05)',
                    transition: 'all 0.3s ease',
                    '&:hover': {
                      background: 'rgba(102,126,234,0.08)',
                      borderColor: 'rgba(102,126,234,0.3)',
                      transform: 'translateY(-8px)',
                      boxShadow: '0 20px 40px rgba(102,126,234,0.15)',
                    },
                  }}
                >
                  <Box sx={{ color: 'rgba(102,126,234,0.7)', mb: 1 }}>{stat.icon}</Box>
                  <Typography
                    variant="h3"
                    sx={{
                      fontWeight: 800,
                      background: 'linear-gradient(135deg, #667eea 0%, #a5b4fc 100%)',
                      backgroundClip: 'text',
                      WebkitBackgroundClip: 'text',
                      WebkitTextFillColor: 'transparent',
                      fontSize: { xs: '2rem', md: '2.5rem' },
                    }}
                  >
                    <GSAPCounter end={stat.value} suffix={stat.suffix} duration={2.5} />
                  </Typography>
                  <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.5)', mt: 0.5 }}>{stat.label}</Typography>
                </Box>
              </Box>
            ))}
          </StaggerReveal>
        </Container>
      </Box>

      {/* Integrations Marquee - Hidden for now */}
      {/*
      <Box sx={{ py: 6, background: '#0f0f24' }}>
        <Container maxWidth="lg">
          <RevealSection>
            <Typography variant="body2" textAlign="center" sx={{ color: 'rgba(255,255,255,0.4)', mb: 3, textTransform: 'uppercase', letterSpacing: 2 }}>
              Works with your favorite tools
            </Typography>
          </RevealSection>
        </Container>
        <IntegrationMarquee />
      </Box>
      */}

      {/* Live Demo Section */}
      <Box sx={{ py: { xs: 10, md: 14 }, background: '#0a0a1a' }}>
        <Container maxWidth="lg">
          <RevealSection>
            <Box sx={{ textAlign: 'center', mb: 8 }}>
              <Chip label="Live Demo" sx={{ mb: 2, background: 'rgba(74,222,128,0.15)', color: '#4ade80' }} />
              <Typography variant="h3" sx={{ color: 'white', fontWeight: 700, mb: 2, fontSize: { xs: '1.75rem', md: '2.5rem' } }}>
                See the Magic in Action
              </Typography>
              <Typography variant="body1" sx={{ color: 'rgba(255,255,255,0.5)', maxWidth: 600, mx: 'auto' }}>
                Watch how GhostQA transforms simple requirements into comprehensive, production-ready test scenarios
              </Typography>
            </Box>
          </RevealSection>
          <CodeTerminal />
        </Container>
      </Box>

      {/* Architecture Flowchart Section */}
      <Box sx={{ py: { xs: 10, md: 14 }, background: 'linear-gradient(180deg, #0a0a1a 0%, #0f0f24 100%)' }}>
        <Container maxWidth="lg">
          <RevealSection>
            <Box sx={{ textAlign: 'center', mb: 6 }}>
              <Chip label="Architecture" sx={{ mb: 2, background: 'rgba(102,126,234,0.15)', color: '#a5b4fc' }} />
              <Typography variant="h3" sx={{ color: 'white', fontWeight: 700, mb: 2, fontSize: { xs: '1.75rem', md: '2.5rem' } }}>
                How It Works
              </Typography>
              <Typography variant="body1" sx={{ color: 'rgba(255,255,255,0.5)', maxWidth: 600, mx: 'auto' }}>
                A self-improving AI pipeline that gets smarter with every test run
              </Typography>
            </Box>
          </RevealSection>

          {/* CTA to full architecture page */}
          <RevealSection>
            <Box
              sx={{
                textAlign: 'center',
                p: 4,
                borderRadius: 3,
                background: 'linear-gradient(135deg, rgba(102,126,234,0.1) 0%, rgba(118,75,162,0.1) 100%)',
                border: '1px solid rgba(102,126,234,0.2)',
                mb: 4,
              }}
            >
              <Typography variant="h6" sx={{ color: 'white', fontWeight: 600, mb: 2 }}>
                Want to see the complete technical architecture?
              </Typography>
              <MagneticButton strength={0.3}>
                <Button
                  variant="contained"
                  size="large"
                  endIcon={<ArrowForward />}
                  onClick={() => navigate('/how-it-works')}
                  sx={{
                    py: 1.5,
                    px: 4,
                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    boxShadow: '0 8px 30px rgba(102,126,234,0.4)',
                    '&:hover': { boxShadow: '0 12px 40px rgba(102,126,234,0.5)' },
                  }}
                >
                  See Full Architecture
                </Button>
              </MagneticButton>
            </Box>
          </RevealSection>

          {/* Flow Step Cards */}
          <Box sx={{ mt: 6 }}>
            <Grid container spacing={3}>
              {[
                {
                  icon: '📄',
                  title: 'Requirements Input',
                  tech: 'BRD / User Stories / Data Dictionary',
                  description: 'Upload your business requirements in any format. Our AI understands plain English, markdown, and structured documents.',
                  features: ['PDF', 'DOCX', 'Markdown', 'Excel'],
                  color: '#667eea',
                },
                {
                  icon: '🧠',
                  title: 'AI Processing',
                  tech: 'Claude / Ollama / GPT',
                  description: 'Multiple AI engines analyze your requirements, understanding context, edge cases, and generating comprehensive test scenarios.',
                  features: ['Auto-detect LLM', 'Batch Processing', 'Smart Prompts'],
                  color: '#f093fb',
                },
                {
                  icon: '💡',
                  title: 'Knowledge Base',
                  tech: 'Element DNA / Semantic Intelligence',
                  description: 'A self-learning knowledge base that remembers element patterns, reducing AI calls by 95% over time.',
                  features: ['Element DNA', 'Pattern Store', '2000x Faster'],
                  color: '#4facfe',
                },
                {
                  icon: '⚙️',
                  title: 'Test Generation',
                  tech: 'Gherkin / BDD / Traditional',
                  description: 'Generate executable test scenarios in Gherkin BDD format or traditional test case tables with full coverage.',
                  features: ['Given-When-Then', 'Tags', 'Scenarios'],
                  color: '#fbbf24',
                },
                {
                  icon: '▶️',
                  title: 'Test Execution',
                  tech: 'Playwright / No-Code',
                  description: 'Execute tests without writing step definitions. Our AI understands natural language and automates browser interactions.',
                  features: ['Zero Code', 'Multi-Browser', 'Screenshots'],
                  color: '#4ade80',
                },
                {
                  icon: '🔄',
                  title: 'Self-Learning',
                  tech: 'Continuous Improvement',
                  description: 'Every test run teaches the system. Success patterns are remembered, failures trigger smart recovery strategies.',
                  features: ['Pattern Mining', 'Auto-Recovery', 'Confidence Decay'],
                  color: '#f472b6',
                },
              ].map((step, index) => (
                <Grid item xs={12} sm={6} md={4} key={index}>
                  <FlowStepCard step={step} index={index} isActive={false} />
                </Grid>
              ))}
            </Grid>
          </Box>
        </Container>
      </Box>

      {/* Detailed Features - Alternating Layout */}
      <Box sx={{ py: { xs: 10, md: 14 }, background: 'linear-gradient(180deg, #0f0f24 0%, #0a0a1a 100%)' }}>
        <Container maxWidth="lg">
          <RevealSection>
            <Box sx={{ textAlign: 'center', mb: 10 }}>
              <Typography variant="h3" sx={{ color: 'white', fontWeight: 700, mb: 2, fontSize: { xs: '1.75rem', md: '2.5rem' } }}>
                Everything You Need
              </Typography>
              <Typography variant="body1" sx={{ color: 'rgba(255,255,255,0.5)', maxWidth: 600, mx: 'auto' }}>
                A complete test automation platform that grows with your team
              </Typography>
            </Box>
          </RevealSection>

          {detailedFeatures.map((feature, index) => (
            <FeatureRow key={index} feature={feature} index={index} reversed={index % 2 === 1} />
          ))}
        </Container>
      </Box>

      {/* Testimonials - Hidden for now */}
      {/*
      <Box sx={{ py: { xs: 10, md: 14 }, background: '#0a0a1a' }}>
        <Container maxWidth="lg">
          <RevealSection>
            <Box sx={{ textAlign: 'center', mb: 8 }}>
              <Chip label="Testimonials" sx={{ mb: 2, background: 'rgba(251,191,36,0.15)', color: '#fbbf24' }} />
              <Typography variant="h3" sx={{ color: 'white', fontWeight: 700, mb: 2, fontSize: { xs: '1.75rem', md: '2.5rem' } }}>
                Loved by QA Teams
              </Typography>
              <Typography variant="body1" sx={{ color: 'rgba(255,255,255,0.5)' }}>
                See what our users have to say about GhostQA
              </Typography>
            </Box>
          </RevealSection>

          <Grid container spacing={4}>
            {testimonials.map((testimonial, index) => (
              <Grid item xs={12} md={4} key={index}>
                <TestimonialCard testimonial={testimonial} index={index} />
              </Grid>
            ))}
          </Grid>
        </Container>
      </Box>
      */}

      {/* Pricing - Hidden for now */}
      {/*
      <Box sx={{ py: { xs: 10, md: 14 }, background: 'linear-gradient(180deg, #0f0f24 0%, #0a0a1a 100%)' }}>
        <Container maxWidth="lg">
          <RevealSection>
            <Box sx={{ textAlign: 'center', mb: 8 }}>
              <Chip label="Pricing" sx={{ mb: 2, background: 'rgba(102,126,234,0.15)', color: '#a5b4fc' }} />
              <Typography variant="h3" sx={{ color: 'white', fontWeight: 700, mb: 2, fontSize: { xs: '1.75rem', md: '2.5rem' } }}>
                Simple, Transparent Pricing
              </Typography>
              <Typography variant="body1" sx={{ color: 'rgba(255,255,255,0.5)' }}>
                Start free, upgrade when you're ready
              </Typography>
            </Box>
          </RevealSection>

          <Grid container spacing={4} justifyContent="center">
            {pricingPlans.map((plan, index) => (
              <Grid item xs={12} sm={6} md={4} key={index}>
                <PricingCard plan={plan} featured={index === 1} />
              </Grid>
            ))}
          </Grid>
        </Container>
      </Box>
      */}

      {/* FAQ */}
      <Box sx={{ py: { xs: 10, md: 14 }, background: '#0a0a1a' }}>
        <Container maxWidth="md">
          <RevealSection>
            <Box sx={{ textAlign: 'center', mb: 6 }}>
              <Typography variant="h3" sx={{ color: 'white', fontWeight: 700, mb: 2, fontSize: { xs: '1.75rem', md: '2.5rem' } }}>
                Frequently Asked Questions
              </Typography>
            </Box>
          </RevealSection>

          <StaggerReveal staggerDelay={0.1}>
            {faqs.map((faq, index) => (
              <Accordion
                key={index}
                disableGutters
                sx={{
                  mb: 2,
                  background: 'rgba(255,255,255,0.02)',
                  border: '1px solid rgba(255,255,255,0.06)',
                  borderRadius: '16px !important',
                  overflow: 'hidden',
                  transition: 'all 0.3s ease',
                  '&:before': { display: 'none' },
                  '&:hover': { background: 'rgba(255,255,255,0.04)', borderColor: 'rgba(102,126,234,0.2)' },
                  '&.Mui-expanded': { background: 'rgba(102,126,234,0.08)', borderColor: 'rgba(102,126,234,0.3)' },
                }}
              >
                <AccordionSummary expandIcon={<ExpandMore sx={{ color: 'rgba(255,255,255,0.5)' }} />} sx={{ px: 3, py: 1 }}>
                  <Typography sx={{ color: 'white', fontWeight: 500 }}>{faq.q}</Typography>
                </AccordionSummary>
                <AccordionDetails sx={{ px: 3, pb: 3, pt: 0 }}>
                  <Typography sx={{ color: 'rgba(255,255,255,0.65)', lineHeight: 1.8 }}>{faq.a}</Typography>
                </AccordionDetails>
              </Accordion>
            ))}
          </StaggerReveal>
        </Container>
      </Box>

      {/* Final CTA */}
      <Box
        sx={{
          py: { xs: 10, md: 14 },
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        <ParallaxSection speed={-0.2}>
          <Box sx={{ position: 'absolute', width: 500, height: 500, borderRadius: '50%', background: 'rgba(255,255,255,0.1)', left: '-15%', top: '-50%' }} />
        </ParallaxSection>
        <ParallaxSection speed={0.2}>
          <Box sx={{ position: 'absolute', width: 400, height: 400, borderRadius: '50%', background: 'rgba(255,255,255,0.05)', right: '-10%', bottom: '-40%' }} />
        </ParallaxSection>

        <Container maxWidth="md" sx={{ position: 'relative', textAlign: 'center' }}>
          <RevealSection>
            <Typography variant="h3" sx={{ color: 'white', fontWeight: 700, mb: 2, fontSize: { xs: '1.75rem', md: '2.5rem' } }}>
              Ready to Transform Your Testing?
            </Typography>
            <Typography variant="body1" sx={{ color: 'rgba(255,255,255,0.9)', mb: 4, maxWidth: 500, mx: 'auto' }}>
              Join thousands of QA teams generating better tests in less time. Start free today.
            </Typography>
            <MagneticButton strength={0.3}>
              <Button
                variant="contained"
                size="large"
                endIcon={<ArrowForward />}
                onClick={handleGetStarted}
                sx={{
                  py: 2,
                  px: 5,
                  fontSize: '1.1rem',
                  backgroundColor: 'white',
                  color: '#667eea',
                  fontWeight: 600,
                  boxShadow: '0 8px 30px rgba(0,0,0,0.2)',
                  '&:hover': { backgroundColor: '#f8f8f8', boxShadow: '0 12px 40px rgba(0,0,0,0.3)' },
                }}
              >
                Get Started Free
              </Button>
            </MagneticButton>
          </RevealSection>
        </Container>
      </Box>

      {/* Footer */}
      <Box sx={{ py: 6, background: '#050510', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
        <Container maxWidth="lg">
          <Grid container spacing={4} alignItems="center">
            <Grid item xs={12} md={4}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                <Avatar sx={{ width: 36, height: 36, background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
                  <BugReport sx={{ fontSize: 20 }} />
                </Avatar>
                <Typography variant="h6" sx={{ fontWeight: 700, color: 'white' }}>GhostQA</Typography>
              </Box>
              <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.4)', mt: 2, maxWidth: 300 }}>
                AI-powered test generation and execution platform. Transform requirements into tests instantly.
              </Typography>
            </Grid>

            <Grid item xs={12} md={4}>
              <Typography variant="subtitle2" sx={{ color: 'rgba(255,255,255,0.6)', mb: 2 }}>Stay Updated</Typography>
              <Box sx={{ display: 'flex', gap: 1 }}>
                <TextField
                  placeholder="Enter your email"
                  size="small"
                  sx={{
                    flex: 1,
                    '& .MuiOutlinedInput-root': {
                      background: 'rgba(255,255,255,0.05)',
                      borderRadius: 2,
                      color: 'white',
                      '& fieldset': { borderColor: 'rgba(255,255,255,0.1)' },
                      '&:hover fieldset': { borderColor: 'rgba(102,126,234,0.3)' },
                      '&.Mui-focused fieldset': { borderColor: '#667eea' },
                    },
                    '& .MuiInputBase-input::placeholder': { color: 'rgba(255,255,255,0.3)' },
                  }}
                />
                <MagneticButton strength={0.4}>
                  <IconButton
                    sx={{
                      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                      color: 'white',
                      borderRadius: 2,
                      '&:hover': { boxShadow: '0 4px 20px rgba(102,126,234,0.4)' },
                    }}
                  >
                    <Send sx={{ fontSize: 18 }} />
                  </IconButton>
                </MagneticButton>
              </Box>
            </Grid>

            <Grid item xs={12} md={4}>
              <Box sx={{ display: 'flex', gap: 2, justifyContent: { xs: 'flex-start', md: 'flex-end' } }}>
                <MagneticButton strength={0.5}>
                  <IconButton sx={{ color: 'rgba(255,255,255,0.4)', '&:hover': { color: 'white' } }}>
                    <GitHub />
                  </IconButton>
                </MagneticButton>
              </Box>
            </Grid>
          </Grid>

          <Box sx={{ mt: 6, pt: 4, borderTop: '1px solid rgba(255,255,255,0.05)', display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 2 }}>
            <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.3)' }}>
              {new Date().getFullYear()} GhostQA. All rights reserved.
            </Typography>
            <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.3)' }}>
              Powered by Claude AI & Ollama
            </Typography>
          </Box>
        </Container>
      </Box>
    </Box>
  );
}
