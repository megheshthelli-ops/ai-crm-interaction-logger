import { configureStore } from '@reduxjs/toolkit';
import interactionSlice from './slices/interactionSlice';
import hcpSlice from './slices/hcpSlice';
import chatSlice from './slices/chatSlice';
import formDataSlice from './slices/formDataSlice';

export const store = configureStore({
  reducer: {
    interactions: interactionSlice,
    hcps: hcpSlice,
    chat: chatSlice,
    formData: formDataSlice,
  },
});

export default store;
