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
    // Store the last set of issue IDs so the periodic checker can report what
    // changed after each refresh. This helps volunteers see when their
    // contributions remove items from the queue.
    let currentIds = new Set();

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
        // When checking for updates, capture the current issue details so we
        // can compare after the refresh completes.
        const before = params.check ? gatherInfo() : null;

        let resp;
        try {
            resp = await fetch(url, {
                headers: {'X-Requested-With': 'XMLHttpRequest'},
            });
        } catch (err) {
            // Network failures should not crash the UI. Inform the user and
            // abort this refresh attempt.
            showMessage('Error contacting server');
            return;
        }
        if (!resp.ok) {
            // If the server responds with an error page (for example a 500
            // Internal Server Error) calling ``resp.json()`` would throw.
            // Display a short message instead and skip updating the table.
            showMessage(`Issue loading data (${resp.status})`);
            return;
        }
        let data;
        try {
            data = await resp.json();
        } catch (err) {
            // Sometimes an HTML error page sneaks through which cannot be
            // parsed as JSON. Showing a friendly note avoids the uncaught
            // exception previously seen in the console.
            showMessage('Invalid response from server');
            return;
        }
        container.innerHTML = data.html;
        container.dataset.order = order;
        container.dataset.dir = dir;
        container.dataset.page = page;
        container.dataset.pageSize = pageSize;
        attachHandlers();
        document.dispatchEvent(new Event('issueTableUpdated'));

        if (params.check && before) {
            const after = gatherInfo();
            const removed = Object.keys(before).filter(id => !after[id]);
            if (removed.length) {
                removed.forEach(id => {
                    showMessage(`${before[id]} resolved: removing from queue`);
                });
            }
        }
    }

    // Helper to map issue IDs to a human readable label so the UI can display
    // what changed after a refresh.
    function gatherInfo() {
        const info = {};
        container.querySelectorAll('tr[data-issue]').forEach(row => {
            const id = row.dataset.issue;
            const council = row.querySelector('td a')?.textContent.trim();
            const field = row.querySelector('.issue-field')?.textContent.trim();
            info[id] = `${field} for ${council}`;
        });
        currentIds = new Set(Object.keys(info));
        return info;
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
    // Initial refresh ensures field labels are up to date and captures the
    // starting set of issues.
    load({refresh: true, check: true});

    // Periodically poll the server so the table reflects new data in real time
    // without forcing a full page reload. Volunteers see a brief spinner and a
    // message describing any issues removed since the last check.
    setInterval(() => {
        showMessage('<i class="fas fa-sync-alt fa-spin mr-1"></i> Checking data...');
        load({page: container.dataset.page, refresh: true, check: true});
    }, 60000);
}

document.addEventListener('DOMContentLoaded', () => {
    ['missing-financial', 'missing-characteristic', 'suspicious'].forEach(setupIssueTable);
});
