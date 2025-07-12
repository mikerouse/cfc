// Helper functions for the contribute page tables.
// Handles search, sorting and pagination using AJAX so the
// user can work through large issue lists without reloading
// the entire page each time.

function setupIssueTable(containerId) {
    const container = document.getElementById(`${containerId}-data-container`);
    const searchInput = document.getElementById(`${containerId}-search`);
    const sizeInput = document.getElementById(`${containerId}-size`);
    const refreshBtn = document.getElementById(`${containerId}-refresh`);
    if (!container) return;
    // Each container stores the ``type`` (missing or suspicious) and optional
    // ``category`` so the AJAX endpoint can filter appropriately.
    const type = container.dataset.type;
    const category = container.dataset.category;

    let timer;

    async function load(params = {}) {
        const order = params.order || container.dataset.order || 'council';
        const dir = params.dir || container.dataset.dir || 'asc';
        const page = params.page || container.dataset.page || 1;
        const pageSize = params.pageSize || container.dataset.pageSize || (sizeInput ? sizeInput.value : 50);
        const q = searchInput.value.trim();
        let url = `/contribute/issues/?type=${type}&page=${page}&order=${order}&dir=${dir}&page_size=${pageSize}`;
        if (category) url += `&category=${category}`;
        if (q) url += `&q=${encodeURIComponent(q)}`;
        if (params.refresh) url += '&refresh=1';
        const resp = await fetch(url, {headers: {'X-Requested-With': 'XMLHttpRequest'}});
        const data = await resp.json();
        container.innerHTML = data.html;
        container.dataset.order = order;
        container.dataset.dir = dir;
        container.dataset.page = page;
        container.dataset.pageSize = pageSize;
        attachHandlers();
        document.dispatchEvent(new Event('issueTableUpdated'));
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
            btn.addEventListener('click', () => {
                load({page: btn.dataset.page});
            });
        });
    }

    searchInput.addEventListener('input', () => {
        clearTimeout(timer);
        timer = setTimeout(() => load({page: 1}), 300);
    });

    if (sizeInput) {
        sizeInput.addEventListener('change', () => {
            load({page: 1, pageSize: sizeInput.value});
        });
    }

    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => load({page: 1, refresh: true}));
    }

    attachHandlers();
    // Initial refresh ensures field labels are up to date
    load({refresh: true});
}

document.addEventListener('DOMContentLoaded', () => {
    ['missing-financial', 'missing-characteristic', 'suspicious'].forEach(setupIssueTable);
});
