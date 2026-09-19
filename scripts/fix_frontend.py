import os

doc_list_code = """import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { apiClient } from '../api/client';
import { FileText, FileSpreadsheet, Image as ImageIcon, Upload, Search, Filter, CheckCircle2, Clock, AlertTriangle, ArrowRight } from 'lucide-react';

interface DocumentItem {
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
  created_at: string;
}

interface Organization {
  id: string;
  code: string;
  name: string;
}

export const DocumentList: React.FC = () => {
  const navigate = useNavigate();
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedOrg, setSelectedOrg] = useState('');
  const [selectedType, setSelectedType] = useState('');
  const [selectedTier, setSelectedTier] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');

  const fetchOrganizations = async () => {
    try {
      const res = await apiClient.get('/organizations/');
      setOrganizations(res.data);
    } catch (err) {
      console.error('Failed to load organizations', err);
    }
  };

  const fetchDocuments = async () => {
    try {
      setLoading(true);
      const params: any = {};
      if (selectedOrg) params.organization_id = selectedOrg;
      if (selectedType) params.document_type = selectedType;
      if (selectedTier) params.source_tier = selectedTier;
      if (selectedStatus) params.status = selectedStatus;
      if (searchTerm) params.search = searchTerm;

      const res = await apiClient.get('/documents/', { params });
      setDocuments(res.data.items);
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load documents');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrganizations();
  }, []);

  useEffect(() => {
    fetchDocuments();
  }, [selectedOrg, selectedType, selectedTier, selectedStatus]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchDocuments();
  };

  const renderFileIcon = (mime: string) => {
    if (mime.includes('pdf')) return <FileText className="w-5 h-5 text-red-500" />;
    if (mime.includes('spreadsheet') || mime.includes('excel')) return <FileSpreadsheet className="w-5 h-5 text-emerald-600" />;
    if (mime.includes('wordprocessingml')) return <FileText className="w-5 h-5 text-blue-600" />;
    if (mime.includes('image')) return <ImageIcon className="w-5 h-5 text-amber-500" />;
    return <FileText className="w-5 h-5 text-gray-500" />;
  };

  const renderTierBadge = (tier: string) => {
    if (tier === 'TIER_A') {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-300">
          Tier A • Authoritative
        </span>
      );
    }
    if (tier === 'TIER_B') {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-blue-100 text-blue-800 border border-blue-300">
          Tier B • Operational
        </span>
      );
    }
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-300">
        Tier C • Unverified
      </span>
    );
  };

  const renderStatusBadge = (status: string) => {
    switch (status) {
      case 'COMPLETED':
        return (
          <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-700 bg-emerald-50 px-2 py-1 rounded border border-emerald-200">
            <CheckCircle2 className="w-3.5 h-3.5" /> Processed
          </span>
        );
      case 'PROCESSING':
        return (
          <span className="inline-flex items-center gap-1 text-xs font-medium text-blue-700 bg-blue-50 px-2 py-1 rounded border border-blue-200 animate-pulse">
            <Clock className="w-3.5 h-3.5" /> Processing
          </span>
        );
      case 'QUEUED':
        return (
          <span className="inline-flex items-center gap-1 text-xs font-medium text-gray-700 bg-gray-100 px-2 py-1 rounded border border-gray-300">
            <Clock className="w-3.5 h-3.5" /> Queued
          </span>
        );
      case 'FAILED':
        return (
          <span className="inline-flex items-center gap-1 text-xs font-medium text-red-700 bg-red-50 px-2 py-1 rounded border border-red-200">
            Failed
          </span>
        );
      default:
        return <span className="text-xs text-gray-500">{status}</span>;
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-gray-200 pb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Document Intelligence Repository</h1>
          <p className="text-sm text-gray-600 mt-1">
            Central repository of multi-format geological reports, borehole logs, mine production schedules, and statutory filings.
          </p>
        </div>
        <Link
          to="/upload"
          className="inline-flex items-center gap-2 bg-blue-700 hover:bg-blue-800 text-white text-sm font-semibold px-4 py-2.5 rounded shadow-sm transition-colors"
        >
          <Upload className="w-4 h-4" /> Ingest New Document
        </Link>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-white p-4 rounded border border-gray-200 shadow-sm space-y-3">
        <div className="flex items-center gap-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">
          <Filter className="w-3.5 h-3.5" /> Filters & Scopes
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {/* Search */}
          <form onSubmit={handleSearchSubmit} className="relative">
            <input
              type="text"
              placeholder="Search title or file..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full text-sm pl-9 pr-3 py-1.5 border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 focus:outline-none"
            />
            <Search className="w-4 h-4 text-gray-400 absolute left-2.5 top-2.5" />
          </form>

          {/* Organization */}
          <select
            value={selectedOrg}
            onChange={(e) => setSelectedOrg(e.target.value)}
            className="text-sm px-3 py-1.5 border border-gray-300 rounded bg-white focus:ring-1 focus:ring-blue-500 focus:outline-none"
          >
            <option value="">All Organizations</option>
            {organizations.map((org) => (
              <option key={org.id} value={org.id}>
                {org.code} - {org.name}
              </option>
            ))}
          </select>

          {/* Document Type */}
          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
            className="text-sm px-3 py-1.5 border border-gray-300 rounded bg-white focus:ring-1 focus:ring-blue-500 focus:outline-none"
          >
            <option value="">All Document Types</option>
            <option value="GEOLOGICAL_REPORT">Geological Report</option>
            <option value="MINE_PRODUCTION">Mine Production Schedule</option>
            <option value="SAFETY_AUDIT">Mine Safety Inspection</option>
            <option value="EXPLORATION_DATA">Exploration Data</option>
            <option value="BOREHOLE_LOG">Borehole Core Log</option>
          </select>

          {/* Source Tier */}
          <select
            value={selectedTier}
            onChange={(e) => setSelectedTier(e.target.value)}
            className="text-sm px-3 py-1.5 border border-gray-300 rounded bg-white focus:ring-1 focus:ring-blue-500 focus:outline-none"
          >
            <option value="">All Trust Tiers</option>
            <option value="TIER_A">Tier A (Authoritative)</option>
            <option value="TIER_B">Tier B (Operational)</option>
            <option value="TIER_C">Tier C (Unverified)</option>
          </select>

          {/* Status */}
          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="text-sm px-3 py-1.5 border border-gray-300 rounded bg-white focus:ring-1 focus:ring-blue-500 focus:outline-none"
          >
            <option value="">All Processing Statuses</option>
            <option value="COMPLETED">Processed</option>
            <option value="PROCESSING">Processing</option>
            <option value="QUEUED">Queued</option>
            <option value="FAILED">Failed</option>
          </select>
        </div>
      </div>

      {/* Document Table */}
      <div className="bg-white rounded border border-gray-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-gray-500 flex flex-col items-center justify-center gap-2">
            <Clock className="w-6 h-6 animate-spin text-blue-600" />
            <span className="text-sm">Loading document repository...</span>
          </div>
        ) : error ? (
          <div className="p-8 text-center text-red-600">
            <AlertTriangle className="w-8 h-8 mx-auto mb-2 text-red-500" />
            <p className="font-semibold">{error}</p>
          </div>
        ) : documents.length === 0 ? (
          <div className="p-12 text-center text-gray-500">
            <FileText className="w-10 h-10 mx-auto mb-3 text-gray-300" />
            <h3 className="text-base font-semibold text-gray-800">No documents found</h3>
            <p className="text-sm text-gray-500 mt-1">
              No documents match your filter criteria or organization scope.
            </p>
            <Link
              to="/upload"
              className="inline-flex items-center gap-1.5 mt-4 text-sm font-semibold text-blue-600 hover:text-blue-800"
            >
              Upload your first document <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200 text-gray-700 font-semibold text-xs tracking-wider uppercase">
                  <th className="py-3 px-4">Document Title & File</th>
                  <th className="py-3 px-4">Organization</th>
                  <th className="py-3 px-4">Document Type</th>
                  <th className="py-3 px-4">Source Tier</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Ingested At</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {documents.map((doc) => (
                  <tr key={doc.id} className="hover:bg-blue-50/40 transition-colors">
                    <td className="py-3.5 px-4">
                      <div className="flex items-start gap-3">
                        <div className="mt-0.5 p-1.5 bg-gray-100 rounded border border-gray-200">
                          {renderFileIcon(doc.mime_type)}
                        </div>
                        <div>
                          <Link
                            to={`/documents/${doc.id}`}
                            className="font-semibold text-gray-900 hover:text-blue-700 block line-clamp-1"
                          >
                            {doc.title}
                          </Link>
                          <span className="text-xs text-gray-500 font-mono">
                            {doc.original_filename} ({(doc.file_size_bytes / 1024).toFixed(1)} KB)
                          </span>
                        </div>
                      </div>
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="inline-block font-mono text-xs font-semibold px-2 py-0.5 bg-gray-100 text-gray-800 rounded border border-gray-200">
                        {doc.organization_code || 'GLOBAL'}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-gray-600 text-xs font-medium">
                      {doc.document_type.replace('_', ' ')}
                    </td>
                    <td className="py-3.5 px-4">{renderTierBadge(doc.source_tier)}</td>
                    <td className="py-3.5 px-4">{renderStatusBadge(doc.status)}</td>
                    <td className="py-3.5 px-4 text-xs text-gray-500">
                      {doc.created_at ? new Date(doc.created_at).toLocaleString() : 'N/A'}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <Link
                        to={`/documents/${doc.id}`}
                        className="inline-flex items-center gap-1 text-xs font-semibold text-blue-700 hover:text-blue-900 bg-blue-50 hover:bg-blue-100 px-3 py-1.5 rounded border border-blue-200 transition-colors"
                      >
                        Inspect <ArrowRight className="w-3.5 h-3.5" />
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
  );
};
"""

