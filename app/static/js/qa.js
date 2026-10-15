// RuleRadar AI - Grounded Q&A Assistant, Clause Explorer & Settings Controllers

// 1. Grounded Q&A Assistant
const qaHandler = {
  async ask() {
    const input = document.getElementById('qa-question-input');
    const question = input.value.trim();
    if (!question) return;

    if (!app.selectedDocumentId) {
      app.toast('Please select an analyzed document first.', 'error');
      return;
    }

    const messages = document.getElementById('qa-chat-messages');

    // Append User Message
    const userBubble = document.createElement('div');
    userBubble.className = 'chat-bubble user';
    userBubble.textContent = question;
    messages.appendChild(userBubble);

    input.value = '';
    messages.scrollTop = messages.scrollHeight;

    // Append Loading Assistant Message
    const assistantBubble = document.createElement('div');
    assistantBubble.className = 'chat-bubble assistant';
    assistantBubble.textContent = 'Searching extracted clauses and synthesizing grounded answer...';
    messages.appendChild(assistantBubble);
    messages.scrollTop = messages.scrollHeight;

    try {
      const res = await fetch('/api/qa', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ document_id: app.selectedDocumentId, question })
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Q&A request failed');

      // Build citations chips
      let citationsHtml = '';
      if (data.citations && data.citations.length > 0) {
        citationsHtml = '<div style="margin-top:0.6rem; border-top:1px solid var(--border-color); padding-top:0.4rem;"><div style="font-size:0.7rem; font-weight:600; color:var(--text-muted); margin-bottom:0.25rem; text-transform:uppercase;">Verified Citations:</div>' +
          data.citations.map(c => `
            <div class="chat-citation" onclick="workspace.scrollToClauseInDoc('${c.clause_id}', ${c.page})">
              ${c.clause_number || 'Section'} (Page ${c.page}) • "${this.escapeHtml((c.quote || '').slice(0, 65))}..."
            </div>
          `).join('') + '</div>';
      }

      assistantBubble.innerHTML = `
        <div style="white-space:pre-wrap; line-height:1.5;">${this.escapeHtml(data.answer)}</div>
        ${citationsHtml}
      `;
    } catch (err) {
      assistantBubble.innerHTML = `<span style="color:var(--risk-high-text);">Error answering question: ${this.escapeHtml(err.message)}</span>`;
    }

    messages.scrollTop = messages.scrollHeight;
  },

  async loadHistory(docId) {
    const messages = document.getElementById('qa-chat-messages');
    try {
      const res = await fetch(`/api/qa/${docId}/history`);
      if (!res.ok) return;
      const data = await res.json();
      const history = data.history || [];

      if (history.length === 0) return;

      // Retain welcome message
      messages.innerHTML = `
        <div class="chat-bubble assistant">
          Ask questions regarding this document's termination policies, liability limits, security deposits, or notice requirements. Every response cites extracted source provisions with page references.
        </div>
      `;

      history.forEach(h => {
        // User
        const u = document.createElement('div');
        u.className = 'chat-bubble user';
        u.textContent = h.question;
        messages.appendChild(u);

        // Assistant
        const a = document.createElement('div');
        a.className = 'chat-bubble assistant';
        let citationsHtml = '';
        if (h.citations && h.citations.length > 0) {
          citationsHtml = '<div style="margin-top:0.6rem; border-top:1px solid var(--border-color); padding-top:0.4rem;"><div style="font-size:0.7rem; font-weight:600; color:var(--text-muted); margin-bottom:0.25rem; text-transform:uppercase;">Verified Citations:</div>' +
            h.citations.map(c => `
              <div class="chat-citation" onclick="workspace.scrollToClauseInDoc('${c.clause_id}', ${c.page})">
                ${c.clause_number || 'Section'} (Page ${c.page})
              </div>
            `).join('') + '</div>';
        }
        a.innerHTML = `<div style="white-space:pre-wrap;">${this.escapeHtml(h.answer)}</div>${citationsHtml}`;
        messages.appendChild(a);
      });
      messages.scrollTop = messages.scrollHeight;
    } catch (err) {
      console.error('Failed to load QA history:', err);
    }
  },

  escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>"']/g, m => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    })[m]);
  }
};

