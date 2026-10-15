// RuleRadar AI - Two-Panel Document Workspace Controller
const workspace = {
  currentDoc: null,
  currentPageIndex: 0,
  activeTab: 'overview',
  activeHighlightedClauseId: null,

  init() {
    this.populateDocSelector();
  },

  async populateDocSelector() {
    try {
      const res = await fetch('/api/documents');
      if (!res.ok) return;
      const data = await res.json();
      const selector = document.getElementById('workspace-doc-selector');
      if (!selector) return;

      selector.innerHTML = '<option value="">Switch document...</option>' + 
        (data.documents || []).map(d => `<option value="${d.id}">${this.escapeHtml(d.filename)}</option>`).join('');

      if (app.selectedDocumentId) {
        selector.value = app.selectedDocumentId;
      }
    } catch (err) {
      console.error('Error populating doc selector:', err);
    }
  },

  async switchDocument(docId) {
    if (!docId) return;
    app.selectedDocumentId = docId;
    await this.loadDocument(docId);
  },

  async loadDocumentAndHighlight(docId, clauseId, pageNum = 1) {
    app.selectedDocumentId = docId;
    app.navigate('workspace');
    await this.loadDocument(docId);
    this.switchTab('risks');
    setTimeout(() => {
      this.scrollToClauseInDoc(clauseId, pageNum);
    }, 300);
  },

  async loadDocument(docId) {
    if (!docId) return;
    try {
      const res = await fetch(`/api/documents/${docId}`);
      if (!res.ok) throw new Error('Failed to load document analysis');
      this.currentDoc = await res.json();
      this.currentPageIndex = 0;

      // Update Header
      document.getElementById('workspace-doc-title').textContent = this.currentDoc.filename || 'Document';
      const catBadge = document.getElementById('workspace-category-badge');
      catBadge.textContent = (this.currentDoc.category || 'General').toUpperCase();
      
      const scanAlert = document.getElementById('workspace-scanned-alert');
      if (this.currentDoc.scanned_warning) {
        scanAlert.style.display = 'inline-flex';
      } else {
        scanAlert.style.display = 'none';
      }

      const selector = document.getElementById('workspace-doc-selector');
      if (selector) {
        if (selector.options.length <= 1) {
          await this.populateDocSelector();
        }
        selector.value = docId;
      }

      // Update Overview Tab
      document.getElementById('workspace-summary-text').textContent = this.currentDoc.summary || 'Summary unavailable.';
      document.getElementById('meta-page-count').textContent = this.currentDoc.page_count || 1;
      document.getElementById('meta-file-size').textContent = `${(this.currentDoc.file_size / 1024).toFixed(1)} KB`;

      // Update Counts in tab headers
      document.getElementById('count-clauses').textContent = (this.currentDoc.clauses || []).length;
      document.getElementById('count-risks').textContent = (this.currentDoc.risk_findings || []).length;

      // Render Entities chips
      this.renderEntities();

      // Render Categories Filter in Clauses tab
      this.populateCategoryFilter();

      // Render Viewers
      this.renderPage();
      this.renderClauses();
      this.renderRisks();
      this.renderObligations();
      
      // Load QA History
      qaHandler.loadHistory(docId);

    } catch (err) {
      app.toast('Failed to load workspace document: ' + err.message, 'error');
    }
  },

  renderEntities() {
    const container = document.getElementById('entities-tags-list');
    const entities = this.currentDoc.entities || [];
    if (entities.length === 0) {
      container.innerHTML = '<span style="color:var(--text-muted); font-size:0.85rem;">No distinct entities identified.</span>';
      return;
    }
    const unique = Array.from(new Set(entities.map(e => `${e.entity_type}: ${e.entity_text}`)));
    container.innerHTML = unique.slice(0, 15).map(item => `
      <span class="badge badge-category" style="font-size:0.75rem;">${this.escapeHtml(item)}</span>
    `).join('');
  },

  populateCategoryFilter() {
    const filter = document.getElementById('filter-clause-category');
    if (!filter) return;
    const cats = Array.from(new Set((this.currentDoc.clauses || []).map(c => c.category).filter(Boolean)));
    filter.innerHTML = '<option value="all">All Categories</option>' + 
      cats.map(c => `<option value="${this.escapeHtml(c)}">${this.escapeHtml(c)}</option>`).join('');
  },

  renderPage() {
    const pages = this.currentDoc?.pages || [];
    if (pages.length === 0) {
      document.getElementById('doc-page-content').innerHTML = '<em>No page content available.</em>';
      return;
    }

    const currentPg = pages[this.currentPageIndex] || pages[0];
    const pageNum = currentPg.page_number;
    document.getElementById('page-indicator').textContent = `Page ${pageNum} of ${pages.length}`;

    // Get clauses belonging to this page
    const pageClauses = (this.currentDoc.clauses || []).filter(c => 
      c.page_start <= pageNum && c.page_end >= pageNum
    );

    const viewer = document.getElementById('doc-page-content');

    if (pageClauses.length > 0) {
      viewer.innerHTML = pageClauses.map(c => {
        const isSelected = this.activeHighlightedClauseId === c.id;
        const hasRisk = (this.currentDoc.risk_findings || []).some(r => r.clause_id === c.id);
        const riskIndicator = hasRisk ? 'border-left-color: #EF4444; background-color: rgba(254, 226, 226, 0.4);' : '';
        
        return `
          <div class="clause-highlight ${isSelected ? 'selected' : ''}" 
               id="doc-clause-${c.id}" 
               style="${riskIndicator}"
               onclick="workspace.selectClause('${c.id}')"
               title="${this.escapeHtml(c.heading || 'Clause')} [${c.category}]">
            <div style="font-size:0.75rem; font-weight:700; color:var(--text-muted); margin-bottom:0.2rem;">
              ${this.escapeHtml(c.clause_number || '')} ${this.escapeHtml(c.heading || '')}
              <span class="badge badge-category" style="margin-left:0.4rem;">${c.category}</span>
            </div>
            <div>${this.escapeHtml(c.original_text)}</div>
          </div>
        `;
      }).join('');
    } else {
      viewer.textContent = currentPg.text || '';
    }
  },

  prevPage() {
    if (this.currentPageIndex > 0) {
      this.currentPageIndex--;
      this.renderPage();
    }
  },

  nextPage() {
    const pages = this.currentDoc?.pages || [];
    if (this.currentPageIndex < pages.length - 1) {
      this.currentPageIndex++;
      this.renderPage();
    }
  },

  switchTab(tabName) {
    this.activeTab = tabName;
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

    const targetBtn = document.getElementById(`tab-btn-${tabName}`);
    const targetContent = document.getElementById(`tab-${tabName}`);
    if (targetBtn) targetBtn.classList.add('active');
    if (targetContent) targetContent.classList.add('active');
  },

  selectClause(clauseId) {
    this.activeHighlightedClauseId = clauseId;
    document.querySelectorAll('.clause-highlight').forEach(el => el.classList.remove('selected'));
    
    const targetInText = document.getElementById(`doc-clause-${clauseId}`);
    if (targetInText) {
      targetInText.classList.add('selected');
      targetInText.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    // If on clauses or risks tab, scroll to corresponding card
    const card = document.getElementById(`clause-card-${clauseId}`) || document.getElementById(`risk-card-${clauseId}`);
    if (card) {
      card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      card.style.outline = '2px solid var(--primary)';
      setTimeout(() => card.style.outline = 'none', 1500);
    }
  },

  scrollToClauseInDoc(clauseId, pageStart) {
    if (pageStart && this.currentDoc?.pages) {
      const targetIdx = this.currentDoc.pages.findIndex(p => p.page_number === pageStart);
      if (targetIdx !== -1 && targetIdx !== this.currentPageIndex) {
        this.currentPageIndex = targetIdx;
        this.renderPage();
      }
    }
    setTimeout(() => {
      this.selectClause(clauseId);
    }, 150);
  },

  renderClauses() {
    const container = document.getElementById('clauses-list-container');
    if (!container) return;

    let clauses = this.currentDoc?.clauses || [];
    const catFilter = document.getElementById('filter-clause-category')?.value || 'all';
    const impFilter = document.getElementById('filter-clause-importance')?.value || 'all';

    if (catFilter !== 'all') {
      clauses = clauses.filter(c => c.category === catFilter);
    }
    if (impFilter !== 'all') {
      clauses = clauses.filter(c => c.importance_category === impFilter);
    }

    if (clauses.length === 0) {
      container.innerHTML = '<p style="color:var(--text-muted); font-size:0.85rem; padding:1rem;">No clauses match the selected criteria.</p>';
      return;
    }

    container.innerHTML = clauses.map(c => {
      const impBadge = c.importance_category === 'High' ? 'badge-high' : (c.importance_category === 'Medium' ? 'badge-review' : 'badge-info');

      return `
        <div class="finding-card" id="clause-card-${c.id}">
          <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:0.4rem; gap:0.5rem;">
            <div>
              <span style="font-weight:600; font-size:0.85rem; color:var(--text-primary);">${this.escapeHtml(c.clause_number || '')} ${this.escapeHtml(c.heading || 'Section')}</span>
              <span class="badge badge-category" style="margin-left:0.35rem;">Page ${c.page_start}</span>
            </div>
            <div style="display:flex; gap:0.35rem;">
              <span class="badge badge-category">${this.escapeHtml(c.category)}</span>
              <span class="badge ${impBadge}">${c.importance_score}/10 ${c.importance_category}</span>
            </div>
          </div>
          
          <div style="font-size:0.8125rem; color:var(--text-secondary); line-height:1.45; margin-bottom:0.4rem;">
            ${this.escapeHtml((c.original_text || '').slice(0, 160))}${(c.original_text || '').length > 160 ? '...' : ''}
          </div>

          <details style="margin-bottom:0.4rem; font-size:0.78rem; color:var(--text-muted); cursor:pointer;">
            <summary style="font-weight:500; color:var(--primary); margin-bottom:0.3rem;">Expand full clause text & diagnostics</summary>
            <div style="background:var(--bg-surface-subtle); padding:0.6rem; border-radius:var(--radius-xs); border:1px solid var(--border-color); white-space:pre-wrap; line-height:1.4; color:var(--text-primary); margin-bottom:0.4rem;">
              ${this.escapeHtml(c.original_text)}
            </div>
            <div><b>Scoring Factors:</b> ${this.escapeHtml(c.importance_explanation || 'Standard contractual structure.')}</div>
            <div style="margin-top:2px;"><b>Model Confidence:</b> ${((c.classification_confidence || 0.85) * 100).toFixed(0)}%</div>
          </details>

          <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid var(--border-color); padding-top:0.4rem;">
            <button class="btn btn-secondary btn-sm" onclick="workspace.scrollToClauseInDoc('${c.id}', ${c.page_start})">
              Jump to Source
            </button>
            <button class="btn btn-subtle btn-sm" onclick="workspace.toggleClauseReview('${c.id}')">
              ${c.is_reviewed ? 'Reviewed' : 'Mark Reviewed'}
            </button>
          </div>
        </div>
      `;
    }).join('');
  },

  renderRisks() {
    const container = document.getElementById('risks-list-container');
    if (!container) return;

    let risks = this.currentDoc?.risk_findings || [];
    const levelFilter = document.getElementById('filter-risk-level')?.value || 'all';

    if (levelFilter !== 'all') {
      risks = risks.filter(r => r.risk_level === levelFilter);
    }

    if (risks.length === 0) {
      container.innerHTML = `
        <div style="text-align:center; padding:2rem; color:var(--text-muted);">
          <div style="font-weight:600; font-size:0.875rem; color:var(--text-primary);">No risk indicators flagged under this filter</div>
          <p style="font-size:0.775rem; margin-top:0.25rem;">Provisions satisfied standard checks or limiting exceptions were recognized.</p>
        </div>
      `;
      return;
    }

    container.innerHTML = risks.map(r => {
      const cardClass = r.risk_level === 'High attention' ? 'risk-high' : (r.risk_level === 'Needs review' ? 'risk-review' : 'risk-info');
      const badgeClass = r.risk_level === 'High attention' ? 'badge-high' : (r.risk_level === 'Needs review' ? 'badge-review' : 'badge-info');

      return `
        <div class="finding-card ${cardClass}" id="risk-card-${r.clause_id || r.id}">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.35rem;">
            <span style="font-weight:600; font-size:0.85rem; color:var(--text-primary);">${this.escapeHtml(r.rule_name)}</span>
            <span class="badge ${badgeClass}">${r.risk_level}</span>
          </div>

          <p style="font-size:0.8125rem; color:var(--text-secondary); margin-bottom:0.35rem; line-height:1.4;">
            ${this.escapeHtml(r.explanation)}
          </p>

          <div class="finding-quote">
            "${this.escapeHtml(r.evidence_quote)}"
          </div>

          <div class="finding-action-box">
            <b>Suggested Question:</b> ${this.escapeHtml(r.suggested_question)}
          </div>

          ${r.uncertainty_note ? `<div style="font-size:0.75rem; color:var(--text-muted); margin-top:0.35rem;"><b>Note:</b> ${this.escapeHtml(r.uncertainty_note)}</div>` : ''}
          ${r.related_clause_context ? `<div style="font-size:0.75rem; color:var(--text-muted); margin-top:2px;"><b>Related Context:</b> ${this.escapeHtml(r.related_clause_context)}</div>` : ''}

          <div style="display:flex; justify-content:space-between; align-items:center; margin-top:0.6rem; border-top:1px solid rgba(0,0,0,0.06); padding-top:0.4rem;">
            <button class="btn btn-secondary btn-sm" onclick="workspace.scrollToClauseInDoc('${r.clause_id}', 1)">
              Jump to Source
            </button>
            <button class="btn btn-subtle btn-sm" onclick="workspace.toggleRiskReview('${r.id}')">
              ${r.is_reviewed ? 'Reviewed' : 'Mark Reviewed'}
            </button>
          </div>
        </div>
      `;
    }).join('');
  },

  renderObligations() {
    const dlContainer = document.getElementById('deadlines-list-container');
    const obContainer = document.getElementById('obligations-list-container');
    const deadlines = this.currentDoc?.deadlines || [];
    const obligations = this.currentDoc?.obligations || [];

    if (deadlines.length === 0) {
      dlContainer.innerHTML = '<p style="color:var(--text-muted); font-size:0.85rem;">No strict calendar deadlines extracted.</p>';
    } else {
      dlContainer.innerHTML = deadlines.map(d => `
        <div style="border:1px solid var(--border-color); padding:0.6rem 0.85rem; border-radius:var(--radius-sm); margin-bottom:0.5rem; background:var(--bg-surface);">
          <div style="display:flex; justify-content:space-between; font-weight:600; font-size:0.85rem;">
            <span style="color:var(--primary);">${this.escapeHtml(d.date_or_period)}</span>
            <span class="badge badge-category">Page ${d.page_number}</span>
          </div>
          <div style="font-size:0.775rem; color:var(--text-muted); margin-top:0.25rem;">
            <b>Type:</b> ${this.escapeHtml(d.deadline_type)} • <i>${this.escapeHtml(d.context)}</i>
          </div>
        </div>
      `).join('');
    }

    if (obligations.length === 0) {
      obContainer.innerHTML = '<p style="color:var(--text-muted); font-size:0.85rem;">No itemized obligations detected.</p>';
    } else {
      obContainer.innerHTML = obligations.map(o => `
        <div style="border:1px solid var(--border-color); padding:0.75rem; border-radius:var(--radius-sm); margin-bottom:0.6rem; background:var(--bg-surface);">
          <div style="display:flex; justify-content:space-between; margin-bottom:0.25rem;">
            <span style="font-weight:700; font-size:0.85rem; color:var(--text-primary);">${this.escapeHtml(o.responsible_party)}</span>
            ${o.deadline ? `<span class="badge badge-review" style="font-size:0.7rem;">${this.escapeHtml(o.deadline)}</span>` : ''}
          </div>
          <div style="font-size:0.85rem; color:var(--text-secondary); line-height:1.4;">
            ${this.escapeHtml(o.required_action)}
          </div>
          ${o.trigger_condition ? `<div style="font-size:0.75rem; color:var(--text-muted); margin-top:0.3rem;"><b>Condition:</b> ${this.escapeHtml(o.trigger_condition)}</div>` : ''}
        </div>
      `).join('');
    }
  },

  async toggleClauseReview(clauseId) {
    try {
      const res = await fetch(`/api/analysis/clauses/${clauseId}/review`, { method: 'POST' });
      const data = await res.json();
      const clause = (this.currentDoc.clauses || []).find(c => c.id === clauseId);
      if (clause) clause.is_reviewed = data.is_reviewed;
      this.renderClauses();
      app.toast('Clause review status updated', 'success');
    } catch (err) {
      app.toast('Failed to update review status', 'error');
    }
  },

  async toggleRiskReview(riskId) {
    try {
      const res = await fetch(`/api/analysis/risks/${riskId}/review`, { method: 'POST' });
      const data = await res.json();
      const risk = (this.currentDoc.risk_findings || []).find(r => r.id === riskId);
      if (risk) risk.is_reviewed = data.is_reviewed;
      this.renderRisks();
      app.toast('Risk review status updated', 'success');
    } catch (err) {
      app.toast('Failed to update risk review status', 'error');
    }
  },

  searchInDocument(term) {
    const cleanTerm = term.trim().toLowerCase();
    if (!cleanTerm) {
      this.renderPage();
      return;
    }

    // Highlight text occurrences on current page
    const viewer = document.getElementById('doc-page-content');
    const highlights = viewer.querySelectorAll('.clause-highlight');

    highlights.forEach(el => {
      const text = el.textContent.toLowerCase();
      if (text.includes(cleanTerm)) {
        el.style.backgroundColor = '#FEF08A';
      } else {
        el.style.backgroundColor = '';
      }
    });
  },

  exportReport(format) {
    if (!this.currentDoc) {
      app.toast('Please select a document first', 'error');
      return;
    }
    window.open(`/api/export/${this.currentDoc.id}/${format}`, '_blank');
  },

  escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>"']/g, m => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    })[m]);
  }
};
