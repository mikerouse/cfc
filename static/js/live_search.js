// Helper to attach live search behaviour to an input element.
// This searches the council API as the user types and shows
// matching results in a dropdown list so the user can quickly
// navigate to a council's detail page.
function attachLiveSearch(input, resultsContainer) {
    if (!input || !resultsContainer) return;
    let timer;
    input.addEventListener('input', () => {
        const q = input.value.trim();
        clearTimeout(timer);
        if (q.length < 2) {
            // Hide results when query is too short.
            resultsContainer.innerHTML = '';
            resultsContainer.classList.add('hidden');
            return;
        }
        // Delay the request slightly so we do not hammer the server
        // when the user is typing quickly.
        timer = setTimeout(() => {
            fetch(`/api/councils/search/?q=${encodeURIComponent(q)}`)
                .then(r => r.json())
                .then(items => {
                    resultsContainer.innerHTML = '';
                    if (!items.length) {
                        resultsContainer.classList.add('hidden');
                        return;
                    }
                    // Build a clickable list of results.
                    items.forEach(item => {
                        const li = document.createElement('li');
                        li.textContent = item.name;
                        li.dataset.slug = item.slug;
                        li.className = 'px-2 py-1 hover:bg-gray-200 cursor-pointer';
                        resultsContainer.appendChild(li);
                    });
                    resultsContainer.classList.remove('hidden');
                })
                .catch(() => resultsContainer.classList.add('hidden'));
        }, 200);
    });
    // Navigate to the clicked result's detail page.
    resultsContainer.addEventListener('click', e => {
        if (e.target.dataset.slug) {
            window.location.href = `/councils/${e.target.dataset.slug}/`;
        }
    });
    // Hide the dropdown when clicking outside of the search area.
    document.addEventListener('click', e => {
        if (!resultsContainer.contains(e.target) && e.target !== input) {
            resultsContainer.classList.add('hidden');
        }
    });
}
// Expose so templates can call window.attachLiveSearch
window.attachLiveSearch = attachLiveSearch;