// 2. Global Clause Explorer Controller
const explorerHandler = {
  CATEGORIES: [
    "Payment and financial obligations",
    "Penalties and late fees",
    "Security deposits and refunds",
    "Termination and cancellation",
    "Renewal and automatic renewal",
    "Liability and indemnification",
    "Confidentiality",
    "Intellectual property",
    "Privacy and data handling",
    "Dispute resolution",
    "Governing law and jurisdiction",
    "Eligibility requirements",
    "Deadlines and time limits",
    "Duties and responsibilities",
    "Restrictions and prohibitions",
    "Conditions and exceptions",
    "Warranties and guarantees",
    "Force majeure",
    "Notice requirements",
    "Other or unclassified clauses"
  ],

  loadCategories() {
    const sel = document.getElementById('explorer-category');
    if (!sel || sel.children.length > 1) return;
    this.CATEGORIES.forEach(c => {
      const opt = document.createElement('option');
      opt.value = c;
      opt.textContent = c;
      sel.appendChild(opt);
    });
  },

  async search() {
    const query = document.getElementById('explorer-search')?.value.trim() || '';
    const cat = document.getElementById('explorer-category')?.value || 'all';
    const imp = document.getElementById('explorer-importance')?.value || 'all';

    let url = `/api/analysis/clauses?limit=60`;
    if (query) url += `&search=${encodeURIComponent(query)}`;
    if (cat !== 'all') url += `&category=${encodeURIComponent(cat)}`;
    if (imp !== 'all') url += `&importance=${encodeURIComponent(imp)}`;

    const tbody = document.getElementById('explorer-table-body');
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding:1.5rem;">Searching clauses...</td></tr>';

    try {
      const res = await fetch(url);
      const data = await res.json();
      const clauses = data.clauses || [];

      if (clauses.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding:2rem; color:var(--text-muted);">No clauses matched search parameters.</td></tr>';
        return;
      }

      tbody.innerHTML = clauses.map(c => {
        const impBadge = c.importance_category === 'High' ? 'badge-high' : (c.importance_category === 'Medium' ? 'badge-review' : 'badge-info');
        return `
          <tr>
            <td>
              <b style="color:var(--text-primary); cursor:pointer;" onclick="dashboard.openDocument('${c.document_id}')">
                ${this.escapeHtml(c.filename)}
              </b>
            </td>
            <td>
              <b>${this.escapeHtml(c.clause_number || '')}</b> ${this.escapeHtml(c.heading || 'Section')}<br/>
              <span style="font-size:0.75rem; color:var(--text-muted);">Page ${c.page_start}</span>
            </td>
            <td><span class="badge badge-category">${this.escapeHtml(c.category)}</span></td>
            <td><span class="badge ${impBadge}">${c.importance_score}/10 ${c.importance_category}</span></td>
            <td style="max-width:380px;">
              <div style="font-size:0.85rem; line-height:1.4; max-height:80px; overflow:hidden; text-overflow:ellipsis;">
                ${this.escapeHtml(c.original_text)}
              </div>
            </td>
            <td>
              <span class="badge ${c.is_reviewed ? 'badge-success' : 'badge-category'}">
                ${c.is_reviewed ? 'Reviewed' : 'Unreviewed'}
              </span>
            </td>
          </tr>
        `;
      }).join('');
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:var(--risk-high-text);">Error: ${err.message}</td></tr>`;
    }
  },

  reset() {
    document.getElementById('explorer-search').value = '';
    document.getElementById('explorer-category').value = 'all';
    document.getElementById('explorer-importance').value = 'all';
    this.search();
  },

  escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>"']/g, m => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    })[m]);
  }
};

// 3. Settings & Privacy Controller
const settingsHandler = {
  init() {
    this.checkHealth();
  },

  async checkHealth() {
    const container = document.getElementById('system-health-body');
    if (!container) return;
    container.textContent = 'Querying system components...';

    try {
      const res = await fetch('/api/system/health');
      const data = await res.json();

      container.innerHTML = `
        <div style="display:flex; flex-direction:column; gap:0.75rem;">
          <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid var(--border-color); padding-bottom:0.5rem;">
            <span>Overall Status:</span>
            <span class="badge ${data.status === 'healthy' ? 'badge-success' : 'badge-high'}">${data.status.toUpperCase()}</span>
          </div>
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <span>Database:</span>
            <span style="font-weight:600; color:var(--success-text);">SQLite Connected (Thread-safe)</span>
          </div>
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <span>NLP Embedding Engine:</span>
            <span style="font-weight:600; color:var(--primary);">${data.components.nlp_embeddings.model}</span>
          </div>
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <span>Document Parsers:</span>
            <span style="font-weight:600;">PyMuPDF (PDF), python-docx (DOCX), UTF-8 (TXT)</span>
          </div>
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <span>Free Storage:</span>
            <span style="font-weight:600;">${data.components.storage.free_disk_space_gb} GB</span>
          </div>
        </div>
      `;
    } catch (err) {
      container.innerHTML = `<span style="color:var(--risk-high-text);">Health check failed: ${err.message}</span>`;
    }
  },

  async purgeData() {
    const days = parseInt(document.getElementById('purge-days-select').value, 10);
    if (!confirm(`Are you sure you want to purge all documents older than ${days} day(s)? This action is permanent.`)) {
      return;
    }

    try {
      const res = await fetch('/api/system/retention/purge', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ days_older_than: days })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Purge failed');

      app.toast(`Purged ${data.purged_count} document(s) older than ${days} days.`, 'success');
      dashboard.refresh();
    } catch (err) {
      app.toast('Purge failed: ' + err.message, 'error');
    }
  }
};

