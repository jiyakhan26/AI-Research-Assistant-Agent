/* Plagiarism Detection Agent - Frontend JS */

// Live word count
const input = document.getElementById('plagiarismInput');
if (input) {
  input.addEventListener('input', () => {
    const words = input.value.trim().split(/\s+/).filter(w => w).length;
    document.getElementById('wordCountBadge').textContent = `${words} words`;
  });
}

async function checkPlagiarism() {
  const text = document.getElementById('plagiarismInput').value.trim();
  if (!text) { alert('Please enter some text.'); return; }
  if (text.split(/\s+/).length < 10) { alert('Please enter at least 10 words.'); return; }

  document.getElementById('plagSpinner').classList.remove('d-none');
  document.getElementById('plagResults').classList.add('d-none');
  document.getElementById('plagEmpty').classList.add('d-none');

  try {
    const res = await fetch('/plagiarism/check', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    });
    const data = await res.json();

    if (data.error) { alert('Error: ' + data.error); return; }

    renderResults(data);
  } catch (err) {
    alert('Request failed. Ensure Flask is running.');
  } finally {
    document.getElementById('plagSpinner').classList.add('d-none');
  }
}

function renderResults(data) {
  // Score circle
  const circle = document.getElementById('scoreCircle');
  document.getElementById('scoreValue').textContent = data.overall_score + '%';
  circle.className = 'score-circle mx-auto mb-3';
  circle.classList.add(data.risk_level.toLowerCase());

  // Risk badge
  const riskBadge = document.getElementById('riskBadge');
  riskBadge.textContent = `${data.risk_level} Risk`;
  riskBadge.className = `badge fs-6 px-3 py-2 bg-${data.risk_class}`;

  // Stats
  document.getElementById('wordCount').textContent = data.word_count;
  document.getElementById('sourcesChecked').textContent = data.sources_checked;

  // Top matches table
  const tbody = document.getElementById('matchesBody');
  tbody.innerHTML = '';
  (data.top_matches || []).forEach(match => {
    const pct = (match.percentage || 0).toFixed(1);
    const barClass = pct >= 70 ? 'bg-danger' : pct >= 40 ? 'bg-warning' : 'bg-success';
    tbody.innerHTML += `
      <tr>
        <td class="small">${match.source}</td>
        <td style="width:120px">
          <div class="d-flex align-items-center gap-2">
            <div class="flex-grow-1 bg-light rounded" style="height:6px">
              <div class="${barClass} rounded sim-bar" style="width:${pct}%"></div>
            </div>
            <small>${pct}%</small>
          </div>
        </td>
      </tr>`;
  });

  // Matching phrases
  const phrasesBody = document.getElementById('phrasesBody');
  if (data.matching_phrases && data.matching_phrases.length > 0) {
    phrasesBody.innerHTML = data.matching_phrases.map(p => `<span class="phrase-badge">${p}</span>`).join('');
    document.getElementById('phrasesCard').classList.remove('d-none');
  } else {
    document.getElementById('phrasesCard').classList.add('d-none');
  }

  document.getElementById('plagResults').classList.remove('d-none');
}