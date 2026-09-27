import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { apiClient } from '../api/client';
import {
  Database,
  FileText,
  Table as TableIcon,
  Image as ImageIcon,
  ShieldAlert,
  ShieldCheck,
  Search,
  Filter,
  CheckCircle2,
  XCircle,
  ExternalLink,
  Layers,
  ArrowRight,
  GitBranch,
  RefreshCw,
  PlusCircle,
  Info
} from 'lucide-react';

interface EvidenceSummary {
  total_documents: number;
  text_evidence_count: number;
  table_evidence_count: number;
  structured_values_count: number;
  visual_assets_count: number;
  needs_review_count: number;
  relationships_count: number;
}

interface EvidenceItem {
  id: string;
  evidence_type: 'TEXT' | 'TABLE' | 'STRUCTURED_VALUE' | 'VISUAL';
  document_id: string;
  document_title: string;
  organization_id: string;
  page_number?: number;
  provenance_display: string;
  content_preview: string;
  field_name?: string;
  value?: string;
  unit?: string;
  numeric_value?: number;
  confidence_score: number;
  verification_status: string;
  metadata: Record<string, any>;
}

interface DocumentRelationship {
  id: string;
  source_document_id: string;
  source_title: string;
  target_document_id: string;
  target_title: string;
  relationship_type: string;
  confidence: number;
  matching_criteria?: Record<string, any>;
  description?: string;
  created_at: string;
}

