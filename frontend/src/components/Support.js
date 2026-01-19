// Support Ticket Components
import React, { useState, useEffect } from 'react';
import api from '../api';
import { useLanguage, useTheme } from '../contexts/AppContext';

export function SupportTickets({ isAdmin = false }) {
  const [tickets, setTickets] = useState([]);
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('all');
  const { t } = useLanguage();
  const { isDark } = useTheme();

  useEffect(() => {
    fetchTickets();
  }, [statusFilter]);

  const fetchTickets = async () => {
    try {
      if (isAdmin) {
        const params = statusFilter !== 'all' ? `?status=${statusFilter}` : '';
        const response = await api.get(`/admin/tickets${params}`);
        setTickets(response.data);
      } else {
        const response = await api.get('/tickets');
        setTickets(response.data);
      }
    } catch (err) {
      console.error('Failed to fetch tickets:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleTicketCreated = () => {
    setShowCreateForm(false);
    fetchTickets();
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
      </div>

      {isAdmin && (
        <div className="card-enhanced p-4">
          <div className="flex items-center space-x-4">
            <label className="text-sm font-medium text-gray-700">Filter by Status:</label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="input-enhanced"
              data-testid="admin-ticket-filter"
            >
              <option value="all">All Tickets</option>
              <option value="OPEN">Open</option>
              <option value="IN_PROGRESS">In Progress</option>
              <option value="WAITING">Waiting</option>
              <option value="RESOLVED">Resolved</option>
              <option value="CLOSED">Closed</option>
            </select>
            <span className="text-sm text-gray-600">{tickets.length} ticket(s)</span>
          </div>
        </div>
      )}

      {showCreateForm && (
        <CreateTicketForm
          onClose={() => setShowCreateForm(false)}
          onSuccess={handleTicketCreated}
        />
      )}

      {tickets.length === 0 ? (
        <div className="card-blue-accent p-8 text-center animate-card">
          <div className="circle-pattern">
            <p className="text-gray-600">No support tickets yet. Create one if you need help!</p>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Tickets List */}
          <div className="lg:col-span-1">
            <div className="card-enhanced">
              <div className="p-4 border-b bg-blue-50/30">
                <h3 className="font-semibold">Your Tickets</h3>
                <p className="text-sm text-gray-600 mt-1">{tickets.length} ticket(s)</p>
              </div>
              <div className="divide-y max-h-[600px] overflow-y-auto">
                {tickets.map((ticket) => (
                  <div
                    key={ticket.id}
                    onClick={() => setSelectedTicket(ticket)}
                    className={`p-4 cursor-pointer hover-blue-bg ${
                      selectedTicket?.id === ticket.id ? 'bg-blue-50' : ''
                    }`}
                    data-testid={`ticket-${ticket.id}`}
                  >
                    <p className="font-medium">{ticket.subject}</p>
                    <div className="flex items-center justify-between mt-2">
                      <TicketStatusBadge status={ticket.status} />
                      <span className="text-xs text-gray-500">
                        {new Date(ticket.updated_at).toLocaleDateString()}
                      </span>
                    </div>
                    {ticket.messages && ticket.messages.length > 1 && (
                      <p className="text-xs text-gray-500 mt-1">
                        {ticket.messages.length} message(s)
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
                isAdmin={isAdmin}
              />
            ) : (
              <div className="card-blue-accent p-12 text-center">
                <p className="text-gray-600">Select a ticket to view details</p>
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
    <div className="card-enhanced p-6 animate-card">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold">Create Support Ticket</h3>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600"
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
          <label className="block text-sm font-medium text-gray-700 mb-2">Subject</label>
          <input
            type="text"
            value={formData.subject}
            onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
            required
            className="input-enhanced w-full"
            placeholder="Brief description of the issue"
            data-testid="ticket-subject"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Description</label>
          <textarea
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            required
            rows={4}
            className="input-enhanced w-full"
            placeholder="Provide details about your issue..."
            data-testid="ticket-description"
          />
        </div>
        <div className="flex justify-end space-x-3">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={submitting}
            className="btn-primary btn-glow"
            data-testid="submit-ticket"
          >
            {submitting ? 'Creating...' : 'Create Ticket'}
          </button>
        </div>
      </form>
    </div>
  );
}

function TicketDetails({ ticket, onUpdate, isAdmin = false }) {
  const [newMessage, setNewMessage] = useState('');
  const [sending, setSending] = useState(false);

  const handleSendMessage = async () => {
    if (!newMessage.trim()) return;

    setSending(true);
    try {
      await api.post(`/tickets/${ticket.id}/messages`, { content: newMessage });
      setNewMessage('');
      onUpdate();
    } catch (err) {
      alert('Failed to send message');
    } finally {
      setSending(false);
    }
  };

  const handleStatusChange = async (newStatus) => {
    try {
      await api.patch(`/admin/tickets/${ticket.id}/status`, { status: newStatus });
      alert('Status updated successfully');
      onUpdate();
    } catch (err) {
      alert('Failed to update status');
    }
  };

  return (
    <div className="card-enhanced space-y-4">
      {/* Header */}
      <div className="p-6 border-b bg-blue-50/30">
        <div className="flex justify-between items-start">
          <div>
            <h3 className="text-lg font-semibold">{ticket.subject}</h3>
            <p className="text-sm text-gray-600 mt-1">
              Created {new Date(ticket.created_at).toLocaleString()}
            </p>
            {isAdmin && ticket.user_id && (
              <p className="text-xs text-gray-500 mt-1">
                Customer ID: {ticket.user_id}
              </p>
            )}
          </div>
          <div className="text-right">
            <TicketStatusBadge status={ticket.status} />
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
                ? 'bg-blue-50 border border-blue-200' 
                : 'bg-gray-50 border border-gray-200'
            }`}
            data-testid={`message-${idx}`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium">
                {msg.sender_name}
                {msg.is_staff && (
                  <span className="ml-2 text-xs bg-blue-600 text-white px-2 py-1 rounded">
                    Staff
                  </span>
                )}
              </span>
              <span className="text-xs text-gray-500">
                {new Date(msg.created_at).toLocaleString()}
              </span>
            </div>
            <p className="text-sm text-gray-700">{msg.content}</p>
          </div>
        ))}
      </div>

      {/* Reply */}
      {ticket.status !== 'CLOSED' && ticket.status !== 'RESOLVED' && (
        <div className="p-6 border-t bg-gray-50/50">
          <div className="space-y-3">
            <textarea
              value={newMessage}
              onChange={(e) => setNewMessage(e.target.value)}
              rows={3}
              placeholder="Type your message..."
              className="input-enhanced w-full"
              data-testid="ticket-reply"
            />
            <button
              onClick={handleSendMessage}
              disabled={sending || !newMessage.trim()}
              className="btn-primary btn-glow"
              data-testid="send-message"
            >
              {sending ? 'Sending...' : 'Send Message'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function TicketStatusBadge({ status }) {
  const colors = {
    OPEN: 'bg-blue-100 text-blue-800 border-blue-300',
    IN_PROGRESS: 'bg-yellow-100 text-yellow-800 border-yellow-300',
    WAITING: 'bg-orange-100 text-orange-800 border-orange-300',
    RESOLVED: 'bg-green-100 text-green-800 border-green-300',
    CLOSED: 'bg-gray-100 text-gray-800 border-gray-300'
  };

  return (
    <span className={`status-badge ${colors[status] || colors.OPEN}`}>
      {status.replace('_', ' ')}
    </span>
  );
}

export { TicketStatusBadge };
