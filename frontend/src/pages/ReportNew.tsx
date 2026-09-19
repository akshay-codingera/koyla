import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { apiClient } from '../api/client';
import { 
  FileText, ArrowLeft, Shield, CheckCircle2, AlertCircle, RefreshCw, 
  Layers, Compass, Scale, FileSpreadsheet
} from 'lucide-react';

interface FormatItem {
  id: string;
  report_type: string;
  issuing_authority: string;
  document_title: string;
  om_number: string;
  om_date: string;
  guideline_year: number;
  effective_status: string;
}

interface OrgItem {
  id: string;
  name: string;
  code: string;
}

export const ReportNew: React.FC = () => {
  const navigate = useNavigate();
  const [formats, setFormats] = useState<FormatItem[]>([]);
  const [organizations, setOrganizations] = useState<OrgItem[]>([]);
  const [selectedFormat, setSelectedFormat] = useState<string>('');
  const [selectedOrg, setSelectedOrg] = useState<string>('');
  const [mineName, setMineName] = useState<string>('Amritnagar Colliery');
  const [blockName, setBlockName] = useState<string>('Raniganj Coal Block');
  const [baseDate, setBaseDate] = useState<string>('2026-03');
  const [loading, setLoading] = useState<boolean>(true);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadInitData = async () => {
      setLoading(true);
      try {
        const [fmtResp, orgResp] = await Promise.all([
          apiClient.get('/reports/formats'),
          apiClient.get('/organizations/'),
        ]);
        setFormats(fmtResp.data);
        if (fmtResp.data.length > 0) {
          setSelectedFormat(fmtResp.data[0].id);
        }
        setOrganizations(orgResp.data);
        if (orgResp.data.length > 0) {
          setSelectedOrg(orgResp.data[0].id);
        }
      } catch (err: any) {
        setError('Failed to load authoritative format registry or organizational scopes.');
      } finally {
        setLoading(false);
      }
    };
    loadInitData();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFormat || !selectedOrg || !mineName || !blockName || !baseDate) {
      setError('All statutory report parameters are mandatory.');
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      const resp = await apiClient.post('/reports/generate', {
        format_id: selectedFormat,
        organization_id: selectedOrg,
        mine_name: mineName,
        block_name: blockName,
        base_date: baseDate,
      });
      navigate(`/reports/${resp.data.report_id}`);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to compile statutory dossier.');
      setSubmitting(false);
    }
  };

  const selectedFormatObj = formats.find(f => f.id === selectedFormat);

  return (
    <div className="min-h-screen bg-survey-grid text-[#e2e8f0] px-6 py-6 font-mono">
      <div className="max-w-4xl mx-auto">
        
        {/* Back Link */}
        <Link
          to="/reports"
          className="inline-flex items-center gap-1.5 text-xs text-[#94a3b8] hover:text-[#38bdf8] mb-4 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>RETURN TO STATUTORY DOSSIER REGISTER</span>
        </Link>

        {/* Compiler Form Container */}
        <div className="bg-[#12161e] border border-[#222a36] rounded-sm shadow-xl overflow-hidden">
          
          {/* Header Strip */}
          <div className="bg-[#161c26] border-b border-[#222a36] p-5">
            <div className="flex items-center gap-2 text-[10px] text-[#60a5fa] font-bold uppercase tracking-wider mb-1">
              <Shield className="w-3.5 h-3.5" />
              <span>MINISTRY OF COAL STATUTORY COMPILATION GATEWAY</span>
            </div>
            <h1 className="text-lg font-bold tracking-tight text-[#f8fafc]">
              Compile Statutory Mining Plan & Mine Closure Plan Dossier
            </h1>
            <p className="text-xs text-[#64748b] mt-0.5">
              Conforms strictly to Appendix-I of Ministry of Coal / Coal Controller Organisation Guidelines (OM dated 31 Jan 2025).
            </p>
          </div>

          {error && (
            <div className="p-3 bg-[#2b1418] border-b border-[#522026] text-xs text-[#fca5a5]">
              [COMPILATION ERROR]: {error}
            </div>
          )}

          {loading ? (
            <div className="p-12 text-center text-xs text-[#94a3b8]">
              <RefreshCw className="w-5 h-5 text-[#38bdf8] animate-spin mx-auto mb-2" />
              <span>INITIALIZING STATUTORY PARAMETER REGISTRIES...</span>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="p-6 space-y-5 text-xs">
              
              {/* 1. Format Selection */}
              <div>
                <label className="block text-[10px] font-bold text-[#94a3b8] uppercase tracking-wider mb-1.5">
                  1. Authoritative Statutory Format Specification
                </label>
                <select
                  value={selectedFormat}
                  onChange={(e) => setSelectedFormat(e.target.value)}
                  className="w-full bg-[#0d1015] border border-[#252f3e] text-[#f8fafc] p-2.5 rounded-none font-mono focus:border-[#38bdf8] focus:outline-none"
                >
                  {formats.map((fmt) => (
                    <option key={fmt.id} value={fmt.id}>
                      {fmt.document_title} — {fmt.om_number} ({fmt.guideline_year})
                    </option>
                  ))}
                </select>

                {selectedFormatObj && (
                  <div className="mt-2.5 p-3 bg-[#0d121a] border border-[#1e2a3b] text-[11px] text-[#cbd5e1] space-y-1">
                    <div className="text-[#38bdf8] font-bold flex items-center gap-1">
                      <CheckCircle2 className="w-3.5 h-3.5 text-[#38bdf8]" />
                      <span>STATUTORY SPECIFICATION VERIFIED</span>
                    </div>
                    <div><span className="text-[#64748b]">Authority:</span> {selectedFormatObj.issuing_authority}</div>
                    <div><span className="text-[#64748b]">OM Reference:</span> {selectedFormatObj.om_number} dated {selectedFormatObj.om_date}</div>
                    <div><span className="text-[#64748b]">Governing Scope:</span> Appendix-I: Details to be furnished in Mining Plans for Coal/Lignite Blocks</div>
                  </div>
                )}
              </div>

              {/* 2. Organization Scope */}
              <div>
                <label className="block text-[10px] font-bold text-[#94a3b8] uppercase tracking-wider mb-1.5">
                  2. Organizational Context / Subsidiary Scope
                </label>
                <select
                  value={selectedOrg}
                  onChange={(e) => setSelectedOrg(e.target.value)}
                  className="w-full bg-[#0d1015] border border-[#252f3e] text-[#f8fafc] p-2.5 rounded-none font-mono focus:border-[#38bdf8] focus:outline-none"
                >
                  {organizations.map((org) => (
                    <option key={org.id} value={org.id}>
                      {org.name} ({org.code})
                    </option>
                  ))}
                </select>
                <div className="text-[10px] text-[#64748b] mt-1">
                  Evidence retrieval, reserve extraction and document boundaries are strictly constrained to this subsidiary.
                </div>
              </div>

              {/* 3. Block & Mine Names */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-[10px] font-bold text-[#94a3b8] uppercase tracking-wider mb-1.5">
                    3. Coal / Lignite Block Designation
                  </label>
                  <input
                    type="text"
                    value={blockName}
                    onChange={(e) => setBlockName(e.target.value)}
                    placeholder="e.g. Raniganj Coal Block"
                    required
                    className="w-full bg-[#0d1015] border border-[#252f3e] text-[#f8fafc] p-2.5 rounded-none font-mono focus:border-[#38bdf8] focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-[10px] font-bold text-[#94a3b8] uppercase tracking-wider mb-1.5">
                    4. Mine / Colliery Designation
                  </label>
                  <input
                    type="text"
                    value={mineName}
                    onChange={(e) => setMineName(e.target.value)}
                    placeholder="e.g. Amritnagar Colliery"
                    required
                    className="w-full bg-[#0d1015] border border-[#252f3e] text-[#f8fafc] p-2.5 rounded-none font-mono focus:border-[#38bdf8] focus:outline-none"
                  />
                </div>
              </div>

              {/* 4. Base Date */}
              <div>
                <label className="block text-[10px] font-bold text-[#94a3b8] uppercase tracking-wider mb-1.5">
                  5. Base Date for Mining Plan (YYYY-MM)
                </label>
                <input
                  type="text"
                  value={baseDate}
                  onChange={(e) => setBaseDate(e.target.value)}
                  placeholder="2026-03"
                  required
                  className="w-full bg-[#0d1015] border border-[#252f3e] text-[#38bdf8] p-2.5 rounded-none font-mono focus:border-[#38bdf8] focus:outline-none font-bold"
                />
                <div className="text-[10px] text-[#64748b] mt-1">
                  Baseline accounting period for reserve calculation cascade, stripping ratio, and 5-yearly progressive closure schedules.
                </div>
              </div>

              {/* Statutory Guarantee Box */}
              <div className="p-4 bg-[#0d121a] border border-[#1e2a3b] text-[11px] text-[#94a3b8] space-y-1.5">
                <div className="font-bold text-[#f1f5f9] flex items-center gap-1.5 uppercase">
                  <Layers className="w-3.5 h-3.5 text-[#38bdf8]" />
                  <span>Compilation Integrity Assurances</span>
                </div>
                <ul className="list-disc list-inside space-y-1 text-[#cbd5e1] pl-1">
                  <li>Maps exactly 156 Chapter Parameters (133 fields + 23 prescribed tables) from verified evidence.</li>
                  <li>Executes 7-step UNFC reserve deduction lineage and Rule A/B closure calculations deterministically in Python.</li>
                  <li>Extracts grounded narrative strictly constrained to retrieved evidence using local LLM.</li>
                  <li>Preserves forensic document provenance (page numbers, chunk IDs) on all extracted values.</li>
                </ul>
              </div>

              {/* Action Buttons */}
              <div className="pt-3 border-t border-[#1e2531] flex items-center justify-end gap-3">
                <Link
                  to="/reports"
                  className="px-3.5 py-2 bg-[#161c24] hover:bg-[#1d2530] border border-[#273240] text-xs text-[#cbd5e1] transition-colors"
                >
                  CANCEL
                </Link>
                <button
                  type="submit"
                  disabled={submitting}
                  className="inline-flex items-center gap-2 px-5 py-2 bg-[#163352] hover:bg-[#1e446e] border border-[#28578b] text-xs font-bold text-[#93c5fd] transition-all disabled:opacity-50"
                >
                  {submitting ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      <span>COMPILING STATUTORY DOSSIER...</span>
                    </>
                  ) : (
                    <>
                      <FileText className="w-3.5 h-3.5" />
                      <span>INITIATE STATUTORY DOSSIER COMPILATION</span>
                    </>
                  )}
                </button>
              </div>

            </form>
          )}

        </div>
      </div>
    </div>
  );
};
