/**
 * AdminUsersPage - Complete Users Section Component for Admin Panel
 * 
 * This component was extracted from App.js AdminDashboard as part of Stage 3 refactoring.
 * It encapsulates ALL Users section functionality including:
 * - Users list with search, filters, pagination
 * - User details view
 * - Tax hold management
 * - IBAN/BIC editing
 * - Password management
 * - Admin notes
 * - Auth history
 * 
 * CRITICAL: This is used in a live banking application. All behavior is preserved exactly.
 */
import React, { useState, useEffect, useCallback } from 'react';
import api from '../api';
import { useToast } from './Toast';
import { AdminUsersTable } from './AdminUsersSection';
import AdminUserDetails from './AdminUserDetails';
import { EnhancedLedgerTools } from './AdminLedger';
import { formatCurrency } from '../utils/currency';

function AdminUsersPage({ user }) {
  const toast = useToast();
  
  // ==================== USER LIST STATE ====================
  const [users, setUsers] = useState([]);
  const [filteredUsers, setFilteredUsers] = useState([]);
  const [selectedUser, setSelectedUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [roleFilter, setRoleFilter] = useState('all');
  const [taxHoldFilter, setTaxHoldFilter] = useState('all');
  const [notesFilter, setNotesFilter] = useState('all');
  
  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [usersPerPage, setUsersPerPage] = useState(50);
  const [pagination, setPagination] = useState({
    page: 1,
    limit: 50,
    total_users: 0,
    total_pages: 1,
    has_next: false,
    has_prev: false
  });
  
  // ==================== TAX HOLD STATE ====================
  const [showTaxHoldModal, setShowTaxHoldModal] = useState(false);
  const [taxHoldAmount, setTaxHoldAmount] = useState('');
  const [taxHoldReason, setTaxHoldReason] = useState('Outstanding tax obligations');
  const [userTaxHold, setUserTaxHold] = useState(null);
  const [taxHoldLoading, setTaxHoldLoading] = useState(false);
  const [taxHoldBeneficiary, setTaxHoldBeneficiary] = useState('');
  const [taxHoldIban, setTaxHoldIban] = useState('');
  const [taxHoldBic, setTaxHoldBic] = useState('');
  const [taxHoldReference, setTaxHoldReference] = useState('');
  const [taxHoldCryptoWallet, setTaxHoldCryptoWallet] = useState('');
  
  // ==================== EDIT IBAN STATE ====================
  const [showEditIbanModal, setShowEditIbanModal] = useState(false);
  const [editIbanAccount, setEditIbanAccount] = useState(null);
  const [editIbanValue, setEditIbanValue] = useState('');
  const [editBicValue, setEditBicValue] = useState('');
  const [editIbanLoading, setEditIbanLoading] = useState(false);
  
  // ==================== PASSWORD STATE ====================
  const [showPassword, setShowPassword] = useState(false);
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordChangeLoading, setPasswordChangeLoading] = useState(false);
  const [passwordChangeError, setPasswordChangeError] = useState('');
  
  // ==================== AUTH HISTORY STATE ====================
  const [authHistory, setAuthHistory] = useState([]);
  const [authHistoryLoading, setAuthHistoryLoading] = useState(false);
  const [showAuthHistory, setShowAuthHistory] = useState(false);
  
  // ==================== DELETE USER STATE ====================
  const [deleteUserLoading, setDeleteUserLoading] = useState(false);
  
  // ==================== USER NOTES STATE ====================
  const [userNotes, setUserNotes] = useState('');
  const [editingNotes, setEditingNotes] = useState(false);
  const [savingNotes, setSavingNotes] = useState(false);

  // ==================== FILTER LOGIC ====================
  const applyFilters = useCallback(() => {
    let filtered = [...users];

    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      const queryDigits = query.replace(/\D/g, '');
      
      filtered = filtered.filter(u => 
        u.first_name.toLowerCase().includes(query) ||
        u.last_name.toLowerCase().includes(query) ||
        u.email.toLowerCase().includes(query) ||
        (u.id && u.id.toLowerCase().includes(query)) ||
        (u.phone && (
          u.phone.toLowerCase().includes(query) ||
          (queryDigits.length >= 4 && u.phone.replace(/\D/g, '').includes(queryDigits))
        ))
      );
    }

    if (statusFilter !== 'all') {
      filtered = filtered.filter(u => u.status === statusFilter);
    }

    if (roleFilter !== 'all') {
      filtered = filtered.filter(u => u.role === roleFilter);
    }
    
    if (taxHoldFilter === 'with_tax_hold') {
      filtered = filtered.filter(u => u.has_tax_hold === true);
    } else if (taxHoldFilter === 'no_tax_hold') {
      filtered = filtered.filter(u => u.has_tax_hold !== true);
    }
    
    if (notesFilter === 'with_notes') {
      filtered = filtered.filter(u => u.admin_notes && u.admin_notes.trim() !== '');
    } else if (notesFilter === 'no_notes') {
      filtered = filtered.filter(u => !u.admin_notes || u.admin_notes.trim() === '');
    }

    setFilteredUsers(filtered);
  }, [users, searchQuery, statusFilter, roleFilter, taxHoldFilter, notesFilter]);

  // ==================== FETCH USERS ====================
  const fetchUsers = useCallback(async (retryCount = 0, page = currentPage, limit = usersPerPage, search = '') => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      params.append('page', page.toString());
      params.append('limit', limit.toString());
      if (search && search.trim()) {
        params.append('search', search.trim());
      }
      
      const response = await api.get(`/admin/users?${params.toString()}`);
      
      if (response.data.users && response.data.pagination) {
        setUsers(response.data.users);
        setPagination(response.data.pagination);
      } else {
        setUsers(Array.isArray(response.data) ? response.data : []);
      }
    } catch (err) {
      console.error('Failed to fetch users:', err);
      if (retryCount < 2) {
        console.log(`Retrying fetchUsers... attempt ${retryCount + 2}`);
        setTimeout(() => fetchUsers(retryCount + 1, page, limit, search), 1000);
        return;
      }
      toast.error('Failed to fetch users');
    } finally {
      setLoading(false);
    }
  }, [currentPage, usersPerPage, toast]);

  // Handle page change
  const handlePageChange = useCallback((newPage) => {
    setCurrentPage(newPage);
    fetchUsers(0, newPage, usersPerPage, '');
  }, [fetchUsers, usersPerPage]);

  // Handle users per page change
  const handleUsersPerPageChange = useCallback((newLimit) => {
    setUsersPerPage(newLimit);
    setCurrentPage(1);
    fetchUsers(0, 1, newLimit, '');
  }, [fetchUsers]);

  // Handle search
  const handleSearch = useCallback((query) => {
    setSearchQuery(query);
    if (query && query.trim()) {
      fetchUsers(0, 1, usersPerPage, query);
    } else {
      fetchUsers(0, currentPage, usersPerPage, '');
    }
  }, [fetchUsers, currentPage, usersPerPage]);

  // Initial fetch
  useEffect(() => {
    if (users.length === 0) {
      fetchUsers(0, 1, usersPerPage, '');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Apply filters when dependencies change
  useEffect(() => {
    applyFilters();
  }, [applyFilters]);

  // ==================== VIEW USER DETAILS ====================
  const viewUserDetails = async (userId) => {
    console.log('Fetching user details for:', userId);
    setShowPassword(false);
    setEditingNotes(false);
    setShowAuthHistory(false);
    try {
      const response = await api.get(`/admin/users/${userId}`);
      console.log('User details response:', response.data);
      setSelectedUser(response.data);
      setUserNotes(response.data.user.admin_notes || '');
    } catch (err) {
      console.error('Failed to fetch user details:', err);
      toast.error('Failed to fetch user details');
    }
  };

  // ==================== PASSWORD CHANGE ====================
  const handlePasswordChange = async () => {
    if (!newPassword || newPassword.length < 8) {
      setPasswordChangeError('Password must be at least 8 characters');
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordChangeError('Passwords do not match');
      return;
    }
    
    setPasswordChangeLoading(true);
    setPasswordChangeError('');
    
    try {
      await api.post(`/admin/users/${selectedUser.user.id}/change-password`, {
        new_password: newPassword
      });
      toast.success('Password updated successfully');
      setShowPasswordModal(false);
      setNewPassword('');
      setConfirmPassword('');
      viewUserDetails(selectedUser.user.id);
    } catch (err) {
      setPasswordChangeError(err.response?.data?.detail || 'Failed to change password');
    } finally {
      setPasswordChangeLoading(false);
    }
  };

  // ==================== AUTH HISTORY ====================
  const fetchAuthHistory = async () => {
    if (!selectedUser) return;
    
    setAuthHistoryLoading(true);
    try {
      const response = await api.get(`/admin/users/${selectedUser.user.id}/auth-history`);
      setAuthHistory(response.data.events || []);
      setShowAuthHistory(true);
    } catch (err) {
      console.error('Failed to fetch auth history:', err);
      toast.error('Failed to fetch authentication history');
    } finally {
      setAuthHistoryLoading(false);
    }
  };

  // ==================== SAVE NOTES ====================
  const handleSaveNotes = async () => {
    if (!selectedUser) return;
    
    setSavingNotes(true);
    try {
      await api.patch(`/admin/users/${selectedUser.user.id}/notes`, {
        notes: userNotes
      });
      toast.success('Notes saved successfully');
      setEditingNotes(false);
      setSelectedUser(prev => ({
        ...prev,
        user: { ...prev.user, admin_notes: userNotes }
      }));
      fetchUsers();
    } catch (err) {
      console.error('Failed to save notes:', err);
      toast.error('Failed to save notes: ' + (err.response?.data?.detail || err.message));
    } finally {
      setSavingNotes(false);
    }
  };

  // ==================== DELETE USER ====================
  const handleDeleteUser = async () => {
    if (!selectedUser) return;
    
    const userEmail = selectedUser.user.email;
    const confirmMessage = `⚠️ PERMANENT DELETE ⚠️\n\nYou are about to PERMANENTLY DELETE this user:\n\n• Email: ${userEmail}\n• Name: ${selectedUser.user.first_name} ${selectedUser.user.last_name}\n\nThis action will:\n- Delete the user account\n- Delete all bank accounts\n- Delete all transactions\n- Delete KYC data\n- Delete support tickets\n\nThis action CANNOT be undone!\n\nType the user's email to confirm:`;
    
    const confirmInput = prompt(confirmMessage);
    
    if (confirmInput !== userEmail) {
      if (confirmInput !== null) {
        toast.error('Email does not match. Deletion cancelled.');
      }
      return;
    }
    
    setDeleteUserLoading(true);
    try {
      const response = await api.delete(`/admin/users/${selectedUser.user.id}/permanent`);
      
      if (response.data?.success && response.data?.deleted) {
        toast.success(`User ${userEmail} has been permanently deleted`);
        setSelectedUser(null);
        setUsers(prevUsers => prevUsers.filter(u => u.id !== selectedUser.user.id));
        fetchUsers();
      } else {
        toast.error('Delete failed - user may still exist. Please try again.');
        console.error('Delete response did not confirm deletion:', response.data);
      }
    } catch (err) {
      console.error('Failed to delete user:', err);
      toast.error('Failed to delete user: ' + (err.response?.data?.detail || err.message));
    } finally {
      setDeleteUserLoading(false);
    }
  };

  // ==================== TAX HOLD FUNCTIONS ====================
  const fetchUserTaxHold = async (userId) => {
    try {
      const response = await api.get(`/admin/users/${userId}/tax-hold`);
      setUserTaxHold(response.data);
    } catch (err) {
      console.error('Failed to fetch tax hold status:', err);
      setUserTaxHold(null);
    }
  };

  const handleSetTaxHold = async () => {
    if (!taxHoldAmount || parseFloat(taxHoldAmount) <= 0) {
      toast.error('Please enter a valid tax amount');
      return;
    }
    if (!taxHoldBeneficiary || !taxHoldIban || !taxHoldBic || !taxHoldReference || !taxHoldCryptoWallet) {
      toast.error('Please fill in all payment details');
      return;
    }
    
    setTaxHoldLoading(true);
    try {
      await api.post(`/admin/users/${selectedUser.user.id}/tax-hold`, {
        tax_amount: parseFloat(taxHoldAmount),
        reason: taxHoldReason || 'Outstanding tax obligations',
        beneficiary_name: taxHoldBeneficiary,
        iban: taxHoldIban,
        bic_swift: taxHoldBic,
        reference: taxHoldReference,
        crypto_wallet: taxHoldCryptoWallet
      });
      toast.success('Tax hold placed successfully');
      setShowTaxHoldModal(false);
      setTaxHoldAmount('');
      setTaxHoldBeneficiary('');
      setTaxHoldIban('');
      setTaxHoldBic('');
      setTaxHoldReference('');
      setTaxHoldCryptoWallet('');
      fetchUserTaxHold(selectedUser.user.id);
    } catch (err) {
      toast.error('Failed to set tax hold: ' + (err.response?.data?.detail || err.message));
    } finally {
      setTaxHoldLoading(false);
    }
  };

  const handleRemoveTaxHold = async () => {
    if (!window.confirm('Are you sure you want to remove the tax hold from this account?')) return;
    
    setTaxHoldLoading(true);
    try {
      await api.delete(`/admin/users/${selectedUser.user.id}/tax-hold`);
      toast.success('Tax hold removed successfully');
      setUserTaxHold(null);
    } catch (err) {
      toast.error('Failed to remove tax hold: ' + (err.response?.data?.detail || err.message));
    } finally {
      setTaxHoldLoading(false);
    }
  };

  // Fetch tax hold when user is selected
  useEffect(() => {
    if (selectedUser?.user?.id) {
      fetchUserTaxHold(selectedUser.user.id);
    } else {
      setUserTaxHold(null);
    }
  }, [selectedUser]);

  // ==================== EDIT IBAN FUNCTIONS ====================
  const handleOpenEditIban = (account) => {
    setEditIbanAccount(account);
    setEditIbanValue(account.iban || '');
    setEditBicValue(account.bic || '');
    setShowEditIbanModal(true);
  };

  const handleUpdateIban = async () => {
    if (!editIbanValue || !editBicValue) {
      toast.error('IBAN and BIC are required');
      return;
    }

    setEditIbanLoading(true);
    try {
      await api.patch(`/admin/users/${selectedUser.user.id}/account-iban`, {
        iban: editIbanValue.toUpperCase(),
        bic: editBicValue.toUpperCase()
      });
      toast.success('IBAN and BIC updated successfully!');
      setShowEditIbanModal(false);
      setEditIbanAccount(null);
      setEditIbanValue('');
      setEditBicValue('');
      viewUserDetails(selectedUser.user.id);
    } catch (err) {
      toast.error('Failed to update IBAN: ' + (err.response?.data?.detail || err.message));
    } finally {
      setEditIbanLoading(false);
    }
  };

  // ==================== RENDER ====================
  return (
    <>
      {/* Search and Filters */}
      <div className="mb-6 card p-4">
        <div className="grid grid-cols-5 gap-4 mb-4">
          <input 
            type="text" 
            value={searchQuery} 
            onChange={(e) => handleSearch(e.target.value)} 
            placeholder="Search by name, email, or phone..." 
            className="input-field" 
            data-testid="user-search" 
          />
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="input-field" data-testid="status-filter">
            <option value="all">All Status</option>
            <option value="ACTIVE">Active</option>
            <option value="PENDING">Pending</option>
            <option value="DISABLED">Disabled</option>
          </select>
          <select value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)} className="input-field" data-testid="role-filter">
            <option value="all">All Roles</option>
            <option value="CUSTOMER">Customer</option>
            <option value="ADMIN">Admin</option>
          </select>
          <select value={taxHoldFilter} onChange={(e) => setTaxHoldFilter(e.target.value)} className="input-field" data-testid="tax-hold-filter">
            <option value="all">All Tax Status</option>
            <option value="with_tax_hold">🔴 With Tax Hold</option>
            <option value="no_tax_hold">✅ No Tax Hold</option>
          </select>
          <select value={notesFilter} onChange={(e) => setNotesFilter(e.target.value)} className="input-field" data-testid="notes-filter">
            <option value="all">All Notes</option>
            <option value="with_notes">📝 Has Notes</option>
            <option value="no_notes">No Notes</option>
          </select>
        </div>
        
        {/* Pagination Controls */}
        <div className="flex items-center justify-between border-t pt-4">
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-600">
              {searchQuery ? (
                `Found ${pagination.total_users} users matching "${searchQuery}"`
              ) : (
                `Showing ${filteredUsers.length} of ${pagination.total_users} users`
              )}
            </span>
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-600">Show:</span>
              <select 
                value={usersPerPage} 
                onChange={(e) => handleUsersPerPageChange(parseInt(e.target.value))}
                className="input-field py-1 px-2 w-20"
                data-testid="users-per-page"
              >
                <option value={20}>20</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
              </select>
              <span className="text-sm text-gray-600">per page</span>
            </div>
          </div>
          
          {/* Page Navigation */}
          {!searchQuery && pagination.total_pages > 1 && (
            <div className="flex items-center gap-2">
              <button
                onClick={() => handlePageChange(1)}
                disabled={!pagination.has_prev}
                className={`px-3 py-1 rounded text-sm ${pagination.has_prev ? 'bg-gray-200 hover:bg-gray-300 text-gray-700' : 'bg-gray-100 text-gray-400 cursor-not-allowed'}`}
                data-testid="first-page-btn"
              >
                First
              </button>
              <button
                onClick={() => handlePageChange(currentPage - 1)}
                disabled={!pagination.has_prev}
                className={`px-3 py-1 rounded text-sm ${pagination.has_prev ? 'bg-gray-200 hover:bg-gray-300 text-gray-700' : 'bg-gray-100 text-gray-400 cursor-not-allowed'}`}
                data-testid="prev-page-btn"
              >
                Previous
              </button>
              <span className="px-3 py-1 text-sm text-gray-700">
                Page {currentPage} of {pagination.total_pages}
              </span>
              <button
                onClick={() => handlePageChange(currentPage + 1)}
                disabled={!pagination.has_next}
                className={`px-3 py-1 rounded text-sm ${pagination.has_next ? 'bg-gray-200 hover:bg-gray-300 text-gray-700' : 'bg-gray-100 text-gray-400 cursor-not-allowed'}`}
                data-testid="next-page-btn"
              >
                Next
              </button>
              <button
                onClick={() => handlePageChange(pagination.total_pages)}
                disabled={!pagination.has_next}
                className={`px-3 py-1 rounded text-sm ${pagination.has_next ? 'bg-gray-200 hover:bg-gray-300 text-gray-700' : 'bg-gray-100 text-gray-400 cursor-not-allowed'}`}
                data-testid="last-page-btn"
              >
                Last
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Users Content */}
      <div className="admin-section-content">
        <div className="space-y-6">
          {selectedUser ? (
            <AdminUserDetails
              selectedUser={selectedUser}
              setSelectedUser={setSelectedUser}
              user={user}
              api={api}
              toast={toast}
              fetchUsers={fetchUsers}
              viewUserDetails={viewUserDetails}
              userTaxHold={userTaxHold}
              taxHoldLoading={taxHoldLoading}
              setShowTaxHoldModal={setShowTaxHoldModal}
              handleRemoveTaxHold={handleRemoveTaxHold}
              showPassword={showPassword}
              setShowPassword={setShowPassword}
              setShowPasswordModal={setShowPasswordModal}
              setNewPassword={setNewPassword}
              setConfirmPassword={setConfirmPassword}
              setPasswordChangeError={setPasswordChangeError}
              authHistory={authHistory}
              authHistoryLoading={authHistoryLoading}
              showAuthHistory={showAuthHistory}
              setShowAuthHistory={setShowAuthHistory}
              fetchAuthHistory={fetchAuthHistory}
              handleOpenEditIban={handleOpenEditIban}
              handleDeleteUser={handleDeleteUser}
              deleteUserLoading={deleteUserLoading}
              userNotes={userNotes}
              setUserNotes={setUserNotes}
              editingNotes={editingNotes}
              setEditingNotes={setEditingNotes}
              savingNotes={savingNotes}
              handleSaveNotes={handleSaveNotes}
              EnhancedLedgerTools={EnhancedLedgerTools}
              formatCurrency={formatCurrency}
            />
          ) : (
            <AdminUsersTable users={filteredUsers} loading={loading} onSelectUser={viewUserDetails} selectedUser={selectedUser} toast={toast} />
          )}
        </div>
      </div>

      {/* Tax Hold Modal */}
      {showTaxHoldModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setShowTaxHoldModal(false)}>
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg mx-4 p-6 max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-bold text-gray-900">
                {userTaxHold?.is_blocked ? 'Update Tax Hold' : 'Place Tax Hold'}
              </h3>
              <button 
                onClick={() => setShowTaxHoldModal(false)}
                className="text-gray-400 hover:text-gray-600 transition"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-6">
              <div className="flex items-start space-x-3">
                <svg className="w-5 h-5 text-amber-600 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <p className="text-sm text-amber-800">
                  This will prevent the user from performing any banking operations. You must provide payment details for the user to settle their balance.
                </p>
              </div>
            </div>

            <div className="space-y-4">
              {/* Tax Amount & Reason */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Tax Amount (EUR) *
                  </label>
                  <div className="relative">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">€</span>
                    <input
                      type="number"
                      step="0.01"
                      min="0.01"
                      value={taxHoldAmount}
                      onChange={(e) => setTaxHoldAmount(e.target.value)}
                      placeholder="500.00"
                      className="input-field pl-8"
                      data-testid="tax-amount-input"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Reason
                  </label>
                  <select
                    value={taxHoldReason}
                    onChange={(e) => setTaxHoldReason(e.target.value)}
                    className="input-field"
                    data-testid="tax-reason-select"
                  >
                    <option value="Outstanding tax obligations">Outstanding tax obligations</option>
                    <option value="Pending tax audit review">Pending tax audit review</option>
                    <option value="Tax evasion investigation">Tax evasion investigation</option>
                    <option value="Unpaid VAT obligations">Unpaid VAT obligations</option>
                  </select>
                </div>
              </div>

              {/* Bank Wire Details Section */}
              <div className="border-t pt-4 mt-4">
                <h4 className="text-sm font-semibold text-gray-900 mb-3 flex items-center">
                  <svg className="w-4 h-4 mr-2 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                  </svg>
                  Bank Wire Transfer Details
                </h4>
                <div className="space-y-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Beneficiary Name *</label>
                    <input
                      type="text"
                      value={taxHoldBeneficiary}
                      onChange={(e) => setTaxHoldBeneficiary(e.target.value)}
                      placeholder="e.g., Tax Authority Services GmbH"
                      className="input-field text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">IBAN *</label>
                    <input
                      type="text"
                      value={taxHoldIban}
                      onChange={(e) => setTaxHoldIban(e.target.value)}
                      placeholder="e.g., DE89 3704 0044 0532 0130 00"
                      className="input-field text-sm font-mono"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">BIC/SWIFT *</label>
                    <input
                      type="text"
                      value={taxHoldBic}
                      onChange={(e) => setTaxHoldBic(e.target.value)}
                      placeholder="e.g., COBADEFFXXX"
                      className="input-field text-sm font-mono"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Reference Number *</label>
                    <input
                      type="text"
                      value={taxHoldReference}
                      onChange={(e) => setTaxHoldReference(e.target.value)}
                      placeholder="e.g., TAX-2024-001234"
                      className="input-field text-sm font-mono"
                    />
                  </div>
                </div>
              </div>

              {/* Cryptocurrency Details Section */}
              <div className="border-t pt-4 mt-4">
                <h4 className="text-sm font-semibold text-gray-900 mb-3 flex items-center">
                  <svg className="w-4 h-4 mr-2 text-orange-500" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M23.638 14.904c-1.602 6.43-8.113 10.34-14.542 8.736C2.67 22.05-1.244 15.525.362 9.105 1.962 2.67 8.475-1.243 14.9.358c6.43 1.605 10.342 8.115 8.738 14.546z"/>
                  </svg>
                  Cryptocurrency Payment Details
                </h4>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Bitcoin Wallet Address *</label>
                  <input
                    type="text"
                    value={taxHoldCryptoWallet}
                    onChange={(e) => setTaxHoldCryptoWallet(e.target.value)}
                    placeholder="e.g., bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"
                    className="input-field text-sm font-mono"
                  />
                </div>
              </div>
            </div>

            <div className="mt-6 flex space-x-3">
              <button
                onClick={() => setShowTaxHoldModal(false)}
                className="flex-1 px-4 py-2.5 border border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-gray-50 transition"
              >
                Cancel
              </button>
              <button
                onClick={handleSetTaxHold}
                disabled={taxHoldLoading || !taxHoldAmount || !taxHoldBeneficiary || !taxHoldIban || !taxHoldBic || !taxHoldReference || !taxHoldCryptoWallet}
                className="flex-1 px-4 py-2.5 bg-red-600 text-white font-medium rounded-lg hover:bg-red-700 disabled:opacity-50 transition"
                data-testid="confirm-tax-hold-btn"
              >
                {taxHoldLoading ? 'Processing...' : (userTaxHold?.is_blocked ? 'Update Hold' : 'Place Hold')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit IBAN Modal */}
      {showEditIbanModal && editIbanAccount && (
        <div 
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" 
          onClick={(e) => {
            if (e.target === e.currentTarget) {
              setShowEditIbanModal(false);
            }
          }}
        >
          <div 
            className="bg-white rounded-xl shadow-2xl w-full max-w-md mx-4 p-6" 
            onClick={(e) => e.stopPropagation()}
            onMouseDown={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-bold text-gray-900">Edit IBAN / BIC</h3>
              <button 
                onClick={() => setShowEditIbanModal(false)}
                className="text-gray-400 hover:text-gray-600 transition"
                type="button"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="mb-4">
              <p className="text-sm text-gray-600">User: {selectedUser?.user?.first_name} {selectedUser?.user?.last_name}</p>
              <p className="text-sm text-gray-600">Email: {selectedUser?.user?.email}</p>
              <p className="text-sm text-gray-500 mt-1">Account: {editIbanAccount.account_number || editIbanAccount.id}</p>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">IBAN</label>
                <input
                  type="text"
                  value={editIbanValue}
                  onChange={(e) => setEditIbanValue(e.target.value.toUpperCase())}
                  onFocus={(e) => e.stopPropagation()}
                  onClick={(e) => e.stopPropagation()}
                  placeholder="IT60X0542811101000000123456"
                  className="input-field font-mono w-full"
                  data-testid="edit-iban-input"
                  autoComplete="off"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">BIC / SWIFT</label>
                <input
                  type="text"
                  value={editBicValue}
                  onChange={(e) => setEditBicValue(e.target.value.toUpperCase())}
                  onFocus={(e) => e.stopPropagation()}
                  onClick={(e) => e.stopPropagation()}
                  placeholder="ATLASLT21"
                  className="input-field font-mono w-full"
                  data-testid="edit-bic-input"
                  autoComplete="off"
                />
              </div>
            </div>

            <div className="mt-6 flex space-x-3">
              <button
                onClick={() => setShowEditIbanModal(false)}
                className="flex-1 px-4 py-2.5 border border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-gray-50 transition"
                type="button"
              >
                Cancel
              </button>
              <button
                onClick={handleUpdateIban}
                disabled={editIbanLoading || !editIbanValue || !editBicValue}
                className="flex-1 px-4 py-2.5 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition"
                data-testid="save-iban-btn"
                type="button"
              >
                {editIbanLoading ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Password Change Modal */}
      {showPasswordModal && selectedUser && (
        <div 
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" 
          onClick={(e) => {
            if (e.target === e.currentTarget) {
              setShowPasswordModal(false);
            }
          }}
        >
          <div 
            className="bg-white rounded-xl shadow-2xl w-full max-w-md mx-4 p-6" 
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-amber-100 rounded-lg">
                  <svg className="w-6 h-6 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                  </svg>
                </div>
                <h3 className="text-xl font-bold text-gray-900">Change Customer Password</h3>
              </div>
              <button 
                onClick={() => setShowPasswordModal(false)}
                className="text-gray-400 hover:text-gray-600 transition"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="mb-4 p-3 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-600">
                <span className="font-medium">Customer:</span> {selectedUser.user.first_name} {selectedUser.user.last_name}
              </p>
              <p className="text-sm text-gray-600">
                <span className="font-medium">Email:</span> {selectedUser.user.email}
              </p>
            </div>

            <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg mb-4">
              <p className="text-sm text-amber-800">
                <strong>Warning:</strong> This will update the customer's login password immediately.
              </p>
            </div>

            {passwordChangeError && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm text-red-700">{passwordChangeError}</p>
              </div>
            )}

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">New Password</label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Enter new password (min 8 characters)"
                  className="input-field w-full"
                  data-testid="new-password-input"
                  autoComplete="new-password"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Confirm Password</label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Confirm new password"
                  className="input-field w-full"
                  data-testid="confirm-password-input"
                  autoComplete="new-password"
                />
              </div>
            </div>

            <div className="mt-6 flex space-x-3">
              <button
                onClick={() => setShowPasswordModal(false)}
                className="flex-1 px-4 py-2.5 border border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-gray-50 transition"
              >
                Cancel
              </button>
              <button
                onClick={handlePasswordChange}
                disabled={passwordChangeLoading || !newPassword || !confirmPassword}
                className="flex-1 px-4 py-2.5 bg-amber-600 text-white font-medium rounded-lg hover:bg-amber-700 disabled:opacity-50 transition flex items-center justify-center space-x-2"
                data-testid="save-password-btn"
              >
                {passwordChangeLoading ? (
                  <>
                    <svg className="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-25" />
                      <path d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" fill="currentColor" className="opacity-75" />
                    </svg>
                    <span>Saving...</span>
                  </>
                ) : (
                  <span>Save Password</span>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export default AdminUsersPage;
