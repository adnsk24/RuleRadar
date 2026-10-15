// RuleRadar AI - Semantic Document Comparison Controller
const compareHandler = {
  currentReport: null,

  init() {
    this.loadDocOptions();
  },

  async loadDocOptions() {
    try {
      const res = await fetch('/api/documents');
      if (!res.ok) return;
      const data = await res.json();
      const docs = data.documents || [];

      const selectA = document.getElementById('compare-select-a');
      const selectB = document.getElementById('compare-select-b');

      if (!selectA || !selectB) return;

      const optionsHtml = '<option value="">Select Document...</option>' + 
        docs.map(d => `<option value="${d.id}">${this.escapeHtml(d.filename)} (${d.category})</option>`).join('');

      selectA.innerHTML = optionsHtml;
      selectB.innerHTML = optionsHtml;

      // Auto-select if at least 2 documents exist
      if (docs.length >= 2) {
        selectA.selectedIndex = 1;
        selectB.selectedIndex = 2;
      }
    } catch (err) {
      console.error('Error loading compare options:', err);
    }
  },

  async runComparison() {
    const docAId = document.getElementById('compare-select-a').value;
    const docBId = document.getElementById('compare-select-b').value;

    if (!docAId || !docBId) {
      app.toast('Please select both Document A and Document B to compare.', 'error');
      return;
    }

    if (docAId === docBId) {
      app.toast('Document A and Document B are identical. Select two different document versions.', 'error');
      return;
    }

    const btn = document.getElementById('btn-run-comparison');
    btn.disabled = true;
    btn.textContent = 'Comparing...';

    try {
      const res = await fetch('/api/compare', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ doc_a_id: docAId, doc_b_id: docBId })
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Comparison request failed');

      this.currentReport = data.comparison;
      this.renderReport(data.comparison, data.doc_a, data.doc_b);
      app.toast('Semantic comparison completed successfully.', 'success');
    } catch (err) {
      app.toast('Comparison failed: ' + err.message, 'error');
    } finally {
      btn.disabled = false;
      btn.textContent = 'Run Comparison';
    }
  },

  renderReport(report, docA, docB) {
    document.getElementById('compare-results-area').style.display = 'block';

    // Counts
    const counts = report.counts || {};
    document.getElementById('comp-modified-count').textContent = counts.modified || 0;
    document.getElementById('comp-added-count').textContent = counts.added || 0;
    document.getElementById('comp-removed-count').textContent = counts.removed || 0;
    document.getElementById('comp-identical-count').textContent = counts.identical || 0;

    document.getElementById('comp-summary-text').textContent = report.summary || 'Comparison complete.';

    // Render Modified
    const modContainer = document.getElementById('comp-modified-list');
    const modified = report.modified_clauses || [];

    if (modified.length === 0) {
      modContainer.innerHTML = '<p style="color:var(--text-muted); font-size:0.8125rem;">No substantive modifications detected between matched provisions.</p>';
    } else {
      modContainer.innerHTML = modified.map((m, idx) => {
        const changesList = [];
        (m.changed_financials || []).forEach(f => {
          changesList.push(`<b>Financial Adjustment:</b> ${f.previous_value} ➔ <b style="color:var(--primary);">${f.new_value}</b>`);
        });
        (m.changed_deadlines || []).forEach(d => {
          changesList.push(`<b>Deadline Shift:</b> ${d.previous_value} ➔ <b style="color:var(--risk-med-text);">${d.new_value}</b>`);
        });
        if (m.obligation_shift) {
          changesList.push(`<b>Obligation Shift:</b> ${m.obligation_shift}`);
        }

        return `
          <div style="border:1px solid var(--border-color); border-radius:var(--radius-sm); padding:0.85rem; margin-bottom:0.75rem; background:var(--bg-surface);">
            <div style="display:flex; justify-content:space-between; margin-bottom:0.4rem; align-items:center;">
              <div>
                <b>Modified Provision #${idx + 1}:</b> 
                <span class="badge badge-category">${this.escapeHtml(m.clause_b?.heading || 'Section')}</span>
              </div>
              <span class="badge badge-review">Similarity: ${(m.similarity * 100).toFixed(0)}%</span>
            </div>

            <p style="font-size:0.8125rem; color:var(--text-secondary); margin-bottom:0.45rem;">
              <b>Detected Shift:</b> ${this.escapeHtml(m.explanation)}
            </p>

            ${changesList.length > 0 ? `
              <div style="background:var(--bg-surface-subtle); padding:0.45rem 0.65rem; border-radius:var(--radius-xs); border:1px solid var(--border-color); font-size:0.775rem; margin-bottom:0.6rem;">
                ${changesList.join('<br/>')}
              </div>
            ` : ''}

            <!-- Side by Side Diff -->
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:0.5rem; font-size:0.8125rem; margin-top:0.4rem;">
              <div style="border:1px solid #FECDCA; padding:0.5rem; border-radius:var(--radius-xs); background:#FEF3F2;">
                <div style="font-size:0.7rem; font-weight:600; color:#912018; margin-bottom:0.2rem; text-transform:uppercase;">Previous (Document A)</div>
                <div style="line-height:1.4;">${m.diff_html_previous || this.escapeHtml(m.clause_a?.original_text || '')}</div>
              </div>

              <div style="border:1px solid #A6F4C5; padding:0.5rem; border-radius:var(--radius-xs); background:#ECFDF3;">
                <div style="font-size:0.7rem; font-weight:600; color:#027A48; margin-bottom:0.2rem; text-transform:uppercase;">Current (Document B)</div>
                <div style="line-height:1.4;">${m.diff_html_current || this.escapeHtml(m.clause_b?.original_text || '')}</div>
              </div>
            </div>
          </div>
        `;
      }).join('');
    }

    // Render Added
    const addedContainer = document.getElementById('comp-added-list');
    const added = report.added_clauses || [];
    if (added.length === 0) {
      addedContainer.innerHTML = '<p style="color:var(--text-muted); font-size:0.8125rem;">No new clauses added.</p>';
    } else {
      addedContainer.innerHTML = added.map(a => `
        <div style="border-left:3px solid var(--success-text); padding:0.5rem 0.75rem; margin-bottom:0.5rem; background:#ECFDF3; border-radius:var(--radius-xs);">
          <div style="font-weight:600; font-size:0.8125rem; color:#027A48;">
            ${this.escapeHtml(a.clause?.clause_number || '')} ${this.escapeHtml(a.clause?.heading || 'New Provision')}
          </div>
          <div style="font-size:0.775rem; margin:0.25rem 0; color:var(--text-secondary); line-height:1.4;">
            ${this.escapeHtml(a.clause?.original_text || '')}
          </div>
          <div style="font-size:0.725rem; color:var(--text-muted); font-style:italic;">${this.escapeHtml(a.reason)}</div>
        </div>
      `).join('');
    }

    // Render Removed
    const removedContainer = document.getElementById('comp-removed-list');
    const removed = report.removed_clauses || [];
    if (removed.length === 0) {
      removedContainer.innerHTML = '<p style="color:var(--text-muted); font-size:0.8125rem;">No clauses removed.</p>';
    } else {
      removedContainer.innerHTML = removed.map(r => `
        <div style="border-left:3px solid var(--risk-high-text); padding:0.5rem 0.75rem; margin-bottom:0.5rem; background:#FEF3F2; border-radius:var(--radius-xs);">
          <div style="font-weight:600; font-size:0.8125rem; color:#912018;">
            ${this.escapeHtml(r.clause?.clause_number || '')} ${this.escapeHtml(r.clause?.heading || 'Deleted Provision')}
          </div>
          <div style="font-size:0.775rem; margin:0.25rem 0; color:var(--text-secondary); line-height:1.4;">
            ${this.escapeHtml(r.clause?.original_text || '')}
          </div>
          <div style="font-size:0.725rem; color:var(--text-muted); font-style:italic;">${this.escapeHtml(r.reason)}</div>
        </div>
      `).join('');
    }
  },

  escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>"']/g, m => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    })[m]);
  }
};
