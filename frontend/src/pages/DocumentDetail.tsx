import React, { useState, useEffect } from 'react';
import { useParams, useSearchParams, Link } from 'react-router-dom';
import { apiClient } from '../api/client';
import {
  FileText,
  Table as TableIcon,
  Layers,
  Info,
  Clock,
  Download,
  Check,
  Copy,
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  Hash,
  CheckCircle,
  AlertTriangle,
  RefreshCw,
  ShieldCheck,
  Eye,
  Tag,
  ImageIcon
} from 'lucide-react';

interface DocumentDetailData {
  id: string;
  title: string;
  original_filename: string;
  organization_id: string;
  organization_code: string;
  organization_name: string;
  document_type: string;
  source_tier: string;
  mime_type: string;
  file_size_bytes: number;
  sha256_hash: string;
  status: string;
  page_count: number;
  table_count: number;
  chunk_count: number;
  latest_job: {
    id: string;
    status: string;
    progress_pct: number;
    error_message: string | null;
  } | null;
  versions: Array<{
    id: string;
    version_number: number;
    supersedes_id: string | null;
    sha256_hash: string;
    created_at: string;
  }>;
  created_at: string;
  updated_at: string;
}

interface DocumentPageItem {
  id: string;
  page_number: number;
  extracted_text: string;
  ocr_applied: boolean;
  confidence_score: number | null;
  width: number | null;
  height: number | null;
  metadata: any;
}

interface TableRowDetail {
  row_index: number;
  logical_row_index: number | null;
  source_page: number | null;
  cells: string[];
}

interface PhysicalSliceInfo {
  id: string;
  page_number: number;
  table_index: number;
  part_number: number;
  row_count: number;
  continuation_status: string;
}

interface TableItem {
  id: string;
  page_number: number;
  table_index: number;
  caption: string;
  headers: string[];
  row_count: number;
  col_count: number;
  logical_table_id?: string;
  is_continuation?: boolean;
  continuation_of_id?: string | null;
  part_number?: number;
  total_parts?: number;
  has_repeated_headers?: boolean;
  continuation_confidence?: number;
  continuation_status?: string;
  spanned_pages?: number[];
  page_label?: string;
  physical_slices?: PhysicalSliceInfo[];
  metadata: any;
  rows: string[][];
  row_details?: TableRowDetail[];
}

interface ChunkItem {
  id: string;
  chunk_index: number;
  page_number: number | null;
  chunk_type: string;
  section_heading: string | null;
  content: string;
  metadata: any;
}

interface VisualItem {
  id: string;
  page_number: number;
  visual_type: string;
  classification_confidence: number;
  extraction_method: string;
  figure_number: string | null;
  caption: string | null;
  ocr_confidence: number | null;
  verification_status: string;
  width_px: number | null;
  height_px: number | null;
  bbox: { x0: number; y0: number; x1: number; y1: number } | null;
  image_hash: string;
  created_at: string | null;
}

interface ExtractedFieldItem {
  id: string;
  field_name: string;
  field_category: string;
  data_type: string;
  raw_value: string;
  normalized_value: string | null;
  numeric_value: number | null;
  unit: string | null;
  page_number: number | null;
  table_id: string | null;
  row_id: string | null;
  chunk_id: string | null;
  source_text: string | null;
  extraction_method: string;
  confidence_score: number;
  confidence_level: string;
  validation_status: string;
  reconciliation_status: string;
  verification_status: string;
  is_corrected: boolean;
  corrected_value: string | null;
  validation_results: Array<{
    id: string;
    rule_name: string;
    rule_category: string;
    status: string;
    severity: string;
    message: string;
    observed_value: string | null;
    expected_constraint: string | null;
  }>;
}

