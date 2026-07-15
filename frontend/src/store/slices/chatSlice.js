import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  messages: [],
  loading: false,
  error: null,
  suggestedTools: [],
};

const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    addMessage: (state, action) => {
      state.messages.push(action.payload);
    },
    setLoading: (state, action) => {
      state.loading = action.payload;
    },
    setSuggestedTools: (state, action) => {
      state.suggestedTools = action.payload;
    },
    clearMessages: (state) => {
      state.messages = [];
      state.suggestedTools = [];
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
  addMessage,
  setLoading,
  setSuggestedTools,
  clearMessages,
  setError,
  clearError,
} = chatSlice.actions;

export default chatSlice.reducer;
