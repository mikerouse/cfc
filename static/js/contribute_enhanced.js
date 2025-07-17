// Enhanced contribute page with inline editing and real-time updates
// Handles AJAX loading, WebSocket updates, and quick editing modals

class ContributeManager {
  constructor() {
    this.container = document.getElementById('issues-data-container');
    this.searchInput = document.getElementById('issues-search');
    this.typeSelect = document.getElementById('issues-type');
    this.categorySelect = document.getElementById('issues-category');
    this.sizeInput = document.getElementById('issues-size');
    this.loading = document.getElementById('issues-loading');
    this.refreshBtn = document.getElementById('issues-refresh');
    this.resultsInfo = document.getElementById('results-info');
    
    // Quick edit modal elements
    this.editModal = document.getElementById('quick-edit-modal');
    this.editForm = document.getElementById('quick-edit-form');
    this.editTitle = document.getElementById('edit-modal-title');
    this.editFieldLabel = document.getElementById('edit-field-label');
    this.editValue = document.getElementById('edit-value');
    this.editValueSelect = document.getElementById('edit-value-select');
    
    this.timer = null;
    this.stats = { missing: 0, pending: 0, suspicious: 0 };
    
    this.init();
  }
  
  init() {
    this.setupEventListeners();
    this.setupWebSocket();
    this.load();
    this.loadStats();
    this.loadModeratorPanel();
  }
  
  setupEventListeners() {
    // Search and filter controls
    this.searchInput.addEventListener('input', () => {
      clearTimeout(this.timer);
      this.timer = setTimeout(() => this.load({ page: 1 }), 300);
    });
    
    this.typeSelect.addEventListener('change', () => this.load({ page: 1 }));
    this.categorySelect.addEventListener('change', () => this.load({ page: 1 }));
    this.sizeInput.addEventListener('change', () => this.load({ page: 1, pageSize: this.sizeInput.value }));
    
    if (this.refreshBtn) {
      this.refreshBtn.addEventListener('click', () => this.load({ refresh: true }));
    }
    
    // Edit modal events
    document.getElementById('edit-modal-close').addEventListener('click', () => this.closeEditModal());
    document.getElementById('edit-cancel').addEventListener('click', () => this.closeEditModal());
    this.editForm.addEventListener('submit', (e) => this.submitEdit(e));
    
    // Close modal on outside click
    this.editModal.addEventListener('click', (e) => {
      if (e.target === this.editModal) {
        this.closeEditModal();
      }
    });
  }
  
  setupWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    this.socket = new WebSocket(`${protocol}://${window.location.host}/ws/contribute/`);
    
    this.socket.onopen = () => {
      console.log('[WebSocket] Connected');
    };
    
    this.socket.onmessage = (event) => {
      console.log('[WebSocket] Message received');
      this.load({ page: this.container.dataset.page });
      this.loadStats();
      this.loadModeratorPanel();
    };
    
    this.socket.onclose = (event) => {
      if (!event.wasClean) {
        console.warn('[WebSocket] Connection lost, attempting to reconnect...');
        setTimeout(() => this.setupWebSocket(), 5000);
      }
    };
    
