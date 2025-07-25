// JS helpers for the Edit Figures tab on council detail pages.
// Handles year selection, AJAX form submission and helper attachment.

// Display a transient notification to the user.
// ``html`` controls whether the message is treated as HTML markup or plain text.
function showMessage(text, html = false) {
    // Prefer the contribute page container if present so messages appear
    // below the nav bar rather than at the very top of the page.
    let area = document.getElementById('contrib-msg');
    if (area) {
        // Use ``innerHTML`` only when explicitly allowed so normal messages
        // remain plain text and cannot accidentally inject markup.
        if (html) {
            area.innerHTML = text;
        } else {
            area.textContent = text;
        }
        area.classList.remove('hidden');
        setTimeout(() => area.classList.add('hidden'), 5000);
        return;
    }

    // Fallback to the generic message area used by the edit figures tab.
    area = document.getElementById('message-area');
    if (!area) {
        area = document.createElement('div');
        area.id = 'message-area';
        document.body.prepend(area);
    }
    const div = document.createElement('div');
    div.className = 'message mb-2 p-2 bg-blue-50 border border-blue-300 text-blue-900 rounded flex justify-between items-start';
    const span = document.createElement('span');
    if (html) {
        span.innerHTML = text;
    } else {
        span.textContent = text;
    }
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'close ml-2';
    btn.setAttribute('aria-label', 'Dismiss');
    btn.innerHTML = '&times;';
    div.appendChild(span);
    div.appendChild(btn);
    area.appendChild(div);
    btn.addEventListener('click', () => div.remove());
    setTimeout(() => div.remove(), 8000);
}

async function loadEditTable(year) {
    const url = `${window.location.pathname}edit-table/?year=${encodeURIComponent(year)}`;
    const resp = await fetch(url, {headers: {'X-Requested-With': 'XMLHttpRequest'}});
    const html = await resp.text();
    document.getElementById('edit-table-container').innerHTML = html;
    enhanceEditForms();
}

function enhanceEditForms() {
    document.querySelectorAll('#edit-table-container form.edit-fig-form, #char-table-container form.edit-fig-form').forEach(form => {
        form.addEventListener('submit', async e => {
            e.preventDefault();
            const data = new FormData(form);
            const resp = await fetch(form.action, {method:'POST', body:data, headers:{'X-Requested-With':'XMLHttpRequest'}});
            const out = await resp.json();
            showMessage(out.message || 'Submitted');
            if (out.status) {
                form.parentElement.innerHTML = '<i class="fas fa-clock mr-1"></i>Pending confirmation';
            }
        });
    });
    document.querySelectorAll('#edit-table-container [data-num-input], #char-table-container [data-num-input]').forEach(inp => {
        const helper = inp.closest('tr').querySelector('.num-helper');
        attachNumberHelper(inp, helper);
    });
}

document.addEventListener('DOMContentLoaded', () => {
    const sel = document.getElementById('edit-year-select');
    if (sel) {
        sel.addEventListener('change', () => loadEditTable(sel.value));
        loadEditTable(sel.value);
    }
    enhanceEditForms();
});