doc_upload_code = """import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { apiClient } from '../api/client';
import { Upload, CheckCircle2, AlertCircle, ArrowRight, RefreshCw } from 'lucide-react';

interface Organization {
  id: string;
  code: string;
  name: string;
}

export const DocumentUpload: React.FC = () => {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [organizationId, setOrganizationId] = useState('');
  const [documentType, setDocumentType] = useState('GEOLOGICAL_REPORT');
  const [sourceTier, setSourceTier] = useState('TIER_B');
  const [dragOver, setDragOver] = useState(false);

  // Upload & processing state
  const [uploading, setUploading] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [documentId, setDocumentId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<string | null>(null);
  const [progressPct, setProgressPct] = useState<number>(0);
  const [sha256Hash, setSha256Hash] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    const fetchOrgs = async () => {
      try {
        const res = await apiClient.get('/organizations/');
        setOrganizations(res.data);
        if (res.data.length > 0) {
          setOrganizationId(res.data[0].id);
        }
      } catch (err) {
        console.error('Failed to load organizations', err);
      }
    };
    fetchOrgs();
  }, []);

  // Job polling
  useEffect(() => {
    let timer: any = null;
    if (jobId && (jobStatus === 'QUEUED' || jobStatus === 'PROCESSING')) {
      timer = setInterval(async () => {
        try {
          const res = await apiClient.get('/ingestion/jobs/' + jobId);
          setJobStatus(res.data.status);
          setProgressPct(res.data.progress_pct || 0);

          if (res.data.status === 'COMPLETED') {
            clearInterval(timer);
          } else if (res.data.status === 'FAILED') {
            clearInterval(timer);
            setErrorMessage(res.data.error_message || 'Processing job failed');
          }
        } catch (err: any) {
          clearInterval(timer);
          setErrorMessage(err.response?.data?.detail || 'Failed to check job status');
        }
      }, 1000);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [jobId, jobStatus]);

  const handleFileSelect = (file: File) => {
    const validExtensions = ['.pdf', '.docx', '.xlsx', '.xls', '.jpg', '.jpeg', '.png'];
    const ext = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!validExtensions.includes(ext)) {
      setErrorMessage(`Unsupported format '${ext}'. Allowed: PDF, DOCX, XLSX, XLS, JPG, PNG`);
      setSelectedFile(null);
      return;
    }
    setSelectedFile(file);
    setErrorMessage(null);
    if (!title) {
      setTitle(file.name.replace(/\\.[^/.]+$/, ''));
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setErrorMessage('Please select a file to ingest');
      return;
    }
    if (!organizationId) {
      setErrorMessage('Please select an authorized organization');
      return;
    }

    setUploading(true);
    setErrorMessage(null);
    setJobStatus('UPLOADING');
    setProgressPct(5);

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('organization_id', organizationId);
    formData.append('title', title);
    formData.append('document_type', documentType);
    formData.append('source_tier', sourceTier);

    try {
      const res = await apiClient.post('/documents/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      setDocumentId(res.data.id);
      setJobId(res.data.job_id);
      setSha256Hash(res.data.sha256_hash);
      setJobStatus('PROCESSING');
      setProgressPct(20);
    } catch (err: any) {
      setUploading(false);
      setJobStatus(null);
      setErrorMessage(err.response?.data?.detail || 'Document upload failed');
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    setTitle('');
    setUploading(false);
    setJobId(null);
    setDocumentId(null);
    setJobStatus(null);
    setProgressPct(0);
    setSha256Hash(null);
    setErrorMessage(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Breadcrumb & Title */}
      <div>
        <div className="flex items-center gap-2 text-xs text-gray-500 mb-1">
          <Link to="/documents" className="hover:underline">Documents</Link>
          <span>/</span>
          <span className="text-gray-800 font-semibold">Ingest Document</span>
        </div>
        <h1 className="text-2xl font-bold text-gray-900">Document Ingestion Studio</h1>
        <p className="text-sm text-gray-600 mt-1">
          Upload digital or scanned reports, production schedules, or boreholes. The pipeline executes native parsing, table preservation, and structure-preserving indexing.
        </p>
      </div>

      {errorMessage && (
        <div className="p-4 bg-red-50 border border-red-200 rounded flex items-start gap-3 text-red-800 text-sm">
          <AlertCircle className="w-5 h-5 flex-shrink-0 text-red-600 mt-0.5" />
          <div>
            <span className="font-bold">Error: </span>
            {errorMessage}
          </div>
        </div>
      )}

      {/* Upload Success Card */}
      {jobStatus === 'COMPLETED' && (
        <div className="bg-emerald-50 border border-emerald-300 rounded p-6 shadow-sm space-y-4">
          <div className="flex items-center gap-3 text-emerald-800 font-bold text-lg">
            <CheckCircle2 className="w-6 h-6 text-emerald-600" />
            Document Successfully Ingested & Processed
          </div>
          <p className="text-sm text-emerald-700">
            The document has been hashed, parsed, structure-extracted, and indexed into the PostgreSQL knowledge store.
          </p>
          <div className="bg-white p-3.5 rounded border border-emerald-200 text-xs font-mono text-gray-700 space-y-1">
            <div><strong>Document ID:</strong> {documentId}</div>
            <div><strong>SHA-256 Hash:</strong> {sha256Hash}</div>
          </div>
          <div className="flex items-center gap-3 pt-2">
            <Link
              to={`/documents/${documentId}`}
              className="inline-flex items-center gap-2 bg-emerald-700 hover:bg-emerald-800 text-white font-semibold text-sm px-4 py-2 rounded transition-colors"
            >
              Inspect Document & Tables <ArrowRight className="w-4 h-4" />
            </Link>
            <button
              onClick={handleReset}
              className="inline-flex items-center gap-1.5 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 text-sm font-semibold px-4 py-2 rounded transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" /> Ingest Another
            </button>
          </div>
        </div>
      )}

      {/* Processing Progress Card */}
      {uploading && jobStatus !== 'COMPLETED' && (
        <div className="bg-white border border-blue-200 rounded p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3 font-semibold text-gray-800">
              <RefreshCw className="w-5 h-5 text-blue-600 animate-spin" />
              <span>Processing Ingestion Pipeline ({jobStatus})...</span>
            </div>
            <span className="text-sm font-mono font-bold text-blue-700">{progressPct}%</span>
          </div>

          <div className="w-full bg-gray-200 rounded-full h-2.5 overflow-hidden">
            <div
              className="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
              style={{ width: `${progressPct}%` }}
            />
          </div>

          <div className="grid grid-cols-4 text-xs text-gray-500 pt-2 border-t border-gray-100 text-center">
            <div className={progressPct >= 10 ? 'text-blue-700 font-bold' : ''}>1. Validation & Hash</div>
            <div className={progressPct >= 30 ? 'text-blue-700 font-bold' : ''}>2. Native / OCR Parse</div>
            <div className={progressPct >= 60 ? 'text-blue-700 font-bold' : ''}>3. Table Extraction</div>
            <div className={progressPct >= 80 ? 'text-blue-700 font-bold' : ''}>4. Structure Chunking</div>
          </div>
        </div>
      )}

      {/* Upload Form */}
      {jobStatus !== 'COMPLETED' && !uploading && (
        <form onSubmit={handleSubmit} className="bg-white rounded border border-gray-200 shadow-sm p-6 space-y-6">
          {/* File Dropzone */}
          <div>
            <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-2">
              Select or Drop File
            </label>
            <div
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded p-8 text-center cursor-pointer transition-colors ${
                dragOver ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-blue-400 bg-gray-50/50'
              }`}
            >
              <input
                type="file"
                ref={fileInputRef}
                onChange={(e) => e.target.files && handleFileSelect(e.target.files[0])}
                className="hidden"
                accept=".pdf,.docx,.xlsx,.xls,.jpg,.jpeg,.png"
              />
              <Upload className="w-10 h-10 text-gray-400 mx-auto mb-3" />
              {selectedFile ? (
                <div className="space-y-1">
                  <p className="text-sm font-semibold text-gray-800">{selectedFile.name}</p>
                  <p className="text-xs text-gray-500 font-mono">
                    {(selectedFile.size / 1024).toFixed(1)} KB • {selectedFile.type || 'Unknown MIME'}
                  </p>
                  <button
                    type="button"
                    onClick={(e) => { e.stopPropagation(); setSelectedFile(null); }}
                    className="text-xs text-red-600 hover:underline mt-2 inline-block"
                  >
                    Remove file
                  </button>
                </div>
              ) : (
                <div className="space-y-1">
                  <p className="text-sm font-semibold text-gray-700">
                    Click to select or drag and drop document here
                  </p>
                  <p className="text-xs text-gray-500">
                    Supported: PDF, DOCX, XLSX, XLS, JPG, PNG (Max 50MB)
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Form Fields */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {/* Title */}
            <div>
              <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-1.5">
                Document Title (Optional)
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Jharia Coalfield Exploration Report"
                className="w-full text-sm px-3 py-2 border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 focus:outline-none"
              />
              <span className="text-xs text-gray-500">Leave blank to use original filename.</span>
            </div>

            {/* Organization Scope */}
            <div>
              <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-1.5">
                Target Organization Scope *
              </label>
              <select
                value={organizationId}
                onChange={(e) => setOrganizationId(e.target.value)}
                required
                className="w-full text-sm px-3 py-2 border border-gray-300 rounded bg-white focus:ring-1 focus:ring-blue-500 focus:outline-none"
              >
                {organizations.map((org) => (
                  <option key={org.id} value={org.id}>
                    {org.code} — {org.name}
                  </option>
                ))}
              </select>
              <span className="text-xs text-gray-500">Enforces server-side data isolation.</span>
            </div>

            {/* Document Type */}
            <div>
              <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-1.5">
                Document Classification *
              </label>
              <select
                value={documentType}
                onChange={(e) => setDocumentType(e.target.value)}
                className="w-full text-sm px-3 py-2 border border-gray-300 rounded bg-white focus:ring-1 focus:ring-blue-500 focus:outline-none"
              >
                <option value="GEOLOGICAL_REPORT">Geological Exploration Report</option>
                <option value="MINE_PRODUCTION">Mine Production Schedule</option>
                <option value="SAFETY_AUDIT">Mine Safety & DGMS Inspection</option>
                <option value="EXPLORATION_DATA">Exploration Block Data</option>
                <option value="BOREHOLE_LOG">Borehole Core Recovery Log</option>
              </select>
            </div>

            {/* Source Tier */}
            <div>
              <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-1.5">
                Source Trust Classification *
              </label>
              <select
                value={sourceTier}
                onChange={(e) => setSourceTier(e.target.value)}
                className="w-full text-sm px-3 py-2 border border-gray-300 rounded bg-white focus:ring-1 focus:ring-blue-500 focus:outline-none"
              >
                <option value="TIER_A">Tier A — Authoritative / Statutory Audit</option>
                <option value="TIER_B">Tier B — Internal Subsidiary Operational</option>
                <option value="TIER_C">Tier C — Unverified / External Reference</option>
              </select>
              <span className="text-xs text-gray-500">Configures grounding confidence weights.</span>
            </div>
          </div>

          {/* Submit Actions */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-200">
            <button
              type="button"
              onClick={() => navigate('/documents')}
              className="text-sm font-semibold text-gray-600 hover:text-gray-800 px-4 py-2"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!selectedFile || uploading}
              className="inline-flex items-center gap-2 bg-blue-700 hover:bg-blue-800 disabled:bg-gray-400 text-white text-sm font-semibold px-6 py-2.5 rounded shadow-sm transition-colors"
            >
              <Upload className="w-4 h-4" /> Ingest Document
            </button>
          </div>
        </form>
      )}
    </div>
  );
};
"""

