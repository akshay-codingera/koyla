import React, { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import { Shield, Clock, Search, Filter, RefreshCw, FileText, UserCheck, AlertTriangle } from 'lucide-react';

interface AuditItem {
  id: string;
  created_at: string;
  actor_name: string | null;
  role_code: string | null;
  organization_id: string | null;
  action: string;
  object_type: string | null;
  object_id: string | null;
  sha256_hash: string | null;
  details: any;
}

export const AuditLog: React.FC = () => {
  const [logs, setLogs] = useState<AuditItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionFilter, setActionFilter] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  const fetchLogs = async () => {
    try {
      setLoading(true);
      const url = actionFilter ? `/audit/logs?action=${actionFilter}` : '/audit/logs';
      const res = await apiClient.get(url);
      setLogs(res.data);
    } catch (err) {
      console.error('Failed to load audit logs', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [actionFilter]);

  const filteredLogs = logs.filter(log => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return (
      (log.action && log.action.toLowerCase().includes(term)) ||
      (log.actor_name && log.actor_name.toLowerCase().includes(term)) ||
      (log.role_code && log.role_code.toLowerCase().includes(term)) ||
      (log.object_type && log.object_type.toLowerCase().includes(term)) ||
      (log.object_id && log.object_id.toLowerCase().includes(term))
    );
  });

  const getActionBadge = (action: string) => {
    if (action.includes('VERIFICATION') || action.includes('APPROVE')) {
      return 'bg-emerald-100 text-emerald-800 border-emerald-200';
    }
    if (action.includes('REJECT') || action.includes('ERROR') || action.includes('CONFLICT')) {
      return 'bg-rose-100 text-rose-800 border-rose-200';
    }
    if (action.includes('CORRECT')) {
      return 'bg-amber-100 text-amber-800 border-amber-200';
    }
    if (action.includes('EXTRACTION')) {
      return 'bg-blue-100 text-blue-800 border-blue-200';
    }
    return 'bg-slate-100 text-slate-800 border-slate-200';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded border border-gray-200 p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-slate-700 font-semibold text-xs tracking-wider uppercase mb-1">
            <Shield size={16} className="text-blue-700" />
            <span>Immutable Governance & Traceability</span>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 tracking-tight">System Audit Trail</h1>
          <p className="text-xs text-gray-500 mt-0.5">
            Real-time provenance log of document ingestion, structured extractions, validations, and verification actions.
          </p>
        </div>
        <button
          onClick={fetchLogs}
          disabled={loading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded text-xs font-semibold border border-slate-300 transition-colors self-start md:self-auto"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Filter Bar */}
      <div className="bg-white rounded border border-gray-200 p-4 shadow-sm flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2 flex-1 min-w-[240px]">
          <Search size={14} className="text-gray-400 shrink-0" />
          <input
            type="text"
            placeholder="Search action, actor, role, or object ID..."
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            className="w-full p-2 border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 focus:outline-none"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter size={14} className="text-gray-400" />
          <select
            value={actionFilter}
            onChange={e => setActionFilter(e.target.value)}
            className="p-2 border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 focus:outline-none bg-white"
          >
            <option value="">All Actions</option>
            <option value="AUTH_LOGIN">AUTH_LOGIN</option>
            <option value="DOCUMENT_UPLOAD">DOCUMENT_UPLOAD</option>
            <option value="DOCUMENT_PROCESSED">DOCUMENT_PROCESSED</option>
            <option value="EXTRACTION_RUN_TRIGGERED">EXTRACTION_RUN_TRIGGERED</option>
            <option value="VERIFICATION_TASK_RESOLVED">VERIFICATION_TASK_RESOLVED</option>
          </select>
        </div>
      </div>

      {/* Log Table */}
      <div className="bg-white rounded border border-gray-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="text-center py-12 text-gray-500 text-xs">Loading audit records from PostgreSQL...</div>
        ) : filteredLogs.length === 0 ? (
          <div className="text-center py-12 text-gray-500 text-xs">No audit events match current filters.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-50 text-slate-600 border-b border-gray-200 font-semibold uppercase tracking-wider text-[11px]">
                  <th className="p-3">Timestamp</th>
                  <th className="p-3">Actor</th>
                  <th className="p-3">Role</th>
                  <th className="p-3">Action</th>
                  <th className="p-3">Target Object</th>
                  <th className="p-3">Event Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filteredLogs.map(log => (
                  <tr key={log.id} className="hover:bg-slate-50/60 transition-colors font-mono text-[11px]">
                    <td className="p-3 text-gray-600 whitespace-nowrap font-sans">
                      <div className="flex items-center gap-1.5">
                        <Clock size={12} className="text-gray-400 shrink-0" />
                        <span>{log.created_at ? new Date(log.created_at).toLocaleString() : 'N/A'}</span>
                      </div>
                    </td>
                    <td className="p-3 font-semibold text-gray-800">
                      {log.actor_name || 'System / Batch'}
                    </td>
                    <td className="p-3">
                      <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 text-[10px] font-sans font-medium border border-slate-200">
                        {log.role_code || 'SYSTEM'}
                      </span>
                    </td>
                    <td className="p-3">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-sans font-bold border ${getActionBadge(log.action)}`}>
                        {log.action}
                      </span>
                    </td>
                    <td className="p-3 text-gray-600">
                      {log.object_type ? `${log.object_type}:${log.object_id?.substring(0, 8) || ''}` : '-'}
                    </td>
                    <td className="p-3 text-gray-700 font-sans max-w-xs truncate">
                      {log.details ? (
                        <span title={JSON.stringify(log.details, null, 2)}>
                          {typeof log.details === 'string' ? log.details : JSON.stringify(log.details)}
                        </span>
                      ) : '-'}
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
