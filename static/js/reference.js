/* Reference Formatting Agent - Frontend JS */

let lastResult = {};

async function formatReference() {
  const data = {
    authors: document.getElementById('refAuthors').value.trim(),
    title:   document.getElementById('refTitle').value.trim(),
    year:    document.getElementById('refYear').value.trim(),
    journal: document.getElementById('refJournal').value.trim(),
    url:     document.getElementById('refUrl').value.trim(),
    style:   document.getElementById('refStyle').value
  };

  if (!data.title && !data.authors) { alert('Please provide at least a title or authors.'); return; }

  try {
    const res = await fetch('/reference/format', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    const result = await res.json();

    lastResult = result;
    document.getElementById('apaOutput').textContent = result.apa || 'Could not format.';
    document.getElementById('ieeeOutput').textContent = result.ieee || 'Could not format.';
    document.getElementById('mlaOutput').textContent = result.mla || 'Could not format.';

    document.getElementById('refEmpty').classList.add('d-none');
    document.getElementById('refResults').classList.remove('d-none');
  } catch (err) {
    alert('Request failed. Ensure Flask is running.');
  }
}

async function batchFormat() {
  const raw = document.getElementById('batchInput').value.trim();
  if (!raw) { alert('Please paste JSON citation data.'); return; }

  let citations;
  try {
    citations = JSON.parse(raw);
  } catch (e) {
    alert('Invalid JSON. Please check your input format.'); return;
  }

  const style = document.getElementById('refStyle').value;

  try {
    const res = await fetch('/reference/batch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ citations, style })
    });
    const data = await res.json();

    if (data.error) { alert('Error: ' + data.error); return; }

    const batchList = document.getElementById('batchList');
    batchList.innerHTML = '';
    data.formatted.forEach((item, i) => {
      batchList.innerHTML += `
        <div class="card mb-2">
          <div class="card-body py-2">
            <span class="badge bg-secondary me-2">[${i+1}]</span>
            <span class="formatted-citation small">${item.formatted}</span>
            <button class="btn btn-xs btn-link float-end" onclick="copyText('${escapeStr(item.formatted)}')">
              <i class="bi bi-copy"></i>
            </button>
          </div>
        </div>`;
    });
    document.getElementById('batchResults').classList.remove('d-none');
  } catch (err) {
    alert('Request failed.');
  }
}

function copyFormat(style) {
  const text = lastResult[style] || '';
  if (!text) { alert('No formatted reference to copy.'); return; }
  navigator.clipboard.writeText(text).then(() => {
    const btn = event.target.closest('button');
    const orig = btn.innerHTML;
    btn.innerHTML = '<i class="bi bi-check me-1"></i>Copied!';
    setTimeout(() => btn.innerHTML = orig, 1500);
  });
}

function copyText(text) {
  navigator.clipboard.writeText(text);
}

function escapeStr(str) {
  return str.replace(/'/g, "\\'").replace(/"/g, '&quot;');
}

// Allow Enter on form fields to trigger format
['refAuthors','refTitle','refYear','refJournal','refUrl'].forEach(id => {
  document.getElementById(id)?.addEventListener('keydown', e => {
    if (e.key === 'Enter') formatReference();
  });
});