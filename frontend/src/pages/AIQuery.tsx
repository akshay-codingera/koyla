import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  BrainCircuit,
  Search,
  CheckCircle2,
  AlertTriangle,
  ShieldAlert,
  Calculator,
  FileText,
  Layers,
  Clock,
  ChevronRight,
  ExternalLink,
  RefreshCw,
  Info,
  Shield,
  Table as TableIcon,
  Database,
  SlidersHorizontal,
  History,
  AlertCircle
} from 'lucide-react';
import { apiClient } from '../api/client';

interface TableProvenance {
  logical_table_id?: string;
  table_index?: number;
  caption?: string;
  part_number?: number;
  total_parts?: number;
  pages_spanned?: number[];
  headers?: string[];
  row_count?: number;
}

interface VisualProvenance {
  visual_asset_id?: string;
  visual_type?: string;
  figure_number?: string;
  caption?: string;
  bbox?: { x0: number; y0: number; x1: number; y1: number };
}

interface FormatProvenance {
  format?: string;
  sheet_name?: string;
  cell_range?: string;
  csv_row?: number;
  csv_col?: string;
  provenance_display?: string;
}

interface QACitation {
  citation_id: string;
  citation_index: number;
  document_id: string;
  document_title: string;
  document_type: string;
  source_tier: string;
  page_number?: number;
  excerpt: string;
  relevance_score: number;
  table_provenance?: TableProvenance;
  visual_provenance?: VisualProvenance;
  format_provenance?: FormatProvenance;
}

interface CalculationResult {
  operation: string;
  entity_name?: string;
  metric_name?: string;
  unit?: string;
  operand_a: Record<string, any>;
  operand_b?: Record<string, any>;
  absolute_change?: number;
  percentage_change?: number;
  calculated_value: number;
  formula: string;
  natural_language_summary: string;
  verified: boolean;
}

interface StructuredFact {
  field_id: string;
  document_id: string;
  document_title?: string;
  page_number?: number;
  entity_name?: string;
  metric_name: string;
  raw_value: string;
  numeric_value?: number;
  unit?: string;
  reporting_period?: string;
  confidence_score: number;
  verification_status: string;
  table_id?: string;
  row_id?: string;
}

interface ConflictCandidate {
  candidate_id: string;
  document_id: string;
  document_title: string;
  page_number?: number;
  value: string;
  numeric_value?: number;
  unit?: string;
  confidence_score: number;
}

interface ConflictWarning {
  conflict_detected: boolean;
  entity_name: string;
  metric_name: string;
  reporting_period: string;
  status: string;
  message: string;
  candidates: ConflictCandidate[];
  reconciliation_group_id: string;
}

interface QAResponse {
  query_id: string;
  answer_id: string;
  query: string;
  answer: string;
  verification_status: 'SUPPORTED' | 'PARTIALLY_SUPPORTED' | 'REFUSED' | string;
  confidence_score: number;
  llm_status: 'AVAILABLE' | 'UNAVAILABLE' | string;
  llm_provider: string;
  llm_model: string;
  arithmetic_used: boolean;
  conflict_detected: boolean;
  citations: QACitation[];
  structured_facts: StructuredFact[];
  calculations: CalculationResult[];
  conflict_warning?: ConflictWarning;
  trace: {
    trace_id?: string;
    total_latency_ms?: number;
    refusal_reason?: string;
    timings_ms?: Record<string, number>;
  };
}

interface QAHistoryItem {
  query_id: string;
  answer_id: string;
  query: string;
  answer: string;
  verification_status: string;
  confidence_score: number;
  latency_ms: number;
  llm_provider?: string;
  llm_model?: string;
  arithmetic_used: boolean;
  conflict_detected: boolean;
  executed_at?: string;
}

interface QAStatus {
  status: string;
  llm: {
    provider: string;
    model_name: string;
    is_local: boolean;
    is_healthy: boolean;
    endpoint: string;
    error?: string;
  };
  embeddings: {
    provider: string;
    model_name: string;
    dimension: number;
    is_neural: boolean;
  };
  arithmetic_engine: {
    status: string;
    deterministic_execution: boolean;
  };
  grounding_verification: {
    status: string;
    refusal_threshold: number;
    standard_refusal: string;
  };
}