    this.socket.onerror = (error) => {
      console.error('[WebSocket] Error:', error);
    };
  }
  
  async load(params = {}) {
    const order = params.order || this.container.dataset.order || 'council';
    const dir = params.dir || this.container.dataset.dir || 'asc';
    const page = params.page || this.container.dataset.page || 1;
    const pageSize = params.pageSize || this.container.dataset.pageSize || this.sizeInput.value;
    const q = this.searchInput.value.trim();
    const type = this.typeSelect.value;
    const category = this.categorySelect.value;
    
    let url = `/contribute/data-issues-table/?type=${type}&page=${page}&order=${order}&dir=${dir}&page_size=${pageSize}`;
    if (q) url += `&q=${encodeURIComponent(q)}`;
    if (category) url += `&category=${category}`;
    if (params.refresh) url += '&refresh=1';
    
    this.showLoading(true);
    
    try {
      const resp = await fetch(url, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
      });
      const data = await resp.json();
      
      this.container.innerHTML = data.html;
      this.container.dataset.order = order;
      this.container.dataset.dir = dir;
      this.container.dataset.page = page;
      this.container.dataset.pageSize = pageSize;
      
      this.updateResultsInfo(data);
      this.attachTableHandlers();
      this.attachEditHandlers();
      this.attachModeratorHandlers(); // Make sure this is called after loading new content
      
    } catch (error) {
      console.error('Failed to load data:', error);
      this.showMessage('Failed to load data. Please try again.', 'error');
    } finally {
      this.showLoading(false);
    }
  }
  
  async loadStats() {
    try {
      const resp = await fetch('/contribute/stats/', {
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
      });
      const data = await resp.json();
      
      document.getElementById('stat-missing').textContent = data.missing || 0;
      document.getElementById('stat-pending').textContent = data.pending || 0;
      document.getElementById('stat-suspicious').textContent = data.suspicious || 0;
    } catch (error) {
      console.error('Failed to load stats:', error);
    }
  }
  
  async loadModeratorPanel() {
    const panel = document.getElementById('moderator-panel');
    if (!panel) return;
    
    try {
      const resp = await fetch('/contribute/mod-panel/', {
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
      });
      const data = await resp.json();
      
      if (data.html) {
        panel.innerHTML = data.html;
        panel.classList.remove('hidden');
        this.attachModeratorHandlers();
      }
    } catch (error) {
      console.error('Failed to load moderator panel:', error);
    }
  }
  
  attachTableHandlers() {
    // Sortable headers
    this.container.querySelectorAll('.sortable').forEach(th => {
      th.addEventListener('click', () => {
        const sort = th.dataset.sort;
        const current = this.container.dataset.order;
        const dir = (sort === current && this.container.dataset.dir === 'asc') ? 'desc' : 'asc';
        this.load({ order: sort, dir: dir, page: 1 });
      });
    });
    
    // Pagination
    this.container.querySelectorAll('.issues-page').forEach(btn => {
      btn.addEventListener('click', () => this.load({ page: btn.dataset.page }));
    });
  }
  
  attachEditHandlers() {
    // Quick edit buttons for missing data
    this.container.querySelectorAll('.edit-missing').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        this.openEditModal({
          council: btn.dataset.council,
          field: btn.dataset.field,
          year: btn.dataset.year,
          fieldName: btn.dataset.fieldName,
          councilName: btn.dataset.councilName
        });
      });
    });
  }
  
  attachModeratorHandlers() {
    // Approve buttons - scope to the container to find buttons in dynamically loaded content
    this.container.querySelectorAll('.approve-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.preventDefault();
        await this.moderateContribution(btn.dataset.url, 'approve');
      });
    });
    
    // Reject buttons
    this.container.querySelectorAll('.reject-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        // Show reject modal (existing functionality)
        const rejectModal = document.getElementById('reject-modal');
        const rejectForm = document.getElementById('reject-form');
        if (rejectForm && rejectModal) {
          rejectForm.action = btn.dataset.url;
          rejectModal.classList.remove('hidden');
        } else {
          // Fallback - just send reject request
          this.moderateContribution(btn.dataset.url, 'reject');
        }
      });
    });
    
    // Delete buttons
    this.container.querySelectorAll('.delete-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        if (confirm('Are you sure you want to delete this contribution? This action cannot be undone.')) {
          this.moderateContribution(btn.dataset.url, 'delete');
        }
      });
    });
  }
  
  async moderateContribution(url, action) {
    try {
      const csrfToken = this.getCSRFToken();
      if (!csrfToken) {
        throw new Error('CSRF token not found. Please refresh the page.');
      }
      
      const resp = await fetch(url, {
        method: 'POST',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken': csrfToken,
          'Content-Type': 'application/x-www-form-urlencoded',
        }
      });
      
      if (!resp.ok) {
        let errorMsg = `HTTP ${resp.status}: ${resp.statusText}`;
        try {
          const errorData = await resp.json();
          if (errorData.error) {
            errorMsg = errorData.error;
          }
        } catch (e) {
          // If JSON parsing fails, use the default error message
        }
        throw new Error(errorMsg);
      }
      
      const data = await resp.json();
      
      if (data.status === 'success') {
        this.showMessage(data.message || `Contribution ${action}d successfully`, 'success');
        // Reload the current page data
        this.load({ page: this.container.dataset.page });
        this.loadStats();
        this.loadModeratorPanel();
      } else {
        throw new Error(data.error || `Failed to ${action} contribution`);
      }
    } catch (error) {
      console.error(`Error ${action}ing contribution:`, error);
      this.showMessage(`Failed to ${action} contribution: ${error.message}`, 'error');
    }
  }
  
  openEditModal(data) {
    this.editTitle.textContent = `Add ${data.fieldName}`;
    this.editFieldLabel.textContent = `${data.fieldName} for ${data.councilName}`;
    
    document.getElementById('edit-council').value = data.council;
    document.getElementById('edit-field').value = data.field;
    document.getElementById('edit-year').value = data.year || '';
    
    // Reset form
    this.editValue.value = '';
    this.editValue.classList.remove('hidden');
    this.editValueSelect.classList.add('hidden');
    
    // Load field options if it's a list field
    this.loadFieldOptions(data.field);
    
    this.editModal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
    this.editValue.focus();
  }
  
  closeEditModal() {
    this.editModal.classList.add('hidden');
    document.body.style.overflow = '';
  }
  
  async loadFieldOptions(fieldSlug) {
    try {
      const resp = await fetch(`/contribute/field-options/${fieldSlug}/`, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
      });
      
      if (resp.ok) {
        const data = await resp.json();
        
        if (data.options && data.options.length > 0) {
          // Show select dropdown instead of text input
          this.editValue.classList.add('hidden');
          this.editValueSelect.classList.remove('hidden');
          
          this.editValueSelect.innerHTML = '<option value="">Select...</option>';
          data.options.forEach(option => {
            const opt = document.createElement('option');
            opt.value = option.id;
            opt.textContent = option.name;
            this.editValueSelect.appendChild(opt);
          });
          
          this.editValueSelect.focus();
        }
      }
    } catch (error) {
      console.error('Failed to load field options:', error);
    }
  }
  
  async submitEdit(e) {
    e.preventDefault();
    
    const formData = new FormData(this.editForm);
    
    try {
      const resp = await fetch('/contribute/submit/', {
        method: 'POST',
        body: formData,
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken': this.getCSRFToken()
        }
      });
      
      const data = await resp.json();
      
      if (resp.ok) {
        this.showMessage(data.message || 'Contribution submitted successfully', 'success');
        this.closeEditModal();
        this.load({ page: this.container.dataset.page });
        this.loadStats();
      } else {
        this.showMessage(data.error || 'Failed to submit contribution', 'error');
      }
    } catch (error) {
      console.error('Error submitting contribution:', error);
      this.showMessage('Failed to submit contribution', 'error');
    }
  }
  
  updateResultsInfo(data) {
    if (data.total !== undefined) {
      const start = (data.page - 1) * data.page_size + 1;
      const end = Math.min(data.page * data.page_size, data.total);
      this.resultsInfo.textContent = `Showing ${start}-${end} of ${data.total} items`;
    }
  }
  
  showLoading(show) {
    if (this.loading) {
      this.loading.classList.toggle('hidden', !show);
    }
  }
  
  showMessage(text, type = 'info') {
    const msgEl = document.getElementById('contrib-msg');
    if (!msgEl) return;
    
    msgEl.className = `mb-4 p-4 rounded-lg border ${type === 'error' ? 'bg-red-50 border-red-200 text-red-800' : 
                       type === 'success' ? 'bg-green-50 border-green-200 text-green-800' : 
                       'bg-blue-50 border-blue-200 text-blue-800'}`;
    msgEl.textContent = text;
    msgEl.classList.remove('hidden');
    
    setTimeout(() => msgEl.classList.add('hidden'), 5000);
  }
  
  getCSRFToken() {
    // Try multiple ways to get CSRF token
    let token = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    if (!token) {
      token = document.querySelector('meta[name=csrf-token]')?.content;
    }
    if (!token) {
      // Try to get from cookies
      const cookies = document.cookie.split(';');
      for (let cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (name === 'csrftoken') {
          token = value;
          break;
        }
      }
    }
    if (!token) {
      console.warn('CSRF token not found');
    }
    return token || '';
  }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  window.contributeManager = new ContributeManager();
});
