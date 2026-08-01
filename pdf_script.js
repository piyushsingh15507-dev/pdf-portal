document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const pdfTokenInput = document.getElementById('pdf-token');
    const pdfUserCoursesSelect = document.getElementById('pdf-user-courses');
    const btnLoadCourses = document.getElementById('btn-pdf-load-courses');
    const pdfCourseIdInput = document.getElementById('pdf-course-id');
    const btnScan = document.getElementById('btn-pdf-scan');
    const btnExportTxt = document.getElementById('btn-pdf-export-txt');
    const btnBatchDownload = document.getElementById('btn-pdf-batch-download');
    
    const searchInput = document.getElementById('pdf-search-input');
    const folderFilterSelect = document.getElementById('pdf-folder-filter');
    const statsBadge = document.getElementById('stats-badge');
    const pdfListTbody = document.getElementById('pdf-list-tbody');

    const progressCard = document.getElementById('progress-card');
    const batchStatusText = document.getElementById('batch-status-text');
    const batchProgressPct = document.getElementById('batch-progress-pct');
    const batchProgressBar = document.getElementById('batch-progress-bar');
    const batchCurrentTitle = document.getElementById('batch-current-title');
    const batchLogsText = document.getElementById('batch-logs-text');

    // Global State
    let extractedPdfs = [];
    let pollingInterval = null;

    // Load saved Access Token from localStorage if exists
    const savedToken = localStorage.getItem('classplus_access_token');
    if (savedToken) {
        pdfTokenInput.value = savedToken;
    }

    pdfTokenInput.addEventListener('change', () => {
        const val = pdfTokenInput.value.trim();
        if (val) {
            localStorage.setItem('classplus_access_token', val);
        }
    });

    // 1. Auto-Discover Purchased Courses
    btnLoadCourses.addEventListener('click', async () => {
        const token = pdfTokenInput.value.trim();
        if (!token) {
            alert('Please paste your Classplus Access Token first.');
            pdfTokenInput.focus();
            return;
        }

        btnLoadCourses.disabled = true;
        btnLoadCourses.innerText = 'Loading...';

        try {
            const res = await fetch('/api/user-courses', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token })
            });
            const data = await res.json();

            if (data.success && Array.isArray(data.courses)) {
                pdfUserCoursesSelect.innerHTML = '<option value="">-- Select a Purchased Course --</option>';
                data.courses.forEach(c => {
                    const opt = document.createElement('option');
                    opt.value = c.id || c.courseId;
                    opt.innerText = `${c.name || c.title} (ID: ${opt.value})`;
                    pdfUserCoursesSelect.appendChild(opt);
                });
                alert(`Successfully found ${data.courses.length} purchased courses!`);
            } else {
                alert(`Failed to load courses: ${data.error || 'Unknown error'}`);
            }
        } catch (err) {
            alert(`Error fetching courses: ${err.message}`);
        } finally {
            btnLoadCourses.disabled = false;
            btnLoadCourses.innerText = 'Auto-Load';
        }
    });

    pdfUserCoursesSelect.addEventListener('change', () => {
        if (pdfUserCoursesSelect.value) {
            pdfCourseIdInput.value = pdfUserCoursesSelect.value;
        }
    });

    // 2. Scan Course PDFs
    btnScan.addEventListener('click', async () => {
        const token = pdfTokenInput.value.trim();
        const courseId = pdfCourseIdInput.value.trim();

        if (!token) {
            alert('Please enter your Access Token.');
            pdfTokenInput.focus();
            return;
        }
        if (!courseId) {
            alert('Please enter a Course ID or select one from Auto-Load.');
            pdfCourseIdInput.focus();
            return;
        }

        const spinner = btnScan.querySelector('.spinner');
        const btnText = btnScan.querySelector('.btn-text');
        spinner.classList.remove('hidden');
        btnText.innerText = 'Scanning...';
        btnScan.disabled = true;

        try {
            const res = await fetch('/api/pdf/course-pdfs', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token, course_id: courseId })
            });
            const data = await res.json();

            if (data.success && Array.isArray(data.pdfs)) {
                extractedPdfs = data.pdfs;
                renderPdfTable(extractedPdfs);
                populateFolderFilter(extractedPdfs);

                statsBadge.innerText = `${extractedPdfs.length} PDFs Found`;
                btnExportTxt.disabled = extractedPdfs.length === 0;
                btnBatchDownload.disabled = extractedPdfs.length === 0;
                searchInput.disabled = extractedPdfs.length === 0;
                folderFilterSelect.disabled = extractedPdfs.length === 0;

                if (extractedPdfs.length === 0) {
                    alert('Scan complete: No PDF files or document materials found in this course.');
                }
            } else {
                alert(`Scan failed: ${data.error || 'Could not fetch PDFs'}`);
            }
        } catch (err) {
            alert(`Error scanning PDFs: ${err.message}`);
        } finally {
            spinner.classList.add('hidden');
            btnText.innerText = '🔍 Scan Course PDFs';
            btnScan.disabled = false;
        }
    });

    // Render Table Rows
    function renderPdfTable(pdfList) {
        if (pdfList.length === 0) {
            pdfListTbody.innerHTML = `
                <tr class="empty-row">
                    <td colspan="4">
                        <div class="empty-state">
                            <div class="empty-icon">📂</div>
                            <p>No matching PDFs found.</p>
                        </div>
                    </td>
                </tr>`;
            return;
        }

        let html = '';
        pdfList.forEach((pdf, index) => {
            const folderPath = pdf.folder_path ? pdf.folder_path : 'Root Directory';
            const downloadUrl = pdf.url || '#';

            html += `
                <tr>
                    <td>${index + 1}</td>
                    <td>
                        <div class="pdf-title-cell">
                            <span class="pdf-icon">📄</span>
                            <span>${escapeHtml(pdf.title)}</span>
                        </div>
                    </td>
                    <td>
                        <span class="pdf-folder-tag">${escapeHtml(folderPath)}</span>
                    </td>
                    <td style="text-align: center;">
                        <a href="${downloadUrl}" target="_blank" download="${escapeHtml(pdf.title)}.pdf" class="btn btn-primary action-btn">
                            ⬇️ Direct Download
                        </a>
                    </td>
                </tr>`;
        });
        pdfListTbody.innerHTML = html;
    }

    // Populate Folder Filter Options
    function populateFolderFilter(pdfList) {
        const folders = new Set();
        pdfList.forEach(p => {
            if (p.folder_path) folders.add(p.folder_path);
        });

        folderFilterSelect.innerHTML = '<option value="ALL">All Folders</option>';
        folders.forEach(f => {
            const opt = document.createElement('option');
            opt.value = f;
            opt.innerText = f;
            folderFilterSelect.appendChild(opt);
        });
    }

    // Live Search & Folder Filtering
    function applyFilters() {
        const query = searchInput.value.toLowerCase().trim();
        const selectedFolder = folderFilterSelect.value;

        const filtered = extractedPdfs.filter(pdf => {
            const matchesQuery = pdf.title.toLowerCase().includes(query) || (pdf.folder_path && pdf.folder_path.toLowerCase().includes(query));
            const matchesFolder = selectedFolder === 'ALL' || pdf.folder_path === selectedFolder;
            return matchesQuery && matchesFolder;
        });

        renderPdfTable(filtered);
    }

    searchInput.addEventListener('input', applyFilters);
    folderFilterSelect.addEventListener('change', applyFilters);

    // 3. Export PDF Direct Links (.txt)
    btnExportTxt.addEventListener('click', async () => {
        const token = pdfTokenInput.value.trim();
        const courseId = pdfCourseIdInput.value.trim();

        if (!token || !courseId) return;

        btnExportTxt.disabled = true;
        btnExportTxt.innerText = 'Exporting...';

        try {
            const res = await fetch('/api/pdf/export-links', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token, course_id: courseId })
            });
            const data = await res.json();

            if (data.success && data.content) {
                // Trigger browser blob download for the .txt file
                const blob = new Blob([data.content], { type: 'text/plain;charset=utf-8;' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = data.filename || `Classplus_PDF_Links_${courseId}.txt`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            } else {
                alert(`Export failed: ${data.error || 'Unknown error'}`);
            }
        } catch (err) {
            alert(`Error exporting links: ${err.message}`);
        } finally {
            btnExportTxt.disabled = false;
            btnExportTxt.innerText = '📄 Export PDF Links (.txt)';
        }
    });

    // 4. Download All PDFs to Disk (Batch Process)
    btnBatchDownload.addEventListener('click', async () => {
        const token = pdfTokenInput.value.trim();
        const courseId = pdfCourseIdInput.value.trim();

        if (!token || !courseId) return;

        if (!confirm(`Are you sure you want to download all ${extractedPdfs.length} PDFs into organized course folders on your machine?`)) {
            return;
        }

        btnBatchDownload.disabled = true;
        progressCard.classList.remove('hidden');

        try {
            const res = await fetch('/api/pdf/batch-download', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token, course_id: courseId })
            });
            const data = await res.json();

            if (data.success) {
                startPollingProgress();
            } else {
                alert(`Batch download error: ${data.error}`);
                btnBatchDownload.disabled = false;
            }
        } catch (err) {
            alert(`Failed to start batch download: ${err.message}`);
            btnBatchDownload.disabled = false;
        }
    });

    function startPollingProgress() {
        if (pollingInterval) clearInterval(pollingInterval);
        pollingInterval = setInterval(pollBatchStatus, 1500);
    }

    async function pollBatchStatus() {
        try {
            const res = await fetch('/api/pdf/batch-status');
            const data = await res.json();

            if (data) {
                batchStatusText.innerText = data.status_text || 'In Progress...';
                batchCurrentTitle.innerText = data.current_title ? `Processing: ${data.current_title}` : '';
                
                const total = data.total_pdfs || 1;
                const current = data.current_index || 0;
                const pct = Math.round((current / total) * 100);

                batchProgressPct.innerText = `${pct}%`;
                batchProgressBar.style.width = `${pct}%`;
                batchLogsText.innerText = data.logs || 'No logs yet...';
                
                // Auto scroll terminal logs
                const terminal = document.getElementById('batch-logs-container');
                terminal.scrollTop = terminal.scrollHeight;

                if (!data.running) {
                    clearInterval(pollingInterval);
                    btnBatchDownload.disabled = false;
                }
            }
        } catch (err) {
            console.error('Polling error:', err);
        }
    }

    function escapeHtml(str) {
        return (str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
});
