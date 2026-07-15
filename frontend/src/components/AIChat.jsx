import React, { useState, useRef, useEffect } from 'react';
import {
  Box,
  Paper,
  TextField,
  Button,
  Typography,
  CircularProgress,
  Alert,
  Divider,
  InputAdornment,
  IconButton,
} from '@mui/material';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import SendIcon from '@mui/icons-material/Send';
import SmartToyOutlinedIcon from '@mui/icons-material/SmartToyOutlined';
import PersonOutlineOutlinedIcon from '@mui/icons-material/PersonOutlineOutlined';
import { useDispatch, useSelector } from 'react-redux';
import { interactionsAPI, extractionAPI } from '../services/api';
import {
  addMessage,
  setLoading,
  setError,
} from '../store/slices/chatSlice';
import {
  setExtractedData,
  setExtractionLoading,
  setExtractionError,
  setLastExtractedMessage,
  setSuggestedTools,
} from '../store/slices/formDataSlice';

const AIChat = ({ interactionData = null, onInteractionCreated = null }) => {
  const dispatch = useDispatch();
  const { messages, loading, error } = useSelector(
    (state) => state.chat
  );
  const selectedHCP = useSelector((state) => state.hcps.selectedHCP);
  const [inputMessage, setInputMessage] = useState('');
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!inputMessage.trim() || loading) return;

    const messageText = inputMessage.trim();
    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: messageText,
      timestamp: new Date(),
    };

    dispatch(addMessage(userMessage));
    setInputMessage('');
    dispatch(setLoading(true));

    try {
      // Step 1: Extract structured data for auto-population
      dispatch(setExtractionLoading(true));
      const hcpContext = selectedHCP ? {
        id: selectedHCP.id,
        name: selectedHCP.name,
      } : null;

      const extractionResponse = await extractionAPI.extractFormData(
        messageText,
        hcpContext
      );

      const extracted = extractionResponse.data;

      // Store extraction in Redux for form auto-population
      if (extracted && (extracted.hcp_name || extracted.topics_discussed)) {
        dispatch(setLastExtractedMessage(messageText));
        dispatch(setExtractedData(extracted));
        dispatch(setSuggestedTools(extracted.suggested_tools || []));
      }

      // Step 2: Send to chat agent for response
      const response = await interactionsAPI.chat(
        messageText,
        interactionData
      );

      const aiMessage = {
        id: Date.now() + 1,
        type: 'ai',
        content: response.data.response,
        timestamp: new Date(),
        tools: response.data.suggested_tools || [],
      };

      dispatch(addMessage(aiMessage));

      if (response.data.interaction_id && onInteractionCreated) {
        onInteractionCreated(response.data.interaction_id);
      }
    } catch (err) {
      const errorMessage =
        err.response?.data?.detail || err.message || 'Failed to send message';
      dispatch(setExtractionError(errorMessage));
      dispatch(setError(errorMessage));

      dispatch(addMessage({
        id: Date.now() + 1,
        type: 'error',
        content: errorMessage,
        timestamp: new Date(),
      }));
    } finally {
      dispatch(setLoading(false));
    }
  };

  const handleExampleClick = (example) => {
    setInputMessage(example);
    if (inputRef.current) {
      inputRef.current.focus();
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage(e);
    }
  };

  const examplePrompts = [
    "Met with Dr. Smith today. Discussed the new cardiac drug. He was interested but wants to see more clinical data.",
    "Called Dr. Johnson's office. Spoke with the nurse about scheduling a follow-up for the diabetes medication trial.",
  ];

  return (
    <Paper
      elevation={0}
      sx={{
        borderRadius: '12px',
        border: '1px solid #e0e0e0',
        backgroundColor: '#ffffff',
        overflow: 'hidden',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      }}
    >
      {/* Header */}
      <Box
        sx={{
          px: 3,
          pt: 2.5,
          pb: 2,
          background: '#1976d2',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 0.5 }}>
          <AutoAwesomeIcon sx={{ fontSize: 20, color: '#fff' }} />
          <Typography
            sx={{
              fontWeight: 700,
              fontSize: '16px',
              color: '#ffffff',
              letterSpacing: '-0.2px',
              fontFamily: 'inherit',
            }}
          >
            AI Assistant
          </Typography>
        </Box>
        <Typography
          sx={{
            color: 'rgba(255,255,255,0.8)',
            fontSize: '12px',
            fontWeight: 400,
            ml: 4.5,
            fontFamily: 'inherit',
          }}
        >
          Log interaction via chat
        </Typography>
      </Box>

      <Divider />

      {/* Content Area */}
      <Box
        sx={{
          flex: 1,
          overflow: 'auto',
          display: 'flex',
          flexDirection: 'column',
          bgcolor: '#f7f8fa',
        }}
      >
        {/* Only show examples + tip when no messages */}
        {messages.length === 0 && (
          <Box sx={{ p: 2.5, display: 'flex', flexDirection: 'column', gap: 2 }}>
            {/* Example Prompts */}
            <Box>
              <Typography
                sx={{
                  fontSize: '10px',
                  fontWeight: 600,
                  color: '#999',
                  textTransform: 'uppercase',
                  letterSpacing: '0.8px',
                  mb: 1.5,
                  fontFamily: 'inherit',
                }}
              >
                Try an example
              </Typography>

              {examplePrompts.map((example, idx) => (
                <Box
                  key={idx}
                  onClick={() => handleExampleClick(example)}
                  sx={{
                    p: 1.5,
                    mb: 1,
                    borderRadius: '8px',
                    border: '1px solid #e8e8e8',
                    bgcolor: '#fff',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                    '&:hover': {
                      borderColor: '#1976d2',
                      bgcolor: '#f0f7ff',
                    },
                  }}
                >
                  <Typography
                    sx={{
                      fontSize: '12px',
                      color: '#555',
                      lineHeight: 1.5,
                      fontFamily: 'inherit',
                    }}
                  >
                    "{example}"
                  </Typography>
                </Box>
              ))}
            </Box>

            {/* Tip */}
            <Box
              sx={{
                p: 1.5,
                borderRadius: '8px',
                bgcolor: '#f0f7ff',
                border: '1px solid #d0e4f7',
              }}
            >
              <Typography
                sx={{
                  fontSize: '11px',
                  color: '#1976d2',
                  lineHeight: 1.5,
                  fontFamily: 'inherit',
                }}
              >
                <strong>💡 Tip:</strong> Describe your interaction naturally and the AI will help structure and log it automatically.
              </Typography>
            </Box>
          </Box>
        )}

        {/* Chat Messages */}
        <Box sx={{ p: 2.5, display: 'flex', flexDirection: 'column', gap: 2 }}>
          {messages.map((msg) => (
            <Box
              key={msg.id}
              sx={{
                display: 'flex',
                gap: 1.5,
                alignItems: 'flex-start',
              }}
            >
              {msg.type === 'ai' ? (
                <SmartToyOutlinedIcon sx={{ fontSize: 20, color: '#1976d2', mt: 0.3, flexShrink: 0 }} />
              ) : (
                <PersonOutlineOutlinedIcon sx={{ fontSize: 20, color: '#666', mt: 0.3, flexShrink: 0 }} />
              )}
              <Box
                sx={{
                  flex: 1,
                  p: 1.5,
                  borderRadius: '8px',
                  bgcolor: msg.type === 'ai' ? '#fff' : '#e3f2fd',
                  border: msg.type === 'ai' ? '1px solid #e8e8e8' : 'none',
                  fontSize: '13px',
                  color: '#333',
                  lineHeight: 1.5,
                  fontFamily: 'inherit',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                }}
              >
                {msg.content}
              </Box>
            </Box>
          ))}
        </Box>

        {error && (
          <Box sx={{ px: 2.5, pb: 1 }}>
            <Alert severity="error" sx={{ fontSize: '12px', py: 0 }}>
              {error}
            </Alert>
          </Box>
        )}

        {loading && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, justifyContent: 'center', py: 1 }}>
            <CircularProgress size={16} sx={{ color: '#1976d2' }} />
            <Typography sx={{ color: '#1976d2', fontSize: '12px', fontFamily: 'inherit' }}>
              Processing...
            </Typography>
          </Box>
        )}

        <div ref={messagesEndRef} />
      </Box>

      {/* Input Area */}
      <Box
        component="form"
        onSubmit={handleSendMessage}
        sx={{
          p: 2,
          borderTop: '1px solid #e8e8e8',
          bgcolor: '#fff',
        }}
      >
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-end' }}>
          <TextField
            fullWidth
            size="small"
            placeholder="Describe your HCP interaction..."
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
            multiline
            maxRows={3}
            inputRef={inputRef}
            sx={{
              '& .MuiOutlinedInput-root': {
                borderRadius: '8px',
                fontSize: '13px',
                bgcolor: '#f7f8fa',
                fontFamily: 'inherit',
                '& fieldset': { borderColor: '#d0d0d0' },
                '&:hover fieldset': { borderColor: '#1976d2' },
                '&.Mui-focused fieldset': { borderColor: '#1976d2' },
              },
            }}
          />
          <Button
            variant="contained"
            type="submit"
            disabled={loading || !inputMessage.trim()}
            sx={{
              borderRadius: '8px',
              minWidth: '44px',
              height: '40px',
              width: '44px',
              p: 0,
              bgcolor: '#1976d2',
              '&:hover': { bgcolor: '#1565c0' },
              '&.Mui-disabled': { bgcolor: '#e0e0e0' },
            }}
          >
            {loading ? (
              <CircularProgress size={18} sx={{ color: '#fff' }} />
            ) : (
              <SendIcon sx={{ fontSize: 18 }} />
            )}
          </Button>
        </Box>
      </Box>
    </Paper>
  );
};

export default AIChat;