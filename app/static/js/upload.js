// RuleRadar AI - Document Upload & Validation Controller
const uploadHandler = {
  selectedFile: null,

  init() {
    this.setupDropzone();
  },

  setupDropzone() {
    const dropzone = document.getElementById('upload-dropzone');
    if (!dropzone) return;

    ['dragenter', 'dragover'].forEach(eventName => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.add('dragover');
      }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.remove('dragover');
      }, false);
    });

    dropzone.addEventListener('drop', (e) => {
      const dt = e.dataTransfer;
      const files = dt.files;
      if (files.length > 0) {
        this.handleFileSelect(files[0]);
      }
    });
  },

  openModal() {
    this.resetModal();
    const modal = document.getElementById('upload-modal');
    if (modal) modal.classList.add('active');
  },

  closeModal() {
    const modal = document.getElementById('upload-modal');
    if (modal) modal.classList.remove('active');
    this.resetModal();
  },

  resetModal() {
    this.selectedFile = null;
    const fileInput = document.getElementById('file-input');
    if (fileInput) fileInput.value = '';
    const label = document.getElementById('dropzone-label');
    if (label) label.textContent = 'Click to browse or drop file here';
    const progress = document.getElementById('upload-progress-box');
    if (progress) progress.style.display = 'none';
    const errBox = document.getElementById('upload-error-box');
    if (errBox) {
      errBox.style.display = 'none';
      errBox.textContent = '';
    }
    const btn = document.getElementById('btn-submit-upload');
    if (btn) btn.disabled = false;
  },

  handleFileSelect(file) {
    if (!file) return;

    const validExtensions = ['.pdf', '.docx', '.txt'];
    const fileName = file.name.toLowerCase();
    const isValidExt = validExtensions.some(ext => fileName.endsWith(ext));

    const errBox = document.getElementById('upload-error-box');
    if (!isValidExt) {
      errBox.textContent = `Invalid file format '${file.name}'. Only PDF, DOCX, and TXT files are supported.`;
      errBox.style.display = 'block';
      this.selectedFile = null;
      return;
    }

    const maxBytes = 25 * 1024 * 1024; // 25 MB
    if (file.size > maxBytes) {
      errBox.textContent = `File size (${(file.size / 1024 / 1024).toFixed(1)} MB) exceeds 25 MB maximum limit.`;
      errBox.style.display = 'block';
      this.selectedFile = null;
      return;
    }

    errBox.style.display = 'none';
    this.selectedFile = file;

    const label = document.getElementById('dropzone-label');
    label.innerHTML = `<b>Selected:</b> ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
  },

  async submitUpload() {
    if (!this.selectedFile) {
      const errBox = document.getElementById('upload-error-box');
      errBox.textContent = 'Please choose a valid PDF, DOCX, or TXT file to upload.';
      errBox.style.display = 'block';
      return;
    }

    const category = document.getElementById('upload-category').value;
    const progressBox = document.getElementById('upload-progress-box');
    const progressText = document.getElementById('upload-progress-text');
    const errBox = document.getElementById('upload-error-box');
    const btn = document.getElementById('btn-submit-upload');

    progressBox.style.display = 'block';
    progressText.textContent = 'Ingesting document, extracting text & running NLP classification...';
    errBox.style.display = 'none';
    btn.disabled = true;

    const formData = new FormData();
    formData.append('file', this.selectedFile);
    formData.append('category', category);

    try {
      const response = await fetch('/api/documents/upload', {
        method: 'POST',
        body: formData
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || data.message || 'Upload processing failed');
      }

      app.toast(`Document '${this.selectedFile.name}' analyzed successfully!`, 'success');
      this.closeModal();

      // Open in workspace immediately
      if (data.document && data.document.id) {
        app.selectedDocumentId = data.document.id;
        app.navigate('workspace');
      } else {
        app.navigate('dashboard');
      }
    } catch (err) {
      btn.disabled = false;
      progressBox.style.display = 'none';
      errBox.textContent = err.message;
      errBox.style.display = 'block';
      app.toast('Upload error: ' + err.message, 'error');
    }
  }
};
