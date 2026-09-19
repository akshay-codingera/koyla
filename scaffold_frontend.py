import os

files = {
    "frontend/vite.config.ts": """
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000'
    }
  }
})
""",
    "frontend/src/index.css": """
@import "tailwindcss";

@theme {
  --color-primary-500: #1a202c;
  --color-secondary-500: #2d3748;
}

body {
  background-color: #f7fafc;
  color: #2d3748;
}
""",
    "frontend/src/api/client.ts": """
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
""",
    "frontend/src/App.tsx": """
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { AuditLog } from './pages/AuditLog';
import { ProtectedRoute } from './components/ProtectedRoute';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<ProtectedRoute />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="governance" element={<AuditLog />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App;
""",
    "frontend/src/components/ProtectedRoute.tsx": """
import { Navigate, Outlet } from 'react-router-dom';

export const ProtectedRoute = () => {
  const token = localStorage.getItem('token');
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-gray-800 text-white p-4 shadow-md flex justify-between items-center">
        <h1 className="text-xl font-bold">CIL/CMPDI Reporting Intelligence</h1>
        <div className="flex gap-4">
          <a href="/dashboard" className="hover:text-blue-300">Dashboard</a>
          <a href="/governance" className="hover:text-blue-300">Audit Log</a>
          <button onClick={() => { localStorage.removeItem('token'); window.location.href='/login'; }} className="text-red-400">Logout</button>
        </div>
      </header>
      <main className="flex-1 p-6">
        <Outlet />
      </main>
    </div>
  );
};
""",
    "frontend/src/pages/Login.tsx": """
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
            <label className="block text-sm font-medium text-gray-700 mb-1">Username</label>
            <input type="text" value={username} onChange={e => setUsername(e.target.value)} className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:outline-none" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)} className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:outline-none" />
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
""",
    "frontend/src/pages/Dashboard.tsx": """
import { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import { FileText, ShieldCheck, Activity, Users } from 'lucide-react';

export const Dashboard = () => {
  const [metrics, setMetrics] = useState<any>(null);
  const user = JSON.parse(localStorage.getItem('user') || '{}');

  useEffect(() => {
    apiClient.get('/dashboard/metrics').then(res => setMetrics(res.data));
  }, []);

  return (
    <div className="max-w-6xl mx-auto">
      <div className="mb-6 flex justify-between items-end">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Executive Dashboard</h1>
          <p className="text-gray-500">Overview of platform intelligence operations.</p>
        </div>
        <div className="bg-blue-50 text-blue-800 px-4 py-2 rounded-md border border-blue-200">
          <span className="font-semibold">Context:</span> {user.organization?.name} [{user.role}]
        </div>
      </div>
      
      {metrics?.is_demo_data && (
        <div className="bg-yellow-100 border-l-4 border-yellow-500 text-yellow-700 p-4 mb-6">
          <p className="font-bold">Prototype Demonstration Dataset</p>
          <p className="text-sm">Values shown are synthetic records for demonstration purposes.</p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-500 font-medium">Documents Ingested</p>
            <p className="text-3xl font-bold text-gray-800">{metrics?.documents_ingested ?? '...'}</p>
          </div>
          <div className="bg-blue-100 p-3 rounded-full text-blue-600"><FileText size={24}/></div>
        </div>
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-500 font-medium">Verification Backlog</p>
            <p className="text-3xl font-bold text-gray-800">{metrics?.verification_backlog ?? '...'}</p>
          </div>
          <div className="bg-orange-100 p-3 rounded-full text-orange-600"><Activity size={24}/></div>
        </div>
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-500 font-medium">Extraction Accuracy</p>
            <p className="text-3xl font-bold text-gray-800">{metrics?.extraction_success_rate ?? '...'}%</p>
          </div>
          <div className="bg-green-100 p-3 rounded-full text-green-600"><ShieldCheck size={24}/></div>
        </div>
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-500 font-medium">Audit Events</p>
            <p className="text-3xl font-bold text-gray-800">{metrics?.audit_events ?? '...'}</p>
          </div>
          <div className="bg-purple-100 p-3 rounded-full text-purple-600"><Users size={24}/></div>
        </div>
      </div>
    </div>
  );
};
""",
    "frontend/src/pages/AuditLog.tsx": """
import { useEffect, useState } from 'react';
import { apiClient } from '../api/client';

export const AuditLog = () => {
  const [logs, setLogs] = useState<any[]>([]);

  // Since we haven't implemented pagination yet in the backend mock, we will just fetch the latest
  const fetchLogs = async () => {
     // Wait, the API contract is GET /api/v1/governance/audit-logs
     // Let's call a fake endpoint if it doesn't exist, but I'll add the endpoint in the backend.
  }
  return <div>Audit Log UI (Check console for now or ensure API is up)</div>
}
"""
}

for path, content in files.items():
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content.strip() + "\n")

print("Frontend scaffolded successfully.")