export const EvidenceControlRoom: React.FC = () => {
  const navigate = useNavigate();

  const [summary, setSummary] = useState<EvidenceSummary | null>(null);
  const [items, setItems] = useState<EvidenceItem[]>([]);
  const [relationships, setRelationships] = useState<DocumentRelationship[]>([]);
  const [totalCount, setTotalCount] = useState(0);

  const [activeTab, setActiveTab] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  // Inspector modal state
  const [inspectItem, setInspectItem] = useState<EvidenceItem | null>(null);
  const [reviewAction, setReviewAction] = useState<'APPROVE' | 'CORRECT' | 'REJECT' | null>(null);
  const [correctedValue, setCorrectedValue] = useState('');
  const [reviewNotes, setReviewNotes] = useState('');
  const [submittingReview, setSubmittingReview] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      // 1. Fetch Summary Metrics
      const sumRes = await apiClient.get('/evidence/summary');
      setSummary(sumRes.data);

      // 2. Fetch Evidence Items
      const itemsRes = await apiClient.get('/evidence/items', {
        params: {
          evidence_type: activeTab,
          search: searchQuery || undefined,
          limit: 50
        }
      });
      setItems(itemsRes.data.items);
      setTotalCount(itemsRes.data.total);

      // 3. Fetch Discovered Relationships
      const relsRes = await apiClient.get('/evidence/relationships');
      setRelationships(relsRes.data);
    } catch (err) {
      console.error('Failed to load universal evidence data', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [activeTab, searchQuery]);

  const handleReviewSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inspectItem || !reviewAction) return;

    setSubmittingReview(true);
    try {
      await apiClient.post(`/evidence/${inspectItem.id}/review`, {
        action: reviewAction,
        corrected_value: reviewAction === 'CORRECT' ? correctedValue : undefined,
        notes: reviewNotes || undefined
      });

      setSuccessMessage(`Successfully updated status to ${reviewAction}`);
      setTimeout(() => setSuccessMessage(null), 3000);
      setInspectItem(null);
      setReviewAction(null);
      setCorrectedValue('');
      setReviewNotes('');
      loadData();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to submit evidence review');
    } finally {
      setSubmittingReview(false);
    }
  };

  const getModalityBadge = (type: string) => {
    switch (type) {
      case 'STRUCTURED_VALUE':
        return (
          <span className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-950 text-emerald-300 border border-emerald-800">
            <Database className="w-2.5 h-2.5 text-emerald-400" /> VALUE
          </span>
        );
      case 'VISUAL':
        return (
          <span className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-blue-950 text-blue-300 border border-blue-800">
            <ImageIcon className="w-2.5 h-2.5 text-blue-400" /> VISUAL
          </span>
        );
      case 'TABLE':
        return (
          <span className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-purple-950 text-purple-300 border border-purple-800">
            <TableIcon className="w-2.5 h-2.5 text-purple-400" /> TABLE
          </span>
        );
      default:
        return (
          <span className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-800 text-slate-300 border border-slate-700">
            <FileText className="w-2.5 h-2.5" /> TEXT
          </span>
        );
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'VERIFIED':
      case 'CORRECTED':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-900/60 text-emerald-300 border border-emerald-700 flex items-center gap-1">
            <CheckCircle2 className="w-2.5 h-2.5" /> VERIFIED
          </span>
        );
      case 'REVIEW_REQUIRED':
      case 'WARNING':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-950 text-amber-300 border border-amber-800 flex items-center gap-1">
            <ShieldAlert className="w-2.5 h-2.5" /> REVIEW REQUIRED
          </span>
        );
      case 'REJECTED':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-rose-950 text-rose-300 border border-rose-800 flex items-center gap-1">
            <XCircle className="w-2.5 h-2.5" /> REJECTED
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-800 text-slate-400 border border-slate-700">
            PENDING
          </span>
        );
    }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 pb-4 border-b border-[#242c38]">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold font-mono tracking-wider text-slate-100 uppercase">
              Universal Evidence Engine
            </h1>
            <span className="text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 bg-blue-950 text-blue-300 border border-blue-800 rounded">
              Phase 10 Ingestion & Verification
            </span>
          </div>
          <p className="text-xs font-mono text-slate-400 mt-1">
            Unified cross-modal evidence layer combining spreadsheets, geological diagrams, structured tables, and reports.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              setRefreshing(true);
              loadData();
            }}
            disabled={refreshing}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-[#161c24] hover:bg-[#1f2733] border border-[#2b3544] rounded text-xs font-mono text-slate-300 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </button>

          <Link
            to="/upload"
            className="flex items-center gap-1.5 px-3.5 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded text-xs font-mono font-bold shadow-sm transition-colors"
          >
            <PlusCircle className="w-3.5 h-3.5" />
            Add Evidence
          </Link>
        </div>
      </div>

      {/* Success Banner */}
      {successMessage && (
        <div className="p-3 bg-emerald-950/80 border border-emerald-800 text-emerald-200 text-xs font-mono rounded flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>{successMessage}</span>
        </div>
      )}

      {/* KPI Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
        <div className="bg-[#12161d] border border-[#242c38] rounded p-3 space-y-1">
          <span className="text-[10px] font-mono text-slate-400 uppercase tracking-tight">Documents</span>
          <p className="text-xl font-mono font-bold text-slate-100">{summary?.total_documents ?? 0}</p>
          <span className="text-[9px] font-mono text-slate-500">All Formats</span>
        </div>

        <div className="bg-[#12161d] border border-[#242c38] rounded p-3 space-y-1">
          <span className="text-[10px] font-mono text-slate-400 uppercase tracking-tight">Values</span>
          <p className="text-xl font-mono font-bold text-emerald-400">{summary?.structured_values_count ?? 0}</p>
          <span className="text-[9px] font-mono text-slate-500">Spreadsheets & Cells</span>
        </div>

        <div className="bg-[#12161d] border border-[#242c38] rounded p-3 space-y-1">
          <span className="text-[10px] font-mono text-slate-400 uppercase tracking-tight">Visuals</span>
          <p className="text-xl font-mono font-bold text-blue-400">{summary?.visual_assets_count ?? 0}</p>
          <span className="text-[9px] font-mono text-slate-500">Maps & Sections</span>
        </div>

        <div className="bg-[#12161d] border border-[#242c38] rounded p-3 space-y-1">
          <span className="text-[10px] font-mono text-slate-400 uppercase tracking-tight">Tables</span>
          <p className="text-xl font-mono font-bold text-purple-400">{summary?.table_evidence_count ?? 0}</p>
          <span className="text-[9px] font-mono text-slate-500">Preserved Structured</span>
        </div>

        <div className="bg-[#12161d] border border-[#242c38] rounded p-3 space-y-1">
          <span className="text-[10px] font-mono text-slate-400 uppercase tracking-tight">Text Pages</span>
          <p className="text-xl font-mono font-bold text-slate-300">{summary?.text_evidence_count ?? 0}</p>
          <span className="text-[9px] font-mono text-slate-500">Indexed for Retrieval</span>
        </div>

        <div className="bg-[#12161d] border border-[#242c38] rounded p-3 space-y-1">
          <span className="text-[10px] font-mono text-slate-400 uppercase tracking-tight">Links</span>
          <p className="text-xl font-mono font-bold text-cyan-400">{summary?.relationships_count ?? 0}</p>
          <span className="text-[9px] font-mono text-slate-500">Cross-Doc Matches</span>
        </div>

        <div className="bg-[#12161d] border border-amber-900/60 rounded p-3 space-y-1 bg-amber-950/20">
          <span className="text-[10px] font-mono text-amber-300 uppercase tracking-tight">Needs Review</span>
          <p className="text-xl font-mono font-bold text-amber-400">{summary?.needs_review_count ?? 0}</p>
          <span className="text-[9px] font-mono text-amber-500/80">Pending Verification</span>
        </div>
      </div>

      {/* Main Workspace Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Left 3 Cols: Evidence Register Table */}
        <div className="lg:col-span-3 space-y-4">
          {/* Controls Bar: Tabs & Search */}
          <div className="bg-[#12161d] border border-[#242c38] rounded p-3 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            {/* Filter Tabs */}
            <div className="flex items-center gap-1 overflow-x-auto pb-1 sm:pb-0">
              {[
                { id: 'ALL', label: 'All Evidence' },
                { id: 'STRUCTURED_VALUE', label: 'Values' },
                { id: 'VISUAL', label: 'Visuals' },
                { id: 'TABLE', label: 'Tables' },
                { id: 'NEEDS_REVIEW', label: 'Needs Review' }
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`px-3 py-1 text-xs font-mono rounded transition-colors whitespace-nowrap ${
                    activeTab === tab.id
                      ? 'bg-blue-600 text-white font-bold'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-[#1a212b]'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Search Input */}
            <div className="relative w-full sm:w-64">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-500" />
              <input
                type="text"
                placeholder="Search metrics, captions..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-8 pr-3 py-1.5 bg-[#0d1015] border border-[#2b3544] rounded text-xs font-mono text-slate-200 focus:outline-none focus:border-blue-500"
              />
            </div>
          </div>

          {/* Evidence Items Register Table */}
          <div className="bg-[#12161d] border border-[#242c38] rounded overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-[#161c24] border-b border-[#242c38] text-[10px] font-mono text-slate-400 uppercase tracking-wider">
                    <th className="py-2.5 px-3">Type</th>
                    <th className="py-2.5 px-3">Provenance / Location</th>
                    <th className="py-2.5 px-3">Evidence Content / Metric</th>
                    <th className="py-2.5 px-3">Extracted Value</th>
                    <th className="py-2.5 px-3">Confidence</th>
                    <th className="py-2.5 px-3">Status</th>
                    <th className="py-2.5 px-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1e2633] text-xs font-mono">
                  {loading && (
                    <tr>
                      <td colSpan={7} className="text-center py-8 text-slate-500">
                        <RefreshCw className="w-4 h-4 animate-spin mx-auto mb-2" />
                        Loading universal evidence register...
                      </td>
                    </tr>
                  )}

                  {!loading && items.length === 0 && (
                    <tr>
                      <td colSpan={7} className="text-center py-8 text-slate-500">
                        No evidence items found matching the selected filter.
                      </td>
                    </tr>
                  )}

                  {!loading &&
                    items.map((item) => (
                      <tr key={item.id} className="hover:bg-[#181f2a] transition-colors">
                        <td className="py-2.5 px-3 whitespace-nowrap">
                          {getModalityBadge(item.evidence_type)}
                        </td>

                        <td className="py-2.5 px-3">
                          <div className="text-[11px] font-bold text-slate-200">{item.provenance_display}</div>
                          <div className="text-[10px] text-slate-400 truncate max-w-[160px]" title={item.document_title}>
                            {item.document_title}
                          </div>
                        </td>

                        <td className="py-2.5 px-3 max-w-[220px]">
                          <span className="text-slate-200 line-clamp-1" title={item.content_preview}>
                            {item.content_preview}
                          </span>
                        </td>

                        <td className="py-2.5 px-3 whitespace-nowrap">
                          {item.value ? (
                            <span className="font-bold text-emerald-300">
                              {item.value} {item.unit || ''}
                            </span>
                          ) : (
                            <span className="text-slate-500 italic">--</span>
                          )}
                        </td>

                        <td className="py-2.5 px-3 whitespace-nowrap">
                          <div className="flex items-center gap-1.5">
                            <div className="w-12 bg-[#1f2733] rounded-full h-1.5 overflow-hidden">
                              <div
                                className={`h-full ${
                                  item.confidence_score >= 0.85
                                    ? 'bg-emerald-500'
                                    : item.confidence_score >= 0.6
                                    ? 'bg-blue-500'
                                    : 'bg-amber-500'
                                }`}
                                style={{ width: `${Math.round(item.confidence_score * 100)}%` }}
                              />
                            </div>
                            <span className="text-[10px] text-slate-400">
                              {item.confidence_score.toFixed(2)}
                            </span>
                          </div>
                        </td>

                        <td className="py-2.5 px-3 whitespace-nowrap">
                          {getStatusBadge(item.verification_status)}
                        </td>

                        <td className="py-2.5 px-3 text-right whitespace-nowrap">
                          <button
                            onClick={() => {
                              setInspectItem(item);
                              setReviewAction(null);
                              setCorrectedValue(item.value || '');
                              setReviewNotes('');
                            }}
                            className="px-2.5 py-1 text-[11px] font-bold bg-[#1e2837] hover:bg-blue-900/40 text-blue-300 border border-[#2f3d52] hover:border-blue-700 rounded transition-colors"
                          >
                            Inspect
                          </button>
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>

            <div className="p-2.5 bg-[#161c24] border-t border-[#242c38] flex items-center justify-between text-[11px] font-mono text-slate-400">
              <span>Showing {items.length} of {totalCount} records</span>
              <span className="text-[10px] text-slate-500">Evidence Provenance strictly linked to source files</span>
            </div>
          </div>
        </div>

        {/* Right 1 Col: Discovered Cross-Document Relationships */}
        <div className="space-y-4">
          <div className="bg-[#12161d] border border-[#242c38] rounded p-4 space-y-3 sticky top-6">
            <div className="flex items-center gap-2 pb-2 border-b border-[#242c38]">
              <GitBranch className="w-4 h-4 text-cyan-400" />
              <h2 className="text-xs font-mono font-bold text-slate-200 uppercase tracking-wider">
                Evidence Relationships
              </h2>
            </div>
            <p className="text-[11px] font-mono text-slate-400">
              Deterministic cross-document links discovered automatically during ingestion:
            </p>

            {relationships.length === 0 ? (
              <div className="py-8 text-center text-slate-500 text-xs font-mono">
                No cross-document links discovered yet. Ingest multiple records for the same mine/block to trigger automatic linkage.
              </div>
            ) : (
              <div className="space-y-2.5 max-h-[700px] overflow-y-auto pr-1">
                {relationships.map((rel) => (
                  <div
                    key={rel.id}
                    className="p-3 bg-[#161c24] border border-[#242c38] rounded space-y-2 hover:border-[#384457] transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <span className="px-1.5 py-0.5 rounded text-[9px] font-mono font-bold bg-cyan-950 text-cyan-300 border border-cyan-800">
                        {rel.relationship_type.replace(/_/g, ' ')}
                      </span>
                      <span className="text-[10px] font-mono text-slate-500">
                        {(rel.confidence * 100).toFixed(0)}%
                      </span>
                    </div>

                    <div className="space-y-1 text-xs font-mono">
                      <div className="text-slate-300 font-bold truncate" title={rel.source_title}>
                        {rel.source_title}
                      </div>
                      <div className="text-[10px] text-slate-500 flex items-center gap-1">
                        <ArrowRight className="w-2.5 h-2.5 text-cyan-500" />
                        <span className="truncate" title={rel.target_title}>
                          {rel.target_title}
                        </span>
                      </div>
                    </div>

                    {rel.description && (
                      <p className="text-[10px] text-slate-400 bg-[#0d1015] p-1.5 rounded border border-[#1f2733]">
                        {rel.description}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Evidence Inspector / Review Modal */}
      {inspectItem && (
        <div className="fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-4">
          <div className="bg-[#12161d] border border-[#2f3d52] rounded-lg max-w-2xl w-full p-5 space-y-4 shadow-xl">
            <div className="flex items-center justify-between pb-3 border-b border-[#242c38]">
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono font-bold text-slate-100 uppercase">
                  Evidence Inspector & Human Verification
                </span>
                {getModalityBadge(inspectItem.evidence_type)}
              </div>
              <button
                onClick={() => setInspectItem(null)}
                className="text-slate-400 hover:text-slate-200 text-sm font-bold"
              >
                ✕
              </button>
            </div>

            {/* Provenance Box */}
            <div className="bg-[#0d1015] border border-[#242c38] rounded p-3 space-y-2 text-xs font-mono">
              <div className="flex items-center justify-between text-[11px] text-slate-400">
                <span>Location: <strong className="text-slate-200">{inspectItem.provenance_display}</strong></span>
                <span>Document ID: {inspectItem.document_id.slice(0, 8)}...</span>
              </div>
              <div className="text-slate-300 font-bold">Document: {inspectItem.document_title}</div>
            </div>

            {/* Visual Preview if VISUAL */}
            {inspectItem.evidence_type === 'VISUAL' && inspectItem.metadata?.image_id && (
              <div className="space-y-2 bg-[#0d1015] p-3 rounded border border-[#242c38]">
                <span className="text-[10px] font-mono text-slate-400 uppercase">Visual Asset Preview:</span>
                <div className="flex justify-center bg-black/40 rounded p-2 border border-[#1f2733] max-h-60 overflow-hidden">
                  <img
                    src={`/api/v1/visuals/${inspectItem.metadata.image_id}/image`}
                    alt="Visual evidence"
                    className="max-h-56 object-contain rounded"
                    onError={(e) => {
                      (e.target as HTMLElement).style.display = 'none';
                    }}
                  />
                </div>
                {inspectItem.metadata.ocr_snippet && (
                  <p className="text-[11px] font-mono text-slate-400">
                    <strong>OCR Text:</strong> {inspectItem.metadata.ocr_snippet}
                  </p>
                )}
              </div>
            )}

            {/* Structured Value details if VALUE */}
            {inspectItem.evidence_type === 'STRUCTURED_VALUE' && (
              <div className="grid grid-cols-2 gap-3 bg-[#0d1015] p-3 rounded border border-[#242c38] text-xs font-mono">
                <div>
                  <span className="text-slate-500 text-[10px] uppercase">Field Name:</span>
                  <p className="text-slate-200 font-bold">{inspectItem.field_name}</p>
                </div>
                <div>
                  <span className="text-slate-500 text-[10px] uppercase">Normalized Value:</span>
                  <p className="text-emerald-400 font-bold text-sm">
                    {inspectItem.value} {inspectItem.unit || ''}
                  </p>
                </div>
              </div>
            )}

            {/* Review Form */}
            <form onSubmit={handleReviewSubmit} className="space-y-3 pt-2 border-t border-[#242c38]">
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono font-bold text-slate-300">Action:</span>
                <button
                  type="button"
                  onClick={() => setReviewAction('APPROVE')}
                  className={`px-3 py-1 rounded text-xs font-mono font-bold transition-colors ${
                    reviewAction === 'APPROVE'
                      ? 'bg-emerald-600 text-white'
                      : 'bg-[#1a2332] text-emerald-400 hover:bg-[#233045]'
                  }`}
                >
                  ✓ Approve
                </button>
                <button
                  type="button"
                  onClick={() => setReviewAction('CORRECT')}
                  className={`px-3 py-1 rounded text-xs font-mono font-bold transition-colors ${
                    reviewAction === 'CORRECT'
                      ? 'bg-blue-600 text-white'
                      : 'bg-[#1a2332] text-blue-400 hover:bg-[#233045]'
                  }`}
                >
                  ✎ Correct Value
                </button>
                <button
                  type="button"
                  onClick={() => setReviewAction('REJECT')}
                  className={`px-3 py-1 rounded text-xs font-mono font-bold transition-colors ${
                    reviewAction === 'REJECT'
                      ? 'bg-rose-600 text-white'
                      : 'bg-[#1a2332] text-rose-400 hover:bg-[#233045]'
                  }`}
                >
                  ✕ Reject
                </button>
              </div>

              {reviewAction === 'CORRECT' && (
                <div>
                  <label className="text-[11px] font-mono text-slate-400 block mb-1">
                    Corrected Value:
                  </label>
                  <input
                    type="text"
                    value={correctedValue}
                    onChange={(e) => setCorrectedValue(e.target.value)}
                    required
                    className="w-full px-3 py-1.5 bg-[#0d1015] border border-[#2b3544] rounded text-xs font-mono text-slate-200"
                  />
                </div>
              )}

              {reviewAction && (
                <div>
                  <label className="text-[11px] font-mono text-slate-400 block mb-1">
                    Verification Notes:
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Cross-verified with physical dispatch slip"
                    value={reviewNotes}
                    onChange={(e) => setReviewNotes(e.target.value)}
                    className="w-full px-3 py-1.5 bg-[#0d1015] border border-[#2b3544] rounded text-xs font-mono text-slate-200"
                  />
                </div>
              )}

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setInspectItem(null)}
                  className="px-3 py-1.5 text-xs font-mono text-slate-400 hover:text-slate-200"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!reviewAction || submittingReview}
                  className="px-4 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded text-xs font-mono font-bold"
                >
                  {submittingReview ? 'Submitting...' : 'Commit Verification'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
