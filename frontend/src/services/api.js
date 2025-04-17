import axios from 'axios';

// Create axios instance with default config
const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:5000',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Function to set API key from local storage
export const setApiKey = (apiKey) => {
  console.log('Setting API key:', apiKey ? `${apiKey.substring(0, 2)}...` : 'none'); // Debug log
  localStorage.setItem('api_key', apiKey);
  api.defaults.headers.common['X-API-Key'] = apiKey;
};

// Initialize API key from localStorage if available
const storedApiKey = localStorage.getItem('api_key');
if (storedApiKey) {
  console.log('Found stored API key'); // Debug log
  api.defaults.headers.common['X-API-Key'] = storedApiKey;
}

// Add request interceptor for debugging
api.interceptors.request.use(config => {
  console.log('API Request:', {
    url: config.url,
    headers: {
      ...config.headers,
      'X-API-Key': config.headers['X-API-Key'] ? `${config.headers['X-API-Key'].substring(0, 2)}...` : 'not set'
    }
  });
  return config;
});

// API functions
export const uploadPdfFile = async (file) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post('/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

// Add a function to check if the API key is valid
export const checkApiKey = async () => {
  try {
    const response = await api.get('/api-key-check');
    return response.data.valid;
  } catch (error) {
    console.error('API Key validation failed:', error);
    return false;
  }
};

export const getDashboardData = async () => {
  // Check if API key is set
  if (!api.defaults.headers.common['X-API-Key']) {
    throw new Error('API key not set. Please configure it in Settings.');
  }
  
  const response = await api.get('/dashboard');
  return response.data;
};

export default api;
