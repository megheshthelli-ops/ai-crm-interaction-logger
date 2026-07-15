import React, { useState } from 'react';
import { Provider, useDispatch, useSelector } from 'react-redux';
import {
  Box,
  Snackbar,
  Alert,
} from '@mui/material';
import store from './store';
import InteractionForm from './components/InteractionForm';
import AIChat from './components/AIChat';
import { setSelectedHCP } from './store/slices/hcpSlice';
import './App.css';

function AppContent() {
  const dispatch = useDispatch();
  const selectedHCP = useSelector((state) => state.hcps.selectedHCP);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });

  const showSuccess = (message) => {
    setSnackbar({ open: true, message, severity: 'success' });
  };

  const handleInteractionLogged = (interaction) => {
    if (interaction?.hcp_id) {
      dispatch(setSelectedHCP({ id: interaction.hcp_id }));
    }
    showSuccess('Interaction logged successfully!');
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', backgroundColor: '#f0f2f5' }}>
      <Box
        className="main-content-wrapper"
        sx={{
          display: 'flex',
          gap: 3,
          p: 3,
          maxWidth: '1400px',
          margin: '0 auto',
          width: '100%',
          minHeight: 'calc(100vh - 32px)',
          boxSizing: 'border-box',
        }}
      >
        {/* Left Column - Form (72%) */}
        <Box className="left-column" sx={{ flex: '0 0 72%', maxWidth: '72%' }}>
          <InteractionForm
            hcpId={selectedHCP?.id || null}
            onSuccess={handleInteractionLogged}
          />
        </Box>

        {/* Right Column - AI Assistant (28%) */}
        <Box className="right-column" sx={{ flex: '0 0 28%', maxWidth: '28%' }}>
          <AIChat
            onInteractionCreated={() => {
              showSuccess('Interaction processed via chat!');
            }}
          />
        </Box>
      </Box>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={() => setSnackbar((prev) => ({ ...prev, open: false }))}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert severity={snackbar.severity} sx={{ width: '100%' }}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}

function App() {
  return (
    <Provider store={store}>
      <AppContent />
    </Provider>
  );
}

export default App;