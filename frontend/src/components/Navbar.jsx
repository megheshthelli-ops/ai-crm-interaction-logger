import React from 'react';
import { AppBar, Toolbar, Typography, Box, Button } from '@mui/material';
import HealthAndSafetyIcon from '@mui/icons-material/HealthAndSafety';

const Navbar = ({ onNavigate = null }) => {
  return (
    <AppBar
      position="static"
      sx={{
        background: 'linear-gradient(135deg, #1976d2 0%, #1565c0 100%)',
        boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
      }}
    >
      <Toolbar sx={{ justifyContent: 'space-between' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <HealthAndSafetyIcon sx={{ fontSize: 28 }} />
          <Typography
            variant="h6"
            sx={{
              fontWeight: 700,
              letterSpacing: '0.5px',
              fontFamily: 'Inter, sans-serif',
            }}
          >
            HCP CRM Module
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            color="inherit"
            onClick={() => onNavigate && onNavigate('dashboard')}
            sx={{
              fontSize: '14px',
              fontFamily: 'Inter, sans-serif',
              '&:hover': { backgroundColor: 'rgba(255,255,255,0.1)' },
            }}
          >
            Dashboard
          </Button>
          <Button
            color="inherit"
            onClick={() => onNavigate && onNavigate('history')}
            sx={{
              fontSize: '14px',
              fontFamily: 'Inter, sans-serif',
              '&:hover': { backgroundColor: 'rgba(255,255,255,0.1)' },
            }}
          >
            History
          </Button>
          <Button
            color="inherit"
            onClick={() => onNavigate && onNavigate('chat')}
            sx={{
              fontSize: '14px',
              fontFamily: 'Inter, sans-serif',
              '&:hover': { backgroundColor: 'rgba(255,255,255,0.1)' },
            }}
          >
            AI Chat
          </Button>
        </Box>
      </Toolbar>
    </AppBar>
  );
};

export default Navbar;