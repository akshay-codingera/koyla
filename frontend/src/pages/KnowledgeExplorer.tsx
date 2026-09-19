import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  Filter,
  Layers,
  FileText,
  Database,
  ExternalLink,
  ChevronRight,
  Info,
  Clock,
  CheckCircle2,
  Table as TableIcon,
  Shield,
  Activity,
  Hash,
  X,
  RefreshCw,
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

interface ProvenanceChain {
  document_id: string;
  document_title: string;
  version_id?: string;
  page_number: number;
  chunk_id: string;
  chunk_type: string;
  section_heading?: string;
  table?: TableProvenance;
}

interface RetrievalResultItem {
  result_id: string;
  chunk_id: string;
  document_id: string;
  document_version_id?: string;
  organization_id: string;
  organization_name?: string;
  title: string;
  document_type: string;
  source_tier: string;
  fiscal_year?: string;
  page_number: number;
  chunk_type: string;
  section_heading?: string;
  source_text: string;
  retrieval_method: string;
  keyword_rank?: number;
  keyword_score?: number;
  dense_rank?: number;
  dense_score?: number;
  rrf_score: number;
  reranker_score?: number;
  final_rank: number;
  provenance: ProvenanceChain;
}

interface RetrievalTrace {
  trace_id: string;
  query: string;
  normalized_query: {
    original_query: string;
    clean_query: string;
    entities: string[];
    metrics: string[];
    fiscal_years: string[];
    period_start?: string;
    period_end?: string;
    topics: string[];
    suggested_filters: Record<string, any>;
  };
  applied_filters: Record<string, any>;
  search_mode: string;
  keyword_candidate_count: number;
  dense_candidate_count: number;
  fused_candidate_count: number;
  final_result_count: number;
  reranker_status: string;
  timings_ms: {
    query_normalization: number;
    keyword_search: number;
    dense_search: number;
    rrf_fusion: number;
    reranking: number;
    total: number;
  };
}

