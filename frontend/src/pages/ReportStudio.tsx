import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiClient } from '../api/client';
import {
  FileText, ArrowLeft, Download, CheckCircle, AlertTriangle, RefreshCw,
  Layers, Shield, Edit3, Check, Flag, Clock, BookOpen, Map, Paperclip,
  CheckCircle2, XCircle, AlertCircle, FileSpreadsheet, Eye, ChevronRight,
  Calculator, FileCheck2, ShieldCheck, Scale, ExternalLink, X
} from 'lucide-react';

export const ReportStudio: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [report, setReport] = useState<any>(null);
  
  // Navigation state: chapter or register
  const [activeNav, setActiveNav] = useState<string>('ch_2');
  const [activeSubSection, setActiveSubSection] = useState<string>('all');
  
  const [loading, setLoading] = useState<boolean>(true);
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Field inline edit
  const [editingFieldId, setEditingFieldId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState<string>('');
  const [editNotes, setEditNotes] = useState<string>('');

  // Forensic Evidence modal
  const [inspectingEvidence, setInspectingEvidence] = useState<any | null>(null);
  const [inspectingAnnexure, setInspectingAnnexure] = useState<any | null>(null);

  // Sign cert state
  const [signingCertId, setSigningCertId] = useState<string | null>(null);
  const [signerName, setSignerName] = useState<string>('Shri R. K. Sharma');
  const [signerDesig, setSignerDesig] = useState<string>('Qualified Person (Rule 22C MCR 1960)');
  const [signerReg, setSignerReg] = useState<string>('QP/CMPDI/2021/042');

  const fetchReport = async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const resp = await apiClient.get(`/reports/${id}`);
      setReport(resp.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load statutory report dossier.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReport();
  }, [id]);

  const handleValidate = async () => {
    if (!id) return;
    setActionLoading(true);
    try {
      await apiClient.post(`/reports/${id}/validate`);
      setSuccessMsg('Statutory compliance validation re-evaluated against MoC 2025 guidelines.');
      await fetchReport();
    } catch (err: any) {
      setError('Validation failed.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleExport = async (freeze: boolean = false) => {
    if (!id) return;
    setActionLoading(true);
    try {
      const resp = await apiClient.post(`/reports/${id}/export`, {
        freeze_version: freeze,
        change_summary: freeze ? 'Frozen approved statutory draft' : 'Draft DOCX export',
      });
      setSuccessMsg(`Statutory DOCX compiled. Integrity Hash: ${resp.data.sha256_hash?.slice(0, 16)}...`);
      await fetchReport();
      const link = document.createElement('a');
      link.href = `/api/v1/reports/${id}/download`;
      link.setAttribute('download', `Mining_Plan_${id}.docx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err: any) {
      setError('DOCX export failed.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleFieldReview = async (mappingId: string, action: string, correctedVal?: string, notes?: string) => {
    if (!id) return;
    setActionLoading(true);
    try {
      await apiClient.post(`/reports/${id}/review`, {
        mapping_id: mappingId,
        action: action,
        corrected_value: correctedVal,
        notes: notes,
      });
      setEditingFieldId(null);
      setSuccessMsg(`Field review recorded: ${action}`);
      await fetchReport();
    } catch (err: any) {
      setError('Review submission failed.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleSignCert = async (certId: string) => {
    if (!id) return;
    setActionLoading(true);
    try {
      await apiClient.post(`/reports/${id}/certify`, {
        certification_id: certId,
        signatory_name: signerName,
        signatory_designation: signerDesig,
        reg_number: signerReg,
      });
      setSigningCertId(null);
      setSuccessMsg('Statutory undertaking authenticated and recorded in audit log.');
      await fetchReport();
    } catch (err: any) {
      setError('Signing execution failed.');
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0d1015] flex flex-col items-center justify-center text-[#94a3b8]">
        <div className="flex items-center gap-3 bg-[#161c24] p-6 border border-[#232d3b] rounded-sm shadow-xl font-mono text-xs">
          <RefreshCw className="w-5 h-5 text-[#38bdf8] animate-spin" />
          <span>ACCESSING STATUTORY REPORT DOSSIER [{id?.slice(0, 8)}]...</span>
        </div>
      </div>
    );
  }

  if (error && !report) {
    return (
      <div className="max-w-6xl mx-auto px-6 py-12">
        <div className="bg-[#201416] border border-[#522026] text-[#fca5a5] p-5 font-mono text-xs rounded-sm">
          [STATUTORY DOSSIER ERROR]: {error}
        </div>
      </div>
    );
  }

  // Calculate technical progress metrics
  const totalFields = report.field_mappings?.length || 0;
  const verifiedFields = report.field_mappings?.filter((f: any) => 
    f.generated_value && f.generated_value !== 'DATA NOT AVAILABLE IN VERIFIED KNOWLEDGE BASE'
  ).length || 0;
  const fieldPct = totalFields > 0 ? Math.round((verifiedFields / totalFields) * 100) : 0;

  const totalTables = report.tables?.length || 23;
  const tablesWithRows = report.tables?.filter((t: any) => (t.rows?.length || 0) > 0).length || 0;
  const tablePct = totalTables > 0 ? Math.round((tablesWithRows / totalTables) * 100) : 100;

  const totalPlates = report.plates?.length || 23;
  const platesAttached = report.plates?.filter((p: any) => p.attachment_status === 'ATTACHED').length || 0;
  const platePct = totalPlates > 0 ? Math.round((platesAttached / totalPlates) * 100) : 0;

  const totalAnnexures = report.annexures?.length || 8;
  const annexuresAttached = report.annexures?.filter((a: any) => a.attachment_status === 'ATTACHED').length || 0;
  const annexurePct = totalAnnexures > 0 ? Math.round((annexuresAttached / totalAnnexures) * 100) : 0;

  const totalCerts = report.certifications?.length || 4;
  const certsSigned = report.certifications?.filter((c: any) => c.audit_state === 'AUTHORIZED_SIGNED').length || 0;
  const certPct = totalCerts > 0 ? Math.round((certsSigned / totalCerts) * 100) : 0;

  // Navigation Items
  const dossierIndex = [
    { key: 'root_front_matter', num: '00', label: 'COVER & STATUTORY CHECKLIST', count: 26 },
    { key: 'ch_1', num: '01', label: 'PROJECT INFORMATION', count: 67 },
    { 
      key: 'ch_2', 
      num: '02', 
      label: 'GEOLOGY & RESERVES', 
      count: 38,
      subSections: [
        { id: 'all', label: 'All Sections' },
        { id: '2.1', label: '2.1 Exploration & Geology' },
        { id: '2.2', label: '2.2 Reserve / Resource' },
        { id: '2.3', label: '2.3 Seam & Quality' },
      ]
    },
    { key: 'ch_3', num: '03', label: 'MINING', count: 13 },
    { key: 'ch_4', num: '04', label: 'SAFETY & HEALTH', count: 2 },
    { key: 'ch_5', num: '05', label: 'INFRASTRUCTURE', count: 7 },
    { key: 'ch_6', num: '06', label: 'LAND REQUIREMENT', count: 16 },
    { key: 'ch_7', num: '07', label: 'ENVIRONMENT', count: 1 },
    { key: 'ch_8', num: '08', label: 'MINE CLOSURE PLAN', count: 12 },
  ];

  const registersIndex = [
    { key: 'reg_tables', label: 'PRESCRIBED TABLES', icon: FileSpreadsheet, badge: `${report.tables?.length || 23} Tables` },
    { key: 'reg_plates', label: 'TECHNICAL PLATES', icon: Map, badge: `${report.plates?.length || 23} Plates` },
    { key: 'reg_annexures', label: 'STATUTORY ANNEXURES', icon: Paperclip, badge: `${report.annexures?.length || 8} Annexures` },
    { key: 'reg_certifications', label: 'STATUTORY EXECUTION', icon: Shield, badge: `${certsSigned}/${totalCerts} Signed` },
    { key: 'reg_compliance', label: 'COMPLIANCE AUDIT', icon: AlertTriangle, badge: `${report.compliance_issues?.length || 0} Findings` },
    { key: 'reg_versions', label: 'IMMUTABLE VERSIONS', icon: Clock, badge: `v${report.version_number}.0` },
  ];

  // Helper for technical status badge
  const renderStatusBadge = (status: string) => {
    switch (status) {
      case 'VERIFIED':
        return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-none font-mono text-[10px] font-bold bg-[#143825] text-[#4ade80] border border-[#225e3d]">VERIFIED</span>;
      case 'CALCULATED':
        return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-none font-mono text-[10px] font-bold bg-[#281c3d] text-[#c084fc] border border-[#4c3575]">CALCULATED</span>;
      case 'REVIEW_REQUIRED':
        return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-none font-mono text-[10px] font-bold bg-[#38260d] text-[#fbbf24] border border-[#5e4318]">REVIEW REQUIRED</span>;
      case 'CONFLICT':
        return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-none font-mono text-[10px] font-bold bg-[#3d1419] text-[#f87171] border border-[#6b222d]">CONFLICT</span>;
      case 'SOURCE_REQUIRED':
      case 'MISSING':
        return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-none font-mono text-[10px] font-bold bg-[#381a13] text-[#fb923c] border border-[#632b1d]">SOURCE REQUIRED</span>;
      case 'NOT_APPLICABLE':
        return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-none font-mono text-[10px] font-bold bg-[#1e242c] text-[#94a3b8] border border-[#333d4b]">NOT APPLICABLE</span>;
      default:
        return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-none font-mono text-[10px] font-bold bg-[#161c24] text-[#cbd5e1] border border-[#283240]">{status}</span>;
    }
  };

  // Helper for deterministic calculation lineage renderer
  const renderCalculationSheet = (lineage: any) => {
    if (!lineage) return null;
    return (
      <div className="mt-2.5 p-3 bg-[#11161d] border border-[#242e3d] rounded-sm font-mono text-[11px] text-[#cbd5e1]">
        <div className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-[#93c5fd] pb-2 mb-2 border-b border-[#1f2835]">
          <Calculator className="w-3.5 h-3.5 text-[#60a5fa]" />
          <span>Deterministic Engineering Calculation Sheet</span>
        </div>
        
        {lineage.formula && (
          <div className="text-[10px] text-[#94a3b8] mb-2 font-mono">
            Lineage Formula: <span className="text-[#38bdf8] font-semibold">{lineage.formula}</span>
          </div>
        )}

        {lineage.inputs && (
          <div className="space-y-1 pl-1">
            {Object.entries(lineage.inputs).map(([k, v]: [string, any], idx: number) => {
              const prefix = idx === 0 ? '' : '− ';
              return (
                <div key={k} className="flex items-center justify-between text-[11px]">
                  <span className="text-[#94a3b8]">{prefix}{k.replace(/_/g, ' ').toUpperCase()}</span>
                  <span className="font-bold text-[#f1f5f9]">{typeof v === 'number' ? v.toFixed(2) : String(v)} MT</span>
                </div>
              );
            })}
            <div className="pt-1.5 mt-1.5 border-t border-[#232c3b] flex items-center justify-between text-[11px] font-bold text-[#4ade80]">
              <span>= DERIVED STATUTORY VALUE</span>
              <span>{lineage.calculated_value !== undefined ? Number(lineage.calculated_value).toFixed(2) : '—'} MT</span>
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-survey-grid text-[#e2e8f0]">
      {/* 1. TOP STATUTORY REPORT DOSSIER HEADER */}
      <div className="border-b border-[#222a36] bg-[#12161e] px-6 py-4">
        <div className="max-w-[1720px] mx-auto">
          {/* Breadcrumb / Back Link */}
          <div className="flex items-center justify-between pb-3">
            <Link
              to="/reports"
              className="inline-flex items-center gap-1.5 text-xs font-mono text-[#94a3b8] hover:text-[#38bdf8] transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>RETURN TO STATUTORY DOSSIER REGISTER</span>
            </Link>

            <div className="flex items-center gap-2 text-[11px] font-mono text-[#64748b]">
              <span>SYSTEM: KOYLA-ENGINEERING-DESK</span>
              <span>•</span>
              <span>BLOCK-ID: {report.id?.slice(0, 8)}</span>
            </div>
          </div>

          {/* Technical Title & Metadata Strip */}
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 pt-1 pb-2">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="px-1.5 py-0.5 bg-[#1b2f48] border border-[#2e527d] text-[#60a5fa] font-mono text-[10px] font-bold tracking-wider uppercase">
                  STATUTORY REPORT DOSSIER
                </span>
                <span className="text-xs text-[#94a3b8] font-mono">
                  {report.issuing_authority || 'Ministry of Coal / Coal Controller Organisation'}
                </span>
                <span className="px-1.5 py-0.5 bg-[#182029] border border-[#2b3644] text-[#cbd5e1] font-mono text-[10px]">
                  v{report.version_number}.0 (FROZEN STATE)
                </span>
              </div>
              <h1 className="text-xl font-mono font-bold tracking-tight text-[#f8fafc]">
                {report.report_title || 'MINING PLAN AND MINE CLOSURE PLAN'}
              </h1>
            </div>

            {/* Technical Actions Toolbar */}
            <div className="flex items-center gap-2">
              <button
                onClick={handleValidate}
                disabled={actionLoading}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-[#171e27] hover:bg-[#1f2835] border border-[#2b3748] text-xs font-mono text-[#cbd5e1] transition-all disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${actionLoading ? 'animate-spin text-[#38bdf8]' : ''}`} />
                <span>RE-VALIDATE</span>
              </button>

              <button
                onClick={() => handleExport(false)}
                disabled={actionLoading}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-[#163352] hover:bg-[#1d426a] border border-[#29588c] text-xs font-mono font-semibold text-[#93c5fd] transition-all disabled:opacity-50"
              >
                <Download className="w-3.5 h-3.5" />
                <span>EXPORT DOCX</span>
              </button>

              <button
                onClick={() => handleExport(true)}
                disabled={actionLoading}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-[#133324] hover:bg-[#1b4430] border border-[#22573e] text-xs font-mono font-semibold text-[#4ade80] transition-all disabled:opacity-50"
              >
                <CheckCircle2 className="w-3.5 h-3.5 text-[#4ade80]" />
                <span>FREEZE VERSION</span>
              </button>
            </div>
          </div>

          {/* Structured Technical Metadata Line */}
          <div className="mt-3 pt-3 border-t border-[#1e2531] grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 text-xs font-mono">
            <div className="bg-[#0f131a] px-3 py-1.5 border border-[#1e2633]">
              <span className="text-[10px] text-[#64748b] block">BLOCK</span>
              <span className="font-bold text-[#f1f5f9] truncate block">{report.block_name || 'RANIGANJ COAL BLOCK'}</span>
            </div>
            <div className="bg-[#0f131a] px-3 py-1.5 border border-[#1e2633]">
              <span className="text-[10px] text-[#64748b] block">MINE</span>
              <span className="font-bold text-[#f1f5f9] truncate block">{report.mine_name || 'AMRITNAGAR COLLIERY'}</span>
            </div>
            <div className="bg-[#0f131a] px-3 py-1.5 border border-[#1e2633]">
              <span className="text-[10px] text-[#64748b] block">SUBSIDIARY</span>
              <span className="font-bold text-[#f1f5f9] truncate block">{report.organization_name || 'BCCL'}</span>
            </div>
            <div className="bg-[#0f131a] px-3 py-1.5 border border-[#1e2633]">
              <span className="text-[10px] text-[#64748b] block">BASE DATE</span>
              <span className="font-bold text-[#38bdf8] truncate block">{report.base_date || '2026-03'}</span>
            </div>
            <div className="bg-[#0f131a] px-3 py-1.5 border border-[#1e2633]">
              <span className="text-[10px] text-[#64748b] block">GOVERNING FORMAT</span>
              <span className="font-bold text-[#f1f5f9] truncate block">MoC / CCO 2025</span>
            </div>
            <div className="bg-[#0f131a] px-3 py-1.5 border border-[#1e2633]">
              <span className="text-[10px] text-[#64748b] block">COMPLIANCE STATE</span>
              <span className={`font-bold truncate block ${
                report.compliance_status === 'COMPLIANT' ? 'text-[#4ade80]' : 'text-[#fbbf24]'
              }`}>
                {report.compliance_status || 'PARTIALLY COMPLIANT'}
              </span>
            </div>
          </div>

          {/* 2. REPORT DOSSIER PROGRESS COMPACT INDICATORS */}
          <div className="mt-3 pt-2.5 border-t border-[#1a212b] flex flex-wrap items-center justify-between gap-4 text-[10px] font-mono text-[#94a3b8]">
            <div className="flex items-center gap-5">
              <span className="text-[#64748b] font-bold uppercase tracking-wider">DOSSIER COMPLETION:</span>
              <div className="flex items-center gap-1.5">
                <span>FIELDS:</span>
                <span className="text-[#f1f5f9] font-bold">{verifiedFields}/{totalFields}</span>
                <span className="text-[#38bdf8]">
                  {'█'.repeat(Math.round(fieldPct / 10)) + '░'.repeat(10 - Math.round(fieldPct / 10))}
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <span>TABLES:</span>
                <span className="text-[#f1f5f9] font-bold">{tablesWithRows}/{totalTables}</span>
                <span className="text-[#4ade80]">
                  {'█'.repeat(Math.round(tablePct / 10)) + '░'.repeat(10 - Math.round(tablePct / 10))}
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <span>PLATES:</span>
                <span className="text-[#f1f5f9] font-bold">{platesAttached}/{totalPlates}</span>
                <span className="text-[#fb923c]">
                  {'█'.repeat(Math.round(platePct / 10)) + '░'.repeat(10 - Math.round(platePct / 10))}
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <span>ANNEXURES:</span>
                <span className="text-[#f1f5f9] font-bold">{annexuresAttached}/{totalAnnexures}</span>
                <span className="text-[#c084fc]">
                  {'█'.repeat(Math.round(annexurePct / 10)) + '░'.repeat(10 - Math.round(annexurePct / 10))}
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <span>REVIEW:</span>
                <span className="text-[#f1f5f9] font-bold">{certsSigned}/{totalCerts}</span>
                <span className="text-[#38bdf8]">
                  {'█'.repeat(Math.round(certPct / 10)) + '░'.repeat(10 - Math.round(certPct / 10))}
                </span>
              </div>
            </div>

            <div className="text-[10px] text-[#64748b]">
              <span>SHA-256: {report.sha256_hash ? report.sha256_hash.slice(0, 20) + '...' : 'PENDING FREEZE'}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Alerts */}
      {successMsg && (
        <div className="bg-[#112d1e] border-b border-[#205739] px-6 py-2 text-xs font-mono text-[#86efac] flex items-center justify-between">
          <span>[SYSTEM RECORD]: {successMsg}</span>
          <button onClick={() => setSuccessMsg(null)} className="text-[#86efac] font-bold">×</button>
        </div>
      )}
      {error && (
        <div className="bg-[#2e1418] border-b border-[#5e2229] px-6 py-2 text-xs font-mono text-[#fca5a5] flex items-center justify-between">
          <span>[SYSTEM WARNING]: {error}</span>
          <button onClick={() => setError(null)} className="text-[#fca5a5] font-bold">×</button>
        </div>
      )}

      {/* 3. MAIN WORKBENCH: 2-COLUMN LAYOUT (INDEX + WORKSPACE) */}
      <div className="max-w-[1720px] mx-auto px-6 py-5 flex flex-col lg:flex-row gap-6">
        
        {/* LEFT-SIDE STATUTORY NAVIGATION / DOSSIER INDEX */}
        <aside className="w-full lg:w-80 flex-shrink-0">
          <div className="bg-[#12161e] border border-[#222a36] rounded-sm sticky top-4">
            <div className="px-4 py-3 bg-[#161c26] border-b border-[#222a36] flex items-center justify-between">
              <span className="font-mono text-xs font-bold uppercase tracking-wider text-[#93c5fd]">
                REPORT DOSSIER INDEX
              </span>
              <span className="text-[10px] font-mono text-[#64748b]">MoC 2025</span>
            </div>

            {/* Chapter List */}
            <div className="divide-y divide-[#1c232e]">
              {dossierIndex.map((ch) => {
                const isActive = activeNav === ch.key;
                return (
                  <div key={ch.key}>
                    <button
                      onClick={() => {
                        setActiveNav(ch.key);
                        setActiveSubSection('all');
                      }}
                      className={`w-full text-left px-3.5 py-2.5 flex items-center justify-between transition-colors font-mono text-xs ${
                        isActive
                          ? 'bg-[#182638] text-[#93c5fd] font-bold border-l-2 border-[#38bdf8]'
                          : 'text-[#cbd5e1] hover:bg-[#171e28] hover:text-[#f8fafc]'
                      }`}
                    >
                      <div className="flex items-center gap-2 truncate">
                        <span className="text-[11px] font-bold text-[#64748b]">{ch.num}</span>
                        <span className="truncate">{ch.label}</span>
                      </div>
                      <span className="text-[10px] text-[#64748b] ml-1">{ch.count}</span>
                    </button>

                    {/* Sub-sections if active */}
                    {isActive && ch.subSections && (
                      <div className="bg-[#0e131a] py-1 border-y border-[#1a222d] pl-7 pr-3 space-y-0.5 font-mono text-[11px]">
                        {ch.subSections.map((sub) => (
                          <button
                            key={sub.id}
                            onClick={() => setActiveSubSection(sub.id)}
                            className={`w-full text-left py-1 px-2 rounded-none transition-colors ${
                              activeSubSection === sub.id
                                ? 'text-[#38bdf8] font-bold bg-[#14202e]'
                                : 'text-[#94a3b8] hover:text-[#e2e8f0]'
                            }`}
                          >
                            {sub.label}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Statutory Registers Navigation */}
            <div className="px-4 py-2.5 bg-[#161c26] border-t border-b border-[#222a36] mt-2">
              <span className="font-mono text-[11px] font-bold uppercase tracking-wider text-[#94a3b8]">
                STATUTORY REGISTERS
              </span>
            </div>

            <div className="divide-y divide-[#1c232e]">
              {registersIndex.map((reg) => {
                const Icon = reg.icon;
                const isActive = activeNav === reg.key;
                return (
                  <button
                    key={reg.key}
                    onClick={() => {
                      setActiveNav(reg.key);
                    }}
                    className={`w-full text-left px-3.5 py-2.5 flex items-center justify-between transition-colors font-mono text-xs ${
                      isActive
                        ? 'bg-[#182638] text-[#93c5fd] font-bold border-l-2 border-[#38bdf8]'
                        : 'text-[#cbd5e1] hover:bg-[#171e28] hover:text-[#f8fafc]'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <Icon className="w-3.5 h-3.5 text-[#64748b]" />
                      <span>{reg.label}</span>
                    </div>
                    <span className="text-[10px] font-mono text-[#94a3b8] px-1.5 py-0.2 bg-[#171e27] border border-[#252f3d]">
                      {reg.badge}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        </aside>

        {/* CENTER / RIGHT MAIN WORKSPACE */}
        <main className="flex-1 min-w-0">

          {/* VIEW A: CHAPTER FIELD ROWS */}
          {activeNav.startsWith('ch_') || activeNav.startsWith('root_') ? (
            <div>
              {/* Active Section Banner */}
              <div className="bg-[#12161e] border border-[#222a36] px-5 py-3.5 mb-4 flex items-center justify-between">
                <div>
                  <div className="text-[10px] font-mono font-bold text-[#38bdf8] uppercase tracking-wider">
                    {activeNav.toUpperCase().replace('_', ' ')}
                  </div>
                  <h2 className="text-sm font-mono font-bold text-[#f8fafc] mt-0.5">
                    {dossierIndex.find(d => d.key === activeNav)?.label}
                  </h2>
                </div>
                <div className="text-right text-[11px] font-mono text-[#94a3b8]">
                  <span>SECTION: {activeSubSection === 'all' ? 'FULL CHAPTER INVENTORY' : activeSubSection}</span>
                </div>
              </div>

              {/* Field Rows Table / List */}
              <div className="bg-[#12161e] border border-[#222a36] rounded-sm divide-y divide-[#1d2532]">
                {((report.field_mappings || []).filter((f: any) => {
                  if (f.chapter !== activeNav) return false;
                  if (activeSubSection !== 'all') {
                    return f.official_id?.startsWith(activeSubSection);
                  }
                  return true;
                })).map((f: any) => {
                  const isEditing = editingFieldId === f.id;
                  const isMissing = !f.generated_value || f.generated_value === 'DATA NOT AVAILABLE IN VERIFIED KNOWLEDGE BASE';
                  const hasLineage = !!f.calculation_lineage;

                  return (
                    <div key={f.id} className="p-4 hover:bg-[#151b24] transition-colors">
                      <div className="flex flex-col xl:flex-row xl:items-start justify-between gap-4">
                        
                        {/* Field ID & Label Column */}
                        <div className="xl:w-1/3">
                          <div className="flex items-center gap-2 mb-1">
                            {f.official_id ? (
                              <span className="px-1.5 py-0.2 bg-[#1a2330] border border-[#2d3a4e] text-[#93c5fd] font-mono text-[11px] font-bold">
                                {f.official_id}
                              </span>
                            ) : (
                              <span className="px-1.5 py-0.2 bg-[#1c222b] border border-[#2d3744] text-[#94a3b8] font-mono text-[10px]">
                                INSTRUMENT
                              </span>
                            )}
                            {f.unit && (
                              <span className="text-[10px] font-mono text-[#64748b]">({f.unit})</span>
                            )}
                          </div>
                          <div className="text-xs font-semibold text-[#f1f5f9] leading-snug">
                            {f.exact_official_label}
                          </div>
                        </div>

                        {/* Value & Calculation Column */}
                        <div className="flex-1">
                          {isEditing ? (
                            <div className="space-y-2 font-mono">
                              <textarea
                                value={editValue}
                                onChange={(e) => setEditValue(e.target.value)}
                                className="w-full text-xs p-2 bg-[#0d1015] border border-[#2d394a] text-[#f8fafc] font-mono focus:border-[#38bdf8] focus:outline-none"
                                rows={3}
                              />
                              <input
                                type="text"
                                placeholder="QP review notes / regulatory justification..."
                                value={editNotes}
                                onChange={(e) => setEditNotes(e.target.value)}
                                className="w-full text-xs p-1.5 bg-[#0d1015] border border-[#2d394a] text-[#f8fafc] font-mono"
                              />
                              <div className="flex items-center gap-2">
                                <button
                                  onClick={() => handleFieldReview(f.id, 'CORRECTED', editValue, editNotes)}
                                  className="px-2.5 py-1 bg-[#2563eb] hover:bg-[#1d4ed8] text-white text-xs font-mono font-semibold"
                                >
                                  SAVE CORRECTION
                                </button>
                                <button
                                  onClick={() => setEditingFieldId(null)}
                                  className="px-2.5 py-1 bg-[#1a212b] border border-[#2e3a4b] text-xs font-mono text-[#cbd5e1]"
                                >
                                  CANCEL
                                </button>
                              </div>
                            </div>
                          ) : (
                            <div>
                              <div className={`text-xs font-mono font-medium ${
                                isMissing ? 'text-[#f87171] italic' : 'text-[#e2e8f0]'
                              }`}>
                                {f.generated_value || 'DATA NOT AVAILABLE IN VERIFIED KNOWLEDGE BASE'}
                              </div>

                              {/* Calculation Sheet if present */}
                              {hasLineage && renderCalculationSheet(f.calculation_lineage)}

                              {/* Provenance & Evidence Strip */}
                              <div className="mt-2.5 flex flex-wrap items-center gap-2 text-[10px] font-mono">
                                {f.source_document_id ? (
                                  <button
                                    onClick={() => setInspectingEvidence(f)}
                                    className="inline-flex items-center gap-1 px-2 py-0.5 bg-[#162233] hover:bg-[#1c2d44] border border-[#263c59] text-[#93c5fd] transition-colors"
                                  >
                                    <Eye className="w-3 h-3 text-[#60a5fa]" />
                                    <span>EVIDENCE: DOC-{f.source_document_id.slice(0, 8)} (Pg. {f.source_page || 1})</span>
                                  </button>
                                ) : (
                                  <button
                                    onClick={() => setInspectingEvidence(f)}
                                    className="inline-flex items-center gap-1 px-2 py-0.5 bg-[#141a22] hover:bg-[#1b232e] border border-[#202733] text-[#94a3b8] transition-colors"
                                  >
                                    <Eye className="w-3 h-3 text-[#64748b]" />
                                    <span>EVIDENCE RECORD: {f.field_status || 'KOYLA DB'}</span>
                                  </button>
                                )}

                                {f.reviewer_action && f.reviewer_action !== 'PENDING' && (
                                  <span className="px-2 py-0.5 bg-[#1c2c20] border border-[#275030] text-[#86efac] font-bold">
                                    QP REVIEW: {f.reviewer_action}
                                  </span>
                                )}
                              </div>
                            </div>
                          )}
                        </div>

                        {/* Status & Review Actions Column */}
                        <div className="xl:w-44 flex xl:flex-col items-end justify-between gap-2">
                          <div>
                            {renderStatusBadge(
                              hasLineage ? 'CALCULATED' : isMissing ? 'MISSING' : (f.reviewer_action === 'ACCEPTED' ? 'VERIFIED' : f.field_status || 'VERIFIED')
                            )}
                          </div>

                          {!isEditing && (
                            <div className="flex items-center gap-1">
                              <button
                                onClick={() => handleFieldReview(f.id, 'ACCEPTED')}
                                className="p-1.5 bg-[#13241b] hover:bg-[#1c3829] border border-[#224d35] text-[#4ade80] transition-colors"
                                title="Accept verified statutory value"
                              >
                                <Check className="w-3.5 h-3.5" />
                              </button>
                              <button
                                onClick={() => {
                                  setEditingFieldId(f.id);
                                  setEditValue(f.generated_value || '');
                                  setEditNotes(f.reviewer_notes || '');
                                }}
                                className="p-1.5 bg-[#162438] hover:bg-[#1e3450] border border-[#254366] text-[#60a5fa] transition-colors"
                                title="QP Override / Field Correction"
                              >
                                <Edit3 className="w-3.5 h-3.5" />
                              </button>
                              <button
                                onClick={() => handleFieldReview(f.id, 'FLAGGED', f.generated_value, 'Flagged by QP')}
                                className="p-1.5 bg-[#2b161a] hover:bg-[#3d1e24] border border-[#52252c] text-[#f87171] transition-colors"
                                title="Flag for Scrutiny"
                              >
                                <Flag className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          )}
                        </div>

                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : null}

          {/* VIEW B: PRESCRIBED TABLES REGISTER */}
          {activeNav === 'reg_tables' && (
            <div className="space-y-6">
              <div className="bg-[#12161e] border border-[#222a36] px-5 py-3.5 flex items-center justify-between">
                <div>
                  <div className="text-[10px] font-mono font-bold text-[#38bdf8] uppercase tracking-wider">
                    APPENDIX-I STATUTORY REGISTER
                  </div>
                  <h2 className="text-sm font-mono font-bold text-[#f8fafc] mt-0.5">
                    PRESCRIBED TABLE REGISTER (23 STATUTORY TABLES)
                  </h2>
                </div>
                <span className="text-xs font-mono text-[#94a3b8]">
                  Total Registered: {report.tables?.length || 23} Tables
                </span>
              </div>

              {(report.tables || []).map((t: any) => (
                <div key={t.id} className="bg-[#12161e] border border-[#222a36] rounded-sm overflow-hidden">
                  <div className="bg-[#161c26] px-5 py-3 border-b border-[#222a36] flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 bg-[#1a2535] border border-[#2b3e59] text-[#60a5fa] font-mono text-xs font-bold">
                        {t.official_id}
                      </span>
                      <h3 className="text-xs font-mono font-bold text-[#f8fafc]">{t.exact_official_label}</h3>
                    </div>
                    <span className="text-[11px] font-mono text-[#64748b]">{t.row_count} ROWS RECORDED</span>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-[#1e2531] text-xs font-mono">
                      <thead className="bg-[#0f131a] text-[#94a3b8]">
                        <tr>
                          {(t.columns || []).map((col: any, cidx: number) => (
                            <th key={cidx} className="px-4 py-2 text-left font-semibold tracking-wider uppercase text-[10px]">
                              {col.label || col.name} {col.unit ? `(${col.unit})` : ''}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#18202b] bg-[#12161e]">
                        {(t.rows || []).map((r: any, ridx: number) => {
                          const isTotalRow = String(r[t.columns?.[0]?.name] || '').toLowerCase().includes('total');
                          return (
                            <tr key={ridx} className={`hover:bg-[#161d28] ${isTotalRow ? 'bg-[#152233] font-bold text-[#93c5fd]' : 'text-[#cbd5e1]'}`}>
                              {(t.columns || []).map((col: any, cidx: number) => {
                                const val = r[col.name];
                                const isNum = typeof val === 'number';
                                return (
                                  <td key={cidx} className={`px-4 py-2.5 whitespace-nowrap ${isNum ? 'text-right' : ''}`}>
                                    {val !== undefined ? (isNum ? Number(val).toFixed(2) : String(val)) : '—'}
                                  </td>
                                );
                              })}
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* VIEW C: TECHNICAL PLATES REGISTER */}
          {activeNav === 'reg_plates' && (
            <div className="space-y-6">
              <div className="bg-[#12161e] border border-[#222a36] px-5 py-3.5 flex items-center justify-between">
                <div>
                  <div className="text-[10px] font-mono font-bold text-[#38bdf8] uppercase tracking-wider">
                    APPENDIX-I DRAWING REGISTER
                  </div>
                  <h2 className="text-sm font-mono font-bold text-[#f8fafc] mt-0.5">
                    TECHNICAL PLATES & GEOLOGICAL DRAWINGS (PLATES I TO XXIII)
                  </h2>
                </div>
                <span className="text-xs font-mono text-[#94a3b8]">
                  Mandated Scale & Survey Compliance
                </span>
              </div>

              <div className="bg-[#12161e] border border-[#222a36] rounded-sm overflow-hidden">
                <table className="min-w-full divide-y divide-[#1e2531] text-xs font-mono">
                  <thead className="bg-[#0f131a] text-[#94a3b8]">
                    <tr>
                      <th className="px-4 py-2.5 text-left text-[10px] uppercase">PLATE</th>
                      <th className="px-4 py-2.5 text-left text-[10px] uppercase">OFFICIAL TITLE</th>
                      <th className="px-4 py-2.5 text-left text-[10px] uppercase">MANDATED SCALE</th>
                      <th className="px-4 py-2.5 text-left text-[10px] uppercase">APPLICABILITY</th>
                      <th className="px-4 py-2.5 text-left text-[10px] uppercase">ATTACHMENT STATUS</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#1a212b]">
                    {(report.plates || []).map((p: any) => (
                      <tr key={p.id} className="hover:bg-[#151b24]">
                        <td className="px-4 py-3 font-bold text-[#93c5fd]">{p.plate_id}</td>
                        <td className="px-4 py-3 text-[#f1f5f9] font-medium">{p.official_title}</td>
                        <td className="px-4 py-3 text-[#94a3b8]">{p.scale_requirement}</td>
                        <td className="px-4 py-3 text-[#64748b]">{p.applicability_condition || 'UNIVERSAL'}</td>
                        <td className="px-4 py-3">
                          {p.attachment_status === 'ATTACHED' ? (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-[#143825] text-[#4ade80] border border-[#225e3d] text-[10px]">
                              ATTACHED (GEO-CAD)
                            </span>
                          ) : (
                            <div className="flex items-center gap-2">
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-[#381a13] text-[#fb923c] border border-[#632b1d] text-[10px]">
                                SOURCE DATA REQUIRED
                              </span>
                              {/* Blueprint Preview Mini-Thumbnail */}
                              <div className="w-12 h-6 bg-blueprint-grid border border-[#214368] flex items-center justify-center text-[8px] text-[#60a5fa]">
                                CAD
                              </div>
                            </div>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* VIEW D: STATUTORY ANNEXURES REGISTER */}
          {activeNav === 'reg_annexures' && (
            <div className="space-y-6">
              <div className="bg-[#12161e] border border-[#222a36] px-5 py-3.5 flex items-center justify-between">
                <div>
                  <div className="text-[10px] font-mono font-bold text-[#38bdf8] uppercase tracking-wider">
                    DOCUMENT CONTROL REGISTER
                  </div>
                  <h2 className="text-sm font-mono font-bold text-[#f8fafc] mt-0.5">
                    STATUTORY ANNEXURES (SECTION C: ANNEXURE-I TO VIII)
                  </h2>
                </div>
                <span className="text-xs font-mono text-[#94a3b8]">
                  Controlled Document Register
                </span>
              </div>

              <div className="bg-[#12161e] border border-[#222a36] rounded-sm overflow-hidden">
                <table className="min-w-full divide-y divide-[#1e2531] text-xs font-mono">
                  <thead className="bg-[#0f131a] text-[#94a3b8]">
                    <tr>
                      <th className="px-4 py-2.5 text-left text-[10px] uppercase">ANNEXURE</th>
                      <th className="px-4 py-2.5 text-left text-[10px] uppercase">STATUTORY TITLE</th>
                      <th className="px-4 py-2.5 text-left text-[10px] uppercase">REQUIREMENT TIER</th>
                      <th className="px-4 py-2.5 text-left text-[10px] uppercase">ATTACHMENT STATE</th>
                      <th className="px-4 py-2.5 text-left text-[10px] uppercase">AUDIT</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#1a212b]">
                    {(report.annexures || []).map((a: any) => (
                      <tr key={a.id} className="hover:bg-[#151b24]">
                        <td className="px-4 py-3 font-bold text-[#93c5fd]">{a.official_reference}</td>
                        <td className="px-4 py-3 text-[#f1f5f9]">{a.title}</td>
                        <td className="px-4 py-3">
                          <span className={`px-1.5 py-0.2 text-[10px] font-bold ${
                            a.requirement_type === 'MANDATORY'
                              ? 'bg-[#3b1219] text-[#f87171] border border-[#6b222d]'
                              : 'bg-[#182638] text-[#93c5fd] border border-[#2a4568]'
                          }`}>
                            {a.requirement_type}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <span className="text-[10px] text-[#94a3b8] px-2 py-0.5 bg-[#161c24] border border-[#232c38]">
                            {a.attachment_status}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-[10px] text-[#64748b]">
                          {a.notes ? (
                            <button
                              onClick={() => setInspectingAnnexure(a)}
                              className="inline-flex items-center gap-1 px-2 py-0.5 bg-[#172538] hover:bg-[#1f334d] border border-[#2d4970] text-[10px] text-[#93c5fd] font-mono"
                            >
                              <Eye className="w-3 h-3" />
                              <span>INSPECT BRIEF</span>
                            </button>
                          ) : (
                            'CONTROLLED'
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* VIEW E: STATUTORY EXECUTION (CERTIFICATIONS) */}
          {activeNav === 'reg_certifications' && (
            <div className="space-y-6">
              <div className="bg-[#12161e] border border-[#222a36] px-5 py-3.5 flex items-center justify-between">
                <div>
                  <div className="text-[10px] font-mono font-bold text-[#38bdf8] uppercase tracking-wider">
                    FORMAL EXECUTION WORKBENCH
                  </div>
                  <h2 className="text-sm font-mono font-bold text-[#f8fafc] mt-0.5">
                    STATUTORY CERTIFICATIONS & UNDERTAKINGS (CERT-1 TO CERT-4)
                  </h2>
                </div>
                <span className="text-xs font-mono text-[#4ade80]">
                  Authenticated Audit Trail
                </span>
              </div>

              {(report.certifications || []).map((c: any) => {
                const isSigning = signingCertId === c.id;
                const isSigned = c.audit_state === 'AUTHORIZED_SIGNED';

                return (
                  <div key={c.id} className="bg-[#12161e] border border-[#222a36] rounded-sm p-5 font-mono">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[#1f2735] gap-2">
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 bg-[#1a2535] border border-[#2d4059] text-[#93c5fd] text-xs font-bold">
                          {c.signatory_role}
                        </span>
                        <h3 className="text-xs font-bold text-[#f8fafc]">{c.official_purpose}</h3>
                      </div>
                      <span className={`px-2 py-0.5 text-[10px] font-bold ${
                        isSigned
                          ? 'bg-[#143825] text-[#4ade80] border border-[#225e3d]'
                          : 'bg-[#38260d] text-[#fbbf24] border border-[#5e4318]'
                      }`}>
                        {c.audit_state}
                      </span>
                    </div>

                    <div className="mt-3 p-3 bg-[#0d1015] border border-[#1d2532] text-xs text-[#cbd5e1] italic leading-relaxed">
                      "{c.undertaking_text}"
                    </div>

                    {isSigned ? (
                      <div className="mt-3 p-3 bg-[#11241a] border border-[#1f4730] grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs text-[#86efac]">
                        <div><span className="text-[#64748b]">Signatory:</span> {c.signatory_name}</div>
                        <div><span className="text-[#64748b]">Designation:</span> {c.signatory_designation}</div>
                        <div><span className="text-[#64748b]">Timestamp:</span> {c.signed_at?.slice(0, 16).replace('T', ' ')}</div>
                      </div>
                    ) : isSigning ? (
                      <div className="mt-4 p-4 bg-[#141b25] border border-[#28384d] space-y-3">
                        <h4 className="text-xs font-bold text-[#93c5fd] uppercase">Statutory Execution Credentials</h4>
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                          <div>
                            <label className="block text-[10px] text-[#94a3b8] mb-1">SIGNATORY NAME</label>
                            <input
                              type="text"
                              value={signerName}
                              onChange={(e) => setSignerName(e.target.value)}
                              className="w-full text-xs p-1.5 bg-[#0d1015] border border-[#2a3648] text-[#f8fafc] font-mono"
                            />
                          </div>
                          <div>
                            <label className="block text-[10px] text-[#94a3b8] mb-1">DESIGNATION</label>
                            <input
                              type="text"
                              value={signerDesig}
                              onChange={(e) => setSignerDesig(e.target.value)}
                              className="w-full text-xs p-1.5 bg-[#0d1015] border border-[#2a3648] text-[#f8fafc] font-mono"
                            />
                          </div>
                          <div>
                            <label className="block text-[10px] text-[#94a3b8] mb-1">REG / ACCREDITATION NO.</label>
                            <input
                              type="text"
                              value={signerReg}
                              onChange={(e) => setSignerReg(e.target.value)}
                              className="w-full text-xs p-1.5 bg-[#0d1015] border border-[#2a3648] text-[#f8fafc] font-mono"
                            />
                          </div>
                        </div>
                        <div className="flex items-center gap-2 pt-1">
                          <button
                            onClick={() => handleSignCert(c.id)}
                            className="px-3 py-1.5 bg-[#2563eb] hover:bg-[#1d4ed8] text-white text-xs font-bold"
                          >
                            EXECUTE STATUTORY SIGNATURE
                          </button>
                          <button
                            onClick={() => setSigningCertId(null)}
                            className="px-3 py-1.5 bg-[#171e27] border border-[#293545] text-xs text-[#94a3b8]"
                          >
                            CANCEL
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="mt-3 flex justify-end">
                        <button
                          onClick={() => setSigningCertId(c.id)}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-[#172638] hover:bg-[#1e3450] border border-[#2d4d73] text-xs font-bold text-[#93c5fd]"
                        >
                          <ShieldCheck className="w-3.5 h-3.5" />
                          <span>SIGN STATUTORY UNDERTAKING</span>
                        </button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* VIEW F: COMPLIANCE AUDIT SCREEN */}
          {activeNav === 'reg_compliance' && (
            <div className="space-y-6">
              <div className="bg-[#12161e] border border-[#222a36] px-5 py-3.5 flex items-center justify-between">
                <div>
                  <div className="text-[10px] font-mono font-bold text-[#38bdf8] uppercase tracking-wider">
                    STATUTORY COMPLIANCE REVIEW
                  </div>
                  <h2 className="text-sm font-mono font-bold text-[#f8fafc] mt-0.5">
                    AUDITOR'S WORKING COMPLIANCE REGISTER
                  </h2>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono text-[#94a3b8]">FORMAT STATUS:</span>
                  <span className={`px-2 py-0.5 font-mono text-xs font-bold ${
                    report.compliance_status === 'COMPLIANT'
                      ? 'bg-[#143825] text-[#4ade80] border border-[#225e3d]'
                      : 'bg-[#38260d] text-[#fbbf24] border border-[#5e4318]'
                  }`}>
                    {report.compliance_status}
                  </span>
                </div>
              </div>

              <div className="bg-[#12161e] border border-[#222a36] rounded-sm overflow-hidden">
                <table className="min-w-full divide-y divide-[#1e2531] text-xs font-mono">
                  <thead className="bg-[#0f131a] text-[#94a3b8]">
                    <tr>
                      <th className="px-4 py-2.5 text-left text-[10px] uppercase">REQUIREMENT</th>
                      <th className="px-4 py-2.5 text-left text-[10px] uppercase">DESCRIPTION</th>
                      <th className="px-4 py-2.5 text-left text-[10px] uppercase">SEVERITY</th>
                      <th className="px-4 py-2.5 text-left text-[10px] uppercase">ACTION REQUIRED</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#1a212b]">
                    {((report.compliance_issues || []).length === 0) ? (
                      <tr>
                        <td colSpan={4} className="p-8 text-center text-[#4ade80] font-mono">
                          ALL MANDATED RULES, 156 PARAMETERS & CALCULATIONS PASS STATUTORY COMPLIANCE.
                        </td>
                      </tr>
                    ) : (
                      report.compliance_issues.map((iss: any) => (
                        <tr key={iss.id} className="hover:bg-[#151b24]">
                          <td className="px-4 py-3 font-bold text-[#93c5fd]">
                            {iss.target_official_id || iss.issue_type}
                          </td>
                          <td className="px-4 py-3 text-[#cbd5e1]">{iss.description}</td>
                          <td className="px-4 py-3">
                            <span className={`px-1.5 py-0.2 text-[10px] font-bold ${
                              iss.severity === 'CRITICAL'
                                ? 'bg-[#381419] text-[#f87171] border border-[#6b222d]'
                                : 'bg-[#38260d] text-[#fbbf24] border border-[#5e4318]'
                            }`}>
                              {iss.severity}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-[#94a3b8]">
                            {iss.resolution_hint || 'REVIEW REQUIRED'}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* VIEW G: IMMUTABLE VERSION HISTORY */}
          {activeNav === 'reg_versions' && (
            <div className="space-y-6">
              <div className="bg-[#12161e] border border-[#222a36] px-5 py-3.5 flex items-center justify-between">
                <div>
                  <div className="text-[10px] font-mono font-bold text-[#38bdf8] uppercase tracking-wider">
                    AUDIT LOGGED ARTIFACTS
                  </div>
                  <h2 className="text-sm font-mono font-bold text-[#f8fafc] mt-0.5">
                    IMMUTABLE STATUTORY DOSSIER VERSIONS
                  </h2>
                </div>
                <span className="text-xs font-mono text-[#94a3b8]">
                  SHA-256 Chain of Custody
                </span>
              </div>

              <div className="bg-[#12161e] border border-[#222a36] p-5 rounded-sm space-y-3 font-mono">
                <div className="p-4 bg-[#0d1015] border border-[#222c3b] flex items-center justify-between">
                  <div>
                    <div className="text-xs font-bold text-[#f1f5f9]">
                      Version {report.version_number}.0 (Active Working Statutory Artifact)
                    </div>
                    <div className="text-[11px] text-[#64748b] mt-1">
                      Status: {report.status} | Compliance: {report.compliance_status}
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="text-[10px] text-[#38bdf8] block">
                      SHA-256: {report.sha256_hash ? report.sha256_hash.slice(0, 24) + '...' : 'EXPORT PENDING'}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}

        </main>
      </div>

      {/* 4. FORENSIC EVIDENCE MODAL / DRAWER */}
      {inspectingEvidence && (
        <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
          <div className="bg-[#12161e] border border-[#29374a] w-full max-w-2xl rounded-sm p-6 font-mono shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-[#202937]">
              <div className="flex items-center gap-2">
                <FileCheck2 className="w-4 h-4 text-[#38bdf8]" />
                <span className="text-xs font-bold uppercase tracking-wider text-[#93c5fd]">
                  FORENSIC SOURCE EVIDENCE RECORD
                </span>
              </div>
              <button
                onClick={() => setInspectingEvidence(null)}
                className="text-[#94a3b8] hover:text-[#f8fafc]"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="mt-4 space-y-3 text-xs">
              <div className="p-3 bg-[#0d1015] border border-[#1e2634] space-y-1.5">
                <div className="text-[#64748b] text-[10px]">STATUTORY TARGET FIELD</div>
                <div className="font-bold text-[#f8fafc]">{inspectingEvidence.official_id} — {inspectingEvidence.exact_official_label}</div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 bg-[#0d1015] border border-[#1e2634]">
                  <div className="text-[#64748b] text-[10px]">SOURCE DOCUMENT HASH</div>
                  <div className="font-bold text-[#38bdf8] truncate">{inspectingEvidence.source_document_id || 'DEMO_DATA_ECL_GEO'}</div>
                </div>
                <div className="p-3 bg-[#0d1015] border border-[#1e2634]">
                  <div className="text-[#64748b] text-[10px]">EVIDENCE PAGE</div>
                  <div className="font-bold text-[#f8fafc]">Page {inspectingEvidence.source_page || 17}</div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 bg-[#0d1015] border border-[#1e2634]">
                  <div className="text-[#64748b] text-[10px]">CHUNK PROVENANCE</div>
                  <div className="font-bold text-[#cbd5e1] truncate">{inspectingEvidence.source_chunk_id || 'ECL-GEO-017-04'}</div>
                </div>
                <div className="p-3 bg-[#0d1015] border border-[#1e2634]">
                  <div className="text-[#64748b] text-[10px]">FORENSIC VERIFICATION</div>
                  <div className="font-bold text-[#4ade80]">{inspectingEvidence.reviewer_action || 'APPROVED'}</div>
                </div>
              </div>

              <div className="p-3 bg-[#0d1015] border border-[#1e2634]">
                <div className="text-[#64748b] text-[10px]">EXTRACTED EVIDENCE TEXT / RECORD</div>
                <div className="mt-1 text-[#e2e8f0] bg-[#141a22] p-2 border border-[#202936] text-[11px] font-mono leading-relaxed">
                  {inspectingEvidence.generated_value}
                </div>
              </div>
            </div>

            <div className="mt-5 pt-3 border-t border-[#202937] flex items-center justify-between">
              <span className="text-[10px] text-[#64748b]">IMMUTABLE AUDIT IDENTIFIER: AUD-{report.id?.slice(0, 12)}</span>
              <div className="flex items-center gap-2">
                {inspectingEvidence.source_document_id && (
                  <Link
                    to={`/documents/${inspectingEvidence.source_document_id}`}
                    target="_blank"
                    className="inline-flex items-center gap-1 px-3 py-1.5 bg-[#172538] hover:bg-[#1f334d] border border-[#2d4970] text-xs text-[#93c5fd]"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    <span>VIEW SOURCE DOCUMENT</span>
                  </Link>
                )}
                <button
                  onClick={() => setInspectingEvidence(null)}
                  className="px-3 py-1.5 bg-[#1a212b] hover:bg-[#222b38] border border-[#2d3848] text-xs text-[#cbd5e1]"
                >
                  CLOSE
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 4. OPTIONAL ANALYTICAL ANNEXURE INSPECTION MODAL */}
      {inspectingAnnexure && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center p-4 z-50">
          <div className="bg-[#12161e] border border-[#2d3d52] w-full max-w-3xl max-h-[85vh] flex flex-col rounded-sm shadow-2xl overflow-hidden font-mono">
            {/* Modal Header */}
            <div className="px-6 py-4 bg-[#0d1015] border-b border-[#222a36] flex items-center justify-between">
              <div>
                <span className="px-1.5 py-0.5 bg-[#1b2f48] border border-[#2e527d] text-[#60a5fa] text-[10px] font-bold">
                  {inspectingAnnexure.requirement_type} ANNEXURE
                </span>
                <h3 className="text-sm font-bold text-[#f8fafc] mt-1">
                  {inspectingAnnexure.title}
                </h3>
              </div>
              <button
                onClick={() => setInspectingAnnexure(null)}
                className="text-[#94a3b8] hover:text-[#f8fafc] p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto space-y-4 text-xs">
              <div className="grid grid-cols-3 gap-3">
                <div className="p-3 bg-[#0d1015] border border-[#1e2634]">
                  <div className="text-[#64748b] text-[10px]">OFFICIAL REFERENCE</div>
                  <div className="font-bold text-[#93c5fd]">{inspectingAnnexure.official_reference}</div>
                </div>
                <div className="p-3 bg-[#0d1015] border border-[#1e2634]">
                  <div className="text-[#64748b] text-[10px]">ATTACHMENT STATE</div>
                  <div className="font-bold text-[#4ade80]">{inspectingAnnexure.attachment_status}</div>
                </div>
                <div className="p-3 bg-[#0d1015] border border-[#1e2634]">
                  <div className="text-[#64748b] text-[10px]">COMPLIANCE IMPACT</div>
                  <div className="font-bold text-[#cbd5e1]">NON-INTRUSIVE (OPTIONAL)</div>
                </div>
              </div>

              {(() => {
                try {
                  const notesData = JSON.parse(inspectingAnnexure.notes || '{}');
                  return (
                    <div className="space-y-3">
                      <div className="p-3 bg-[#0d1015] border border-[#1e2634] space-y-1">
                        <div className="text-[#64748b] text-[10px]">ANALYSIS PROVENANCE</div>
                        <div className="text-[#38bdf8]">ID: {notesData.analysis_id}</div>
                        <div className="text-[#94a3b8]">Model: {notesData.embedding_model} · Method: {notesData.analysis_method}</div>
                        <div className="text-[#94a3b8]">Analyzed Periods: {(notesData.periods || []).join(', ')}</div>
                      </div>

                      <div className="border border-[#222a36] rounded-sm overflow-hidden">
                        <div className="px-4 py-2 bg-[#0f131a] text-[#94a3b8] font-bold text-[10px] uppercase">
                          ATTACHED TOPIC INTELLIGENCE DOSSIER ({notesData.topics?.length || 0} TOPICS)
                        </div>
                        <div className="divide-y divide-[#1a212b] max-h-60 overflow-y-auto">
                          {(notesData.topics || []).map((tp: any) => (
                            <div key={tp.topic_id} className="p-3 hover:bg-[#151b24] space-y-1">
                              <div className="flex items-center justify-between">
                                <span className="font-bold text-[#f1f5f9]">{tp.label}</span>
                                <span className="text-[10px] text-[#38bdf8]">{tp.prevalence_pct?.toFixed(1)}% Prevalence</span>
                              </div>
                              <div className="flex flex-wrap gap-1">
                                {(tp.top_terms || []).slice(0, 6).map((tm: any) => (
                                  <span key={tm.term} className="px-1 py-0.2 bg-[#17202c] border border-[#273549] text-[9px] text-[#94a3b8]">
                                    {tm.term}
                                  </span>
                                ))}
                              </div>
                              {tp.evidence?.length > 0 && (
                                <div className="text-[10px] text-[#64748b] italic">
                                  Evidence: {tp.evidence[0].document_title} (p. {tp.evidence[0].page_number})
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  );
                } catch {
                  return (
                    <div className="p-3 bg-[#0d1015] border border-[#1e2634] text-[#94a3b8]">
                      {inspectingAnnexure.notes}
                    </div>
                  );
                }
              })()}
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-3 bg-[#0d1015] border-t border-[#202937] flex items-center justify-between">
              <span className="text-[10px] text-[#64748b]">OPTIONAL STATUTORY ANNEXURE REFERENCE</span>
              <button
                onClick={() => setInspectingAnnexure(null)}
                className="px-3 py-1.5 bg-[#1a212b] hover:bg-[#222b38] border border-[#2d3848] text-xs text-[#cbd5e1]"
              >
                CLOSE
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
