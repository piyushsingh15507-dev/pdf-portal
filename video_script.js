document.addEventListener('DOMContentLoaded', () => {
    // Disable context menu (right click)
    document.addEventListener('contextmenu', e => e.preventDefault());

    // Anti-Debugging Keyboard Blockers (F12, Ctrl+Shift+I/J/C, Ctrl+U, Ctrl+S)
    document.addEventListener('keydown', e => {
        if (
            e.keyCode === 123 || 
            (e.ctrlKey && e.shiftKey && (e.keyCode === 73 || e.keyCode === 74 || e.keyCode === 67)) || 
            (e.ctrlKey && (e.keyCode === 85 || e.keyCode === 83))
        ) {
            e.preventDefault();
            return false;
        }
    });

    const loginSection = document.getElementById('login-section');
    const dashboardSection = document.getElementById('dashboard-section');
    const passcodeInput = document.getElementById('student-passcode');
    const studentNameInput = document.getElementById('student-name');
    const btnUnlock = document.getElementById('btn-unlock');
    const loginError = document.getElementById('login-error');
    const courseTitleDisplay = document.getElementById('course-title-display');
    const accessCodeBadge = document.getElementById('access-code-badge');
    const categoryBadge = document.getElementById('category-badge');
    const btnChangeCode = document.getElementById('btn-change-code');
    const btnLogout = document.getElementById('btn-logout');

    const videoGrid = document.getElementById('video-grid');
    const videoSearchInput = document.getElementById('video-search-input');
    const videoPlayerModal = document.getElementById('video-player-modal');
    const videoModalTitle = document.getElementById('video-modal-title');
    const videoIframe = document.getElementById('video-iframe');
    const btnCloseVideo = document.getElementById('btn-close-video');
    const videoWatermark = document.getElementById('video-watermark');

    let currentVideos = [];
    let heartbeatTimer = null;
    const FOUR_DAYS_MS = 4 * 24 * 60 * 60 * 1000;

    // Check if passcode and name are saved in localStorage (with 4-day expiry)
    const savedPasscode = localStorage.getItem('student_passcode');
    const savedName = localStorage.getItem('student_name');
    const savedTime = localStorage.getItem('student_login_time');
    const now = Date.now();

    if (savedPasscode && savedName) {
        if (savedTime && (now - parseInt(savedTime)) > FOUR_DAYS_MS) {
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
        closeVideoPlayer();
    }

    function showError(msg) {
        loginError.innerText = msg;
        loginError.classList.remove('hidden');
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
        if (e.key === 'Enter') btnUnlock.click();
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

    async function unlockMaterials(passcode, name) {
        loginError.classList.add('hidden');
        const spinner = btnUnlock.querySelector('.spinner');
        const btnText = btnUnlock.querySelector('.btn-text');

        spinner.classList.remove('hidden');
        btnUnlock.disabled = true;
        btnText.innerText = '⚡ Loading Lectures...';

        try {
            const res = await fetch('/api/student/access', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ passcode, name, portal_type: 'video' })
            });
            const data = await res.json();

            if (data.success && (Array.isArray(data.videos) || Array.isArray(data.pdfs))) {
                localStorage.setItem('student_passcode', passcode);
                localStorage.setItem('student_name', name);
                localStorage.setItem('student_login_time', Date.now().toString());

                sessionStorage.setItem('student_passcode', passcode);
                sessionStorage.setItem('student_name', name);
                currentVideos = data.videos || [];
                
                courseTitleDisplay.innerText = data.course_name ? `🎥 ${data.course_name}` : '🎥 Course Video Lectures';
                accessCodeBadge.innerText = `Student: ${name} | Code: ${passcode}`;

                if (categoryBadge) {
                    categoryBadge.innerText = `Category: ${data.category || 'IAT & NEST'}`;
                }

                renderVideoGrid(currentVideos);

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
            btnText.innerText = 'Unlock Videos';
            btnUnlock.disabled = false;
        }
    }

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

    function closeVideoPlayer() {
        if (videoPlayerModal) {
            videoPlayerModal.classList.add('hidden');
            if (videoIframe) videoIframe.src = '';
        }
    }

    if (btnCloseVideo) btnCloseVideo.addEventListener('click', closeVideoPlayer);
    if (videoPlayerModal) {
        videoPlayerModal.addEventListener('click', (e) => {
            if (e.target === videoPlayerModal) closeVideoPlayer();
        });
    }
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeVideoPlayer();
    });

    function escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function renderVideoGrid(list) {
        if (!videoGrid) return;

        if (!list || list.length === 0) {
            videoGrid.innerHTML = `
                <div style="grid-column: 1 / -1; text-align: center; padding: 40px; color: #9ca3af; background: rgba(15, 23, 42, 0.5); border-radius: 12px; border: 1px dashed rgba(255, 255, 255, 0.1);">
                    🎥 No video lectures added to this course passcode yet. Ask your instructor!
                </div>`;
            return;
        }

        let html = '';
        list.forEach((vid) => {
            const folderStr = vid.folder_path ? vid.folder_path : 'Main Lectures';
            html += `
                <div class="video-card" style="background: #0f172a; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 18px; display: flex; flex-direction: column; justify-content: space-between; transition: transform 0.2s, border-color 0.2s;">
                    <div>
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                            <span style="font-size: 1.8rem;">🎥</span>
                            <span style="background: rgba(236, 72, 153, 0.15); color: #f472b6; font-size: 0.78rem; padding: 4px 10px; border-radius: 12px; font-weight: 500;">
                                ${escapeHtml(folderStr)}
                            </span>
                        </div>
                        <h4 style="font-size: 1.02rem; color: #f3f4f6; font-weight: 600; margin-bottom: 8px; line-height: 1.4;">
                            ${escapeHtml(vid.title)}
                        </h4>
                    </div>
                    <button class="btn btn-primary btn-play-video" data-title="${escapeHtml(vid.title)}" data-url="${escapeHtml(vid.url)}" style="margin-top: 16px; width: 100%; background: linear-gradient(135deg, #ec4899, #8b5cf6); padding: 10px; font-size: 0.9rem; font-weight: 600;">
                        ▶️ Play Lecture
                    </button>
                </div>`;
        });
        videoGrid.innerHTML = html;

        document.querySelectorAll('.btn-play-video').forEach(btn => {
            btn.addEventListener('click', () => {
                const title = btn.getAttribute('data-title');
                const videoUrl = btn.getAttribute('data-url');
                const sName = localStorage.getItem('student_name') || sessionStorage.getItem('student_name') || 'Student';
                const pCode = localStorage.getItem('student_passcode') || sessionStorage.getItem('student_passcode') || '';

                if (videoWatermark) {
                    const todayStr = new Date().toLocaleDateString();
                    videoWatermark.innerText = `🛡️ PROTECTED | ${sName} | Code: ${pCode} | ${todayStr}`;
                }

                if (pCode && sName) {
                    fetch('/api/student/click', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ passcode: pCode, name: sName, pdf_title: `[VIDEO PLAY] ${title}` })
                    }).catch(() => {});
                }

                const formattedUrl = formatEmbedVideoUrl(videoUrl);

                if (videoModalTitle) videoModalTitle.innerHTML = `🎥 ${escapeHtml(title)}`;
                if (videoIframe) {
                    videoIframe.src = formattedUrl;
                }
                if (videoPlayerModal) videoPlayerModal.classList.remove('hidden');
            });
        });
    }

    function formatEmbedVideoUrl(rawUrl) {
        if (!rawUrl) return '';
        let url = rawUrl.trim();

        const ytRegex = /(?:youtube\.com\/(?:watch\?v=|live\/|embed\/|shorts\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})/;
        const match = url.match(ytRegex);

        if (match && match[1]) {
            const videoId = match[1];
            return `https://www.youtube.com/embed/${videoId}?autoplay=1&modestbranding=1&rel=0&iv_load_policy=3&controls=1&enablejsapi=1`;
        }

        return url;
    }

    if (videoSearchInput) {
        videoSearchInput.addEventListener('input', () => {
            const query = videoSearchInput.value.toLowerCase().trim();
            const filtered = currentVideos.filter(v => {
                return v.title.toLowerCase().includes(query) || (v.folder_path && v.folder_path.toLowerCase().includes(query));
            });
            renderVideoGrid(filtered);
        });
    }
});
