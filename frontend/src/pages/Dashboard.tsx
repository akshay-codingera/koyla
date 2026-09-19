import { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import { FileText, ShieldCheck, Activity, Users, Database, Building2 } from 'lucide-react';

export const Dashboard = () => {
  const [metrics, setMetrics] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const user = JSON.parse(localStorage.getItem('user') || '{}');

  useEffect(() => {
    apiClient.get('/dashboard/metrics')
      .then(res => setMetrics(res.data))
      .catch(err => console.error("Error loading dashboard metrics:", err))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4 border-b border-gray-200 pb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Executive Dashboard</h1>
          <p className="text-sm text-gray-500">CIL / CMPDI Unified Reporting Intelligence Platform</p>
        </div>
        <div className="flex flex-wrap gap-2 items-center">
          <div className="bg-emerald-50 text-emerald-800 text-xs px-3 py-1.5 rounded-full font-medium border border-emerald-200 flex items-center gap-1.5">
            <Database size={14} className="text-emerald-600" />
            <span>PostgreSQL 16 + pgvector (Active)</span>
          </div>
          <div className="bg-blue-50 text-blue-900 text-xs px-3 py-1.5 rounded-full font-medium border border-blue-200 flex items-center gap-1.5">
            <Building2 size={14} className="text-blue-700" />
            <span>{user.organization?.name || 'CMPDI'} [{user.role}]</span>
          </div>
        </div>
      </div>
      
      {metrics?.is_demo_data && (
        <div className="bg-amber-50 border-l-4 border-amber-500 text-amber-900 p-4 rounded-r-md text-sm shadow-sm flex items-start gap-3">
          <div className="font-semibold shrink-0">Demo Dataset:</div>
          <div>All displayed statistics and document counts are queried live from the seeded PostgreSQL demonstration records.</div>
        </div>
      )}

      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading verified metrics from PostgreSQL...</div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
            <div className="bg-white p-5 rounded-lg border border-gray-200 shadow-sm flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-wider text-gray-500 font-semibold">Documents Ingested</p>
                <p className="text-3xl font-bold text-gray-900 mt-1">{metrics?.documents_ingested ?? 0}</p>
                <p className="text-xs text-emerald-600 font-medium mt-1">{metrics?.documents_processed ?? 0} processed</p>
              </div>
              <div className="bg-blue-50 p-3 rounded-lg text-blue-700"><FileText size={24}/></div>
            </div>

            <div className="bg-white p-5 rounded-lg border border-gray-200 shadow-sm flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-wider text-gray-500 font-semibold">Verification Backlog</p>
                <p className="text-3xl font-bold text-gray-900 mt-1">{metrics?.verification_backlog ?? 0}</p>
                <p className="text-xs text-amber-600 font-medium mt-1">{metrics?.documents_awaiting_verification ?? 0} awaiting review</p>
              </div>
              <div className="bg-amber-50 p-3 rounded-lg text-amber-700"><Activity size={24}/></div>
            </div>

            <div className="bg-white p-5 rounded-lg border border-gray-200 shadow-sm flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-wider text-gray-500 font-semibold">Extraction Success</p>
                <p className="text-3xl font-bold text-gray-900 mt-1">{metrics?.extraction_success_rate ?? 0}%</p>
                <p className="text-xs text-gray-500 font-medium mt-1">Grounded schema metrics</p>
              </div>
              <div className="bg-emerald-50 p-3 rounded-lg text-emerald-700"><ShieldCheck size={24}/></div>
            </div>

            <div className="bg-white p-5 rounded-lg border border-gray-200 shadow-sm flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-wider text-gray-500 font-semibold">Audit Events</p>
                <p className="text-3xl font-bold text-gray-900 mt-1">{metrics?.audit_events ?? 0}</p>
                <p className="text-xs text-gray-500 font-medium mt-1">Immutable PostgreSQL log</p>
              </div>
              <div className="bg-purple-50 p-3 rounded-lg text-purple-700"><Users size={24}/></div>
            </div>
          </div>

          <div className="bg-white p-6 rounded-lg border border-gray-200 shadow-sm">
            <h2 className="text-base font-semibold text-gray-800 mb-3">Organization Scope Details</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
              <div className="p-3 bg-gray-50 rounded border border-gray-100">
                <span className="text-gray-500 block text-xs">Active Scope:</span>
                <span className="font-semibold text-gray-800">{metrics?.organization_scope?.name} ({metrics?.organization_scope?.code})</span>
              </div>
              <div className="p-3 bg-gray-50 rounded border border-gray-100">
                <span className="text-gray-500 block text-xs">Access Level:</span>
                <span className="font-semibold text-gray-800">{metrics?.organization_scope?.is_unrestricted ? "National / Apex Unrestricted" : "Regional Organization Restricted"}</span>
              </div>
              <div className="p-3 bg-gray-50 rounded border border-gray-100">
                <span className="text-gray-500 block text-xs">Storage Engine:</span>
                <span className="font-semibold text-gray-800">{metrics?.data_source}</span>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
