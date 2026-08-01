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

    btnCreateCode.addEventListener('click', async () => {
        const code = passcodeCodeInput.value.trim().toUpperCase();
        const courseId = passcodeCourseIdInput.value.trim();
        const courseName = passcodeCourseNameInput.value.trim() || `Course ${courseId}`;

        if (!code || !courseId) {
            alert('Please enter both a Student Passcode and a Target Course ID.');
            return;
        }

        btnCreateCode.disabled = true;
        btnCreateCode.innerText = 'Creating...';

        try {
            const res = await fetch('/api/admin/create-code', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ code, course_id: courseId, course_name: courseName })
            });
            const data = await res.json();

            if (data.success) {
                passcodeCodeInput.value = '';
                passcodeCourseIdInput.value = '';
                passcodeCourseNameInput.value = '';
                loadAdminData();
                alert(`Passcode '${code}' created successfully! Students can now access this course using code '${code}'.`);
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

    const activeStudentsBadge = document.getElementById('active-students-badge');
    const studentsTbody = document.getElementById('students-tbody');

    // Auto-refresh live student sessions every 5 seconds
    setInterval(loadAdminData, 5000);

    async function loadAdminData() {
        try {
            const res = await fetch('/api/admin/get-data');
            const data = await res.json();

            if (data.success) {
                if (data.admin_token) {
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
                    <td colspan="4" style="text-align: center; padding: 30px; color: #9ca3af;">
                        🔑 No student access passcodes created yet. Fill the form on the left to create one!
                    </td>
                </tr>`;
            return;
        }

        let html = '';
        entries.forEach(([code, details]) => {
            html += `
                <tr>
                    <td>
                        <span class="code-tag">${escapeHtml(code)}</span>
                    </td>
                    <td><code>${escapeHtml(details.course_id)}</code></td>
                    <td>${escapeHtml(details.course_name || '--')}</td>
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
        activeStudentsBadge.innerText = `${sessionsList.length} Connected Students`;

        if (sessionsList.length === 0) {
            studentsTbody.innerHTML = `
                <tr class="empty-row">
                    <td colspan="6" style="text-align: center; padding: 30px; color: #9ca3af;">
                        📡 No student activity recorded yet. When students enter their passcode, their name and IP will appear here live!
                    </td>
                </tr>`;
            return;
        }

        let html = '';
        sessionsList.forEach(s => {
            const isBlocked = blockedIpsList.includes(s.ip);
            const statusLabel = isBlocked ? 
                '<span style="color:#ef4444; font-weight:600;">🚫 Blocked</span>' : 
                '<span style="color:#34d399; font-weight:600;">🟢 Online</span>';

            html += `
                <tr>
                    <td><b>${escapeHtml(s.name)}</b></td>
                    <td><span class="code-tag">${escapeHtml(s.passcode)}</span></td>
                    <td><code>${escapeHtml(s.ip)}</code></td>
                    <td><small style="color:#9ca3af;">${escapeHtml(s.time)}</small></td>
                    <td>${statusLabel}</td>
                    <td style="text-align: center;">
                        ${isBlocked ? 
                            `<button class="btn btn-secondary btn-unblock-ip" data-ip="${escapeHtml(s.ip)}" data-name="${escapeHtml(s.name)}" style="background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid #10b981;">
                                🟢 Unblock Student
                            </button>` : 
                            `<button class="btn btn-danger btn-block-ip" data-ip="${escapeHtml(s.ip)}" data-name="${escapeHtml(s.name)}">
                                🚫 Block Student
                            </button>`
                        }
                    </td>
                </tr>`;
        });
        studentsTbody.innerHTML = html;

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
