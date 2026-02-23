/**
 * AdminUserDetails - Extracted User Details Panel from AdminDashboard
 * 
 * This component renders the User Details view when a user is selected in the admin panel.
 * All state management and handlers remain in the parent AdminDashboard.
 * 
 * Props passed from parent:
 * - selectedUser: The currently selected user object
 * - setSelectedUser: Function to clear selected user (back button)
 * - user: Current admin user (for role checks)
 * - api: API instance for requests
 * - toast: Toast notification helper
 * - fetchUsers: Function to refresh users list
 * - viewUserDetails: Function to refresh user details
 * - userTaxHold: Tax hold status object
 * - taxHoldLoading: Loading state for tax hold operations
 * - setShowTaxHoldModal: Function to show tax hold modal
 * - handleRemoveTaxHold: Handler for removing tax hold
 * - showPassword/setShowPassword: Password visibility toggle
 * - handleChangePassword: Password change handler
 * - handleUpdateNotes: Notes update handler
 * - handleDeleteUser: User deletion handler
 * - authHistory: Login history array
 * - authHistoryLoading: Loading state for auth history
 * - showAuthHistoryModal/setShowAuthHistoryModal: Auth history modal state
 * - fetchAuthHistory: Function to fetch auth history
 * - handleUpdateIBAN: IBAN update handler
 */
import React, { useState } from 'react';
import { StatusBadge, KycBadge, CopyPhoneButton, CopyEmailButton } from './AdminUsersSection';

// Enhanced Ledger Tools Component - inline for now
const EnhancedLedgerTools = ({ account, onSuccess }) => {
  return null; // Placeholder - actual implementation is in parent
};

