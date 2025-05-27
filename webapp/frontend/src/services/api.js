import axios from 'axios';

// Get the API URL from the environment or use a default
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Create an axios instance with default config
const api = axios.create({
  baseURL: `${API_URL}/api`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add a request interceptor to include the auth token in requests
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add a response interceptor to handle auth errors
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (error.response) {
      console.error('API Error:', {
        status: error.response.status,
        url: error.config.url,
        data: error.response.data
      });
      
      // If we get a 401 (Unauthorized) or 403 (Forbidden), the token might be invalid
      if (error.response.status === 401 || error.response.status === 403) {
        // Authentication error, handled by components
      }
    }
    return Promise.reject(error);
  }
);

// Auth service
export const authService = {
  // Login with Google (redirects to Google OAuth)
  loginWithGoogle: () => {
    window.location.href = `${API_URL}/api/auth/google`;
  },
  
  // Process token from callback
  handleCallback: (token) => {
    localStorage.setItem('token', token);
    return token;
  },
  
  // Refresh token
  refreshToken: async () => {
    const response = await api.post('/auth/refresh');
    const { access_token } = response.data;
    localStorage.setItem('token', access_token);
    return access_token;
  },
  
  // Logout
  logout: async () => {
    await api.get('/auth/logout');
    localStorage.removeItem('token');
  },
  
  // Check if user is authenticated
  isAuthenticated: () => {
    return !!localStorage.getItem('token');
  }
};

// User service
export const userService = {
  // Get user profile
  getProfile: async () => {
    const response = await api.get('/user/profile');
    return response.data;
  },
  
  // Get user folders
  getFolders: async () => {
    const response = await api.get('/user/folders');
    return response.data;
  },
  
  // Get user courses
  getCourses: async () => {
    const response = await api.get('/user/courses');
    return response.data;
  },
  
  // Get course structure by ID
  getCourseById: async (courseId) => {
    const response = await api.get(`/user/courses/${courseId}`);
    return response.data;
  }
};

// Orchestrator service
export const orchestratorService = {
  // Send a message to the orchestrator
  sendMessage: async (message, sessionId = null, params = {}) => {
    const userId = localStorage.getItem('userId');
    
    if (!userId) {
      console.error('User ID not found in localStorage');
      throw new Error('User ID is required. Please log in again.');
    }
    
    const response = await api.post('/orchestrator/message', {
      message,
      session_id: sessionId,
      user_id: userId,
      params
    });
    
    return response.data;
  },
  
  // Get task status from the orchestrator
  getTaskStatus: async (taskId) => {
    const response = await api.get(`/orchestrator/task/${taskId}`);
    return response.data;
  }
};

export default api;
