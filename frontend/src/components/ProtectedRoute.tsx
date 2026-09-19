import { Navigate, Outlet, Link, useLocation } from 'react-router-dom';
import { 
  BarChart3, 
  FileText, 
  Search, 
  ShieldCheck, 
  ShieldAlert, 
  LogOut, 
  FileSpreadsheet, 
  Compass,
  Layers,
  UploadCloud,
  CheckCircle
} from 'lucide-react';

export const ProtectedRoute = () => {
  const token = localStorage.getItem('token');
  const location = useLocation();

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  const navLinks = [
    { to: '/dashboard', label: 'Dashboard', icon: BarChart3 },
    { to: '/reports', label: 'Reports', icon: FileSpreadsheet },
    { to: '/topics', label: 'Topics', icon: Layers },
    { to: '/documents', label: 'Documents', icon: FileText },
    { to: '/knowledge', label: 'Knowledge', icon: Compass },
    { to: '/verification', label: 'Verification', icon: ShieldCheck },
    { to: '/governance', label: 'Audit', icon: ShieldAlert },
    { to: '/system', label: 'System', icon: CheckCircle },
  ];

  return (
    <div className="min-h-screen flex flex-col bg-[#0d1015] text-[#e2e8f0] font-sans antialiased">
      {/* Top Technical Header Bar */}
      <header className="bg-[#12161d] text-white px-5 py-2.5 border-b border-[#242c38] flex justify-between items-center z-20">
        <div className="flex items-center gap-6">
          {/* KOYLA Brandmark */}
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-sm bg-[#16273d] border border-[#2b4c73] flex items-center justify-center font-mono font-black text-[#60a5fa] text-xs tracking-wider shadow-inner">
              CIL
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-sm font-black tracking-widest text-[#f1f5f9]">KOYLA</span>
                <span className="text-[10px] font-mono uppercase tracking-wider text-[#94a3b8] px-1.5 py-0.2 bg-[#1a212b] border border-[#2d3748] rounded-sm">
                  CIL / CMPDI INTELLIGENCE
                </span>
              </div>
              <p className="text-[9px] text-[#64748b] tracking-tight uppercase font-mono mt-0.5">
                Geological, Mining & Reporting Intelligence
              </p>
            </div>
          </div>

          {/* Primary Dossier / System Navigation */}
          <nav className="hidden lg:flex items-center gap-1 pl-5 border-l border-[#242c38]">
            {navLinks.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.to || (item.to !== '/dashboard' && location.pathname.startsWith(item.to));
              return (
                <Link
                  key={item.to}
                  to={item.to}
                  className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono tracking-tight transition-all rounded-sm ${
                    isActive
                      ? 'bg-[#1e3450] text-[#93c5fd] font-bold border-b-2 border-[#3b82f6] shadow-sm'
                      : 'text-[#94a3b8] hover:text-[#f8fafc] hover:bg-[#181f28]'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5 opacity-80" />
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Right Status & Evidence Badge */}
        <div className="flex items-center gap-4">
          {/* Persistent "EVIDENCE FIRST" Methodology Indicator */}
          <div className="hidden xl:flex items-center gap-2 px-3 py-1 bg-[#161c24] border border-[#252f3d] rounded-sm text-[10px] font-mono text-[#94a3b8]">
            <span className="flex items-center gap-1 font-bold text-[#38bdf8] uppercase tracking-wider">
              <span className="w-1.5 h-1.5 rounded-full bg-[#38bdf8] animate-pulse"></span>
              EVIDENCE FIRST
            </span>
            <span className="text-[#475569]">|</span>
            <span className="text-[#cbd5e1]">Verified Data · Deterministic Calculations · Grounded Narrative · QP Review</span>
          </div>

          <button
            onClick={() => {
              localStorage.removeItem('token');
              window.location.href = '/login';
            }}
            className="flex items-center gap-1 text-[11px] font-mono text-[#f87171] hover:text-[#fca5a5] px-2.5 py-1 rounded-sm hover:bg-[#201618] border border-transparent hover:border-[#451e24] transition-colors"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Logout</span>
          </button>
        </div>
      </header>

      {/* Main Content Stage */}
      <main className="flex-1 bg-survey-grid">
        <Outlet />
      </main>
    </div>
  );
};