export const KnowledgeExplorer: React.FC = () => {
  const navigate = useNavigate();

  const [query, setQuery] = useState('');
  const [searchMode, setSearchMode] = useState<'HYBRID' | 'SEMANTIC' | 'KEYWORD'>('HYBRID');
  const [selectedOrg, setSelectedOrg] = useState('');
  const [selectedFY, setSelectedFY] = useState('');
  const [selectedDocType, setSelectedDocType] = useState('');
  const [selectedTier, setSelectedTier] = useState('');
  const [topK, setTopK] = useState(10);
  const [enableReranker, setEnableReranker] = useState(true);

  const [organizations, setOrganizations] = useState<any[]>([]);
  const [results, setResults] = useState<RetrievalResultItem[]>([]);
  const [trace, setTrace] = useState<RetrievalTrace | null>(null);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [activeProvenanceModal, setActiveProvenanceModal] = useState<RetrievalResultItem | null>(null);
  const [showTraceModal, setShowTraceModal] = useState(false);
  const [statusInfo, setStatusInfo] = useState<any>(null);

  // Load authorized organizations and search status
  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        const [orgsRes, statusRes] = await Promise.all([
          apiClient.get('/organizations/'),
          apiClient.get('/search/status').catch(() => ({ data: null }))
        ]);
        setOrganizations(orgsRes.data);
        if (statusRes.data) {
          setStatusInfo(statusRes.data);
        }
      } catch (err) {
        console.error('Failed to load organizations or search status', err);
      }
    };
    fetchInitialData();
  }, []);

  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const payload: Record<string, any> = {
        query: query.trim(),
        search_mode: searchMode,
        top_k: topK,
        enable_reranker: enableReranker,
      };

      if (selectedOrg) payload.organization_id = selectedOrg;
      if (selectedFY) payload.fiscal_year = selectedFY;
      if (selectedDocType) payload.document_type = selectedDocType;
      if (selectedTier) payload.source_tier = selectedTier;

      const res = await apiClient.post('/search/query', payload);
      setResults(res.data.results || []);
      setTrace(res.data.trace || null);
      setSearched(true);
    } catch (err: any) {
      console.error('Search request failed', err);
      setError(err.response?.data?.detail || 'Search query failed. Please verify criteria.');
      setResults([]);
      setTrace(null);
      setSearched(true);
    } finally {
      setLoading(false);
    }
  };

  const getTierBadge = (tier: string) => {
    switch (tier) {
      case 'TIER_A':
        return <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-green-100 text-green-800 border border-green-300">Tier A: Authoritative</span>;
      case 'TIER_B':
        return <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-blue-100 text-blue-800 border border-blue-300">Tier B: Operational</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-amber-100 text-amber-800 border border-amber-300">Tier C: Unverified</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white p-5 rounded-lg border border-slate-200 shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">Knowledge Explorer</h1>
            <span className="px-2 py-0.5 rounded bg-blue-100 text-blue-800 text-xs font-semibold uppercase tracking-wider">
              Dual-Engine Retrieval
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Hybrid evidence retrieval combining PostgreSQL lexical/FTS search and pgvector dense embeddings with Reciprocal Rank Fusion.
          </p>
        </div>

        {trace && (
          <button
            onClick={() => setShowTraceModal(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded border border-slate-300 transition-colors shadow-sm"
          >
            <Activity className="w-3.5 h-3.5 text-blue-600" />
            Inspect Retrieval Trace ({trace.timings_ms.total}ms)
          </button>
        )}
      </div>

      {/* Active Embedding Engine Status Banner */}
      {statusInfo && (
        <div className="bg-slate-50 border border-slate-200 rounded-lg p-3.5 px-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2.5 text-xs shadow-sm">
          <div className="flex items-center gap-2 flex-wrap">
            <Database className="w-4 h-4 text-blue-600 flex-shrink-0" />
            <span className="font-bold text-slate-700">Active Vector Provider:</span>
            <span className="font-mono bg-white px-2 py-0.5 border border-slate-300 rounded font-semibold text-slate-800">
              {statusInfo.provider_info?.model_name || 'koyla-deterministic-hash-384'}
            </span>
            <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${
              statusInfo.provider_info?.is_neural
                ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                : 'bg-amber-50 text-amber-900 border border-amber-300'
            }`}>
              {statusInfo.provider_info?.is_neural ? 'Neural SentenceTransformer (384-d)' : 'Deterministic Feature Hash (384-d)'}
            </span>
            <span className="text-slate-500 italic text-[11px]">
              {statusInfo.provider_info?.is_neural
                ? '(BAAI/bge-small-en-v1.5 running locally on PyTorch CPU)'
                : '(Deterministic fallback active)'}
            </span>
          </div>
          <div className="flex items-center gap-3 text-slate-600 font-mono text-[11px] flex-wrap">
            <span>Index Coverage: <strong className="text-slate-900">{statusInfo.coverage_pct}%</strong> ({statusInfo.total_embeddings}/{statusInfo.total_chunks} chunks)</span>
            <span className="text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200 font-bold">
              pgvector {statusInfo.health?.status === 'UP' ? 'ONLINE' : 'OFFLINE'}
            </span>
          </div>
        </div>
      )}

      {/* Search & Mode Selector Card */}
      <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-sm space-y-4">
        {/* Search Mode Tabs */}
        <div className="flex items-center justify-between border-b border-slate-200 pb-3">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider mr-1">Mode:</span>
            <button
              type="button"
              onClick={() => setSearchMode('HYBRID')}
              className={`px-3 py-1 text-xs font-bold rounded-md transition-colors ${
                searchMode === 'HYBRID'
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              Hybrid (Recommended)
            </button>
            <button
              type="button"
              onClick={() => setSearchMode('SEMANTIC')}
              className={`px-3 py-1 text-xs font-bold rounded-md transition-colors ${
                searchMode === 'SEMANTIC'
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              Semantic (Dense pgvector)
            </button>
            <button
              type="button"
              onClick={() => setSearchMode('KEYWORD')}
              className={`px-3 py-1 text-xs font-bold rounded-md transition-colors ${
                searchMode === 'KEYWORD'
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              Keyword (PostgreSQL FTS)
            </button>
          </div>

          <div className="flex items-center gap-2">
            <label className="flex items-center gap-1.5 text-xs text-slate-600 cursor-pointer">
              <input
                type="checkbox"
                checked={enableReranker}
                onChange={(e) => setEnableReranker(e.target.checked)}
                className="rounded border-slate-300 text-blue-600 focus:ring-blue-500 w-3.5 h-3.5"
              />
              Cross-Encoder Reranker
            </label>
          </div>
        </div>

        {/* Search Input Bar */}
        <form onSubmit={handleSearch} className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3.5 top-3 w-4 h-4 text-slate-400" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search reports, boreholes (e.g. BH-01), geological seams, production figures, or financial years..."
              className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-300 rounded-md text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all font-sans"
            />
          </div>
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-semibold text-sm rounded-md shadow-sm flex items-center gap-2 transition-colors"
          >
            {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            Retrieve Evidence
          </button>
        </form>

        {/* Query Normalization Chips (Live Context) */}
        {trace && (
          <div className="bg-slate-50 border border-slate-200 rounded p-3 flex flex-wrap items-center gap-2 text-xs">
            <span className="font-bold text-slate-600 flex items-center gap-1">
              <Info className="w-3.5 h-3.5 text-blue-600" />
              Detected in Query:
            </span>
            {trace.normalized_query.entities.length > 0 && (
              <span className="px-2 py-0.5 bg-indigo-100 text-indigo-800 rounded font-medium border border-indigo-200">
                Entity: {trace.normalized_query.entities.join(', ')}
              </span>
            )}
            {trace.normalized_query.metrics.length > 0 && (
              <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded font-medium border border-emerald-200">
                Metric: {trace.normalized_query.metrics.join(', ')}
              </span>
            )}
            {trace.normalized_query.fiscal_years.length > 0 && (
              <span className="px-2 py-0.5 bg-amber-100 text-amber-800 rounded font-medium border border-amber-200">
                Period: {trace.normalized_query.fiscal_years.join(', ')}
              </span>
            )}
            {trace.normalized_query.topics.length > 0 && (
              <span className="px-2 py-0.5 bg-cyan-100 text-cyan-800 rounded font-medium border border-cyan-200">
                Topic: {trace.normalized_query.topics.join(', ')}
              </span>
            )}
            {trace.normalized_query.entities.length === 0 &&
              trace.normalized_query.metrics.length === 0 &&
              trace.normalized_query.fiscal_years.length === 0 &&
              trace.normalized_query.topics.length === 0 && (
                <span className="text-slate-400 italic">No domain entities detected; executing general semantic retrieval.</span>
              )}
          </div>
        )}

        {/* Filters Toolbar */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-3 pt-2">
          {/* Organization */}
          <div>
            <label className="block text-[11px] font-bold text-slate-600 uppercase tracking-wider mb-1">
              Organization Scope
            </label>
            <select
              value={selectedOrg}
              onChange={(e) => setSelectedOrg(e.target.value)}
              className="w-full text-xs py-1.5 px-2 bg-slate-50 border border-slate-300 rounded focus:ring-1 focus:ring-blue-500 focus:outline-none"
            >
              <option value="">All Authorized Units</option>
              {organizations.map((org) => (
                <option key={org.id} value={org.id}>
                  {org.code} - {org.name}
                </option>
              ))}
            </select>
          </div>

          {/* Fiscal Year */}
          <div>
            <label className="block text-[11px] font-bold text-slate-600 uppercase tracking-wider mb-1">
              Fiscal Year
            </label>
            <select
              value={selectedFY}
              onChange={(e) => setSelectedFY(e.target.value)}
              className="w-full text-xs py-1.5 px-2 bg-slate-50 border border-slate-300 rounded focus:ring-1 focus:ring-blue-500 focus:outline-none"
            >
              <option value="">All Periods</option>
              <option value="FY2025-26">FY2025-26</option>
              <option value="FY2024-25">FY2024-25</option>
              <option value="FY2023-24">FY2023-24</option>
              <option value="FY2022-23">FY2022-23</option>
              <option value="FY2021-22">FY2021-22</option>
            </select>
          </div>

          {/* Document Type */}
          <div>
            <label className="block text-[11px] font-bold text-slate-600 uppercase tracking-wider mb-1">
              Document Type
            </label>
            <select
              value={selectedDocType}
              onChange={(e) => setSelectedDocType(e.target.value)}
              className="w-full text-xs py-1.5 px-2 bg-slate-50 border border-slate-300 rounded focus:ring-1 focus:ring-blue-500 focus:outline-none"
            >
              <option value="">All Document Types</option>
              <option value="GEOLOGICAL_REPORT">Geological Report</option>
              <option value="PRODUCTION_SUMMARY">Production Summary</option>
              <option value="BOREHOLE_LOG">Borehole Log</option>
              <option value="STRIPPING_RETURN">Stripping Return</option>
              <option value="STATUTORY_FILING">Statutory Filing</option>
            </select>
          </div>

          {/* Source Tier */}
          <div>
            <label className="block text-[11px] font-bold text-slate-600 uppercase tracking-wider mb-1">
              Trust Tier
            </label>
            <select
              value={selectedTier}
              onChange={(e) => setSelectedTier(e.target.value)}
              className="w-full text-xs py-1.5 px-2 bg-slate-50 border border-slate-300 rounded focus:ring-1 focus:ring-blue-500 focus:outline-none"
            >
              <option value="">All Tiers</option>
              <option value="TIER_A">Tier A: Authoritative</option>
              <option value="TIER_B">Tier B: Operational</option>
              <option value="TIER_C">Tier C: Unverified</option>
            </select>
          </div>

          {/* Top-K Limit */}
          <div>
            <label className="block text-[11px] font-bold text-slate-600 uppercase tracking-wider mb-1">
              Max Results
            </label>
            <select
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              className="w-full text-xs py-1.5 px-2 bg-slate-50 border border-slate-300 rounded focus:ring-1 focus:ring-blue-500 focus:outline-none"
            >
              <option value={5}>Top 5</option>
              <option value={10}>Top 10</option>
              <option value={20}>Top 20</option>
              <option value={50}>Top 50</option>
            </select>
          </div>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3 text-red-800 text-sm">
          <Shield className="w-5 h-5 text-red-600 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Results Header */}
      {searched && (
        <div className="flex justify-between items-center px-1">
          <p className="text-xs font-bold text-slate-600 uppercase tracking-wider">
            {results.length} Evidence Candidate{results.length !== 1 ? 's' : ''} Retrieved
          </p>
          <span className="text-xs text-slate-500 font-mono">
            Mode: {searchMode} | Reranker: {trace?.reranker_status || 'N/A'}
          </span>
        </div>
      )}

      {/* Results List */}
      <div className="space-y-3">
        {results.map((item) => (
          <div
            key={item.result_id}
            className="bg-white p-5 rounded-lg border border-slate-200 shadow-sm hover:border-blue-300 transition-colors space-y-3"
          >
            {/* Result Header */}
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 border-b border-slate-100 pb-2.5">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="w-6 h-6 rounded-full bg-slate-800 text-white text-[11px] font-mono font-bold flex items-center justify-center">
                  #{item.final_rank}
                </span>
                <button
                  onClick={() => navigate(`/documents/${item.document_id}?page=${item.page_number}`)}
                  className="font-bold text-sm text-blue-700 hover:text-blue-900 hover:underline flex items-center gap-1 text-left"
                >
                  {item.title}
                  <ExternalLink className="w-3.5 h-3.5 inline text-slate-400" />
                </button>
              </div>

              <div className="flex items-center gap-2 flex-wrap text-xs">
                {getTierBadge(item.source_tier)}
                <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-medium border border-slate-200">
                  {item.organization_name || 'Organization'}
                </span>
                {item.fiscal_year && (
                  <span className="px-2 py-0.5 rounded bg-amber-50 text-amber-800 font-semibold border border-amber-200">
                    {item.fiscal_year}
                  </span>
                )}
                <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-800 font-bold border border-slate-200">
                  Page {item.page_number}
                </span>
                {item.chunk_type === 'TABLE' ? (
                  <span className="px-2 py-0.5 rounded bg-purple-100 text-purple-800 font-bold border border-purple-200 flex items-center gap-1">
                    <TableIcon className="w-3 h-3" />
                    Table Evidence
                  </span>
                ) : (
                  <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-medium">
                    Text Chunk
                  </span>
                )}
              </div>
            </div>

            {/* Content Snippet */}
            <div className="bg-slate-50 p-3.5 rounded border border-slate-200 font-mono text-xs text-slate-800 leading-relaxed whitespace-pre-wrap max-h-48 overflow-y-auto">
              {item.source_text}
            </div>

            {/* Score Breakdown & Actions Footer */}
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 pt-1">
              <div className="flex items-center gap-3 text-xs text-slate-600 flex-wrap">
                <span className="font-semibold text-slate-900">
                  RRF Score: <span className="font-mono text-blue-700 font-bold">{item.rrf_score}</span>
                </span>
                {item.dense_rank !== null && item.dense_rank !== undefined && (
                  <span className="px-1.5 py-0.5 bg-blue-50 border border-blue-200 rounded font-mono text-[11px] text-blue-800">
                    Dense Rank: #{item.dense_rank}
                  </span>
                )}
                {item.keyword_rank !== null && item.keyword_rank !== undefined && (
                  <span className="px-1.5 py-0.5 bg-emerald-50 border border-emerald-200 rounded font-mono text-[11px] text-emerald-800">
                    Keyword Rank: #{item.keyword_rank}
                  </span>
                )}
                {item.reranker_score !== null && item.reranker_score !== undefined ? (
                  <span className="px-1.5 py-0.5 bg-purple-50 border border-purple-200 rounded font-mono text-[11px] text-purple-800">
                    Reranker Score: {item.reranker_score}
                  </span>
                ) : (
                  <span className="px-1.5 py-0.5 bg-slate-100 rounded font-mono text-[11px] text-slate-500">
                    Reranker: Untouched
                  </span>
                )}
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setActiveProvenanceModal(item)}
                  className="px-3 py-1.5 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded border border-slate-300 flex items-center gap-1 transition-colors"
                >
                  <Layers className="w-3.5 h-3.5 text-slate-500" />
                  Inspect Provenance
                </button>
                <button
                  type="button"
                  onClick={() => navigate(`/documents/${item.document_id}?page=${item.page_number}`)}
                  className="px-3 py-1.5 text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 rounded shadow-sm flex items-center gap-1 transition-colors"
                >
                  Open in Document Viewer
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>
        ))}

        {searched && results.length === 0 && !loading && (
          <div className="bg-white p-12 text-center rounded-lg border border-slate-200 space-y-3">
            <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center mx-auto text-slate-400">
              <Search className="w-6 h-6" />
            </div>
            <h3 className="text-base font-bold text-slate-800">No Evidence Found</h3>
            <p className="text-xs text-slate-500 max-w-md mx-auto">
              No chunks satisfied your query and filters within your authorized organization scope.
              Try adjusting the filters or switching search modes.
            </p>
          </div>
        )}

        {!searched && !loading && (
          <div className="bg-white p-10 text-center rounded-lg border border-dashed border-slate-300 space-y-4">
            <div className="w-12 h-12 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center mx-auto">
              <Database className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-900">Knowledge Explorer Ready</h3>
              <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
                Search across all ingested geological reports, borehole stratigraphy logs, and multi-page production tables.
              </p>
            </div>
            <div className="flex flex-wrap justify-center gap-2 pt-2 text-xs">
              <span className="text-slate-400 font-semibold">Example Queries:</span>
              <button
                onClick={() => setQuery('BCCL geological survey Moonidih Block')}
                className="px-2 py-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 font-mono text-[11px]"
              >
                "BCCL geological survey Moonidih Block"
              </button>
              <button
                onClick={() => setQuery('monthly coal production FY2024-25')}
                className="px-2 py-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 font-mono text-[11px]"
              >
                "monthly coal production FY2024-25"
              </button>
              <button
                onClick={() => setQuery('borehole recovery log strata')}
                className="px-2 py-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 font-mono text-[11px]"
              >
                "borehole recovery log strata"
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Provenance Lineage Modal */}
      {activeProvenanceModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full p-6 space-y-4 border border-slate-200 animate-in fade-in zoom-in duration-150">
            <div className="flex justify-between items-center border-b border-slate-200 pb-3">
              <div className="flex items-center gap-2">
                <Layers className="w-5 h-5 text-blue-600" />
                <h3 className="font-bold text-base text-slate-900">Evidence Provenance Lineage</h3>
              </div>
              <button
                onClick={() => setActiveProvenanceModal(null)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded hover:bg-slate-100"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="p-3 bg-slate-50 rounded border border-slate-200 space-y-1.5 font-mono">
                <div className="text-slate-500">
                  <span className="font-bold text-slate-700">Document Title:</span> {activeProvenanceModal.title}
                </div>
                <div className="text-slate-500">
                  <span className="font-bold text-slate-700">Document ID:</span> {activeProvenanceModal.document_id}
                </div>
                <div className="text-slate-500">
                  <span className="font-bold text-slate-700">Physical Page:</span> Page {activeProvenanceModal.page_number}
                </div>
                <div className="text-slate-500">
                  <span className="font-bold text-slate-700">Chunk ID:</span> {activeProvenanceModal.chunk_id}
                </div>
                <div className="text-slate-500">
                  <span className="font-bold text-slate-700">Chunk Type:</span> {activeProvenanceModal.chunk_type}
                </div>
              </div>

              {activeProvenanceModal.provenance.table && (
                <div className="p-3 bg-purple-50 rounded border border-purple-200 space-y-1.5 font-mono text-purple-900">
                  <div className="font-bold text-purple-950 flex items-center gap-1.5 mb-1">
                    <TableIcon className="w-4 h-4 text-purple-700" />
                    Logical Table Continuation Lineage
                  </div>
                  <div>Logical Table ID: {activeProvenanceModal.provenance.table.logical_table_id || 'N/A'}</div>
                  <div>Part: Part {activeProvenanceModal.provenance.table.part_number} of {activeProvenanceModal.provenance.table.total_parts}</div>
                  <div>Spanned Pages: {activeProvenanceModal.provenance.table.pages_spanned?.join(', ')}</div>
                  <div>Caption: {activeProvenanceModal.provenance.table.caption || 'Table'}</div>
                  <div>Total Rows in Logical Group: {activeProvenanceModal.provenance.table.row_count}</div>
                  {activeProvenanceModal.provenance.table.headers && (
                    <div className="mt-1 pt-1 border-t border-purple-200">
                      <span className="font-bold">Master Headers:</span> {activeProvenanceModal.provenance.table.headers.join(' | ')}
                    </div>
                  )}
                </div>
              )}

              <div className="space-y-1">
                <span className="font-bold text-slate-700">Verbatim Extracted Content:</span>
                <div className="p-3 bg-slate-900 text-slate-100 rounded font-mono text-xs whitespace-pre-wrap max-h-48 overflow-y-auto">
                  {activeProvenanceModal.source_text}
                </div>
              </div>
            </div>

            <div className="flex justify-end pt-3 border-t border-slate-200">
              <button
                onClick={() => {
                  const docId = activeProvenanceModal.document_id;
                  const page = activeProvenanceModal.page_number;
                  setActiveProvenanceModal(null);
                  navigate(`/documents/${docId}?page=${page}`);
                }}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs rounded shadow-sm flex items-center gap-1.5"
              >
                Navigate to Source Page in Viewer
                <ExternalLink className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Retrieval Trace Modal */}
      {showTraceModal && trace && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full p-6 space-y-4 border border-slate-200 animate-in fade-in zoom-in duration-150">
            <div className="flex justify-between items-center border-b border-slate-200 pb-3">
              <div className="flex items-center gap-2">
                <Activity className="w-5 h-5 text-blue-600" />
                <h3 className="font-bold text-base text-slate-900">Retrieval Trace & Performance Telemetry</h3>
              </div>
              <button
                onClick={() => setShowTraceModal(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded hover:bg-slate-100"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4 text-xs">
              {/* Latency Pipeline Breakdown */}
              <div>
                <h4 className="font-bold text-slate-700 uppercase tracking-wider mb-2">
                  Execution Latency Breakdown (Total: {trace.timings_ms.total}ms)
                </h4>
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2">
                  <div className="p-2.5 bg-slate-50 border border-slate-200 rounded text-center">
                    <div className="text-[10px] text-slate-400 font-bold uppercase">Normalization</div>
                    <div className="text-sm font-mono font-bold text-slate-800 mt-1">{trace.timings_ms.query_normalization}ms</div>
                  </div>
                  <div className="p-2.5 bg-slate-50 border border-slate-200 rounded text-center">
                    <div className="text-[10px] text-slate-400 font-bold uppercase">FTS Keyword</div>
                    <div className="text-sm font-mono font-bold text-slate-800 mt-1">{trace.timings_ms.keyword_search}ms</div>
                  </div>
                  <div className="p-2.5 bg-slate-50 border border-slate-200 rounded text-center">
                    <div className="text-[10px] text-slate-400 font-bold uppercase">pgvector Dense</div>
                    <div className="text-sm font-mono font-bold text-slate-800 mt-1">{trace.timings_ms.dense_search}ms</div>
                  </div>
                  <div className="p-2.5 bg-slate-50 border border-slate-200 rounded text-center">
                    <div className="text-[10px] text-slate-400 font-bold uppercase">RRF Fusion</div>
                    <div className="text-sm font-mono font-bold text-slate-800 mt-1">{trace.timings_ms.rrf_fusion}ms</div>
                  </div>
                  <div className="p-2.5 bg-slate-50 border border-slate-200 rounded text-center">
                    <div className="text-[10px] text-slate-400 font-bold uppercase">Reranker</div>
                    <div className="text-sm font-mono font-bold text-slate-800 mt-1">{trace.timings_ms.reranking}ms</div>
                  </div>
                  <div className="p-2.5 bg-blue-50 border border-blue-200 rounded text-center">
                    <div className="text-[10px] text-blue-600 font-bold uppercase">Total E2E</div>
                    <div className="text-sm font-mono font-bold text-blue-900 mt-1">{trace.timings_ms.total}ms</div>
                  </div>
                </div>
              </div>

              {/* Candidate Counts */}
              <div className="p-3 bg-slate-50 rounded border border-slate-200 grid grid-cols-4 gap-2 text-center font-mono">
                <div>
                  <div className="text-[10px] text-slate-500">Keyword Candidates</div>
                  <div className="font-bold text-sm text-slate-800">{trace.keyword_candidate_count}</div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-500">Dense Candidates</div>
                  <div className="font-bold text-sm text-slate-800">{trace.dense_candidate_count}</div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-500">Fused Candidates</div>
                  <div className="font-bold text-sm text-slate-800">{trace.fused_candidate_count}</div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-500">Final Top-K</div>
                  <div className="font-bold text-sm text-blue-700">{trace.final_result_count}</div>
                </div>
              </div>

              {/* Normalized Query Structure */}
              <div className="space-y-1">
                <span className="font-bold text-slate-700">Normalized Query JSON Representation:</span>
                <pre className="p-3 bg-slate-900 text-slate-100 rounded font-mono text-xs overflow-x-auto">
                  {JSON.stringify(trace.normalized_query, null, 2)}
                </pre>
              </div>
            </div>

            <div className="flex justify-end pt-3 border-t border-slate-200">
              <button
                onClick={() => setShowTraceModal(false)}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-xs rounded"
              >
                Close Trace
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
