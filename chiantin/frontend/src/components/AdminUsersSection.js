/**
 * AdminUsersSection - Extracted Users section from AdminDashboard
 * 
 * This component renders the Users table and User Details view.
 * All state management remains in the parent AdminDashboard for safety.
 * 
 * Props:
 * - users: Array of user objects to display
 * - filteredUsers: Array of filtered users (after search/filters applied)
 * - loading: Boolean indicating if data is loading
 * - selectedUser: Currently selected user object or null
 * - setSelectedUser: Function to set selected user
 * - searchQuery: Current search query string
 * - handleSearch: Function to handle search changes
 * - statusFilter/roleFilter/taxFilter/notesFilter: Filter values
 * - setStatusFilter/setRoleFilter/setTaxFilter/setNotesFilter: Filter setters
 * - pagination: Pagination object {page, limit, total, total_pages}
 * - usersPerPage/setUsersPerPage: Users per page controls
 * - currentPage/setCurrentPage: Current page controls
 * - fetchUsers: Function to fetch users
 * - viewUserDetails: Function to view user details
 * - toast: Toast notification helper
 * - api: API instance for making requests
 */
import React, { useState } from 'react';

// Status Badge Component - Professional colored badge for user account status
const StatusBadge = ({ status }) => {
  const normalizedStatus = (status || '').toUpperCase().trim();
  
  const getBadgeStyle = () => {
    switch (normalizedStatus) {
      case 'ACTIVE':
        return {
          bg: 'bg-green-100',
          text: 'text-green-800',
          icon: (
            <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
            </svg>
          )
        };
      case 'PENDING':
        return {
          bg: 'bg-amber-100',
          text: 'text-amber-800',
          icon: (
            <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
            </svg>
          )
        };
      case 'DISABLED':
      case 'SUSPENDED':
      case 'BLOCKED':
        return {
          bg: 'bg-red-100',
          text: 'text-red-800',
          icon: (
            <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M13.477 14.89A6 6 0 015.11 6.524l8.367 8.368zm1.414-1.414L6.524 5.11a6 6 0 018.367 8.367zM18 10a8 8 0 11-16 0 8 8 0 0116 0z" clipRule="evenodd" />
            </svg>
          )
        };
      default:
        return {
          bg: 'bg-gray-100',
          text: 'text-gray-700',
          icon: null
        };
    }
  };

  const style = getBadgeStyle();
  const displayLabel = normalizedStatus || 'Unknown';

  return (
    <span 
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${style.bg} ${style.text}`}
      data-testid="status-badge"
    >
      {style.icon}
      {displayLabel}
    </span>
  );
};

// KYC Status Badge Component
const KycBadge = ({ status }) => {
  const normalizedStatus = (status || '').toUpperCase().trim();
  
  const getBadgeStyle = () => {
    switch (normalizedStatus) {
      case 'APPROVED':
        return {
          bg: 'bg-green-100',
          text: 'text-green-800',
          label: 'Approved',
          icon: (
            <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
            </svg>
          )
        };
      case 'PENDING':
      case 'SUBMITTED':
      case 'UNDER_REVIEW':
      case 'UNDER REVIEW':
        return {
          bg: 'bg-blue-100',
          text: 'text-blue-800',
          label: normalizedStatus === 'UNDER_REVIEW' || normalizedStatus === 'UNDER REVIEW' ? 'Under Review' : 'Pending',
          icon: (
            <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
            </svg>
          )
        };
      case 'REJECTED':
      case 'DECLINED':
        return {
          bg: 'bg-red-100',
          text: 'text-red-800',
          label: 'Rejected',
          icon: (
            <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          )
        };
      case '':
      case 'NOT SUBMITTED':
      case 'NOT_SUBMITTED':
      case 'NONE':
        return {
          bg: 'bg-slate-100',
          text: 'text-slate-600',
          label: 'Not submitted',
          icon: (
            <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
            </svg>
          )
        };
      default:
        return {
          bg: 'bg-gray-100',
          text: 'text-gray-700',
          label: status || 'Unknown',
          icon: null
        };
    }
  };

  const style = getBadgeStyle();

  return (
    <span 
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${style.bg} ${style.text}`}
      data-testid="kyc-badge"
    >
      {style.icon}
      {style.label}
    </span>
  );
};

