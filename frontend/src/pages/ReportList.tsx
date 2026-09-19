import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { apiClient } from '../api/client';
import { 
  FileText, Plus, Download, ArrowRight, ShieldCheck, AlertTriangle, 
  CheckCircle2, RefreshCw, Layers, Compass, FileSpreadsheet, Scale
} from 'lucide-react';

interface ReportSummary {
  id: string;
  report_title: string;
  mine_name: string;
  block_name: string;
  organization_id: string;
  organization_name: string;
  base_date: string;
  status: string;
  compliance_status: string;
  version_number: number;
  has_docx: boolean;
  created_at: string;
  updated_at: string;
}

export const ReportList: React.FC = () => {
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const fetchReports = async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await apiClient.get('/reports');
      setReports(resp.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch statutory report register.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, []);

  const renderStatusBadge = (status: string) => {
    switch (status) {
      case 'READY_FOR_AUTHORIZED_SUBMISSION':
        return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-none font-mono text-[10px] font-bold bg-[#143825] text-[#4ade80] border border-[#225e3d]">READY FOR SUBMISSION</span>;
      case 'READY_FOR_AUTHORIZED_REVIEW':
        return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-none font-mono text-[10px] font-bold bg-[#162d47] text-[#60a5fa] border border-[#2b4c73]">READY FOR QP REVIEW</span>;
      case 'VERIFIED':
        return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-none font-mono text-[10px] font-bold bg-[#143825] text-[#4ade80] border border-[#225e3d]">QP VERIFIED</span>;
      case 'FORMAT_COMPLIANT':
        return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-none font-mono text-[10px] font-bold bg-[#1b3530] text-[#5eead4] border border-[#2a5951]">FORMAT COMPLIANT</span>;
      case 'REVIEW_REQUIRED':
        return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-none font-mono text-[10px] font-bold bg-[#38260d] text-[#fbbf24] border border-[#5e4318]">REVIEW REQUIRED</span>;
      case 'DATA_INCOMPLETE':
        return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-none font-mono text-[10px] font-bold bg-[#381419] text-[#f87171] border border-[#6b222d]">DATA INCOMPLETE</span>;
      default:
        return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-none font-mono text-[10px] font-bold bg-[#171e27] text-[#94a3b8] border border-[#263140]">DRAFT STATE</span>;
    }
  };

  const renderComplianceBadge = (status: string) => {
    switch (status) {
      case 'COMPLIANT':
        return <span className="px-1.5 py-0.2 rounded-none font-mono text-[10px] font-bold bg-[#143825] text-[#4ade80] border border-[#225e3d]">COMPLIANT</span>;
      case 'PARTIALLY_COMPLIANT':
        return <span className="px-1.5 py-0.2 rounded-none font-mono text-[10px] font-bold bg-[#38260d] text-[#fbbf24] border border-[#5e4318]">PARTIALLY COMPLIANT</span>;
      default:
        return <span className="px-1.5 py-0.2 rounded-none font-mono text-[10px] font-bold bg-[#381419] text-[#f87171] border border-[#6b222d]">NON-COMPLIANT</span>;
    }
  };

  return (
    <div className="min-h-screen bg-survey-grid text-[#e2e8f0] px-6 py-6 font-mono">
      <div className="max-w-[1720px] mx-auto">
        
        {/* Header Strip */}
        <div className="bg-[#12161e] border border-[#222a36] p-5 mb-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="px-1.5 py-0.5 bg-[#1b2f48] border border-[#2e527d] text-[#60a5fa] text-[10px] font-bold tracking-wider uppercase">
                STATUTORY REPORT DOSSIER REGISTER
              </span>
              <span className="text-xs text-[#94a3b8]">
                Ministry of Coal / CCO OM F.No. CPAM-34011/28/2019-CPAM [31-01-2025]
              </span>
            </div>
            <h1 className="text-xl font-bold tracking-tight text-[#f8fafc]">
              Official Mining Plan & Mine Closure Plan Dossiers
            </h1>
            <p className="text-xs text-[#64748b] mt-0.5">
              156-parameter statutory mapping (133 fields + 23 prescribed tables) derived deterministically from verified evidence.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={fetchReports}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-[#171e27] hover:bg-[#1f2835] border border-[#2b3748] text-xs text-[#cbd5e1] transition-all"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>REFRESH REGISTER</span>
            </button>
            <Link
              to="/reports/new"
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-[#163352] hover:bg-[#1d426a] border border-[#29588c] text-xs font-semibold text-[#93c5fd] transition-all"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>COMPILE NEW STATUTORY DOSSIER</span>
            </Link>
          </div>
        </div>

        {/* Register Table */}
        <div className="bg-[#12161e] border border-[#222a36] rounded-sm overflow-hidden">
          <div className="px-5 py-3 bg-[#161c26] border-b border-[#222a36] flex items-center justify-between text-xs">
            <span className="font-bold text-[#93c5fd] uppercase tracking-wider">
              OFFICIAL DOSSIER INVENTORY ({reports.length} DOSSIERS RECORDED)
            </span>
            <span className="text-[#64748b] text-[11px]">
              EVIDENCE-FIRST COMPILATION
            </span>
          </div>

          {loading ? (
            <div className="p-12 text-center text-xs text-[#94a3b8]">
              <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-[#38bdf8]" />
              <span>FETCHING STATUTORY DOSSIER RECORDS...</span>
            </div>
          ) : reports.length === 0 ? (
            <div className="p-12 text-center text-xs text-[#64748b]">
              NO STATUTORY DOSSIERS REGISTERED YET. CLICK "COMPILE NEW STATUTORY DOSSIER" TO INITIATE.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-[#1e2531] text-xs">
                <thead className="bg-[#0f131a] text-[#94a3b8]">
                  <tr>
                    <th className="px-4 py-2.5 text-left text-[10px] uppercase">DOSSIER REF</th>
                    <th className="px-4 py-2.5 text-left text-[10px] uppercase">MINE & BLOCK IDENTIFICATION</th>
                    <th className="px-4 py-2.5 text-left text-[10px] uppercase">SUBSIDIARY SCOPE</th>
                    <th className="px-4 py-2.5 text-left text-[10px] uppercase">BASE PERIOD</th>
                    <th className="px-4 py-2.5 text-left text-[10px] uppercase">COMPLIANCE STATE</th>
                    <th className="px-4 py-2.5 text-left text-[10px] uppercase">STATUS</th>
                    <th className="px-4 py-2.5 text-left text-[10px] uppercase">VERSION</th>
                    <th className="px-4 py-2.5 text-right text-[10px] uppercase">ACTIONS</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#18202b] bg-[#12161e]">
                  {reports.map((rep) => (
                    <tr key={rep.id} className="hover:bg-[#161d28] transition-colors">
                      <td className="px-4 py-3 font-bold text-[#38bdf8]">
                        DOS-{rep.id.slice(0, 8)}
                      </td>
                      <td className="px-4 py-3">
                        <div className="font-bold text-[#f1f5f9]">{rep.block_name}</div>
                        <div className="text-[11px] text-[#94a3b8]">{rep.mine_name}</div>
                      </td>
                      <td className="px-4 py-3">
                        <span className="px-1.5 py-0.5 bg-[#151c24] border border-[#252f3d] text-[#cbd5e1]">
                          {rep.organization_name}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-[#cbd5e1]">
                        {rep.base_date}
                      </td>
                      <td className="px-4 py-3">
                        {renderComplianceBadge(rep.compliance_status)}
                      </td>
                      <td className="px-4 py-3">
                        {renderStatusBadge(rep.status)}
                      </td>
                      <td className="px-4 py-3 text-[#94a3b8]">
                        v{rep.version_number}.0
                      </td>
                      <td className="px-4 py-3 text-right">
                        <Link
                          to={`/reports/${rep.id}`}
                          className="inline-flex items-center gap-1 px-3 py-1 bg-[#172538] hover:bg-[#1f334d] border border-[#2b4b73] text-[#93c5fd] text-xs font-semibold"
                        >
                          <span>OPEN DOSSIER</span>
                          <ArrowRight className="w-3 h-3" />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

      </div>
    </div>
  );
};
