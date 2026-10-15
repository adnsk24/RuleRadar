// RuleRadar AI - Core State & Navigation Router
const app = {
  currentView: 'dashboard',
  selectedDocumentId: null,

  init() {
    this.setupNavigation();
    dashboard.init();
    uploadHandler.init();
    workspace.init();
    compareHandler.init();
    explorerHandler.init();
    settingsHandler.init();

    // Check URL hash if present
    const validViews = ['dashboard', 'documents', 'workspace', 'compare', 'explorer', 'risks', 'activity', 'settings'];
    const hash = window.location.hash.replace('#', '');
    if (hash && validViews.includes(hash)) {
      this.navigate(hash);
    } else {
      this.navigate('dashboard');
    }
  },

  setupNavigation() {
    window.addEventListener('hashchange', () => {
      const h = window.location.hash.replace('#', '');
      if (h) this.navigate(h, false);
    });
  },

  navigate(viewName, updateHash = true) {
    this.currentView = viewName;
    if (updateHash) {
      window.location.hash = viewName;
    }

    // Scroll to top of main content
    window.scrollTo({ top: 0, behavior: 'instant' });

    // Hide all view sections
    document.querySelectorAll('.view-section').forEach(el => el.classList.remove('active'));

    // Deactivate all sidebar nav items & legacy items
    document.querySelectorAll('.sidebar-nav-item, .nav-item').forEach(el => el.classList.remove('active'));

    const targetView = document.getElementById(`view-${viewName}`);
    if (targetView) {
      targetView.classList.add('active');
    }

    const targetNav = document.getElementById(`nav-sidebar-${viewName}`) || document.getElementById(`nav-${viewName}`);
    if (targetNav) {
      targetNav.classList.add('active');
    }

    // Update Header Breadcrumb Title
    const breadcrumb = document.getElementById('header-breadcrumb');
    if (breadcrumb) {
      const titles = {
        dashboard: 'Overview',
        documents: 'My Documents',
        workspace: 'Analyze Document',
        compare: 'Compare Documents',
        explorer: 'Important Clauses',
        risks: 'Risk Analysis',
        activity: 'Activity History',
        settings: 'Settings & Privacy'
      };
      breadcrumb.textContent = titles[viewName] || 'Overview';
    }

    // Trigger view-specific workflows
    if (viewName === 'dashboard') {
      dashboard.refresh();
    } else if (viewName === 'documents') {
      dashboard.loadFullDocuments();
    } else if (viewName === 'compare') {
      compareHandler.loadDocOptions();
    } else if (viewName === 'explorer') {
      explorerHandler.loadCategories();
      explorerHandler.search();
    } else if (viewName === 'risks') {
      risksHandler.loadAllRisks();
    } else if (viewName === 'activity') {
      dashboard.loadActivities('activity-full-feed-container', 50);
    } else if (viewName === 'settings') {
      settingsHandler.checkHealth();
    } else if (viewName === 'workspace') {
      if (!this.selectedDocumentId && dashboard.documentsList && dashboard.documentsList.length > 0) {
        this.selectedDocumentId = dashboard.documentsList[0].id;
      }
      if (this.selectedDocumentId) {
        workspace.loadDocument(this.selectedDocumentId);
      }
    }
  },

  handleGlobalSearch(query) {
    const q = (query || '').trim();
    if (!q) return;

    if (this.currentView === 'documents') {
      const searchBox = document.getElementById('full-doc-search');
      if (searchBox) {
        searchBox.value = q;
        dashboard.filterFullTable(q);
      }
    } else {
      this.navigate('explorer');
      const searchBox = document.getElementById('explorer-search');
      if (searchBox) {
        searchBox.value = q;
        explorerHandler.search();
      }
    }
  },

  escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>"']/g, m => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    })[m]);
  },

  toast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    const icon = type === 'error' ? '!' : (type === 'success' ? '✓' : 'i');
    toast.innerHTML = `<span style="font-weight:700; font-family:monospace; margin-right:4px;">[${icon}]</span> <span>${this.escapeHtml(message)}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      setTimeout(() => toast.remove(), 250);
    }, 3500);
  }
};

// Help Modal Handler
const helpHandler = {
  openModal() {
    const modal = document.getElementById('help-modal');
    if (modal) modal.classList.add('active');
  },
  closeModal() {
    const modal = document.getElementById('help-modal');
    if (modal) modal.classList.remove('active');
  }
};

document.addEventListener('DOMContentLoaded', () => app.init());
