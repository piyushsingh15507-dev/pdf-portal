document.addEventListener("DOMContentLoaded", () => {
    try {
        const streamUrlInput = document.getElementById("stream-url");
        const btnFetch = document.getElementById("btn-fetch");
        const authTokenInput = document.getElementById("auth-token");
        const selectUserCourse = document.getElementById("select-user-course");
        const btnLoadCourses = document.getElementById("btn-load-courses");
        const courseIdInput = document.getElementById("course-id");
        const btnExplore = document.getElementById("btn-explore");
        const btnExportTxt = document.getElementById("btn-export-txt");
        const btnBatchDownload = document.getElementById("btn-batch-download");
        const qualitySection = document.getElementById("quality-section");
        const qualityList = document.getElementById("quality-list");
        const outputNameInput = document.getElementById("output-name");
        const outputFormatSelect = document.getElementById("output-format");
        const btnDownload = document.getElementById("btn-download");
        const btnCancel = document.getElementById("btn-cancel");
        const statusBadge = document.getElementById("status-badge");
        const progressRingBar = document.querySelector(".progress-ring-bar");
        const progressPercentage = document.getElementById("progress-percentage");
        const progressStatus = document.getElementById("progress-status");
        const consoleLogs = document.getElementById("console-logs");
        const btnCopyLogs = document.getElementById("btn-copy-logs");
        const courseExplorerCard = document.getElementById("course-explorer-card");
        const explorerPath = document.getElementById("explorer-path");
        const btnBackFolder = document.getElementById("btn-back-folder");
        const explorerList = document.getElementById("explorer-list");

        let selectedStreamUrl = "";
        let pollingInterval = null;
        let batchInterval = null;

        function addLogLine(text, type = "") {
            const div = document.createElement("div");
            div.className = "console-line";
            if (type) div.classList.add(type);
            else if (text.includes("[SYSTEM]")) div.classList.add("system");
            else if (text.includes("[ERROR]") || text.toLowerCase().includes("error")) div.classList.add("error");
            div.textContent = text;
            consoleLogs.appendChild(div);
            consoleLogs.scrollTop = consoleLogs.scrollHeight;
        }

        function setProgress(percent) {
            const circleRadius = 70;
            const circumference = 2 * Math.PI * circleRadius;
            const offset = circumference - (percent / 100) * circumference;
            if (progressRingBar) progressRingBar.style.strokeDashoffset = offset;
            if (progressPercentage) progressPercentage.textContent = `${percent}%`;
        }

        // Fetch stream info
        btnFetch.addEventListener("click", async () => {
            const url = streamUrlInput.value.trim();
            const token = authTokenInput.value.trim();

            if (!url) {
                alert("Please enter a Video URL, Encrypted Content ID, or Proxy Link.");
                return;
            }

            // Auto-detect if user pasted Access Token into URL box by mistake
            if (url.startsWith("eyJhbGci")) {
                authTokenInput.value = url;
                streamUrlInput.value = "";
                alert("Access Token detected! I have automatically saved it in the Access Token box above.\n\nNow please paste your Video Link or Content ID (U2FsdGVk...) in the link box.");
                btnFetch.disabled = false;
                return;
            }

            btnFetch.disabled = true;
            addLogLine(`[SYSTEM] Fetching stream information for: ${url.substring(0, 60)}...`);

            try {
                const res = await fetch("/api/fetch-info", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ url, token })
                });
                const data = await res.json();
                btnFetch.disabled = false;

                if (data.success && data.streams) {
                    qualityList.innerHTML = "";
                    data.streams.forEach((st, i) => {
                        const div = document.createElement("div");
                        div.style.cssText = "padding: 10px; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; cursor: pointer; margin-bottom: 6px;";
                        div.textContent = `▶ ${st.resolution} (Bitrate: ${st.bandwidth || 'Auto'})`;
                        div.addEventListener("click", () => {
                            document.querySelectorAll("#quality-list > div").forEach(d => d.style.borderColor = "rgba(255,255,255,0.1)");
                            div.style.borderColor = "#10b981";
                            selectedStreamUrl = st.url;
                            btnDownload.disabled = false;
                            addLogLine(`[SYSTEM] Selected resolution: ${st.resolution}`);
                        });
                        qualityList.appendChild(div);
                        if (i === 0) div.click();
                    });
                    qualitySection.classList.remove("hidden");
                } else {
                    alert(data.error || "Failed to fetch stream info.");
                }
            } catch (e) {
                btnFetch.disabled = false;
                alert(`Network error: ${e.message}`);
            }
        });

        // Download Video
        btnDownload.addEventListener("click", async () => {
            if (!selectedStreamUrl) {
                alert("Please select a video quality first.");
                return;
            }

            const filename = outputNameInput.value.trim() || "Classplus_Video";
            const format = outputFormatSelect.value || "mp4";

            btnDownload.disabled = true;
            addLogLine(`[SYSTEM] Starting download: ${filename}.${format}...`);

            try {
                const res = await fetch("/api/download", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ url: selectedStreamUrl, filename, format })
                });
                const data = await res.json();
                if (data.success) {
                    startStatusPolling();
                } else {
                    btnDownload.disabled = false;
                    alert(data.message || "Download failed to start.");
                }
            } catch (e) {
                btnDownload.disabled = false;
                alert(`Download error: ${e.message}`);
            }
        });

        function startStatusPolling() {
            if (pollingInterval) clearInterval(pollingInterval);
            pollingInterval = setInterval(async () => {
                try {
                    const res = await fetch("/api/status");
                    const data = await res.json();
                    if (data.logs) {
                        consoleLogs.innerHTML = "";
                        data.logs.split("\n").forEach(l => addLogLine(l));
                    }
                    setProgress(data.progress || 0);
                    if (data.status_text && progressStatus) progressStatus.textContent = data.status_text;

                    if (!data.running) {
                        clearInterval(pollingInterval);
                        btnDownload.disabled = false;
                    }
                } catch (e) {}
            }, 1000);
        }

        // Auto Course Discovery
        btnLoadCourses.addEventListener("click", async () => {
            const token = authTokenInput.value.trim();
            if (!token) {
                alert("Please enter your Access Token first.");
                return;
            }

            btnLoadCourses.textContent = "Loading...";
            try {
                const res = await fetch("/api/user-courses", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ token })
                });
                const data = await res.json();
                btnLoadCourses.textContent = "Auto-Find";

                if (data.success && data.courses) {
                    selectUserCourse.innerHTML = `<option value="">-- Select Course (${data.courses.length} Found) --</option>`;
                    data.courses.forEach(c => {
                        const opt = document.createElement("option");
                        opt.value = c.id || c.courseId;
                        opt.textContent = `${c.name} (ID: ${c.id || c.courseId})`;
                        selectUserCourse.appendChild(opt);
                    });
                    addLogLine(`[SYSTEM] Discovered ${data.courses.length} courses!`);
                } else {
                    alert(data.error || "Could not fetch courses.");
                }
            } catch (e) {
                btnLoadCourses.textContent = "Auto-Find";
                alert(`Error: ${e.message}`);
            }
        });

        selectUserCourse.addEventListener("change", () => {
            if (selectUserCourse.value) {
                courseIdInput.value = selectUserCourse.value;
            }
        });

        // Explore Course Folders
        btnExplore.addEventListener("click", () => {
            const token = authTokenInput.value.trim();
            const courseId = courseIdInput.value.trim();
            if (!token || !courseId) {
                alert("Please enter Access Token and Course ID first.");
                return;
            }
            fetchFolderContent("0", "Root");
        });

        let folderHistory = [];
        async function fetchFolderContent(folderId, folderName) {
            const token = authTokenInput.value.trim();
            const courseId = courseIdInput.value.trim();

            courseExplorerCard.classList.remove("hidden");
            explorerList.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: #94a3b8;">⏳ Loading contents...</div>`;

            try {
                const res = await fetch("/api/course-content", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ token, course_id: courseId, folder_id: folderId })
                });
                const resData = await res.json();

                if (resData.success) {
                    const dataObj = resData.data || {};
                    const items = dataObj.courseContent || dataObj.contents || [];
                    renderExplorerItems(items);

                    if (folderId !== "0" && folderName) {
                        if (folderHistory.length === 0 || folderHistory[folderHistory.length - 1].id !== folderId) {
                            folderHistory.push({ id: folderId, name: folderName });
                        }
                    }
                    explorerPath.textContent = "Root Path: /" + folderHistory.map(f => f.name).join("/");
                    btnBackFolder.disabled = folderHistory.length === 0;
                } else {
                    explorerList.innerHTML = `<div style="grid-column: 1/-1; color: #f87171;">${resData.error || "Error loading folder"}</div>`;
                }
            } catch (e) {
                explorerList.innerHTML = `<div style="grid-column: 1/-1; color: #f87171;">Network Error: ${e.message}</div>`;
            }
        }

        btnBackFolder.addEventListener("click", () => {
            folderHistory.pop();
            const prev = folderHistory[folderHistory.length - 1];
            fetchFolderContent(prev ? prev.id : "0", prev ? prev.name : "Root");
        });

        function renderExplorerItems(items) {
            explorerList.innerHTML = "";
            if (items.length === 0) {
                explorerList.innerHTML = `<div style="grid-column: 1/-1; color: #94a3b8;">Empty folder.</div>`;
                return;
            }

            items.forEach(item => {
                const ct = item.contentType || item.type || 0;
                const name = item.name || "Untitled";
                const id = item.id;
                const contentHashId = item.contentHashId || item.contentId || item.url || item.id || "";

                const el = document.createElement("div");
                el.style.cssText = "padding: 10px; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; cursor: pointer; display: flex; align-items: center; gap: 8px;";

                if (ct === 1) {
                    el.innerHTML = `<span>📁</span> <div><div style="font-weight: 600;">${name}</div><div style="font-size: 0.75rem; color: #94a3b8;">Folder</div></div>`;
                    el.addEventListener("click", () => fetchFolderContent(id.toString(), name));
                } else {
                    el.innerHTML = `<span>📹</span> <div><div style="font-weight: 600;">${name}</div><div style="font-size: 0.75rem; color: #94a3b8;">Video / Resource</div></div>`;
                    el.addEventListener("click", () => {
                        streamUrlInput.value = `https://api.classplusapp.com/cams/uploader/video/jw-signed-url?contentId=${contentHashId}`;
                        outputNameInput.value = name;
                        addLogLine(`[SYSTEM] Explorer selected video: "${name}"`);
                        btnFetch.click();
                    });
                }
                explorerList.appendChild(el);
            });
        }

        // Export Links to TXT
        btnExportTxt.addEventListener("click", async () => {
            const token = authTokenInput.value.trim();
            const courseId = courseIdInput.value.trim();

            if (!token || !courseId) {
                alert("Please enter Access Token and Course ID first.");
                return;
            }

            btnExportTxt.disabled = true;
            btnExportTxt.textContent = "Exporting...";

            try {
                const res = await fetch("/api/export-course-links", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ token, course_id: courseId })
                });
                const data = await res.json();
                btnExportTxt.disabled = false;
                btnExportTxt.textContent = "📄 Export Links (.txt)";

                if (data.success) {
                    addLogLine(`[SYSTEM] Exported ${data.total_videos} video links to ${data.filename}!`);
                    const blob = new Blob([data.content], { type: "text/plain;charset=utf-8" });
                    const link = document.createElement("a");
                    link.href = URL.createObjectURL(blob);
                    link.download = data.filename;
                    link.click();
                } else {
                    alert(data.error || "Export failed.");
                }
            } catch (e) {
                btnExportTxt.disabled = false;
                btnExportTxt.textContent = "📄 Export Links (.txt)";
                alert(`Export error: ${e.message}`);
            }
        });

        // Batch Download
        btnBatchDownload.addEventListener("click", async () => {
            const token = authTokenInput.value.trim();
            const courseId = courseIdInput.value.trim();

            if (!token || !courseId) {
                alert("Please enter Access Token and Course ID first.");
                return;
            }

            if (!confirm(`Start batch download for Course ${courseId}?`)) return;

            btnBatchDownload.disabled = true;
            try {
                const res = await fetch("/api/batch-download", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ token, course_id: courseId, format: outputFormatSelect.value })
                });
                const data = await res.json();
                if (data.success) {
                    startBatchPolling();
                } else {
                    btnBatchDownload.disabled = false;
                    alert(data.error || "Batch start failed.");
                }
            } catch (e) {
                btnBatchDownload.disabled = false;
                alert(`Error: ${e.message}`);
            }
        });

        function startBatchPolling() {
            if (batchInterval) clearInterval(batchInterval);
            batchInterval = setInterval(async () => {
                try {
                    const res = await fetch("/api/batch-status");
                    const status = await res.json();
                    if (status.status_text && progressStatus) progressStatus.textContent = status.status_text;
                    if (status.total_videos > 0) {
                        setProgress(Math.round((status.current_index / status.total_videos) * 100));
                    }
                    if (!status.running) {
                        clearInterval(batchInterval);
                        btnBatchDownload.disabled = false;
                    }
                } catch (e) {}
            }, 2000);
        }

        // Copy Logs
        btnCopyLogs.addEventListener("click", () => {
            navigator.clipboard.writeText(consoleLogs.innerText).then(() => {
                btnCopyLogs.textContent = "Copied!";
                setTimeout(() => btnCopyLogs.textContent = "Copy Logs", 1500);
            });
        });

    } catch (err) {
        console.error("DOM Initialization Error:", err);
    }
});