function AdminUserDetails({
  selectedUser,
  setSelectedUser,
  user,
  api,
  toast,
  fetchUsers,
  viewUserDetails,
  userTaxHold,
  taxHoldLoading,
  setShowTaxHoldModal,
  handleRemoveTaxHold,
  showPassword,
  setShowPassword,
  handleChangePassword,
  handleUpdateNotes,
  handleDeleteUser,
  authHistory,
  authHistoryLoading,
  showAuthHistoryModal,
  setShowAuthHistoryModal,
  fetchAuthHistory,
  handleUpdateIBAN,
  EnhancedLedgerToolsComponent
}) {
  const [localNotes, setLocalNotes] = useState(selectedUser?.user?.admin_notes || '');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  // Use the passed EnhancedLedgerTools or default to empty
  const LedgerTools = EnhancedLedgerToolsComponent || (() => null);

  if (!selectedUser) return null;

  return (
    <div className="space-y-6">
      {/* Back Button */}
      <div className="mb-4">
        <button
          onClick={() => setSelectedUser(null)}
          className="flex items-center space-x-2 text-gray-600 hover:text-gray-900 transition"
          data-testid="back-to-users-btn"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          <span className="font-medium">Back to Users</span>
        </button>
      </div>

      {/* User Details Card */}
      <div className="card p-6">
        <div className="flex justify-between items-start mb-4">
          <h2 className="text-lg font-semibold">User Details</h2>
          <div className="flex space-x-2">
            {/* Verify Email Button - Only show if email is NOT verified */}
            {selectedUser.user.email_verified === false && (
              <button
                onClick={() => {
                  if (window.confirm(
                    `Manually verify email for ${selectedUser.user.email}?\n\n` +
                    `This will allow the user to log in without going through email verification.\n\n` +
                    `Only use this if the user is having trouble receiving verification emails.`
                  )) {
                    api.post(`/admin/users/${selectedUser.user.id}/verify-email`)
                      .then(() => { 
                        toast.success('Email verified successfully'); 
                        fetchUsers();
                        viewUserDetails(selectedUser.user.id); 
                      })
                      .catch((err) => {
                        console.error('Verify email error:', err);
                        toast.error('Failed to verify email');
                      });
                  }
                }}
                className="px-3 py-1 text-sm border border-blue-600 text-blue-600 rounded hover:bg-blue-50"
                data-testid="verify-email-btn"
              >Verify Email</button>
            )}
            
            {selectedUser.user.status === 'ACTIVE' ? (
              <button
                onClick={() => {
                  if (window.confirm('Disable this user?')) {
                    api.patch(`/admin/users/${selectedUser.user.id}/status`, { status: 'DISABLED' })
                      .then(() => { 
                        toast.success('User disabled'); 
                        fetchUsers();
                        viewUserDetails(selectedUser.user.id); 
                      })
                      .catch((err) => {
                        console.error('Disable error:', err);
                        toast.error('Failed to disable user');
                      });
                  }
                }}
                className="px-3 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700"
                data-testid="disable-user-btn"
              >Disable</button>
            ) : (
              <button
                onClick={() => {
                  if (window.confirm('Enable this user?')) {
                    api.patch(`/admin/users/${selectedUser.user.id}/status`, { status: 'ACTIVE' })
                      .then(() => { 
                        toast.success('User enabled'); 
                        fetchUsers();
                        viewUserDetails(selectedUser.user.id); 
                      })
                      .catch((err) => {
                        console.error('Enable error:', err);
                        toast.error('Failed to enable user');
                      });
                  }
                }}
                className="px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700"
                data-testid="enable-user-btn"
              >Enable</button>
            )}
            
            {/* Demote Admin Button - Only show for admin users */}
            {selectedUser && selectedUser.user && 
             (selectedUser.user.role === 'ADMIN' || selectedUser.user.role === 'SUPER_ADMIN') &&
             selectedUser.user.id !== user.id && (
              <button
                onClick={() => {
                  if (window.confirm(
                    `⚠️ DEMOTE ADMIN USER ⚠️\n\n` +
                    `User: ${selectedUser.user.first_name} ${selectedUser.user.last_name}\n` +
                    `Email: ${selectedUser.user.email}\n` +
                    `Current Role: ${selectedUser.user.role}\n\n` +
                    `This will change their role from ${selectedUser.user.role} to USER.\n` +
                    `They will lose all admin privileges.\n\n` +
                    `Are you sure?`
                  )) {
                    api.post(`/admin/users/${selectedUser.user.id}/demote`)
                      .then(() => { 
                        toast.success('User demoted from admin'); 
                        fetchUsers();
                        viewUserDetails(selectedUser.user.id); 
                      })
                      .catch((err) => {
                        console.error('Demote error:', err);
                        toast.error('Failed to demote user');
                      });
                  }
                }}
                className="px-3 py-1 text-sm border border-orange-600 text-orange-600 rounded hover:bg-orange-50"
                data-testid="demote-admin-btn"
              >Demote Admin</button>
            )}
            
            <button
              onClick={handleDeleteUser}
              className="px-3 py-1 text-sm border border-red-600 text-red-600 rounded hover:bg-red-50"
              data-testid="delete-user-btn"
            >Delete</button>
            
            <button
              onClick={async () => {
                try {
                  await api.delete(`/admin/users/${selectedUser.user.id}/notifications`);
                  toast.success('All notifications cleared for this user');
                } catch (err) {
                  console.error('Clear notifications error:', err);
                  toast.error('Failed to clear notifications');
                }
              }}
              className="px-3 py-1 text-sm border border-gray-400 text-gray-600 rounded hover:bg-gray-50"
              title="Clear all notification badges for this user"
              data-testid="clear-notifications-btn"
            >
              <svg className="w-4 h-4 inline mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
              </svg>
              Clear Notifications
            </button>
          </div>
        </div>
        
        {/* User Info Grid */}
        <dl className="grid grid-cols-2 gap-4">
          <div><dt className="text-sm text-gray-700 font-medium">Name</dt><dd className="font-semibold mt-1">{selectedUser.user.first_name} {selectedUser.user.last_name}</dd></div>
          <div>
            <dt className="text-sm text-gray-700 font-medium">Email</dt>
            <dd className="font-semibold mt-1 flex items-center gap-1" data-testid="user-detail-email">
              <span>{selectedUser.user.email}</span>
              <CopyEmailButton email={selectedUser.user.email} toast={toast} size="md" />
            </dd>
          </div>
          <div>
            <dt className="text-sm text-gray-700 font-medium">Phone</dt>
            <dd className="font-semibold mt-1 flex items-center gap-1" data-testid="user-detail-phone">
              {selectedUser.user.phone ? (
                <>
                  <span>{selectedUser.user.phone}</span>
                  <CopyPhoneButton phone={selectedUser.user.phone} toast={toast} size="md" />
                </>
              ) : (
                <span className="text-gray-400 italic">Not provided</span>
              )}
            </dd>
          </div>
          <div>
            <dt className="text-sm text-gray-700 font-medium">Status</dt>
            <dd className="mt-1" data-testid="user-detail-status">
              <StatusBadge status={selectedUser.user.status} />
            </dd>
          </div>
          <div>
            <dt className="text-sm text-gray-700 font-medium">Email Verified</dt>
            <dd className="mt-1">
              {selectedUser.user.email_verified ? (
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                  <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  Verified
                </span>
              ) : (
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800">
                  <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                  Not Verified
                </span>
              )}
            </dd>
          </div>
          <div>
            <dt className="text-sm text-gray-700 font-medium">KYC</dt>
            <dd className="mt-1" data-testid="user-detail-kyc">
              <KycBadge status={selectedUser.kyc_status} />
            </dd>
          </div>
        </dl>
        
        {/* Password Section */}
        <div className="mt-6 pt-4 border-t">
          <div className="flex items-center space-x-3">
            <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
            <span className="text-sm font-medium text-gray-700">Password (Admin Only)</span>
          </div>
          <div className="mt-2 flex items-center space-x-2">
            <div className="relative flex-grow max-w-xs">
              <input
                type={showPassword ? 'text' : 'password'}
                value={selectedUser.user.password_plain || '••••••••••••'}
                readOnly
                className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-gray-700 font-mono"
                data-testid="user-password-field"
              />
              <button
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-gray-400 hover:text-gray-600"
                title={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                  </svg>
                ) : (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                )}
              </button>
            </div>
            <button
              onClick={() => handleChangePassword(newPassword, confirmPassword)}
              className="px-3 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              data-testid="change-password-btn"
            >
              <svg className="w-4 h-4 inline mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
              </svg>
              Change
            </button>
          </div>
        </div>
      </div>
      
      {/* View Login Activity Button */}
      <div className="card p-4">
        <button
          onClick={fetchAuthHistory}
          disabled={authHistoryLoading}
          className="w-full flex items-center justify-center space-x-2 text-gray-600 hover:text-gray-900 transition"
          data-testid="view-login-activity-btn"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>{authHistoryLoading ? 'Loading...' : 'View Login Activity'}</span>
        </button>
      </div>
      
      {/* Admin Notes Section */}
      <div className="card p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <h3 className="font-semibold text-lg">Admin Notes</h3>
          </div>
          <p className="text-xs text-gray-500">Private notes about this user (only visible to admins)</p>
        </div>
        
        <textarea
          value={localNotes}
          onChange={(e) => setLocalNotes(e.target.value)}
          placeholder="No notes added for this user"
          className="w-full p-3 border border-gray-200 rounded-lg min-h-[100px] resize-y focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          data-testid="admin-notes-textarea"
        />
        
        <div className="mt-3 flex justify-end">
          <button
            onClick={() => handleUpdateNotes(localNotes)}
            className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition"
            data-testid="save-notes-btn"
          >
            <svg className="w-4 h-4 inline mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            Save Notes
          </button>
        </div>
      </div>
      
      {/* Tax Hold Management Card */}
      <div className="card p-6">
        <div className="flex justify-between items-start mb-4">
          <div>
            <h3 className="font-semibold text-lg">Tax Hold Management</h3>
            <p className="text-sm text-gray-500 mt-1">Restrict user from performing banking operations due to tax obligations</p>
          </div>
          {userTaxHold?.is_blocked ? (
            <span className="px-3 py-1 text-sm font-medium bg-red-100 text-red-800 rounded-full">
              BLOCKED
            </span>
          ) : (
            <span className="px-3 py-1 text-sm font-medium bg-green-100 text-green-800 rounded-full">
              CLEAR
            </span>
          )}
        </div>

        {userTaxHold?.is_blocked ? (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
            <div className="flex items-start space-x-3">
              <svg className="w-6 h-6 text-red-600 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <div className="flex-1">
                <h4 className="font-semibold text-red-800">Account Restricted</h4>
                <p className="text-sm text-red-700 mt-1">
                  Tax Amount Due: <span className="font-bold">€{userTaxHold.tax_amount_due?.toLocaleString('de-DE', { minimumFractionDigits: 2 })}</span>
                </p>
                <p className="text-sm text-red-600 mt-1">Reason: {userTaxHold.reason || 'Outstanding tax obligations'}</p>
                {userTaxHold.blocked_at && (
                  <p className="text-xs text-red-500 mt-2">
                    Blocked since: {new Date(userTaxHold.blocked_at).toLocaleString()}
                  </p>
                )}
              </div>
            </div>
            <div className="mt-4 flex space-x-3">
              <button
                onClick={handleRemoveTaxHold}
                disabled={taxHoldLoading}
                className="px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700 disabled:opacity-50 transition"
                data-testid="remove-tax-hold-btn"
              >
                {taxHoldLoading ? 'Processing...' : 'Remove Tax Hold'}
              </button>
              <button
                onClick={() => setShowTaxHoldModal(true)}
                className="px-4 py-2 border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 transition"
              >
                Update Amount
              </button>
            </div>
          </div>
        ) : (
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 mb-4">
            <div className="flex items-center space-x-3">
              <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div>
                <h4 className="font-semibold text-gray-800">No Tax Hold Active</h4>
                <p className="text-sm text-gray-600">User can perform all banking operations normally.</p>
              </div>
            </div>
            <button
              onClick={() => setShowTaxHoldModal(true)}
              className="mt-4 px-4 py-2 border border-red-300 text-red-700 text-sm font-medium rounded-lg hover:bg-red-50 transition"
              data-testid="add-tax-hold-btn"
            >
              <svg className="w-4 h-4 inline mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v3m0 0v3m0-3h3m-3 0H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Add Tax Hold
            </button>
          </div>
        )}
      </div>
      
      {/* User Accounts */}
      {selectedUser.accounts && selectedUser.accounts.length > 0 && (
        <div className="card p-6">
          <h3 className="font-semibold text-lg mb-4">User Accounts</h3>
          <div className="space-y-4">
            {selectedUser.accounts.map((acc, idx) => (
              <div key={idx} className="border rounded-lg p-4">
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <p className="font-medium">{acc.account_type} Account</p>
                    <p className="text-sm text-gray-500">IBAN: {acc.iban || 'Not assigned'}</p>
                    <p className="text-sm text-gray-500">BIC: {acc.bic || 'ECOMBXXX'}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-xl font-bold text-green-600">
                      €{acc.balance?.toLocaleString('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </p>
                    <p className="text-xs text-gray-400">Available Balance</p>
                  </div>
                </div>
                
                {/* Edit IBAN Section */}
                <div className="mt-3 pt-3 border-t">
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-gray-600">Update IBAN:</span>
                    <input
                      type="text"
                      placeholder="Enter new IBAN"
                      defaultValue={acc.iban || ''}
                      className="flex-1 px-2 py-1 text-sm border rounded"
                      id={`iban-input-${idx}`}
                      data-testid={`iban-input-${idx}`}
                    />
                    <button
                      onClick={() => {
                        const newIban = document.getElementById(`iban-input-${idx}`)?.value;
                        if (newIban) {
                          handleUpdateIBAN(acc.id, newIban);
                        }
                      }}
                      className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
                      data-testid={`update-iban-btn-${idx}`}
                    >
                      Update
                    </button>
                  </div>
                </div>
                
                <LedgerTools account={acc} onSuccess={() => viewUserDetails(selectedUser.user.id)} />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default AdminUserDetails;
