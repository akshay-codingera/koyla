import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { apiClient } from '../api/client';
import { 
  Upload, 
  CheckCircle2, 
  AlertCircle, 
  ArrowRight, 
  RefreshCw, 
  Files, 
  Trash2, 
  Database, 
  FileSpreadsheet, 
  FileText, 
  Image as ImageIcon 
} from 'lucide-react';

interface Organization {
  id: string;
  code: string;
  name: string;
}

interface QueuedFile {
  id: string;
  file: File;
  detectedFormat: string;
  inferredType: string;
  sizeBytes: number;
}

interface UploadedReceipt {
  document_id: string;
  original_filename: string;
  detected_format: string;
  inferred_type: string;
  status: string;
  file_size_bytes: number;
  sha256_hash: string;
}

export const DocumentUpload: React.FC = () => {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [organizationId, setOrganizationId] = useState('');
  const [sourceTier, setSourceTier] = useState('TIER_B');
  const [queuedFiles, setQueuedFiles] = useState<QueuedFile[]>([]);
  const [dragOver, setDragOver] = useState(false);

  // Processing state
  const [uploading, setUploading] = useState(false);
  const [receipts, setReceipts] = useState<UploadedReceipt[]>([]);
  const [batchId, setBatchId] = useState<string | null>(null);
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

  const inferDocumentType = (filename: string, ext: string): string => {
    const fn = filename.toLowerCase();
    if (fn.includes('prod') || fn.includes('target') || fn.includes('dispatch')) return 'PRODUCTION_REPORT';
    if (fn.includes('geo') || fn.includes('borehole') || fn.includes('reserve') || fn.includes('litho')) return 'GEOLOGICAL_REPORT';
    if (fn.includes('mine') || fn.includes('plan') || fn.includes('block') || fn.includes('ocp')) return 'MINE_INFORMATION';
    if (ext === '.xlsx' || ext === '.xls' || ext === '.csv') return 'ANNEXURE_SPREADSHEET';
    return 'GEOLOGICAL_REPORT';
  };

  const handleFilesAdded = (files: FileList | File[]) => {
    const validExtensions = ['.pdf', '.docx', '.xlsx', '.xls', '.csv', '.txt', '.jpg', '.jpeg', '.png'];
    const newQueued: QueuedFile[] = [];
    let hasError = false;

    Array.from(files).forEach((f) => {
      const ext = '.' + f.name.split('.').pop()?.toLowerCase();
      if (!validExtensions.includes(ext)) {
        setErrorMessage(`Skipped unsupported file '${f.name}'. Supported: PDF, DOCX, XLSX, XLS, CSV, TXT, JPG, PNG`);
        hasError = true;
        return;
      }
      newQueued.push({
        id: Math.random().toString(36).substring(7),
        file: f,
        detectedFormat: ext.replace('.', '').toUpperCase(),
        inferredType: inferDocumentType(f.name, ext),
        sizeBytes: f.size,
      });
    });

    if (newQueued.length > 0) {
      setQueuedFiles((prev) => [...prev, ...newQueued]);
      if (!hasError) setErrorMessage(null);
    }
  };

  const removeQueuedFile = (id: string) => {
    setQueuedFiles((prev) => prev.filter((f) => f.id !== id));
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFilesAdded(e.dataTransfer.files);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (queuedFiles.length === 0) {
      setErrorMessage('Please select one or more files to ingest.');
      return;
    }
    if (!organizationId) {
      setErrorMessage('Please select an authorized organization scope.');
      return;
    }

    setUploading(true);
    setErrorMessage(null);

    const formData = new FormData();
    formData.append('organization_id', organizationId);
    formData.append('source_tier', sourceTier);

    queuedFiles.forEach((qf) => {
      formData.append('files', qf.file);
    });

    try {
      // Post to Phase 10 Universal Evidence batch upload endpoint
      const res = await apiClient.post('/evidence/upload?sync=true', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      setBatchId(res.data.batch_id);
      setReceipts(res.data.items);
      setQueuedFiles([]);
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || 'Evidence ingestion failed');
    } finally {
      setUploading(false);
    }
  };

  const handleReset = () => {
    setQueuedFiles([]);
    setReceipts([]);
    setBatchId(null);
    setErrorMessage(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 text-xs text-slate-400 font-mono mb-1">
          <Link to="/evidence" className="hover:underline text-blue-400">Universal Evidence</Link>
          <span>/</span>
          <span className="text-slate-200 font-semibold">Automatic Evidence Ingestion</span>
        </div>
        <h1 className="text-2xl font-bold font-mono text-slate-100 uppercase tracking-wider">
          Automatic Evidence Ingestion Studio
        </h1>
        <p className="text-xs font-mono text-slate-400 mt-1">
          One-action ingestion for heterogeneous mining records: PDF, DOCX, XLSX, XLS (Legacy BIFF8), CSV, TXT, and Geological Images.
          Automatic parsing, structure preservation, visual detection, and cross-document relationship discovery.
        </p>
      </div>

      {errorMessage && (
        <div className="p-3 bg-rose-950/80 border border-rose-800 rounded flex items-start gap-2.5 text-rose-200 text-xs font-mono">
          <AlertCircle className="w-4 h-4 flex-shrink-0 text-rose-400 mt-0.5" />
          <div>
            <span className="font-bold">Error: </span>
            {errorMessage}
          </div>
        </div>
      )}

      {/* Upload Success Receipt Card */}
      {receipts.length > 0 && (
        <div className="bg-[#12161d] border border-emerald-800 rounded-lg p-5 shadow-sm space-y-4 font-mono">
          <div className="flex items-center justify-between pb-3 border-b border-[#242c38]">
            <div className="flex items-center gap-2 text-emerald-300 font-bold text-sm">
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              <span>Evidence Batch Successfully Ingested ({receipts.length} Documents)</span>
            </div>
            <span className="text-[10px] text-slate-500">Batch ID: {batchId?.slice(0, 8)}...</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="bg-[#161c24] text-slate-400 text-[10px] uppercase border-b border-[#242c38]">
                  <th className="py-2 px-3">File Name</th>
                  <th className="py-2 px-3">Format</th>
                  <th className="py-2 px-3">Inferred Type</th>
                  <th className="py-2 px-3">SHA-256 Hash</th>
                  <th className="py-2 px-3">Status</th>
                  <th className="py-2 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1e2633]">
                {receipts.map((rc) => (
                  <tr key={rc.document_id} className="hover:bg-[#181f2a]">
                    <td className="py-2.5 px-3 font-bold text-slate-200">{rc.original_filename}</td>
                    <td className="py-2.5 px-3">
                      <span className="px-1.5 py-0.5 rounded text-[9px] bg-slate-800 text-slate-300 border border-slate-700">
                        {rc.detected_format}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-[11px] text-slate-400">{rc.inferred_type}</td>
                    <td className="py-2.5 px-3 text-[10px] text-slate-500 font-mono truncate max-w-[120px]" title={rc.sha256_hash}>
                      {rc.sha256_hash.slice(0, 12)}...
                    </td>
                    <td className="py-2.5 px-3">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950 text-emerald-300 border border-emerald-800">
                        COMPLETED
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      <Link
                        to={`/documents/${rc.document_id}`}
                        className="text-blue-400 hover:text-blue-300 text-[11px] font-bold flex items-center justify-end gap-1"
                      >
                        Inspect <ArrowRight className="w-3 h-3" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex items-center justify-between pt-3 border-t border-[#242c38]">
            <button
              onClick={handleReset}
              className="px-3 py-1.5 bg-[#161c24] hover:bg-[#1f2733] border border-[#2b3544] rounded text-xs text-slate-300"
            >
              Ingest More Files
            </button>

            <Link
              to="/evidence"
              className="px-4 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded text-xs font-bold flex items-center gap-1.5"
            >
              <Database className="w-3.5 h-3.5" />
              View In Evidence Control Room
            </Link>
          </div>
        </div>
      )}

      {/* Main Ingestion Form */}
      {receipts.length === 0 && (
        <form onSubmit={handleSubmit} className="space-y-5 bg-[#12161d] border border-[#242c38] rounded-lg p-6 shadow-sm">
          {/* Metadata Selection */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-mono text-slate-300 font-bold mb-1.5">
                Authorized Organization Scope <span className="text-rose-400">*</span>
              </label>
              <select
                value={organizationId}
                onChange={(e) => setOrganizationId(e.target.value)}
                disabled={uploading}
                className="w-full px-3 py-2 bg-[#0d1015] border border-[#2b3544] rounded text-xs font-mono text-slate-200 focus:outline-none focus:border-blue-500"
              >
                {organizations.map((org) => (
                  <option key={org.id} value={org.id}>
                    {org.code} — {org.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-mono text-slate-300 font-bold mb-1.5">
                Source Trust Tier <span className="text-rose-400">*</span>
              </label>
              <select
                value={sourceTier}
                onChange={(e) => setSourceTier(e.target.value)}
                disabled={uploading}
                className="w-full px-3 py-2 bg-[#0d1015] border border-[#2b3544] rounded text-xs font-mono text-slate-200 focus:outline-none focus:border-blue-500"
              >
                <option value="TIER_A">Tier A: Authoritative / Statutory Ground Truth</option>
                <option value="TIER_B">Tier B: Internal Operational Record (Default)</option>
                <option value="TIER_C">Tier C: Unverified / Third-Party Evidence</option>
              </select>
            </div>
          </div>

          {/* Multi-File Drag & Drop Zone */}
          <div>
            <label className="block text-xs font-mono text-slate-300 font-bold mb-1.5">
              Select or Drop Evidence Files (Heterogeneous Batch) <span className="text-rose-400">*</span>
            </label>
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                dragOver
                  ? 'border-blue-500 bg-blue-950/20'
                  : 'border-[#2b3544] hover:border-slate-500 bg-[#0d1015]'
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                multiple
                className="hidden"
                accept=".pdf,.docx,.xlsx,.xls,.csv,.txt,.jpg,.jpeg,.png"
                onChange={(e) => {
                  if (e.target.files) handleFilesAdded(e.target.files);
                }}
              />

              <div className="flex flex-col items-center gap-2">
                <Upload className="w-8 h-8 text-blue-400" />
                <p className="text-sm font-mono font-bold text-slate-200">
                  Drag and drop files here, or click to browse
                </p>
                <p className="text-xs font-mono text-slate-500">
                  Supports PDF, DOCX, XLSX, XLS, CSV, TXT, JPG, PNG (Multi-file batch enabled)
                </p>
              </div>
            </div>
          </div>

          {/* Queued Files Register */}
          {queuedFiles.length > 0 && (
            <div className="space-y-2 pt-2 border-t border-[#242c38]">
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="font-bold text-slate-300">
                  Ready to Ingest ({queuedFiles.length} files selected):
                </span>
                <button
                  type="button"
                  onClick={() => setQueuedFiles([])}
                  className="text-rose-400 hover:text-rose-300 text-[11px]"
                >
                  Clear all
                </button>
              </div>

              <div className="divide-y divide-[#1e2633] border border-[#242c38] rounded bg-[#0d1015] max-h-56 overflow-y-auto">
                {queuedFiles.map((qf) => (
                  <div key={qf.id} className="p-2.5 flex items-center justify-between text-xs font-mono">
                    <div className="flex items-center gap-2 truncate">
                      <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-slate-800 text-slate-300 border border-slate-700">
                        {qf.detectedFormat}
                      </span>
                      <span className="text-slate-200 font-bold truncate max-w-sm" title={qf.file.name}>
                        {qf.file.name}
                      </span>
                      <span className="text-[10px] text-slate-500">
                        ({(qf.sizeBytes / 1024).toFixed(1)} KB)
                      </span>
                      <span className="text-[10px] px-1.5 py-0.2 rounded bg-blue-950/60 text-blue-400 border border-blue-900">
                        {qf.inferredType}
                      </span>
                    </div>

                    <button
                      type="button"
                      onClick={() => removeQueuedFile(qf.id)}
                      className="text-slate-500 hover:text-rose-400 p-1"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Submit Action */}
          <div className="flex items-center justify-end gap-3 pt-3 border-t border-[#242c38]">
            <button
              type="submit"
              disabled={queuedFiles.length === 0 || uploading}
              className="px-5 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded text-xs font-mono font-bold flex items-center gap-2 shadow-sm transition-colors"
            >
              {uploading ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  Processing Universal Evidence...
                </>
              ) : (
                <>
                  <Upload className="w-3.5 h-3.5" />
                  Ingest Evidence Batch ({queuedFiles.length})
                </>
              )}
            </button>
          </div>
        </form>
      )}
    </div>
  );
};
