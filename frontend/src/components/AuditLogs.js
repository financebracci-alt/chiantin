// Audit Log Viewer
import React, { useState, useEffect } from 'react';
import api from '../api';

export function AuditLogViewer() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [selectedLog, setSelectedLog] = useState(null);

  useEffect(() => {
    fetchLogs();
  }, [filter]);

  const fetchLogs = async () => {
    try {
      const params = filter !== 'all' ? `?entity_type=${filter}` : '';
      const response = await api.get(`/admin/audit-logs${params}`);
      setLogs(response.data);
    } catch (err) {
      console.error('Failed to fetch audit logs:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleString();
  };

  const getActionColor = (action) => {
    if (action.includes('SUCCESS') || action.includes('APPROVED') || action.includes('CREATED') || action.includes('REMOVED')) return 'text-green-600 bg-green-50';
    if (action.includes('FAILED') || action.includes('REJECTED') || action.includes('BLOCKED')) return 'text-red-600 bg-red-50';
    if (action.includes('MODIFIED') || action.includes('UPDATED') || action.includes('CHANGED') || action.includes('SET')) return 'text-amber-600 bg-amber-50';
    return 'text-blue-600 bg-blue-50';
  };

  const getActionBadgeColor = (action) => {
    if (action.includes('SUCCESS') || action.includes('APPROVED') || action.includes('CREATED')) return 'bg-green-100 text-green-800 border-green-200';
    if (action.includes('FAILED') || action.includes('REJECTED') || action.includes('BLOCKED')) return 'bg-red-100 text-red-800 border-red-200';
    if (action.includes('MODIFIED') || action.includes('UPDATED') || action.includes('CHANGED') || action.includes('SET')) return 'bg-amber-100 text-amber-800 border-amber-200';
    return 'bg-blue-100 text-blue-800 border-blue-200';
  };

  if (loading) {
    return <div className="text-center py-8">Loading audit logs...</div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold">Audit Logs</h3>
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-md text-sm"
          data-testid="audit-filter"
        >
          <option value="all">All Events</option>
          <option value="auth">Authentication</option>
          <option value="user">User Events</option>
          <option value="kyc">KYC Events</option>
          <option value="ledger">Ledger Events</option>
          <option value="account">Account Events</option>
          <option value="tax_hold">Tax Hold Events</option>
          <option value="ticket">Ticket Events</option>
        </select>
      </div>

      {logs.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-8 text-center">
          <p className="text-gray-600">No audit logs found</p>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow">
          <div className="divide-y max-h-[600px] overflow-y-auto">
            {logs.map((log) => (
              <div
                key={log.id}
                onClick={() => setSelectedLog(log)}
                className="p-4 hover:bg-gray-50 cursor-pointer transition-colors"
                data-testid={`audit-log-${log.id}`}
              >
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <div className="flex items-center space-x-2">
                      <span className={`font-medium px-2 py-0.5 rounded text-sm ${getActionColor(log.action)}`}>
                        {log.action.replace(/_/g, ' ')}
                      </span>
                      <span className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded">
                        {log.entity_type}
                      </span>
                    </div>
                    <p className="text-sm text-gray-700 mt-1">{log.description}</p>
                    <div className="flex items-center space-x-4 mt-2 text-xs text-gray-500">
                      <span>By: {log.performed_by_email || log.performed_by}</span>
                      <span>•</span>
                      <span>{formatDate(log.created_at)}</span>
                      {log.entity_id && (
                        <>
                          <span>•</span>
                          <span className="font-mono">{log.entity_id.substring(0, 12)}...</span>
                        </>
                      )}
                    </div>
                  </div>
                  <div className="ml-4 text-gray-400">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Audit Log Detail Modal */}
      {selectedLog && (
        <>
          <div 
            className="fixed inset-0 bg-black/50 z-40" 
            onClick={() => setSelectedLog(null)}
          />
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-hidden">
              {/* Header */}
              <div className={`p-6 ${getActionColor(selectedLog.action)}`}>
                <div className="flex justify-between items-start">
                  <div>
                    <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium border ${getActionBadgeColor(selectedLog.action)}`}>
                      {selectedLog.action.replace(/_/g, ' ')}
                    </span>
                    <h3 className="text-xl font-bold mt-3 text-gray-900">{selectedLog.description}</h3>
                  </div>
                  <button 
                    onClick={() => setSelectedLog(null)}
                    className="text-gray-500 hover:text-gray-700 transition-colors"
                  >
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              </div>

              {/* Details */}
              <div className="p-6 space-y-4 overflow-y-auto max-h-[60vh]">
                {/* Basic Info */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-xs text-gray-500 uppercase tracking-wide font-medium">Action Type</p>
                    <p className="text-sm font-semibold text-gray-900 mt-1">{selectedLog.action}</p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-xs text-gray-500 uppercase tracking-wide font-medium">Entity Type</p>
                    <p className="text-sm font-semibold text-gray-900 mt-1">{selectedLog.entity_type}</p>
                  </div>
                </div>

                {/* Entity ID */}
                {selectedLog.entity_id && (
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-xs text-gray-500 uppercase tracking-wide font-medium">Entity ID</p>
                    <p className="text-sm font-mono text-gray-900 mt-1 break-all">{selectedLog.entity_id}</p>
                  </div>
                )}

                {/* Performed By */}
                <div className="bg-gray-50 rounded-lg p-4">
                  <p className="text-xs text-gray-500 uppercase tracking-wide font-medium">Performed By</p>
                  <div className="mt-1 space-y-1">
                    {selectedLog.performed_by_email && (
                      <p className="text-sm text-gray-900">{selectedLog.performed_by_email}</p>
                    )}
                    <p className="text-xs font-mono text-gray-600">{selectedLog.performed_by}</p>
                    {selectedLog.performed_by_role && (
                      <span className="inline-block text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded">
                        {selectedLog.performed_by_role}
                      </span>
                    )}
                  </div>
                </div>

                {/* Timestamp */}
                <div className="bg-gray-50 rounded-lg p-4">
                  <p className="text-xs text-gray-500 uppercase tracking-wide font-medium">Timestamp</p>
                  <p className="text-sm text-gray-900 mt-1">{formatDate(selectedLog.created_at)}</p>
                  <p className="text-xs text-gray-500 mt-0.5">UTC: {selectedLog.created_at}</p>
                </div>

                {/* Metadata */}
                {selectedLog.metadata && Object.keys(selectedLog.metadata).length > 0 && (
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-xs text-gray-500 uppercase tracking-wide font-medium mb-3">Additional Details</p>
                    <div className="space-y-2">
                      {Object.entries(selectedLog.metadata).map(([key, value]) => (
                        <div key={key} className="flex justify-between items-start py-2 border-b border-gray-200 last:border-0">
                          <span className="text-sm text-gray-600 capitalize">{key.replace(/_/g, ' ')}</span>
                          <span className="text-sm font-medium text-gray-900 text-right max-w-[60%] break-all">
                            {typeof value === 'boolean' ? (value ? 'Yes' : 'No') : String(value)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Log ID */}
                <div className="border-t pt-4">
                  <p className="text-xs text-gray-400">
                    Log ID: <span className="font-mono">{selectedLog.id}</span>
                  </p>
                </div>
              </div>

              {/* Footer */}
              <div className="p-4 bg-gray-50 border-t">
                <button 
                  onClick={() => setSelectedLog(null)}
                  className="w-full py-2.5 bg-gray-900 text-white font-medium rounded-lg hover:bg-gray-800 transition-colors"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
