document.addEventListener('DOMContentLoaded', () => {
    const adminTokenInput = document.getElementById('admin-token');
    const btnSaveToken = document.getElementById('btn-save-token');

    const passcodeCodeInput = document.getElementById('passcode-code');
    const passcodeCourseIdInput = document.getElementById('passcode-course-id');
    const passcodeCourseNameInput = document.getElementById('passcode-course-name');
    const btnCreateCode = document.getElementById('btn-create-code');

    const passcodeCountBadge = document.getElementById('passcode-count-badge');
    const passcodesTbody = document.getElementById('passcodes-tbody');

    // Load initial data
    loadAdminData();

    btnSaveToken.addEventListener('click', async () => {
        const token = adminTokenInput.value.trim();
        if (!token) {
            alert('Please paste a Classplus Access Token.');
            return;
        }

        btnSaveToken.disabled = true;
        btnSaveToken.innerText = 'Saving...';

        try {
            const res = await fetch('/api/admin/save-token', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
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

    const passcodeCategorySelect = document.getElementById('passcode-category');
    const customPdfCodeInput = document.getElementById('custom-pdf-code');
    const customPdfTitleInput = document.getElementById('custom-pdf-title');
    const customPdfFolderInput = document.getElementById('custom-pdf-folder');
    const customPdfUrlInput = document.getElementById('custom-pdf-url');
    const btnAddCustomPdf = document.getElementById('btn-add-custom-pdf');

    btnCreateCode.addEventListener('click', async () => {
        const code = passcodeCodeInput.value.trim().toUpperCase();
        const courseId = passcodeCourseIdInput.value.trim();
        const category = passcodeCategorySelect.value;
        const type = (category === 'IAT & NEST') ? 'classplus' : 'custom';
        const courseName = passcodeCourseNameInput.value.trim() || `${category} Course (${code})`;

        if (!code) {
            alert('Please enter a Student Passcode.');
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
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ code, course_id: courseId, course_name: courseName, category, type })
            });
            const data = await res.json();

            if (data.success) {
                passcodeCodeInput.value = '';
                passcodeCourseIdInput.value = '';
                passcodeCourseNameInput.value = '';
                loadAdminData();
                alert(`Passcode '${code}' for category [${category}] created successfully!`);
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

    btnAddCustomPdf.addEventListener('click', async () => {
        const code = customPdfCodeInput.value.trim().toUpperCase();
        const title = customPdfTitleInput.value.trim();
        const folder_path = customPdfFolderInput.value.trim() || 'Main Directory';
        const url = customPdfUrlInput.value.trim();

        if (!code || !title || !url) {
            alert('Please enter Target Passcode, Document Title, and Direct PDF URL.');
            return;
        }

        btnAddCustomPdf.disabled = true;
        btnAddCustomPdf.innerText = 'Adding PDF...';

        try {
            const res = await fetch('/api/admin/add-custom-pdf', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ code, title, folder_path, url })
            });
            const data = await res.json();

            if (data.success) {
                customPdfTitleInput.value = '';
                customPdfUrlInput.value = '';
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
    const customVidCodeInput = document.getElementById('custom-vid-code');
    const customVidTitleInput = document.getElementById('custom-vid-title');
    const customVidFolderInput = document.getElementById('custom-vid-folder');
    const customVidUrlInput = document.getElementById('custom-vid-url');
    const btnAddCustomVid = document.getElementById('btn-add-custom-vid');

    if (btnAddCustomVid) {
        btnAddCustomVid.addEventListener('click', async () => {
            const code = customVidCodeInput.value.trim().toUpperCase();
            const title = customVidTitleInput.value.trim();
            const folder_path = customVidFolderInput.value.trim() || 'Main Lectures';
            const url = customVidUrlInput.value.trim();

            if (!code || !title || !url) {
                alert('Please enter Target Passcode, Video Title, and Video Stream / YouTube URL.');
                return;
            }

            btnAddCustomVid.disabled = true;
            btnAddCustomVid.innerText = 'Adding Video...';

            try {
                const res = await fetch('/api/admin/add-custom-video', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ code, title, folder_path, url })
                });
                const data = await res.json();

                if (data.success) {
                    customVidTitleInput.value = '';
                    customVidUrlInput.value = '';
                    loadAdminData();
                    alert(`Video '${title}' added successfully to passcode '${code}'!`);
                } else {
                    alert(`Failed to add Video: ${data.error}`);
                }
            } catch (err) {
                alert(`Error: ${err.message}`);
            } finally {
                btnAddCustomVid.disabled = false;
                btnAddCustomVid.innerText = '🎥 Add Video Lecture to Passcode';
            }
        });
    }

    const activeStudentsBadge = document.getElementById('active-students-badge');
    const studentsTbody = document.getElementById('students-tbody');

    // Auto-refresh live student sessions every 5 seconds
    setInterval(loadAdminData, 5000);

    async function loadAdminData() {
        try {
            const res = await fetch('/api/admin/get-data');
            const data = await res.json();

            if (data.success) {
                if (data.admin_token && document.activeElement !== adminTokenInput) {
                    adminTokenInput.value = data.admin_token;
                }
                renderPasscodesTable(data.access_codes || {});
                renderStudentsTable(data.student_sessions || [], data.blocked_ips || []);
            }
        } catch (err) {
            console.error('Error loading admin data:', err);
        }
    }

    function renderPasscodesTable(codesObj) {
        const entries = Object.entries(codesObj);
        passcodeCountBadge.innerText = `${entries.length} Active Codes`;

        if (entries.length === 0) {
            passcodesTbody.innerHTML = `
                <tr class="empty-row">
                    <td colspan="5" style="text-align: center; padding: 30px; color: #9ca3af;">
                        🔑 No student access passcodes created yet. Fill the form on the left to create one!
                    </td>
                </tr>`;
            return;
        }

        let html = '';
        entries.forEach(([code, details]) => {
            const cat = details.category || 'IAT & NEST';
            const isCustom = details.type === 'custom' || cat !== 'IAT & NEST';
            const pdfCount = isCustom ? (details.custom_pdfs ? details.custom_pdfs.length : 0) : 'Classplus Auto';
            const vidCount = details.custom_videos ? details.custom_videos.length : 0;

            html += `
                <tr>
                    <td>
                        <span class="code-tag">${escapeHtml(code)}</span>
                        <div style="font-size:0.75rem; color:#9ca3af; margin-top:3px;">${escapeHtml(cat)}</div>
                    </td>
                    <td><code>${escapeHtml(details.course_id || 'N/A')}</code></td>
                    <td>${escapeHtml(details.course_name || '--')}</td>
                    <td>
                        <div style="display:flex; gap:4px; flex-direction:column;">
                            <span style="background:rgba(139,92,246,0.2); color:#c084fc; padding:2px 8px; border-radius:4px; font-size:0.8rem;">📄 ${pdfCount} PDFs</span>
                            <span style="background:rgba(236,72,153,0.2); color:#f472b6; padding:2px 8px; border-radius:4px; font-size:0.8rem;">🎥 ${vidCount} Videos</span>
                        </div>
                    </td>
                    <td style="text-align: center;">
                        <button class="btn btn-danger btn-delete-code" data-code="${escapeHtml(code)}">
                            🗑️ Delete
                        </button>
                    </td>
                </tr>`;
        });
        passcodesTbody.innerHTML = html;

        document.querySelectorAll('.btn-delete-code').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const codeToDelete = e.target.getAttribute('data-code');
                if (!confirm(`Are you sure you want to delete passcode '${codeToDelete}'?`)) return;

                try {
                    const res = await fetch('/api/admin/delete-code', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ code: codeToDelete })
                    });
                    const data = await res.json();
                    if (data.success) {
                        loadAdminData();
                    } else {
                        alert(`Error deleting passcode: ${data.error}`);
                    }
                } catch (err) {
                    alert(`Error: ${err.message}`);
                }
            });
        });
    }

    function renderStudentsTable(sessionsList, blockedIpsList) {
        let onlineCount = 0;
        sessionsList.forEach(s => {
            if (s.is_online && !blockedIpsList.includes(s.ip)) onlineCount++;
        });

        activeStudentsBadge.innerText = `${onlineCount} Online | ${sessionsList.length} Total Sessions`;

        if (sessionsList.length === 0) {
            studentsTbody.innerHTML = `
                <tr class="empty-row">
                    <td colspan="7" style="text-align: center; padding: 30px; color: #9ca3af;">
                        📡 No student activity recorded yet. When students enter their passcode, their name and IP will appear here live!
                    </td>
                </tr>`;
            return;
        }

        let html = '';
        sessionsList.forEach(s => {
            const isBlocked = blockedIpsList.includes(s.ip);
            let statusLabel = '';

            if (isBlocked) {
                statusLabel = '<span style="color:#ef4444; font-weight:600; background:rgba(239,68,68,0.15); padding:3px 8px; border-radius:4px;">🚫 Blocked</span>';
            } else if (s.is_online) {
                statusLabel = '<span style="color:#34d399; font-weight:600; background:rgba(52,211,153,0.15); padding:3px 8px; border-radius:4px;">🟢 Online</span>';
            } else {
                statusLabel = '<span style="color:#9ca3af; font-weight:500; background:rgba(156,163,175,0.15); padding:3px 8px; border-radius:4px;">🔴 Offline</span>';
            }

            const clickCount = s.clicks_count || 0;
            const clickedList = Array.isArray(s.clicked_pdfs) ? s.clicked_pdfs : [];
            const clickedTooltip = clickedList.length > 0 ? clickedList.join('\n• ') : 'No PDFs clicked yet';
            const clickDisplay = `<div title="Downloaded PDFs:\n• ${escapeHtml(clickedTooltip)}">
                <span style="background:rgba(59,130,246,0.2); color:#60a5fa; font-weight:600; padding:2px 8px; border-radius:4px; font-size:0.85rem;">
                    📥 ${clickCount} Downloads
                </span>
                ${clickedList.length > 0 ? `<div style="font-size:0.75rem; color:#9ca3af; margin-top:3px; max-width:180px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${escapeHtml(clickedList[clickedList.length-1])}</div>` : ''}
            </div>`;

            html += `
                <tr>
                    <td><b>${escapeHtml(s.name)}</b></td>
                    <td><span class="code-tag">${escapeHtml(s.passcode)}</span></td>
                    <td><code>${escapeHtml(s.ip)}</code></td>
                    <td>${statusLabel}</td>
                    <td>${clickDisplay}</td>
                    <td><small style="color:#9ca3af;">${escapeHtml(s.time)}</small></td>
                    <td style="text-align: center;">
                        <div style="display:flex; gap:6px; justify-content:center;">
                            <button class="btn btn-secondary btn-force-logout" data-ip="${escapeHtml(s.ip)}" data-passcode="${escapeHtml(s.passcode)}" data-name="${escapeHtml(s.name)}" style="background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4); padding: 4px 8px; font-size: 0.8rem;">
                                🚪 Logout
                            </button>
                            ${isBlocked ? 
                                `<button class="btn btn-secondary btn-unblock-ip" data-ip="${escapeHtml(s.ip)}" data-name="${escapeHtml(s.name)}" style="background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid #10b981; padding: 4px 8px; font-size: 0.8rem;">
                                    🟢 Unblock
                                </button>` : 
                                `<button class="btn btn-danger btn-block-ip" data-ip="${escapeHtml(s.ip)}" data-name="${escapeHtml(s.name)}" style="padding: 4px 8px; font-size: 0.8rem;">
                                    🚫 Block
                                </button>`
                            }
                        </div>
                    </td>
                </tr>`;
        });
        studentsTbody.innerHTML = html;

        document.querySelectorAll('.btn-force-logout').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const ipToLogout = e.target.getAttribute('data-ip');
                const pCode = e.target.getAttribute('data-passcode');
                const studentName = e.target.getAttribute('data-name');

                if (!confirm(`Force logout student '${studentName}' (${ipToLogout})?`)) return;

                try {
                    const res = await fetch('/api/admin/force-logout', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ ip: ipToLogout, passcode: pCode })
                    });
                    const data = await res.json();
                    if (data.success) {
                        alert(`Student '${studentName}' has been FORCE LOGGED OUT!`);
                        loadAdminData();
                    } else {
                        alert(`Error: ${data.error}`);
                    }
                } catch (err) {
                    alert(`Error: ${err.message}`);
                }
            });
        });

        document.querySelectorAll('.btn-block-ip').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const ipToBlock = e.target.getAttribute('data-ip');
                const studentName = e.target.getAttribute('data-name');

                if (!confirm(`Are you sure you want to BLOCK student '${studentName}' (${ipToBlock}) from accessing all materials?`)) return;

                try {
                    const res = await fetch('/api/admin/block-ip', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ ip: ipToBlock })
                    });
                    const data = await res.json();
                    if (data.success) {
                        loadAdminData();
                    } else {
                        alert(`Error: ${data.error}`);
                    }
                } catch (err) {
                    alert(`Error: ${err.message}`);
                }
            });
        });

        document.querySelectorAll('.btn-unblock-ip').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const ipToUnblock = e.target.getAttribute('data-ip');
                const studentName = e.target.getAttribute('data-name');

                if (!confirm(`Unblock student '${studentName}' (${ipToUnblock})?`)) return;

                try {
                    const res = await fetch('/api/admin/unblock-ip', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ ip: ipToUnblock })
                    });
                    const data = await res.json();
                    if (data.success) {
                        alert(`Student '${studentName}' (${ipToUnblock}) UNBLOCKED successfully!`);
                        loadAdminData();
                    } else {
                        alert(`Error: ${data.error}`);
                    }
                } catch (err) {
                    alert(`Error: ${err.message}`);
                }
            });
        });
    }

    function escapeHtml(str) {
        return (str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
});
