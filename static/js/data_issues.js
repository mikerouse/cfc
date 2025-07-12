// Real-time contribute table helper.
// Loads issue data via AJAX and updates when WebSocket events arrive.
// The heavy database refresh is triggered manually to avoid lock ups.
// God Mode users have extra delete controls wired up by this script.

function contributeTable() {
  const container = document.getElementById('issues-data-container');
  if (!container) return;
  const searchInput = document.getElementById('issues-search');
  const typeSelect = document.getElementById('issues-type');
  const sizeInput = document.getElementById('issues-size');
  const loading = document.getElementById('issues-loading');
  const refreshBtn = document.getElementById('issues-refresh');

  let timer;

  async function load(params = {}) {
    const order = params.order || container.dataset.order || 'council';
    const dir = params.dir || container.dataset.dir || 'asc';
    const page = params.page || container.dataset.page || 1;
    const pageSize = params.pageSize || container.dataset.pageSize || sizeInput.value;
    const q = searchInput.value.trim();
    const type = typeSelect.value;
    let url = `/contribute/issues/?type=${type}&page=${page}&order=${order}&dir=${dir}&page_size=${pageSize}`;
    if (q) url += `&q=${encodeURIComponent(q)}`;
    if (params.refresh) url += '&refresh=1';
    if (loading) loading.classList.remove('hidden');
    const resp = await fetch(url, {headers:{'X-Requested-With':'XMLHttpRequest'}});
    const data = await resp.json();
    container.innerHTML = data.html;
    container.dataset.order = order;
    container.dataset.dir = dir;
    container.dataset.page = page;
    container.dataset.pageSize = pageSize;
    // Wire up table interactions once the new HTML has been inserted.
    attachHandlers();
    attachRejectButtons();
    attachDeleteButtons();
    if (loading) loading.classList.add('hidden');
  }

  function attachHandlers() {
    // Sortable column headers and pagination links
    container.querySelectorAll('.sortable').forEach(th => {
      th.addEventListener('click', () => {
        const sort = th.dataset.sort;
        const current = container.dataset.order;
        const dir = (sort === current && container.dataset.dir === 'asc') ? 'desc' : 'asc';
        load({order: sort, dir: dir, page: 1});
      });
    });
    container.querySelectorAll('.issues-page').forEach(btn => {
      btn.addEventListener('click', () => load({page: btn.dataset.page}));
    });
  }

  searchInput.addEventListener('input', () => {
    clearTimeout(timer);
    timer = setTimeout(() => load({page: 1}), 300);
  });
  typeSelect.addEventListener('change', () => load({page:1}));
  sizeInput.addEventListener('change', () => load({page:1, pageSize:sizeInput.value}));

  // Initial load without triggering a heavy refresh
  load();
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => load({refresh:true}));
  }

  // WebSocket connection for real-time updates
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
  const socket = new WebSocket(`${protocol}://${window.location.host}/ws/contribute/`);

  socket.onopen = function(e) {
    console.log("[open] Connection established");
  };

  socket.addEventListener('message', () => {
    console.log("[message] Message received from server");
    load({page: container.dataset.page});
    updateModeratorPanel();
  });

  socket.onclose = function(event) {
    if (event.wasClean) {
      console.log(`[close] Connection closed cleanly, code=${event.code} reason=${event.reason}`);
    } else {
      // e.g. server process killed or network down
      // event.code is usually 1006 in this case
      console.error('[close] Connection died');
    }
  };

  socket.onerror = function(error) {
    console.error(`[error] WebSocket Error: ${error.message}`);
  };
}

function attachRejectButtons() {
  // Open the reject modal pre-populated with the correct form action.
  document.querySelectorAll('.reject-btn').forEach(btn => {
    btn.onclick = e => {
      e.preventDefault();
      document.getElementById('reject-form').action = btn.dataset.url;
      document.getElementById('reject-modal').classList.remove('hidden');
    };
  });
}

function attachDeleteButtons() {
  // God Mode users get a simple confirmation modal before deleting.
  document.querySelectorAll('.delete-btn').forEach(btn => {
    btn.onclick = e => {
      e.preventDefault();
      document.getElementById('delete-form').action = btn.dataset.url;
      document.getElementById('delete-modal').classList.remove('hidden');
    };
  });
}

async function updateModeratorPanel() {
  const panel = document.getElementById('moderator-panel');
  if (!panel) return;
  const resp = await fetch('/contribute/mod-panel/', {headers:{'X-Requested-With':'XMLHttpRequest'}});
  const data = await resp.json();
  panel.innerHTML = data.html;
}

document.addEventListener('DOMContentLoaded', contributeTable);
