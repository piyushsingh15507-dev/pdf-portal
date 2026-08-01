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

    async function loadAdminData() {
        try {
            const res = await fetch('/api/admin/get-data');
            const data = await res.json();

            if (data.success) {
                if (data.admin_token) {
                    adminTokenInput.value = data.admin_token;
                }
                renderPasscodesTable(data.access_codes || {});
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
                    <td colspan="4" style="text-align: center; padding: 40px; color: #9ca3af;">
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

        // Attach delete listeners
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

    function escapeHtml(str) {
        return (str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
});
