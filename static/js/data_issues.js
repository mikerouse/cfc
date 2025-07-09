// Helper functions for the contribute page tables.
// Handles search, sorting and pagination using AJAX so the
// user can work through large issue lists without reloading
// the entire page each time.

function setupIssueTable(type) {
    const searchInput = document.getElementById(`${type}-search`);
    const container = document.getElementById(`${type}-data-container`);
    if (!container) return;

    let timer;

    async function load(params = {}) {
        const order = params.order || container.dataset.order || 'council';
        const dir = params.dir || container.dataset.dir || 'asc';
        const page = params.page || container.dataset.page || 1;
        const q = searchInput.value.trim();
        let url = `/contribute/issues/?type=${type}&page=${page}&order=${order}&dir=${dir}`;
        if (q) url += `&q=${encodeURIComponent(q)}`;
        const resp = await fetch(url, {headers: {'X-Requested-With': 'XMLHttpRequest'}});
        const data = await resp.json();
        container.innerHTML = data.html;
        container.dataset.order = order;
        container.dataset.dir = dir;
        container.dataset.page = page;
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
            btn.addEventListener('click', () => {
                load({page: btn.dataset.page});
            });
        });
    }

    searchInput.addEventListener('input', () => {
        clearTimeout(timer);
        timer = setTimeout(() => load({page: 1}), 300);
    });

    attachHandlers();
}

document.addEventListener('DOMContentLoaded', () => {
    ['missing', 'suspicious'].forEach(setupIssueTable);
});