// Copy Phone Button Component
const CopyPhoneButton = ({ phone, toast, size = 'sm' }) => {
  const [copied, setCopied] = useState(false);
  
  if (!phone) return null;
  
  const handleCopy = async (e) => {
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(phone);
      setCopied(true);
      toast.success('Phone number copied');
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      toast.error('Failed to copy phone number');
    }
  };
  
  const sizeClasses = size === 'sm' ? 'p-1 w-6 h-6' : 'p-1.5 w-7 h-7';
  
  return (
    <button
      onClick={handleCopy}
      className={`inline-flex items-center justify-center ${sizeClasses} rounded hover:bg-gray-100 text-gray-500 hover:text-gray-700 transition-colors focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-red-500`}
      title={copied ? 'Copied!' : 'Copy phone number'}
      data-testid="copy-phone-button"
    >
      {copied ? (
        <svg className="w-4 h-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        </svg>
      ) : (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
        </svg>
      )}
    </button>
  );
};

// Copy Email Button Component
const CopyEmailButton = ({ email, toast, size = 'sm' }) => {
  const [copied, setCopied] = useState(false);
  
  if (!email) return null;
  
  const handleCopy = async (e) => {
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(email);
      setCopied(true);
      toast.success('Email address copied');
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      toast.error('Failed to copy email');
    }
  };
  
  const sizeClasses = size === 'sm' ? 'p-1 w-6 h-6' : 'p-1.5 w-7 h-7';
  
  return (
    <button
      onClick={handleCopy}
      className={`inline-flex items-center justify-center ${sizeClasses} rounded hover:bg-gray-100 text-gray-500 hover:text-gray-700 transition-colors focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-red-500`}
      title={copied ? 'Copied!' : 'Copy email address'}
      data-testid="copy-email-button"
    >
      {copied ? (
        <svg className="w-4 h-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        </svg>
      ) : (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
        </svg>
      )}
    </button>
  );
};

// Admin Users Table Component
function AdminUsersTable({ users, loading, onSelectUser, selectedUser, toast }) {
  if (loading) {
    return (
      <div className="card p-8 flex justify-center">
        <div className="flex items-center space-x-3">
          <svg className="animate-spin h-5 w-5 text-red-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span className="text-gray-600">Loading users...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="card overflow-x-auto">
      <table className="w-full">
        <thead className="bg-gray-50 border-b">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Email</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Phone</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Role</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Flags</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Created</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {users.map(user => (
            <tr 
              key={user.id} 
              onClick={() => onSelectUser(user.id)}
              className="hover:bg-gray-50 cursor-pointer"
            >
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm font-medium text-gray-900">
                  {user.first_name} {user.last_name}
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm text-gray-600 flex items-center gap-1" data-testid={`user-email-${user.id}`}>
                  <span>{user.email}</span>
                  <CopyEmailButton email={user.email} toast={toast} size="sm" />
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm text-gray-600 flex items-center gap-1" data-testid={`user-phone-${user.id}`}>
                  {user.phone ? (
                    <>
                      <span>{user.phone}</span>
                      <CopyPhoneButton phone={user.phone} toast={toast} size="sm" />
                    </>
                  ) : (
                    <span className="text-gray-400 italic">—</span>
                  )}
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <span className="badge badge-info">{user.role}</span>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <span className={`badge ${user.status === 'ACTIVE' ? 'badge-success' : 'badge-gray'}`}>
                  {user.status}
                </span>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="flex items-center space-x-2">
                  {user.has_tax_hold && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800" title="User has active tax hold">
                      🔴 TAX
                    </span>
                  )}
                  {user.admin_notes && user.admin_notes.trim() !== '' && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800" title="User has admin notes">
                      📝
                    </span>
                  )}
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                {new Date(user.created_at).toLocaleDateString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export { AdminUsersTable, StatusBadge, KycBadge, CopyPhoneButton, CopyEmailButton };
export default AdminUsersTable;
