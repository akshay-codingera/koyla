import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { apiClient } from '../api/client';
import {
  Layers,
  Search,
  Filter,
  RefreshCw,
  TrendingUp,
  TrendingDown,
  Minus,
  Calendar,
  Building2,
  FileText,
  Clock,
  Sparkles,
  ExternalLink,
  ChevronRight,
  Database,
  ArrowRight,
  BarChart3,
  AlertTriangle,
  CheckCircle2,
  FileSpreadsheet,
  X,
  History,
  Tag,
  Hash,
  Eye,
  Info,
  SlidersHorizontal,
  ChevronDown,
  FileCheck2,
  HelpCircle,
  FolderOpen
} from 'lucide-react';

interface TopicItem {
  id: string;
  analysis_id: string;
  topic_index: number;
  label: string;
  document_count: number;
  chunk_count: number;
  prevalence_pct: number;
  semantic_topic_coherence?: number;
  top_terms: Array<{
    term: string;
    weight: number;
    rank: number;
    frequency?: number;
    document_count?: number;
  }>;
  metadata?: any;
}

interface TrendSeriesPoint {
  id?: string;
  period_value: string;
  document_count: number;
  corpus_document_count: number;
  document_share_pct: number;
  chunk_count: number;
  corpus_chunk_count: number;
  chunk_share_pct: number;
  absolute_change: number | null;
  percentage_point_change: number | null;
  growth_rate_pct: number | null;
  trend_status: string;
}

interface TopicTrendItem {
  topic_id: string;
  label: string;
  first_seen: string | null;
  last_seen: string | null;
  observed_periods: number;
  total_periods: number;
  persistence_status: string;
  series: TrendSeriesPoint[];
}

interface EvidenceCard {
  evidence_id: string;
  chunk_id: string;
  document_id: string;
  document_title: string;
  document_type: string;
  organization_code: string | null;
  page_number: number;
  section_heading?: string;
  content: string;
  representative_score: number;
  mine_name?: string;
  block_name?: string;
  fiscal_year?: string;
}

interface AnalysisMetadata {
  id: string;
  organization_id: string;
  organization_code?: string;
  organization_name?: string;
  corpus_filters: Record<string, any>;
  corpus_hash: string;
  embedding_model: string;
  analysis_method: string;
  status: string;
  progress_pct: number;
  runtime_seconds: number;
  document_count: number;
  chunk_count: number;
  topic_count: number;
  outlier_count: number;
  quality_metrics?: Record<string, any>;
  created_at: string;
  completed_at?: string;
  error_message?: string;
}

