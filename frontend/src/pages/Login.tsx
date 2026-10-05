import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../api/client';
import { Shield, ArrowRight, Database } from 'lucide-react';

export const Login = () => {
  const [username, setUsername] = useState('hq_officer');
  const [password, setPassword] = useState('Admin123!');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async (e?: React.FormEvent, customUser?: string, customPass?: string) => {
    if (e) e.preventDefault();
    setLoading(true);
    setError('');
    const u = customUser || username;
    const p = customPass || password;

    try {
      const formData = new URLSearchParams();
      formData.append('username', u);
      formData.append('password', p);
      
      const response = await apiClient.post('/auth/login', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      });
      localStorage.setItem('token', response.data.access_token);
      localStorage.setItem('user', JSON.stringify(response.data.user));
      navigate('/dashboard');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Authentication failed. Please verify credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col justify-between bg-[#0a0d12] text-[#f1f5f9] font-sans antialiased p-6">
      {/* Top Banner */}
      <div className="flex items-center justify-between border-b border-[#1f2733] pb-4 max-w-6xl w-full mx-auto">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-sm bg-[#16273d] border border-[#2b4c73] flex items-center justify-center font-mono font-black text-[#60a5fa] text-sm">
            CIL
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-base font-black tracking-widest text-[#f1f5f9]">KOYLA</span>
              <span className="text-[10px] font-mono uppercase tracking-wider text-[#94a3b8] px-2 py-0.5 bg-[#141b24] border border-[#2d3748] rounded-sm">
                INTERNAL CONSOLE
              </span>
            </div>
            <p className="text-[11px] text-[#64748b] tracking-tight font-mono">
              Coal India Limited & Central Mine Planning and Design Institute
            </p>
          </div>
        </div>

        <div className="hidden sm:flex items-center gap-2 font-mono text-xs text-[#94a3b8]">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
          <span>POSTGRESQL 16 + PGVECTOR ONLINE</span>
        </div>
      </div>

      {/* Main Authentication Box */}
      <div className="w-full max-w-md mx-auto my-auto bg-[#12161f] border border-[#242c38] rounded-sm shadow-2xl p-7">
        <div className="mb-6">
          <div className="flex items-center gap-2 mb-2 text-[#60a5fa] font-mono text-xs uppercase tracking-wider">
            <Shield className="w-4 h-4" />
            <span>Secure Access Control</span>
          </div>
          <h1 className="text-xl font-bold text-[#f8fafc] tracking-tight">Geological & Mining Intelligence</h1>
          <p className="text-xs text-[#94a3b8] mt-1 font-mono">
            Role-scoped authorization for CIL subsidiaries, CMPDI RIs, and Verification Officers.
          </p>
        </div>

        {error && (
          <div className="mb-5 p-3 bg-[#2a1215] border border-[#5c1d24] text-[#fca5a5] text-xs font-mono rounded-sm">
            {error}
          </div>
        )}

        <form onSubmit={(e) => handleLogin(e)} className="space-y-4">
          <div>
            <label className="block text-[11px] font-mono uppercase tracking-wider text-[#94a3b8] mb-1.5">
              Operator Username
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full bg-[#0d1015] border border-[#242c38] rounded-sm px-3.5 py-2 text-sm text-[#f1f5f9] focus:outline-none focus:border-[#3b82f6] font-mono transition-colors"
              placeholder="Username"
              required
            />
          </div>

          <div>
            <label className="block text-[11px] font-mono uppercase tracking-wider text-[#94a3b8] mb-1.5">
              Authentication Token / Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-[#0d1015] border border-[#242c38] rounded-sm px-3.5 py-2 text-sm text-[#f1f5f9] focus:outline-none focus:border-[#3b82f6] font-mono transition-colors"
              placeholder="Password"
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full mt-2 bg-[#1e40af] hover:bg-[#2563eb] text-white font-mono text-xs uppercase tracking-wider font-semibold py-2.5 px-4 rounded-sm flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
          >
            {loading ? (
              <span>Verifying Credentials...</span>
            ) : (
              <>
                <span>Access Console</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        {/* Quick Demo Launch Options */}
        <div className="mt-6 pt-5 border-t border-[#1f2733]">
          <div className="text-[10px] font-mono text-[#64748b] uppercase tracking-wider mb-2.5">
            Quick Launch Roles (Prototype Mode)
          </div>
          <div className="grid grid-cols-2 gap-2 font-mono text-[11px]">
            <button
              type="button"
              onClick={() => {
                setUsername('hq_officer');
                setPassword('Admin123!');
                handleLogin(undefined, 'hq_officer', 'Admin123!');
              }}
              className="p-2 bg-[#161c26] hover:bg-[#1f2837] border border-[#263345] hover:border-[#3b82f6] rounded-sm text-left transition-colors"
            >
              <div className="text-[#93c5fd] font-bold">HQ Officer</div>
              <div className="text-[9px] text-[#64748b]">Central Reviewer Scope</div>
            </button>
            <button
              type="button"
              onClick={() => {
                setUsername('ri1_analyst');
                setPassword('Password123!');
                handleLogin(undefined, 'ri1_analyst', 'Password123!');
              }}
              className="p-2 bg-[#161c26] hover:bg-[#1f2837] border border-[#263345] hover:border-[#3b82f6] rounded-sm text-left transition-colors"
            >
              <div className="text-[#93c5fd] font-bold">RI-1 Analyst</div>
              <div className="text-[9px] text-[#64748b]">Subsidiary / Regional</div>
            </button>
          </div>
        </div>
      </div>

      {/* Footer Audit Disclaimer */}
      <div className="max-w-6xl w-full mx-auto pt-4 border-t border-[#1f2733] flex flex-col sm:flex-row items-center justify-between text-[11px] font-mono text-[#64748b] gap-2">
        <div className="flex items-center gap-2">
          <Database className="w-3.5 h-3.5 text-[#3b82f6]" />
          <span>Local Sovereign Instance · SIH Problem Statement 26023</span>
        </div>
        <div>
          <span>Deterministic Audit Trail Enforced · All Actions Recorded</span>
        </div>
      </div>
    </div>
  );
};
