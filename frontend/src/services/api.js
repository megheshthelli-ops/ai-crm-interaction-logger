import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// FIX: Generate or retrieve a unique session ID for the browser tab
// This ensures conversation context is maintained across messages
function getSessionId() {
  let sessionId = sessionStorage.getItem('crm_session_id');
  if (!sessionId) {
    sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    sessionStorage.setItem('crm_session_id', sessionId);
  }
  return sessionId;
}

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 20000,
});

// Debugging interceptors to surface errors in the browser console
apiClient.interceptors.request.use(
  (config) => {
    try {
      console.debug('[api] Request', config.method, config.url, config);
    } catch (e) {}
    return config;
  },
  (error) => {
    console.error('[api] Request error', error);
    return Promise.reject(error);
  }
);

apiClient.interceptors.response.use(
  (response) => {
    try {
      console.debug('[api] Response', response.status, response.config.url, response.data);
    } catch (e) {}
    return response;
  },
  (error) => {
    console.error('[api] Response error', error?.response?.status, error?.config?.url, error?.message, error?.response?.data);
    return Promise.reject(error);
  }
);

// Extraction API
export const extractionAPI = {
  extractFormData: (message, hcpContext = null) =>
    apiClient.post('/extract', {
      message,
      hcp_context: hcpContext,
    }),
};

// Interactions API
export const interactionsAPI = {
  listInteractions: (hcpId = null, limit = 50) =>
    apiClient.get('/interactions', {
      params: {
        limit,
        ...(hcpId ? { hcp_id: hcpId } : {}),
      },
    }),

  logInteraction: (data) =>
    apiClient.post('/interactions/log', data),

  getInteraction: (id) =>
    apiClient.get(`/interactions/${id}`),

  getHCPInteractions: (hcpId, limit = 10) =>
    apiClient.get(`/interactions/hcp/${hcpId}`, {
      params: { limit },
    }),

  editInteraction: (id, data) =>
    apiClient.put(`/interactions/${id}`, data),

  deleteInteraction: (id) =>
    apiClient.delete(`/interactions/${id}`),

  searchHCP: (query, searchType = 'name') =>
    apiClient.post('/interactions/search', null, {
      params: { query, search_type: searchType },
    }),

  getFollowUpSuggestions: (interactionId) =>
    apiClient.post(`/interactions/follow-up/${interactionId}`),

  getMaterialRecommendations: (topic) =>
    apiClient.get(`/interactions/recommendations/${topic}`),

  // FIX: Pass user_id (session_id) with every chat message to maintain context
  chat: (message, interactionData = null) =>
    apiClient.post('/interactions/chat', {
      message,
      user_id: getSessionId(),
      interaction_data: interactionData,
    }),
};

// HCP API (if separate endpoints exist)
export const hcpAPI = {
  listHCPs: () => apiClient.get('/interactions/hcps'),
  searchHCP: (query, searchType = 'name') =>
    apiClient.post('/interactions/search', null, {
      params: { query, search_type: searchType },
    }),
};

export default apiClient;