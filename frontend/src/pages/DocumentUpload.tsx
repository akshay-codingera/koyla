import React, { useState, useEffect, useRef } from 'react';
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
      setTitle(file.name.replace(/\.[^/.]+$/, ''));
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
