/**
 * AdminUserDetails - Extracted User Details Panel from AdminDashboard
 * 
 * This component renders the User Details view when a user is selected in the admin panel.
 * All state management and handlers remain in the parent AdminDashboard for safety.
 * 
 * CRITICAL: This is used in a live banking application. Changes must preserve all functionality.
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
 * - setShowPasswordModal: Function to show password change modal
 * - authHistory: Login history array
 * - authHistoryLoading: Loading state for auth history
 * - showAuthHistory/setShowAuthHistory: Auth history visibility state
 * - fetchAuthHistory: Function to fetch auth history
 * - handleOpenEditIban: Handler to open IBAN edit modal
 * - handleDeleteUser: User deletion handler
 * - deleteUserLoading: Loading state for delete operation
 * - userNotes/setUserNotes: Admin notes state
 * - editingNotes/setEditingNotes: Notes editing state
 * - savingNotes: Loading state for saving notes
 * - handleSaveNotes: Handler for saving notes
 * - EnhancedLedgerTools: Ledger tools component
 * - formatCurrency: Currency formatting function
 */
import React from 'react';
import { StatusBadge, KycBadge, CopyPhoneButton, CopyEmailButton } from './AdminUsersSection';

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
  setShowPasswordModal,
  setNewPassword,
  setConfirmPassword,
  setPasswordChangeError,
  authHistory,
  authHistoryLoading,
  showAuthHistory,
  setShowAuthHistory,
  fetchAuthHistory,
  handleOpenEditIban,
  handleDeleteUser,
  deleteUserLoading,
  userNotes,
  setUserNotes,
  editingNotes,
  setEditingNotes,
  savingNotes,
  handleSaveNotes,
  EnhancedLedgerTools,
  formatCurrency,
  openDomainChangeModal
}) {
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
                className="px-3 py-1 text-sm border border-red-600 text-red-600 rounded hover:bg-red-50"
                data-testid="disable-user-btn"
              >Disable</button>
            ) : (
              <button
                onClick={() => {
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
                }}
                className="px-3 py-1 text-sm border border-green-600 text-green-600 rounded hover:bg-green-50"
                data-testid="enable-user-btn"
              >Enable</button>
            )}
            
            {/* Demote Admin Button - Only show for admin/super_admin users (but not yourself) */}
            {selectedUser && selectedUser.user && 
             (selectedUser.user.role === 'ADMIN' || selectedUser.user.role === 'SUPER_ADMIN') &&
             selectedUser.user.id !== user.id && (
              <button
                onClick={() => {
                  if (window.confirm(
                    `⚠️ DEMOTE ADMIN USER\n\n` +
                    `User: ${selectedUser.user.first_name} ${selectedUser.user.last_name}\n` +
                    `Email: ${selectedUser.user.email}\n` +
                    `Current Role: ${selectedUser.user.role}\n\n` +
                    `This will change their role from ${selectedUser.user.role} to USER.\n` +
                    `They will lose all admin privileges immediately.\n\n` +
                    `Are you sure you want to proceed?`
                  )) {
                    api.post(`/admin/users/${selectedUser.user.id}/demote`)
                      .then(response => {
                        toast.success(response.data.message || 'User demoted successfully');
                        fetchUsers(); // Refresh the user list
                        setSelectedUser(null); // Close the details panel
                      })
                      .catch(err => {
                        console.error('Demote error:', err);
                        toast.error(err.response?.data?.detail || 'Failed to demote user');
                      });
                  }
                }}
                className="px-3 py-1 text-sm border border-orange-600 text-orange-600 rounded hover:bg-orange-50"
                data-testid="demote-user-btn"
                title="Demote this admin user to regular user"
              >
                <span className="flex items-center space-x-1">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6" />
                  </svg>
                  <span>Demote to User</span>
                </span>
              </button>
            )}
            
            {/* Delete User Button - Disabled for admin users */}
            <button
              onClick={handleDeleteUser}
              disabled={deleteUserLoading || selectedUser.user.role === 'ADMIN' || selectedUser.user.role === 'SUPER_ADMIN'}
              className={`px-3 py-1 text-sm rounded flex items-center space-x-1 ${
                selectedUser.user.role === 'ADMIN' || selectedUser.user.role === 'SUPER_ADMIN'
                  ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  : 'bg-red-600 text-white hover:bg-red-700 disabled:opacity-50'
              }`}
              data-testid="delete-user-btn"
              title={
                selectedUser.user.role === 'ADMIN' || selectedUser.user.role === 'SUPER_ADMIN'
                  ? 'Cannot delete admin users - demote first'
                  : 'Permanently delete this user'
              }
            >
              {deleteUserLoading ? (
                <svg className="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              ) : (
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              )}
              <span>Delete</span>
            </button>
            {/* Clear Notifications Button */}
            <button
              onClick={() => {
                if (window.confirm('Are you sure you want to clear all notifications for this user? This action cannot be undone.')) {
                  api.delete(`/admin/users/${selectedUser.user.id}/notifications`)
                    .then((res) => { 
                      toast.success(`Cleared ${res.data.deleted_count} notifications`); 
                    })
                    .catch((err) => {
                      console.error('Clear notifications error:', err);
                      toast.error('Failed to clear notifications');
                    });
                }
              }}
              className="px-3 py-1 text-sm border border-gray-400 text-gray-600 rounded hover:bg-gray-50 flex items-center space-x-1"
              data-testid="clear-notifications-btn"
              title="Clear all notifications for this user"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
              </svg>
              <span>Clear Notifications</span>
            </button>
            <button
              onClick={() => openDomainChangeModal(selectedUser.user.id)}
              className="px-3 py-1 text-sm border border-blue-400 text-blue-600 rounded hover:bg-blue-50 flex items-center space-x-1"
              data-testid="send-domain-change-btn"
              title="Send domain change notification to this user"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
              <span>Notify Domain Change</span>
            </button>
          </div>
        </div>
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
            <dd className="font-semibold mt-1">
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
          <div className="col-span-2 border-t pt-4 mt-2">
            <dt className="text-sm text-gray-700 font-medium flex items-center justify-between">
              <span className="flex items-center space-x-2">
                <svg className="w-4 h-4 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
                <span>Password (Admin Only)</span>
              </span>
              <button
                onClick={() => {
                  setNewPassword('');
                  setConfirmPassword('');
                  setPasswordChangeError('');
                  setShowPasswordModal(true);
                }}
                className="text-xs px-2 py-1 bg-amber-100 text-amber-700 hover:bg-amber-200 rounded flex items-center space-x-1"
                title="Change customer password"
                data-testid="change-password-btn"
              >
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                </svg>
                <span>Change</span>
              </button>
            </dt>
            <dd className="mt-1 flex items-center space-x-2">
              <code className="px-3 py-2 bg-gray-100 border border-gray-300 rounded font-mono text-sm inline-block min-w-[150px]" data-testid="user-password-display">
                {showPassword 
                  ? (selectedUser.user.password_plain || 'Not available')
                  : '••••••••••••'
                }
              </code>
              <button
                onClick={() => setShowPassword(!showPassword)}
                className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
                title={showPassword ? 'Hide password' : 'Show password'}
                data-testid="toggle-password-visibility"
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
            </dd>
          </div>
          
          {/* Login Activity Button */}
          <div className="col-span-2 border-t pt-4 mt-2">
            <button
              onClick={fetchAuthHistory}
              disabled={authHistoryLoading}
              className="w-full py-2 px-4 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg flex items-center justify-center space-x-2 transition-colors"
              data-testid="view-login-activity-btn"
            >
              {authHistoryLoading ? (
                <svg className="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-25" />
                  <path d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" fill="currentColor" className="opacity-75" />
                </svg>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span>{showAuthHistory ? 'Refresh Login Activity' : 'View Login Activity'}</span>
                </>
              )}
            </button>
          </div>
        </dl>
      </div>

      {/* Admin Notes Card */}
      <div className="card p-6">
        <div className="flex justify-between items-start mb-4">
          <div>
            <h3 className="font-semibold text-lg flex items-center space-x-2">
              <svg className="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
              <span>Admin Notes</span>
            </h3>
            <p className="text-sm text-gray-700 mt-1">Private notes about this user (only visible to admins)</p>
          </div>
          {!editingNotes && (
            <button
              onClick={() => setEditingNotes(true)}
              className="px-3 py-1 text-sm border border-blue-600 text-blue-600 rounded hover:bg-blue-50 flex items-center space-x-1"
              data-testid="edit-notes-btn"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
              </svg>
              <span>Edit</span>
            </button>
          )}
        </div>
        
        {editingNotes ? (
          <div className="space-y-3">
            <textarea
              value={userNotes}
              onChange={(e) => setUserNotes(e.target.value)}
              rows={4}
              placeholder="Add notes about this user..."
              className="input-field w-full resize-y min-h-[100px] max-h-[300px]"
              style={{ resize: 'vertical' }}
              data-testid="user-notes-textarea"
            />
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-500">
                {userNotes.length} characters
              </span>
              <div className="flex space-x-2">
                <button
                  onClick={() => {
                    setUserNotes(selectedUser.user.admin_notes || '');
                    setEditingNotes(false);
                  }}
                  className="px-3 py-1.5 text-sm border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveNotes}
                  disabled={savingNotes}
                  className="px-4 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center space-x-1"
                  data-testid="save-notes-btn"
                >
                  {savingNotes ? (
                    <>
                      <svg className="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                      </svg>
                      <span>Saving...</span>
                    </>
                  ) : (
                    <>
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      <span>Save Notes</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 min-h-[80px]">
            {selectedUser.user.admin_notes && selectedUser.user.admin_notes.trim() !== '' ? (
              <p className="text-sm text-gray-700 whitespace-pre-wrap">{selectedUser.user.admin_notes}</p>
            ) : (
              <p className="text-sm text-gray-400 italic">No notes added for this user</p>
            )}
          </div>
        )}
      </div>

      {/* Login Activity Card */}
      {showAuthHistory && (
        <div className="card p-6" data-testid="auth-history-card">
          <div className="flex justify-between items-start mb-4">
            <div>
              <h3 className="font-semibold text-lg flex items-center space-x-2">
                <svg className="w-5 h-5 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span>Login Activity</span>
              </h3>
              <p className="text-sm text-gray-500 mt-1">Authentication history for this user</p>
            </div>
            <button
              onClick={() => setShowAuthHistory(false)}
              className="text-gray-400 hover:text-gray-600"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          
          {authHistory.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              No authentication events found
            </div>
          ) : (
            <div className="space-y-3 max-h-[400px] overflow-y-auto">
              {authHistory.map((event) => (
                <div key={event.id} className="bg-gray-50 rounded-lg p-3 border border-gray-200">
                  <div className="flex justify-between items-start">
                    <div className="flex items-center space-x-2">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                        event.action.includes('SUCCESS') 
                          ? 'bg-green-100 text-green-800' 
                          : event.action.includes('FAILED') || event.action.includes('BLOCKED')
                            ? 'bg-red-100 text-red-800'
                            : event.action.includes('LOGOUT')
                              ? 'bg-blue-100 text-blue-800'
                              : event.action.includes('CHANGED')
                                ? 'bg-amber-100 text-amber-800'
                                : 'bg-gray-100 text-gray-800'
                      }`}>
                        {event.action.replace(/_/g, ' ')}
                      </span>
                    </div>
                    <span className="text-xs text-gray-500">
                      {new Date(event.created_at).toLocaleString()}
                    </span>
                  </div>
                  <p className="text-sm text-gray-600 mt-1">{event.description}</p>
                  <div className="flex flex-wrap gap-2 mt-2 text-xs text-gray-500">
                    {event.ip_address && event.ip_address !== 'N/A' && (
                      <span className="bg-gray-100 px-2 py-0.5 rounded">
                        IP: {event.ip_address}
                      </span>
                    )}
                    {event.source && (
                      <span className="bg-gray-100 px-2 py-0.5 rounded">
                        Source: {event.source}
                      </span>
                    )}
                    {event.actor_email && event.actor_email !== selectedUser.user.email && (
                      <span className="bg-amber-100 text-amber-700 px-2 py-0.5 rounded">
                        By: {event.actor_email}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

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
                <h4 className="font-semibold text-gray-800">No Active Tax Hold</h4>
                <p className="text-sm text-gray-600">This user can perform all banking operations normally.</p>
              </div>
            </div>
            <button
              onClick={() => setShowTaxHoldModal(true)}
              className="mt-4 px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 transition"
              data-testid="set-tax-hold-btn"
            >
              Place Tax Hold
            </button>
          </div>
        )}
      </div>

      {selectedUser.accounts.length > 0 && (
        <div className="card p-6">
          <h3 className="font-semibold mb-4">Accounts</h3>
          {selectedUser.accounts.map(acc => (
            <div key={acc.id} className="border rounded p-4 mb-4">
              <div className="flex justify-between items-start">
                <div>
                  <p className="font-mono text-sm">{acc.iban || 'Not set'}</p>
                  {acc.bic && <p className="font-mono text-xs text-gray-500">BIC: {acc.bic}</p>}
                </div>
                <div className="flex items-center gap-4">
                  <button
                    onClick={() => handleOpenEditIban(acc)}
                    className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 font-medium transition"
                    data-testid={`edit-iban-btn-${acc.id}`}
                  >
                    Edit IBAN
                  </button>
                  <p className="text-xl font-bold">{formatCurrency(acc.balance)}</p>
                </div>
              </div>
              <EnhancedLedgerTools account={acc} onSuccess={() => viewUserDetails(selectedUser.user.id)} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default AdminUserDetails;
