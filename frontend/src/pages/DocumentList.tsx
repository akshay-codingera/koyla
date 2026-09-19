import React, { useState, useEffect } from 'react';
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
