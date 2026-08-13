document.addEventListener('DOMContentLoaded', () => {
    const adminLoginSection = document.getElementById('admin-login-section');
    const adminDashboardSection = document.getElementById('admin-dashboard-section');
    const adminAuthPassInput = document.getElementById('admin-auth-pass');
    const btnAdminAuth = document.getElementById('btn-admin-auth');
    const adminAuthError = document.getElementById('admin-auth-error');
    const btnLockAdmin = document.getElementById('btn-lock-admin');

    const adminTokenInput = document.getElementById('admin-token');
    const btnSaveToken = document.getElementById('btn-save-token');

    const passcodeCodeInput = document.getElementById('passcode-code');
    const passcodeCourseIdInput = document.getElementById('passcode-course-id');
    const passcodeCourseNameInput = document.getElementById('passcode-course-name');
    const passcodeCategorySelect = document.getElementById('passcode-category');
    const passcodeScopeSelect = document.getElementById('passcode-scope');
    const btnCreateCode = document.getElementById('btn-create-code');

    const passcodeCountBadge = document.getElementById('passcode-count-badge');
    const passcodesTbody = document.getElementById('passcodes-tbody');
    const studentCountBadge = document.getElementById('student-count-badge');
    const studentsTbody = document.getElementById('students-tbody');

    const customPdfCodeInput = document.getElementById('custom-pdf-code');
    const customPdfTitleInput = document.getElementById('custom-pdf-title');
    const customPdfFolderInput = document.getElementById('custom-pdf-folder');
    const customPdfUrlInput = document.getElementById('custom-pdf-url');
    const btnAddCustomPdf = document.getElementById('btn-add-custom-pdf');

    const customVidCodeInput = document.getElementById('custom-vid-code');
    const customVidTitleInput = document.getElementById('custom-vid-title');
    const customVidFolderInput = document.getElementById('custom-vid-folder');
    const customVidUrlInput = document.getElementById('custom-vid-url');
    const btnAddCustomVid = document.getElementById('btn-add-custom-vid');

    const newAdminSecretInput = document.getElementById('new-admin-secret');
    const btnChangeAdminSecret = document.getElementById('btn-change-admin-secret');

    let currentAdminSecret = sessionStorage.getItem('admin_secret') || localStorage.getItem('admin_secret') || '';

    async function checkSupabaseStatus() {
        const badge = document.getElementById('supabase-db-status-badge');
        if (!badge) return;
        try {
            const res = await fetch('/api/admin/supabase-status');
            const data = await res.json();
            if (data.success) {
                badge.innerText = data.status || (data.enabled ? '🟢 Supabase PostgreSQL Active' : '🟡 Cloud DB Fallback Active');
                if (!data.enabled) {
                    badge.style.background = 'rgba(245, 158, 11, 0.15)';
                    badge.style.color = '#fbbf24';
                    badge.style.borderColor = 'rgba(245, 158, 11, 0.3)';
                }
            }
        } catch (err) {}
    }

    if (!currentAdminSecret) {
        window.location.href = '/admin_login.html';
        return;
    }

    verifyAndLoadAdmin(currentAdminSecret);

    // Layout Customization & Panel Reordering
    const btnToggleLayoutEdit = document.getElementById('btn-toggle-layout-edit');
    const topControlsContainer = document.getElementById('top-controls-container');
    let isLayoutEditMode = false;

    restoreLayoutOrder();

    if (btnToggleLayoutEdit) {
        btnToggleLayoutEdit.addEventListener('click', () => {
            isLayoutEditMode = !isLayoutEditMode;
            document.querySelectorAll('.card-order-controls').forEach(ctrl => {
                if (isLayoutEditMode) {
                    ctrl.classList.remove('hidden');
                } else {
                    ctrl.classList.add('hidden');
                }
            });

            if (isLayoutEditMode) {
                btnToggleLayoutEdit.innerText = '✅ Save Layout Order';
                btnToggleLayoutEdit.style.background = 'linear-gradient(135deg, #10b981, #059669)';
                btnToggleLayoutEdit.style.color = '#fff';
            } else {
                btnToggleLayoutEdit.innerText = '🛠️ Customize Layout';
                btnToggleLayoutEdit.style.background = 'rgba(139, 92, 246, 0.2)';
                btnToggleLayoutEdit.style.color = '#c084fc';
                saveLayoutOrder();
            }
        });
    }

    document.querySelectorAll('.btn-move-up').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const card = e.target.closest('.panel-item');
            if (card && card.previousElementSibling) {
                card.parentNode.insertBefore(card, card.previousElementSibling);
                saveLayoutOrder();
            }
        });
    });

    document.querySelectorAll('.btn-move-down').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const card = e.target.closest('.panel-item');
            if (card && card.nextElementSibling) {
                card.parentNode.insertBefore(card.nextElementSibling, card);
                saveLayoutOrder();
            }
        });
    });

    function saveLayoutOrder() {
        if (!topControlsContainer) return;
        const order = Array.from(topControlsContainer.querySelectorAll('.panel-item'))
            .map(item => item.getAttribute('data-panel-id'));
        localStorage.setItem('admin_layout_order', JSON.stringify(order));
    }

    function restoreLayoutOrder() {
        if (!topControlsContainer) return;
        const saved = localStorage.getItem('admin_layout_order');
        if (!saved) return;
        try {
            const order = JSON.parse(saved);
            const panelMap = {};
            topControlsContainer.querySelectorAll('.panel-item').forEach(item => {
                panelMap[item.getAttribute('data-panel-id')] = item;
            });
            order.forEach(panelId => {
                if (panelMap[panelId]) {
                    topControlsContainer.appendChild(panelMap[panelId]);
                }
            });
        } catch (e) {}
    }

    if (btnLockAdmin) {
        btnLockAdmin.addEventListener('click', () => {
            currentAdminSecret = '';
            sessionStorage.removeItem('admin_secret');
            localStorage.removeItem('admin_secret');
            window.location.href = '/admin_login.html';
        });
    }

    function hideDashboard() {
        sessionStorage.removeItem('admin_secret');
        localStorage.removeItem('admin_secret');
        window.location.href = '/admin_login.html';
    }

    async function verifyAndLoadAdmin(secret) {
        try {
            const res = await fetch('/api/admin/get-data', {
                headers: { 'X-Admin-Secret': secret }
            });
            if (res.ok) {
                const data = await res.json();
                if (data.success) {
                    renderPasscodesTable(data.access_codes || {});
                    renderStudentsTable(data.student_sessions || [], data.blocked_ips || []);
                    if (adminTokenInput && data.admin_token && document.activeElement !== adminTokenInput) {
                        adminTokenInput.value = data.admin_token;
                    }
                    return;
                }
            }
        } catch (e) {}
        hideDashboard();
    }

    async function loadAdminData() {
        if (!currentAdminSecret) return;
        checkSupabaseStatus();
        try {
            const res = await fetch('/api/admin/get-data', {
                headers: { 'X-Admin-Secret': currentAdminSecret }
            });
            const data = await res.json();
            if (data.success) {
                renderPasscodesTable(data.access_codes || {});
                renderStudentsTable(data.student_sessions || [], data.blocked_ips || []);
                if (adminTokenInput && data.admin_token && document.activeElement !== adminTokenInput) {
                    adminTokenInput.value = data.admin_token;
                }
            } else if (res.status === 401) {
                hideDashboard();
            }
        } catch (err) {
            console.error('Error loading admin data:', err);
        }
    }

    // Auto Refresh every 5 seconds
    setInterval(() => {
        if (currentAdminSecret && adminDashboardSection && !adminDashboardSection.classList.contains('hidden')) {
            loadAdminData();
        }
    }, 5000);

    if (btnSaveToken) {
        btnSaveToken.addEventListener('click', async (e) => {
            if (e) e.preventDefault();
            const token = adminTokenInput ? adminTokenInput.value.trim() : '';
            if (!token) {
                alert('Please paste a Classplus Access Token.');
                return;
            }

            btnSaveToken.disabled = true;
            btnSaveToken.innerText = 'Saving...';

            try {
                const res = await fetch('/api/admin/save-token', {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json',
                        'X-Admin-Secret': currentAdminSecret 
                    },
                    body: JSON.stringify({ token })
                });
                const data = await res.json();

                if (data.success) {
                    alert('Admin Access Token saved successfully!');
                } else {
                    alert(`Error saving token: ${data.error}`);
                }
            } catch (err) {
                alert(`Network error: ${err.message}`);
            } finally {
                btnSaveToken.disabled = false;
                btnSaveToken.innerText = '💾 Save Admin Token';
            }
        });
    }

    if (btnCreateCode) {
        btnCreateCode.addEventListener('click', async (e) => {
            if (e) e.preventDefault();
            const code = passcodeCodeInput ? passcodeCodeInput.value.trim().toUpperCase() : '';
            const courseId = passcodeCourseIdInput ? passcodeCourseIdInput.value.trim() : '';
            const category = passcodeCategorySelect ? passcodeCategorySelect.value : 'IAT & NEST';
            const access_scope = passcodeScopeSelect ? passcodeScopeSelect.value : 'all';
            const type = (category === 'IAT & NEST') ? 'classplus' : 'custom';
            const courseName = (passcodeCourseNameInput && passcodeCourseNameInput.value.trim()) ? passcodeCourseNameInput.value.trim() : `${category} Course (${code})`;

            if (!code) {
                alert('Please enter a Custom Student Passcode.');
                return;
            }

            if (type === 'classplus' && !courseId) {
                alert('Target Classplus Course ID is required for IAT & NEST category.');
                return;
            }

            btnCreateCode.disabled = true;
            btnCreateCode.innerText = 'Creating...';

            try {
                const res = await fetch('/api/admin/create-code', {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json',
                        'X-Admin-Secret': currentAdminSecret 
                    },
                    body: JSON.stringify({ code, course_id: courseId, course_name: courseName, category, type, access_scope })
                });
                const data = await res.json();

                if (data.success) {
                    if (passcodeCodeInput) passcodeCodeInput.value = '';
                    if (passcodeCourseIdInput) passcodeCourseIdInput.value = '';
                    if (passcodeCourseNameInput) passcodeCourseNameInput.value = '';
                    loadAdminData();
                    alert(`Passcode '${code}' created successfully!\n\nCategory: [${category}]\nScope: [${access_scope.toUpperCase()}]`);
                } else {
                    alert(`Failed to create passcode: ${data.error}`);
                }
            } catch (err) {
                alert(`Error creating passcode: ${err.message}`);
            } finally {
                btnCreateCode.disabled = false;
                btnCreateCode.innerText = '➕ Create Access Passcode';
            }
        });
    }

    if (btnAddCustomPdf) {
        btnAddCustomPdf.addEventListener('click', async (e) => {
            if (e) e.preventDefault();
            const code = customPdfCodeInput ? customPdfCodeInput.value.trim().toUpperCase() : '';
            const title = customPdfTitleInput ? customPdfTitleInput.value.trim() : '';
            const folder_path = (customPdfFolderInput && customPdfFolderInput.value.trim()) ? customPdfFolderInput.value.trim() : 'Main Directory';
            const url = customPdfUrlInput ? customPdfUrlInput.value.trim() : '';

            if (!code || !title || !url) {
                alert('Please enter Target Passcode, Document Title, and Direct PDF URL.');
                return;
            }

            btnAddCustomPdf.disabled = true;
            btnAddCustomPdf.innerText = 'Adding PDF...';

            try {
                const res = await fetch('/api/admin/add-custom-pdf', {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json',
                        'X-Admin-Secret': currentAdminSecret 
                    },
                    body: JSON.stringify({ code, title, folder_path, url })
                });
                const data = await res.json();

                if (data.success) {
                    if (customPdfTitleInput) customPdfTitleInput.value = '';
                    if (customPdfUrlInput) customPdfUrlInput.value = '';
                    loadAdminData();
                    alert(`PDF '${title}' added successfully to passcode '${code}'!`);
                } else {
                    alert(`Failed to add PDF: ${data.error}`);
                }
            } catch (err) {
                alert(`Error: ${err.message}`);
            } finally {
                btnAddCustomPdf.disabled = false;
                btnAddCustomPdf.innerText = '➕ Add PDF to Passcode';
            }
        });
    }

    if (btnAddCustomVid) {
        btnAddCustomVid.addEventListener('click', async (e) => {
            if (e) e.preventDefault();
            const code = customVidCodeInput ? customVidCodeInput.value.trim().toUpperCase() : '';
            const title = customVidTitleInput ? customVidTitleInput.value.trim() : '';
            const folder_path = (customVidFolderInput && customVidFolderInput.value.trim()) ? customVidFolderInput.value.trim() : 'Main Lectures';
            const url = customVidUrlInput ? customVidUrlInput.value.trim() : '';

            if (!code || !title || !url) {
                alert('Please enter Target Passcode, Video Title, and Video Stream / YouTube URL.');
                return;
            }

            btnAddCustomVid.disabled = true;
            btnAddCustomVid.innerText = 'Adding Video...';

            try {
                const res = await fetch('/api/admin/add-custom-video', {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json',
                        'X-Admin-Secret': currentAdminSecret 
                    },
                    body: JSON.stringify({ code, title, folder_path, url })
                });
                const data = await res.json();

                if (data.success) {
                    if (customVidTitleInput) customVidTitleInput.value = '';
                    if (customVidUrlInput) customVidUrlInput.value = '';
                    loadAdminData();
                    alert(`Video Lecture '${title}' added successfully to passcode '${code}'!`);
                } else {
                    alert(`Failed to add video: ${data.error}`);
                }
            } catch (err) {
                alert(`Error: ${err.message}`);
            } finally {
                btnAddCustomVid.disabled = false;
                btnAddCustomVid.innerText = '🎥 Add Video Lecture to Passcode';
            }
        });
    }

    const smsApiKeyInput = document.getElementById('sms-api-key');
    const btnSaveSmsKey = document.getElementById('btn-save-sms-key');

    const tgBotTokenInput = document.getElementById('tg-bot-token');
    const tgChatIdInput = document.getElementById('tg-chat-id');
    const btnSaveTgGateway = document.getElementById('btn-save-tg-gateway');

    if (btnSaveTgGateway) {
        btnSaveTgGateway.addEventListener('click', async (e) => {
            if (e) e.preventDefault();
            const botToken = tgBotTokenInput ? tgBotTokenInput.value.trim() : '';
            const chatId = tgChatIdInput ? tgChatIdInput.value.trim() : '';
            
            if (!botToken || !chatId) {
                alert('Please enter both Telegram Bot Token and Chat ID.');
                return;
            }

            btnSaveTgGateway.disabled = true;
            btnSaveTgGateway.innerText = 'Saving...';

            try {
                const res = await fetch('/api/admin/save-telegram-gateway', {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json',
                        'X-Admin-Secret': currentAdminSecret 
                    },
                    body: JSON.stringify({ bot_token: botToken, chat_id: chatId })
                });
                const data = await res.json();

                if (data.success) {
                    alert('Telegram Bot Gateway Settings saved successfully! Instant 6-Digit OTP notifications will now arrive in your Telegram App.');
                } else {
                    alert(`Failed to save Telegram settings: ${data.error}`);
                }
            } catch (err) {
                alert(`Error: ${err.message}`);
            } finally {
                btnSaveTgGateway.disabled = false;
                btnSaveTgGateway.innerText = '🤖 Save Telegram Bot Gateway Settings';
            }
        });
    }

    const hlsTitleInput = document.getElementById('hls-stream-title');
    const hlsUrlInput = document.getElementById('hls-stream-url');
    const btnDownloadHlsStream = document.getElementById('btn-download-hls-stream');
    const hlsStatusBox = document.getElementById('hls-download-status-box');
    const hlsStatusText = document.getElementById('hls-download-status-text');
    const hlsPercentText = document.getElementById('hls-download-percent');
    const hlsProgressBar = document.getElementById('hls-download-progress-bar');
    const hlsLinkContainer = document.getElementById('hls-download-link-container');
    const btnSaveMp4File = document.getElementById('btn-save-mp4-file');

    let hlsPollInterval = null;

    if (btnDownloadHlsStream) {
        btnDownloadHlsStream.addEventListener('click', async (e) => {
            if (e) e.preventDefault();
            const title = hlsTitleInput ? hlsTitleInput.value.trim() : 'Live_Lecture';
            const url = hlsUrlInput ? hlsUrlInput.value.trim() : '';

            if (!url) {
                alert('Please enter an HLS Stream URL (.m3u8).');
                return;
            }

            btnDownloadHlsStream.disabled = true;
            btnDownloadHlsStream.innerText = 'Starting Stream Download...';
            if (hlsStatusBox) hlsStatusBox.classList.remove('hidden');
            if (hlsLinkContainer) hlsLinkContainer.classList.add('hidden');

            try {
                const res = await fetch('/api/admin/download-hls-stream', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Admin-Secret': currentAdminSecret
                    },
                    body: JSON.stringify({ title, url })
                });
                const data = await res.json();

                if (data.success) {
                    pollHlsDownloadStatus();
                } else {
                    alert(`Error starting download: ${data.error}`);
                    btnDownloadHlsStream.disabled = false;
                    btnDownloadHlsStream.innerText = '📥 Download Stream to MP4';
                }
            } catch (err) {
                alert(`Network error: ${err.message}`);
                btnDownloadHlsStream.disabled = false;
                btnDownloadHlsStream.innerText = '📥 Download Stream to MP4';
            }
        });
    }

    function pollHlsDownloadStatus() {
        if (hlsPollInterval) clearInterval(hlsPollInterval);
        hlsPollInterval = setInterval(async () => {
            try {
                const res = await fetch('/api/admin/hls-download-status');
                const data = await res.json();

                if (data.success && data.status) {
                    const st = data.status;
                    if (hlsStatusText) hlsStatusText.innerText = st.status_text || 'Downloading...';
                    if (hlsPercentText) hlsPercentText.innerText = `${st.percent || 0}%`;
                    if (hlsProgressBar) hlsProgressBar.style.width = `${st.percent || 0}%`;

                    if (!st.running) {
                        clearInterval(hlsPollInterval);
                        if (btnDownloadHlsStream) {
                            btnDownloadHlsStream.disabled = false;
                            btnDownloadHlsStream.innerText = '📥 Download Stream to MP4';
                        }
                        if (st.download_url && btnSaveMp4File) {
                            btnSaveMp4File.href = st.download_url;
                            btnSaveMp4File.setAttribute('download', st.filename || 'video.mp4');
                            if (hlsLinkContainer) hlsLinkContainer.classList.remove('hidden');
                        }
                    }
                }
            } catch (err) {}
        }, 1500);
    }

    const tgPipeCodeInput = document.getElementById('tg-pipe-code');
    const tgPipeTitleInput = document.getElementById('tg-pipe-title');
    const tgPipeUrlInput = document.getElementById('tg-pipe-url');
    const tgPipeFolderInput = document.getElementById('tg-pipe-folder');
    const btnRunTgPipe = document.getElementById('btn-run-tg-pipe');
    const tgPipeStatusBox = document.getElementById('tg-pipe-status-box');
    const tgPipeStatusText = document.getElementById('tg-pipe-status-text');
    const tgPipePercentText = document.getElementById('tg-pipe-percent');
    const tgPipeProgressBar = document.getElementById('tg-pipe-progress-bar');

    let tgPipePollInterval = null;

    if (btnRunTgPipe) {
        btnRunTgPipe.addEventListener('click', async (e) => {
            if (e) e.preventDefault();
            const code = tgPipeCodeInput ? tgPipeCodeInput.value.trim().toUpperCase() : '';
            const title = tgPipeTitleInput ? tgPipeTitleInput.value.trim() : '';
            const url = tgPipeUrlInput ? tgPipeUrlInput.value.trim() : '';
            const folder_path = tgPipeFolderInput ? tgPipeFolderInput.value.trim() : 'Main Lectures';

            if (!code || !title || !url) {
                alert('Please fill in Course Passcode, Video Title, and Stream URL.');
                return;
            }

            btnRunTgPipe.disabled = true;
            btnRunTgPipe.innerText = 'Starting Automated Telegram Pipeline...';
            if (tgPipeStatusBox) tgPipeStatusBox.classList.remove('hidden');

            try {
                const res = await fetch('/api/admin/auto-telegram-stream', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Admin-Secret': currentAdminSecret
                    },
                    body: JSON.stringify({ code, title, url, folder_path })
                });
                const data = await res.json();

                if (data.success) {
                    pollTgPipeStatus();
                } else {
                    alert(`Pipeline error: ${data.error}`);
                    btnRunTgPipe.disabled = false;
                    btnRunTgPipe.innerText = '⚡ Auto-Upload to Telegram Cloud & Add to Course';
                }
            } catch (err) {
                alert(`Network error: ${err.message}`);
                btnRunTgPipe.disabled = false;
                btnRunTgPipe.innerText = '⚡ Auto-Upload to Telegram Cloud & Add to Course';
            }
        });
    }

    function pollTgPipeStatus() {
        if (tgPipePollInterval) clearInterval(tgPipePollInterval);
        tgPipePollInterval = setInterval(async () => {
            try {
                const res = await fetch('/api/admin/auto-telegram-status');
                const data = await res.json();

                if (data.success && data.status) {
                    const st = data.status;
                    if (tgPipeStatusText) tgPipeStatusText.innerText = st.status_text || 'Processing...';
                    if (tgPipePercentText) tgPipePercentText.innerText = `${st.percent || 0}%`;
                    if (tgPipeProgressBar) tgPipeProgressBar.style.width = `${st.percent || 0}%`;

                    if (!st.running) {
                        clearInterval(tgPipePollInterval);
                        if (btnRunTgPipe) {
                            btnRunTgPipe.disabled = false;
                            btnRunTgPipe.innerText = '⚡ Auto-Upload to Telegram Cloud & Add to Course';
                        }
                        if (st.percent === 100) {
                            alert(st.status_text || '🎉 Video successfully processed and added to Course!');
                            loadAdminData();
                        } else if (st.error) {
                            alert(`Pipeline Alert: ${st.error}`);
                        }
                    }
                }
            } catch (err) {}
        }, 1500);
    }

    const smtpEmailInput = document.getElementById('smtp-email');
    const smtpPassInput = document.getElementById('smtp-pass');
    const btnSaveEmailGateway = document.getElementById('btn-save-email-gateway');

    if (btnSaveEmailGateway) {
        btnSaveEmailGateway.addEventListener('click', async (e) => {
            if (e) e.preventDefault();
            const smtpEmail = smtpEmailInput ? smtpEmailInput.value.trim() : '';
            const smtpPass = smtpPassInput ? smtpPassInput.value.trim() : '';
            
            if (!smtpEmail || !smtpPass) {
                alert('Please enter both your Sender Gmail Address and Gmail App Password.');
                return;
            }

            btnSaveEmailGateway.disabled = true;
            btnSaveEmailGateway.innerText = 'Saving...';

            try {
                const res = await fetch('/api/admin/save-email-gateway', {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json',
                        'X-Admin-Secret': currentAdminSecret 
                    },
                    body: JSON.stringify({ smtp_email: smtpEmail, smtp_pass: smtpPass })
                });
                const data = await res.json();

                if (data.success) {
                    alert('Gmail / Email Gateway Settings saved successfully! Real OTP emails will now be sent directly to your Gmail inbox.');
                } else {
                    alert(`Failed to save Email Gateway: ${data.error}`);
                }
            } catch (err) {
                alert(`Error: ${err.message}`);
            } finally {
                btnSaveEmailGateway.disabled = false;
                btnSaveEmailGateway.innerText = '📧 Save Email Gateway Settings';
            }
        });
    }

    if (btnSaveSmsKey) {
        btnSaveSmsKey.addEventListener('click', async (e) => {
            if (e) e.preventDefault();
            const smsKey = smsApiKeyInput ? smsApiKeyInput.value.trim() : '';
            btnSaveSmsKey.disabled = true;
            btnSaveSmsKey.innerText = 'Saving...';

            try {
                const res = await fetch('/api/admin/save-sms-key', {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json',
                        'X-Admin-Secret': currentAdminSecret 
                    },
                    body: JSON.stringify({ sms_key: smsKey })
                });
                const data = await res.json();

                if (data.success) {
                    alert('SMS Gateway API Key saved successfully! Real SMS OTPs will now be dispatched to mobile numbers.');
                } else {
                    alert(`Failed to save SMS key: ${data.error}`);
                }
            } catch (err) {
                alert(`Error: ${err.message}`);
            } finally {
                btnSaveSmsKey.disabled = false;
                btnSaveSmsKey.innerText = '📱 Save SMS Gateway Key';
            }
        });
    }

    if (btnChangeAdminSecret) {
        btnChangeAdminSecret.addEventListener('click', async (e) => {
            if (e) e.preventDefault();
            const newSecret = newAdminSecretInput ? newAdminSecretInput.value.trim() : '';
            if (!newSecret || newSecret.length < 4) {
                alert('Please enter a new Admin Password (at least 4 characters).');
                return;
            }

            btnChangeAdminSecret.disabled = true;
            btnChangeAdminSecret.innerText = 'Updating...';

            try {
                const res = await fetch('/api/admin/change-secret', {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json',
                        'X-Admin-Secret': currentAdminSecret 
                    },
                    body: JSON.stringify({ new_secret: newSecret })
                });
                const data = await res.json();

                if (data.success) {
                    currentAdminSecret = newSecret;
                    sessionStorage.setItem('admin_secret', newSecret);
                    localStorage.setItem('admin_secret', newSecret);
                    if (newAdminSecretInput) newAdminSecretInput.value = '';
                    alert('Admin Master Password updated successfully! Use your new password to log in next time.');
                } else {
                    alert(`Failed to update password: ${data.error}`);
                }
            } catch (err) {
                alert(`Error: ${err.message}`);
            } finally {
                btnChangeAdminSecret.disabled = false;
                btnChangeAdminSecret.innerText = '🔒 Update Admin Password';
            }
        });
    }

    function renderPasscodesTable(codesObj) {
        const entries = Object.entries(codesObj);
        if (passcodeCountBadge) passcodeCountBadge.innerText = `${entries.length} Active Codes`;

        if (!passcodesTbody) return;
        if (entries.length === 0) {
            passcodesTbody.innerHTML = `
                <tr class="empty-row">
                    <td colspan="5" style="text-align: center; padding: 30px; color: #9ca3af;">
                        🔑 No student access passcodes created yet.
                    </td>
                </tr>`;
            return;
        }

        let html = '';
        entries.forEach(([code, details]) => {
            const cat = details.category || 'IAT & NEST';
            const scope = details.access_scope || 'all';
            const isCustom = details.type === 'custom' || cat !== 'IAT & NEST';
            const pdfCount = isCustom ? (details.custom_pdfs ? details.custom_pdfs.length : 0) : 'Classplus Auto';
            const vidCount = details.custom_videos ? details.custom_videos.length : 0;

            let scopeBadge = '<span style="background:rgba(16,185,129,0.2); color:#34d399; font-size:0.7rem; padding:1px 6px; border-radius:3px; margin-left:4px;">🌟 All</span>';
            if (scope === 'pdf') {
                scopeBadge = '<span style="background:rgba(59,130,246,0.2); color:#60a5fa; font-size:0.7rem; padding:1px 6px; border-radius:3px; margin-left:4px;">📄 PDF Only</span>';
            } else if (scope === 'video') {
                scopeBadge = '<span style="background:rgba(236,72,153,0.2); color:#f472b6; font-size:0.7rem; padding:1px 6px; border-radius:3px; margin-left:4px;">🎥 Video Only</span>';
            }

            let pdfItemsHtml = '';
            if (details.custom_pdfs && details.custom_pdfs.length > 0) {
                pdfItemsHtml = details.custom_pdfs.map((pdf, idx) => `
                    <div style="display:flex; justify-content:space-between; align-items:center; background:rgba(255,255,255,0.05); padding:2px 6px; border-radius:4px; margin-top:2px; font-size:0.75rem;">
                        <span style="overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:140px;" title="${escapeHtml(pdf.url)}">📄 ${escapeHtml(pdf.title)}</span>
                        <button class="btn-del-custom-pdf" data-code="${escapeHtml(code)}" data-index="${idx}" style="background:none; border:none; color:#f87171; cursor:pointer; font-size:0.75rem; padding:0 4px;" title="Delete this PDF">✖</button>
                    </div>
                `).join('');
            }

            let vidItemsHtml = '';
            if (details.custom_videos && details.custom_videos.length > 0) {
                vidItemsHtml = details.custom_videos.map((vid, idx) => `
                    <div style="display:flex; justify-content:space-between; align-items:center; background:rgba(255,255,255,0.05); padding:2px 6px; border-radius:4px; margin-top:2px; font-size:0.75rem;">
                        <span style="overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:140px;" title="${escapeHtml(vid.url)}">🎥 ${escapeHtml(vid.title)}</span>
                        <button class="btn-del-custom-vid" data-code="${escapeHtml(code)}" data-index="${idx}" style="background:none; border:none; color:#f87171; cursor:pointer; font-size:0.75rem; padding:0 4px;" title="Delete this Video">✖</button>
                    </div>
                `).join('');
            }

            html += `
                <tr>
                    <td>
                        <span class="code-tag">${escapeHtml(code)}</span>${scopeBadge}
                        <div style="font-size:0.75rem; color:#9ca3af; margin-top:3px;">${escapeHtml(cat)}</div>
                    </td>
                    <td><code>${escapeHtml(details.course_id || 'N/A')}</code></td>
                    <td>${escapeHtml(details.course_name || '--')}</td>
                    <td>
                        <div style="display:flex; gap:4px; flex-direction:column;">
                            <span style="background:rgba(139,92,246,0.2); color:#c084fc; padding:2px 8px; border-radius:4px; font-size:0.8rem;">📄 ${pdfCount} PDFs</span>
                            ${pdfItemsHtml}
                            <span style="background:rgba(236,72,153,0.2); color:#f472b6; padding:2px 8px; border-radius:4px; font-size:0.8rem; margin-top:4px;">🎥 ${vidCount} Videos</span>
                            ${vidItemsHtml}
                        </div>
                    </td>
                    <td style="text-align: center;">
                        <button class="btn btn-danger delete-btn btn-delete-code" data-code="${escapeHtml(code)}" style="padding: 6px 12px; font-size: 0.8rem;">
                            🗑️ Delete Passcode
                        </button>
                    </td>
                </tr>`;
        });
        passcodesTbody.innerHTML = html;

        document.querySelectorAll('.btn-del-custom-pdf').forEach(btn => {
            btn.addEventListener('click', async () => {
                const code = btn.getAttribute('data-code');
                const idx = btn.getAttribute('data-index');
                if (confirm(`Delete this PDF from passcode '${code}'?`)) {
                    await fetch('/api/admin/delete-custom-pdf', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json', 'X-Admin-Secret': currentAdminSecret },
                        body: JSON.stringify({ code, index: idx })
                    });
                    loadAdminData();
                }
            });
        });

        document.querySelectorAll('.btn-del-custom-vid').forEach(btn => {
            btn.addEventListener('click', async () => {
                const code = btn.getAttribute('data-code');
                const idx = btn.getAttribute('data-index');
                if (confirm(`Delete this Video from passcode '${code}'?`)) {
                    await fetch('/api/admin/delete-custom-video', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json', 'X-Admin-Secret': currentAdminSecret },
                        body: JSON.stringify({ code, index: idx })
                    });
                    loadAdminData();
                }
            });
        });

        document.querySelectorAll('.btn-delete-code').forEach(btn => {
            btn.addEventListener('click', async () => {
                const codeToDelete = btn.getAttribute('data-code');
                if (confirm(`Are you sure you want to delete passcode '${codeToDelete}'?`)) {
                    try {
                        const res = await fetch('/api/admin/delete-code', {
                            method: 'POST',
                            headers: { 
                                'Content-Type': 'application/json',
                                'X-Admin-Secret': currentAdminSecret 
                            },
                            body: JSON.stringify({ code: codeToDelete })
                        });
                        const data = await res.json();
                        if (data.success) {
                            loadAdminData();
                        } else {
                            alert(`Error deleting passcode: ${data.error}`);
                        }
                    } catch (err) {
                        alert(`Network error: ${err.message}`);
                    }
                }
            });
        });
    }

    function renderStudentsTable(sessions, blockedIps) {
        if (!studentsTbody) return;
        const nowTs = Date.now() / 1000;
        let onlineCount = 0;

        if (sessions.length === 0) {
            studentsTbody.innerHTML = `
                <tr class="empty-row">
                    <td colspan="6" style="text-align: center; padding: 30px; color: #9ca3af;">
                        👥 No student sessions recorded yet.
                    </td>
                </tr>`;
            if (studentCountBadge) studentCountBadge.innerText = `0 Online`;
            return;
        }

        let html = '';
        sessions.forEach(s => {
            const isOnline = (nowTs - (s.last_ping || 0)) < 30;
            if (isOnline) onlineCount++;

            const isBlocked = blockedIps.includes(s.ip);
            let statusBadge = isOnline 
                ? '<span style="background:rgba(16,185,129,0.2); color:#34d399; font-size:0.75rem; padding:2px 8px; border-radius:4px;">🟢 Online</span>'
                : '<span style="background:rgba(156,163,175,0.2); color:#9ca3af; font-size:0.75rem; padding:2px 8px; border-radius:4px;">⚪ Offline</span>';

            if (isBlocked) {
                statusBadge = '<span style="background:rgba(239,68,68,0.2); color:#f87171; font-size:0.75rem; padding:2px 8px; border-radius:4px;">🚫 Blocked</span>';
            }

            const pdfsList = (s.clicked_pdfs && s.clicked_pdfs.length > 0)
                ? s.clicked_pdfs.map(p => `<span style="display:inline-block; background:rgba(255,255,255,0.06); font-size:0.75rem; padding:2px 6px; border-radius:4px; margin:2px;">📄 ${escapeHtml(p)}</span>`).join('')
                : '<span style="font-size:0.75rem; color:#6b7280;">No clicks yet</span>';

            html += `
                <tr>
                    <td>
                        <strong>${escapeHtml(s.name || 'Anonymous')}</strong>
                        <div style="margin-top:2px;">${statusBadge}</div>
                    </td>
                    <td><span class="code-tag" style="font-size:0.8rem;">${escapeHtml(s.passcode)}</span></td>
                    <td><code>${escapeHtml(s.ip)}</code></td>
                    <td style="font-size:0.8rem; color:#9ca3af;">${escapeHtml(s.time || '--')}</td>
                    <td>${pdfsList}</td>
                    <td style="text-align: center;">
                        <div style="display:flex; gap:4px; justify-content:center; flex-wrap:wrap;">
                            <button class="btn btn-secondary action-btn btn-force-logout" data-ip="${escapeHtml(s.ip)}" data-code="${escapeHtml(s.passcode)}" style="background:rgba(245,158,11,0.2); color:#fbbf24; border:1px solid rgba(245,158,11,0.4); padding:4px 8px; font-size:0.75rem;">
                                🚪 Logout
                            </button>
                            ${isBlocked ? `
                                <button class="btn btn-secondary action-btn btn-unblock-ip" data-ip="${escapeHtml(s.ip)}" style="background:rgba(16,185,129,0.2); color:#34d399; border:1px solid rgba(16,185,129,0.4); padding:4px 8px; font-size:0.75rem;">
                                    🟢 Unblock
                                </button>
                            ` : `
                                <button class="btn btn-danger action-btn btn-block-ip" data-ip="${escapeHtml(s.ip)}" style="padding:4px 8px; font-size:0.75rem;">
                                    🚫 Block IP
                                </button>
                            `}
                        </div>
                    </td>
                </tr>`;
        });

        studentsTbody.innerHTML = html;
        if (studentCountBadge) studentCountBadge.innerText = `${onlineCount} Online`;

        document.querySelectorAll('.btn-force-logout').forEach(btn => {
            btn.addEventListener('click', async () => {
                const ip = btn.getAttribute('data-ip');
                const pCode = btn.getAttribute('data-code');
                try {
                    const res = await fetch('/api/admin/force-logout', {
                        method: 'POST',
                        headers: { 
                            'Content-Type': 'application/json',
                            'X-Admin-Secret': currentAdminSecret 
                        },
                        body: JSON.stringify({ ip, passcode: pCode })
                    });
                    const data = await res.json();
                    if (data.success) {
                        loadAdminData();
                        alert(`Force logged out student at IP ${ip}`);
                    }
                } catch (err) {
                    alert(`Error: ${err.message}`);
                }
            });
        });

        document.querySelectorAll('.btn-block-ip').forEach(btn => {
            btn.addEventListener('click', async () => {
                const ip = btn.getAttribute('data-ip');
                if (confirm(`Block IP ${ip} from accessing the portal?`)) {
                    try {
                        const res = await fetch('/api/admin/block-ip', {
                            method: 'POST',
                            headers: { 
                                'Content-Type': 'application/json',
                                'X-Admin-Secret': currentAdminSecret 
                            },
                            body: JSON.stringify({ ip })
                        });
                        const data = await res.json();
                        if (data.success) loadAdminData();
                    } catch (err) {
                        alert(`Error: ${err.message}`);
                    }
                }
            });
        });

        document.querySelectorAll('.btn-unblock-ip').forEach(btn => {
            btn.addEventListener('click', async () => {
                const ip = btn.getAttribute('data-ip');
                try {
                    const res = await fetch('/api/admin/unblock-ip', {
                        method: 'POST',
                        headers: { 
                            'Content-Type': 'application/json',
                            'X-Admin-Secret': currentAdminSecret 
                        },
                        body: JSON.stringify({ ip })
                    });
                    const data = await res.json();
                    if (data.success) loadAdminData();
                } catch (err) {
                    alert(`Error: ${err.message}`);
                }
            });
        });
    }

    function escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
});
