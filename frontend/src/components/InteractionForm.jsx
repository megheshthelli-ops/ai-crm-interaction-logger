import React, { useEffect, useState, useCallback } from 'react';
import {
  Box,
  Button,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Paper,
  Typography,
  CircularProgress,
  Alert,
  Snackbar,
  Chip,
  RadioGroup,
  Radio,
  FormControlLabel,
  FormLabel,
  Divider,
  Collapse,
  IconButton,
} from '@mui/material';
import { useDispatch, useSelector } from 'react-redux';
import { interactionsAPI, hcpAPI } from '../services/api';
import {
  addInteraction,
  setError as setStoreError,
} from '../store/slices/interactionSlice';
import {
  clearExtractedData,
  applyExtractedData,
} from '../store/slices/formDataSlice';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import KeyboardVoiceIcon from '@mui/icons-material/KeyboardVoice';
import AddCircleOutlinedIcon from '@mui/icons-material/AddCircleOutlined';

const InteractionForm = ({ hcpId = null, onSuccess = null }) => {
  const dispatch = useDispatch();
  const extractedData = useSelector((state) => state.formData.extractedData);
  const pendingExtraction = useSelector((state) => state.formData.pendingExtraction);
  const [loading, setLoading] = useState(false);
  const [error, setErrorLocal] = useState(null);
  const [hcps, setHcps] = useState([]);
  const [hcpLoading, setHcpLoading] = useState(false);
  const [hcpError, setHcpError] = useState(null);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });
  const [voiceNoteOpen, setVoiceNoteOpen] = useState(false);
  const [sentiment, setSentiment] = useState('');

  const [formData, setFormData] = useState({
    hcp_id: hcpId || '',
    interaction_type: 'Meeting',
    date: new Date().toISOString().split('T')[0],
    time: '09:00',
    attendees: '',
    topics_discussed: '',
    voice_note: '',
    materials_shared: '',
    sentiment: '',
    outcomes: '',
    follow_up_actions: '',
    ai_suggested_followups: '',
  });

  // Track previously set fields for AI editing (don't overwrite if already set)
  const [aiSetFields, setAiSetFields] = useState(new Set());

  useEffect(() => {
    const loadHcps = async () => {
      setHcpLoading(true);
      setHcpError(null);
      try {
        const response = await hcpAPI.listHCPs();
        setHcps(response.data);
      } catch (err) {
        setHcpError(
          err.response?.data?.detail || err.message || 'Unable to load HCP list'
        );
      } finally {
        setHcpLoading(false);
      }
    };
    loadHcps();
  }, []);

  useEffect(() => {
    if (hcpId) {
      setFormData((prev) => ({ ...prev, hcp_id: hcpId }));
    }
  }, [hcpId]);

  // Auto-populate form from AI-extracted data
  useEffect(() => {
    if (pendingExtraction && extractedData) {
      const updates = {};
      const newAiFields = new Set();
      
      if (extractedData.date) { updates.date = extractedData.date; newAiFields.add('date'); }
      if (extractedData.time) { updates.time = extractedData.time; newAiFields.add('time'); }
      if (extractedData.attendees) { updates.attendees = extractedData.attendees; newAiFields.add('attendees'); }
      if (extractedData.topics_discussed) { updates.topics_discussed = extractedData.topics_discussed; newAiFields.add('topics_discussed'); }
      if (extractedData.outcomes) { updates.outcomes = extractedData.outcomes; newAiFields.add('outcomes'); }
      if (extractedData.follow_up_actions) { updates.follow_up_actions = extractedData.follow_up_actions; newAiFields.add('follow_up_actions'); }
      if (extractedData.interaction_type) { updates.interaction_type = extractedData.interaction_type; newAiFields.add('interaction_type'); }
      
      if (extractedData.sentiment) {
        setSentiment(extractedData.sentiment);
        updates.sentiment = extractedData.sentiment;
        newAiFields.add('sentiment');
      }

      if (extractedData.ai_summary) {
        updates.ai_suggested_followups = extractedData.ai_summary;
        newAiFields.add('ai_suggested_followups');
      }
      
      // Find HCP from name only if not already selected
      if (extractedData.hcp_name && !hcpId) {
        const hcpNameLower = extractedData.hcp_name.toLowerCase();
        const matched = hcps.find(h => 
          h.name.toLowerCase().includes(hcpNameLower) || 
          hcpNameLower.includes(h.name.toLowerCase())
        );
        if (matched) {
          updates.hcp_id = matched.id;
          newAiFields.add('hcp_id');
        }
      }
      
      setFormData((prev) => ({ ...prev, ...updates }));
      setAiSetFields(newAiFields);
      dispatch(applyExtractedData());
    }
  }, [pendingExtraction, extractedData, hcps, hcpId, dispatch]);

  // AI Editing: if new extraction comes in but some fields already set by previous AI,
  // only update fields that the new message explicitly mentions
  useEffect(() => {
    if (!pendingExtraction && extractedData && extractedData.lastExtractedMessage) {
      // Check if this is an edit request
      const msg = (extractedData.lastExtractedMessage || '').toLowerCase();
      if (msg.includes('change') || msg.includes('update') || msg.includes('edit') || 
          msg.includes('actually') || msg.includes('instead')) {
        // Only update specific fields mentioned in the edit message
        // The form will NOT be fully overwritten - it's handled above
      }
    }
  }, [extractedData]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    // Clear AI flag when user manually edits
    setAiSetFields((prev) => {
      const updated = new Set(prev);
      updated.delete(name);
      return updated;
    });
  };

  const handleSentimentChange = (e) => {
    const value = e.target.value;
    setSentiment(value);
    setFormData((prev) => ({ ...prev, sentiment: value }));
    setAiSetFields((prev) => {
      const updated = new Set(prev);
      updated.delete('sentiment');
      return updated;
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setErrorLocal(null);

    try {
      const submitData = {
        ...formData,
        date: new Date(formData.date).toISOString(),
        hcp_id: parseInt(formData.hcp_id),
      };

      const response = await interactionsAPI.logInteraction(submitData);
      dispatch(addInteraction(response.data));
      setErrorLocal(null);

      setFormData({
        hcp_id: hcpId || '',
        interaction_type: 'Meeting',
        date: new Date().toISOString().split('T')[0],
        time: '09:00',
        attendees: '',
        topics_discussed: '',
        voice_note: '',
        materials_shared: '',
        sentiment: '',
        outcomes: '',
        follow_up_actions: '',
        ai_suggested_followups: '',
      });
      setSentiment('');
      setAiSetFields(new Set());

      setSnackbar({ open: true, message: 'Interaction logged successfully!', severity: 'success' });

      if (onSuccess) {
        onSuccess(response.data);
      }
    } catch (err) {
      const errorMessage =
        err.response?.data?.detail || err.message || 'Failed to log interaction';
      setErrorLocal(errorMessage);
      dispatch(setStoreError(errorMessage));
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setFormData({
      hcp_id: hcpId || '',
      interaction_type: 'Meeting',
      date: new Date().toISOString().split('T')[0],
      time: '09:00',
      attendees: '',
      topics_discussed: '',
      voice_note: '',
      materials_shared: '',
      sentiment: '',
      outcomes: '',
      follow_up_actions: '',
      ai_suggested_followups: '',
    });
    setSentiment('');
    setAiSetFields(new Set());
    setErrorLocal(null);
  };

  return (
    <Paper
      elevation={0}
      sx={{
        borderRadius: '12px',
        border: '1px solid #e0e0e0',
        backgroundColor: '#ffffff',
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <Box sx={{ px: 4, pt: 3, pb: 2 }}>
        <Typography
          sx={{
            fontWeight: 700,
            fontSize: '22px',
            color: '#1a1a2e',
            letterSpacing: '-0.3px',
            fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
          }}
        >
          Log HCP Interaction
        </Typography>
        <Typography
          sx={{
            color: '#888',
            fontSize: '13px',
            mt: 0.5,
            fontWeight: 400,
            fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
          }}
        >
          Record details of your interaction with the Healthcare Professional
        </Typography>
      </Box>

      <Divider sx={{ borderColor: '#e8e8e8' }} />

      {error && (
        <Alert severity="error" sx={{ mx: 4, mt: 2 }} onClose={() => setErrorLocal(null)}>
          {error}
        </Alert>
      )}

      {/* AI Auto-Population Banner */}
      {extractedData && !pendingExtraction && aiSetFields.size > 0 && (
        <Box
          sx={{
            mx: 4,
            mt: 2,
            p: 1.5,
            borderRadius: '8px',
            backgroundColor: '#e8f5e9',
            border: '1px solid #a5d6a7',
            display: 'flex',
            alignItems: 'center',
            gap: 1,
          }}
        >
          <Typography sx={{ fontSize: '12px', color: '#2e7d32', fontWeight: 500, fontFamily: 'inherit' }}>
            ✓ AI filled {aiSetFields.size} field{aiSetFields.size !== 1 ? 's' : ''}
          </Typography>
        </Box>
      )}

      <Box component="form" onSubmit={handleSubmit} sx={{ px: 4, py: 3 }}>
        {/* 1. HCP Name */}
        <FormControl fullWidth sx={{ mb: 2.5 }}>
          <InputLabel sx={{ fontSize: '14px', color: '#555', '&.Mui-focused': { color: '#1976d2' }, fontFamily: 'inherit' }}>
            HCP Name
          </InputLabel>
          <Select
            name="hcp_id"
            value={formData.hcp_id}
            onChange={handleChange}
            required
            label="HCP Name"
            sx={{
              borderRadius: '8px',
              height: '44px',
              fontSize: '14px',
              fontFamily: 'inherit',
              '& .MuiOutlinedInput-notchedOutline': { borderColor: '#d0d0d0' },
              '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: '#1976d2' },
            }}
          >
            <MenuItem value="">
              <em style={{ color: '#999' }}>Select HCP</em>
            </MenuItem>
            {hcpLoading ? (
              <MenuItem disabled>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <CircularProgress size={16} /> Loading...
                </Box>
              </MenuItem>
            ) : hcps.length > 0 ? (
              hcps.map((hcp) => (
                <MenuItem key={hcp.id} value={hcp.id}>
                  {hcp.name} — {hcp.specialty}
                </MenuItem>
              ))
            ) : (
              <MenuItem disabled>
                {hcpError || 'No HCPs available.'}
              </MenuItem>
            )}
          </Select>
        </FormControl>

        {/* 2. Interaction Type */}
        <FormControl fullWidth sx={{ mb: 2.5 }}>
          <InputLabel sx={{ fontSize: '14px', color: '#555', '&.Mui-focused': { color: '#1976d2' }, fontFamily: 'inherit' }}>
            Interaction Type
          </InputLabel>
          <Select
            name="interaction_type"
            value={formData.interaction_type}
            onChange={handleChange}
            label="Interaction Type"
            sx={{
              borderRadius: '8px',
              height: '44px',
              fontSize: '14px',
              fontFamily: 'inherit',
              '& .MuiOutlinedInput-notchedOutline': { borderColor: '#d0d0d0' },
              '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: '#1976d2' },
            }}
          >
            <MenuItem value="Meeting">Meeting</MenuItem>
            <MenuItem value="Call">Call</MenuItem>
            <MenuItem value="Email">Email</MenuItem>
            <MenuItem value="Conference">Conference</MenuItem>
            <MenuItem value="Other">Other</MenuItem>
          </Select>
        </FormControl>

        {/* 3. Date */}
        <TextField
          label="Date"
          name="date"
          type="date"
          value={formData.date}
          onChange={handleChange}
          InputLabelProps={{ shrink: true, sx: { color: '#555', '&.Mui-focused': { color: '#1976d2' }, fontFamily: 'inherit' } }}
          fullWidth
          required
          sx={{ mb: 2.5,
            '& .MuiOutlinedInput-root': {
              borderRadius: '8px', height: '44px', fontSize: '14px', fontFamily: 'inherit',
              '& fieldset': { borderColor: '#d0d0d0' },
              '&:hover fieldset': { borderColor: '#1976d2' },
            },
          }}
        />

        {/* 4. Time */}
        <TextField
          label="Time"
          name="time"
          type="time"
          value={formData.time}
          onChange={handleChange}
          InputLabelProps={{ shrink: true, sx: { color: '#555', '&.Mui-focused': { color: '#1976d2' }, fontFamily: 'inherit' } }}
          fullWidth
          required
          sx={{ mb: 2.5,
            '& .MuiOutlinedInput-root': {
              borderRadius: '8px', height: '44px', fontSize: '14px', fontFamily: 'inherit',
              '& fieldset': { borderColor: '#d0d0d0' },
              '&:hover fieldset': { borderColor: '#1976d2' },
            },
          }}
        />

        {/* 5. Attendees */}
        <TextField
          label="Attendees"
          name="attendees"
          value={formData.attendees}
          onChange={handleChange}
          placeholder="Enter names separated by commas..."
          fullWidth
          sx={{ mb: 2.5 }}
          required
          InputLabelProps={{ sx: { color: '#555', '&.Mui-focused': { color: '#1976d2' }, fontFamily: 'inherit' } }}
          InputProps={{
            sx: {
              borderRadius: '8px', height: '44px', fontSize: '14px', fontFamily: 'inherit',
              '& fieldset': { borderColor: '#d0d0d0' },
              '&:hover fieldset': { borderColor: '#1976d2' },
            },
          }}
        />

        {/* 6. Topics Discussed */}
        <Typography
          sx={{
            fontSize: '13px', fontWeight: 600, color: '#444', mb: 1,
            fontFamily: 'inherit',
          }}
        >
          Topics Discussed
        </Typography>
        <TextField
          name="topics_discussed"
          value={formData.topics_discussed}
          onChange={handleChange}
          placeholder="Enter key discussion points..."
          fullWidth
          multiline
          minRows={3}
          required
          sx={{ mb: 2.5 }}
          InputProps={{
            sx: {
              borderRadius: '8px', fontSize: '14px', fontFamily: 'inherit',
              '& fieldset': { borderColor: '#d0d0d0' },
              '&:hover fieldset': { borderColor: '#1976d2' },
            },
          }}
        />

        {/* 7. Summarize from Voice Note */}
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            cursor: 'pointer',
            mb: 1,
          }}
          onClick={() => setVoiceNoteOpen(!voiceNoteOpen)}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <KeyboardVoiceIcon sx={{ fontSize: 20, color: '#1976d2' }} />
            <Typography
              sx={{
                fontSize: '13px', fontWeight: 600, color: '#444',
                fontFamily: 'inherit',
              }}
            >
              Summarize from Voice Note <span style={{ fontWeight: 400, fontSize: '11px', color: '#999' }}>(Requires Consent)</span>
            </Typography>
          </Box>
          <IconButton size="small" sx={{ color: '#888' }}>
            {voiceNoteOpen ? <ExpandLessIcon /> : <ExpandMoreIcon />}
          </IconButton>
        </Box>
        <Collapse in={voiceNoteOpen}>
          <TextField
            name="voice_note"
            value={formData.voice_note}
            onChange={handleChange}
            placeholder="Paste or type voice note transcription here for AI summarization..."
            fullWidth
            multiline
            minRows={3}
            sx={{ mb: 2.5 }}
            InputProps={{
              sx: {
                borderRadius: '8px', fontSize: '14px', fontFamily: 'inherit',
                backgroundColor: '#fafafa',
                '& fieldset': { borderColor: '#d0d0d0' },
                '&:hover fieldset': { borderColor: '#1976d2' },
              },
            }}
          />
        </Collapse>

        {/* 8. Materials Shared / Samples Distributed */}
        <Typography
          sx={{
            fontSize: '13px', fontWeight: 600, color: '#444', mb: 1,
            fontFamily: 'inherit',
          }}
        >
          Materials Shared / Samples Distributed
        </Typography>
        <TextField
          name="materials_shared"
          value={formData.materials_shared}
          onChange={handleChange}
          placeholder="List any materials, brochures, or samples provided..."
          fullWidth
          multiline
          minRows={2}
          sx={{ mb: 1.5 }}
          InputProps={{
            sx: {
              borderRadius: '8px', fontSize: '14px', fontFamily: 'inherit',
              '& fieldset': { borderColor: '#d0d0d0' },
              '&:hover fieldset': { borderColor: '#1976d2' },
            },
          }}
        />
        <Box sx={{ display: 'flex', gap: 1, mb: 2.5 }}>
          <Button
            variant="outlined"
            size="small"
            startIcon={<AddCircleOutlinedIcon />}
            sx={{
              borderRadius: '8px', height: '36px', fontSize: '12px', textTransform: 'none',
              fontFamily: 'inherit', borderColor: '#d0d0d0', color: '#555',
              '&:hover': { borderColor: '#1976d2', bgcolor: '#f0f7ff' },
            }}
          >
            Search/Add Material
          </Button>
          <Button
            variant="outlined"
            size="small"
            startIcon={<AddCircleOutlinedIcon />}
            sx={{
              borderRadius: '8px', height: '36px', fontSize: '12px', textTransform: 'none',
              fontFamily: 'inherit', borderColor: '#d0d0d0', color: '#555',
              '&:hover': { borderColor: '#1976d2', bgcolor: '#f0f7ff' },
            }}
          >
            Add Sample
          </Button>
        </Box>

        <Divider sx={{ mb: 2.5, borderColor: '#e8e8e8' }} />

        {/* 9. Observed / Inferred HCP Sentiment */}
        <Box sx={{ mb: 2.5 }}>
          <FormLabel
            component="legend"
            sx={{
              fontSize: '13px', fontWeight: 600, color: '#444', mb: 1,
              fontFamily: 'inherit',
            }}
          >
            Observed / Inferred HCP Sentiment
          </FormLabel>
          <RadioGroup row value={sentiment} onChange={handleSentimentChange}>
            <FormControlLabel
              value="Positive"
              control={<Radio sx={{ color: '#4caf50', '&.Mui-checked': { color: '#4caf50' }, '& .MuiSvgIcon-root': { fontSize: 20 } }} />}
              label={<Typography sx={{ fontSize: '13px', color: '#555', fontFamily: 'inherit' }}>Positive</Typography>}
            />
            <FormControlLabel
              value="Neutral"
              control={<Radio sx={{ color: '#ff9800', '&.Mui-checked': { color: '#ff9800' }, '& .MuiSvgIcon-root': { fontSize: 20 } }} />}
              label={<Typography sx={{ fontSize: '13px', color: '#555', fontFamily: 'inherit' }}>Neutral</Typography>}
            />
            <FormControlLabel
              value="Negative"
              control={<Radio sx={{ color: '#f44336', '&.Mui-checked': { color: '#f44336' }, '& .MuiSvgIcon-root': { fontSize: 20 } }} />}
              label={<Typography sx={{ fontSize: '13px', color: '#555', fontFamily: 'inherit' }}>Negative</Typography>}
            />
          </RadioGroup>
        </Box>

        <Divider sx={{ mb: 2.5, borderColor: '#e8e8e8' }} />

        {/* 10. Outcomes */}
        <Typography
          sx={{
            fontSize: '13px', fontWeight: 600, color: '#444', mb: 1,
            fontFamily: 'inherit',
          }}
        >
          Outcomes
        </Typography>
        <TextField
          name="outcomes"
          value={formData.outcomes}
          onChange={handleChange}
          placeholder="Document outcomes and agreements from the interaction..."
          fullWidth
          multiline
          minRows={2}
          sx={{ mb: 2.5 }}
          InputProps={{
            sx: {
              borderRadius: '8px', fontSize: '14px', fontFamily: 'inherit',
              '& fieldset': { borderColor: '#d0d0d0' },
              '&:hover fieldset': { borderColor: '#1976d2' },
            },
          }}
        />

        {/* 11. Follow-up Actions */}
        <Typography
          sx={{
            fontSize: '13px', fontWeight: 600, color: '#444', mb: 1,
            fontFamily: 'inherit',
          }}
        >
          Follow-up Actions
        </Typography>
        <TextField
          name="follow_up_actions"
          value={formData.follow_up_actions}
          onChange={handleChange}
          placeholder="List next steps and follow-up actions..."
          fullWidth
          multiline
          minRows={2}
          sx={{ mb: 2.5 }}
          InputProps={{
            sx: {
              borderRadius: '8px', fontSize: '14px', fontFamily: 'inherit',
              '& fieldset': { borderColor: '#d0d0d0' },
              '&:hover fieldset': { borderColor: '#1976d2' },
            },
          }}
        />

        <Divider sx={{ mb: 2.5, borderColor: '#e8e8e8' }} />

        {/* 12. AI Suggested Follow-ups */}
        <Typography
          sx={{
            fontSize: '13px', fontWeight: 600, color: '#444', mb: 1,
            fontFamily: 'inherit',
          }}
        >
          AI Suggested Follow-ups
        </Typography>
        <TextField
          name="ai_suggested_followups"
          value={formData.ai_suggested_followups}
          onChange={handleChange}
          placeholder="AI-generated follow-up suggestions will appear here..."
          fullWidth
          multiline
          minRows={3}
          sx={{ mb: 3 }}
          InputProps={{
            sx: {
              borderRadius: '8px', fontSize: '14px', fontFamily: 'inherit',
              backgroundColor: '#f7f9fc',
              '& fieldset': { borderColor: '#d0d0d0', borderStyle: 'dashed' },
              '&:hover fieldset': { borderColor: '#1976d2' },
            },
          }}
        />

        {/* Action Buttons */}
        <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end', pt: 1 }}>
          <Button
            variant="outlined"
            onClick={resetForm}
            disabled={loading}
            sx={{
              borderRadius: '8px', height: '40px', px: 3, fontSize: '13px', fontWeight: 500,
              textTransform: 'none', fontFamily: 'inherit',
              borderColor: '#d0d0d0', color: '#666',
              '&:hover': { borderColor: '#999', backgroundColor: '#f5f5f5' },
            }}
          >
            Clear
          </Button>
          <Button
            variant="contained"
            type="submit"
            disabled={loading}
            sx={{
              borderRadius: '8px', height: '40px', px: 4, fontSize: '13px', fontWeight: 500,
              textTransform: 'none', fontFamily: 'inherit',
              backgroundColor: '#1976d2',
              boxShadow: '0 2px 6px rgba(25, 118, 210, 0.3)',
              '&:hover': {
                backgroundColor: '#1565c0',
                boxShadow: '0 4px 12px rgba(25, 118, 210, 0.4)',
              },
            }}
          >
            {loading ? <CircularProgress size={20} sx={{ color: '#fff' }} /> : 'Log Interaction'}
          </Button>
        </Box>
      </Box>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={3000}
        onClose={() => setSnackbar((prev) => ({ ...prev, open: false }))}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert severity={snackbar.severity} sx={{ width: '100%' }}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Paper>
  );
};

export default InteractionForm;