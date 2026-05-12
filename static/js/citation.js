/* Citation Extraction Agent - Frontend JS */

let allCitations = [];

function handleFileSelect(input) {
  const file = input.files[0];
  if (file) {
    document.getElementById('selectedFileName').textContent = `Selected: ${file.name}`;
    document.getElementById('selectedFileName').classList.remove('d-none');
    document.getElementById('extractPdfBtn').disabled = false;
  }
}

async function extractFromPdf() {
  const fileInput = document.getElementById('pdfFile');
  if (!fileInput.files[0]) { alert('Please select a PDF file.'); return; }

  const formData = new FormData();
  formData.append('file', fileInput.files[0]);

  showSpinner();

  try {
    const res = await fetch('/citation/upload', { method: 'POST', body: formData });
    const data = await res.json();
    if (data.error) { alert('Error: ' + data.error); hideSpinner(); return; }
    allCitations = data.citations;
    renderCitations(data.citations);
  } catch (err) {
    alert('Upload failed. Ensure Flask is running.');
    hideSpinner();
  }
}

async function extractFromText() {
  const text = document.getElementById('textInput').value.trim();
  if (!text) { alert('Please paste some text.'); return; }

  showSpinner();

  try {
    const res = await fetch('/citation/from-text', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    });
    const data = await res.json();
    if (data.error) { alert('Error: ' + data.error); hideSpinner(); return; }
    allCitations = data.citations;
    renderCitations(data.citations);
  } catch (err) {
    alert('Request failed.');
    hideSpinner();
  }
}

function renderCitations(citations) {
  hideSpinner();
  document.getElementById('citationEmpty').classList.add('d-none');

  if (!citations || citations.length === 0) {
    document.getElementById('citationEmpty').textContent = 'No citations detected. Try a paper with a clear References section.';
    document.getElementById('citationEmpty').classList.remove('d-none');
    return;
  }

  document.getElementById('citationCount').textContent = citations.length;
  document.getElementById('citationResults').classList.remove('d-none');

  const list = document.getElementById('citationList');
  list.innerHTML = '';

  citations.forEach((cit, i) => {
    const card = document.createElement('div');
    card.className = 'citation-card';
    card.innerHTML = `
      <div class="d-flex justify-content-between align-items-start mb-2">
        <span class="badge bg-secondary">#${i + 1}</span>
        ${cit.year ? `<span class="badge bg-primary-subtle text-primary">${cit.year}</span>` : ''}
      </div>
      ${cit.title ? `<p class="fw-semibold small mb-1">${cit.title}</p>` : ''}
      ${cit.authors ? `<p class="paper-meta mb-2"><i class="bi bi-person me-1"></i>${cit.authors}</p>` : ''}
      <div class="citation-raw mb-2">${cit.raw_text.substring(0, 200)}${cit.raw_text.length > 200 ? '...' : ''}</div>
      <div class="d-flex gap-2 flex-wrap">
        <div>
          <small class="text-muted">APA:</small>
          <code class="small d-block text-dark">${cit.apa_format || 'N/A'}</code>
        </div>
      </div>`;
    list.appendChild(card);
  });
}

function copyAll(style) {
  if (!allCitations.length) return;
  const texts = allCitations.map(c => style === 'apa' ? c.apa_format : c.ieee_format).filter(Boolean);
  navigator.clipboard.writeText(texts.join('\n\n')).then(() => alert(`${style.toUpperCase()} citations copied to clipboard!`));
}

function showSpinner() {
  document.getElementById('citationSpinner').classList.remove('d-none');
  document.getElementById('citationResults').classList.add('d-none');
  document.getElementById('citationEmpty').classList.add('d-none');
}

function hideSpinner() {
  document.getElementById('citationSpinner').classList.add('d-none');
}

// Drag and drop support
const uploadZone = document.getElementById('uploadZone');
if (uploadZone) {
  uploadZone.addEventListener('dragover', e => { e.preventDefault(); uploadZone.style.borderColor = '#16a34a'; });
  uploadZone.addEventListener('dragleave', () => { uploadZone.style.borderColor = '#cbd5e1'; });
  uploadZone.addEventListener('drop', e => {
    e.preventDefault();
    uploadZone.style.borderColor = '#cbd5e1';
    const file = e.dataTransfer.files[0];
    if (file && file.type === 'application/pdf') {
      const dt = new DataTransfer();
      dt.items.add(file);
      document.getElementById('pdfFile').files = dt.files;
      handleFileSelect(document.getElementById('pdfFile'));
    } else {
      alert('Please drop a PDF file.');
    }
  });
}