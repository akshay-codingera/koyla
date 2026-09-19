import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../api/client';
import { Lock } from 'lucide-react';

export const Login = () => {
  const [username, setUsername] = useState('hq_officer');
  const [password, setPassword] = useState('Admin123!');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const formData = new URLSearchParams();
      formData.append('username', username);
      formData.append('password', password);
      
      const response = await apiClient.post('/auth/login', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      });
      localStorage.setItem('token', response.data.access_token);
      localStorage.setItem('user', JSON.stringify(response.data.user));
      navigate('/dashboard');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <div className="bg-white p-8 rounded-lg shadow-lg w-full max-w-md border border-gray-200">
        <div className="flex justify-center mb-4">
          <div className="bg-blue-900 p-3 rounded-full text-white">
            <Lock size={24} />
          </div>
        </div>
        <h2 className="text-2xl font-bold text-center mb-6 text-gray-800">CMPDI Secure Portal</h2>
        {error && <div className="bg-red-100 text-red-700 p-3 rounded mb-4 text-sm">{error}</div>}
        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-1">Username</label>
            <input id="username" type="text" value={username} onChange={e => setUsername(e.target.value)} className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:outline-none" />
          </div>
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">Password</label>
            <input id="password" type="password" value={password} onChange={e => setPassword(e.target.value)} className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:outline-none" />
          </div>
          <button type="submit" className="w-full bg-blue-900 text-white p-2 rounded hover:bg-blue-800 transition-colors font-medium">Authenticate</button>
        </form>
        <div className="mt-4 text-xs text-gray-500 text-center">
          <p>Demo accounts: hq_officer / Admin123! | ri1_analyst / Password123!</p>
        </div>
      </div>
    </div>
  );
};
