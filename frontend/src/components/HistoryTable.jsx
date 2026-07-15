import React, { useState, useEffect } from 'react';
import {
  Box,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Button,
  Chip,
  Typography,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Alert,
  Snackbar,
} from '@mui/material';
import { useDispatch, useSelector } from 'react-redux';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import RefreshIcon from '@mui/icons-material/Refresh';
import { interactionsAPI } from '../services/api';
import {
  setLoading,
  setInteractions,
  setError,
  updateInteraction,
} from '../store/slices/interactionSlice';

const HistoryTable = ({ hcpId = null }) => {
  const dispatch = useDispatch();
  const { interactions, loading, error } = useSelector(
    (state) => state.interactions
  );
  const [selectedInteraction, setSelectedInteraction] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [openDialog, setOpenDialog] = useState(false);
  const [saving, setSaving] = useState(false);
  const [dialogError, setDialogError] = useState(null);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });
  const [hcpCache, setHcpCache] = useState({});

  useEffect(() => {
    loadInteractions();
  }, [hcpId]);

  const getHcpName = async (hcpId) => {
    if (hcpCache[hcpId]) return hcpCache[hcpId];
    try {
      const response = await interactionsAPI.searchHCP(`id:${hcpId}`, 'name');
      const hcps = response.data?.results || [];
      if (hcps.length > 0) {
        const name = hcps[0].name;
        setHcpCache(prev => ({ ...prev, [hcpId]: name }));
        return name;
      }
    } catch {}
    return `HCP #${hcpId}`;
  };

  const loadInteractions = async () => {
    dispatch(setLoading(true));
    try {
      const response = await interactionsAPI.listInteractions(hcpId);
      const data = response.data || [];
      // Resolve HCP names
      const enriched = await Promise.all(
        data.map(async (interaction) => {
          const name = await getHcpName(interaction.hcp_id);
          return { ...interaction, resolved_hcp_name: name };
        })
      );
      dispatch(setInteractions(data));
    } catch (err) {
      const errorMessage =
        err.response?.data?.detail || err.message || 'Failed to load interactions';
      dispatch(setError(errorMessage));
    }
  };

  const handleEdit = (interaction) => {
    setSelectedInteraction(interaction);
    setEditForm({
      topics_discussed: interaction.topics_discussed || '',
      outcomes: interaction.outcomes || '',
      follow_up_actions: interaction.follow_up_actions || '',
      attendees: interaction.attendees || '',
    });
    setDialogError(null);
    setOpenDialog(true);
  };

  const handleSaveEdit = async () => {
    if (!selectedInteraction) return;
    setSaving(true);
    setDialogError(null);
    try {
      const response = await interactionsAPI.editInteraction(
        selectedInteraction.id,
        editForm
      );
      dispatch(updateInteraction(response.data));
      handleCloseDialog();
      setSnackbar({ open: true, message: 'Interaction updated successfully!', severity: 'success' });
    } catch (err) {
      setDialogError(
        err.response?.data?.detail || err.message || 'Failed to update interaction'
      );
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this interaction?')) return;
    try {
      await interactionsAPI.deleteInteraction(id);
      dispatch(setInteractions(interactions.filter((i) => i.id !== id)));
      setSnackbar({ open: true, message: 'Interaction deleted!', severity: 'success' });
    } catch (err) {
      dispatch(setError('Failed to delete interaction'));
    }
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setSelectedInteraction(null);
    setEditForm({});
    setDialogError(null);
  };

  const getSentimentColor = (sentiment) => {
    switch (sentiment) {
      case 'Positive': return 'success';
      case 'Negative': return 'error';
      default: return 'default';
    }
  };

  return (
    <Box sx={{ fontFamily: 'Inter, sans-serif' }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6" sx={{ fontWeight: 600 }}>
          Interaction History
          {hcpId ? ` (Filtered)` : ''}
        </Typography>
        <Button
          variant="outlined"
          onClick={loadInteractions}
          size="small"
          startIcon={<RefreshIcon />}
        >
          Refresh
        </Button>
      </Box>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
          <CircularProgress />
        </Box>
      ) : error ? (
        <Paper sx={{ p: 2, backgroundColor: '#ffebee', color: '#c62828' }}>
          <Typography variant="body2">{error}</Typography>
          <Button size="small" onClick={loadInteractions} sx={{ mt: 1 }}>
            Retry
          </Button>
        </Paper>
      ) : interactions.length === 0 ? (
        <Paper sx={{ p: 4, textAlign: 'center', color: '#999' }}>
          <Typography variant="h6" sx={{ mb: 1, color: '#666' }}>
            No interactions found
          </Typography>
          <Typography variant="body2">
            Log an interaction using the form or chat tab to see it here.
          </Typography>
        </Paper>
      ) : (
        <TableContainer component={Paper} elevation={2}>
          <Table>
            <TableHead sx={{ backgroundColor: '#f5f5f5' }}>
              <TableRow>
                <TableCell sx={{ fontWeight: 600 }}>Date</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Type</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>HCP</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Topics</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Sentiment</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Summary</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {interactions.map((interaction) => (
                <TableRow key={interaction.id} hover>
                  <TableCell>
                    <Typography variant="body2">
                      {new Date(interaction.date).toLocaleDateString()}
                    </Typography>
                    <Typography variant="caption" color="textSecondary">
                      {interaction.time}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip label={interaction.interaction_type} size="small" variant="outlined" />
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">
                      {hcpCache[interaction.hcp_id] || `HCP #${interaction.hcp_id}`}
                    </Typography>
                  </TableCell>
                  <TableCell sx={{ maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {interaction.topics_discussed}
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={interaction.sentiment}
                      size="small"
                      color={getSentimentColor(interaction.sentiment)}
                      variant="filled"
                    />
                  </TableCell>
                  <TableCell sx={{ maxWidth: '250px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {interaction.ai_summary || (
                      <Typography variant="caption" color="textSecondary">
                        Not summarized
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', gap: 1 }}>
                      <Button
                        size="small"
                        variant="outlined"
                        startIcon={<EditIcon />}
                        onClick={() => handleEdit(interaction)}
                      >
                        Edit
                      </Button>
                      <Button
                        size="small"
                        variant="outlined"
                        color="error"
                        startIcon={<DeleteIcon />}
                        onClick={() => handleDelete(interaction.id)}
                      >
                        Delete
                      </Button>
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>Edit Interaction</DialogTitle>
        <DialogContent sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
          {dialogError && <Alert severity="error">{dialogError}</Alert>}
          {selectedInteraction && (
            <>
              <Typography variant="body2" sx={{ mb: 1 }}>
                <strong>Date:</strong> {new Date(selectedInteraction.date).toLocaleDateString()} at {selectedInteraction.time}
                <br />
                <strong>HCP:</strong> {hcpCache[selectedInteraction.hcp_id] || `HCP #${selectedInteraction.hcp_id}`}
                <br />
                <strong>Type:</strong> {selectedInteraction.interaction_type}
              </Typography>
              <TextField
                label="Attendees"
                value={editForm.attendees}
                onChange={(e) => setEditForm((prev) => ({ ...prev, attendees: e.target.value }))}
                fullWidth
                size="small"
              />
              <TextField
                label="Topics Discussed"
                value={editForm.topics_discussed}
                onChange={(e) => setEditForm((prev) => ({ ...prev, topics_discussed: e.target.value }))}
                fullWidth
                multiline
                minRows={3}
                size="small"
              />
              <TextField
                label="Outcomes"
                value={editForm.outcomes}
                onChange={(e) => setEditForm((prev) => ({ ...prev, outcomes: e.target.value }))}
                fullWidth
                multiline
                minRows={2}
                size="small"
              />
              <TextField
                label="Follow-up Actions"
                value={editForm.follow_up_actions}
                onChange={(e) => setEditForm((prev) => ({ ...prev, follow_up_actions: e.target.value }))}
                fullWidth
                multiline
                minRows={2}
                size="small"
              />
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog} disabled={saving}>Cancel</Button>
          <Button onClick={handleSaveEdit} variant="contained" disabled={saving}>
            {saving ? <CircularProgress size={20} /> : 'Save'}
          </Button>
        </DialogActions>
      </Dialog>

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
    </Box>
  );
};

export default HistoryTable;