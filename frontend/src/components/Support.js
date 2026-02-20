// Support Ticket Components
import React, { useState, useEffect, useRef, useCallback } from 'react';
import api from '../api';
import { useLanguage, useTheme } from '../contexts/AppContext';
import { toast } from 'sonner';

export function SupportTickets({ isAdmin = false }) {
  const [tickets, setTickets] = useState([]);
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [showAdminCreateForm, setShowAdminCreateForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const { t } = useLanguage();
  const { isDark } = useTheme();

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchQuery);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Fetch tickets when filters change
  useEffect(() => {
    fetchTickets();
  }, [statusFilter, debouncedSearch]);

  // Auto-refresh for admin every 30 seconds
  useEffect(() => {
    if (isAdmin) {
      const interval = setInterval(() => {
        fetchTickets(true); // Silent refresh
      }, 30000);
      return () => clearInterval(interval);
    }
  }, [isAdmin, statusFilter, debouncedSearch]);

  const fetchTickets = async (silent = false) => {
    try {
      if (!silent) setLoading(true);
      if (isAdmin) {
        let params = new URLSearchParams();
        if (statusFilter !== 'all') params.append('status', statusFilter);
        if (debouncedSearch) params.append('search', debouncedSearch);
        const queryString = params.toString();
        const response = await api.get(`/admin/tickets${queryString ? `?${queryString}` : ''}`);
        setTickets(response.data);
      } else {
        const response = await api.get('/tickets');
        setTickets(response.data);
      }
    } catch (err) {
      console.error('Failed to fetch tickets:', err);
    } finally {
      if (!silent) setLoading(false);
    }
  };

  // Function to refresh a single ticket and update selectedTicket
  const refreshSelectedTicket = async (ticketId) => {
    try {
      if (isAdmin) {
        // For admin, fetch all tickets and find the updated one
        const response = await api.get('/admin/tickets');
        const updatedTicket = response.data.find(t => t.id === ticketId);
        if (updatedTicket) {
          setSelectedTicket(updatedTicket);
        }
        setTickets(response.data);
      } else {
        // For regular users, fetch their tickets and find the updated one
        const response = await api.get('/tickets');
        const updatedTicket = response.data.find(t => t.id === ticketId);
        if (updatedTicket) {
          setSelectedTicket(updatedTicket);
        }
        setTickets(response.data);
      }
    } catch (err) {
      console.error('Failed to refresh ticket:', err);
    }
  };

  const handleTicketCreated = () => {
    setShowCreateForm(false);
    setShowAdminCreateForm(false);
    fetchTickets();
  };

  // Mark ticket as read when user/admin selects it
  const handleSelectTicket = async (ticket) => {
    setSelectedTicket(ticket);
    
    // Mark as read if there are unread messages
    if (ticket.unread_count > 0) {
      try {
        if (isAdmin) {
          await api.post(`/admin/tickets/${ticket.id}/mark-read`);
        } else {
          // Client marks ticket as read
          await api.post(`/tickets/${ticket.id}/mark-read`);
        }
        // Update local state to reflect read status
        setTickets(prev => prev.map(t => 
          t.id === ticket.id ? { ...t, unread_count: 0 } : t
        ));
      } catch (err) {
        console.error('Failed to mark ticket as read:', err);
      }
    }
  };

  const updateTicketStatus = async (ticketId, newStatus) => {
    try {
      await api.patch(`/admin/tickets/${ticketId}/status`, { status: newStatus });
      alert('Ticket status updated');
      fetchTickets();
      if (selectedTicket?.id === ticketId) {
        setSelectedTicket(null);
      }
    } catch (err) {
      alert('Failed to update status');
    }
  };

  if (loading) {
    return <div className="text-center py-8"><div className={`skeleton h-32 rounded-lg ${isDark ? 'bg-gray-700' : ''}`}></div></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4">
        <div>
          <h2 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>{t('supportTickets')}</h2>
          <p className={`text-sm mt-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            {isAdmin ? t('manageCustomerRequests') : t('getHelpFromSupport')}
          </p>
        </div>
        {!isAdmin && (
          <button
            onClick={() => setShowCreateForm(true)}
            className="btn-primary text-sm px-4 py-2 whitespace-nowrap w-full sm:w-auto"
            data-testid="create-ticket-button"
          >
            {t('createNewTicket')}
          </button>
        )}
        {isAdmin && (
          <button
            onClick={() => setShowAdminCreateForm(true)}
            className="btn-primary text-sm px-4 py-2 whitespace-nowrap w-full sm:w-auto flex items-center gap-2"
            data-testid="admin-create-ticket-button"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Create Ticket for Client
          </button>
        )}
      </div>

      {isAdmin && (
        <div className={`card-enhanced p-4 ${isDark ? 'bg-gray-800 border-gray-700' : ''}`}>
          <div className="flex flex-col md:flex-row md:items-center gap-4">
            {/* Search Bar */}
            <div className="flex-1">
              <div className="relative">
                <svg className={`absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 ${isDark ? 'text-gray-400' : 'text-gray-500'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search by client email or name..."
                  className={`input-enhanced w-full pl-10 ${isDark ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400' : ''}`}
                  data-testid="admin-ticket-search"
                />
                {searchQuery && (
                  <button
                    onClick={() => setSearchQuery('')}
                    className={`absolute right-3 top-1/2 transform -translate-y-1/2 ${isDark ? 'text-gray-400 hover:text-gray-200' : 'text-gray-400 hover:text-gray-600'}`}
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                )}
              </div>
            </div>
            
            {/* Status Filter */}
            <div className="flex items-center space-x-4">
              <label className={`text-sm font-medium ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{t('filterByStatus')}:</label>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className={`input-enhanced ${isDark ? 'bg-gray-700 border-gray-600 text-white' : ''}`}
                data-testid="admin-ticket-filter"
              >
                <option value="all">{t('allTickets')}</option>
                <option value="OPEN">{t('open')}</option>
                <option value="IN_PROGRESS">{t('inProgress')}</option>
                <option value="WAITING">{t('waiting')}</option>
                <option value="RESOLVED">{t('resolved')}</option>
                <option value="CLOSED">{t('closed')}</option>
              </select>
              <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{tickets.length} {t('ticketCount')}</span>
            </div>
          </div>
        </div>
      )}

      {showCreateForm && (
        <CreateTicketForm
          onClose={() => setShowCreateForm(false)}
          onSuccess={handleTicketCreated}
        />
      )}

      {showAdminCreateForm && (
        <AdminCreateTicketForm
          onClose={() => setShowAdminCreateForm(false)}
          onSuccess={handleTicketCreated}
        />
      )}

      {tickets.length === 0 ? (
        <div className={`card-blue-accent p-8 text-center animate-card ${isDark ? 'bg-gray-800 border-gray-700' : ''}`}>
          <div className="circle-pattern">
            <p className={isDark ? 'text-gray-400' : 'text-gray-600'}>
              {searchQuery ? 'No tickets found matching your search' : t('noSupportTicketsYet')}
            </p>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Tickets List */}
          <div className="lg:col-span-1">
            <div className={`card-enhanced ${isDark ? 'bg-gray-800 border-gray-700' : ''}`}>
              <div className={`p-4 border-b ${isDark ? 'bg-gray-700/50 border-gray-600' : 'bg-blue-50/30'}`}>
                <h3 className={`font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>{isAdmin ? 'All Tickets' : t('yourTickets')}</h3>
                <p className={`text-sm mt-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{tickets.length} {t('ticketCount')}</p>
              </div>
              <div className={`divide-y max-h-[600px] overflow-y-auto ${isDark ? 'divide-gray-700' : ''}`}>
                {tickets.map((ticket) => (
                  <div
                    key={ticket.id}
                    onClick={() => handleSelectTicket(ticket)}
                    className={`p-4 cursor-pointer transition-colors ${
                      selectedTicket?.id === ticket.id 
                        ? (isDark ? 'bg-gray-700' : 'bg-blue-50') 
                        : (isDark ? 'hover:bg-gray-700' : 'hover:bg-blue-50/50')
                    }`}
                    data-testid={`ticket-${ticket.id}`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <p className={`font-medium flex-1 ${isDark ? 'text-white' : 'text-gray-900'}`}>
                        {ticket.subject}
                        {/* "Created by Support" tag */}
                        {ticket.created_by_admin && (
                          <span className={`ml-2 text-xs px-2 py-0.5 rounded-full ${isDark ? 'bg-purple-900/50 text-purple-300' : 'bg-purple-100 text-purple-700'}`}>
                            Created by Support
                          </span>
                        )}
                      </p>
                      {/* Unread badge - shows for both admin and client */}
                      {ticket.unread_count > 0 && (
                        <span 
                          className="flex-shrink-0 bg-red-500 text-white text-xs font-bold rounded-full h-5 min-w-[20px] px-1.5 flex items-center justify-center"
                          data-testid={`unread-badge-${ticket.id}`}
                        >
                          {ticket.unread_count > 9 ? '9+' : ticket.unread_count}
                        </span>
                      )}
                    </div>
                    {/* Show client name for admin view */}
                    {isAdmin && ticket.user_name && (
                      <p className={`text-xs mt-1 ${isDark ? 'text-blue-400' : 'text-blue-600'}`}>
                        <span className="font-medium">{ticket.user_name}</span>
                        {ticket.user_email && ticket.user_name !== ticket.user_email && (
                          <span className={isDark ? 'text-gray-500' : 'text-gray-500'}> • {ticket.user_email}</span>
                        )}
                      </p>
                    )}
                    <div className="flex items-center justify-between mt-2">
                      <TicketStatusBadge status={ticket.status} t={t} />
                      <span className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>
                        {new Date(ticket.updated_at).toLocaleDateString()}
                      </span>
                    </div>
                    {ticket.messages && ticket.messages.length > 1 && (
                      <p className={`text-xs mt-1 ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>
                        {ticket.messages.length} messages
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Ticket Details */}
          <div className="lg:col-span-2">
            {selectedTicket ? (
              <TicketDetails
                ticket={selectedTicket}
                onUpdate={fetchTickets}
                onRefreshTicket={refreshSelectedTicket}
                onDelete={(ticketId) => {
                  setSelectedTicket(null);
                  fetchTickets();
                }}
                isAdmin={isAdmin}
              />
            ) : (
              <div className={`card-blue-accent p-12 text-center ${isDark ? 'bg-gray-800 border-gray-700' : ''}`}>
                <p className={isDark ? 'text-gray-400' : 'text-gray-600'}>{t('selectTicketToView')}</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function CreateTicketForm({ onClose, onSuccess }) {
  const [formData, setFormData] = useState({
    subject: '',
    description: ''
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const { t } = useLanguage();
  const { isDark } = useTheme();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError('');

    try {
      await api.post('/tickets/create', formData);
      onSuccess();
    } catch (err) {
      const errorMsg = err.response?.data?.detail 
        ? (typeof err.response.data.detail === 'string' 
            ? err.response.data.detail 
            : JSON.stringify(err.response.data.detail))
        : err.message || 'Failed to create ticket';
      setError(errorMsg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className={`card-enhanced p-6 animate-card ${isDark ? 'bg-gray-800 border-gray-700' : ''}`}>
      <div className="flex justify-between items-center mb-4">
        <h3 className={`text-lg font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>{t('createSupportTicket')}</h3>
        <button
          onClick={onClose}
          className={`${isDark ? 'text-gray-500 hover:text-gray-300' : 'text-gray-400 hover:text-gray-600'}`}
        >
          ✕
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-800 rounded p-3 text-sm mb-4">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{t('subject')}</label>
          <input
            type="text"
            value={formData.subject}
            onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
            required
            className={`input-enhanced w-full ${isDark ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400' : ''}`}
            placeholder={t('briefDescription')}
            data-testid="ticket-subject"
          />
        </div>
        <div>
          <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{t('descriptionLabel')}</label>
          <textarea
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            required
            rows={5}
            className={`input-enhanced w-full resize-y min-h-[120px] max-h-[400px] ${isDark ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400' : ''}`}
            style={{ resize: 'vertical' }}
            placeholder={t('provideDetails')}
            data-testid="ticket-description"
          />
          <p className="text-xs text-gray-500 mt-1">Drag the bottom edge to resize</p>
        </div>
        <div className="flex justify-end space-x-3">
          <button
            type="button"
            onClick={onClose}
            className={`px-4 py-2 border rounded-lg ${isDark ? 'border-gray-600 text-gray-300 hover:bg-gray-700' : 'border-gray-300 hover:bg-gray-50'}`}
          >
            {t('cancel')}
          </button>
          <button
            type="submit"
            disabled={submitting}
            className="btn-primary btn-glow"
            data-testid="submit-ticket"
          >
            {submitting ? t('creating') : t('createTicket')}
          </button>
        </div>
      </form>
    </div>
  );
}

// Admin: Create ticket on behalf of a client
function AdminCreateTicketForm({ onClose, onSuccess }) {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [selectedUser, setSelectedUser] = useState(null);
  const [searching, setSearching] = useState(false);
  const [formData, setFormData] = useState({
    subject: '',
    description: ''
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const { isDark } = useTheme();

  // Search users as they type
  useEffect(() => {
    const searchUsers = async () => {
      if (searchQuery.length < 2) {
        setSearchResults([]);
        return;
      }
      setSearching(true);
      try {
        const response = await api.get(`/admin/users/search-for-ticket?q=${encodeURIComponent(searchQuery)}`);
        setSearchResults(response.data);
      } catch (err) {
        console.error('Search failed:', err);
        setSearchResults([]);
      } finally {
        setSearching(false);
      }
    };

    const timer = setTimeout(searchUsers, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  const handleSelectUser = (user) => {
    setSelectedUser(user);
    setSearchQuery('');
    setSearchResults([]);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedUser) {
      setError('Please select a client');
      return;
    }
    setSubmitting(true);
    setError('');

    try {
      await api.post('/admin/tickets/create-for-user', {
        user_id: selectedUser.id,
        subject: formData.subject,
        description: formData.description
      });
      onSuccess();
    } catch (err) {
      const errorMsg = err.response?.data?.detail 
        ? (typeof err.response.data.detail === 'string' 
            ? err.response.data.detail 
            : JSON.stringify(err.response.data.detail))
        : err.message || 'Failed to create ticket';
      setError(errorMsg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className={`card-enhanced p-6 animate-card ${isDark ? 'bg-gray-800 border-gray-700' : ''}`}>
      <div className="flex justify-between items-center mb-4">
        <h3 className={`text-lg font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>
          Create Ticket for Client
        </h3>
        <button
          onClick={onClose}
          className={`${isDark ? 'text-gray-500 hover:text-gray-300' : 'text-gray-400 hover:text-gray-600'}`}
        >
          ✕
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-800 rounded p-3 text-sm mb-4">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Client Search */}
        <div>
          <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            Select Client *
          </label>
          
          {selectedUser ? (
            <div className={`flex items-center justify-between p-3 rounded-lg border ${isDark ? 'bg-gray-700 border-gray-600' : 'bg-blue-50 border-blue-200'}`}>
              <div>
                <p className={`font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>
                  {selectedUser.full_name || selectedUser.email}
                </p>
                <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                  {selectedUser.email}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setSelectedUser(null)}
                className={`text-sm ${isDark ? 'text-red-400 hover:text-red-300' : 'text-red-600 hover:text-red-700'}`}
              >
                Change
              </button>
            </div>
          ) : (
            <div className="relative">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search by email, name, or ID..."
                className={`input-enhanced w-full ${isDark ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400' : ''}`}
                data-testid="admin-client-search"
              />
              {searching && (
                <div className={`absolute right-3 top-1/2 transform -translate-y-1/2 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                  <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                </div>
              )}
              
              {/* Search Results Dropdown */}
              {searchResults.length > 0 && (
                <div className={`absolute z-10 w-full mt-1 rounded-lg shadow-lg border overflow-hidden ${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`}>
                  {searchResults.map((user) => (
                    <div
                      key={user.id}
                      onClick={() => handleSelectUser(user)}
                      className={`p-3 cursor-pointer transition-colors ${isDark ? 'hover:bg-gray-700' : 'hover:bg-gray-50'}`}
                      data-testid={`search-result-${user.id}`}
                    >
                      <p className={`font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>
                        {user.full_name || user.email}
                      </p>
                      <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                        {user.email}
                        <span className={`ml-2 text-xs px-1.5 py-0.5 rounded ${
                          user.status === 'ACTIVE' 
                            ? (isDark ? 'bg-green-900/50 text-green-300' : 'bg-green-100 text-green-700')
                            : (isDark ? 'bg-gray-700 text-gray-400' : 'bg-gray-100 text-gray-600')
                        }`}>
                          {user.status}
                        </span>
                      </p>
                    </div>
                  ))}
                </div>
              )}
              
              {searchQuery.length >= 2 && !searching && searchResults.length === 0 && (
                <div className={`absolute z-10 w-full mt-1 p-3 rounded-lg shadow-lg border ${isDark ? 'bg-gray-800 border-gray-700 text-gray-400' : 'bg-white border-gray-200 text-gray-500'}`}>
                  No clients found
                </div>
              )}
            </div>
          )}
        </div>

        {/* Subject */}
        <div>
          <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            Subject *
          </label>
          <input
            type="text"
            value={formData.subject}
            onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
            required
            className={`input-enhanced w-full ${isDark ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400' : ''}`}
            placeholder="Brief description of the issue"
            data-testid="admin-ticket-subject"
          />
        </div>

        {/* Description */}
        <div>
          <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            Message *
          </label>
          <textarea
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            required
            rows={5}
            className={`input-enhanced w-full resize-y min-h-[120px] max-h-[400px] ${isDark ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400' : ''}`}
            style={{ resize: 'vertical' }}
            placeholder="Detailed message for the client..."
            data-testid="admin-ticket-description"
          />
        </div>

        <div className={`p-3 rounded-lg ${isDark ? 'bg-purple-900/20 border border-purple-800' : 'bg-purple-50 border border-purple-200'}`}>
          <p className={`text-sm ${isDark ? 'text-purple-300' : 'text-purple-700'}`}>
            <strong>Note:</strong> This ticket will be marked as "Created by Support" and the client will receive a notification.
          </p>
        </div>

        <div className="flex justify-end space-x-3">
          <button
            type="button"
            onClick={onClose}
            className={`px-4 py-2 border rounded-lg ${isDark ? 'border-gray-600 text-gray-300 hover:bg-gray-700' : 'border-gray-300 hover:bg-gray-50'}`}
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={submitting || !selectedUser}
            className="btn-primary btn-glow disabled:opacity-50"
            data-testid="admin-submit-ticket"
          >
            {submitting ? 'Creating...' : 'Create Ticket'}
          </button>
        </div>
      </form>
    </div>
  );
}

function TicketDetails({ ticket, onUpdate, onDelete, isAdmin = false, onRefreshTicket }) {
  const [newMessage, setNewMessage] = useState('');
  const [sending, setSending] = useState(false);
  const [editingSubject, setEditingSubject] = useState(false);
  const [editedSubject, setEditedSubject] = useState(ticket.subject);
  const [editingMessageIndex, setEditingMessageIndex] = useState(null);
  const [editedMessageContent, setEditedMessageContent] = useState('');
  const [savingEdit, setSavingEdit] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deletingMessageIndex, setDeletingMessageIndex] = useState(null);
  const [confirmDeleteMessage, setConfirmDeleteMessage] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [uploadingFiles, setUploadingFiles] = useState(false);
  const fileInputRef = React.useRef(null);
  const { t } = useLanguage();
  const { isDark } = useTheme();

  // File upload constants
  const MAX_FILES = 5;
  const MAX_FILE_SIZE = 25 * 1024 * 1024; // 25 MB
  const ALLOWED_EXTENSIONS = ['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'rtf', 'odt', 'ods', 'odp', 'csv', 'zip'];

  // Reset edit states when ticket changes
  useEffect(() => {
    setEditingSubject(false);
    setEditedSubject(ticket.subject);
    setEditingMessageIndex(null);
    setEditedMessageContent('');
    setDeletingMessageIndex(null);
    setConfirmDeleteMessage(false);
    setSelectedFiles([]);
  }, [ticket.id, ticket.subject]);

  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files || []);
    const validFiles = [];
    const errors = [];

    files.forEach(file => {
      const ext = file.name.split('.').pop()?.toLowerCase() || '';
      
      if (!ALLOWED_EXTENSIONS.includes(ext)) {
        errors.push(`${file.name}: File type not allowed`);
        return;
      }
      
      if (file.size > MAX_FILE_SIZE) {
        errors.push(`${file.name}: File too large (max 25 MB)`);
        return;
      }
      
      if (selectedFiles.length + validFiles.length >= MAX_FILES) {
        errors.push(`${file.name}: Maximum ${MAX_FILES} files allowed`);
        return;
      }
      
      validFiles.push(file);
    });

    if (errors.length > 0) {
      alert(errors.join('\n'));
    }

    if (validFiles.length > 0) {
      setSelectedFiles(prev => [...prev, ...validFiles].slice(0, MAX_FILES));
    }
    
    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const removeFile = (index) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  const getFileIcon = (filename) => {
    const ext = filename.split('.').pop()?.toLowerCase() || '';
    if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'].includes(ext)) {
      return (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
      );
    }
    if (ext === 'pdf') {
      return (
        <svg className="w-5 h-5 text-red-500" fill="currentColor" viewBox="0 0 24 24">
          <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6zm-1 2l5 5h-5V4zM8.5 13H10v5H8.5v-3.5L7 16H5.5l1.5-1.5L5.5 13H7l1.5 1.5V13zm3.5 0h2c.83 0 1.5.67 1.5 1.5v2c0 .83-.67 1.5-1.5 1.5h-2v-5zm1.5 4h.5a.5.5 0 00.5-.5v-2a.5.5 0 00-.5-.5h-.5v3z"/>
        </svg>
      );
    }
    return (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    );
  };

  const handleSendMessage = async () => {
    if (!newMessage.trim() && selectedFiles.length === 0) return;

    setSending(true);
    setUploadingFiles(selectedFiles.length > 0);
    
    try {
      let response;
      if (selectedFiles.length > 0) {
        // Send message with attachments using FormData
        const formData = new FormData();
        formData.append('content', newMessage.trim() || '(Attachment)');
        selectedFiles.forEach(file => {
          formData.append('files', file);
        });
        
        response = await api.post(`/tickets/${ticket.id}/messages/with-attachments`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });
      } else {
        // Send text-only message
        response = await api.post(`/tickets/${ticket.id}/messages`, { content: newMessage });
      }
      
      // Clear inputs immediately for responsive UX
      setNewMessage('');
      setSelectedFiles([]);
      
      // Update ticket with new messages from response (SPA behavior - no full refetch)
      if (response.data && response.data.messages) {
        // Use the updated ticket from the API response directly
        if (onRefreshTicket) {
          await onRefreshTicket(ticket.id);
        }
      }
      
      // Silent background sync of ticket list (no loading state)
      // This keeps the list in sync without visual reload
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Failed to send message';
      alert(errorMsg);
    } finally {
      setSending(false);
      setUploadingFiles(false);
    }
  };

  const handleStatusChange = async (newStatus) => {
    try {
      await api.patch(`/admin/tickets/${ticket.id}/status`, { status: newStatus });
      toast.success('Status updated successfully');
      // Refresh only the selected ticket to show updated status
      if (onRefreshTicket) {
        await onRefreshTicket(ticket.id);
      }
      // No full refetch needed - ticket list will sync on next interaction
    } catch (err) {
      alert('Failed to update status');
    }
  };

  const handleSaveSubject = async () => {
    if (!editedSubject.trim()) return;
    setSavingEdit(true);
    try {
      await api.patch(`/admin/tickets/${ticket.id}/subject`, { subject: editedSubject.trim() });
      setEditingSubject(false);
      toast.success('Subject updated');
      // Refresh only the selected ticket
      if (onRefreshTicket) {
        await onRefreshTicket(ticket.id);
      }
      // No full refetch needed
    } catch (err) {
      alert('Failed to update subject');
    } finally {
      setSavingEdit(false);
    }
  };

  const handleEditMessage = (index, content) => {
    setEditingMessageIndex(index);
    setEditedMessageContent(content);
  };

  const handleSaveMessage = async () => {
    if (!editedMessageContent.trim()) return;
    setSavingEdit(true);
    try {
      await api.patch(`/admin/tickets/${ticket.id}/messages/${editingMessageIndex}`, { 
        content: editedMessageContent.trim() 
      });
      setEditingMessageIndex(null);
      setEditedMessageContent('');
      toast.success('Message updated');
      // Refresh the ticket to show updated message
      if (onRefreshTicket) {
        await onRefreshTicket(ticket.id);
      }
      // No full refetch needed
    } catch (err) {
      alert('Failed to update message');
    } finally {
      setSavingEdit(false);
    }
  };

  const handleCancelMessageEdit = () => {
    setEditingMessageIndex(null);
    setEditedMessageContent('');
  };

  const handleDeleteTicket = async () => {
    setDeleting(true);
    try {
      await api.delete(`/admin/tickets/${ticket.id}`);
      setShowDeleteConfirm(false);
      toast.success('Ticket deleted');
      if (onDelete) {
        onDelete(ticket.id);
      }
    } catch (err) {
      alert('Failed to delete ticket: ' + (err.response?.data?.detail || err.message));
    } finally {
      setDeleting(false);
    }
  };

  const handleDeleteMessage = async () => {
    if (deletingMessageIndex === null) return;
    
    try {
      await api.delete(`/admin/tickets/${ticket.id}/messages/${deletingMessageIndex}`);
      setConfirmDeleteMessage(false);
      setDeletingMessageIndex(null);
      toast.success('Message deleted');
      // Refresh the ticket to show messages without deleted one
      if (onRefreshTicket) {
        await onRefreshTicket(ticket.id);
      }
      // No full refetch needed
    } catch (err) {
      alert('Failed to delete message: ' + (err.response?.data?.detail || err.message));
    }
  };

  const initiateDeleteMessage = (index) => {
    setDeletingMessageIndex(index);
    setConfirmDeleteMessage(true);
  };

  return (
    <div className={`card-enhanced space-y-4 ${isDark ? 'bg-gray-800 border-gray-700' : ''}`}>
      {/* Header */}
      <div className={`p-6 border-b ${isDark ? 'bg-gray-700/50 border-gray-600' : 'bg-blue-50/30'}`}>
        <div className="flex justify-between items-start">
          <div className="flex-1 mr-4">
            {editingSubject && isAdmin ? (
              <div className="space-y-3">
                <input
                  type="text"
                  value={editedSubject}
                  onChange={(e) => setEditedSubject(e.target.value)}
                  className={`input-enhanced w-full text-lg font-semibold ${isDark ? 'bg-gray-700 border-gray-600 text-white' : ''}`}
                  autoFocus
                  data-testid="edit-subject-input"
                />
                <div className="flex items-center space-x-2">
                  <button
                    onClick={handleSaveSubject}
                    disabled={savingEdit || !editedSubject.trim()}
                    className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50 transition"
                    data-testid="save-subject-btn"
                  >
                    {savingEdit ? 'Saving...' : 'Save'}
                  </button>
                  <button
                    onClick={() => { setEditingSubject(false); setEditedSubject(ticket.subject); }}
                    className={`px-3 py-1.5 text-sm rounded-lg transition ${isDark ? 'bg-gray-600 text-gray-200 hover:bg-gray-500' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex items-start gap-2">
                <h3 className={`text-lg font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>{ticket.subject}</h3>
                {isAdmin && (
                  <button
                    onClick={() => setEditingSubject(true)}
                    className={`p-1.5 rounded-lg transition opacity-60 hover:opacity-100 ${isDark ? 'hover:bg-gray-600 text-gray-400' : 'hover:bg-gray-200 text-gray-500'}`}
                    title="Edit subject"
                    data-testid="edit-subject-btn"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                    </svg>
                  </button>
                )}
              </div>
            )}
            <p className={`text-sm mt-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
              {t('created')} {new Date(ticket.created_at).toLocaleString()}
              {ticket.created_by_admin && (
                <span className={`ml-2 text-xs px-2 py-0.5 rounded-full ${isDark ? 'bg-purple-900/50 text-purple-300' : 'bg-purple-100 text-purple-700'}`}>
                  Created by Support
                </span>
              )}
            </p>
            {isAdmin && ticket.user_id && (
              <p className={`text-xs mt-1 ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>
                Customer ID: {ticket.user_id}
              </p>
            )}
          </div>
          <div className="text-right">
            <TicketStatusBadge status={ticket.status} t={t} />
            {isAdmin && (
              <div className="mt-2 flex flex-col space-y-1">
                <button
                  onClick={() => handleStatusChange('IN_PROGRESS')}
                  className="text-xs text-blue-600 hover:text-blue-700"
                  data-testid="mark-in-progress"
                >
                  Mark In Progress
                </button>
                <button
                  onClick={() => handleStatusChange('RESOLVED')}
                  className="text-xs text-green-600 hover:text-green-700"
                  data-testid="mark-resolved"
                >
                  Mark Resolved
                </button>
                <button
                  onClick={() => handleStatusChange('CLOSED')}
                  className="text-xs text-gray-600 hover:text-gray-700"
                  data-testid="mark-closed"
                >
                  Close Ticket
                </button>
                <div className={`border-t my-2 ${isDark ? 'border-gray-600' : 'border-gray-200'}`}></div>
                <button
                  onClick={() => setShowDeleteConfirm(true)}
                  className="text-xs text-red-600 hover:text-red-700 font-medium"
                  data-testid="delete-ticket-btn"
                >
                  Delete Ticket
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="p-6 space-y-4 max-h-[400px] overflow-y-auto">
        {ticket.messages && ticket.messages.map((msg, idx) => (
          <div
            key={idx}
            className={`p-4 rounded-lg ${
              msg.is_staff 
                ? (isDark ? 'bg-blue-900/30 border border-blue-700' : 'bg-blue-50 border border-blue-200')
                : (isDark ? 'bg-gray-700 border border-gray-600' : 'bg-gray-50 border border-gray-200')
            }`}
            data-testid={`message-${idx}`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className={`text-sm font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>
                {msg.is_staff ? 'ECOMMBX' : msg.sender_name}
                {msg.is_staff && (
                  <span className="ml-2 text-xs bg-blue-600 text-white px-2 py-1 rounded">
                    Support
                  </span>
                )}
              </span>
              <div className="flex items-center gap-2">
                <span className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>
                  {new Date(msg.created_at).toLocaleString()}
                </span>
                {isAdmin && editingMessageIndex !== idx && (
                  <>
                    <button
                      onClick={() => handleEditMessage(idx, msg.content)}
                      className={`p-1 rounded transition opacity-60 hover:opacity-100 ${isDark ? 'hover:bg-gray-600 text-gray-400' : 'hover:bg-gray-200 text-gray-500'}`}
                      title="Edit message"
                      data-testid={`edit-message-btn-${idx}`}
                    >
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                      </svg>
                    </button>
                    <button
                      onClick={() => initiateDeleteMessage(idx)}
                      className={`p-1 rounded transition opacity-60 hover:opacity-100 ${isDark ? 'hover:bg-red-900/50 text-red-400' : 'hover:bg-red-100 text-red-500'}`}
                      title="Delete message"
                      data-testid={`delete-message-btn-${idx}`}
                    >
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </>
                )}
              </div>
            </div>
            
            {editingMessageIndex === idx ? (
              <div className="space-y-3">
                <textarea
                  value={editedMessageContent}
                  onChange={(e) => setEditedMessageContent(e.target.value)}
                  rows={4}
                  className={`input-enhanced w-full text-sm resize-y min-h-[80px] max-h-[300px] ${isDark ? 'bg-gray-600 border-gray-500 text-white' : ''}`}
                  style={{ resize: 'vertical' }}
                  autoFocus
                  data-testid={`edit-message-textarea-${idx}`}
                />
                <div className="flex items-center space-x-2">
                  <button
                    onClick={handleSaveMessage}
                    disabled={savingEdit || !editedMessageContent.trim()}
                    className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50 transition"
                    data-testid={`save-message-btn-${idx}`}
                  >
                    {savingEdit ? 'Saving...' : 'Save'}
                  </button>
                  <button
                    onClick={handleCancelMessageEdit}
                    className={`px-3 py-1.5 text-sm rounded-lg transition ${isDark ? 'bg-gray-600 text-gray-200 hover:bg-gray-500' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <>
                <p className={`text-sm whitespace-pre-wrap ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{msg.content}</p>
                
                {/* Display attachments */}
                {msg.attachments && msg.attachments.length > 0 && (
                  <div className="mt-3 space-y-2">
                    <p className={`text-xs font-medium ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                      Attachments ({msg.attachments.length})
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {msg.attachments.map((att, attIdx) => {
                        const isImage = ['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'].includes(
                          att.file_name.split('.').pop()?.toLowerCase() || ''
                        );
                        
                        // Create download URL - add fl_attachment for Cloudinary to force download
                        const getDownloadUrl = (url, filename) => {
                          if (url.includes('cloudinary.com')) {
                            // Insert fl_attachment transformation
                            // URL format: https://res.cloudinary.com/cloud/type/upload/v123/path
                            const parts = url.split('/upload/');
                            if (parts.length === 2) {
                              // Remove extension from filename for fl_attachment parameter
                              const nameWithoutExt = filename.replace(/\.[^/.]+$/, '');
                              return `${parts[0]}/upload/fl_attachment:${nameWithoutExt}/${parts[1]}`;
                            }
                          }
                          return url;
                        };
                        
                        const downloadUrl = getDownloadUrl(att.url, att.file_name);
                        const viewUrl = att.url; // Original URL for viewing
                        
                        return (
                          <div
                            key={attIdx}
                            className={`flex items-center gap-2 px-3 py-2 rounded-lg border transition ${
                              isDark 
                                ? 'bg-gray-600 border-gray-500 text-gray-200' 
                                : 'bg-white border-gray-200 text-gray-700'
                            }`}
                            data-testid={`attachment-${idx}-${attIdx}`}
                          >
                            {/* Left side: Clickable to VIEW/ZOOM (opens in new tab) */}
                            <a
                              href={viewUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              className={`flex items-center gap-2 flex-1 min-w-0 cursor-pointer ${
                                isDark ? 'hover:text-blue-300' : 'hover:text-blue-600'
                              }`}
                              title="Click to view"
                            >
                              {isImage ? (
                                <img 
                                  src={att.url} 
                                  alt={att.file_name}
                                  className="w-8 h-8 object-cover rounded flex-shrink-0"
                                />
                              ) : (
                                <svg className="w-5 h-5 text-gray-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                </svg>
                              )}
                              <div className="min-w-0">
                                <p className="text-xs font-medium truncate max-w-[120px]">{att.file_name}</p>
                                <p className="text-xs opacity-60">
                                  {att.file_size < 1024 * 1024 
                                    ? (att.file_size / 1024).toFixed(1) + ' KB'
                                    : (att.file_size / (1024 * 1024)).toFixed(1) + ' MB'
                                  }
                                </p>
                              </div>
                            </a>
                            
                            {/* Right side: Download button */}
                            <a
                              href={downloadUrl}
                              download={att.file_name}
                              className={`p-1.5 rounded-lg transition flex-shrink-0 ${
                                isDark 
                                  ? 'hover:bg-gray-500 text-gray-300 hover:text-white' 
                                  : 'hover:bg-gray-100 text-gray-500 hover:text-gray-700'
                              }`}
                              title="Download file"
                              onClick={(e) => e.stopPropagation()}
                            >
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                              </svg>
                            </a>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        ))}
      </div>

      {/* Reply */}
      {ticket.status !== 'CLOSED' && ticket.status !== 'RESOLVED' && (
        <div className={`p-6 border-t ${isDark ? 'bg-gray-700/30 border-gray-600' : 'bg-gray-50/50'}`}>
          <div className="space-y-3">
            <textarea
              value={newMessage}
              onChange={(e) => setNewMessage(e.target.value)}
              rows={4}
              placeholder={t('typeYourMessage')}
              className={`input-enhanced w-full resize-y min-h-[100px] max-h-[400px] ${isDark ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400' : ''}`}
              style={{ resize: 'vertical' }}
              data-testid="ticket-reply"
            />
            
            {/* File attachments section */}
            <div className="space-y-2">
              {/* Selected files preview */}
              {selectedFiles.length > 0 && (
                <div className={`p-3 rounded-lg ${isDark ? 'bg-gray-600' : 'bg-gray-100'}`}>
                  <p className={`text-xs font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                    Attached files ({selectedFiles.length}/{MAX_FILES})
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {selectedFiles.map((file, idx) => (
                      <div 
                        key={idx}
                        className={`flex items-center gap-2 px-2 py-1.5 rounded-lg ${isDark ? 'bg-gray-700' : 'bg-white'} border ${isDark ? 'border-gray-600' : 'border-gray-200'}`}
                      >
                        {getFileIcon(file.name)}
                        <div className="min-w-0">
                          <p className={`text-xs font-medium truncate max-w-[100px] ${isDark ? 'text-gray-200' : 'text-gray-700'}`}>
                            {file.name}
                          </p>
                          <p className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                            {formatFileSize(file.size)}
                          </p>
                        </div>
                        <button
                          onClick={() => removeFile(idx)}
                          className={`p-1 rounded-full hover:bg-red-100 ${isDark ? 'text-gray-400 hover:text-red-400 hover:bg-red-900/30' : 'text-gray-400 hover:text-red-500'}`}
                          title="Remove file"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {/* File input */}
              <input
                ref={fileInputRef}
                type="file"
                multiple
                onChange={handleFileSelect}
                className="hidden"
                accept=".png,.jpg,.jpeg,.gif,.webp,.bmp,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.rtf,.odt,.ods,.odp,.csv,.zip"
                data-testid="file-input"
              />
            </div>
            
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <button
                  onClick={() => fileInputRef.current?.click()}
                  disabled={selectedFiles.length >= MAX_FILES || sending}
                  className={`flex items-center gap-1.5 px-3 py-2 rounded-lg border transition text-sm ${
                    isDark 
                      ? 'border-gray-600 text-gray-300 hover:bg-gray-700 disabled:opacity-50' 
                      : 'border-gray-300 text-gray-600 hover:bg-gray-50 disabled:opacity-50'
                  }`}
                  title={`Attach files (max ${MAX_FILES}, 25 MB each)`}
                  data-testid="attach-file-btn"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                  </svg>
                  <span>Attach</span>
                </button>
                <span className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                  Max {MAX_FILES} files, 25 MB each
                </span>
              </div>
              <button
                onClick={handleSendMessage}
                disabled={sending || (!newMessage.trim() && selectedFiles.length === 0)}
                className="btn-primary btn-glow"
                data-testid="send-message"
              >
                {uploadingFiles ? 'Uploading...' : sending ? t('sending') : t('sendMessage')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" data-testid="delete-ticket-modal">
          <div className={`p-6 rounded-xl shadow-xl max-w-md w-full mx-4 ${isDark ? 'bg-gray-800 border border-gray-700' : 'bg-white'}`}>
            <h3 className={`text-lg font-semibold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>
              Delete Ticket
            </h3>
            <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
              Are you sure you want to permanently delete this ticket? This action cannot be undone.
            </p>
            <p className={`text-sm mb-6 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
              <strong>Subject:</strong> {ticket.subject}
            </p>
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className={`px-4 py-2 rounded-lg border transition ${isDark ? 'border-gray-600 text-gray-300 hover:bg-gray-700' : 'border-gray-300 hover:bg-gray-50'}`}
                disabled={deleting}
                data-testid="cancel-delete-ticket"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteTicket}
                disabled={deleting}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition disabled:opacity-50"
                data-testid="confirm-delete-ticket"
              >
                {deleting ? 'Deleting...' : 'Delete Ticket'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Message Confirmation Modal */}
      {confirmDeleteMessage && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" data-testid="delete-message-modal">
          <div className={`p-6 rounded-xl shadow-xl max-w-md w-full mx-4 ${isDark ? 'bg-gray-800 border border-gray-700' : 'bg-white'}`}>
            <h3 className={`text-lg font-semibold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>
              Delete Message
            </h3>
            <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
              Are you sure you want to delete this message? This action cannot be undone.
            </p>
            {deletingMessageIndex !== null && ticket.messages && ticket.messages[deletingMessageIndex] && (
              <div className={`p-3 rounded-lg mb-4 ${isDark ? 'bg-gray-700' : 'bg-gray-100'}`}>
                <p className={`text-xs mb-1 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                  <strong>From:</strong> {ticket.messages[deletingMessageIndex].is_staff ? 'ECOMMBX Support' : ticket.messages[deletingMessageIndex].sender_name}
                </p>
                <p className={`text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                  {ticket.messages[deletingMessageIndex].content.length > 100 
                    ? ticket.messages[deletingMessageIndex].content.substring(0, 100) + '...' 
                    : ticket.messages[deletingMessageIndex].content}
                </p>
              </div>
            )}
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => {
                  setConfirmDeleteMessage(false);
                  setDeletingMessageIndex(null);
                }}
                className={`px-4 py-2 rounded-lg border transition ${isDark ? 'border-gray-600 text-gray-300 hover:bg-gray-700' : 'border-gray-300 hover:bg-gray-50'}`}
                data-testid="cancel-delete-message"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteMessage}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition"
                data-testid="confirm-delete-message"
              >
                Delete Message
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function TicketStatusBadge({ status, t }) {
  const colors = {
    OPEN: 'bg-blue-100 text-blue-800 border-blue-300',
    IN_PROGRESS: 'bg-yellow-100 text-yellow-800 border-yellow-300',
    WAITING: 'bg-orange-100 text-orange-800 border-orange-300',
    RESOLVED: 'bg-green-100 text-green-800 border-green-300',
    CLOSED: 'bg-gray-100 text-gray-800 border-gray-300'
  };

  // Translate status labels
  const getStatusLabel = (status) => {
    if (!t) return status.replace('_', ' ');
    switch(status) {
      case 'OPEN': return t('open');
      case 'IN_PROGRESS': return t('inProgress');
      case 'WAITING': return t('waiting');
      case 'RESOLVED': return t('resolved');
      case 'CLOSED': return t('closed');
      default: return status.replace('_', ' ');
    }
  };

  return (
    <span className={`status-badge ${colors[status] || colors.OPEN}`}>
      {getStatusLabel(status)}
    </span>
  );
}

export { TicketStatusBadge };
