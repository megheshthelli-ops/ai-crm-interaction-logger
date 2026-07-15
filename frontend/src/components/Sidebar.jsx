import React, { useState } from 'react';
import {
  Drawer,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Divider,
  Box,
  Typography,
  TextField,
  Button,
  CircularProgress,
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import HistoryIcon from '@mui/icons-material/History';
import PersonIcon from '@mui/icons-material/Person';
import AddIcon from '@mui/icons-material/Add';
import ChatIcon from '@mui/icons-material/Chat';
import { useDispatch } from 'react-redux';
import { setSelectedHCP } from '../store/slices/hcpSlice';
import { interactionsAPI } from '../services/api';

const Sidebar = ({ open = true, onNavigate = null, onClose = null }) => {
  const dispatch = useDispatch();
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setSearching(true);
    try {
      const response = await interactionsAPI.searchHCP(searchQuery, 'name');
      setSearchResults(response.data.results || []);
    } catch (err) {
      console.error('Search failed:', err);
    } finally {
      setSearching(false);
    }
  };

  const handleSelectHCP = (hcp) => {
    dispatch(setSelectedHCP(hcp));
    setSearchQuery('');
    setSearchResults([]);
    if (onNavigate) onNavigate('log');
  };

  return (
    <Drawer
      variant="persistent"
      open={open}
      sx={{
        width: 280,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: 280,
          boxSizing: 'border-box',
          backgroundColor: '#f9f9f9',
          borderRight: '1px solid #eee',
        },
      }}
    >
      <Box sx={{ p: 2 }}>
        <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>
          HCP Search
        </Typography>

        <TextField
          fullWidth
          size="small"
          placeholder="Search by name..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') handleSearch();
          }}
          sx={{ mb: 1 }}
        />

        <Button
          fullWidth
          variant="contained"
          size="small"
          startIcon={searching ? <CircularProgress size={16} color="inherit" /> : <SearchIcon />}
          onClick={handleSearch}
          disabled={searching}
          sx={{ mb: 2 }}
        >
          Search
        </Button>

        {searchResults.length > 0 && (
          <Box>
            <Divider sx={{ my: 1 }} />
            <Typography variant="caption" sx={{ fontWeight: 600, display: 'block', mb: 1 }}>
              Search Results ({searchResults.length})
            </Typography>
            <List sx={{ maxHeight: 300, overflowY: 'auto' }}>
              {searchResults.map((hcp) => (
                <ListItem
                  button
                  key={hcp.id}
                  onClick={() => handleSelectHCP(hcp)}
                  sx={{
                    py: 1,
                    px: 1,
                    borderRadius: '4px',
                    '&:hover': { backgroundColor: '#e3f2fd' },
                  }}
                >
                  <ListItemIcon sx={{ minWidth: 32 }}>
                    <PersonIcon fontSize="small" />
                  </ListItemIcon>
                  <ListItemText
                    primary={hcp.name}
                    secondary={`${hcp.specialty} — ${hcp.organization}`}
                    primaryTypographyProps={{ variant: 'body2' }}
                    secondaryTypographyProps={{ variant: 'caption' }}
                  />
                </ListItem>
              ))}
            </List>
          </Box>
        )}

        {searchResults.length === 0 && searchQuery && !searching && (
          <Typography variant="caption" color="textSecondary">
            No HCPs found matching "{searchQuery}"
          </Typography>
        )}
      </Box>

      <Divider />

      <List sx={{ p: 1 }}>
        <ListItem
          button
          onClick={() => onNavigate && onNavigate('log')}
          sx={{
            borderRadius: '4px',
            mb: 1,
            '&:hover': { backgroundColor: '#e3f2fd' },
          }}
        >
          <ListItemIcon>
            <AddIcon />
          </ListItemIcon>
          <ListItemText
            primary="New Interaction"
            primaryTypographyProps={{ variant: 'body2', fontWeight: 500 }}
          />
        </ListItem>

        <ListItem
          button
          onClick={() => onNavigate && onNavigate('history')}
          sx={{
            borderRadius: '4px',
            mb: 1,
            '&:hover': { backgroundColor: '#e3f2fd' },
          }}
        >
          <ListItemIcon>
            <HistoryIcon />
          </ListItemIcon>
          <ListItemText
            primary="Interaction History"
            primaryTypographyProps={{ variant: 'body2', fontWeight: 500 }}
          />
        </ListItem>

        <ListItem
          button
          onClick={() => onNavigate && onNavigate('chat')}
          sx={{
            borderRadius: '4px',
            mb: 1,
            '&:hover': { backgroundColor: '#e3f2fd' },
          }}
        >
          <ListItemIcon>
            <ChatIcon />
          </ListItemIcon>
          <ListItemText
            primary="AI Chat Assistant"
            primaryTypographyProps={{ variant: 'body2', fontWeight: 500 }}
          />
        </ListItem>
      </List>
    </Drawer>
  );
};

export default Sidebar;