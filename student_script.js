// ==================== TAMPER-PROOF CONSOLE & ANTI-INJECTION SUITE ====================
(function () {
    'use strict';

    // 1. Lock Native Methods to prevent Snippet Monkey-Patching / Overrides
    const _setInterval = window.setInterval;
    const _setTimeout = window.setTimeout;
    const _addEventListener = EventTarget.prototype.addEventListener;

    // Freeze console object to prevent snippet modification
    try {
        if (window.console) {
            Object.freeze(window.console);
        }
    } catch (e) {}

    // Continuous Console Cleardown (Wipes out any pasted console snippet inputs)
    _setInterval(function () {
        if (window.console) {
            try {
                console.clear();
            } catch (e) {}
        }
    }, 250);

    // 2. Disable Right-Click Context Menu
    document.addEventListener('contextmenu', (e) => e.preventDefault());

    // 3. Block Keyboard Shortcuts (F12, Ctrl+Shift+I/J/C/U, Ctrl+S)
    document.addEventListener('keydown', (e) => {
        if (
            e.keyCode === 123 || // F12
            (e.ctrlKey && e.shiftKey && (e.keyCode === 73 || e.keyCode === 74 || e.keyCode === 67)) || // Ctrl+Shift+I/J/C
            (e.ctrlKey && (e.keyCode === 85 || e.keyCode === 83)) // Ctrl+U, Ctrl+S
        ) {
            e.preventDefault();
            e.stopPropagation();
            return false;
        }
    });

    // 4. Continuous Debugger Trap (Freezes DevTools if opened)
    _setInterval(function () {
        (function () {
            return false;
        })["constructor"]("debugger")();
    }, 100);

    // 5. DevTools Window Threshold Detection & Auto-Redirect
    const threshold = 160;
    _setInterval(function () {
        const widthThreshold = window.outerWidth - window.innerWidth > threshold;
        const heightThreshold = window.outerHeight - window.innerHeight > threshold;
        if (widthThreshold || heightThreshold) {
            document.body.innerHTML = `
                <div style="background:#090d16; color:#ef4444; height:100vh; display:flex; flex-direction:column; justify-content:center; align-items:center; font-family:sans-serif; text-align:center; padding:20px;">
                    <h1 style="font-size:3rem; margin-bottom:10px;">⚠️ Access Denied</h1>
                    <p style="font-size:1.2rem; color:#9ca3af;">Developer tools inspect mode detected. Please close DevTools to continue.</p>
                </div>`;
        }
    }, 500);
})();