doc_detail_code = """import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
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
  Hash
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

interface TableItem {
  id: string;
  page_number: number;
  table_index: number;
  caption: string;
  headers: string[];
  row_count: number;
  col_count: number;
  metadata: any;
  rows: string[][];
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

export const DocumentDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();

  const [document, setDocument] = useState<DocumentDetailData | null>(null);
  const [pages, setPages] = useState<DocumentPageItem[]>([]);
  const [tables, setTables] = useState<TableItem[]>([]);
  const [chunks, setChunks] = useState<ChunkItem[]>([]);

  const [activeTab, setActiveTab] = useState<'metadata' | 'pages' | 'tables' | 'chunks' | 'job'>('pages');
  const [selectedPageIndex, setSelectedPageIndex] = useState<number>(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copiedHash, setCopiedHash] = useState(false);

  useEffect(() => {
    if (!id) return;

    const fetchAllData = async () => {
      try {
        setLoading(true);
        const [docRes, pagesRes, tablesRes, chunksRes] = await Promise.all([
          apiClient.get('/documents/' + id),
          apiClient.get('/documents/' + id + '/pages'),
          apiClient.get('/documents/' + id + '/tables'),
          apiClient.get('/documents/' + id + '/chunks'),
        ]);

        setDocument(docRes.data);
        setPages(pagesRes.data);
        setTables(tablesRes.data);
        setChunks(chunksRes.data);
        setError(null);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to load document details');
      } finally {
        setLoading(false);
      }
    };

    fetchAllData();
  }, [id]);

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
          onClick={() => setActiveTab('chunks')}
          className={`pb-3 border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === 'chunks' ? 'border-blue-600 text-blue-700' : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          <Layers className="w-4 h-4" /> Structure Chunks ({chunks.length})
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
                <div className="p-4 bg-gray-50 border-b border-gray-200 flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-bold text-gray-900">
                      {table.caption || `Table ${table.table_index} (Page ${table.page_number})`}
                    </h3>
                    <span className="text-xs text-gray-500 font-mono">
                      Page {table.page_number} • {table.row_count} rows × {table.col_count} columns
                    </span>
                  </div>
                  <span className="text-xs font-semibold px-2 py-0.5 bg-emerald-100 text-emerald-800 border border-emerald-300 rounded">
                    Structure Preserved
                  </span>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="bg-gray-100 border-b border-gray-300 text-gray-800 font-bold uppercase tracking-wider">
                        {table.headers.map((h, hIdx) => (
                          <th key={hIdx} className="py-2.5 px-3 border-r border-gray-200 last:border-r-0">
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200 font-mono">
                      {table.rows.map((row, rIdx) => (
                        <tr key={rIdx} className="hover:bg-blue-50/50">
                          {row.map((cell, cIdx) => (
                            <td key={cIdx} className="py-2 px-3 border-r border-gray-100 last:border-r-0 text-gray-700">
                              {cell || '—'}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ))
          )}
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
    </div>
  );
};
"""

with open('frontend/src/pages/DocumentList.tsx', 'w', encoding='utf-8') as f:
    f.write(doc_list_code)
print("Updated DocumentList.tsx")

with open('frontend/src/pages/DocumentUpload.tsx', 'w', encoding='utf-8') as f:
    f.write(doc_upload_code)
print("Updated DocumentUpload.tsx")

with open('frontend/src/pages/DocumentDetail.tsx', 'w', encoding='utf-8') as f:
    f.write(doc_detail_code)
print("Updated DocumentDetail.tsx")
