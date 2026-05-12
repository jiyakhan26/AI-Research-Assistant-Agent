/* ============================================================
   Search Agent — Frontend JS
   OpenAlex-powered, smart scoring, no API picker needed
   ============================================================ */

let lastResults = [];

async function searchPapers() {
  const query = document.getElementById('searchQuery').value.trim();
  const maxResults = document.getElementById('maxResults').value;

  if (!query) {
    shakeInput();
    return;
  }

  const btn = document.getElementById('searchBtn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Searching...';

  document.getElementById('resultsArea').classList.add('d-none');
  document.getElementById('emptyState').classList.add('d-none');
  document.getElementById('loadingSpinner').classList.remove('d-none');
  document.getElementById('papersList').innerHTML = '';

  try {
    const res = await fetch('/search/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, source: 'auto', max_results: parseInt(maxResults) })
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    if (data.error) {
      showError(data.error);
      return;
    }

    lastResults = data.papers || [];

    document.getElementById('loadingSpinner').classList.add('d-none');
    document.getElementById('resultsArea').classList.remove('d-none');
    document.getElementById('resultCount').textContent = lastResults.length;
    document.getElementById('queryLabel').textContent = `"${query}"`;

    // Update sort bar counts
    updateFilterBar(lastResults);

    renderPapers(lastResults);

  } catch (err) {
    showError('Could not reach the server. Make sure Flask is running.');
  } finally {
    document.getElementById('loadingSpinner').classList.add('d-none');
    btn.disabled = false;
    btn.innerHTML = '<i class="bi bi-search me-2"></i>Search';
  }
}

/* ── RENDER ─────────────────────────────────────────────────── */

function renderPapers(papers) {
  const list = document.getElementById('papersList');
  list.innerHTML = '';

  if (!papers || papers.length === 0) {
    document.getElementById('resultsArea').classList.add('d-none');
    document.getElementById('emptyState').classList.remove('d-none');
    return;
  }

  papers.forEach((paper, i) => {
    const card = document.createElement('div');
    card.className = 'paper-card-wrap';
    card.style.animationDelay = `${i * 60}ms`;
    card.innerHTML = buildCard(paper, i);
    list.appendChild(card);
  });
}

function buildCard(paper, rank) {
  const score = paper.score || 0;
  const level = paper.recommendation_level || 'low';
  const label = paper.recommendation_label || '';
  const breakdown = paper.score_breakdown || {};

  const scoreColor = {
    top:  '#16a34a',
    good: '#2563eb',
    fair: '#d97706',
    low:  '#6b7280'
  }[level] || '#6b7280';

  const scoreBg = {
    top:  'rgba(22,163,74,0.08)',
    good: 'rgba(37,99,235,0.08)',
    fair: 'rgba(217,119,6,0.08)',
    low:  'rgba(107,114,128,0.08)'
  }[level] || 'rgba(107,114,128,0.08)';

  const topBadge = level === 'top'
    ? `<span class="top-pick-badge"><i class="bi bi-star-fill me-1"></i>Top Pick</span>`
    : '';

  const oaBadge = paper.is_open_access
    ? `<span class="oa-badge" title="Open Access"><i class="bi bi-unlock-fill me-1"></i>Free PDF</span>`
    : '';

  const concepts = (paper.concepts || []).slice(0, 4)
    .map(c => `<span class="concept-tag">${c}</span>`).join('');

  const abstract = paper.abstract || 'No abstract available.';
  const shortAbstract = abstract.length > 280 ? abstract.slice(0, 280) + '…' : abstract;
  const hasMore = abstract.length > 280;

  const breakdownHtml = `
    <div class="score-breakdown">
      ${Object.entries(breakdown).map(([k, v]) => `
        <div class="breakdown-row">
          <span class="breakdown-label">${breakdownLabel(k)}</span>
          <div class="breakdown-bar-wrap">
            <div class="breakdown-bar" style="width:${Math.round((v / maxBreakdown(k)) * 100)}%; background:${scoreColor}"></div>
          </div>
          <span class="breakdown-val">${v}</span>
        </div>`).join('')}
    </div>`;

  return `
    <div class="paper-card ${level === 'top' ? 'paper-card--top' : ''}">
      <div class="paper-card-inner">

        <!-- LEFT: rank + score -->
        <div class="paper-rank-col">
          <div class="rank-num">#${rank + 1}</div>
          <div class="score-ring" style="--score-color:${scoreColor}; --score-bg:${scoreBg};">
            <svg viewBox="0 0 36 36" class="score-svg">
              <circle class="score-track" cx="18" cy="18" r="15.9"/>
              <circle class="score-fill" cx="18" cy="18" r="15.9"
                stroke="${scoreColor}"
                stroke-dasharray="${score} ${100 - score}"
                stroke-dashoffset="25"/>
            </svg>
            <div class="score-num" style="color:${scoreColor}">${score}</div>
          </div>
          <div class="score-label" style="color:${scoreColor}">${label}</div>
        </div>

        <!-- RIGHT: content -->
        <div class="paper-content-col">
          <div class="paper-badges-row">
            <span class="source-badge source-badge--${paper.source_badge || 'openalex'}">${paper.source}</span>
            ${oaBadge}
            ${topBadge}
            ${paper.year ? `<span class="year-badge">${paper.year}</span>` : ''}
            ${paper.citation_count > 0
              ? `<span class="cite-badge"><i class="bi bi-quote me-1"></i>${paper.citation_count.toLocaleString()} citations</span>`
              : ''}
          </div>

          <h5 class="paper-title">
            ${paper.url
              ? `<a href="${paper.url}" target="_blank" rel="noopener">${paper.title}</a>`
              : paper.title}
          </h5>

          ${paper.authors ? `<p class="paper-authors"><i class="bi bi-person me-1"></i>${paper.authors}</p>` : ''}
          ${paper.venue ? `<p class="paper-venue"><i class="bi bi-journal me-1"></i>${paper.venue}</p>` : ''}

          <div class="paper-abstract">
            <span class="abstract-text" id="abs-${rank}">${shortAbstract}</span>
            ${hasMore ? `<button class="expand-btn" onclick="expandAbstract(${rank}, \`${escapeForAttr(abstract)}\`)">Show more</button>` : ''}
          </div>

          ${concepts ? `<div class="concepts-row">${concepts}</div>` : ''}

          <!-- Score breakdown (collapsible) -->
          <details class="score-details">
            <summary class="score-summary">
              <i class="bi bi-bar-chart me-1"></i>Why this score?
            </summary>
            ${breakdownHtml}
          </details>

          <div class="paper-actions">
            ${paper.url ? `<a href="${paper.url}" target="_blank" class="action-btn action-btn--view"><i class="bi bi-box-arrow-up-right me-1"></i>View</a>` : ''}
            ${paper.pdf_url ? `<a href="${paper.pdf_url}" target="_blank" class="action-btn action-btn--pdf"><i class="bi bi-file-earmark-pdf me-1"></i>PDF</a>` : ''}
            <button class="action-btn action-btn--related" onclick="findRelated(${rank})">
              <i class="bi bi-diagram-3 me-1"></i>Related
            </button>
            <button class="action-btn action-btn--save" onclick="savePaper(${rank}, this)">
              <i class="bi bi-bookmark me-1"></i>Save
            </button>
          </div>
        </div>
      </div>
    </div>`;
}

function breakdownLabel(key) {
  const labels = {
    relevance: 'Relevance',
    citations: 'Citations',
    recency: 'Recency',
    open_access: 'Open Access',
    abstract: 'Abstract'
  };
  return labels[key] || key;
}

function maxBreakdown(key) {
  const maxes = { relevance: 40, citations: 35, recency: 15, open_access: 5, abstract: 5 };
  return maxes[key] || 10;
}

/* ── FILTER / SORT ───────────────────────────────────────────── */

function updateFilterBar(papers) {
  const counts = { all: papers.length, top: 0, good: 0, fair: 0 };
  papers.forEach(p => { if (counts[p.recommendation_level] !== undefined) counts[p.recommendation_level]++; });
  document.getElementById('count-all').textContent  = counts.all;
  document.getElementById('count-top').textContent  = counts.top;
  document.getElementById('count-good').textContent = counts.good;
  document.getElementById('count-fair').textContent = counts.fair;
}

function filterPapers(level) {
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  document.querySelector(`.filter-btn[data-level="${level}"]`).classList.add('active');

  const filtered = level === 'all'
    ? lastResults
    : lastResults.filter(p => p.recommendation_level === level);
  renderPapers(filtered);
}

function sortPapers(by) {
  const sorted = [...lastResults];
  if (by === 'score')    sorted.sort((a, b) => (b.score || 0) - (a.score || 0));
  if (by === 'year')     sorted.sort((a, b) => (b.year || 0) - (a.year || 0));
  if (by === 'citations') sorted.sort((a, b) => (b.citation_count || 0) - (a.citation_count || 0));
  renderPapers(sorted);
}

/* ── ABSTRACT EXPAND ─────────────────────────────────────────── */

function expandAbstract(rank, full) {
  const el = document.getElementById(`abs-${rank}`);
  if (el) {
    el.textContent = full;
    el.nextElementSibling && el.nextElementSibling.remove();
  }
}

/* ── RELATED PAPERS ──────────────────────────────────────────── */

async function findRelated(rank) {
  const paper = lastResults[rank];
  if (!paper) return;

  document.getElementById('relatedModalTitle').textContent = paper.title;
  const listEl = document.getElementById('relatedPapersList');
  listEl.innerHTML = `
    <div class="text-center py-5">
      <div class="spinner-border text-primary mb-3"></div>
      <p class="text-muted small">Finding related work…</p>
    </div>`;

  const modal = new bootstrap.Modal(document.getElementById('relatedModal'));
  modal.show();

  try {
    const res = await fetch('/search/related', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: paper.title, abstract: paper.abstract || '' })
    });
    const data = await res.json();
    const papers = data.papers || [];

    if (!papers.length) {
      listEl.innerHTML = '<p class="text-center text-muted py-4">No related papers found.</p>';
      return;
    }

    listEl.innerHTML = papers.map(p => `
      <div class="related-card">
        <div class="d-flex align-items-center gap-2 mb-1">
          <span class="source-badge source-badge--${p.source_badge || 'openalex'} badge-sm">${p.source}</span>
          ${p.score ? `<span class="score-pill" style="background:${scoreColorFor(p.recommendation_level)}">${p.score}/100</span>` : ''}
          ${p.year ? `<span class="year-badge badge-sm">${p.year}</span>` : ''}
        </div>
        <h6 class="related-title">${p.url ? `<a href="${p.url}" target="_blank">${p.title}</a>` : p.title}</h6>
        <p class="related-authors">${p.authors || ''}</p>
        <p class="related-abstract">${(p.abstract || '').slice(0, 200)}${(p.abstract || '').length > 200 ? '…' : ''}</p>
        <div class="d-flex gap-2 mt-2">
          ${p.url ? `<a href="${p.url}" target="_blank" class="action-btn action-btn--view btn-xs"><i class="bi bi-box-arrow-up-right me-1"></i>View</a>` : ''}
          ${p.pdf_url ? `<a href="${p.pdf_url}" target="_blank" class="action-btn action-btn--pdf btn-xs"><i class="bi bi-file-earmark-pdf me-1"></i>PDF</a>` : ''}
        </div>
      </div>`).join('');
  } catch {
    listEl.innerHTML = '<p class="text-danger text-center py-3">Error loading related papers.</p>';
  }
}

