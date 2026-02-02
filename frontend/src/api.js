// API client with axios
import axios from 'axios';
import { API_BASE_URL } from './config';

const api = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Only redirect to login on 401 if NOT already on a public auth page
    // This prevents the login form from refreshing when credentials are wrong
    if (error.response?.status === 401) {
      const currentPath = window.location.pathname;
      const publicAuthPaths = ['/login', '/signup', '/forgot-password', '/reset-password', '/verify-email'];
      const isPublicAuthPage = publicAuthPaths.some(path => currentPath.startsWith(path));
      
      // Only clear tokens and redirect if we're NOT on a public auth page
      // (i.e., the user was logged in and their session expired)
      if (!isPublicAuthPage) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('user');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default api;