export const DocumentDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const pageParam = searchParams.get('page');
  const chunkParam = searchParams.get('chunk');

  const [document, setDocument] = useState<DocumentDetailData | null>(null);
  const [pages, setPages] = useState<DocumentPageItem[]>([]);
  const [tables, setTables] = useState<TableItem[]>([]);
  const [chunks, setChunks] = useState<ChunkItem[]>([]);
  const [fields, setFields] = useState<ExtractedFieldItem[]>([]);
  const [isExtracting, setIsExtracting] = useState<boolean>(false);
  const [evidenceModalField, setEvidenceModalField] = useState<ExtractedFieldItem | null>(null);
  const [visuals, setVisuals] = useState<VisualItem[]>([]);
  const [selectedVisual, setSelectedVisual] = useState<VisualItem | null>(null);

  const [activeTab, setActiveTab] = useState<'metadata' | 'pages' | 'tables' | 'figures' | 'chunks' | 'extraction' | 'validation' | 'job'>('pages');
  const [tableView, setTableView] = useState<'logical' | 'physical'>('logical');
  const [selectedPageIndex, setSelectedPageIndex] = useState<number>(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copiedHash, setCopiedHash] = useState(false);

  const fetchTables = async (viewMode: 'logical' | 'physical') => {
    try {
      const res = await apiClient.get(`/documents/${id}/tables?view=${viewMode}`);
      setTables(res.data);
    } catch (err: any) {
      console.error('Failed to load tables', err);
    }
  };

  const fetchFields = async () => {
    try {
      const res = await apiClient.get('/extraction/documents/' + id + '/fields');
      setFields(res.data);
    } catch (err) {
      console.log('No extraction fields found yet', err);
    }
  };

  const handleRunExtraction = async () => {
    try {
      setIsExtracting(true);
      await apiClient.post('/extraction/run/' + id);
      await fetchFields();
      setActiveTab('extraction');
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Extraction failed');
    } finally {
      setIsExtracting(false);
    }
  };

  useEffect(() => {
    if (!id) return;

    const fetchAllData = async () => {
      try {
        setLoading(true);
        const [docRes, pagesRes, tablesRes, chunksRes] = await Promise.all([
          apiClient.get('/documents/' + id),
          apiClient.get('/documents/' + id + '/pages'),
          apiClient.get('/documents/' + id + '/tables?view=' + tableView),
          apiClient.get('/documents/' + id + '/chunks'),
        ]);

        setDocument(docRes.data);
        setPages(pagesRes.data);
        setTables(tablesRes.data);
        setChunks(chunksRes.data);

        // Fetch visual assets (Phase 9)
        try {
          const visualsRes = await apiClient.get('/visuals/document/' + id);
          setVisuals(visualsRes.data?.visuals || []);
        } catch {
          setVisuals([]);
        }

        // Apply URL parameter target navigation (Topic Evidence provenance)
        if (pageParam) {
          const targetPageNum = parseInt(pageParam, 10);
          const targetIdx = (pagesRes.data || []).findIndex((p: any) => p.page_number === targetPageNum);
          if (targetIdx >= 0) {
            setSelectedPageIndex(targetIdx);
            setActiveTab('pages');
          }
        } else if (chunkParam) {
          setActiveTab('chunks');
        }

        await fetchFields();
        setError(null);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to load document details');
      } finally {
        setLoading(false);
      }
    };

    fetchAllData();
  }, [id, pageParam, chunkParam]);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedHash(true);
    setTimeout(() => setCopiedHash(false), 2000);
  };

  const handleDownload = async () => {
    if (!document) return;
    try {
      const response = await apiClient.get('/documents/' + document.id + '/download', {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', document.original_filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      alert('Failed to download document file.');
    }
  };

  if (loading) {
    return (
      <div className="p-12 text-center text-gray-500 flex flex-col items-center justify-center gap-3">
        <Clock className="w-8 h-8 animate-spin text-blue-600" />
        <span className="text-sm font-medium">Loading document intelligence data...</span>
      </div>
    );
  }

  if (error || !document) {
    return (
      <div className="max-w-4xl mx-auto p-8 bg-red-50 border border-red-200 rounded text-center space-y-3">
        <AlertCircle className="w-8 h-8 text-red-600 mx-auto" />
        <h2 className="text-lg font-bold text-red-900">Document Access Error</h2>
        <p className="text-sm text-red-700">{error || 'Document not found'}</p>
        <Link to="/documents" className="text-sm font-semibold text-blue-600 hover:underline">
          ← Back to Documents
        </Link>
      </div>
    );
  }

  const selectedPage = pages[selectedPageIndex] || null;

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-xs text-gray-500">
        <Link to="/documents" className="hover:underline">Documents</Link>
        <span>/</span>
        <span className="text-gray-800 font-semibold truncate max-w-md">{document.title}</span>
      </div>

      {/* Header Card */}
      <div className="bg-white rounded border border-gray-200 p-6 shadow-sm space-y-4">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5 mb-1.5 flex-wrap">
              <span className="font-mono text-xs font-bold px-2 py-0.5 bg-gray-100 text-gray-800 rounded border border-gray-300">
                {document.organization_code}
              </span>
              <span className={`text-xs font-semibold px-2.5 py-0.5 rounded border ${
                document.source_tier === 'TIER_A'
                  ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
                  : document.source_tier === 'TIER_B'
                  ? 'bg-blue-100 text-blue-800 border-blue-300'
                  : 'bg-amber-100 text-amber-800 border-amber-300'
              }`}>
                {document.source_tier === 'TIER_A' ? 'Tier A • Authoritative' : document.source_tier === 'TIER_B' ? 'Tier B • Operational' : 'Tier C • Unverified'}
              </span>
              <span className="text-xs font-medium text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                {document.status}
              </span>
            </div>
            <h1 className="text-2xl font-bold text-gray-900">{document.title}</h1>
            <p className="text-xs text-gray-500 font-mono mt-1">
              Original file: {document.original_filename} ({(document.file_size_bytes / 1024).toFixed(1)} KB)
            </p>
          </div>

          <button
            onClick={handleDownload}
            className="inline-flex items-center gap-2 bg-gray-100 hover:bg-gray-200 text-gray-800 text-xs font-semibold px-3.5 py-2 rounded border border-gray-300 transition-colors self-start"
          >
            <Download className="w-4 h-4 text-gray-600" /> Download Original
          </button>
        </div>

        {/* SHA-256 Provenance Banner */}
        <div className="bg-gray-50 border border-gray-200 rounded p-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs font-mono text-gray-700">
          <div className="flex items-center gap-2 overflow-hidden">
            <Hash className="w-4 h-4 text-gray-500 flex-shrink-0" />
            <span className="text-gray-500">SHA-256:</span>
            <span className="truncate font-bold text-gray-900">{document.sha256_hash}</span>
          </div>
          <button
            onClick={() => copyToClipboard(document.sha256_hash)}
            className="inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 self-start sm:self-auto flex-shrink-0"
          >
            {copiedHash ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
            {copiedHash ? 'Copied' : 'Copy Hash'}
          </button>
        </div>

        {/* Stat badges */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 text-center text-xs">
          <div className="p-2.5 bg-gray-50 rounded border border-gray-200">
            <span className="block text-gray-500 uppercase tracking-wider text-[10px]">Pages Processed</span>
            <span className="text-lg font-bold text-gray-800">{document.page_count}</span>
          </div>
          <div className="p-2.5 bg-gray-50 rounded border border-gray-200">
            <span className="block text-gray-500 uppercase tracking-wider text-[10px]">Preserved Tables</span>
            <span className="text-lg font-bold text-emerald-700">{document.table_count}</span>
          </div>
          <div className="p-2.5 bg-gray-50 rounded border border-gray-200">
            <span className="block text-gray-500 uppercase tracking-wider text-[10px]">Structured Chunks</span>
            <span className="text-lg font-bold text-blue-700">{document.chunk_count}</span>
          </div>
          <div className="p-2.5 bg-gray-50 rounded border border-gray-200">
            <span className="block text-gray-500 uppercase tracking-wider text-[10px]">Document Type</span>
            <span className="text-sm font-semibold text-gray-800">{document.document_type.replace('_', ' ')}</span>
          </div>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="border-b border-gray-200 flex gap-4 text-sm font-semibold">
        <button
          onClick={() => setActiveTab('pages')}
          className={`pb-3 border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === 'pages' ? 'border-blue-600 text-blue-700' : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          <FileText className="w-4 h-4" /> Extracted Pages ({pages.length})
        </button>
        <button
          onClick={() => setActiveTab('tables')}
          className={`pb-3 border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === 'tables' ? 'border-blue-600 text-blue-700' : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          <TableIcon className="w-4 h-4" /> Extracted Tables ({tables.length})
        </button>
        <button
          onClick={() => setActiveTab('figures')}
          className={`pb-3 border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === 'figures' ? 'border-blue-600 text-blue-700' : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          <ImageIcon className="w-4 h-4" /> Figures ({visuals.length})
        </button>
        <button
          onClick={() => setActiveTab('chunks')}
          className={`pb-3 border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === 'chunks' ? 'border-blue-600 text-blue-700' : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          <Layers className="w-4 h-4" /> Structure Chunks ({chunks.length})
        </button>
        <button
          onClick={() => setActiveTab('extraction')}
          className={`pb-3 border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === 'extraction' ? 'border-blue-600 text-blue-700' : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          <CheckCircle className="w-4 h-4" /> Structured Fields ({fields.length})
        </button>
        <button
          onClick={() => setActiveTab('validation')}
          className={`pb-3 border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === 'validation' ? 'border-blue-600 text-blue-700' : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          <AlertTriangle className="w-4 h-4" /> Validation Rules ({fields.reduce((acc, f) => acc + (f.validation_results?.filter(vr => vr.status !== 'PASS').length || 0), 0)})
        </button>
        <button
          onClick={() => setActiveTab('metadata')}
          className={`pb-3 border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === 'metadata' ? 'border-blue-600 text-blue-700' : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          <Info className="w-4 h-4" /> Metadata & Provenance
        </button>
        <button
          onClick={() => setActiveTab('job')}
          className={`pb-3 border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === 'job' ? 'border-blue-600 text-blue-700' : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          <Clock className="w-4 h-4" /> Processing History
        </button>
      </div>

      {/* Tab 1: Extracted Pages */}
      {activeTab === 'pages' && (
        <div className="space-y-4">
          {pages.length === 0 ? (
            <div className="p-8 bg-white rounded border border-gray-200 text-center text-gray-500">
              No pages extracted for this document.
            </div>
          ) : (
            <div className="bg-white rounded border border-gray-200 shadow-sm overflow-hidden">
              {/* Page Navigator */}
              <div className="p-3 bg-gray-50 border-b border-gray-200 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setSelectedPageIndex(Math.max(0, selectedPageIndex - 1))}
                    disabled={selectedPageIndex === 0}
                    className="p-1.5 rounded border border-gray-300 hover:bg-gray-100 disabled:opacity-40"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  <span className="text-xs font-semibold text-gray-700">
                    Page {selectedPageIndex + 1} of {pages.length}
                  </span>
                  <button
                    onClick={() => setSelectedPageIndex(Math.min(pages.length - 1, selectedPageIndex + 1))}
                    disabled={selectedPageIndex === pages.length - 1}
                    className="p-1.5 rounded border border-gray-300 hover:bg-gray-100 disabled:opacity-40"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>

                {/* Page Status Badges */}
                {selectedPage && (
                  <div className="flex items-center gap-2 text-xs">
                    <span className={`px-2 py-0.5 rounded font-semibold border ${
                      selectedPage.ocr_applied
                        ? 'bg-amber-100 text-amber-800 border-amber-300'
                        : 'bg-emerald-100 text-emerald-800 border-emerald-300'
                    }`}>
                      {selectedPage.ocr_applied ? 'OCR Applied' : 'Native Digital Parser'}
                    </span>
                    <span className="px-2 py-0.5 rounded font-mono bg-gray-100 text-gray-700 border border-gray-300">
                      Confidence: {selectedPage.confidence_score ? (selectedPage.confidence_score * 100).toFixed(0) + '%' : '100%'}
                    </span>
                    {selectedPage.width && selectedPage.height && (
                      <span className="text-gray-500 font-mono">
                        {selectedPage.width}x{selectedPage.height} pt
                      </span>
                    )}
                  </div>
                )}
              </div>

              {/* Page Text Viewer */}
              <div className="p-6">
                {selectedPage ? (
                  <pre className="whitespace-pre-wrap font-sans text-sm text-gray-800 leading-relaxed bg-gray-50/70 p-4 rounded border border-gray-200 overflow-x-auto select-text">
                    {selectedPage.extracted_text || '(No text extracted on this page)'}
                  </pre>
                ) : (
                  <div className="text-sm text-gray-500">Select a page to inspect extracted content.</div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Extracted Tables */}
      {activeTab === 'tables' && (
        <div className="space-y-6">
          {/* Table View Presentation Switcher */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-gray-50 border border-gray-200 rounded p-3">
            <div>
              <span className="text-xs font-bold text-gray-700 uppercase tracking-wider block">
                Table Presentation Mode
              </span>
              <p className="text-xs text-gray-500">
                {tableView === 'logical'
                  ? 'Logical View: Multi-page continuous tables are merged seamlessly with row-level page provenance.'
                  : 'Physical View: Inspect each raw physical table instance on its exact source page.'}
              </p>
            </div>
            <div className="inline-flex rounded-md shadow-sm border border-gray-300 p-0.5 bg-white self-start sm:self-auto">
              <button
                onClick={() => { setTableView('logical'); fetchTables('logical'); }}
                className={`px-3 py-1.5 text-xs font-semibold rounded transition-colors ${
                  tableView === 'logical' ? 'bg-blue-600 text-white shadow-xs' : 'text-gray-700 hover:bg-gray-100'
                }`}
              >
                Logical View (Unified)
              </button>
              <button
                onClick={() => { setTableView('physical'); fetchTables('physical'); }}
                className={`px-3 py-1.5 text-xs font-semibold rounded transition-colors ${
                  tableView === 'physical' ? 'bg-blue-600 text-white shadow-xs' : 'text-gray-700 hover:bg-gray-100'
                }`}
              >
                Physical View (Raw Slices)
              </button>
            </div>
          </div>

          {tables.length === 0 ? (
            <div className="p-12 bg-white rounded border border-gray-200 text-center text-gray-500">
              <TableIcon className="w-10 h-10 text-gray-300 mx-auto mb-2" />
              <h3 className="text-base font-semibold text-gray-700">No Tables Detected</h3>
              <p className="text-xs text-gray-500 mt-1">
                No structured data grids or tables were extracted from this document.
              </p>
            </div>
          ) : (
            tables.map((table) => (
              <div key={table.id} className="bg-white rounded border border-gray-200 shadow-sm overflow-hidden">
                <div className="p-4 bg-gray-50 border-b border-gray-200 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div>
                    <div className="flex items-center gap-2 flex-wrap mb-1">
                      <h3 className="text-sm font-bold text-gray-900">
                        {table.caption || `Table ${table.table_index} (Page ${table.page_number})`}
                      </h3>
                      {table.total_parts && table.total_parts > 1 && (
                        <span className="text-[11px] font-bold px-2 py-0.5 bg-purple-100 text-purple-900 border border-purple-300 rounded">
                          {tableView === 'logical'
                            ? `Spans ${table.total_parts} Pages (${table.page_label || `Parts 1–${table.total_parts}`})`
                            : `Part ${table.part_number} of ${table.total_parts}`}
                        </span>
                      )}
                      {table.continuation_status === 'AUTO_MERGED' && (
                        <span className="text-[11px] font-semibold px-2 py-0.5 bg-blue-100 text-blue-800 border border-blue-300 rounded">
                          Multi-Page Continuation (Confidence: {((table.continuation_confidence || 1.0) * 100).toFixed(0)}%)
                        </span>
                      )}
                      {table.continuation_status === 'REVIEW_REQUIRED' && (
                        <span className="text-[11px] font-semibold px-2 py-0.5 bg-amber-100 text-amber-800 border border-amber-300 rounded">
                          Ambiguous Continuation • Verification Required
                        </span>
                      )}
                      {table.has_repeated_headers && (
                        <span className="text-[11px] font-semibold px-2 py-0.5 bg-teal-100 text-teal-800 border border-teal-300 rounded">
                          Repeated Header Normalized
                        </span>
                      )}
                    </div>
                    <span className="text-xs text-gray-500 font-mono">
                      {tableView === 'logical' ? (table.page_label || `Page ${table.page_number}`) : `Page ${table.page_number}`}
                      {` • ${table.row_count} rows × ${table.col_count} columns`}
                      {table.logical_table_id && ` • Logical ID: ${table.logical_table_id.substring(0, 8)}...`}
                    </span>
                    {/* Slice Composition Pills for Logical View */}
                    {tableView === 'logical' && table.physical_slices && table.physical_slices.length > 1 && (
                      <div className="flex items-center gap-1.5 mt-2 flex-wrap text-[11px]">
                        <span className="text-gray-500 font-medium">Physical Slices:</span>
                        {table.physical_slices.map((slice, sIdx) => (
                          <span
                            key={slice.id}
                            className="px-2 py-0.5 bg-white border border-gray-300 rounded text-gray-700 font-mono text-[10px]"
                          >
                            Part {slice.part_number}: Page {slice.page_number} ({slice.row_count} rows)
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                  <span className="text-xs font-semibold px-2 py-0.5 bg-emerald-100 text-emerald-800 border border-emerald-300 rounded self-start sm:self-auto">
                    Structure Preserved
                  </span>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="bg-gray-100 border-b border-gray-300 text-gray-800 font-bold uppercase tracking-wider">
                        <th className="py-2.5 px-2.5 w-12 text-center border-r border-gray-200 text-gray-500">
                          #
                        </th>
                        <th className="py-2.5 px-2 w-16 text-center border-r border-gray-200 text-gray-500">
                          Src Page
                        </th>
                        {table.headers.map((h, hIdx) => (
                          <th key={hIdx} className="py-2.5 px-3 border-r border-gray-200 last:border-r-0">
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200 font-mono">
                      {table.rows.map((row, rIdx) => {
                        const detail = table.row_details && table.row_details[rIdx];
                        const logRowIdx = detail?.logical_row_index ?? (rIdx + 1);
                        const srcPage = detail?.source_page ?? table.page_number;
                        return (
                          <tr key={rIdx} className="hover:bg-blue-50/50">
                            <td className="py-2 px-2.5 text-center border-r border-gray-100 text-gray-400 font-mono">
                              {logRowIdx}
                            </td>
                            <td className="py-2 px-2 text-center border-r border-gray-100">
                              <span className="inline-block px-1.5 py-0.5 bg-gray-100 text-gray-700 text-[10px] font-bold rounded border border-gray-200">
                                P.{srcPage}
                              </span>
                            </td>
                            {row.map((cell, cIdx) => (
                              <td key={cIdx} className="py-2 px-3 border-r border-gray-100 last:border-r-0 text-gray-700">
                                {cell || '—'}
                              </td>
                            ))}
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Tab: Figures (Phase 9 — Visual & Figure Intelligence) */}
      {activeTab === 'figures' && (
        <div className="space-y-4">
          {visuals.length === 0 ? (
            <div className="p-8 bg-white rounded border border-gray-200 text-center text-gray-500">
              No visual assets detected in this document.
            </div>
          ) : (
            <>
              <div className="text-xs text-gray-600 bg-amber-50 border border-amber-200 rounded p-3">
                <strong>Visual &amp; Figure Intelligence:</strong> Detected figures, charts, maps, and technical drawings are extracted with deterministic heuristics. Classification may be UNKNOWN when evidence is insufficient — this is the correct safe output.
              </div>
              <div className="bg-white rounded border border-gray-200 shadow-sm overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 border-b">
                    <tr>
                      <th className="text-left px-4 py-3 font-semibold text-gray-700">Figure</th>
                      <th className="text-left px-4 py-3 font-semibold text-gray-700">Type</th>
                      <th className="text-left px-4 py-3 font-semibold text-gray-700">Caption</th>
                      <th className="text-center px-4 py-3 font-semibold text-gray-700">Page</th>
                      <th className="text-center px-4 py-3 font-semibold text-gray-700">Confidence</th>
                      <th className="text-center px-4 py-3 font-semibold text-gray-700">Status</th>
                      <th className="text-center px-4 py-3 font-semibold text-gray-700">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {visuals.map((v, idx) => (
                      <tr key={v.id} className={idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                        <td className="px-4 py-3 font-medium text-gray-800">
                          {v.figure_number || <span className="text-gray-400 italic">—</span>}
                        </td>
                        <td className="px-4 py-3">
                          <span className={`inline-block px-2 py-0.5 rounded text-xs font-semibold ${
                            v.visual_type === 'UNKNOWN' ? 'bg-gray-100 text-gray-600' :
                            v.visual_type === 'MAP' ? 'bg-green-100 text-green-800' :
                            v.visual_type === 'CHART' || v.visual_type === 'PLOT' ? 'bg-blue-100 text-blue-800' :
                            v.visual_type === 'PHOTOGRAPH' ? 'bg-purple-100 text-purple-800' :
                            v.visual_type === 'BOREHOLE_LOG' ? 'bg-yellow-100 text-yellow-800' :
                            'bg-orange-100 text-orange-800'
                          }`}>
                            {v.visual_type.replace(/_/g, ' ')}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-gray-600 max-w-xs truncate" title={v.caption || ''}>
                          {v.caption || <span className="text-gray-400 italic">No caption detected</span>}
                        </td>
                        <td className="px-4 py-3 text-center text-gray-700">{v.page_number}</td>
                        <td className="px-4 py-3 text-center">
                          <span className={`text-xs font-semibold ${
                            v.classification_confidence >= 0.7 ? 'text-green-700' :
                            v.classification_confidence >= 0.4 ? 'text-yellow-700' : 'text-red-600'
                          }`}>
                            {(v.classification_confidence * 100).toFixed(0)}%
                          </span>
                        </td>
                        <td className="px-4 py-3 text-center">
                          <span className={`inline-block px-2 py-0.5 rounded text-xs font-semibold ${
                            v.verification_status === 'VERIFIED' ? 'bg-green-100 text-green-800' :
                            v.verification_status === 'REVIEW_REQUIRED' ? 'bg-red-100 text-red-700' :
                            v.verification_status === 'REJECTED' ? 'bg-gray-200 text-gray-600' :
                            'bg-yellow-100 text-yellow-700'
                          }`}>
                            {v.verification_status.replace(/_/g, ' ')}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-center space-x-2">
                          <button onClick={() => setSelectedVisual(v)} className="text-xs bg-blue-600 text-white px-2 py-1 rounded hover:bg-blue-700" title="View figure detail">
                            <Eye className="w-3 h-3 inline mr-1" />View
                          </button>
                          <button
                            onClick={() => {
                              const pageIdx = pages.findIndex(p => p.page_number === v.page_number);
                              if (pageIdx >= 0) { setSelectedPageIndex(pageIdx); setActiveTab('pages'); }
                            }}
                            className="text-xs bg-gray-600 text-white px-2 py-1 rounded hover:bg-gray-700" title="View source page"
                          >
                            Source
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      )}

      {/* Visual Detail Modal */}
      {selectedVisual && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setSelectedVisual(null)}>
          <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto p-6" onClick={e => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-bold text-gray-800">
                {selectedVisual.figure_number || 'Visual Asset'}
                <span className="ml-2 text-sm font-normal text-gray-500">({selectedVisual.visual_type.replace(/_/g, ' ')})</span>
              </h3>
              <button onClick={() => setSelectedVisual(null)} className="text-gray-400 hover:text-gray-600 text-xl font-bold">&times;</button>
            </div>
            <div className="mb-4 bg-gray-100 rounded border flex items-center justify-center p-2 min-h-[200px]">
              <img
                src={`/api/v1/visuals/${selectedVisual.id}/content${localStorage.getItem('token') ? `?token=${encodeURIComponent(localStorage.getItem('token') || '')}` : ''}`}
                alt={selectedVisual.caption || 'Extracted visual'}
                className="max-w-full max-h-[400px] object-contain"
              />
            </div>
            <div className="grid grid-cols-2 gap-3 text-sm mb-4">
              <div><span className="text-gray-500">Type:</span> <span className="font-semibold">{selectedVisual.visual_type.replace(/_/g, ' ')}</span></div>
              <div><span className="text-gray-500">Page:</span> <span className="font-semibold">{selectedVisual.page_number}</span></div>
              <div><span className="text-gray-500">Classification Confidence:</span> <span className="font-semibold">{(selectedVisual.classification_confidence * 100).toFixed(1)}%</span></div>
              <div><span className="text-gray-500">Extraction:</span> <span className="font-semibold">{selectedVisual.extraction_method}</span></div>
              <div><span className="text-gray-500">Dimensions:</span> <span className="font-semibold">{selectedVisual.width_px}&times;{selectedVisual.height_px} px</span></div>
              <div><span className="text-gray-500">Status:</span>
                <span className={`ml-1 inline-block px-2 py-0.5 rounded text-xs font-semibold ${
                  selectedVisual.verification_status === 'VERIFIED' ? 'bg-green-100 text-green-800' :
                  selectedVisual.verification_status === 'REVIEW_REQUIRED' ? 'bg-red-100 text-red-700' : 'bg-yellow-100 text-yellow-700'
                }`}>{selectedVisual.verification_status.replace(/_/g, ' ')}</span>
              </div>
              {selectedVisual.ocr_confidence !== null && (
                <div><span className="text-gray-500">OCR Confidence:</span> <span className="font-semibold">{(selectedVisual.ocr_confidence * 100).toFixed(1)}%</span></div>
              )}
              <div><span className="text-gray-500">Hash:</span> <span className="font-mono text-xs">{selectedVisual.image_hash?.substring(0, 16)}…</span></div>
            </div>
            {selectedVisual.caption && (
              <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded">
                <div className="text-xs font-semibold text-blue-700 mb-1">Caption</div>
                <div className="text-sm text-gray-800">{selectedVisual.caption}</div>
              </div>
            )}
            {selectedVisual.bbox && (
              <div className="mb-4 p-3 bg-gray-50 border rounded">
                <div className="text-xs font-semibold text-gray-600 mb-1">Bounding Region (PDF Points)</div>
                <div className="text-xs font-mono text-gray-700">
                  x0={selectedVisual.bbox.x0.toFixed(1)}, y0={selectedVisual.bbox.y0.toFixed(1)}, x1={selectedVisual.bbox.x1.toFixed(1)}, y1={selectedVisual.bbox.y1.toFixed(1)}
                </div>
              </div>
            )}
            <div className="flex gap-2 mt-4">
              <button
                onClick={() => {
                  const pageIdx = pages.findIndex(p => p.page_number === selectedVisual.page_number);
                  if (pageIdx >= 0) { setSelectedPageIndex(pageIdx); setActiveTab('pages'); setSelectedVisual(null); }
                }}
                className="px-4 py-2 bg-gray-700 text-white rounded text-sm hover:bg-gray-800"
              >View Source Page</button>
              <button onClick={() => setSelectedVisual(null)} className="px-4 py-2 bg-gray-200 text-gray-700 rounded text-sm hover:bg-gray-300">Close</button>
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: Structure Chunks */}
      {activeTab === 'chunks' && (
        <div className="space-y-4">
          <div className="text-xs text-gray-600 bg-blue-50 border border-blue-200 rounded p-3">
            <strong>Structure-Preserving Chunking:</strong> Tables are preserved intact with column headers replicated across batches, ensuring semantic vector embeddings and LLM retrieval retain full tabular context.
          </div>

          {chunks.map((chunk) => (
            <div key={chunk.id} className="bg-white rounded border border-gray-200 p-4 shadow-sm space-y-2">
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <span className="font-mono font-bold px-2 py-0.5 bg-gray-100 rounded border border-gray-300 text-gray-700">
                    Chunk #{chunk.chunk_index}
                  </span>
                  <span className={`font-semibold px-2 py-0.5 rounded border ${
                    chunk.chunk_type === 'TABLE'
                      ? 'bg-purple-100 text-purple-800 border-purple-300'
                      : 'bg-blue-100 text-blue-800 border-blue-300'
                  }`}>
                    {chunk.chunk_type}
                  </span>
                  {chunk.page_number && (
                    <span className="text-gray-500 font-mono">Page {chunk.page_number}</span>
                  )}
                </div>
                {chunk.section_heading && (
                  <span className="text-gray-600 font-medium truncate max-w-sm">
                    {chunk.section_heading}
                  </span>
                )}
              </div>

              <pre className="whitespace-pre-wrap font-mono text-xs bg-gray-50 p-3 rounded border border-gray-200 text-gray-800 overflow-x-auto">
                {chunk.content}
              </pre>
            </div>
          ))}
        </div>
      )}

      {/* Tab: Structured Fields Extraction */}
      {activeTab === 'extraction' && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-4 rounded border border-gray-200 shadow-sm">
            <div>
              <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-blue-600" />
                Structured Machine-Extracted Fields ({fields.length})
              </h3>
              <p className="text-xs text-gray-500 mt-0.5">
                Domain values extracted from tables and text with physical source-page provenance.
              </p>
            </div>
            <button
              onClick={handleRunExtraction}
              disabled={isExtracting}
              className="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs font-semibold flex items-center gap-1.5 transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isExtracting ? 'animate-spin' : ''}`} />
              {isExtracting ? 'Extracting...' : 'Re-run Extraction'}
            </button>
          </div>

          {fields.length === 0 ? (
            <div className="p-12 bg-white rounded border border-gray-200 text-center space-y-3">
              <CheckCircle className="w-8 h-8 text-gray-400 mx-auto" />
              <p className="text-sm font-semibold text-gray-700">No structured fields extracted yet.</p>
              <p className="text-xs text-gray-500 max-w-md mx-auto">
                Trigger the deterministic extraction and domain validation pipeline to parse identification, geological, and mining metrics.
              </p>
              <button
                onClick={handleRunExtraction}
                disabled={isExtracting}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs font-bold transition-colors"
              >
                Run Structured Extraction Pipeline
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {fields.map((f) => {
                let confColor = 'bg-emerald-50 text-emerald-700 border-emerald-200';
                if (f.confidence_level === 'MEDIUM') confColor = 'bg-amber-50 text-amber-700 border-amber-200';
                else if (f.confidence_level === 'LOW') confColor = 'bg-red-50 text-red-700 border-red-200';

                let valColor = 'bg-emerald-50 text-emerald-700 border-emerald-200';
                if (f.validation_status === 'WARNING') valColor = 'bg-amber-50 text-amber-700 border-amber-200';
                else if (f.validation_status === 'ERROR') valColor = 'bg-red-50 text-red-700 border-red-200';

                return (
                  <div key={f.id} className="bg-white rounded border border-gray-200 p-4 shadow-sm space-y-3 flex flex-col justify-between">
                    <div className="space-y-2">
                      <div className="flex items-start justify-between gap-2">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
                          {f.field_category}
                        </span>
                        <div className="flex items-center gap-1">
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${confColor}`}>
                            {Math.round(f.confidence_score * 100)}% {f.confidence_level}
                          </span>
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${valColor}`}>
                            {f.validation_status}
                          </span>
                        </div>
                      </div>

                      <div>
                        <h4 className="text-xs font-bold text-gray-900 font-mono">
                          {f.field_name}
                        </h4>
                        <div className="mt-1">
                          {f.is_corrected ? (
                            <div>
                              <span className="text-xs line-through text-gray-400 mr-2">{f.raw_value}</span>
                              <span className="text-base font-bold text-blue-700 font-mono">{f.corrected_value}</span>
                              <span className="text-xs text-gray-500 ml-1">{f.unit || ''}</span>
                              <span className="block text-[10px] text-blue-600 font-semibold mt-0.5">Verified Corrected</span>
                            </div>
                          ) : (
                            <div className="flex items-baseline gap-1">
                              <span className="text-base font-bold text-gray-900 font-mono">{f.raw_value}</span>
                              {f.unit && <span className="text-xs font-semibold text-gray-600">{f.unit}</span>}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="pt-3 border-t border-gray-100 space-y-2">
                      <div className="flex items-center justify-between text-[11px] text-gray-600">
                        <span className="flex items-center gap-1 font-semibold text-blue-700">
                          <FileText className="w-3.5 h-3.5" />
                          Physical Page {f.page_number || 'N/A'}
                        </span>
                        <span className="font-mono text-gray-500">
                          {f.table_id ? `Table #${f.table_id.slice(0, 6)}` : 'Text Block'}
                        </span>
                      </div>

                      <button
                        onClick={() => setEvidenceModalField(f)}
                        className="w-full py-1 text-center text-xs font-semibold text-blue-600 hover:text-blue-800 bg-blue-50 hover:bg-blue-100 rounded transition-colors flex items-center justify-center gap-1"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        Inspect Provenance
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Tab: Validation Rules */}
      {activeTab === 'validation' && (
        <div className="space-y-4">
          <div className="bg-white p-4 rounded border border-gray-200 shadow-sm">
            <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-600" />
              Automated Domain Validation Results
            </h3>
            <p className="text-xs text-gray-500 mt-0.5">
              Deterministic rule checks for physical range bounds, unit consistency, type compliance, and fiscal periods.
            </p>
          </div>

          <div className="bg-white rounded border border-gray-200 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead className="bg-gray-50 border-b border-gray-200 text-gray-700 font-semibold uppercase tracking-wider">
                  <tr>
                    <th className="py-3 px-4">Field</th>
                    <th className="py-3 px-4">Rule Name</th>
                    <th className="py-3 px-4">Category</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Severity</th>
                    <th className="py-3 px-4">Expected</th>
                    <th className="py-3 px-4">Observed</th>
                    <th className="py-3 px-4">Message</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {fields.flatMap((f) =>
                    (f.validation_results || []).map((vr) => {
                      let sColor = 'text-green-700 bg-green-50';
                      if (vr.status === 'WARNING') sColor = 'text-amber-700 bg-amber-50';
                      else if (vr.status === 'ERROR') sColor = 'text-red-700 bg-red-50';

                      return (
                        <tr key={vr.id} className="hover:bg-gray-50/80">
                          <td className="py-2.5 px-4 font-mono font-bold text-gray-800">{f.field_name}</td>
                          <td className="py-2.5 px-4 font-semibold text-gray-700">{vr.rule_name}</td>
                          <td className="py-2.5 px-4 text-gray-600">{vr.rule_category}</td>
                          <td className="py-2.5 px-4">
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${sColor}`}>
                              {vr.status}
                            </span>
                          </td>
                          <td className="py-2.5 px-4 font-semibold text-gray-600">{vr.severity}</td>
                          <td className="py-2.5 px-4 font-mono text-gray-600">{vr.expected_constraint || 'N/A'}</td>
                          <td className="py-2.5 px-4 font-mono font-semibold text-gray-800">{vr.observed_value || 'N/A'}</td>
                          <td className="py-2.5 px-4 text-gray-700">{vr.message}</td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Tab 4: Metadata & Provenance */}
      {activeTab === 'metadata' && (
        <div className="bg-white rounded border border-gray-200 p-6 shadow-sm space-y-6">
          <div>
            <h3 className="text-base font-bold text-gray-900 mb-4">Document Metadata</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div className="p-3 bg-gray-50 rounded border border-gray-200 space-y-1">
                <span className="text-gray-500 block">Document ID</span>
                <span className="font-mono font-bold text-gray-800">{document.id}</span>
              </div>
              <div className="p-3 bg-gray-50 rounded border border-gray-200 space-y-1">
                <span className="text-gray-500 block">Organization</span>
                <span className="font-semibold text-gray-800">
                  {document.organization_code} — {document.organization_name}
                </span>
              </div>
              <div className="p-3 bg-gray-50 rounded border border-gray-200 space-y-1">
                <span className="text-gray-500 block">MIME Type</span>
                <span className="font-mono text-gray-800">{document.mime_type}</span>
              </div>
              <div className="p-3 bg-gray-50 rounded border border-gray-200 space-y-1">
                <span className="text-gray-500 block">File Size</span>
                <span className="font-mono text-gray-800">{(document.file_size_bytes / 1024).toFixed(2)} KB</span>
              </div>
              <div className="p-3 bg-gray-50 rounded border border-gray-200 space-y-1">
                <span className="text-gray-500 block">Ingested At</span>
                <span className="text-gray-800">{new Date(document.created_at).toLocaleString()}</span>
              </div>
              <div className="p-3 bg-gray-50 rounded border border-gray-200 space-y-1">
                <span className="text-gray-500 block">Last Updated</span>
                <span className="text-gray-800">{new Date(document.updated_at).toLocaleString()}</span>
              </div>
            </div>
          </div>

          {/* Versions */}
          {document.versions && document.versions.length > 0 && (
            <div>
              <h3 className="text-sm font-bold text-gray-900 mb-3">Document Version Lineage</h3>
              <div className="space-y-2">
                {document.versions.map((v) => (
                  <div key={v.id} className="p-3 bg-gray-50 rounded border border-gray-200 flex items-center justify-between text-xs">
                    <div>
                      <span className="font-bold text-gray-800">Version {v.version_number}</span>
                      {v.supersedes_id && (
                        <span className="text-gray-500 ml-2 font-mono">(Supersedes: {v.supersedes_id})</span>
                      )}
                    </div>
                    <span className="font-mono text-gray-500 truncate max-w-xs">{v.sha256_hash}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab 5: Processing History */}
      {activeTab === 'job' && (
        <div className="bg-white rounded border border-gray-200 p-6 shadow-sm space-y-4">
          <h3 className="text-base font-bold text-gray-900">Ingestion Job Record</h3>
          {document.latest_job ? (
            <div className="p-4 bg-gray-50 rounded border border-gray-200 space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <span className="text-gray-500 block">Job ID</span>
                  <span className="font-mono font-bold text-gray-800">{document.latest_job.id}</span>
                </div>
                <div>
                  <span className="text-gray-500 block">Status</span>
                  <span className="font-bold text-emerald-700">{document.latest_job.status}</span>
                </div>
                <div>
                  <span className="text-gray-500 block">Progress</span>
                  <span className="font-mono font-bold text-blue-700">{document.latest_job.progress_pct}%</span>
                </div>
                <div>
                  <span className="text-gray-500 block">Errors</span>
                  <span className="text-gray-800">{document.latest_job.error_message || 'None (Clean Execution)'}</span>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-sm text-gray-500">No processing job log found.</div>
          )}
        </div>
      )}
      {/* Provenance Inspection Modal */}
      {evidenceModalField && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl overflow-hidden">
            <div className="bg-slate-900 text-white px-5 py-3.5 flex items-center justify-between">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-blue-400">Field Provenance Inspector</span>
                <h3 className="text-sm font-bold font-mono">{evidenceModalField.field_name}</h3>
              </div>
              <button
                onClick={() => setEvidenceModalField(null)}
                className="text-slate-400 hover:text-white text-base font-bold px-2 py-1"
              >
                ✕
              </button>
            </div>

            <div className="p-5 space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-3 bg-gray-50 p-3 rounded border border-gray-200">
                <div>
                  <span className="text-gray-500 block font-semibold">Physical Source Page</span>
                  <span className="font-bold text-blue-700">Page {evidenceModalField.page_number || 'N/A'}</span>
                </div>
                <div>
                  <span className="text-gray-500 block font-semibold">Extracted Value & Unit</span>
                  <span className="font-bold font-mono text-gray-900">{evidenceModalField.raw_value} {evidenceModalField.unit || ''}</span>
                </div>
                <div>
                  <span className="text-gray-500 block font-semibold">Extraction Confidence</span>
                  <span className="font-semibold text-emerald-700">{Math.round(evidenceModalField.confidence_score * 100)}% ({evidenceModalField.confidence_level})</span>
                </div>
                <div>
                  <span className="text-gray-500 block font-semibold">Validation Status</span>
                  <span className="font-semibold text-gray-900">{evidenceModalField.validation_status}</span>
                </div>
              </div>

              <div>
                <span className="text-gray-700 font-bold block mb-1">Source Snippet / Context</span>
                <div className="p-3 bg-slate-900 text-slate-100 rounded font-mono text-xs whitespace-pre-wrap max-h-48 overflow-y-auto">
                  {evidenceModalField.source_text || 'Exact context snippet captured from primary document stream.'}
                </div>
              </div>

              {evidenceModalField.validation_results && evidenceModalField.validation_results.length > 0 && (
                <div>
                  <span className="text-gray-700 font-bold block mb-1">Applied Validation Rules</span>
                  <div className="space-y-1">
                    {evidenceModalField.validation_results.map((vr) => (
                      <div key={vr.id} className="p-2 rounded border bg-gray-50 flex justify-between items-center text-[11px]">
                        <div>
                          <span className="font-bold text-gray-800">{vr.rule_name}</span>
                          <span className="text-gray-500 ml-2">({vr.message})</span>
                        </div>
                        <span className={`px-2 py-0.5 rounded font-bold text-[10px] ${
                          vr.status === 'PASS' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                        }`}>
                          {vr.status}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="pt-3 border-t border-gray-200 flex justify-end">
                <button
                  onClick={() => setEvidenceModalField(null)}
                  className="px-4 py-1.5 bg-gray-800 text-white rounded text-xs font-semibold hover:bg-gray-900"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