function scoreColorFor(level) {
  return { top: '#16a34a', good: '#2563eb', fair: '#d97706', low: '#6b7280' }[level] || '#6b7280';
}

/* ── SAVE PAPER ──────────────────────────────────────────────── */

function savePaper(rank, btn) {
  const paper = lastResults[rank];
  if (!paper) return;

  let saved = JSON.parse(localStorage.getItem('saved_papers') || '[]');
  const exists = saved.some(p => p.paper_id === paper.paper_id);

  if (exists) {
    btn.innerHTML = '<i class="bi bi-bookmark me-1"></i>Save';
    btn.classList.remove('action-btn--saved');
    saved = saved.filter(p => p.paper_id !== paper.paper_id);
  } else {
    btn.innerHTML = '<i class="bi bi-bookmark-fill me-1"></i>Saved';
    btn.classList.add('action-btn--saved');
    saved.push(paper);
  }
  localStorage.setItem('saved_papers', JSON.stringify(saved));
}

/* ── UTILITIES ───────────────────────────────────────────────── */

function shakeInput() {
  const el = document.getElementById('searchQuery');
  el.classList.add('shake');
  el.focus();
  setTimeout(() => el.classList.remove('shake'), 500);
}

function showError(msg) {
  document.getElementById('loadingSpinner').classList.add('d-none');
  const list = document.getElementById('papersList');
  list.innerHTML = `
    <div class="error-state">
      <i class="bi bi-exclamation-triangle-fill text-danger fs-2 mb-2 d-block"></i>
      <p class="text-danger fw-semibold">${msg}</p>
    </div>`;
  document.getElementById('resultsArea').classList.remove('d-none');
}

function escapeForAttr(str) {
  return (str || '')
    .replace(/\\/g, '\\\\')
    .replace(/`/g, '\\`')
    .replace(/\$/g, '\\$')
    .slice(0, 800);
}

/* ── ENTER KEY ───────────────────────────────────────────────── */
document.getElementById('searchQuery')?.addEventListener('keydown', e => {
  if (e.key === 'Enter') searchPapers();
});

/* ── AUTO SEARCH FROM URL PARAM ─────────────────────────────── */
(function () {
  const q = new URLSearchParams(window.location.search).get('q');
  if (q) {
    document.getElementById('searchQuery').value = q;
    searchPapers();
  }
})();