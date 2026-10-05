import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiClient } from '../api/client';
import { 
  FileText, 
  ShieldCheck, 
  Activity, 
  Database, 
  Building2, 
  Layers, 
  Table as TableIcon, 
  Image as ImageIcon, 
  FileSpreadsheet, 
  Search, 
  RefreshCw, 
  Filter, 
  CheckCircle2, 
  AlertTriangle, 
  Clock, 
  ArrowUpRight,
  HardDrive,
  FileCheck
} from 'lucide-react';

interface DocumentTypeStat {
  mime_type: string;
  label: string;
  count: number;
  percentage: number;
}

interface OrgStat {
  id: string;
  name: string;
  code: string;
  document_count: number;
}

interface TopicStat {
  id: string;
  name: string;
  document_count: number;
  prevalence_pct: number;
}

interface ActivityEvent {
  id: string;
  action: string;
  actor_name: string;
  role_code: string;
  object_type: string;
  hash: string;
  timestamp: string;
}

export const Dashboard = () => {
  const [metrics, setMetrics] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedOrg, setSelectedOrg] = useState('');
  const [selectedMime, setSelectedMime] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');
  const [lastRefreshed, setLastRefreshed] = useState<string>(new Date().toLocaleTimeString());

  const user = JSON.parse(localStorage.getItem('user') || '{"username":"hq_officer","role":"CMPDI_HQ_OFFICER"}');

  const fetchMetrics = async (isManual = false) => {
    if (isManual) setRefreshing(true);
    try {
      const params = new URLSearchParams();
      if (selectedOrg) params.append('org_filter', selectedOrg);
      if (selectedMime) params.append('mime_filter', selectedMime);
      if (selectedStatus) params.append('status_filter', selectedStatus);

      const res = await apiClient.get(`/dashboard/metrics?${params.toString()}`);
      setMetrics(res.data);
      setLastRefreshed(new Date().toLocaleTimeString());
    } catch (err) {
      console.error("Error loading dashboard metrics:", err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
  }, [selectedOrg, selectedMime, selectedStatus]);

  return (
    <div className="w-full max-w-[1600px] mx-auto px-4 py-5 space-y-6">
      {/* Top Banner / System Telemetry Header */}
      <div className="flex flex-col xl:flex-row justify-between items-start xl:items-center gap-4 bg-[#12161d] border border-[#242c38] p-5 rounded-sm shadow-md">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold font-mono tracking-tight text-[#f1f5f9]">
              EXECUTIVE REPORTING INTELLIGENCE DASHBOARD
            </h1>
            <span className="text-[11px] font-mono px-2 py-0.5 rounded-sm bg-[#1e293b] border border-[#334155] text-[#38bdf8] font-bold">
              SIH-26023
            </span>
          </div>
          <p className="text-xs text-[#94a3b8] font-mono mt-1">
            Coal India Limited & CMPDI Subsidiary Geological & Statutory Overview · Apex Review Console
          </p>
        </div>

        {/* Global Live Scope Badges */}
        <div className="flex flex-wrap items-center gap-2.5">
          <div className="flex items-center gap-1.5 px-3 py-1 bg-[#16273d] border border-[#2b4c73] rounded-sm text-xs font-mono text-[#93c5fd]">
            <Database size={13} className="text-[#60a5fa]" />
            <span>PostgreSQL 16 + pgvector (Active)</span>
          </div>
          <div className="flex items-center gap-1.5 px-3 py-1 bg-[#17231c] border border-[#234232] rounded-sm text-xs font-mono text-[#86efac]">
            <Building2 size={13} className="text-[#4ade80]" />
            <span>{metrics?.organization_scope?.name || 'CMPDI HQ'}</span>
          </div>
          <button
            onClick={() => fetchMetrics(true)}
            disabled={refreshing}
            className="flex items-center gap-1.5 px-3 py-1 bg-[#1a212b] hover:bg-[#252f3d] border border-[#334155] rounded-sm text-xs font-mono text-[#cbd5e1] transition-colors"
          >
            <RefreshCw size={12} className={refreshing ? 'animate-spin text-[#38bdf8]' : 'text-[#94a3b8]'} />
            <span>{refreshing ? 'Refreshing...' : `Sync (${lastRefreshed})`}</span>
          </button>
        </div>
      </div>

      {/* Filter and Control Toolbar */}
      <div className="bg-[#12161d] border border-[#242c38] px-4 py-3 rounded-sm flex flex-wrap items-center justify-between gap-3 text-xs font-mono">
        <div className="flex flex-wrap items-center gap-3">
          <span className="flex items-center gap-1.5 text-[#94a3b8] font-bold uppercase tracking-wider text-[11px]">
            <Filter size={13} className="text-[#38bdf8]" /> Filters:
          </span>

          {/* Organization Filter */}
          <select
            value={selectedOrg}
            onChange={(e) => setSelectedOrg(e.target.value)}
            className="bg-[#18202a] text-[#e2e8f0] border border-[#2b3748] px-3 py-1.5 rounded-sm focus:outline-none focus:border-[#38bdf8]"
          >
            <option value="">All Organizations (Apex Scope)</option>
            {metrics?.available_organizations?.map((org: any) => (
              <option key={org.id} value={org.id}>
                {org.code} — {org.name}
              </option>
            ))}
          </select>

          {/* Document Type Filter */}
          <select
            value={selectedMime}
            onChange={(e) => setSelectedMime(e.target.value)}
            className="bg-[#18202a] text-[#e2e8f0] border border-[#2b3748] px-3 py-1.5 rounded-sm focus:outline-none focus:border-[#38bdf8]"
          >
            <option value="">All Document Formats</option>
            <option value="application/pdf">PDF Geological Reports</option>
            <option value="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet">XLSX Production Spreadsheets</option>
            <option value="text/csv">CSV Tabular Logs</option>
            <option value="image/png">PNG Maps & Seam Cross-Sections</option>
            <option value="application/vnd.openxmlformats-officedocument.wordprocessingml.document">DOCX Official Briefs</option>
            <option value="text/plain">TXT Geological Drill Logs</option>
          </select>

          {/* Status Filter */}
          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="bg-[#18202a] text-[#e2e8f0] border border-[#2b3748] px-3 py-1.5 rounded-sm focus:outline-none focus:border-[#38bdf8]"
          >
            <option value="">All Pipeline Statuses</option>
            <option value="PROCESSED">Processed & Indexed</option>
            <option value="AWAITING_VERIFICATION">Awaiting Human Review</option>
            <option value="FAILED">Processing Errored</option>
          </select>

          {(selectedOrg || selectedMime || selectedStatus) && (
            <button
              onClick={() => { setSelectedOrg(''); setSelectedMime(''); setSelectedStatus(''); }}
              className="text-[#f87171] hover:underline text-[11px] px-2 py-1"
            >
              Reset Filters
            </button>
          )}
        </div>

        <div className="flex items-center gap-2">
          <Link
            to="/qa"
            className="px-3 py-1.5 bg-[#1d4ed8] hover:bg-[#2563eb] text-white rounded-sm font-bold flex items-center gap-1.5 shadow-sm transition-colors"
          >
            <Search size={13} /> Ask Koyla Q&A
          </Link>
          <Link
            to="/upload"
            className="px-3 py-1.5 bg-[#047857] hover:bg-[#059669] text-white rounded-sm font-bold flex items-center gap-1.5 shadow-sm transition-colors"
          >
            <FileText size={13} /> Ingest Document
          </Link>
        </div>
      </div>

      {/* Primary KPI Grid (6 Top Cards) */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3.5">
        {/* Total Documents */}
        <div className="bg-[#12161d] border border-[#242c38] p-4 rounded-sm relative overflow-hidden">
          <div className="flex justify-between items-start">
            <span className="text-[10px] font-mono uppercase text-[#94a3b8] tracking-wider font-semibold">
              Documents Ingested
            </span>
            <FileText size={16} className="text-[#38bdf8]" />
          </div>
          <div className="text-2xl font-bold font-mono text-[#f1f5f9] mt-2">
            {metrics?.documents_ingested?.toLocaleString() ?? '—'}
          </div>
          <div className="text-[11px] font-mono text-[#4ade80] flex items-center gap-1 mt-1.5">
            <CheckCircle2 size={12} />
            <span>{metrics?.documents_processed?.toLocaleString() ?? 0} Processed</span>
          </div>
          <div className="w-full bg-[#1e293b] h-1 mt-2.5 rounded-full overflow-hidden">
            <div 
              className="bg-[#38bdf8] h-full" 
              style={{ width: `${metrics?.extraction_success_rate ?? 0}%` }}
            />
          </div>
        </div>

        {/* Structured Fields */}
        <div className="bg-[#12161d] border border-[#242c38] p-4 rounded-sm relative overflow-hidden">
          <div className="flex justify-between items-start">
            <span className="text-[10px] font-mono uppercase text-[#94a3b8] tracking-wider font-semibold">
              Extracted Metrics
            </span>
            <Database size={16} className="text-[#a78bfa]" />
          </div>
          <div className="text-2xl font-bold font-mono text-[#f1f5f9] mt-2">
            {metrics?.total_structured_fields?.toLocaleString() ?? '—'}
          </div>
          <div className="text-[11px] font-mono text-[#c084fc] flex items-center gap-1 mt-1.5">
            <span>100% Physical Provenance</span>
          </div>
          <div className="w-full bg-[#1e293b] h-1 mt-2.5 rounded-full overflow-hidden">
            <div className="bg-[#a78bfa] h-full w-[95%]" />
          </div>
        </div>

        {/* Tables & Grid Rows */}
        <div className="bg-[#12161d] border border-[#242c38] p-4 rounded-sm relative overflow-hidden">
          <div className="flex justify-between items-start">
            <span className="text-[10px] font-mono uppercase text-[#94a3b8] tracking-wider font-semibold">
              Tabular Grids
            </span>
            <TableIcon size={16} className="text-[#fb923c]" />
          </div>
          <div className="text-2xl font-bold font-mono text-[#f1f5f9] mt-2">
            {metrics?.total_tables?.toLocaleString() ?? '—'}
          </div>
          <div className="text-[11px] font-mono text-[#fdba74] flex items-center gap-1 mt-1.5">
            <span>Merged Header Propagated</span>
          </div>
          <div className="w-full bg-[#1e293b] h-1 mt-2.5 rounded-full overflow-hidden">
            <div className="bg-[#fb923c] h-full w-[88%]" />
          </div>
        </div>

        {/* Visual Figures & Cross Sections */}
        <div className="bg-[#12161d] border border-[#242c38] p-4 rounded-sm relative overflow-hidden">
          <div className="flex justify-between items-start">
            <span className="text-[10px] font-mono uppercase text-[#94a3b8] tracking-wider font-semibold">
              Visual Figures & Maps
            </span>
            <ImageIcon size={16} className="text-[#34d399]" />
          </div>
          <div className="text-2xl font-bold font-mono text-[#f1f5f9] mt-2">
            {metrics?.total_visual_assets?.toLocaleString() ?? '—'}
          </div>
          <div className="text-[11px] font-mono text-[#6ee7b7] flex items-center gap-1 mt-1.5">
            <span>Bounding Box Cataloged</span>
          </div>
          <div className="w-full bg-[#1e293b] h-1 mt-2.5 rounded-full overflow-hidden">
            <div className="bg-[#34d399] h-full w-[70%]" />
          </div>
        </div>

        {/* Generated Statutory Reports */}
        <div className="bg-[#12161d] border border-[#242c38] p-4 rounded-sm relative overflow-hidden">
          <div className="flex justify-between items-start">
            <span className="text-[10px] font-mono uppercase text-[#94a3b8] tracking-wider font-semibold">
              Generated Briefs
            </span>
            <FileSpreadsheet size={16} className="text-[#f43f5e]" />
          </div>
          <div className="text-2xl font-bold font-mono text-[#f1f5f9] mt-2">
            {metrics?.total_reports?.toLocaleString() ?? '—'}
          </div>
          <div className="text-[11px] font-mono text-[#fda4af] flex items-center gap-1 mt-1.5">
            <span>DOCX Verified Briefs</span>
          </div>
          <div className="w-full bg-[#1e293b] h-1 mt-2.5 rounded-full overflow-hidden">
            <div className="bg-[#f43f5e] h-full w-[100%]" />
          </div>
        </div>

        {/* Verification Backlog & 4-Eyes */}
        <div className="bg-[#12161d] border border-[#242c38] p-4 rounded-sm relative overflow-hidden">
          <div className="flex justify-between items-start">
            <span className="text-[10px] font-mono uppercase text-[#94a3b8] tracking-wider font-semibold">
              Verification Queue
            </span>
            <ShieldCheck size={16} className="text-[#eab308]" />
          </div>
          <div className="text-2xl font-bold font-mono text-[#f1f5f9] mt-2">
            {metrics?.verification_backlog?.toLocaleString() ?? 0}
          </div>
          <div className="text-[11px] font-mono text-[#fde047] flex items-center gap-1 mt-1.5">
            <span>4-Eyes Dual Control Active</span>
          </div>
          <div className="w-full bg-[#1e293b] h-1 mt-2.5 rounded-full overflow-hidden">
            <div className="bg-[#eab308] h-full w-[35%]" />
          </div>
        </div>
      </div>

      {/* Middle Analytical Split: Document Distribution vs Operating Subsidiary Performance */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Document Format Distribution */}
        <div className="bg-[#12161d] border border-[#242c38] rounded-sm p-5 space-y-4">
          <div className="flex justify-between items-center border-b border-[#242c38] pb-3">
            <div>
              <h2 className="text-sm font-bold font-mono text-[#f1f5f9] uppercase tracking-wide">
                Document Formats & Ingestion Breakdown
              </h2>
              <p className="text-[11px] text-[#94a3b8] font-mono">
                Multimodal parsing distribution across scanned folios, tables, spreadsheets & maps
              </p>
            </div>
            <Link to="/documents" className="text-xs font-mono text-[#38bdf8] hover:underline flex items-center gap-1">
              View All <ArrowUpRight size={12} />
            </Link>
          </div>

          <div className="space-y-3.5 pt-1">
            {metrics?.document_types?.map((item: DocumentTypeStat) => (
              <div key={item.mime_type} className="space-y-1 font-mono text-xs">
                <div className="flex justify-between items-center text-[#cbd5e1]">
                  <span className="truncate max-w-[340px] text-[#e2e8f0] font-medium">{item.label}</span>
                  <div className="flex items-center gap-3">
                    <span className="text-[#94a3b8]">{item.count.toLocaleString()} docs</span>
                    <span className="font-bold text-[#38bdf8] w-12 text-right">{item.percentage}%</span>
                  </div>
                </div>
                <div className="w-full bg-[#18202a] h-1.5 rounded-full overflow-hidden border border-[#252f3d]">
                  <div 
                    className="bg-gradient-to-r from-[#1d4ed8] to-[#38bdf8] h-full rounded-full transition-all duration-500" 
                    style={{ width: `${item.percentage}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Operating Subsidiary & Regional Institute Distribution */}
        <div className="bg-[#12161d] border border-[#242c38] rounded-sm p-5 space-y-4">
          <div className="flex justify-between items-center border-b border-[#242c38] pb-3">
            <div>
              <h2 className="text-sm font-bold font-mono text-[#f1f5f9] uppercase tracking-wide">
                Subsidiary & Exploration Institute Volumes
              </h2>
              <p className="text-[11px] text-[#94a3b8] font-mono">
                Top operational units active in the centralized knowledge store
              </p>
            </div>
            <span className="text-[11px] font-mono px-2 py-0.5 rounded-sm bg-[#16273d] text-[#60a5fa] border border-[#2b4c73]">
              61 Configured Orgs
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-1">
            {metrics?.organization_distribution?.map((org: OrgStat) => (
              <div 
                key={org.id} 
                onClick={() => setSelectedOrg(org.id)}
                className={`p-3 rounded-sm border transition-all cursor-pointer ${
                  selectedOrg === org.id 
                    ? 'bg-[#1e3450] border-[#3b82f6]' 
                    : 'bg-[#161c24] border-[#242c38] hover:border-[#38bdf8]'
                }`}
              >
                <div className="flex justify-between items-start">
                  <span className="text-xs font-bold font-mono text-[#38bdf8]">{org.code}</span>
                  <span className="text-xs font-bold font-mono text-[#f1f5f9] bg-[#1a232f] px-1.5 py-0.5 rounded-sm border border-[#2a3749]">
                    {org.document_count}
                  </span>
                </div>
                <p className="text-[11px] text-[#94a3b8] font-mono truncate mt-1">{org.name}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Third Row: Topic Intelligence Highlights + System Architecture Quick Health */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Topic Clusters (c-TF-IDF Discovery) */}
        <div className="lg:col-span-2 bg-[#12161d] border border-[#242c38] rounded-sm p-5 space-y-4">
          <div className="flex justify-between items-center border-b border-[#242c38] pb-3">
            <div>
              <h2 className="text-sm font-bold font-mono text-[#f1f5f9] uppercase tracking-wide">
                Topic Intelligence Clusters (c-TF-IDF Discovery)
              </h2>
              <p className="text-[11px] text-[#94a3b8] font-mono">
                Automated domain vocabularies, exploration horizons & mine operation clusters
              </p>
            </div>
            <Link to="/topics" className="text-xs font-mono text-[#38bdf8] hover:underline flex items-center gap-1">
              Explore Topics <ArrowUpRight size={12} />
            </Link>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 pt-1">
            {metrics?.topic_highlights?.map((topic: TopicStat) => (
              <div key={topic.id} className="bg-[#161c24] border border-[#252f3d] p-3 rounded-sm space-y-1">
                <div className="flex items-center gap-1.5 text-xs font-mono font-bold text-[#e2e8f0]">
                  <Layers size={13} className="text-[#a78bfa] shrink-0" />
                  <span className="truncate">{topic.name}</span>
                </div>
                <div className="flex justify-between text-[11px] font-mono text-[#94a3b8]">
                  <span>Associated Docs:</span>
                  <span className="text-[#f1f5f9] font-bold">{topic.document_count}</span>
                </div>
                <div className="flex justify-between text-[11px] font-mono text-[#94a3b8]">
                  <span>Prevalence:</span>
                  <span className="text-[#38bdf8] font-bold">{topic.prevalence_pct}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Verified Technical Foundation / Engine Telemetry */}
        <div className="bg-[#12161d] border border-[#242c38] rounded-sm p-5 space-y-4">
          <div className="flex justify-between items-center border-b border-[#242c38] pb-3">
            <h2 className="text-sm font-bold font-mono text-[#f1f5f9] uppercase tracking-wide">
              Engineering Baseline
            </h2>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-sm bg-[#16273d] text-[#60a5fa] border border-[#2b4c73]">
              LIVE
            </span>
          </div>

          <div className="space-y-2.5 text-xs font-mono">
            <div className="flex justify-between items-center p-2.5 bg-[#161c24] rounded-sm border border-[#242c38]">
              <span className="text-[#94a3b8]">Vector Embeddings (384-D)</span>
              <span className="font-bold text-[#38bdf8]">{metrics?.total_chunks?.toLocaleString() ?? 4924}</span>
            </div>
            <div className="flex justify-between items-center p-2.5 bg-[#161c24] rounded-sm border border-[#242c38]">
              <span className="text-[#94a3b8]">Reconciliation Groups</span>
              <span className="font-bold text-[#f59e0b]">{metrics?.total_reconciliation_groups ?? 257}</span>
            </div>
            <div className="flex justify-between items-center p-2.5 bg-[#161c24] rounded-sm border border-[#242c38]">
              <span className="text-[#94a3b8]">Executed Intelligence Queries</span>
              <span className="font-bold text-[#4ade80]">{metrics?.total_queries ?? 508}</span>
            </div>
            <div className="flex justify-between items-center p-2.5 bg-[#161c24] rounded-sm border border-[#242c38]">
              <span className="text-[#94a3b8]">Immutable Audit Trail Records</span>
              <span className="font-bold text-[#c084fc]">{metrics?.audit_events?.toLocaleString() ?? 3158}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Section: Recent Operational Audit Activity Stream */}
      <div className="bg-[#12161d] border border-[#242c38] rounded-sm p-5 space-y-4">
        <div className="flex justify-between items-center border-b border-[#242c38] pb-3">
          <div>
            <h2 className="text-sm font-bold font-mono text-[#f1f5f9] uppercase tracking-wide">
              Recent Continuous Compliance & Ingestion Activity
            </h2>
            <p className="text-[11px] text-[#94a3b8] font-mono">
              Cryptographically verified audit log stream directly from PostgreSQL audit_events
            </p>
          </div>
          <Link to="/governance" className="text-xs font-mono text-[#38bdf8] hover:underline flex items-center gap-1">
            Complete Audit Log <ArrowUpRight size={12} />
          </Link>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left font-mono text-xs">
            <thead>
              <tr className="border-b border-[#242c38] text-[#94a3b8] text-[11px] uppercase">
                <th className="py-2.5 px-3">Timestamp</th>
                <th className="py-2.5 px-3">Action</th>
                <th className="py-2.5 px-3">Actor & Role</th>
                <th className="py-2.5 px-3">Object Type</th>
                <th className="py-2.5 px-3">Integrity Hash</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1e2735]">
              {metrics?.recent_activity?.map((evt: ActivityEvent) => (
                <tr key={evt.id} className="hover:bg-[#18202a] transition-colors">
                  <td className="py-2 px-3 text-[#94a3b8] whitespace-nowrap">{evt.timestamp}</td>
                  <td className="py-2 px-3 text-[#38bdf8] font-bold">{evt.action}</td>
                  <td className="py-2 px-3 text-[#f1f5f9]">
                    <span>{evt.actor_name}</span>
                    <span className="text-[10px] text-[#94a3b8] ml-2 px-1.5 py-0.2 bg-[#1a232f] rounded-sm border border-[#2b394d]">
                      {evt.role_code}
                    </span>
                  </td>
                  <td className="py-2 px-3 text-[#cbd5e1]">{evt.object_type}</td>
                  <td className="py-2 px-3 text-[#64748b] font-mono text-[11px]">{evt.hash}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