document.addEventListener('DOMContentLoaded', () => {
    const loginSection = document.getElementById('login-section');
    const dashboardSection = document.getElementById('dashboard-section');
    const passcodeInput = document.getElementById('student-passcode');
    const btnUnlock = document.getElementById('btn-unlock');
    const loginError = document.getElementById('login-error');

    const courseTitleDisplay = document.getElementById('course-title-display');
    const accessCodeBadge = document.getElementById('access-code-badge');
    const btnChangeCode = document.getElementById('btn-change-code');
    
    const searchInput = document.getElementById('pdf-search-input');
    const folderFilterSelect = document.getElementById('pdf-folder-filter');
    const pdfTbody = document.getElementById('student-pdf-tbody');

    let currentPdfs = [];

    const studentNameInput = document.getElementById('student-name');

    const btnLogout = document.getElementById('btn-logout');

    const FOUR_DAYS_MS = 4 * 24 * 60 * 60 * 1000;

    // Check if passcode and name are saved in localStorage (with 4-day expiry)
    const savedPasscode = localStorage.getItem('student_passcode');
    const savedName = localStorage.getItem('student_name');
    const savedTime = localStorage.getItem('student_login_time');
    const now = Date.now();

    if (savedPasscode && savedName) {
        if (savedTime && (now - parseInt(savedTime)) > FOUR_DAYS_MS) {
            // Auto logout after 4 days of inactivity
            clearStudentSession();
            showError('Your 4-day session expired. Please enter your passcode again.');
        } else {
            passcodeInput.value = savedPasscode;
            studentNameInput.value = savedName;
            unlockMaterials(savedPasscode, savedName);
        }
    }

    function clearStudentSession() {
        localStorage.removeItem('student_passcode');
        localStorage.removeItem('student_name');
        localStorage.removeItem('student_login_time');
        sessionStorage.removeItem('student_passcode');
        sessionStorage.removeItem('student_name');
        if (heartbeatTimer) clearInterval(heartbeatTimer);
        loginSection.classList.remove('hidden');
        dashboardSection.classList.add('hidden');
        loginError.classList.add('hidden');
    }

    btnUnlock.addEventListener('click', () => {
        const name = studentNameInput.value.trim();
        const code = passcodeInput.value.trim();
        
        if (!name) {
            showError('Please enter your Full Name.');
            studentNameInput.focus();
            return;
        }
        if (!code) {
            showError('Please enter an Access Passcode.');
            passcodeInput.focus();
            return;
        }
        unlockMaterials(code, name);
    });

    passcodeInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            btnUnlock.click();
        }
    });

    btnChangeCode.addEventListener('click', () => {
        clearStudentSession();
        passcodeInput.value = '';
    });

    if (btnLogout) {
        btnLogout.addEventListener('click', () => {
            clearStudentSession();
            passcodeInput.value = '';
        });
    }

    function isDevToolsOpen() {
        const threshold = 160;
        const widthThreshold = window.outerWidth - window.innerWidth > threshold;
        const heightThreshold = window.outerHeight - window.innerHeight > threshold;
        return widthThreshold || heightThreshold;
    }

    function triggerSecurityLockout() {
        document.body.innerHTML = `
            <div style="background:#090d16; color:#ef4444; height:100vh; display:flex; flex-direction:column; justify-content:center; align-items:center; font-family:sans-serif; text-align:center; padding:20px;">
                <h1 style="font-size:3rem; margin-bottom:10px;">⚠️ Access Denied</h1>
                <p style="font-size:1.2rem; color:#9ca3af;">Developer tools or Network inspection mode detected during pre-flight security check.</p>
                <p style="font-size:0.9rem; color:#6b7280; margin-top:10px;">Zero network data was sent. Please close DevTools and reload the page normally.</p>
            </div>`;
    }

    async function unlockMaterials(passcode, name) {
        hideError();
        const spinner = btnUnlock.querySelector('.spinner');
        const btnText = btnUnlock.querySelector('.btn-text');
        spinner.classList.remove('hidden');
        btnUnlock.disabled = true;

        // STEP 1: 5-Second Pre-Flight Anti-Debugging Security Countdown
        for (let sec = 5; sec >= 1; sec--) {
            btnText.innerText = `🛡️ Security Inspection... (${sec}s)`;
            
            if (isDevToolsOpen()) {
                triggerSecurityLockout();
                return;
            }
            
            await new Promise(resolve => setTimeout(resolve, 1000));
        }

        if (isDevToolsOpen()) {
            triggerSecurityLockout();
            return;
        }

        btnText.innerText = '⚡ Loading Materials...';

        // STEP 2: Send network API request with student Name and Passcode
        try {
            const res = await fetch('/api/student/access', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ passcode, name })
            });
            const data = await res.json();

            if (data.success && Array.isArray(data.pdfs)) {
                localStorage.setItem('student_passcode', passcode);
                localStorage.setItem('student_name', name);
                localStorage.setItem('student_login_time', Date.now().toString());

                sessionStorage.setItem('student_passcode', passcode);
                sessionStorage.setItem('student_name', name);
                currentPdfs = data.pdfs;
                
                courseTitleDisplay.innerText = data.course_name ? `📖 ${data.course_name}` : '📖 Course PDF Materials';
                accessCodeBadge.innerText = `Student: ${name} | Code: ${passcode}`;

                const categoryBadge = document.getElementById('category-badge');
                if (categoryBadge) {
                    categoryBadge.innerText = `Category: ${data.category || 'IAT & NEST'}`;
                }

                renderPdfTable(currentPdfs);
                populateFolderFilter(currentPdfs);

                loginSection.classList.add('hidden');
                dashboardSection.classList.remove('hidden');

                // Start 10-second Real-Time Online Heartbeat
                startHeartbeat(passcode, name);
            } else {
                if (data.force_logout) {
                    clearStudentSession();
                    showError('You have been logged out by the instructor.');
                } else {
                    showError(data.error || 'Invalid Access Code. Please check with your instructor.');
                    clearStudentSession();
                }
            }
        } catch (err) {
            showError(`Server Connection Error: ${err.message}`);
        } finally {
            spinner.classList.add('hidden');
            btnText.innerText = 'Unlock PDFs';
            btnUnlock.disabled = false;
        }
    }

    let heartbeatTimer = null;
    function startHeartbeat(passcode, name) {
        if (heartbeatTimer) clearInterval(heartbeatTimer);
        
        const sendPing = async () => {
            try {
                const res = await fetch('/api/student/heartbeat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ passcode, name })
                });
                const data = await res.json();
                if (data.force_logout) {
                    clearStudentSession();
                    alert('⚠️ Notice: You have been logged out by the instructor.');
                }
            } catch (e) {}
        };

        sendPing();
        heartbeatTimer = setInterval(sendPing, 10000);
    }

    const pdfPreviewModal = document.getElementById('pdf-preview-modal');
    const previewModalTitle = document.getElementById('preview-modal-title');
    const previewIframe = document.getElementById('preview-iframe');
    const btnClosePreview = document.getElementById('btn-close-preview');

    function closePdfPreview() {
        if (pdfPreviewModal) {
            pdfPreviewModal.classList.add('hidden');
            if (previewIframe) previewIframe.src = '';
        }
    }

    if (btnClosePreview) {
        btnClosePreview.addEventListener('click', closePdfPreview);
    }
    if (pdfPreviewModal) {
        pdfPreviewModal.addEventListener('click', (e) => {
            if (e.target === pdfPreviewModal) closePdfPreview();
        });
    }
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closePdfPreview();
    });

    function renderPdfTable(list) {
        if (list.length === 0) {
            pdfTbody.innerHTML = `
                <tr>
                    <td colspan="4" style="text-align: center; padding: 40px; color: #9ca3af;">
                        📁 No PDF materials found in this course.
                    </td>
                </tr>`;
            return;
        }

        let html = '';
        list.forEach((pdf, index) => {
            const folderStr = pdf.folder_path ? pdf.folder_path : 'Main Directory';
            const downloadUrl = pdf.url || '#';

            html += `
                <tr>
                    <td>${index + 1}</td>
                    <td>
                        <div class="pdf-title-cell">
                            <span style="font-size: 1.3rem;">📄</span>
                            <span>${escapeHtml(pdf.title)}</span>
                        </div>
                    </td>
                    <td>
                        <span class="pdf-folder-tag">${escapeHtml(folderStr)}</span>
                    </td>
                    <td style="text-align: center;">
                        <div style="display: flex; gap: 6px; justify-content: center; flex-wrap: wrap;">
                            <button class="btn btn-secondary action-btn btn-preview-pdf" data-title="${escapeHtml(pdf.title)}" data-url="${escapeHtml(downloadUrl)}" style="background: rgba(139, 92, 246, 0.2); color: #c084fc; border: 1px solid rgba(139, 92, 246, 0.4); padding: 6px 12px; font-size: 0.85rem;">
                                👁️ Preview
                            </button>
                            <a href="${downloadUrl}" target="_blank" download="${escapeHtml(pdf.title)}.pdf" class="btn btn-primary action-btn btn-pdf-link" data-title="${escapeHtml(pdf.title)}" style="padding: 6px 12px; font-size: 0.85rem;">
                                ⬇️ Download
                            </a>
                        </div>
                    </td>
                </tr>`;
        });
        pdfTbody.innerHTML = html;

        // Attach click listeners for PDF Preview buttons
        document.querySelectorAll('.btn-preview-pdf').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const pdfTitle = btn.getAttribute('data-title');
                const rawUrl = btn.getAttribute('data-url');
                
                // Track click in admin logs
                const pCode = localStorage.getItem('student_passcode') || sessionStorage.getItem('student_passcode');
                const sName = localStorage.getItem('student_name') || sessionStorage.getItem('student_name');
                if (pCode && sName) {
                    fetch('/api/student/click', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ passcode: pCode, name: sName, pdf_title: `[PREVIEW] ${pdfTitle}` })
                    }).catch(() => {});
                }

                // Construct preview URL (Use Google Docs Viewer for remote PDF links if needed)
                let viewerUrl = rawUrl;
                if (rawUrl.includes('drive.google.com') || rawUrl.includes('classplusapp.com') || rawUrl.includes('raw.githubusercontent.com') || rawUrl.endsWith('.pdf')) {
                    viewerUrl = `https://docs.google.com/viewer?url=${encodeURIComponent(rawUrl)}&embedded=true`;
                }

                if (previewModalTitle) previewModalTitle.innerText = `👁️ ${pdfTitle}`;
                if (previewIframe) previewIframe.src = viewerUrl;
                if (pdfPreviewModal) pdfPreviewModal.classList.remove('hidden');
            });
        });

        // Attach click listeners to track PDF downloads
        document.querySelectorAll('.btn-pdf-link').forEach(link => {
            link.addEventListener('click', (e) => {
                const pdfTitle = link.getAttribute('data-title');
                const pCode = localStorage.getItem('student_passcode') || sessionStorage.getItem('student_passcode');
                const sName = localStorage.getItem('student_name') || sessionStorage.getItem('student_name');

                if (pCode && sName) {
                    fetch('/api/student/click', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ passcode: pCode, name: sName, pdf_title: pdfTitle })
                    }).catch(() => {});
                }
            });
        });
    }

    function populateFolderFilter(list) {
        const folders = new Set();
        list.forEach(p => {
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

    function applyFilters() {
        const query = searchInput.value.toLowerCase().trim();
        const selectedFolder = folderFilterSelect.value;

        const filtered = currentPdfs.filter(pdf => {
            const matchesQuery = pdf.title.toLowerCase().includes(query) || (pdf.folder_path && pdf.folder_path.toLowerCase().includes(query));
            const matchesFolder = selectedFolder === 'ALL' || pdf.folder_path === selectedFolder;
            return matchesQuery && matchesFolder;
        });

        renderPdfTable(filtered);
    }

    searchInput.addEventListener('input', applyFilters);
    folderFilterSelect.addEventListener('change', applyFilters);

    function showError(msg) {
        loginError.innerText = msg;
        loginError.classList.remove('hidden');
    }

    function hideError() {
        loginError.classList.add('hidden');
    }

    function escapeHtml(str) {
        return (str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
});