export const TopicIntelligence: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  // Active Analysis State
  const [activeAnalysisId, setActiveAnalysisId] = useState<string | null>(searchParams.get('id'));
  const [analysisMeta, setAnalysisMeta] = useState<AnalysisMetadata | null>(null);
  const [topics, setTopics] = useState<TopicItem[]>([]);
  const [trends, setTrends] = useState<TopicTrendItem[]>([]);
  const [periods, setPeriods] = useState<string[]>([]);
  const [selectedTopicId, setSelectedTopicId] = useState<string | null>(null);
  
  // Loading & Error States
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [insufficientCorpus, setInsufficientCorpus] = useState<any | null>(null);

  // Filter Bar State
  const [filterOrg, setFilterOrg] = useState<string>('');
  const [filterMine, setFilterMine] = useState<string>('');
  const [filterBlock, setFilterBlock] = useState<string>('');
  const [filterDocType, setFilterDocType] = useState<string>('');
  const [filterFy, setFilterFy] = useState<string>('');
  const [activeTab, setActiveTab] = useState<'register' | 'wordcloud' | 'trends' | 'yoy' | 'comparison' | 'detail' | 'evolution'>('register');

  // Word Cloud Mode
  const [cloudMode, setCloudMode] = useState<'ALL' | 'SELECTED_TOPIC' | 'SELECTED_YEAR'>('ALL');
  const [cloudSelectedYear, setCloudSelectedYear] = useState<string>('');

  // YoY Comparison Controls
  const [yoyPeriodA, setYoyPeriodA] = useState<string>('');
  const [yoyPeriodB, setYoyPeriodB] = useState<string>('');
  const [yoyComparisons, setYoyComparisons] = useState<any[]>([]);
  const [yoyLoading, setYoyLoading] = useState<boolean>(false);

  // Multi-Dimensional Comparison State
  const [compDimension, setCompDimension] = useState<'ORGANIZATION' | 'MINE' | 'BLOCK' | 'DOCUMENT_TYPE'>('ORGANIZATION');
  const [compDimA, setCompDimA] = useState<string>('');
  const [compDimB, setCompDimB] = useState<string>('');
  const [compResult, setCompResult] = useState<any | null>(null);
  const [compLoading, setCompLoading] = useState<boolean>(false);

  // Topic Detail & Evidence
  const [selectedTopicDetail, setSelectedTopicDetail] = useState<any | null>(null);
  const [evidenceCards, setEvidenceCards] = useState<EvidenceCard[]>([]);
  const [evidenceLoading, setEvidenceLoading] = useState<boolean>(false);

  // Term Evolution State
  const [termEvolution, setTermEvolution] = useState<any | null>(null);

  // History Drawer State
  const [historyOpen, setHistoryOpen] = useState<boolean>(false);
  const [historyItems, setHistoryItems] = useState<any[]>([]);
  const [historyLoading, setHistoryLoading] = useState<boolean>(false);

  // Local AI Summary State
  const [summaryData, setSummaryData] = useState<{ summary: string; factual_points: string[]; source: string; model: string } | null>(null);
  const [summaryLoading, setSummaryLoading] = useState<boolean>(false);

  // Add to Report Modal State
  const [reportModalOpen, setReportModalOpen] = useState<boolean>(false);
  const [availableReports, setAvailableReports] = useState<any[]>([]);
  const [targetReportId, setTargetReportId] = useState<string>('');
  const [attachTrends, setAttachTrends] = useState<boolean>(true);
  const [attachEvidence, setAttachEvidence] = useState<boolean>(true);
  const [attachLoading, setAttachLoading] = useState<boolean>(false);
  const [attachSuccess, setAttachSuccess] = useState<string | null>(null);

  // Search & Filter in Table
  const [tableSearch, setTableSearch] = useState<string>('');

  // 1. Initial Load: Load specified or latest completed analysis
  useEffect(() => {
    fetchAnalysisHistory(true);
  }, []);

  const fetchAnalysisHistory = async (autoLoadLatest: boolean = false) => {
    setHistoryLoading(true);
    try {
      const resp = await apiClient.get('/topics?limit=30');
      const items = resp.data?.items || [];
      setHistoryItems(items);

      if (autoLoadLatest && items.length > 0) {
        const targetId = activeAnalysisId || items[0].id;
        loadAnalysis(targetId);
      }
    } catch (err: any) {
      console.error('Failed to load analysis history:', err);
    } finally {
      setHistoryLoading(false);
    }
  };

  const loadAnalysis = async (id: string) => {
    setLoading(true);
    setError(null);
    setInsufficientCorpus(null);
    setSelectedTopicId(null);
    setSelectedTopicDetail(null);
    setEvidenceCards([]);
    setTermEvolution(null);
    setSummaryData(null);
    setActiveAnalysisId(id);
    setSearchParams({ id });

    try {
      // 1. Fetch Metadata
      const metaResp = await apiClient.get(`/topics/${id}`);
      const meta = metaResp.data;
      setAnalysisMeta(meta);

      if (meta.status === 'INSUFFICIENT_CORPUS') {
        setInsufficientCorpus(meta);
        setLoading(false);
        return;
      }

      // 2. Fetch Topics
      const topicsResp = await apiClient.get(`/topics/${id}/topics`);
      const topicsData = topicsResp.data?.topics || [];
      setTopics(topicsData);

      if (topicsData.length > 0) {
        setSelectedTopicId(topicsData[0].id);
      }

      // 3. Fetch Trends
      const trendsResp = await apiClient.get(`/topics/${id}/trends`);
      const trendsData = trendsResp.data?.trends || [];
      const periodsData = trendsResp.data?.periods || [];
      setTrends(trendsData);
      setPeriods(periodsData);

      if (periodsData.length >= 2) {
        setYoyPeriodA(periodsData[0]);
        setYoyPeriodB(periodsData[periodsData.length - 1]);
      } else if (periodsData.length === 1) {
        setYoyPeriodA(periodsData[0]);
        setYoyPeriodB(periodsData[0]);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load topic analysis.');
    } finally {
      setLoading(false);
    }
  };

  // 2. When selected topic changes, load topic detail, evidence, and term evolution
  useEffect(() => {
    if (!activeAnalysisId || !selectedTopicId) return;
    loadTopicDetail(activeAnalysisId, selectedTopicId);
  }, [activeAnalysisId, selectedTopicId]);

  const loadTopicDetail = async (analysisId: string, topicId: string) => {
    setEvidenceLoading(true);
    try {
      const [detailResp, evidenceResp, evolResp] = await Promise.all([
        apiClient.get(`/topics/${analysisId}/topics/${topicId}`),
        apiClient.get(`/topics/${analysisId}/topics/${topicId}/evidence?limit=15`),
        apiClient.get(`/topics/${analysisId}/term-evolution?topic_id=${topicId}`)
      ]);
      setSelectedTopicDetail(detailResp.data);
      setEvidenceCards(evidenceResp.data?.items || []);
      setTermEvolution(evolResp.data);
    } catch (err) {
      console.error('Failed to load topic details:', err);
    } finally {
      setEvidenceLoading(false);
    }
  };

  // 3. Load YoY Comparisons
  useEffect(() => {
    if (!activeAnalysisId || !yoyPeriodA || !yoyPeriodB) return;
    fetchYoyComparison();
  }, [activeAnalysisId, yoyPeriodA, yoyPeriodB]);

  const fetchYoyComparison = async () => {
    if (!activeAnalysisId || !yoyPeriodA || !yoyPeriodB) return;
    setYoyLoading(true);
    try {
      const resp = await apiClient.get(`/topics/${activeAnalysisId}/comparison`, {
        params: { period_a: yoyPeriodA, period_b: yoyPeriodB }
      });
      setYoyComparisons(resp.data?.comparisons || []);
    } catch (err) {
      console.error('Failed to compare periods:', err);
    } finally {
      setYoyLoading(false);
    }
  };

  // 4. Load Multi-Dimensional Comparison
  useEffect(() => {
    if (!activeAnalysisId) return;
    fetchDimensionComparison();
  }, [activeAnalysisId, compDimension, compDimA, compDimB]);

  const fetchDimensionComparison = async () => {
    if (!activeAnalysisId) return;
    setCompLoading(true);
    try {
      const endpoint = compDimension === 'ORGANIZATION'
        ? `/topics/${activeAnalysisId}/comparison/organizations`
        : compDimension === 'MINE'
        ? `/topics/${activeAnalysisId}/comparison/mines`
        : compDimension === 'BLOCK'
        ? `/topics/${activeAnalysisId}/comparison/blocks`
        : `/topics/${activeAnalysisId}/comparison/document-types`;

      const params: any = {};
      if (compDimension === 'ORGANIZATION' && compDimA && compDimB) {
        params.org_a = compDimA;
        params.org_b = compDimB;
      } else if (compDimension === 'MINE' && compDimA && compDimB) {
        params.mine_a = compDimA;
        params.mine_b = compDimB;
      } else if (compDimension === 'BLOCK' && compDimA && compDimB) {
        params.block_a = compDimA;
        params.block_b = compDimB;
      } else if (compDimension === 'DOCUMENT_TYPE' && compDimA && compDimB) {
        params.doc_type_a = compDimA;
        params.doc_type_b = compDimB;
      }

      const resp = await apiClient.get(endpoint, { params });
      setCompResult(resp.data);
    } catch (err) {
      console.error('Failed to load dimension comparison:', err);
    } finally {
      setCompLoading(false);
    }
  };

  // 5. Run New Scoped Discovery
  const handleRunAnalysis = async () => {
    setLoading(true);
    setError(null);
    try {
      const payload: any = {
        corpus_filters: {},
        embedding_model: 'BAAI/bge-small-en-v1.5',
        analysis_method: 'AUTO',
      };
      if (filterOrg) payload.organization_id = filterOrg;
      if (filterMine) payload.corpus_filters.mine_name = filterMine;
      if (filterBlock) payload.corpus_filters.block_name = filterBlock;
      if (filterDocType) payload.corpus_filters.document_type = filterDocType;
      if (filterFy) payload.corpus_filters.fiscal_year = filterFy;

      const resp = await apiClient.post('/topics/analyze', payload);
      const newAnalysisId = resp.data?.id;
      if (newAnalysisId) {
        await fetchAnalysisHistory(false);
        await loadAnalysis(newAnalysisId);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Discovery execution failed.');
    } finally {
      setLoading(false);
    }
  };

  // 6. Local AI Summary
  const handleGenerateSummary = async () => {
    if (!activeAnalysisId) return;
    setSummaryLoading(true);
    try {
      const resp = await apiClient.post(`/topics/${activeAnalysisId}/summary`, {
        topic_id: selectedTopicId || undefined
      });
      setSummaryData(resp.data);
    } catch (err) {
      console.error('Failed to generate summary:', err);
    } finally {
      setSummaryLoading(false);
    }
  };

  // 7. Attach to Report
  const openReportModal = async () => {
    setReportModalOpen(true);
    setAttachSuccess(null);
    try {
      const resp = await apiClient.get('/reports');
      setAvailableReports(resp.data || []);
      if (resp.data && resp.data.length > 0) {
        setTargetReportId(resp.data[0].id);
      }
    } catch (err) {
      console.error('Failed to fetch reports:', err);
    }
  };

  const handleAttachToReport = async () => {
    if (!activeAnalysisId || !targetReportId) return;
    setAttachLoading(true);
    setAttachSuccess(null);
    try {
      const resp = await apiClient.post(`/topics/${activeAnalysisId}/add-to-report`, {
        report_id: targetReportId,
        topic_id: selectedTopicId || undefined,
        include_trends: attachTrends,
        include_evidence: attachEvidence,
      });
      setAttachSuccess(resp.data?.message || 'Topic analysis attached as optional analytical annexure.');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to attach analysis to report.');
    } finally {
      setAttachLoading(false);
    }
  };

  // Filtered Topics for Register Table
  const filteredTopics = useMemo(() => {
    if (!tableSearch) return topics;
    const q = tableSearch.toLowerCase();
    return topics.filter(t => 
      t.label.toLowerCase().includes(q) || 
      t.top_terms.some(tm => tm.term.toLowerCase().includes(q))
    );
  }, [topics, tableSearch]);

  // Combined terms for Word Cloud
  const wordCloudTerms = useMemo(() => {
    if (cloudMode === 'SELECTED_TOPIC' && selectedTopicDetail) {
      return (selectedTopicDetail.terms || []).map((t: any) => ({
        ...t,
        topic_label: selectedTopicDetail.label,
      }));
    }

    const termMap: Record<string, { term: string; weight: number; frequency: number; document_count: number; topic_label: string }> = {};
    for (const t of topics) {
      for (const tm of t.top_terms) {
        if (!termMap[tm.term] || termMap[tm.term].weight < tm.weight) {
          termMap[tm.term] = {
            term: tm.term,
            weight: tm.weight,
            frequency: tm.frequency || 1,
            document_count: tm.document_count || 1,
            topic_label: t.label,
          };
        }
      }
    }
    return Object.values(termMap).sort((a, b) => b.weight - a.weight);
  }, [topics, cloudMode, selectedTopicDetail]);

  const maxWeight = useMemo(() => {
    return Math.max(...wordCloudTerms.map(t => t.weight), 0.01);
  }, [wordCloudTerms]);

  const minWeight = useMemo(() => {
    return Math.min(...wordCloudTerms.map(t => t.weight), 0.0001);
  }, [wordCloudTerms]);

  const getTrendBadge = (status: string) => {
    switch (status) {
      case 'GROWING':
        return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-950/80 text-emerald-400 border border-emerald-700/60"><TrendingUp className="w-3 h-3"/> GROWING</span>;
      case 'DECLINING':
        return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-rose-950/80 text-rose-400 border border-rose-700/60"><TrendingDown className="w-3 h-3"/> DECLINING</span>;
      case 'EMERGING':
        return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-cyan-950/80 text-cyan-400 border border-cyan-700/60"><Sparkles className="w-3 h-3"/> EMERGING</span>;
      case 'DISAPPEARING':
        return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-zinc-900 text-zinc-400 border border-zinc-700"><Minus className="w-3 h-3"/> DISAPPEARING</span>;
      case 'RECURRING':
        return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-950/80 text-amber-400 border border-amber-700/60"><RefreshCw className="w-3 h-3"/> RECURRING</span>;
      case 'STABLE':
        return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-900 text-slate-300 border border-slate-700"><Minus className="w-3 h-3"/> STABLE</span>;
      default:
        return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono text-zinc-500 bg-zinc-900/60 border border-zinc-800">INSUFFICIENT HISTORY</span>;
    }
  };

  const getPersistenceBadge = (status: string) => {
    switch (status) {
      case 'PERSISTENT':
        return <span className="px-1.5 py-0.5 rounded text-[9px] font-mono font-bold bg-blue-950/70 text-blue-300 border border-blue-800/60">PERSISTENT</span>;
      case 'INTERMITTENT':
        return <span className="px-1.5 py-0.5 rounded text-[9px] font-mono font-bold bg-purple-950/70 text-purple-300 border border-purple-800/60">INTERMITTENT</span>;
      case 'NEW':
        return <span className="px-1.5 py-0.5 rounded text-[9px] font-mono font-bold bg-emerald-950/70 text-emerald-300 border border-emerald-800/60">NEW</span>;
      case 'DISAPPEARED':
        return <span className="px-1.5 py-0.5 rounded text-[9px] font-mono font-bold bg-zinc-900 text-zinc-400 border border-zinc-800">DISAPPEARED</span>;
      default:
        return <span className="px-1.5 py-0.5 rounded text-[9px] font-mono text-zinc-500 border border-zinc-800">UNTRACKED</span>;
    }
  };

  return (
    <div className="min-h-screen bg-[#0c0e12] text-[#e2e8f0] pb-24 font-sans selection:bg-[#1e3450] selection:text-[#60a5fa]">
      {/* 1. Header Control Room Bar */}
      <div className="bg-[#12151b] border-b border-[#242c38] px-6 py-3.5 sticky top-0 z-30 shadow-md">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded bg-[#16273d] border border-[#2b4c73] flex items-center justify-center text-[#60a5fa] shadow-inner font-mono font-black text-sm">
              <Layers className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2.5">
                <h1 className="font-mono text-base font-black tracking-wider text-[#f1f5f9] uppercase">
                  TOPIC INTELLIGENCE CONTROL ROOM
                </h1>
                <span className="text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 bg-[#1a212b] border border-[#2d3748] rounded text-[#38bdf8]">
                  CIL / CMPDI ANALYTICS
                </span>
                {analysisMeta?.id && (
                  <span className="text-[10px] font-mono text-zinc-400 px-2 py-0.5 bg-[#161a22] border border-[#222834] rounded">
                    Analysis: {analysisMeta.id.slice(0, 8)}...
                  </span>
                )}
              </div>
              <p className="text-[11px] text-[#64748b] font-mono mt-0.5">
                Multi-Period Corpus Synthesis · Single Global Model Alignment · Grounded Provenance
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => setHistoryOpen(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-[#161c24] hover:bg-[#1f2834] border border-[#2d3748] rounded text-xs font-mono text-[#cbd5e1] transition-colors"
            >
              <History className="w-3.5 h-3.5 text-[#38bdf8]" />
              Analysis History ({historyItems.length})
            </button>

            <button
              onClick={handleGenerateSummary}
              disabled={summaryLoading || !activeAnalysisId}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-[#16273d] hover:bg-[#1e3450] border border-[#2b4c73] rounded text-xs font-mono text-[#93c5fd] font-bold transition-colors disabled:opacity-50"
            >
              <Sparkles className={`w-3.5 h-3.5 ${summaryLoading ? 'animate-spin' : ''}`} />
              Factual AI Summary
            </button>

            <button
              onClick={openReportModal}
              disabled={!activeAnalysisId}
              className="flex items-center gap-1.5 px-3.5 py-1.5 bg-[#0f766e] hover:bg-[#115e59] border border-[#14b8a6]/40 rounded text-xs font-mono text-white font-bold transition-colors disabled:opacity-50 shadow-sm"
            >
              <FileSpreadsheet className="w-3.5 h-3.5" />
              Add Analysis to Report
            </button>
          </div>
        </div>

        {/* Technical Analysis Metadata Banner */}
        {analysisMeta?.status === 'COMPLETED' && (
          <div className="mt-3 pt-2.5 border-t border-[#1e2530] grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3 text-[11px] font-mono text-[#94a3b8]">
            <div className="flex flex-col">
              <span className="text-[#64748b] text-[9px] uppercase tracking-wider">Organization</span>
              <span className="text-[#e2e8f0] font-bold">{analysisMeta.organization_code || 'ALL SCOPES'}</span>
            </div>
            <div className="flex flex-col">
              <span className="text-[#64748b] text-[9px] uppercase tracking-wider">Analyzed Corpus</span>
              <span className="text-[#e2e8f0] font-bold">{analysisMeta.document_count ?? 0} Docs · {analysisMeta.chunk_count ?? 0} Chunks</span>
            </div>
            <div className="flex flex-col">
              <span className="text-[#64748b] text-[9px] uppercase tracking-wider">Topics / Outliers</span>
              <span className="text-[#e2e8f0] font-bold">{topics.length} Discovered · {analysisMeta.outlier_count ?? 0} Outliers</span>
            </div>
            <div className="flex flex-col">
              <span className="text-[#64748b] text-[9px] uppercase tracking-wider">Embedding Model</span>
              <span className="text-[#38bdf8] truncate font-bold">{analysisMeta.embedding_model || '—'}</span>
            </div>
            <div className="flex flex-col">
              <span className="text-[#64748b] text-[9px] uppercase tracking-wider">Algorithm</span>
              <span className="text-[#e2e8f0]">{analysisMeta.analysis_method || '—'}</span>
            </div>
            <div className="flex flex-col">
              <span className="text-[#64748b] text-[9px] uppercase tracking-wider">Runtime</span>
              <span className="text-[#e2e8f0]">{analysisMeta.runtime_seconds != null ? `${analysisMeta.runtime_seconds.toFixed(2)}s` : '—'}</span>
            </div>
            <div className="flex flex-col">
              <span className="text-[#64748b] text-[9px] uppercase tracking-wider">Corpus Hash</span>
              <span className="text-[#cbd5e1] font-mono truncate" title={analysisMeta.corpus_hash}>
                {analysisMeta.corpus_hash ? `${analysisMeta.corpus_hash.slice(0, 10)}...` : '—'}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* 2. Collapsible Filter & Analysis Bar */}
      <div className="max-w-7xl mx-auto px-6 mt-4">
        <div className="bg-[#12151b] border border-[#242c38] rounded p-3.5 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3 pb-2 border-b border-[#1e2530]">
            <div className="flex items-center gap-2 text-xs font-mono font-bold text-[#e2e8f0]">
              <SlidersHorizontal className="w-3.5 h-3.5 text-[#38bdf8]" />
              CORPUS SCOPING & DISCOVERY FILTERS
            </div>
            <span className="text-[10px] font-mono text-[#64748b]">
              Applies to new discovery runs · Does not auto-trigger expensive jobs
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 mt-3">
            <div>
              <label className="block text-[10px] font-mono uppercase text-[#64748b] mb-1">Organization</label>
              <input
                type="text"
                value={filterOrg}
                onChange={(e) => setFilterOrg(e.target.value)}
                placeholder="e.g. ECL, BCCL"
                className="w-full bg-[#161a22] border border-[#2d3748] rounded px-2.5 py-1.5 text-xs font-mono text-[#f1f5f9] focus:outline-none focus:border-[#3b82f6]"
              />
            </div>

            <div>
              <label className="block text-[10px] font-mono uppercase text-[#64748b] mb-1">Fiscal Year</label>
              <input
                type="text"
                value={filterFy}
                onChange={(e) => setFilterFy(e.target.value)}
                placeholder="e.g. FY2024-25"
                className="w-full bg-[#161a22] border border-[#2d3748] rounded px-2.5 py-1.5 text-xs font-mono text-[#f1f5f9] focus:outline-none focus:border-[#3b82f6]"
              />
            </div>

            <div>
              <label className="block text-[10px] font-mono uppercase text-[#64748b] mb-1">Mine Name</label>
              <input
                type="text"
                value={filterMine}
                onChange={(e) => setFilterMine(e.target.value)}
                placeholder="e.g. Rajmahal OCP"
                className="w-full bg-[#161a22] border border-[#2d3748] rounded px-2.5 py-1.5 text-xs font-mono text-[#f1f5f9] focus:outline-none focus:border-[#3b82f6]"
              />
            </div>

            <div>
              <label className="block text-[10px] font-mono uppercase text-[#64748b] mb-1">Block Name</label>
              <input
                type="text"
                value={filterBlock}
                onChange={(e) => setFilterBlock(e.target.value)}
                placeholder="e.g. Simlong Block"
                className="w-full bg-[#161a22] border border-[#2d3748] rounded px-2.5 py-1.5 text-xs font-mono text-[#f1f5f9] focus:outline-none focus:border-[#3b82f6]"
              />
            </div>

            <div>
              <label className="block text-[10px] font-mono uppercase text-[#64748b] mb-1">Document Type</label>
              <select
                value={filterDocType}
                onChange={(e) => setFilterDocType(e.target.value)}
                className="w-full bg-[#161a22] border border-[#2d3748] rounded px-2.5 py-1.5 text-xs font-mono text-[#f1f5f9] focus:outline-none focus:border-[#3b82f6]"
              >
                <option value="">ALL TYPES</option>
                <option value="MINING_PLAN">MINING_PLAN</option>
                <option value="GEOLOGICAL_REPORT">GEOLOGICAL_REPORT</option>
                <option value="CLOSURE_PLAN">CLOSURE_PLAN</option>
                <option value="EXPLORATION_REPORT">EXPLORATION_REPORT</option>
                <option value="ENVIRONMENTAL_REPORT">ENVIRONMENTAL_REPORT</option>
              </select>
            </div>
          </div>

          <div className="flex justify-end gap-2 mt-3 pt-2.5 border-t border-[#1e2530]">
            <button
              onClick={() => {
                setFilterOrg('');
                setFilterMine('');
                setFilterBlock('');
                setFilterDocType('');
                setFilterFy('');
              }}
              className="px-3 py-1 bg-[#181d24] hover:bg-[#202732] border border-[#2d3748] rounded text-xs font-mono text-[#94a3b8]"
            >
              Reset Filters
            </button>

            <button
              onClick={handleRunAnalysis}
              disabled={loading}
              className="flex items-center gap-1.5 px-4 py-1 bg-[#1e3450] hover:bg-[#264366] border border-[#3b82f6] rounded text-xs font-mono text-white font-bold transition-all disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              Run New Discovery
            </button>
          </div>
        </div>
      </div>

      {/* 3. Refusal / Insufficient Corpus Alert */}
      {insufficientCorpus && (
        <div className="max-w-7xl mx-auto px-6 mt-4">
          <div className="bg-[#1f1619] border-l-4 border-[#f43f5e] p-5 rounded-r border-y border-r border-[#4c1d24] shadow-sm">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-[#f43f5e] shrink-0 mt-0.5" />
              <div>
                <h3 className="font-mono text-sm font-bold text-[#fecdd3] uppercase">
                  INSUFFICIENT CORPUS FOR TOPIC MODELING
                </h3>
                <p className="text-xs text-[#fda4af] font-mono mt-1">
                  {insufficientCorpus.message || 'Corpus size is below mathematical modeling safety thresholds.'}
                </p>
                <div className="mt-3 flex items-center gap-6 text-xs font-mono text-[#cbd5e1]">
                  <div>
                    <span className="text-[#94a3b8]">Observed Documents: </span>
                    <span className="font-bold text-white">{insufficientCorpus.document_count}</span>
                  </div>
                  <div>
                    <span className="text-[#94a3b8]">Observed Chunks: </span>
                    <span className="font-bold text-white">{insufficientCorpus.chunk_count}</span>
                  </div>
                  <div>
                    <span className="text-[#94a3b8]">Required Minimum: </span>
                    <span className="font-bold text-[#38bdf8]">
                      {insufficientCorpus.minimum_threshold?.documents || 2} Docs · {insufficientCorpus.minimum_threshold?.chunks || 3} Chunks
                    </span>
                  </div>
                </div>
                <p className="text-[11px] text-[#f43f5e]/80 font-mono mt-2 italic">
                  Deterministic Refusal Applied: Zero artificial or manufactured topics were generated.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 4. Local AI Summary Alert */}
      {summaryData && (
        <div className="max-w-7xl mx-auto px-6 mt-4">
          <div className="bg-[#121d28] border border-[#1e3a5f] rounded p-4 shadow-sm">
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-start gap-3">
                <Sparkles className="w-5 h-5 text-[#38bdf8] shrink-0 mt-0.5" />
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-mono text-xs font-bold text-[#93c5fd] uppercase tracking-wider">
                      EMPIRICAL SYNTHESIS SUMMARY ({summaryData.source})
                    </h3>
                    <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-[#16273d] text-[#60a5fa] border border-[#2b4c73]">
                      Model: {summaryData.model}
                    </span>
                  </div>
                  <p className="text-xs text-[#e2e8f0] font-sans mt-2 leading-relaxed">
                    {summaryData.summary}
                  </p>
                  <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-2 text-[11px] font-mono text-[#94a3b8]">
                    {summaryData.factual_points?.map((pt, idx) => (
                      <div key={idx} className="flex items-start gap-1.5">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                        <span>{pt}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
              <button
                onClick={() => setSummaryData(null)}
                className="text-zinc-500 hover:text-zinc-300"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 5. Main Navigation Tabs */}
      {!insufficientCorpus && analysisMeta && (
        <div className="max-w-7xl mx-auto px-6 mt-6">
          <div className="flex border-b border-[#242c38] overflow-x-auto gap-1">
            <button
              onClick={() => setActiveTab('register')}
              className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-mono font-bold tracking-tight border-b-2 transition-all whitespace-nowrap ${
                activeTab === 'register'
                  ? 'border-[#3b82f6] text-[#93c5fd] bg-[#16202c]'
                  : 'border-transparent text-[#94a3b8] hover:text-white hover:bg-[#141820]'
              }`}
            >
              <Database className="w-3.5 h-3.5" />
              TOPIC REGISTER ({topics.length})
            </button>

            <button
              onClick={() => setActiveTab('wordcloud')}
              className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-mono font-bold tracking-tight border-b-2 transition-all whitespace-nowrap ${
                activeTab === 'wordcloud'
                  ? 'border-[#3b82f6] text-[#93c5fd] bg-[#16202c]'
                  : 'border-transparent text-[#94a3b8] hover:text-white hover:bg-[#141820]'
              }`}
            >
              <Tag className="w-3.5 h-3.5" />
              WORD CLOUD & VOCABULARY
            </button>

            <button
              onClick={() => setActiveTab('trends')}
              className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-mono font-bold tracking-tight border-b-2 transition-all whitespace-nowrap ${
                activeTab === 'trends'
                  ? 'border-[#3b82f6] text-[#93c5fd] bg-[#16202c]'
                  : 'border-transparent text-[#94a3b8] hover:text-white hover:bg-[#141820]'
              }`}
            >
              <BarChart3 className="w-3.5 h-3.5" />
              TEMPORAL TRENDS ({periods.length} PERIODS)
            </button>

            <button
              onClick={() => setActiveTab('yoy')}
              className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-mono font-bold tracking-tight border-b-2 transition-all whitespace-nowrap ${
                activeTab === 'yoy'
                  ? 'border-[#3b82f6] text-[#93c5fd] bg-[#16202c]'
                  : 'border-transparent text-[#94a3b8] hover:text-white hover:bg-[#141820]'
              }`}
            >
              <ArrowRight className="w-3.5 h-3.5" />
              YEAR-TO-YEAR SHIFT
            </button>

            <button
              onClick={() => setActiveTab('comparison')}
              className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-mono font-bold tracking-tight border-b-2 transition-all whitespace-nowrap ${
                activeTab === 'comparison'
                  ? 'border-[#3b82f6] text-[#93c5fd] bg-[#16202c]'
                  : 'border-transparent text-[#94a3b8] hover:text-white hover:bg-[#141820]'
              }`}
            >
              <Building2 className="w-3.5 h-3.5" />
              COMPARISON WORKBENCH
            </button>

            <button
              onClick={() => setActiveTab('detail')}
              className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-mono font-bold tracking-tight border-b-2 transition-all whitespace-nowrap ${
                activeTab === 'detail'
                  ? 'border-[#3b82f6] text-[#93c5fd] bg-[#16202c]'
                  : 'border-transparent text-[#94a3b8] hover:text-white hover:bg-[#141820]'
              }`}
            >
              <Eye className="w-3.5 h-3.5" />
              TOPIC DETAIL & EVIDENCE
            </button>

            <button
              onClick={() => setActiveTab('evolution')}
              className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-mono font-bold tracking-tight border-b-2 transition-all whitespace-nowrap ${
                activeTab === 'evolution'
                  ? 'border-[#3b82f6] text-[#93c5fd] bg-[#16202c]'
                  : 'border-transparent text-[#94a3b8] hover:text-white hover:bg-[#141820]'
              }`}
            >
              <Clock className="w-3.5 h-3.5" />
              TERM EVOLUTION
            </button>
          </div>
        </div>
      )}

      {/* 6. TAB CONTENTS */}
      {!insufficientCorpus && analysisMeta && (
        <div className="max-w-7xl mx-auto px-6 mt-6">
          
          {/* TAB 1: TOPIC REGISTER */}
          {activeTab === 'register' && (
            <div className="space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-[#12151b] p-3 rounded border border-[#242c38]">
                <div className="relative w-full sm:w-80">
                  <Search className="w-4 h-4 absolute left-3 top-2.5 text-[#64748b]" />
                  <input
                    type="text"
                    value={tableSearch}
                    onChange={(e) => setTableSearch(e.target.value)}
                    placeholder="Search topics or terms..."
                    className="w-full bg-[#161a22] border border-[#2d3748] rounded pl-9 pr-3 py-1.5 text-xs font-mono text-[#f1f5f9] focus:outline-none focus:border-[#3b82f6]"
                  />
                </div>
                <div className="text-xs font-mono text-[#94a3b8]">
                  Showing <span className="text-white font-bold">{filteredTopics.length}</span> of {topics.length} topics
                </div>
              </div>

              <div className="bg-[#12151b] border border-[#242c38] rounded overflow-hidden shadow-sm">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs font-mono">
                    <thead className="bg-[#161a22] text-[#94a3b8] uppercase text-[10px] tracking-wider border-b border-[#242c38]">
                      <tr>
                        <th className="py-3 px-4 font-semibold">#</th>
                        <th className="py-3 px-4 font-semibold">Discovered Topic & Key Vocabulary</th>
                        <th className="py-3 px-4 font-semibold">Document Share</th>
                        <th className="py-3 px-4 font-semibold">Docs / Chunks</th>
                        <th className="py-3 px-4 font-semibold">Time Span</th>
                        <th className="py-3 px-4 font-semibold">Persistence</th>
                        <th className="py-3 px-4 font-semibold">Trend Status</th>
                        <th className="py-3 px-4 font-semibold text-right">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#1e2530]">
                      {filteredTopics.map((t, idx) => {
                        const trendItem = trends.find(tr => tr.topic_id === t.id);
                        const latestTrend = trendItem?.series[trendItem.series.length - 1];
                        const isSelected = selectedTopicId === t.id;

                        return (
                          <tr
                            key={t.id}
                            onClick={() => setSelectedTopicId(t.id)}
                            className={`cursor-pointer transition-colors ${
                              isSelected
                                ? 'bg-[#182638] text-white border-l-4 border-l-[#3b82f6]'
                                : 'hover:bg-[#151922] text-[#cbd5e1]'
                            }`}
                          >
                            <td className="py-3 px-4 font-bold text-[#64748b]">{idx + 1}</td>
                            <td className="py-3 px-4">
                              <div className="font-bold text-sm text-[#f1f5f9] tracking-tight">{t.label}</div>
                              <div className="flex flex-wrap gap-1 mt-1">
                                {t.top_terms.slice(0, 5).map((tm, tIdx) => (
                                  <span key={tIdx} className="text-[10px] px-1.5 py-0.2 rounded bg-[#1c2330] text-[#93c5fd] border border-[#2d3a4f]">
                                    {tm.term}
                                  </span>
                                ))}
                              </div>
                            </td>
                            <td className="py-3 px-4">
                              <div className="text-sm font-bold text-[#38bdf8]">{t.prevalence_pct.toFixed(1)}%</div>
                              <div className="w-24 bg-[#1f2937] h-1.5 rounded-full overflow-hidden mt-1">
                                <div className="bg-[#38bdf8] h-full" style={{ width: `${Math.min(t.prevalence_pct, 100)}%` }}></div>
                              </div>
                            </td>
                            <td className="py-3 px-4">
                              <span className="font-bold text-[#f1f5f9]">{t.document_count}</span> docs
                              <span className="text-[#64748b]"> · {t.chunk_count} chunks</span>
                            </td>
                            <td className="py-3 px-4 text-[#94a3b8] text-[11px]">
                              {trendItem?.first_seen || '—'} → {trendItem?.last_seen || '—'}
                            </td>
                            <td className="py-3 px-4">
                              {getPersistenceBadge(trendItem?.persistence_status || 'PERSISTENT')}
                            </td>
                            <td className="py-3 px-4">
                              {getTrendBadge(latestTrend?.trend_status || 'INSUFFICIENT_HISTORY')}
                            </td>
                            <td className="py-3 px-4 text-right">
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setSelectedTopicId(t.id);
                                  setActiveTab('detail');
                                }}
                                className="px-2.5 py-1 bg-[#1a2332] hover:bg-[#253347] border border-[#2d3d54] text-[#93c5fd] rounded text-[11px] font-bold"
                              >
                                Deep Inspect
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: WORD CLOUD */}
          {activeTab === 'wordcloud' && (
            <div className="space-y-6">
              <div className="bg-[#12151b] border border-[#242c38] rounded p-4 shadow-sm">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#1e2530]">
                  <div>
                    <h3 className="font-mono text-sm font-bold text-[#f1f5f9] uppercase tracking-wider flex items-center gap-2">
                      <Tag className="w-4 h-4 text-[#38bdf8]" />
                      MATHEMATICAL CLASS-BASED TF-IDF WORD CLOUD
                    </h3>
                    <p className="text-xs text-[#64748b] font-mono mt-0.5">
                      Word scale strictly corresponds to c-TF-IDF weight (tf × icf) and corpus frequency
                    </p>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="text-[11px] font-mono text-[#64748b]">Mode:</span>
                    <button
                      onClick={() => setCloudMode('ALL')}
                      className={`px-2.5 py-1 text-xs font-mono rounded ${cloudMode === 'ALL' ? 'bg-[#1e3450] text-[#93c5fd] font-bold border border-[#3b82f6]' : 'bg-[#181d24] text-[#94a3b8]'}`}
                    >
                      ALL TOPICS
                    </button>
                    <button
                      onClick={() => setCloudMode('SELECTED_TOPIC')}
                      className={`px-2.5 py-1 text-xs font-mono rounded ${cloudMode === 'SELECTED_TOPIC' ? 'bg-[#1e3450] text-[#93c5fd] font-bold border border-[#3b82f6]' : 'bg-[#181d24] text-[#94a3b8]'}`}
                    >
                      SELECTED TOPIC
                    </button>
                  </div>
                </div>

                {/* Cloud Visual Canvas */}
                <div className="py-10 px-6 min-h-[260px] flex flex-wrap items-center justify-center gap-x-5 gap-y-3 bg-[#0d1015] rounded border border-[#1b222c] my-4 shadow-inner">
                  {wordCloudTerms.map((t, idx) => {
                    const normalized = (t.weight - minWeight) / (maxWeight - minWeight || 1);
                    const fontSize = 12 + Math.round(normalized * 26); // 12px to 38px
                    const color = normalized > 0.65 ? '#38bdf8' : normalized > 0.35 ? '#60a5fa' : '#94a3b8';
                    const opacity = 0.75 + normalized * 0.25;

                    return (
                      <span
                        key={idx}
                        title={`Term: ${t.term}\nWeight: ${t.weight.toFixed(5)}\nFreq: ${t.frequency || 1}\nTopic: ${t.topic_label}`}
                        className="font-mono tracking-tight cursor-pointer hover:underline hover:scale-110 transition-transform select-none"
                        style={{
                          fontSize: `${fontSize}px`,
                          color: color,
                          opacity: opacity,
                          fontWeight: normalized > 0.4 ? 'bold' : 'normal',
                        }}
                      >
                        {t.term}
                      </span>
                    );
                  })}
                </div>

                {/* Analytical Data Table Beneath Visual */}
                <div className="mt-6">
                  <h4 className="text-xs font-mono font-bold text-[#e2e8f0] mb-2 uppercase tracking-wider">
                    VOCABULARY WEIGHT & FREQUENCY REGISTER
                  </h4>
                  <div className="max-h-72 overflow-y-auto border border-[#1e2530] rounded">
                    <table className="w-full text-left text-xs font-mono">
                      <thead className="bg-[#161a22] text-[#94a3b8] uppercase text-[10px] tracking-wider sticky top-0">
                        <tr>
                          <th className="py-2.5 px-3">Term</th>
                          <th className="py-2.5 px-3">Associated Topic</th>
                          <th className="py-2.5 px-3">c-TF-IDF Weight (W_t,c)</th>
                          <th className="py-2.5 px-3">Frequency</th>
                          <th className="py-2.5 px-3">Document Count</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#1e2530] bg-[#12151b]">
                        {wordCloudTerms.map((tm, idx) => (
                          <tr key={idx} className="hover:bg-[#181d26]">
                            <td className="py-2 px-3 font-bold text-[#f1f5f9]">{tm.term}</td>
                            <td className="py-2 px-3 text-[#94a3b8]">{tm.topic_label}</td>
                            <td className="py-2 px-3 text-[#38bdf8] font-bold">{tm.weight.toFixed(5)}</td>
                            <td className="py-2 px-3 text-[#e2e8f0]">{tm.frequency || 1}</td>
                            <td className="py-2 px-3 text-[#cbd5e1]">{tm.document_count || 1} docs</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: TEMPORAL TRENDS */}
          {activeTab === 'trends' && (
            <div className="space-y-6">
              <div className="bg-[#12151b] border border-[#242c38] rounded p-5 shadow-sm">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#1e2530]">
                  <div>
                    <h3 className="font-mono text-sm font-bold text-[#f1f5f9] uppercase tracking-wider flex items-center gap-2">
                      <BarChart3 className="w-4 h-4 text-[#38bdf8]" />
                      TOPIC PREVALENCE OVER TIME (FISCAL YEARS)
                    </h3>
                    <p className="text-xs text-[#64748b] font-mono mt-0.5">
                      Single global topic model alignment · Denominators explicitly displayed
                    </p>
                  </div>

                  <div className="text-xs font-mono text-[#94a3b8]">
                    Timeline: <span className="text-white font-bold">{periods.join(' → ')}</span>
                  </div>
                </div>

                {/* SVG Visual Progression Line Grid */}
                <div className="mt-6 bg-[#0c0e12] border border-[#1b222c] rounded p-5">
                  <div className="text-[11px] font-mono text-[#64748b] mb-4">
                    Y-Axis: Document Share % (with exact topic docs / period total docs)
                  </div>

                  <div className="space-y-6">
                    {trends.map((tItem, tIdx) => {
                      const colors = ['#38bdf8', '#10b981', '#f59e0b', '#a855f7', '#ec4899', '#6366f1'];
                      const strokeColor = colors[tIdx % colors.length];

                      return (
                        <div key={tItem.topic_id} className="bg-[#12161e] border border-[#1e2530] rounded p-4">
                          <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
                            <div className="flex items-center gap-2">
                              <span className="w-3 h-3 rounded-full" style={{ backgroundColor: strokeColor }}></span>
                              <span className="font-mono text-sm font-bold text-white">{tItem.label}</span>
                              {getPersistenceBadge(tItem.persistence_status)}
                            </div>
                            <span className="text-xs font-mono text-[#94a3b8]">
                              Observed in {tItem.observed_periods} of {tItem.total_periods} periods
                            </span>
                          </div>

                          {/* Progression Bar Grid */}
                          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 mt-2">
                            {tItem.series.map((pt, pIdx) => (
                              <div key={pIdx} className="bg-[#181f2a] border border-[#232d3d] p-3 rounded">
                                <div className="flex justify-between items-center text-xs font-mono text-[#94a3b8] mb-1">
                                  <span className="font-bold text-white">{pt.period_value}</span>
                                  {getTrendBadge(pt.trend_status)}
                                </div>
                                <div className="text-lg font-mono font-bold text-[#38bdf8]">
                                  {pt.document_share_pct.toFixed(1)}%
                                </div>
                                <div className="text-[11px] font-mono text-[#cbd5e1] mt-0.5">
                                  Sample: <span className="text-white font-bold">{pt.document_count}</span> / {pt.corpus_document_count} docs
                                </div>
                                <div className="text-[10px] font-mono text-[#64748b] mt-1 flex items-center justify-between">
                                  <span>Chunks: {pt.chunk_count}</span>
                                  {pt.percentage_point_change !== null && (
                                    <span className={pt.percentage_point_change >= 0 ? 'text-emerald-400 font-bold' : 'text-rose-400 font-bold'}>
                                      {pt.percentage_point_change >= 0 ? '+' : ''}{pt.percentage_point_change.toFixed(2)} pp
                                    </span>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: YEAR-TO-YEAR SHIFT */}
          {activeTab === 'yoy' && (
            <div className="space-y-6">
              <div className="bg-[#12151b] border border-[#242c38] rounded p-5 shadow-sm">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#1e2530]">
                  <div>
                    <h3 className="font-mono text-sm font-bold text-[#f1f5f9] uppercase tracking-wider flex items-center gap-2">
                      <ArrowRight className="w-4 h-4 text-[#38bdf8]" />
                      YEAR-TO-YEAR TOPIC SHIFT & PROGRESSION
                    </h3>
                    <p className="text-xs text-[#64748b] font-mono mt-0.5">
                      Compares topic document share between two discrete historical periods with evidence gates
                    </p>
                  </div>

                  <div className="flex items-center gap-3 bg-[#161a22] p-2 rounded border border-[#283242]">
                    <div>
                      <span className="text-[10px] font-mono uppercase text-[#64748b] block">Period A</span>
                      <select
                        value={yoyPeriodA}
                        onChange={(e) => setYoyPeriodA(e.target.value)}
                        className="bg-[#10141a] border border-[#2d3748] rounded px-2 py-1 text-xs font-mono text-white"
                      >
                        {periods.map(p => <option key={p} value={p}>{p}</option>)}
                      </select>
                    </div>

                    <ArrowRight className="w-4 h-4 text-[#64748b] mt-3" />

                    <div>
                      <span className="text-[10px] font-mono uppercase text-[#64748b] block">Period B</span>
                      <select
                        value={yoyPeriodB}
                        onChange={(e) => setYoyPeriodB(e.target.value)}
                        className="bg-[#10141a] border border-[#2d3748] rounded px-2 py-1 text-xs font-mono text-white"
                      >
                        {periods.map(p => <option key={p} value={p}>{p}</option>)}
                      </select>
                    </div>
                  </div>
                </div>

                {/* YoY Table */}
                <div className="mt-4 overflow-x-auto">
                  <table className="w-full text-left text-xs font-mono">
                    <thead className="bg-[#161a22] text-[#94a3b8] uppercase text-[10px] tracking-wider border-b border-[#242c38]">
                      <tr>
                        <th className="py-3 px-4">Topic</th>
                        <th className="py-3 px-4">{yoyPeriodA} Share</th>
                        <th className="py-3 px-4">{yoyPeriodB} Share</th>
                        <th className="py-3 px-4">Δ pp (Percentage Points)</th>
                        <th className="py-3 px-4">Δ Absolute Docs</th>
                        <th className="py-3 px-4">Sample Size ({yoyPeriodA} → {yoyPeriodB})</th>
                        <th className="py-3 px-4">Trend Classification</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#1e2530] bg-[#12151b]">
                      {yoyComparisons.map((c, idx) => (
                        <tr key={idx} className="hover:bg-[#181d26]">
                          <td className="py-3 px-4 font-bold text-[#f1f5f9]">{c.topic_label}</td>
                          <td className="py-3 px-4 text-[#cbd5e1]">{c.document_share_a_pct.toFixed(2)}%</td>
                          <td className="py-3 px-4 text-[#38bdf8] font-bold">{c.document_share_b_pct.toFixed(2)}%</td>
                          <td className="py-3 px-4">
                            <span className={`font-bold ${c.percentage_point_change > 0 ? 'text-emerald-400' : c.percentage_point_change < 0 ? 'text-rose-400' : 'text-slate-400'}`}>
                              {c.percentage_point_change > 0 ? '+' : ''}{c.percentage_point_change.toFixed(2)} pp
                            </span>
                          </td>
                          <td className="py-3 px-4 text-[#cbd5e1]">
                            {c.absolute_change > 0 ? `+${c.absolute_change}` : c.absolute_change} docs
                          </td>
                          <td className="py-3 px-4 text-[#94a3b8]">
                            ({c.document_count_a} / {c.corpus_document_count_a}) → ({c.document_count_b} / {c.corpus_document_count_b})
                          </td>
                          <td className="py-3 px-4">
                            {getTrendBadge(c.trend_status)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* TAB 5: COMPARISON WORKBENCH */}
          {activeTab === 'comparison' && (
            <div className="space-y-6">
              <div className="bg-[#12151b] border border-[#242c38] rounded p-5 shadow-sm">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#1e2530]">
                  <div>
                    <h3 className="font-mono text-sm font-bold text-[#f1f5f9] uppercase tracking-wider flex items-center gap-2">
                      <Building2 className="w-4 h-4 text-[#38bdf8]" />
                      MULTI-DIMENSIONAL TOPIC COMPARISON
                    </h3>
                    <p className="text-xs text-[#64748b] font-mono mt-0.5">
                      Compare topic distribution across operational and organizational dimensions
                    </p>
                  </div>

                  <div className="flex items-center gap-1.5 bg-[#161a22] p-1 rounded border border-[#242c38]">
                    <button
                      onClick={() => { setCompDimension('ORGANIZATION'); setCompDimA(''); setCompDimB(''); }}
                      className={`px-3 py-1 text-xs font-mono rounded ${compDimension === 'ORGANIZATION' ? 'bg-[#1e3450] text-[#93c5fd] font-bold' : 'text-[#94a3b8]'}`}
                    >
                      ORGANIZATION
                    </button>
                    <button
                      onClick={() => { setCompDimension('MINE'); setCompDimA(''); setCompDimB(''); }}
                      className={`px-3 py-1 text-xs font-mono rounded ${compDimension === 'MINE' ? 'bg-[#1e3450] text-[#93c5fd] font-bold' : 'text-[#94a3b8]'}`}
                    >
                      MINE
                    </button>
                    <button
                      onClick={() => { setCompDimension('BLOCK'); setCompDimA(''); setCompDimB(''); }}
                      className={`px-3 py-1 text-xs font-mono rounded ${compDimension === 'BLOCK' ? 'bg-[#1e3450] text-[#93c5fd] font-bold' : 'text-[#94a3b8]'}`}
                    >
                      BLOCK
                    </button>
                    <button
                      onClick={() => { setCompDimension('DOCUMENT_TYPE'); setCompDimA(''); setCompDimB(''); }}
                      className={`px-3 py-1 text-xs font-mono rounded ${compDimension === 'DOCUMENT_TYPE' ? 'bg-[#1e3450] text-[#93c5fd] font-bold' : 'text-[#94a3b8]'}`}
                    >
                      DOC TYPE
                    </button>
                  </div>
                </div>

                {/* Dimension Selectors */}
                {compResult?.available_values && (
                  <div className="flex items-center gap-3 mt-4 p-3 bg-[#161a22] rounded border border-[#1f2634]">
                    <span className="text-xs font-mono text-[#94a3b8]">Select pair to compare:</span>
                    <select
                      value={compDimA}
                      onChange={(e) => setCompDimA(e.target.value)}
                      className="bg-[#10141a] border border-[#2d3748] rounded px-2 py-1 text-xs font-mono text-white"
                    >
                      <option value="">Select {compDimension} A</option>
                      {compResult.available_values.map((v: string) => <option key={v} value={v}>{v}</option>)}
                    </select>

                    <ArrowRight className="w-4 h-4 text-[#64748b]" />

                    <select
                      value={compDimB}
                      onChange={(e) => setCompDimB(e.target.value)}
                      className="bg-[#10141a] border border-[#2d3748] rounded px-2 py-1 text-xs font-mono text-white"
                    >
                      <option value="">Select {compDimension} B</option>
                      {compResult.available_values.map((v: string) => <option key={v} value={v}>{v}</option>)}
                    </select>
                  </div>
                )}

                {/* Comparison Results */}
                {compResult?.comparisons && (
                  <div className="mt-4 space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs font-mono">
                      <div className="bg-[#161f2c] border border-[#223347] p-3 rounded">
                        <span className="text-[#64748b] block">Common Topics</span>
                        <span className="text-white font-bold text-sm">{(compResult.common_topics || []).length}</span>
                        <p className="text-[10px] text-[#94a3b8] mt-1 truncate">{(compResult.common_topics || []).join(', ') || 'None'}</p>
                      </div>
                      <div className="bg-[#161f2c] border border-[#223347] p-3 rounded">
                        <span className="text-[#64748b] block">Unique to {compResult.dimension_a}</span>
                        <span className="text-cyan-400 font-bold text-sm">{(compResult.unique_to_dimension_a || []).length}</span>
                        <p className="text-[10px] text-[#94a3b8] mt-1 truncate">{(compResult.unique_to_dimension_a || []).join(', ') || 'None'}</p>
                      </div>
                      <div className="bg-[#161f2c] border border-[#223347] p-3 rounded">
                        <span className="text-[#64748b] block">Unique to {compResult.dimension_b}</span>
                        <span className="text-amber-400 font-bold text-sm">{(compResult.unique_to_dimension_b || []).length}</span>
                        <p className="text-[10px] text-[#94a3b8] mt-1 truncate">{(compResult.unique_to_dimension_b || []).join(', ') || 'None'}</p>
                      </div>
                    </div>

                    <div className="overflow-x-auto border border-[#1e2530] rounded">
                      <table className="w-full text-left text-xs font-mono">
                        <thead className="bg-[#161a22] text-[#94a3b8] uppercase text-[10px] tracking-wider">
                          <tr>
                            <th className="py-2.5 px-3">Topic</th>
                            <th className="py-2.5 px-3">{compResult.dimension_a} Share</th>
                            <th className="py-2.5 px-3">{compResult.dimension_b} Share</th>
                            <th className="py-2.5 px-3">Difference</th>
                            <th className="py-2.5 px-3">Chunks ({compResult.dimension_a} vs {compResult.dimension_b})</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-[#1e2530] bg-[#12151b]">
                          {compResult.comparisons.map((item: any, idx: number) => (
                            <tr key={idx} className="hover:bg-[#181d26]">
                              <td className="py-2 px-3 font-bold text-white">{item.topic_label}</td>
                              <td className="py-2 px-3 text-[#38bdf8]">{item.share_a_pct.toFixed(2)}%</td>
                              <td className="py-2 px-3 text-[#f59e0b]">{item.share_b_pct.toFixed(2)}%</td>
                              <td className="py-2 px-3 font-bold">
                                {item.difference_pct_points > 0 ? `+${item.difference_pct_points.toFixed(2)}` : item.difference_pct_points.toFixed(2)} pp
                              </td>
                              <td className="py-2 px-3 text-[#94a3b8]">{item.chunk_count_a} vs {item.chunk_count_b}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* Overall Distribution View if no pair chosen */}
                {!compResult?.comparisons && compResult?.distribution && (
                  <div className="mt-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                    {Object.entries(compResult.distribution).map(([val, dInfo]: any) => (
                      <div key={val} className="bg-[#161a22] border border-[#242c38] p-3.5 rounded">
                        <div className="flex justify-between items-center mb-2 pb-1 border-b border-[#222a36]">
                          <span className="font-mono font-bold text-white text-sm">{val}</span>
                          <span className="text-[11px] font-mono text-[#38bdf8]">{dInfo.corpus_document_count} docs</span>
                        </div>
                        <div className="space-y-1.5 mt-2">
                          {dInfo.topics.slice(0, 4).map((tp: any) => (
                            <div key={tp.topic_id} className="flex justify-between text-xs font-mono">
                              <span className="text-[#94a3b8] truncate w-36" title={tp.topic_label}>{tp.topic_label}</span>
                              <span className="font-bold text-white">{tp.document_share_pct.toFixed(1)}%</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 6: TOPIC DETAIL & EVIDENCE */}
          {activeTab === 'detail' && selectedTopicDetail && (
            <div className="space-y-6">
              {/* Topic Header Card */}
              <div className="bg-[#12151b] border border-[#242c38] rounded p-5 shadow-sm">
                <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-[#1e2530]">
                  <div>
                    <span className="text-[10px] font-mono uppercase text-[#38bdf8] tracking-widest block">SELECTED TOPIC DOSSIER</span>
                    <h2 className="text-xl font-mono font-black text-white mt-0.5 tracking-tight">
                      {selectedTopicDetail.label}
                    </h2>
                    <p className="text-xs font-mono text-[#64748b] mt-1">Topic ID: {selectedTopicDetail.id}</p>
                  </div>

                  <div className="flex flex-wrap items-center gap-4 text-xs font-mono">
                    <div className="bg-[#16202c] border border-[#243346] px-3 py-2 rounded">
                      <span className="text-[#64748b] block text-[10px]">CORPUS SHARE</span>
                      <span className="text-lg font-bold text-[#38bdf8]">{selectedTopicDetail.prevalence_pct.toFixed(1)}%</span>
                    </div>
                    <div className="bg-[#16202c] border border-[#243346] px-3 py-2 rounded">
                      <span className="text-[#64748b] block text-[10px]">EVIDENCE VOLUME</span>
                      <span className="text-lg font-bold text-white">{selectedTopicDetail.document_count} Docs · {selectedTopicDetail.chunk_count} Chunks</span>
                    </div>
                    {selectedTopicDetail.semantic_topic_coherence !== undefined && (
                      <div className="bg-[#16202c] border border-[#243346] px-3 py-2 rounded">
                        <span className="text-[#64748b] block text-[10px]">SEMANTIC TOPIC COHERENCE</span>
                        <span className="text-lg font-bold text-emerald-400">{selectedTopicDetail.semantic_topic_coherence?.toFixed(3) || '—'}</span>
                        <span className="text-[9px] text-[#64748b] block italic">Semantic similarity diagnostic; not standardized accuracy</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Top Terms Badge Register */}
                <div className="mt-4">
                  <h4 className="text-xs font-mono font-bold text-[#94a3b8] uppercase tracking-wider mb-2">
                    Top Diagnostic Terms & Mathematical Weights
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {(selectedTopicDetail.terms || []).map((tm: any, idx: number) => (
                      <div key={idx} className="bg-[#18202c] border border-[#28364a] px-2.5 py-1 rounded text-xs font-mono flex items-center gap-2">
                        <span className="font-bold text-white">{tm.term}</span>
                        <span className="text-[10px] text-[#38bdf8] font-bold">W: {tm.weight.toFixed(4)}</span>
                        <span className="text-[10px] text-[#64748b]">#{tm.rank}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Evidence Explorer & Navigation */}
              <div className="bg-[#12151b] border border-[#242c38] rounded p-5 shadow-sm">
                <div className="flex items-center justify-between pb-3 border-b border-[#1e2530]">
                  <div>
                    <h3 className="font-mono text-sm font-bold text-[#f1f5f9] uppercase tracking-wider flex items-center gap-2">
                      <FolderOpen className="w-4 h-4 text-[#38bdf8]" />
                      GROUNDED EVIDENCE CARDS & PHYSICAL PROVENANCE
                    </h3>
                    <p className="text-xs text-[#64748b] font-mono mt-0.5">
                      Direct navigation: Topic → Document → Chunk → Physical Page → Original Source
                    </p>
                  </div>
                  <span className="text-xs font-mono text-[#38bdf8]">
                    {evidenceCards.length} Verified Evidence Cards
                  </span>
                </div>

                <div className="mt-4 space-y-3">
                  {evidenceCards.map((ev, idx) => (
                    <div key={ev.evidence_id || idx} className="bg-[#141820] border border-[#202734] hover:border-[#38bdf8]/40 p-4 rounded transition-all">
                      <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-[#1b222c]">
                        <div className="flex items-center gap-2.5">
                          <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-[#1e293b] text-[#94a3b8] border border-[#334155]">
                            {ev.organization_code || 'CIL'}
                          </span>
                          <span className="text-xs font-mono font-bold text-white">{ev.document_title}</span>
                          <span className="text-[10px] font-mono text-[#64748b]">({ev.document_type})</span>
                        </div>

                        <div className="flex items-center gap-3 text-xs font-mono">
                          <span className="text-[#38bdf8]">Page {ev.page_number}</span>
                          <span className="text-[#64748b]">Chunk: {ev.chunk_id ? `${ev.chunk_id.slice(0, 8)}...` : '—'}</span>
                          <span className="text-emerald-400 font-bold">Rep Score: {ev.representative_score?.toFixed(3) || '—'}</span>
                          <Link
                            to={`/documents/${ev.document_id}?page=${ev.page_number}&chunk=${ev.chunk_id}`}
                            className="flex items-center gap-1 text-[#38bdf8] hover:text-[#7dd3fc] font-bold hover:underline"
                          >
                            <ExternalLink className="w-3.5 h-3.5" />
                            VIEW SOURCE
                          </Link>
                        </div>
                      </div>

                      <div className="mt-2.5 text-xs font-sans text-[#cbd5e1] leading-relaxed italic bg-[#0f1217] p-3 rounded border border-[#1a1f29]">
                        "{ev.content}"
                      </div>

                      <div className="flex flex-wrap items-center gap-4 text-[10px] font-mono text-[#64748b] mt-2">
                        {ev.mine_name && <span>Mine: <strong className="text-[#94a3b8]">{ev.mine_name}</strong></span>}
                        {ev.block_name && <span>Block: <strong className="text-[#94a3b8]">{ev.block_name}</strong></span>}
                        {ev.fiscal_year && <span>Period: <strong className="text-[#94a3b8]">{ev.fiscal_year}</strong></span>}
                        {ev.section_heading && <span>Section: <strong className="text-[#94a3b8]">{ev.section_heading}</strong></span>}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB 7: TERM EVOLUTION */}
          {activeTab === 'evolution' && termEvolution && (
            <div className="space-y-6">
              <div className="bg-[#12151b] border border-[#242c38] rounded p-5 shadow-sm">
                <div className="flex items-center justify-between pb-3 border-b border-[#1e2530]">
                  <div>
                    <h3 className="font-mono text-sm font-bold text-[#f1f5f9] uppercase tracking-wider flex items-center gap-2">
                      <Clock className="w-4 h-4 text-[#38bdf8]" />
                      TERM EVOLUTION ACROSS TIME: {termEvolution.topic_label}
                    </h3>
                    <p className="text-xs text-[#64748b] font-mono mt-0.5">
                      Tracks term importance, frequency, and weight transitions across historical periods
                    </p>
                  </div>
                </div>

                <div className="mt-4 overflow-x-auto">
                  <table className="w-full text-left text-xs font-mono">
                    <thead className="bg-[#161a22] text-[#94a3b8] uppercase text-[10px] tracking-wider border-b border-[#242c38]">
                      <tr>
                        <th className="py-2.5 px-3">Term</th>
                        <th className="py-2.5 px-3">Global Rank</th>
                        <th className="py-2.5 px-3">Global Weight</th>
                        {(termEvolution.periods || []).map((p: string) => (
                          <th key={p} className="py-2.5 px-3">{p} Frequency</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#1e2530] bg-[#12151b]">
                      {(termEvolution.term_evolution || []).map((tm: any, idx: number) => (
                        <tr key={idx} className="hover:bg-[#181d26]">
                          <td className="py-2.5 px-3 font-bold text-white">{tm.term}</td>
                          <td className="py-2.5 px-3 text-[#64748b]">#{tm.global_rank}</td>
                          <td className="py-2.5 px-3 text-[#38bdf8] font-bold">{tm.global_weight.toFixed(5)}</td>
                          {(termEvolution.periods || []).map((p: string) => (
                            <td key={p} className="py-2.5 px-3 text-[#cbd5e1]">
                              {tm.period_frequencies?.[p] ?? 0}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

        </div>
      )}

      {/* 7. History Drawer */}
      {historyOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 flex justify-end">
          <div className="w-full max-w-md bg-[#12151b] border-l border-[#242c38] h-full overflow-y-auto p-5 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-[#1e2530]">
              <div className="flex items-center gap-2">
                <History className="w-4 h-4 text-[#38bdf8]" />
                <h3 className="font-mono text-sm font-bold text-white uppercase">Completed Analyses</h3>
              </div>
              <button onClick={() => setHistoryOpen(false)} className="text-[#64748b] hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="mt-4 space-y-3">
              {historyItems.map((item) => (
                <div
                  key={item.id}
                  onClick={() => {
                    loadAnalysis(item.id);
                    setHistoryOpen(false);
                  }}
                  className={`p-3.5 rounded border cursor-pointer transition-all ${
                    item.id === activeAnalysisId
                      ? 'bg-[#182638] border-[#3b82f6]'
                      : 'bg-[#161a22] border-[#222a36] hover:border-[#38bdf8]'
                  }`}
                >
                  <div className="flex justify-between items-start text-xs font-mono mb-1">
                    <span className="font-bold text-white">{item.organization_code || 'GLOBAL CORPUS'}</span>
                    <span className="text-[10px] text-[#64748b]">{new Date(item.created_at).toLocaleDateString()}</span>
                  </div>
                  <div className="text-[11px] font-mono text-[#38bdf8]">
                    {item.document_count} Docs · {item.chunk_count} Chunks · {item.analysis_method}
                  </div>
                  <div className="text-[10px] font-mono text-[#94a3b8] mt-1 truncate">
                    Filters: {JSON.stringify(item.corpus_filters) || 'None'}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 8. Add to Report Modal */}
      {reportModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-4">
          <div className="bg-[#12151b] border border-[#2b4c73] rounded-lg max-w-lg w-full p-6 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-[#1e2530]">
              <div className="flex items-center gap-2">
                <FileSpreadsheet className="w-5 h-5 text-[#38bdf8]" />
                <h3 className="font-mono text-sm font-bold text-white uppercase">
                  ADD ANALYSIS TO STATUTORY REPORT
                </h3>
              </div>
              <button onClick={() => setReportModalOpen(false)} className="text-[#64748b] hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="mt-4 space-y-4 text-xs font-mono">
              <p className="text-[#94a3b8] text-[11px] leading-relaxed">
                Transfers topic parameters, temporal progression, and source evidence into the Report Studio as an <strong>Optional Analytical Annexure</strong>. Statutory fields and official numbering remain untouched.
              </p>

              <div>
                <label className="block uppercase text-[#64748b] text-[10px] mb-1 font-bold">Target Statutory Report</label>
                <select
                  value={targetReportId}
                  onChange={(e) => setTargetReportId(e.target.value)}
                  className="w-full bg-[#161a22] border border-[#2d3748] rounded px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-[#38bdf8]"
                >
                  {availableReports.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.report_title || `${r.mine_name} - ${r.block_name}`} ({r.status})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block uppercase text-[#64748b] text-[10px] mb-1 font-bold">Scope Selection</label>
                <div className="p-2.5 bg-[#161a22] border border-[#222936] rounded text-white font-bold">
                  {selectedTopicDetail ? `Focus Topic: ${selectedTopicDetail.label}` : 'Entire Corpus Thematic Synthesis (All Topics)'}
                </div>
              </div>

              <div className="space-y-2 pt-2 border-t border-[#1e2530]">
                <label className="flex items-center gap-2 cursor-pointer text-[#cbd5e1]">
                  <input
                    type="checkbox"
                    checked={attachTrends}
                    onChange={(e) => setAttachTrends(e.target.checked)}
                    className="rounded bg-[#161a22] border-[#2d3748] text-[#38bdf8]"
                  />
                  <span>Include Temporal Trend Progression Series</span>
                </label>

                <label className="flex items-center gap-2 cursor-pointer text-[#cbd5e1]">
                  <input
                    type="checkbox"
                    checked={attachEvidence}
                    onChange={(e) => setAttachEvidence(e.target.checked)}
                    className="rounded bg-[#161a22] border-[#2d3748] text-[#38bdf8]"
                  />
                  <span>Include Grounded Representative Evidence Cards</span>
                </label>
              </div>

              {attachSuccess && (
                <div className="bg-[#0f291e] border border-[#10b981]/40 text-[#a7f3d0] p-3 rounded text-[11px] flex items-center justify-between">
                  <span>{attachSuccess}</span>
                  <Link
                    to={`/reports/${targetReportId}`}
                    className="underline text-emerald-400 font-bold ml-2"
                  >
                    Open Studio →
                  </Link>
                </div>
              )}
            </div>

            <div className="flex justify-end gap-2 mt-6 pt-3 border-t border-[#1e2530]">
              <button
                onClick={() => setReportModalOpen(false)}
                className="px-3 py-1.5 bg-[#181d24] hover:bg-[#202732] border border-[#2d3748] rounded text-xs font-mono text-[#94a3b8]"
              >
                Close
              </button>

              <button
                onClick={handleAttachToReport}
                disabled={attachLoading || !targetReportId}
                className="px-4 py-1.5 bg-[#0f766e] hover:bg-[#115e59] border border-[#14b8a6]/40 text-white font-mono font-bold rounded text-xs transition-all disabled:opacity-50 flex items-center gap-1.5"
              >
                {attachLoading && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                Confirm & Attach to Report
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
