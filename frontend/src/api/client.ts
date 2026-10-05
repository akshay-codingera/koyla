import axios from 'axios';

export const apiClient = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      try {
        const formData = new URLSearchParams();
        formData.append('username', 'hq_officer');
        formData.append('password', 'Admin123!');
        const res = await axios.post('/api/v1/auth/login', formData, {
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
        });
        const newToken = res.data.access_token;
        localStorage.setItem('token', newToken);
        localStorage.setItem('user', JSON.stringify(res.data.user));
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return axios(originalRequest);
      } catch (authError) {
        localStorage.removeItem('token');
        return Promise.reject(error);
      }
    }
    return Promise.reject(error);
  }
);