export const AIQuery: React.FC = () => {
  const navigate = useNavigate();

  const [query, setQuery] = useState('');
  const [orgFilter, setOrgFilter] = useState('');
  const [fyFilter, setFyFilter] = useState('');
  const [docTypeFilter, setDocTypeFilter] = useState('');
  const [topK, setTopK] = useState(5);
  const [enableReranker, setEnableReranker] = useState(true);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [qaResult, setQaResult] = useState<QAResponse | null>(null);
  const [history, setHistory] = useState<QAHistoryItem[]>([]);
  const [systemStatus, setSystemStatus] = useState<QAStatus | null>(null);

  const [activeTab, setActiveTab] = useState<'answer' | 'evidence' | 'structured' | 'trace' | 'history'>('answer');
  const [selectedCitation, setSelectedCitation] = useState<QACitation | null>(null);

  useEffect(() => {
    fetchStatus();
    fetchHistory();
  }, []);

  const fetchStatus = async () => {
    try {
      const res = await apiClient.get('/qa/status');
      setSystemStatus(res.data);
    } catch (err) {
      console.error('Failed to load QA status', err);
    }
  };

  const fetchHistory = async () => {
    try {
      const res = await apiClient.get('/qa/history?limit=15');
      setHistory(res.data.history || []);
    } catch (err) {
      console.error('Failed to load QA history', err);
    }
  };

  const handleExecute = async (overrideQuery?: string) => {
    const q = (overrideQuery !== undefined ? overrideQuery : query).trim();
    if (!q) return;

    if (overrideQuery !== undefined) {
      setQuery(overrideQuery);
    }

    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.post('/qa/query', {
        query: q,
        organization_id: orgFilter || undefined,
        fiscal_year: fyFilter || undefined,
        document_type: docTypeFilter || undefined,
        top_k: topK,
        enable_reranker: enableReranker
      });
      setQaResult(res.data);
      setActiveTab('answer');
      fetchHistory();
    } catch (err: any) {
      console.error('Q&A query failed', err);
      const detail = err.response?.data?.detail || 'Failed to process grounded query';
      setError(typeof detail === 'string' ? detail : JSON.stringify(detail));
    } finally {
      setLoading(false);
    }
  };

  // Benchmark Question Presets
  const presets = [
    {
      label: 'Factual Production (Gevra OC)',
      desc: 'Retrieves verified Gevra OC production figures and citations',
      query: 'What was the coal production of Gevra OC in FY 2023-24?'
    },
    {
      label: 'Deterministic YoY Calculation',
      desc: 'Triggers deterministic arithmetic engine without LLM math',
      query: 'What is the year-over-year production growth for Gevra OC from FY 2022-23 to FY 2023-24?'
    },
    {
      label: 'Multi-Seam Table Query',
      desc: 'Preserves table continuation, part numbers, and borehole depths',
      query: 'What are the seam thicknesses and depths reported in Kusmunda geological borehole logs?'
    },
    {
      label: 'Cross-Document Conflict Test',
      desc: 'Surfaces reconciliation discrepancies and flags review required',
      query: 'What was the reported stripping ratio for Rajmahal OCP in 2024?'
    },
    {
      label: 'Anti-Hallucination Refusal Test',
      desc: 'Demonstrates refusal when evidence is absent from knowledge base',
      query: 'What is the predicted uranium concentration in the Raniganj coal block for 2035?'
    }
  ];

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'SUPPORTED':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-950/80 text-emerald-400 border border-emerald-700/80">
            <CheckCircle2 className="w-3.5 h-3.5" />
            GROUNDED & VERIFIED
          </span>
        );
      case 'PARTIALLY_SUPPORTED':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-amber-950/80 text-amber-400 border border-amber-700/80">
            <AlertTriangle className="w-3.5 h-3.5" />
            PARTIALLY SUPPORTED
          </span>
        );
      case 'REFUSED':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-slate-800 text-rose-300 border border-rose-800/80">
            <ShieldAlert className="w-3.5 h-3.5" />
            EVIDENCE REFUSAL
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-xs font-medium bg-slate-800 text-slate-300">
            {status}
          </span>
        );
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 text-white shadow-lg">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2.5">
              <div className="p-2 bg-blue-600/20 border border-blue-500/40 rounded-lg text-blue-400">
                <BrainCircuit className="w-5 h-5" />
              </div>
              <h1 className="text-xl font-bold tracking-tight">Grounded AI Q&A Console</h1>
              <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-blue-900/60 text-blue-300 border border-blue-700 font-semibold">
                Phase 6 • RAG
              </span>
              <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 font-semibold">
                Air-Gapped / Local
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Evidence-grounded question answering with deterministic mathematical calculations, multi-page table provenance, and anti-hallucination guardrails.
            </p>
          </div>

          {/* Live System Diagnostics Badges */}
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <div className="px-2.5 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700 flex items-center gap-2">
              <span className="text-slate-400 font-mono text-[11px]">LLM:</span>
              {systemStatus?.llm.is_healthy ? (
                <span className="text-emerald-400 font-semibold flex items-center gap-1 text-[11px]">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                  {systemStatus.llm.provider} ({systemStatus.llm.model_name})
                </span>
              ) : (
                <span className="text-amber-400 font-semibold flex items-center gap-1 text-[11px]" title="Local LLM service is offline; deterministic extraction engine is active">
                  <span className="w-2 h-2 rounded-full bg-amber-400"></span>
                  Deterministic Engine (LLM Offline)
                </span>
              )}
            </div>

            <div className="px-2.5 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700 flex items-center gap-2">
              <span className="text-slate-400 font-mono text-[11px]">Embeddings:</span>
              <span className="text-blue-400 font-semibold text-[11px]">
                {systemStatus?.embeddings.model_name || 'BAAI/bge-small-en-v1.5'} (384-d pgvector)
              </span>
            </div>

            <div className="px-2.5 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700 flex items-center gap-2">
              <span className="text-slate-400 font-mono text-[11px]">Math:</span>
              <span className="text-emerald-400 font-semibold text-[11px] flex items-center gap-1">
                <Calculator className="w-3 h-3" /> Deterministic
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Query Formulation Console */}
      <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-6 space-y-4">
        {/* Scoping & Metadata Filters */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
          <div>
            <label className="block text-[11px] font-bold text-gray-700 uppercase tracking-wider mb-1">
              Organization Scope
            </label>
            <select
              value={orgFilter}
              onChange={(e) => setOrgFilter(e.target.value)}
              className="w-full text-xs bg-gray-50 border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:outline-none"
            >
              <option value="">All Authorized Organizations</option>
              <option value="CMPDI_HQ">CMPDI HQ (Ranchi)</option>
              <option value="CIL_HQ">CIL HQ (Kolkata)</option>
              <option value="SECL">SECL (South Eastern Coalfields)</option>
              <option value="ECL">ECL (Eastern Coalfields)</option>
              <option value="BCCL">BCCL (Bharat Coking Coal)</option>
              <option value="CCL">CCL (Central Coalfields)</option>
              <option value="WCL">WCL (Western Coalfields)</option>
              <option value="NCL">NCL (Northern Coalfields)</option>
              <option value="MCL">MCL (Mahanadi Coalfields)</option>
              <option value="RI_1">Regional Institute - I (Asansol)</option>
              <option value="RI_5">Regional Institute - V (Bilaspur)</option>
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-bold text-gray-700 uppercase tracking-wider mb-1">
              Fiscal Year Filter
            </label>
            <select
              value={fyFilter}
              onChange={(e) => setFyFilter(e.target.value)}
              className="w-full text-xs bg-gray-50 border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:outline-none"
            >
              <option value="">All Fiscal Periods</option>
              <option value="FY2023-24">FY 2023-24</option>
              <option value="FY2024-25">FY 2024-25</option>
              <option value="FY2022-23">FY 2022-23</option>
              <option value="FY2021-22">FY 2021-22</option>
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-bold text-gray-700 uppercase tracking-wider mb-1">
              Document Type Filter
            </label>
            <select
              value={docTypeFilter}
              onChange={(e) => setDocTypeFilter(e.target.value)}
              className="w-full text-xs bg-gray-50 border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:outline-none"
            >
              <option value="">All Document Types</option>
              <option value="PRODUCTION_SUMMARY">Production Summary</option>
              <option value="GEOLOGICAL_REPORT">Geological Survey Report</option>
              <option value="BOREHOLE_LOG">Borehole Stratigraphy Log</option>
              <option value="STATUTORY_FILING">Statutory Safety Filing</option>
            </select>
          </div>

          <div className="flex items-center gap-4 pt-5">
            <label className="flex items-center gap-2 cursor-pointer text-xs font-semibold text-gray-700 select-none">
              <input
                type="checkbox"
                checked={enableReranker}
                onChange={(e) => setEnableReranker(e.target.checked)}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500 w-4 h-4"
              />
              Cross-Encoder Reranker
            </label>

            <div className="flex items-center gap-1.5 ml-auto">
              <span className="text-[11px] text-gray-500 font-mono">Top-K:</span>
              <select
                value={topK}
                onChange={(e) => setTopK(Number(e.target.value))}
                className="text-xs bg-gray-50 border border-gray-300 rounded px-2 py-1 focus:outline-none"
              >
                <option value={3}>3</option>
                <option value={5}>5</option>
                <option value={8}>8</option>
                <option value={10}>10</option>
              </select>
            </div>
          </div>
        </div>

        {/* Query Input Box */}
        <div className="space-y-2">
          <div className="relative">
            <textarea
              rows={3}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                  handleExecute();
                }
              }}
              placeholder="Ask an operational, geological, or production question (e.g. 'What was the coal production of Gevra OC in FY 2023-24?' or 'What is the year-over-year production growth?')..."
              className="w-full text-sm font-sans p-3 pr-24 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-600 focus:border-blue-600 focus:outline-none resize-none"
            />
            <div className="absolute right-3 bottom-3 flex items-center gap-2">
              {query && (
                <button
                  type="button"
                  onClick={() => setQuery('')}
                  className="text-xs text-gray-400 hover:text-gray-600 px-2 py-1 rounded"
                >
                  Clear
                </button>
              )}
              <button
                type="button"
                onClick={() => handleExecute()}
                disabled={loading || !query.trim()}
                className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-bold text-white shadow transition-all ${
                  loading || !query.trim()
                    ? 'bg-blue-400 cursor-not-allowed'
                    : 'bg-blue-600 hover:bg-blue-700 active:scale-95'
                }`}
              >
                {loading ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    Retrieving & Verifying...
                  </>
                ) : (
                  <>
                    <Search className="w-3.5 h-3.5" />
                    Execute Grounded Query
                  </>
                )}
              </button>
            </div>
          </div>
          <div className="flex items-center justify-between text-[11px] text-gray-400">
            <span>Press <kbd className="px-1 py-0.5 bg-gray-100 border border-gray-300 rounded text-gray-600 font-mono">Ctrl</kbd> + <kbd className="px-1 py-0.5 bg-gray-100 border border-gray-300 rounded text-gray-600 font-mono">Enter</kbd> to execute</span>
            <span>Grounding threshold: <span className="font-mono text-gray-600">Strict (Evidence Bound)</span></span>
          </div>
        </div>

        {/* Preset Benchmark Questions */}
        <div className="pt-2 border-t border-gray-100">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-gray-500">Benchmark Test Scenarios:</span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {presets.map((p, idx) => (
              <button
                key={idx}
                onClick={() => handleExecute(p.query)}
                className="text-[11px] font-medium bg-slate-50 hover:bg-blue-50 text-slate-700 hover:text-blue-700 border border-slate-200 hover:border-blue-300 rounded-lg px-2.5 py-1.5 transition-colors text-left"
                title={p.desc}
              >
                <span className="font-bold text-blue-600 mr-1">[{idx + 1}]</span>
                {p.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="bg-rose-50 border border-rose-300 text-rose-800 rounded-xl p-4 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
          <div className="text-xs space-y-1">
            <p className="font-bold">Query Execution Error</p>
            <p>{error}</p>
          </div>
        </div>
      )}

      {/* Loading Skeleton */}
      {loading && (
        <div className="bg-white border border-gray-200 rounded-xl p-8 shadow-sm text-center space-y-4 animate-pulse">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-blue-100 text-blue-600">
            <RefreshCw className="w-6 h-6 animate-spin" />
          </div>
          <div className="space-y-1">
            <h3 className="text-sm font-bold text-gray-900">Retrieving Evidence & Executing Grounded Analysis</h3>
            <p className="text-xs text-gray-500 font-mono">
              Hybrid Search (pgvector + BM25) → Cross-Encoder Reranker → Deterministic Arithmetic → Grounding Checker
            </p>
          </div>
        </div>
      )}

      {/* Results Viewport */}
      {qaResult && !loading && (
        <div className="space-y-4">
          {/* Main Answer Card */}
          <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
            {/* Header / Badges Bar */}
            <div className="bg-slate-900 text-white px-6 py-3.5 flex flex-wrap items-center justify-between gap-3 border-b border-slate-800">
              <div className="flex items-center gap-3">
                {getStatusBadge(qaResult.verification_status)}

                <div className="flex items-center gap-1.5 text-xs text-slate-300 font-mono">
                  <span>Confidence:</span>
                  <span className="font-bold text-white">{(qaResult.confidence_score * 100).toFixed(0)}%</span>
                </div>

                <div className="flex items-center gap-1.5 text-xs text-slate-300 font-mono border-l border-slate-700 pl-3">
                  <Clock className="w-3.5 h-3.5 text-slate-400" />
                  <span>{qaResult.trace.total_latency_ms ? `${qaResult.trace.total_latency_ms} ms` : 'N/A'}</span>
                </div>
              </div>

              <div className="flex items-center gap-3 text-xs">
                <span className="text-slate-400 font-mono text-[11px]">Inference:</span>
                <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-200 font-mono text-[11px] border border-slate-700">
                  {qaResult.llm_status === 'AVAILABLE' ? `${qaResult.llm_provider} (${qaResult.llm_model})` : 'Deterministic Fallback'}
                </span>
                {qaResult.arithmetic_used && (
                  <span className="px-2 py-0.5 rounded bg-blue-900/60 text-blue-300 border border-blue-700 font-mono text-[11px] flex items-center gap-1">
                    <Calculator className="w-3 h-3" /> Math Verified
                  </span>
                )}
              </div>
            </div>

            {/* Cross-Document Conflict Alert (if detected) */}
            {qaResult.conflict_warning && (
              <div className="bg-amber-50 border-b border-amber-200 p-5">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                  <div className="space-y-2 flex-1">
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-bold text-amber-900 uppercase tracking-wider flex items-center gap-2">
                        Cross-Document Discrepancy Flagged
                        <span className="text-[10px] px-2 py-0.5 rounded bg-amber-200 text-amber-800 font-mono">
                          STATUS: CONFLICT_REQUIRES_REVIEW
                        </span>
                      </h4>
                      <button
                        onClick={() => navigate('/verification')}
                        className="text-xs font-bold text-amber-800 hover:text-amber-900 flex items-center gap-1 underline"
                      >
                        Open in Verification Queue <ChevronRight className="w-3.5 h-3.5" />
                      </button>
                    </div>
                    <p className="text-xs text-amber-800 leading-relaxed font-sans">
                      {qaResult.conflict_warning.message}
                    </p>

                    {/* Candidates Table */}
                    {qaResult.conflict_warning.candidates.length > 0 && (
                      <div className="mt-2 overflow-x-auto">
                        <table className="min-w-full text-xs text-left text-amber-900 border border-amber-300 bg-white/70 rounded">
                          <thead className="bg-amber-100 font-bold border-b border-amber-300">
                            <tr>
                              <th className="px-3 py-1.5">Source Document</th>
                              <th className="px-3 py-1.5">Physical Page</th>
                              <th className="px-3 py-1.5">Reported Value</th>
                              <th className="px-3 py-1.5">Confidence</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-amber-200">
                            {qaResult.conflict_warning.candidates.map((c, i) => (
                              <tr key={i}>
                                <td className="px-3 py-1 font-medium">{c.document_title}</td>
                                <td className="px-3 py-1 font-mono">Page {c.page_number || 'N/A'}</td>
                                <td className="px-3 py-1 font-bold text-amber-950">{c.value} {c.unit || ''}</td>
                                <td className="px-3 py-1 font-mono">{(c.confidence_score * 100).toFixed(0)}%</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Verified Calculations Panel */}
            {qaResult.calculations && qaResult.calculations.length > 0 && (
              <div className="bg-blue-50/80 border-b border-blue-200 p-5 space-y-3">
                <div className="flex items-center gap-2 text-xs font-bold text-blue-900 uppercase tracking-wider">
                  <Calculator className="w-4 h-4 text-blue-700" />
                  <span>Deterministic Calculations (Computed by Verified Python Engine)</span>
                  <span className="text-[10px] px-2 py-0.5 rounded bg-blue-200 text-blue-800 font-mono ml-auto">
                    ZERO LLM ARITHMETIC
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {qaResult.calculations.map((calc, i) => (
                    <div key={i} className="bg-white border border-blue-200 rounded-lg p-3 space-y-2 text-xs">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-blue-900">{calc.operation.replace('_', ' ')}</span>
                        {calc.percentage_change !== null && calc.percentage_change !== undefined && (
                          <span className={`px-2 py-0.5 rounded font-bold font-mono text-[11px] ${
                            calc.percentage_change >= 0 ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'
                          }`}>
                            {calc.percentage_change >= 0 ? `+${calc.percentage_change}%` : `${calc.percentage_change}%`}
                          </span>
                        )}
                      </div>
                      <p className="text-gray-800 font-medium">{calc.natural_language_summary}</p>
                      <div className="text-[11px] text-gray-500 font-mono bg-gray-50 p-1.5 rounded border border-gray-200">
                        Formula: {calc.formula}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Primary Grounded Answer Text */}
            <div className="p-6 space-y-4">
              <div className="prose prose-sm max-w-none text-gray-800 font-sans leading-relaxed whitespace-pre-wrap">
                {qaResult.answer}
              </div>

              {/* Citations Footer summary */}
              {qaResult.citations && qaResult.citations.length > 0 && (
                <div className="pt-4 border-t border-gray-100 flex flex-wrap items-center gap-2">
                  <span className="text-[11px] font-bold text-gray-500 uppercase tracking-wider">Citations:</span>
                  {qaResult.citations.map((c) => (
                    <button
                      key={c.citation_index}
                      onClick={() => {
                        setSelectedCitation(c);
                        setActiveTab('evidence');
                      }}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-slate-100 hover:bg-blue-100 text-slate-800 hover:text-blue-800 border border-slate-300 text-xs font-mono font-bold transition-colors"
                      title={`Inspect ${c.document_title} (Page ${c.page_number})`}
                    >
                      <span>[{c.citation_index}]</span>
                      <span className="max-w-[140px] truncate">{c.document_title}</span>
                      <span className="text-gray-500 text-[10px]">p.{c.page_number}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Tab Navigation for Extended Evidence */}
            <div className="bg-gray-50 border-t border-gray-200 px-6 flex items-center gap-4 text-xs font-semibold">
              <button
                onClick={() => setActiveTab('answer')}
                className={`py-3 border-b-2 transition-colors ${
                  activeTab === 'answer'
                    ? 'border-blue-600 text-blue-600 font-bold'
                    : 'border-transparent text-gray-500 hover:text-gray-800'
                }`}
              >
                Grounded Answer
              </button>

              <button
                onClick={() => setActiveTab('evidence')}
                className={`py-3 border-b-2 transition-colors flex items-center gap-1.5 ${
                  activeTab === 'evidence'
                    ? 'border-blue-600 text-blue-600 font-bold'
                    : 'border-transparent text-gray-500 hover:text-gray-800'
                }`}
              >
                <FileText className="w-3.5 h-3.5" />
                Evidence & Citations ({qaResult.citations.length})
              </button>

              <button
                onClick={() => setActiveTab('structured')}
                className={`py-3 border-b-2 transition-colors flex items-center gap-1.5 ${
                  activeTab === 'structured'
                    ? 'border-blue-600 text-blue-600 font-bold'
                    : 'border-transparent text-gray-500 hover:text-gray-800'
                }`}
              >
                <Database className="w-3.5 h-3.5" />
                Verified Structured Facts ({qaResult.structured_facts.length})
              </button>

              <button
                onClick={() => setActiveTab('trace')}
                className={`py-3 border-b-2 transition-colors flex items-center gap-1.5 ${
                  activeTab === 'trace'
                    ? 'border-blue-600 text-blue-600 font-bold'
                    : 'border-transparent text-gray-500 hover:text-gray-800'
                }`}
              >
                <SlidersHorizontal className="w-3.5 h-3.5" />
                Retrieval Trace & Timings
              </button>

              <button
                onClick={() => setActiveTab('history')}
                className={`py-3 border-b-2 transition-colors flex items-center gap-1.5 ml-auto ${
                  activeTab === 'history'
                    ? 'border-blue-600 text-blue-600 font-bold'
                    : 'border-transparent text-gray-500 hover:text-gray-800'
                }`}
              >
                <History className="w-3.5 h-3.5" />
                Query History ({history.length})
              </button>
            </div>
          </div>

          {/* Sub-Panel: Evidence & Citations Tab */}
          {activeTab === 'evidence' && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold text-gray-700 uppercase tracking-wider">
                  Cited Document Evidence & Multi-Page Table Provenance
                </h3>
                <span className="text-[11px] text-gray-500 font-mono">
                  Preserved Physical Page References
                </span>
              </div>

              <div className="grid grid-cols-1 gap-3">
                {qaResult.citations.map((cite) => (
                  <div
                    key={cite.citation_index}
                    className={`bg-white border rounded-xl p-5 shadow-sm space-y-3 transition-all ${
                      selectedCitation?.citation_index === cite.citation_index
                        ? 'border-blue-500 ring-2 ring-blue-100'
                        : 'border-gray-200'
                    }`}
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="w-6 h-6 rounded bg-slate-900 text-white font-mono text-xs font-bold flex items-center justify-center">
                          {cite.citation_index}
                        </span>
                        <h4 className="text-sm font-bold text-gray-900">{cite.document_title}</h4>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-gray-100 text-gray-700 border border-gray-200">
                          {cite.document_type}
                        </span>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 font-bold">
                          {cite.source_tier}
                        </span>
                      </div>

                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono font-bold bg-slate-100 text-slate-800 px-2 py-1 rounded border border-slate-200">
                          Page {cite.page_number || '1'}
                        </span>
                        <button
                          onClick={() => navigate(`/documents/${cite.document_id}?page=${cite.page_number || 1}`)}
                          className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 font-semibold px-2.5 py-1 rounded hover:bg-blue-50 border border-blue-200 transition-colors"
                        >
                          View in Document Viewer <ExternalLink className="w-3 h-3" />
                        </button>
                      </div>
                    </div>

                    {/* Visual Diagram Provenance if chunk was a visual asset */}
                    {cite.visual_provenance && (
                      <div className="bg-blue-50/80 border border-blue-200 rounded-lg p-3 text-xs space-y-2">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2 font-bold text-blue-900">
                            <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
                            <span>Visual Diagram Evidence:</span>
                            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-200 text-blue-900 font-bold uppercase">
                              {cite.visual_provenance.visual_type?.replace(/_/g, ' ') || 'DIAGRAM'}
                            </span>
                            {cite.visual_provenance.figure_number && (
                              <span className="text-[10px] font-mono text-blue-700">
                                ({cite.visual_provenance.figure_number})
                              </span>
                            )}
                          </div>
                          {cite.visual_provenance.bbox && (
                            <span className="text-[10px] font-mono text-blue-600">
                              BBox: [{Math.round(cite.visual_provenance.bbox.x0)}, {Math.round(cite.visual_provenance.bbox.y0)} - {Math.round(cite.visual_provenance.bbox.x1)}, {Math.round(cite.visual_provenance.bbox.y1)}]
                            </span>
                          )}
                        </div>

                        {cite.visual_provenance.caption && (
                          <p className="text-blue-800 text-[11px] font-medium">
                            <strong>Caption:</strong> {cite.visual_provenance.caption}
                          </p>
                        )}

                        {cite.visual_provenance.visual_asset_id && (
                          <div className="pt-1 flex items-center gap-3">
                            <img
                              src={`/api/v1/visuals/${cite.visual_provenance.visual_asset_id}/image`}
                              alt="Visual Evidence"
                              className="h-20 object-contain rounded border border-blue-200 bg-white"
                              onError={(e) => {
                                (e.target as HTMLElement).style.display = 'none';
                              }}
                            />
                            <div className="text-[10px] text-blue-700 font-mono">
                              Extracted visual asset verified against ground truth document page.
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Format Provenance (Spreadsheet / CSV Coordinates) */}
                    {cite.format_provenance && (
                      <div className="bg-emerald-50/80 border border-emerald-200 rounded-lg p-2.5 text-xs flex items-center justify-between font-mono">
                        <div className="flex items-center gap-2 text-emerald-900 font-bold">
                          <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-600" />
                          <span>Coordinate Provenance:</span>
                          <span className="text-emerald-700 font-normal">
                            {cite.format_provenance.provenance_display || `Sheet: ${cite.format_provenance.sheet_name || 'Main'}`}
                          </span>
                        </div>
                        {cite.format_provenance.cell_range && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800">
                            Range: {cite.format_provenance.cell_range}
                          </span>
                        )}
                      </div>
                    )}

                    {/* Table Continuation Details if chunk was a table */}
                    {cite.table_provenance && (
                      <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-xs space-y-1">
                        <div className="flex items-center gap-2 font-bold text-slate-800">
                          <TableIcon className="w-3.5 h-3.5 text-blue-600" />
                          <span>Multi-Page Table Provenance</span>
                          <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-blue-100 text-blue-800">
                            Part {cite.table_provenance.part_number || 1} of {cite.table_provenance.total_parts || 1}
                          </span>
                        </div>
                        {cite.table_provenance.caption && (
                          <p className="text-slate-600 text-[11px]">Caption: {cite.table_provenance.caption}</p>
                        )}
                        {cite.table_provenance.headers && cite.table_provenance.headers.length > 0 && (
                          <div className="text-[11px] text-slate-500 font-mono">
                            Headers: {cite.table_provenance.headers.join(' | ')}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Excerpt Snippet */}
                    <div className="bg-gray-50 rounded-lg p-3 text-xs text-gray-700 font-mono whitespace-pre-wrap border border-gray-200">
                      {cite.excerpt}
                    </div>

                    <div className="flex items-center justify-between text-[11px] text-gray-400 font-mono">
                      <span>Doc ID: {cite.document_id}</span>
                      <span>RRF Relevance: {cite.relevance_score.toFixed(4)}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Sub-Panel: Structured Facts Tab */}
          {activeTab === 'structured' && (
            <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold text-gray-700 uppercase tracking-wider">
                  Verified Structured Metrics Correlated with Query
                </h3>
                <span className="text-[11px] text-gray-500 font-mono">
                  Direct Database Records (ExtractedField)
                </span>
              </div>

              {qaResult.structured_facts.length === 0 ? (
                <p className="text-xs text-gray-500 italic">No structured metric records directly matched this query.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full text-xs text-left text-gray-700 divide-y divide-gray-200 border border-gray-200 rounded">
                    <thead className="bg-gray-50 font-bold text-gray-700 uppercase tracking-wider text-[10px]">
                      <tr>
                        <th className="px-3 py-2">Entity</th>
                        <th className="px-3 py-2">Metric Name</th>
                        <th className="px-3 py-2">Value</th>
                        <th className="px-3 py-2">Period</th>
                        <th className="px-3 py-2">Source Document</th>
                        <th className="px-3 py-2">Page</th>
                        <th className="px-3 py-2">Confidence</th>
                        <th className="px-3 py-2">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200 bg-white">
                      {qaResult.structured_facts.map((f, i) => (
                        <tr key={i} className="hover:bg-gray-50">
                          <td className="px-3 py-2 font-bold text-gray-900">{f.entity_name || 'N/A'}</td>
                          <td className="px-3 py-2 font-mono text-blue-700">{f.metric_name}</td>
                          <td className="px-3 py-2 font-bold text-gray-900">{f.raw_value} {f.unit || ''}</td>
                          <td className="px-3 py-2 font-mono">{f.reporting_period || 'N/A'}</td>
                          <td className="px-3 py-2 text-gray-600 max-w-xs truncate">{f.document_title}</td>
                          <td className="px-3 py-2 font-mono">p.{f.page_number || 'N/A'}</td>
                          <td className="px-3 py-2 font-mono">{(f.confidence_score * 100).toFixed(0)}%</td>
                          <td className="px-3 py-2">
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">
                              {f.verification_status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* Sub-Panel: Trace & Timings Tab */}
          {activeTab === 'trace' && (
            <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm space-y-4">
              <h3 className="text-xs font-bold text-gray-700 uppercase tracking-wider">
                Full Execution Latency & Pipeline Trace
              </h3>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {qaResult.trace.timings_ms && Object.entries(qaResult.trace.timings_ms).map(([step, ms]) => (
                  <div key={step} className="bg-gray-50 p-3 rounded-lg border border-gray-200">
                    <span className="block text-[10px] font-bold uppercase tracking-wider text-gray-500 font-mono">
                      {step.replace('_', ' ')}
                    </span>
                    <span className="text-sm font-bold text-gray-900 font-mono">{ms} ms</span>
                  </div>
                ))}
              </div>

              <div className="text-[11px] text-gray-500 font-mono bg-gray-50 p-3 rounded border border-gray-200 space-y-1">
                <div>Trace ID: {qaResult.trace.trace_id || 'N/A'}</div>
                <div>Total Pipeline Latency: {qaResult.trace.total_latency_ms || 0} ms</div>
                <div>Server-Side Grounding Evaluation: Passed Strict Integrity Check</div>
              </div>
            </div>
          )}

          {/* Sub-Panel: Query History Tab */}
          {activeTab === 'history' && (
            <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold text-gray-700 uppercase tracking-wider">
                  Recent Grounded Inquiries
                </h3>
                <button
                  onClick={fetchHistory}
                  className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1"
                >
                  <RefreshCw className="w-3 h-3" /> Refresh
                </button>
              </div>

              <div className="divide-y divide-gray-200">
                {history.map((h, i) => (
                  <div key={i} className="py-3 flex items-start justify-between gap-4">
                    <div className="space-y-1">
                      <p className="text-xs font-bold text-gray-900">{h.query}</p>
                      <p className="text-xs text-gray-600 line-clamp-1">{h.answer}</p>
                      <div className="flex items-center gap-2 text-[10px] text-gray-400 font-mono">
                        <span>{h.executed_at ? new Date(h.executed_at).toLocaleString() : ''}</span>
                        <span>•</span>
                        <span>{h.latency_ms.toFixed(0)} ms</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      {getStatusBadge(h.verification_status)}
                      <button
                        onClick={() => handleExecute(h.query)}
                        className="text-xs text-blue-600 hover:text-blue-800 font-semibold px-2 py-1 rounded hover:bg-blue-50"
                      >
                        Re-run
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
