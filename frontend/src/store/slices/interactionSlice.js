import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  interactions: [],
  currentInteraction: null,
  loading: false,
  error: null,
};

const interactionSlice = createSlice({
  name: 'interactions',
  initialState,
  reducers: {
    setLoading: (state, action) => {
      state.loading = action.payload;
    },
    setInteractions: (state, action) => {
      state.interactions = action.payload;
      state.loading = false;
    },
    setCurrentInteraction: (state, action) => {
      state.currentInteraction = action.payload;
    },
    addInteraction: (state, action) => {
      state.interactions.unshift(action.payload);
    },
    updateInteraction: (state, action) => {
      const index = state.interactions.findIndex(
        (i) => i.id === action.payload.id
      );
      if (index !== -1) {
        state.interactions[index] = action.payload;
      }
      if (state.currentInteraction?.id === action.payload.id) {
        state.currentInteraction = action.payload;
      }
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
  setInteractions,
  setCurrentInteraction,
  addInteraction,
  updateInteraction,
  setError,
  clearError,
} = interactionSlice.actions;

export default interactionSlice.reducer;