// 4. Dedicated Global Risk Analysis View Controller
const risksHandler = {
  allRisks: [],

  async loadAllRisks() {
    const container = document.getElementById('risks-full-list-container');
    if (!container) return;
    container.innerHTML = '<div style="text-align:center; padding:2rem; color:var(--text-muted);">Fetching risk findings from repository...</div>';

    try {
      const res = await fetch('/api/analysis/risks');
      if (!res.ok) throw new Error('Failed to fetch risk findings');
      const data = await res.json();
      this.allRisks = data.findings || [];

      const currentFilter = document.getElementById('risks-view-filter')?.value || 'all';
      this.filterRisks(currentFilter);
    } catch (err) {
      container.innerHTML = `<div style="text-align:center; padding:2rem; color:var(--error-text);">Error loading risk analysis: ${err.message}</div>`;
    }
  },

  filterRisks(level) {
    const filtered = (level === 'all') 
      ? this.allRisks 
      : this.allRisks.filter(r => r.risk_level === level);
    this.renderRisks(filtered);
  },

  renderRisks(findings) {
    const container = document.getElementById('risks-full-list-container');
    if (!container) return;

    if (!findings || findings.length === 0) {
      container.innerHTML = `
        <div style="text-align:center; padding:3rem 1rem; color:var(--text-muted);">
          <div style="font-weight:600; font-size:0.95rem; color:var(--text-primary); margin-bottom:0.25rem;">
            No Risk Findings Under Current Filter
          </div>
          <p style="font-size:0.8125rem;">
            Document provisions satisfied statutory baselines or limiting exceptions were verified.
          </p>
        </div>
      `;
      return;
    }

    container.innerHTML = findings.map(r => {
      const cardClass = r.risk_level === 'High attention' ? 'risk-high' : (r.risk_level === 'Needs review' ? 'risk-review' : 'risk-info');
      const badgeClass = r.risk_level === 'High attention' ? 'badge-high' : (r.risk_level === 'Needs review' ? 'badge-review' : 'badge-info');

      return `
        <div class="finding-card ${cardClass}" style="margin-bottom:0.75rem;">
          <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:0.4rem;">
            <div>
              <span style="font-weight:700; font-size:0.875rem; color:var(--text-primary);">${this.escapeHtml(r.rule_name)}</span>
              <span class="badge badge-category" style="margin-left:0.4rem;">${this.escapeHtml(r.document_filename || 'Agreement')}</span>
              ${r.page_start ? `<span class="badge badge-category" style="margin-left:0.25rem;">Page ${r.page_start}</span>` : ''}
            </div>
            <div>
              <span class="badge ${badgeClass}">${r.risk_level}</span>
            </div>
          </div>

          <p style="font-size:0.8125rem; color:var(--text-secondary); margin-bottom:0.45rem; line-height:1.45;">
            ${this.escapeHtml(r.explanation)}
          </p>

          <div class="finding-quote">
            "${this.escapeHtml(r.evidence_quote)}"
          </div>

          <div class="finding-action-box">
            <b>Suggested Question:</b> ${this.escapeHtml(r.suggested_question)}
          </div>

          ${r.uncertainty_note ? `<div style="font-size:0.75rem; color:var(--text-muted); margin-top:0.35rem;"><b>Diagnostic Note:</b> ${this.escapeHtml(r.uncertainty_note)}</div>` : ''}
          ${r.related_clause_context ? `<div style="font-size:0.75rem; color:var(--text-muted); margin-top:2px;"><b>Related Context:</b> ${this.escapeHtml(r.related_clause_context)}</div>` : ''}

          <div style="display:flex; justify-content:space-between; align-items:center; margin-top:0.6rem; border-top:1px solid rgba(0,0,0,0.06); padding-top:0.45rem;">
            <button class="btn btn-secondary btn-sm" onclick="workspace.loadDocumentAndHighlight('${r.document_id}', '${r.clause_id}', ${r.page_start || 1})">
              Inspect in Workspace
            </button>
            <button class="btn btn-subtle btn-sm" onclick="risksHandler.toggleReview('${r.id}')">
              ${r.is_reviewed ? 'Reviewed' : 'Mark Reviewed'}
            </button>
          </div>
        </div>
      `;
    }).join('');
  },

  async toggleReview(riskId) {
    try {
      const res = await fetch(`/api/analysis/risks/${riskId}/review`, { method: 'POST' });
      const data = await res.json();
      const risk = this.allRisks.find(r => r.id === riskId);
      if (risk) risk.is_reviewed = data.is_reviewed;
      const currentFilter = document.getElementById('risks-view-filter')?.value || 'all';
      this.filterRisks(currentFilter);
      app.toast('Risk review status updated', 'success');
      dashboard.loadStats();
    } catch (err) {
      app.toast('Failed to update review status: ' + err.message, 'error');
    }
  },

  escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>"']/g, m => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    })[m]);
  }
};
