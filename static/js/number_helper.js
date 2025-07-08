// Helper that displays formatted values next to numeric inputs so
// users can easily confirm large figures (in thousands, millions, etc.).
function attachNumberHelper(input) {
    if (!input) return;
    const span = document.createElement('span');
    span.className = 'ml-2 text-gray-500 text-sm';
    input.after(span);
    function update(val) {
        const num = Number(val.replace(/,/g, ''));
        if (isNaN(num)) { span.textContent = ''; return; }
        let text = num.toLocaleString();
        const abs = Math.abs(num);
        if (abs >= 1e9) { text += ` (${(num/1e9).toFixed(2)}b)`; }
        else if (abs >= 1e6) { text += ` (${(num/1e6).toFixed(2)}m)`; }
        else if (abs >= 1e3) { text += ` (${(num/1e3).toFixed(2)}k)`; }
        span.textContent = text;
    }
    update(input.value);
    input.addEventListener('input', e => update(e.target.value));
}

// Auto attach to any element with the data-num-input attribute.
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-num-input]').forEach(attachNumberHelper);
});

// Expose the helper for manual use if needed.
window.attachNumberHelper = attachNumberHelper;
