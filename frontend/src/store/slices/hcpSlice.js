import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  hcps: [],
  selectedHCP: null,
  searchResults: [],
  loading: false,
  error: null,
};

const hcpSlice = createSlice({
  name: 'hcps',
  initialState,
  reducers: {
    setLoading: (state, action) => {
      state.loading = action.payload;
    },
    setHCPs: (state, action) => {
      state.hcps = action.payload;
      state.loading = false;
    },
    setSelectedHCP: (state, action) => {
      state.selectedHCP = action.payload;
    },
    setSearchResults: (state, action) => {
      state.searchResults = action.payload;
    },
    addHCP: (state, action) => {
      state.hcps.unshift(action.payload);
    },
    setError: (state, action) => {
      state.error = action.payload;
      state.loading = false;
    },
    clearError: (state) => {
      state.error = null;
    },
  },
});

export const {
  setLoading,
  setHCPs,
  setSelectedHCP,
  setSearchResults,
  addHCP,
  setError,
  clearError,
} = hcpSlice.actions;

export default hcpSlice.reducer;
