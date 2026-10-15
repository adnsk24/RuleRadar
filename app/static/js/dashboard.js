// RuleRadar AI - Dashboard & Repository Controller
const dashboard = {
  documentsList: [],
  fullDocumentsList: [],

  init() {
    this.refresh();
  },

  async refresh() {
    await Promise.all([
      this.loadStats(),
      this.loadDocuments(),
      this.loadReviewQueue(),
      this.loadActivities('activity-feed-container', 8),
      this.loadFullDocuments()
    ]);
  },

  async loadStats() {
    try {
      const res = await fetch('/api/system/stats');
      if (!res.ok) throw new Error('Failed to fetch statistics');
      const data = await res.json();

      const totalDocsEl = document.getElementById('stat-total-docs');
      if (totalDocsEl) totalDocsEl.textContent = data.total_documents || 0;

      const clausesEl = document.getElementById('stat-clauses-identified') || document.getElementById('stat-important-clauses');
      if (clausesEl) clausesEl.textContent = (data.clauses_identified !== undefined) ? data.clauses_identified : (data.important_clauses || 0);

      const reviewEl = document.getElementById('stat-review-queue') || document.getElementById('stat-risk-findings');
      if (reviewEl) reviewEl.textContent = (data.findings_requiring_review !== undefined) ? data.findings_requiring_review : (data.risk_findings || 0);

      const compEl = document.getElementById('stat-comparisons-completed') || document.getElementById('stat-comparisons');
      if (compEl) compEl.textContent = (data.comparisons_completed !== undefined) ? data.comparisons_completed : (data.total_comparisons || 0);
    } catch (err) {
      console.error('Stats error:', err);
    }
  },

  async loadDocuments() {
    const tbody = document.getElementById('documents-table-body');
    if (!tbody) return;

    try {
      const res = await fetch('/api/documents');
      if (!res.ok) throw new Error('Failed to fetch documents');
      const data = await res.json();
      this.documentsList = data.documents || [];

      if (this.documentsList.length === 0) {
        tbody.innerHTML = `
          <tr>
            <td colspan="6" style="text-align:center; padding: 2.5rem 1rem;">
              <div style="font-weight: 600; font-size: 0.95rem; color: var(--text-primary); margin-bottom: 0.25rem;">
                No documents in repository
              </div>
              <p style="font-size: 0.8125rem; color: var(--text-muted); margin-bottom: 1rem;">
                Upload a rental agreement, employment contract, or corporate policy to generate intelligence.
              </p>
              <button class="btn btn-primary btn-sm" onclick="uploadHandler.openModal()">
                + Upload Document
              </button>
            </td>
          </tr>
        `;
        return;
      }

      this.renderRecentTable(this.documentsList);
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:var(--error-text);">Error loading documents: ${err.message}</td></tr>`;
    }
  },

  renderRecentTable(docs) {
    const tbody = document.getElementById('documents-table-body');
    if (!tbody) return;

    tbody.innerHTML = docs.slice(0, 10).map(d => {
      const dateStr = d.created_at ? new Date(d.created_at).toLocaleDateString() : '-';
      const catLabel = (d.category || 'general').replace('_', ' ');

      return `
        <tr>
          <td style="max-width:190px;">
            <div style="font-weight:600; color:var(--text-primary); cursor:pointer; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${this.escapeHtml(d.filename)}" onclick="dashboard.openDocument('${d.id}')">
              ${this.escapeHtml(d.filename)}
            </div>
            <div style="font-size:0.725rem; color:var(--text-muted);">
              ${(d.file_size / 1024).toFixed(1)} KB • ${d.page_count} pg
            </div>
          </td>
          <td><span class="badge badge-category">${catLabel.toUpperCase()}</span></td>
          <td style="font-size:0.775rem; color:var(--text-secondary); white-space:nowrap;">${dateStr}</td>
          <td style="text-align:center;"><span style="font-weight:600;">${d.clause_count}</span></td>
          <td style="white-space:nowrap;">
            ${d.risk_count > 0 
              ? `<span class="badge badge-high">${d.risk_count} Flags</span>` 
              : `<span class="badge badge-success">Clean</span>`}
            ${d.scanned_warning ? '<span class="badge badge-review" style="margin-left:0.25rem;" title="Low extractable text detected; may be scanned">Low-Text</span>' : ''}
          </td>
          <td style="white-space:nowrap;">
            <div style="display:flex; gap:0.25rem;">
              <button class="btn btn-subtle btn-sm" onclick="dashboard.openDocument('${d.id}')" title="Inspect Document Analysis">
                Inspect
              </button>
              <a href="/api/export/${d.id}/pdf" class="btn btn-secondary btn-sm" title="Download PDF Report" target="_blank">
                PDF
              </a>
              <button class="btn btn-danger-outline btn-sm" onclick="dashboard.deleteDocument('${d.id}', '${this.escapeHtml(d.filename)}')" title="Delete Document">
                Delete
              </button>
            </div>
          </td>
        </tr>
      `;
    }).join('');
  },

  async loadReviewQueue() {
    const container = document.getElementById('review-queue-container');
    if (!container) return;

    try {
      const res = await fetch('/api/analysis/review-queue?limit=5');
      if (!res.ok) throw new Error('Failed to load review queue');
      const data = await res.json();
      const findings = data.findings || [];

      if (findings.length === 0) {
        container.innerHTML = `
          <div style="text-align:center; padding:1.75rem 1rem; color:var(--text-muted);">
            <div style="font-weight:600; font-size:0.875rem; color:var(--text-primary); margin-bottom:0.25rem;">
              Review Queue Clear
            </div>
            <p style="font-size:0.775rem;">
              No unreviewed risk findings. All provisions have been evaluated or satisfied standard terms.
            </p>
          </div>
        `;
        return;
      }

      container.innerHTML = findings.map(item => {
        const priorityBadge = item.risk_level === 'High attention' 
          ? '<span class="badge badge-high">High Attention</span>'
          : '<span class="badge badge-review">Needs Review</span>';

        return `
          <div class="review-queue-item">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:0.35rem;">
              <div>
                <b style="color:var(--text-primary); font-size:0.8125rem;">${this.escapeHtml(item.document_filename)}</b>
                <span class="badge badge-category" style="margin-left:0.35rem;">${this.escapeHtml(item.category || item.rule_name)}</span>
              </div>
              <div>${priorityBadge}</div>
            </div>

            <div style="font-size:0.8rem; color:var(--text-secondary); line-height:1.4; margin-bottom:0.35rem;">
              ${this.escapeHtml(item.explanation)}
            </div>

            <div class="finding-quote" style="margin:0.35rem 0; font-size:0.775rem;">
              "${this.escapeHtml(item.evidence_quote)}"
            </div>

            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:0.5rem; font-size:0.75rem;">
              <span style="color:var(--text-muted);">
                Page ${item.page_start} • Section ${this.escapeHtml(item.clause_number || '')}
              </span>
              <div style="display:flex; gap:0.4rem;">
                <button class="btn btn-secondary btn-sm" onclick="workspace.loadDocumentAndHighlight('${item.document_id}', '${item.clause_id}', ${item.page_start})">
                  Inspect Clause
                </button>
                <button class="btn btn-subtle btn-sm" onclick="dashboard.markFindingReviewed('${item.id}')">
                  Mark Reviewed
                </button>
              </div>
            </div>
          </div>
        `;
      }).join('');
    } catch (err) {
      container.innerHTML = `<div style="text-align:center; padding:1rem; color:var(--error-text); font-size:0.8rem;">Error loading review queue: ${err.message}</div>`;
    }
  },

  async markFindingReviewed(findingId) {
    try {
      const res = await fetch(`/api/analysis/risks/${findingId}/review`, { method: 'POST' });
      if (!res.ok) throw new Error('Failed to update review status');
      app.toast('Finding marked as reviewed', 'success');
      this.loadReviewQueue();
      this.loadStats();
    } catch (err) {
      app.toast('Failed to update finding: ' + err.message, 'error');
    }
  },

  async loadActivities(containerId = 'activity-feed-container', limit = 10) {
    const container = document.getElementById(containerId);
    if (!container) return;

    try {
      const res = await fetch(`/api/system/activity?limit=${limit}`);
      if (!res.ok) throw new Error('Failed to fetch activity records');
      const data = await res.json();
      const activities = data.activities || [];

      if (activities.length === 0) {
        container.innerHTML = `
          <div style="text-align:center; padding:1.5rem; color:var(--text-muted); font-size:0.775rem;">
            No repository activity recorded yet. Ingest an agreement to record events.
          </div>
        `;
        return;
      }

      container.innerHTML = activities.map(act => {
        const timeStr = this.formatRelativeTime(act.timestamp);
        let iconSvg = '';

        if (act.type === 'document_uploaded' || act.type === 'analysis_completed') {
          iconSvg = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline></svg>';
        } else if (act.type === 'comparison_completed') {
          iconSvg = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="16 3 21 3 21 8"></polyline><line x1="4" y1="20" x2="21" y2="3"></line></svg>';
        } else if (act.type === 'qa_query') {
          iconSvg = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"></circle><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>';
        } else {
          iconSvg = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path></svg>';
        }

        return `
          <div class="activity-feed-item">
            <div class="activity-icon-bullet">
              ${iconSvg}
            </div>
            <div style="flex:1;">
              <div style="font-weight:600; font-size:0.8125rem; color:var(--text-primary);">
                ${this.escapeHtml(act.title)}
              </div>
              <div style="font-size:0.75rem; color:var(--text-secondary); margin-top:2px; line-height:1.35;">
                ${this.escapeHtml(act.description)}
              </div>
              <div style="font-size:0.6875rem; color:var(--text-muted); margin-top:3px;">
                ${timeStr}
              </div>
            </div>
          </div>
        `;
      }).join('');
    } catch (err) {
      container.innerHTML = `<div style="text-align:center; padding:1rem; color:var(--error-text); font-size:0.775rem;">Error: ${err.message}</div>`;
    }
  },

  async loadFullDocuments() {
    const tbody = document.getElementById('full-documents-table-body');
    if (!tbody) return;

    try {
      const res = await fetch('/api/documents');
      if (!res.ok) throw new Error('Failed to load documents');
      const data = await res.json();
      this.fullDocumentsList = data.documents || [];

      if (this.fullDocumentsList.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; padding:2rem; color:var(--text-muted);">No documents found in repository.</td></tr>';
        return;
      }

      this.renderFullTable(this.fullDocumentsList);
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; color:var(--error-text);">Error loading repository: ${err.message}</td></tr>`;
    }
  },

  renderFullTable(docs) {
    const tbody = document.getElementById('full-documents-table-body');
    if (!tbody) return;

    tbody.innerHTML = docs.map(d => {
      const dateStr = d.created_at ? new Date(d.created_at).toLocaleDateString() : '-';
      const catLabel = (d.category || 'general').replace('_', ' ');

      return `
        <tr>
          <td>
            <div style="font-weight:600; color:var(--text-primary); cursor:pointer;" onclick="dashboard.openDocument('${d.id}')">
              ${this.escapeHtml(d.filename)}
            </div>
            <div style="font-size:0.725rem; color:var(--text-muted);">${(d.file_size / 1024).toFixed(1)} KB</div>
          </td>
          <td><span class="badge badge-category">${catLabel.toUpperCase()}</span></td>
          <td>${d.page_count}</td>
          <td><b>${d.clause_count}</b></td>
          <td>
            <span class="badge ${d.risk_count > 0 ? 'badge-high' : 'badge-success'}">
              ${d.risk_count} ${d.risk_count > 0 ? 'Flags' : 'Clean'}
            </span>
          </td>
          <td><b>${d.deadline_count}</b></td>
          <td style="font-size:0.775rem; color:var(--text-secondary);">${dateStr}</td>
          <td>
            <div style="display:flex; gap:0.35rem;">
              <button class="btn btn-subtle btn-sm" onclick="dashboard.openDocument('${d.id}')">Inspect</button>
              <a href="/api/export/${d.id}/pdf" class="btn btn-secondary btn-sm" target="_blank">PDF</a>
              <button class="btn btn-danger-outline btn-sm" onclick="dashboard.deleteDocument('${d.id}', '${this.escapeHtml(d.filename)}')">Delete</button>
            </div>
          </td>
        </tr>
      `;
    }).join('');
  },

  filterFullTable(term) {
    const clean = (term || '').toLowerCase().trim();
    if (!clean) {
      this.renderFullTable(this.fullDocumentsList);
      return;
    }
    const filtered = this.fullDocumentsList.filter(d =>
      (d.filename && d.filename.toLowerCase().includes(clean)) ||
      (d.category && d.category.toLowerCase().includes(clean))
    );
    this.renderFullTable(filtered);
  },

  openDocument(docId) {
    app.selectedDocumentId = docId;
    app.navigate('workspace');
  },

  async deleteDocument(docId, filename) {
    if (!confirm(`Are you sure you want to permanently delete '${filename}' and all its extracted findings?`)) {
      return;
    }

    try {
      const res = await fetch(`/api/documents/${docId}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Delete request failed');
      app.toast(`Document '${filename}' deleted successfully.`, 'success');
      this.refresh();
      if (app.selectedDocumentId === docId) {
        app.selectedDocumentId = null;
      }
    } catch (err) {
      app.toast('Failed to delete document: ' + err.message, 'error');
    }
  },

  filterTable() {
    const term = document.getElementById('doc-search-input')?.value.toLowerCase().trim() || '';
    if (!term) {
      this.renderRecentTable(this.documentsList);
      return;
    }
    const filtered = this.documentsList.filter(d => 
      (d.filename && d.filename.toLowerCase().includes(term)) ||
      (d.category && d.category.toLowerCase().includes(term))
    );
    this.renderRecentTable(filtered);
  },

  formatRelativeTime(isoStr) {
    if (!isoStr) return '-';
    try {
      const date = new Date(isoStr);
      const now = new Date();
      const diffSecs = Math.floor((now - date) / 1000);
      if (diffSecs < 60) return 'Just now';
      if (diffSecs < 3600) return `${Math.floor(diffSecs / 60)}m ago`;
      if (diffSecs < 86400) return `${Math.floor(diffSecs / 3600)}h ago`;
      return date.toLocaleDateString();
    } catch {
      return isoStr;
    }
  },

  escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>"']/g, m => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    })[m]);
  }
};
