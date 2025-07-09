// Simple live updating log for the God Mode page
// Fetches data from the server every 5 seconds and renders rows

(function () {
  const tableBody = document.querySelector('#activity-log-body');
  if (!tableBody) return;

  let page = 1;
  let search = '';
  let sort = '';

  function fetchLogs() {
    const params = new URLSearchParams({ page, q: search, sort });
    fetch(`/god-mode/activity-log/?${params.toString()}`)
      .then(r => r.json())
      .then(data => {
        tableBody.innerHTML = '';
        data.results.forEach(row => {
          const tr = document.createElement('tr');
          tr.className = 'odd:bg-gray-50';
          tr.innerHTML = `
            <td class="border px-2 py-1">${row.time}</td>
            <td class="border px-2 py-1">${row.user}</td>
            <td class="border px-2 py-1">${row.council}</td>
            <td class="border px-2 py-1">${row.page}</td>
            <td class="border px-2 py-1">${row.activity}</td>
            <td class="border px-2 py-1">${row.button}</td>
            <td class="border px-2 py-1">${row.action}</td>
            <td class="border px-2 py-1">${row.response}</td>
            <td class="border px-2 py-1">${row.extra}</td>`;
          tableBody.appendChild(tr);
        });
      });
  }

  document.getElementById('activity-search').addEventListener('input', (e) => {
    search = e.target.value;
    page = 1;
    fetchLogs();
  });

  // Poll every 5 seconds while the page is visible
  fetchLogs();
  setInterval(fetchLogs, 5000);
})();
