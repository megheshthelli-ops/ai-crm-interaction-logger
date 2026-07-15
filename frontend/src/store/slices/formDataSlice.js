import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  // AI-extracted form data for auto-population
  extractedData: null,
  // Whether AI data is pending to be applied to the form
  pendingExtraction: false,
  // The raw message that was extracted
  lastExtractedMessage: null,
  // Suggested tools from the extraction
  suggestedTools: [],
  // Loading state for extraction
  loading: false,
  // Error state
  error: null,
};

const formDataSlice = createSlice({
  name: 'formData',
  initialState,
  reducers: {
    setExtractedData: (state, action) => {
      state.extractedData = action.payload;
      state.pendingExtraction = true;
      state.loading = false;
      state.error = null;
    },
    clearExtractedData: (state) => {
      state.extractedData = null;
      state.pendingExtraction = false;
      state.lastExtractedMessage = null;
      state.suggestedTools = [];
    },
    applyExtractedData: (state) => {
      state.pendingExtraction = false;
    },
    setLastExtractedMessage: (state, action) => {
      state.lastExtractedMessage = action.payload;
    },
    setSuggestedTools: (state, action) => {
      state.suggestedTools = action.payload;
    },
    setExtractionLoading: (state, action) => {
      state.loading = action.payload;
    },
    setExtractionError: (state, action) => {
      state.error = action.payload;
      state.loading = false;
    },
    clearExtractionError: (state) => {
      state.error = null;
    },
  },
});

export const {
  setExtractedData,
  clearExtractedData,
  applyExtractedData,
  setLastExtractedMessage,
  setSuggestedTools,
  setExtractionLoading,
  setExtractionError,
  clearExtractionError,
} = formDataSlice.actions;

export default formDataSlice.reducer;