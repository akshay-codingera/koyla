import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { apiClient } from '../api/client';
import {
  CheckCircle,
  XCircle,
  AlertTriangle,
  Clock,
  ShieldCheck,
  FileText,
  HelpCircle,
  Edit3,
  Filter,
  Check,
  RotateCcw,
  ExternalLink
} from 'lucide-react';

interface VerificationItem {
  id: string;
  task_type: string;
  organization_id: string | null;
  document_id: string | null;
  document_title: string | null;
  field_id: string | null;
  reconciliation_group_id: string | null;
  status: string;
  action_taken: string | null;
  corrected_value: string | null;
  evidence_context: any;
  review_notes: string | null;
  reviewed_at: string | null;
  created_at: string | null;
  field_details: any;
}

export const VerificationQueue: React.FC = () => {
  const [tasks, setTasks] = useState<VerificationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTask, setSelectedTask] = useState<VerificationItem | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('PENDING');
  const [typeFilter, setTypeFilter] = useState<string>('ALL');

  // Form states
  const [correctedValue, setCorrectedValue] = useState<string>('');
  const [reviewNotes, setReviewNotes] = useState<string>('');
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [actionMessage, setActionMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const fetchQueue = async () => {
    try {
      setLoading(true);
      const url = statusFilter === 'ALL'
        ? '/verification/queue'
        : `/verification/queue?status=${statusFilter}`;
      const res = await apiClient.get(url);
      setTasks(res.data);
    } catch (err: any) {
      console.error('Failed to load verification queue', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQueue();
  }, [statusFilter]);

  const handleOpenReview = (task: VerificationItem) => {
    setSelectedTask(task);
    setCorrectedValue(task.field_details?.raw_value || '');
    setReviewNotes(task.review_notes || '');
    setActionMessage(null);
  };

  const handleApplyAction = async (action: 'APPROVE' | 'CORRECT' | 'REJECT' | 'DEFER') => {
    if (!selectedTask) return;
    try {
      setActionLoading(true);
      setActionMessage(null);

      const payload: any = {
        action,
        review_notes: reviewNotes,
      };
      if (action === 'CORRECT') {
        payload.corrected_value = correctedValue;
      }

      await apiClient.post(`/verification/tasks/${selectedTask.id}/action`, payload);

      setActionMessage({
        type: 'success',
        text: `Successfully executed action: ${action}`,
      });

      // Refresh list
      await fetchQueue();
      setTimeout(() => {
        setSelectedTask(null);
      }, 1000);
    } catch (err: any) {
      setActionMessage({
        type: 'error',
        text: err.response?.data?.detail || 'Failed to execute verification action',
      });
    } finally {
      setActionLoading(false);
    }
  };

  const filteredTasks = tasks.filter((t) => {
    if (typeFilter !== 'ALL' && t.task_type !== typeFilter) return false;
    return true;
  });

  const conflictCount = tasks.filter((t) => t.task_type === 'EXTRACTION_CONFLICT').length;
  const validationErrorCount = tasks.filter((t) => t.task_type === 'VALIDATION_ERROR').length;
  const lowConfidenceCount = tasks.filter((t) => t.task_type.includes('LOW_CONFIDENCE')).length;

  return (
    <div className="space-y-6">
      {/* Header & Metrics */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-gray-200 pb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 tracking-tight flex items-center gap-2.5">
            <ShieldCheck className="w-6 h-6 text-blue-600" />
            Human Verification Queue
          </h1>
          <p className="text-xs text-gray-500 mt-1">
            Institutional governance interface for verifying low-confidence extractions, resolving cross-document conflicts, and audit logging.
          </p>
        </div>
      </div>

      {/* Metrics Banner */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="bg-white border border-gray-200 p-4 rounded-lg shadow-sm">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Pending Review</p>
          <p className="text-2xl font-bold text-blue-600 mt-1">{tasks.filter(t => t.status === 'PENDING').length}</p>
        </div>
        <div className="bg-white border border-gray-200 p-4 rounded-lg shadow-sm">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Cross-Doc Conflicts</p>
          <p className="text-2xl font-bold text-purple-600 mt-1">{conflictCount}</p>
        </div>
        <div className="bg-white border border-gray-200 p-4 rounded-lg shadow-sm">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Validation Errors</p>
          <p className="text-2xl font-bold text-red-600 mt-1">{validationErrorCount}</p>
        </div>
        <div className="bg-white border border-gray-200 p-4 rounded-lg shadow-sm">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Low Confidence</p>
          <p className="text-2xl font-bold text-amber-600 mt-1">{lowConfidenceCount}</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-white p-3 rounded-lg border border-gray-200">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-gray-500" />
          <span className="text-xs font-semibold text-gray-700">Status:</span>
          {['PENDING', 'APPROVED', 'CORRECTED', 'REJECTED', 'ALL'].map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                statusFilter === s
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {s}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-gray-700">Category:</span>
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="border border-gray-300 rounded px-2.5 py-1 text-xs bg-white text-gray-800"
          >
            <option value="ALL">All Tasks</option>
            <option value="EXTRACTION_CONFLICT">Extraction Conflicts</option>
            <option value="VALIDATION_ERROR">Validation Errors</option>
            <option value="LOW_CONFIDENCE_EXTRACTION">Low Confidence Extraction</option>
            <option value="LOW_CONFIDENCE_OCR">Low Confidence OCR</option>
            <option value="TABLE_CONTINUATION_REVIEW">Table Continuations</option>
          </select>
        </div>
      </div>

      {/* Tasks Table */}
      <div className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-sm text-gray-500">Loading verification queue...</div>
        ) : filteredTasks.length === 0 ? (
          <div className="p-8 text-center text-sm text-gray-500">No verification tasks found matching filters.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-gray-50 border-b border-gray-200 text-gray-700 font-semibold uppercase tracking-wider">
                <tr>
                  <th className="py-3 px-4">Task Type</th>
                  <th className="py-3 px-4">Document / Source</th>
                  <th className="py-3 px-4">Subject / Metric</th>
                  <th className="py-3 px-4">Observed Value</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Created</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {filteredTasks.map((t) => {
                  let badgeColor = 'bg-gray-100 text-gray-700';
                  if (t.task_type === 'EXTRACTION_CONFLICT') badgeColor = 'bg-purple-100 text-purple-800 border border-purple-200';
                  else if (t.task_type === 'VALIDATION_ERROR') badgeColor = 'bg-red-100 text-red-800 border border-red-200';
                  else if (t.task_type.includes('LOW_CONFIDENCE')) badgeColor = 'bg-amber-100 text-amber-800 border border-amber-200';

                  let statusColor = 'bg-amber-50 text-amber-700 border border-amber-200';
                  if (t.status === 'APPROVED') statusColor = 'bg-green-50 text-green-700 border border-green-200';
                  else if (t.status === 'CORRECTED') statusColor = 'bg-blue-50 text-blue-700 border border-blue-200';
                  else if (t.status === 'REJECTED') statusColor = 'bg-red-50 text-red-700 border border-red-200';

                  return (
                    <tr key={t.id} className="hover:bg-gray-50/80 transition-colors">
                      <td className="py-3 px-4">
                        <span className={`inline-block px-2 py-0.5 rounded text-[11px] font-semibold ${badgeColor}`}>
                          {t.task_type.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        {t.document_id ? (
                          <Link to={`/documents/${t.document_id}`} className="font-semibold text-blue-600 hover:underline flex items-center gap-1">
                            <FileText className="w-3.5 h-3.5" />
                            {t.document_title || t.document_id.slice(0, 8)}
                          </Link>
                        ) : (
                          <span className="text-gray-400">Cross-Document</span>
                        )}
                      </td>
                      <td className="py-3 px-4 font-medium text-gray-800">
                        {t.field_details?.field_name || t.evidence_context?.metric_name || 'Anomalous Item'}
                      </td>
                      <td className="py-3 px-4 font-mono text-gray-700">
                        {t.field_details?.raw_value
                          ? `${t.field_details.raw_value} ${t.field_details.unit || ''}`
                          : (t.evidence_context?.divergence_pct
                              ? `Divergence: ${t.evidence_context.divergence_pct}%`
                              : 'Review Context')}
                      </td>
                      <td className="py-3 px-4">
                        <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold ${statusColor}`}>
                          {t.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-gray-500">
                        {t.created_at ? new Date(t.created_at).toLocaleDateString() : 'N/A'}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={() => handleOpenReview(t)}
                          className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs font-semibold transition-colors"
                        >
                          Review & Act
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Review Modal (3-Column Governance View) */}
      {selectedTask && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-5xl overflow-hidden flex flex-col max-h-[90vh]">
            {/* Modal Header */}
            <div className="bg-slate-900 text-white px-6 py-4 flex items-center justify-between">
              <div>
                <span className="text-xs font-bold uppercase tracking-wider text-blue-400">Governance Review Task</span>
                <h2 className="text-lg font-bold flex items-center gap-2 mt-0.5">
                  <ShieldCheck className="w-5 h-5 text-blue-400" />
                  {selectedTask.task_type.replace(/_/g, ' ')}
                </h2>
              </div>
              <button
                onClick={() => setSelectedTask(null)}
                className="text-slate-400 hover:text-white text-lg font-bold px-2 py-1"
              >
                ✕
              </button>
            </div>

            {/* Modal Body - 3 Columns */}
            <div className="p-6 grid grid-cols-1 md:grid-cols-3 gap-6 overflow-y-auto flex-1">
              {/* Column 1: Source Document & Provenance */}
              <div className="space-y-4 bg-gray-50 p-4 rounded-lg border border-gray-200">
                <h3 className="text-xs font-bold uppercase tracking-wider text-gray-700 border-b pb-2">
                  1. Source Provenance
                </h3>
                <div>
                  <label className="text-[11px] font-semibold text-gray-500 block">Document Title</label>
                  <p className="text-xs font-bold text-gray-900 mt-0.5">{selectedTask.document_title || 'Cross-Document Group'}</p>
                </div>
                <div>
                  <label className="text-[11px] font-semibold text-gray-500 block">Physical Source Page</label>
                  <p className="text-xs font-semibold text-blue-700 mt-0.5">
                    {selectedTask.field_details?.page_number
                      ? `Page ${selectedTask.field_details.page_number}`
                      : (selectedTask.evidence_context?.source_page
                          ? `Page ${selectedTask.evidence_context.source_page}`
                          : 'Aggregated Evidence')}
                  </p>
                </div>
                <div>
                  <label className="text-[11px] font-semibold text-gray-500 block">Context Snippet / Table Row</label>
                  <div className="bg-white border rounded p-2 text-xs font-mono text-gray-800 whitespace-pre-wrap mt-1 max-h-36 overflow-y-auto">
                    {selectedTask.field_details?.source_text ||
                     selectedTask.evidence_context?.source_text ||
                     selectedTask.review_notes ||
                     'Context verified against primary source table.'}
                  </div>
                </div>
              </div>

              {/* Column 2: Extracted Value & Validation Details */}
              <div className="space-y-4 bg-gray-50 p-4 rounded-lg border border-gray-200">
                <h3 className="text-xs font-bold uppercase tracking-wider text-gray-700 border-b pb-2">
                  2. Extraction & Validation
                </h3>
                <div>
                  <label className="text-[11px] font-semibold text-gray-500 block">Field Identifier</label>
                  <p className="text-xs font-bold text-gray-900 mt-0.5">
                    {selectedTask.field_details?.field_name || selectedTask.evidence_context?.metric_name || 'N/A'}
                  </p>
                </div>
                <div>
                  <label className="text-[11px] font-semibold text-gray-500 block">Current Extracted Value</label>
                  <p className="text-sm font-mono font-bold text-gray-900 mt-0.5">
                    {selectedTask.field_details?.raw_value || 'None'} {selectedTask.field_details?.unit || ''}
                  </p>
                </div>
                <div className="flex gap-2">
                  <div className="flex-1">
                    <label className="text-[11px] font-semibold text-gray-500 block">Confidence</label>
                    <span className="inline-block px-2 py-0.5 rounded text-[11px] font-bold bg-blue-100 text-blue-800 mt-0.5">
                      {selectedTask.field_details ? `${Math.round(selectedTask.field_details.confidence_score * 100)}% (${selectedTask.field_details.confidence_level})` : 'N/A'}
                    </span>
                  </div>
                  <div className="flex-1">
                    <label className="text-[11px] font-semibold text-gray-500 block">Validation</label>
                    <span className="inline-block px-2 py-0.5 rounded text-[11px] font-bold bg-red-100 text-red-800 mt-0.5">
                      {selectedTask.field_details?.validation_status || 'ATTENTION REQUIRED'}
                    </span>
                  </div>
                </div>
                {selectedTask.field_details?.validation_results && selectedTask.field_details.validation_results.length > 0 && (
                  <div>
                    <label className="text-[11px] font-semibold text-gray-500 block">Validation Findings</label>
                    <div className="space-y-1.5 mt-1">
                      {selectedTask.field_details.validation_results.map((vr: any) => (
                        <div key={vr.id} className="p-2 rounded border bg-white text-[11px]">
                          <p className="font-bold text-red-700">{vr.rule_name} ({vr.status})</p>
                          <p className="text-gray-600 mt-0.5">{vr.message}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Column 3: Decision & Action Form */}
              <div className="space-y-4 bg-gray-50 p-4 rounded-lg border border-gray-200 flex flex-col justify-between">
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-gray-700 border-b pb-2">
                    3. Governance Decision
                  </h3>
                  <div className="space-y-3 mt-3">
                    <div>
                      <label className="text-[11px] font-semibold text-gray-700 block">Corrected Value (if modifying)</label>
                      <input
                        type="text"
                        value={correctedValue}
                        onChange={(e) => setCorrectedValue(e.target.value)}
                        placeholder="Enter verified corrected value"
                        className="w-full mt-1 border border-gray-300 rounded px-2.5 py-1.5 text-xs font-mono bg-white"
                      />
                      <p className="text-[10px] text-gray-500 mt-1">
                        Original raw value will be preserved in the audit trail.
                      </p>
                    </div>

                    <div>
                      <label className="text-[11px] font-semibold text-gray-700 block">Reviewer Notes</label>
                      <textarea
                        value={reviewNotes}
                        onChange={(e) => setReviewNotes(e.target.value)}
                        rows={3}
                        placeholder="Enter rationale for verification or correction..."
                        className="w-full mt-1 border border-gray-300 rounded p-2 text-xs bg-white"
                      />
                    </div>

                    {actionMessage && (
                      <div className={`p-2 rounded text-xs font-medium ${
                        actionMessage.type === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                      }`}>
                        {actionMessage.text}
                      </div>
                    )}
                  </div>
                </div>

                <div className="space-y-2 pt-4 border-t border-gray-200">
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      onClick={() => handleApplyAction('APPROVE')}
                      disabled={actionLoading}
                      className="w-full py-2 bg-green-600 hover:bg-green-700 text-white rounded text-xs font-bold transition-colors disabled:opacity-50"
                    >
                      Approve As-Is
                    </button>
                    <button
                      onClick={() => handleApplyAction('CORRECT')}
                      disabled={actionLoading || !correctedValue}
                      className="w-full py-2 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs font-bold transition-colors disabled:opacity-50"
                    >
                      Apply Correction
                    </button>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      onClick={() => handleApplyAction('REJECT')}
                      disabled={actionLoading}
                      className="w-full py-2 bg-red-600 hover:bg-red-700 text-white rounded text-xs font-bold transition-colors disabled:opacity-50"
                    >
                      Reject Field
                    </button>
                    <button
                      onClick={() => handleApplyAction('DEFER')}
                      disabled={actionLoading}
                      className="w-full py-2 bg-gray-500 hover:bg-gray-600 text-white rounded text-xs font-bold transition-colors disabled:opacity-50"
                    >
                      Defer Review
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
