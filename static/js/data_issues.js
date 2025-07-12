// Real-time contribute table helper
// Connects via WebSocket and refreshes when the server broadcasts updates.

function contributeTable() {
  const container = document.getElementById('issues-data-container');
  if (!container) return;
  const searchInput = document.getElementById('issues-search');
  const typeSelect = document.getElementById('issues-type');
  const sizeInput = document.getElementById('issues-size');

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
    const resp = await fetch(url, {headers:{'X-Requested-With':'XMLHttpRequest'}});
    const data = await resp.json();
    container.innerHTML = data.html;
    container.dataset.order = order;
    container.dataset.dir = dir;
    container.dataset.page = page;
    container.dataset.pageSize = pageSize;
    attachHandlers();
  }

  function attachHandlers() {
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

  load({refresh:true});

  // WebSocket connection for real-time updates
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
  const socket = new WebSocket(`${protocol}://${window.location.host}/ws/contribute/`);
  socket.addEventListener('message', () => {
    load({page: container.dataset.page});
    updateModeratorPanel();
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
