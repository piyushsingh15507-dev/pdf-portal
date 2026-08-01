try {
    document.addEventListener("DOMContentLoaded", () => {
        try {
            // DOM Elements
            const streamUrlInput = document.getElementById("stream-url");
            const btnFetch = document.getElementById("btn-fetch");
            const decryptionToggle = document.getElementById("decryption-toggle");
            const decryptionContent = document.getElementById("decryption-content");
            const authTokenInput = document.getElementById("auth-token");
            const o1TokenInput = document.getElementById("o1-token");
            const decKeyInput = document.getElementById("dec-key");
            const decIvInput = document.getElementById("dec-iv");
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
            const downloadSpeed = document.getElementById("download-speed");
            const downloadEta = document.getElementById("download-eta");
            
            const consoleLogs = document.getElementById("console-logs");
            const btnCopyLogs = document.getElementById("btn-copy-logs");

            // Course Explorer & Auto-Discovery Elements
            const courseIdInput = document.getElementById("course-id");
            const btnExplore = document.getElementById("btn-explore");
            const selectUserCourse = document.getElementById("select-user-course");
            const btnLoadCourses = document.getElementById("btn-load-courses");
            const btnExportTxt = document.getElementById("btn-export-txt");
            const btnBatchDownload = document.getElementById("btn-batch-download");
            const courseExplorerCard = document.getElementById("course-explorer-card");
            const explorerPath = document.getElementById("explorer-path");
            const btnBackFolder = document.getElementById("btn-back-folder");
            const explorerList = document.getElementById("explorer-list");
            
            let fetchStreams = [];
            let selectedStreamUrl = "";
            let pollingInterval = null;
            const progressRingCircumference = 439.82; // 2 * Math.PI * 70

            // Folder navigation stack: Array of { id, name }
            let folderHistory = [];
            let currentPath = "/";

            // Verify essential elements exist
            if (!btnFetch || !streamUrlInput || !consoleLogs) {
                throw new Error("Essential DOM elements (btn-fetch, stream-url, or console-logs) were not found.");
            }

            console.log("Classplus Downloader JS initialized successfully.");

            // Setup collapsible decryption panel
            if (decryptionToggle && decryptionContent) {
                decryptionToggle.addEventListener("click", () => {
                    decryptionToggle.classList.toggle("active");
                    decryptionContent.classList.toggle("active");
                });
            }

            // Logger Helper
            function addLogLine(text, type = "") {
                const div = document.createElement("div");
                div.className = "console-line";
                if (type) {
                    div.classList.add(type);
                } else if (text.includes("[SYSTEM]")) {
                    div.classList.add("system");
                } else if (text.includes("[ERROR]") || text.toLowerCase().includes("error") || text.includes("[FATAL")) {
                    div.classList.add("error");
                } else if (text.includes("[WARNING]")) {
                    div.classList.add("warning");
                } else if (text.includes("[CMD]")) {
                    div.classList.add("cmd");
                }
                div.textContent = text;
                consoleLogs.appendChild(div);
                consoleLogs.scrollTop = consoleLogs.scrollHeight;
            }

            // Set Progress ring offset
            function setProgress(percent) {
                if (progressRingBar) {
                    const offset = progressRingCircumference - (percent / 100) * progressRingCircumference;
                    progressRingBar.style.strokeDashoffset = offset;
                }
                if (progressPercentage) {
                    progressPercentage.textContent = `${percent}%`;
                }
            }

            // --- Course Explorer Functions ---
            async function fetchFolderContent(folderId = "0", folderName = "") {
                const token = authTokenInput.value.trim();
                const courseId = courseIdInput.value.trim();

                if (!token) {
                    alert("Please enter your Access Token in the Decryption Settings first.");
                    if (decryptionContent && !decryptionContent.classList.contains("active")) {
                        decryptionToggle.click(); // expand panel
                    }
                    authTokenInput.focus();
                    return;
                }

                if (!courseId) {
                    alert("Please enter a valid Course ID.");
                    courseIdInput.focus();
                    return;
                }

                // Show explorer loading state
                explorerList.innerHTML = `<div class="explorer-item span-2" style="cursor: default; border: none; background: transparent; justify-content: center; width: 100%;">
                    <div class="item-icon">⏳</div>
                    <div class="item-details" style="flex: none;">
                        <span class="item-name">Loading course folders...</span>
                    </div>
                </div>`;
                
                try {
                    const response = await fetch("/api/course-content", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ token, course_id: courseId, folder_id: folderId })
                    });
                    const resData = await response.json();

                    if (resData.success) {
                        const items = resData.data.courseContent || [];
                        renderExplorerItems(items);
                        
                        // Update folder navigation path breadcrumbs
                        if (folderId !== "0" && folderName) {
                            if (folderHistory.length === 0 || folderHistory[folderHistory.length - 1].id !== folderId) {
                                folderHistory.push({ id: folderId, name: folderName });
                            }
                        }
                        
                        // Reconstruct path name
                        currentPath = "/" + folderHistory.map(f => f.name).join("/");
                        explorerPath.textContent = `Root Path: ${currentPath}`;
                        
                        // Enable/disable back button
                        btnBackFolder.disabled = folderHistory.length === 0;
                    } else {
                        explorerList.innerHTML = `<div class="explorer-item span-2" style="border-color: #ef4444; background: rgba(239, 68, 68, 0.1);">
                            <div class="item-icon">❌</div>
                            <div class="item-details">
                                <span class="item-name">Explorer Error</span>
                                <span class="item-meta">${resData.error}</span>
                            </div>
                        </div>`;
                    }
                } catch (err) {
                    explorerList.innerHTML = `<div class="explorer-item span-2" style="border-color: #ef4444; background: rgba(239, 68, 68, 0.1);">
                        <div class="item-icon">❌</div>
                        <div class="item-details">
                            <span class="item-name">Connection Error</span>
                            <span class="item-meta">${err.message}</span>
                        </div>
                    </div>`;
                }
            }

            function renderExplorerItems(items) {
                explorerList.innerHTML = "";
                
                if (items.length === 0) {
                    explorerList.innerHTML = `<div class="explorer-item" style="cursor: default; width: 100%; border: none; background: transparent; justify-content: center; grid-column: 1 / -1;">
                        <span class="item-meta" style="font-size: 1rem;">This folder is empty.</span>
                    </div>`;
                    return;
                }

                items.forEach(item => {
                    const ct = item.contentType;
                    const name = item.name || "Unnamed Item";
                    const id = item.id;
                    const contentHashId = item.contentHashId || item.contentId || item.url || item.id || "";

                    const el = document.createElement("div");
                    el.className = "explorer-item";
                    
                    if (ct === 1) {
                        // Folder
                        el.innerHTML = `
                            <div class="item-icon">📁</div>
                            <div class="item-details">
                                <span class="item-name">${name}</span>
                                <span class="item-meta">Folder</span>
                            </div>
                        `;
                        el.addEventListener("click", () => {
                            fetchFolderContent(id.toString(), name);
                        });
                    } else if (ct === 2) {
                        // Video
                        const durationSec = item.duration || 0;
                        let durationText = "Unknown Length";
                        if (durationSec > 0) {
                            const min = Math.floor(durationSec / 60);
                            const sec = Math.floor(durationSec % 60);
                            durationText = `${min}m ${sec}s`;
                        }
                        
                        el.innerHTML = `
                            <div class="item-icon">📹</div>
                            <div class="item-details">
                                <span class="item-name">${name}</span>
                                <span class="item-meta">Video • ${durationText}</span>
                            </div>
                        `;
                        
                        el.addEventListener("click", () => {
                            // Autofill forms and fetch automatically
                            streamUrlInput.value = `https://api.classplusapp.com/cams/uploader/video/jw-signed-url?contentId=${contentHashId}`;
                            if (o1TokenInput) o1TokenInput.value = contentHashId;
                            if (outputNameInput) outputNameInput.value = name;
                            
                            addLogLine(`[SYSTEM] Explorer selected video: "${name}"`);
                            btnFetch.click(); // Trigger auto-fetch
                            
                            // Scroll to control panel
                            document.querySelector(".control-panel").scrollIntoView({ behavior: "smooth" });
                        });
                    } else {
                        // Other files (like PDFs)
                        el.innerHTML = `
                            <div class="item-icon">📄</div>
                            <div class="item-details">
                                <span class="item-name">${name}</span>
                                <span class="item-meta">Document File</span>
                            </div>
                        `;
                        el.style.opacity = "0.6";
                        el.style.cursor = "default";
                    }

                    explorerList.appendChild(el);
                });
            }

            // Handle explore course button
            btnExplore.addEventListener("click", () => {
                const token = authTokenInput.value.trim();
                const courseId = courseIdInput.value.trim();

                if (!token || !courseId) {
                    alert("Please fill in both the access token (under Decryption Settings) and the Course ID to explore.");
                    return;
                }

                // Reset navigation stack
                folderHistory = [];
                currentPath = "/";
                explorerPath.textContent = "Root Path: /";
                btnBackFolder.disabled = true;

                // Show explorer panel
                courseExplorerCard.classList.remove("hidden");
                fetchFolderContent("0");
            });

            // Handle folder back button
            btnBackFolder.addEventListener("click", () => {
                if (folderHistory.length > 0) {
                    folderHistory.pop(); // remove current folder
                    const parentFolder = folderHistory[folderHistory.length - 1];
                    const parentId = parentFolder ? parentFolder.id : "0";
                    const parentName = parentFolder ? parentFolder.name : "";
                    
                    fetchFolderContent(parentId.toString(), parentName);
                }
            });

            // Fetch stream information
            btnFetch.addEventListener("click", async () => {
                const url = streamUrlInput.value.trim();
                const token = authTokenInput ? authTokenInput.value.trim() : "";
                const o1 = o1TokenInput ? o1TokenInput.value.trim() : "";

                if (!url) {
                    alert("Please enter an HLS Stream URL first.");
                    return;
                }

                // Reset quality section
                if (qualitySection) qualitySection.classList.add("hidden");
                if (qualityList) qualityList.innerHTML = "";
                btnDownload.disabled = true;
                fetchStreams = [];
                selectedStreamUrl = "";

                // UI Loading state
                btnFetch.disabled = true;
                const btnTextEl = btnFetch.querySelector(".btn-text");
                if (btnTextEl) btnTextEl.textContent = "Fetching...";
                const spinnerEl = btnFetch.querySelector(".spinner");
                if (spinnerEl) spinnerEl.classList.remove("hidden");
                
                addLogLine(`[SYSTEM] Querying server for stream manifest...`);
                if (token) addLogLine(`[SYSTEM] Passing x-access-token for auto-decryption.`);
                if (o1) addLogLine(`[SYSTEM] Passing o1/contentId token directly.`);

                try {
                    const response = await fetch("/api/fetch-info", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ url, token, o1 })
                    });
                    const data = await response.json();

                    if (data.success) {
                        fetchStreams = data.streams;
                        if (fetchStreams.length === 0) {
                            addLogLine("[ERROR] No streams found in the manifest.", "error");
                            alert("No video streams could be parsed from the provided URL.");
                            return;
                        }

                        // If o1 extracted successfully, display key/IV and inform user
                        if (data.o1_extracted) {
                            addLogLine(`[SYSTEM] Success! Key and IV auto-extracted from o1 parameter.`);
                            addLogLine(`[SYSTEM] Extracted Key (Hex): ${data.key_hex}`);
                            addLogLine(`[SYSTEM] Extracted IV (Hex): ${data.iv_hex}`);
                            
                            // Autofill the Key & IV input boxes
                            if (decKeyInput) decKeyInput.value = data.key_hex;
                            if (decIvInput) decIvInput.value = data.iv_hex;
                        } else {
                            addLogLine(`[SYSTEM] Manifest fetched, but o1 key extraction was not found. If this stream is encrypted, please enter Key & IV manually.`);
                        }

                        addLogLine(`[SYSTEM] Successfully parsed ${fetchStreams.length} stream option(s).`);
                        
                        // Populate qualities UI
                        if (qualityList) {
                            fetchStreams.forEach((stream, index) => {
                                const item = document.createElement("div");
                                item.className = "quality-item";
                                
                                const targetUrl = stream.url || data.resolved_url || url;
                                
                                if (index === 0) {
                                    item.classList.add("selected");
                                    selectedStreamUrl = targetUrl;
                                    btnDownload.disabled = false;
                                }

                                let bwText = "";
                                if (stream.bandwidth > 0) {
                                    const mbps = (stream.bandwidth / 1000000).toFixed(2);
                                    bwText = `(${mbps} Mbps)`;
                                } else if (stream.resolution !== "Unknown") {
                                    bwText = `(${stream.resolution})`;
                                }

                                item.innerHTML = `
                                    <input type="radio" name="stream-quality" id="quality-${index}" value="${targetUrl}" ${index === 0 ? 'checked' : ''}>
                                    <div class="quality-info">
                                        <span class="quality-res">${stream.quality} ${stream.resolution !== "Unknown" ? `[${stream.resolution}]` : ''}</span>
                                        <span class="quality-bw">${bwText}</span>
                                    </div>
                                `;

                                // Handle selection click
                                item.addEventListener("click", () => {
                                    document.querySelectorAll(".quality-item").forEach(el => el.classList.remove("selected"));
                                    item.classList.add("selected");
                                    item.querySelector("input").checked = true;
                                    selectedStreamUrl = targetUrl;
                                    btnDownload.disabled = false;
                                    addLogLine(`[SYSTEM] Selected quality: ${stream.quality} (${stream.resolution})`);
                                });

                                qualityList.appendChild(item);
                            });
                        }

                        if (qualitySection) qualitySection.classList.remove("hidden");
                        
                        // Autofill filename suggestion from URL (if output name has default value)
                        try {
                            if (outputNameInput.value === "Classplus_Video" && !url.includes("contentId=")) {
                                const urlObj = new URL(url);
                                const pathParts = urlObj.pathname.split('/');
                                const m3u8Name = pathParts[pathParts.length - 1];
                                const suggestion = m3u8Name.replace(/\.m3u8$/i, "");
                                if (suggestion && suggestion !== "master" && suggestion !== "playlist" && !suggestion.includes("p")) {
                                    if (outputNameInput) outputNameInput.value = suggestion;
                                }
                            }
                        } catch(e) {}

                    } else {
                        addLogLine(`[ERROR] ${data.error}`, "error");
                        alert(`Error fetching playlist: ${data.error}`);
                    }
                } catch (err) {
                    addLogLine(`[ERROR] Network error or server offline: ${err.message}`, "error");
                    alert("Could not connect to Python backend server.");
                } finally {
                    btnFetch.disabled = false;
                    if (btnTextEl) btnTextEl.textContent = "Fetch Info";
                    if (spinnerEl) spinnerEl.classList.add("hidden");
                }
            });

            // Start download process
            btnDownload.addEventListener("click", async () => {
                if (!selectedStreamUrl) {
                    alert("Please fetch and select a stream quality first.");
                    return;
                }

                const key = decKeyInput ? decKeyInput.value.trim() : "";
                const iv = decIvInput ? decIvInput.value.trim() : "";
                const filename = outputNameInput ? outputNameInput.value.trim() : "";
                const format = outputFormatSelect ? outputFormatSelect.value : "mp4";

                // Disable input panel
                if (streamUrlInput) streamUrlInput.disabled = true;
                btnFetch.disabled = true;
                if (authTokenInput) authTokenInput.disabled = true;
                if (o1TokenInput) o1TokenInput.disabled = true;
                if (decKeyInput) decKeyInput.disabled = true;
                if (decIvInput) decIvInput.disabled = true;
                if (outputNameInput) outputNameInput.disabled = true;
                if (outputFormatSelect) outputFormatSelect.disabled = true;
                if (courseIdInput) courseIdInput.disabled = true;
                btnExplore.disabled = true;
                
                // Swap action buttons
                btnDownload.classList.add("hidden");
                if (btnCancel) btnCancel.classList.remove("hidden");
                
                if (statusBadge) {
                    statusBadge.textContent = "Starting...";
                    statusBadge.className = "status-badge downloading";
                }
                
                consoleLogs.innerHTML = "";
                addLogLine("[SYSTEM] Initializing request parameters...");

                try {
                    const response = await fetch("/api/download", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            url: selectedStreamUrl,
                            key: key,
                            iv: iv,
                            filename: filename,
                            format: format
                        })
                    });
                    const data = await response.json();

                    if (data.success) {
                        addLogLine("[SYSTEM] Download process started successfully.");
                        startStatusPolling();
                    } else {
                        addLogLine(`[ERROR] ${data.message}`, "error");
                        resetUIAfterDownload();
                        alert(`Failed to start download: ${data.message}`);
                    }
                } catch (err) {
                    addLogLine(`[ERROR] Server connection failed: ${err.message}`, "error");
                    resetUIAfterDownload();
                    alert("Could not connect to Python backend server.");
                }
            });

            // Cancel download
            if (btnCancel) {
                btnCancel.addEventListener("click", async () => {
                    if (confirm("Are you sure you want to stop the current download?")) {
                        btnCancel.disabled = true;
                        addLogLine("[SYSTEM] Requesting cancellation...");
                        try {
                            await fetch("/api/cancel", { method: "POST" });
                        } catch (e) {
                            addLogLine(`[ERROR] Failed to send cancel request: ${e.message}`, "error");
                        }
                    }
                });
            }

            // Poll server for downloader state
            function startStatusPolling() {
                if (pollingInterval) clearInterval(pollingInterval);
                
                pollingInterval = setInterval(async () => {
                    try {
                        const response = await fetch("/api/status");
                        const data = await response.json();

                        // 1. Update logs panel
                        updateLogs(data.logs);

                        // 2. Update progress UI
                        setProgress(data.progress);
                        if (progressStatus) progressStatus.textContent = data.status_text;
                        if (downloadSpeed) downloadSpeed.textContent = data.speed;
                        if (downloadEta) downloadEta.textContent = data.eta;

                        // 3. Update status badge
                        if (data.running) {
                            if (statusBadge) {
                                statusBadge.textContent = "Downloading";
                                statusBadge.className = "status-badge downloading";
                            }
                        } else {
                            clearInterval(pollingInterval);
                            pollingInterval = null;
                            
                            if (data.status_text === "Completed") {
                                if (statusBadge) {
                                    statusBadge.textContent = "Completed";
                                    statusBadge.className = "status-badge completed";
                                }
                                setProgress(100);
                                addLogLine("[SYSTEM] Download task finished successfully.");
                            } else if (data.status_text === "Cancelled") {
                                if (statusBadge) {
                                    statusBadge.textContent = "Cancelled";
                                    statusBadge.className = "status-badge failed";
                                }
                                addLogLine("[SYSTEM] Download task was cancelled.");
                            } else {
                                if (statusBadge) {
                                    statusBadge.textContent = "Failed";
                                    statusBadge.className = "status-badge failed";
                                }
                                addLogLine("[SYSTEM] Download task failed. Check terminal logs.", "error");
                            }
                            
                            resetUIAfterDownload();
                        }

                    } catch (err) {
                        console.error("Error polling status:", err);
                    }
                }, 800);
            }

            let lastLogCount = 0;
            function updateLogs(rawLogs) {
                if (!rawLogs) return;
                const lines = rawLogs.split("\n");
                
                if (lines.length === lastLogCount) return;
                lastLogCount = lines.length;

                consoleLogs.innerHTML = "";
                lines.forEach(line => {
                    if (!line.trim()) return;
                    
                    const div = document.createElement("div");
                    div.className = "console-line";
                    
                    if (line.includes("[SYSTEM]")) {
                        div.classList.add("system");
                    } else if (line.includes("[ERROR]") || line.toLowerCase().includes("error") || line.includes("[FATAL")) {
                        div.classList.add("error");
                    } else if (line.includes("[WARNING]")) {
                        div.classList.add("warning");
                    } else if (line.includes("[CMD]")) {
                        div.classList.add("cmd");
                    } else if (line.includes("Progress:")) {
                        div.style.color = "#10b981";
                    }
                    
                    div.textContent = line;
                    consoleLogs.appendChild(div);
                });
                
                consoleLogs.scrollTop = consoleLogs.scrollHeight;
            }

            function resetUIAfterDownload() {
                if (streamUrlInput) streamUrlInput.disabled = false;
                btnFetch.disabled = false;
                if (authTokenInput) authTokenInput.disabled = false;
                if (o1TokenInput) o1TokenInput.disabled = false;
                if (decKeyInput) decKeyInput.disabled = false;
                if (decIvInput) decIvInput.disabled = false;
                if (outputNameInput) outputNameInput.disabled = false;
                if (outputFormatSelect) outputFormatSelect.disabled = false;
                if (courseIdInput) courseIdInput.disabled = false;
                btnExplore.disabled = false;
                
                btnDownload.classList.remove("hidden");
                if (btnCancel) {
                    btnCancel.classList.add("hidden");
                    btnCancel.disabled = false;
                }
            }

            // Copy terminal logs
            if (btnCopyLogs) {
                btnCopyLogs.addEventListener("click", () => {
                    const textToCopy = consoleLogs.innerText;
                    if (!textToCopy || textToCopy.includes("Awaiting input URL")) {
                        return;
                    }

                    navigator.clipboard.writeText(textToCopy).then(() => {
                        const originalText = btnCopyLogs.textContent;
                        btnCopyLogs.textContent = "Copied!";
                        btnCopyLogs.disabled = true;
                        setTimeout(() => {
                            btnCopyLogs.textContent = originalText;
                            btnCopyLogs.disabled = false;
                        }, 1500);
                    }).catch(err => {
                        console.error("Could not copy logs: ", err);
                    });
                });
            }

            // Auto Course Discovery
            async function loadUserCourses() {
                const token = authTokenInput.value.trim();
                if (!token) {
                    alert("Please enter your Access Token in Decryption Settings first.");
                    if (decryptionContent && !decryptionContent.classList.contains("active")) {
                        decryptionToggle.click();
                    }
                    authTokenInput.focus();
                    return;
                }

                if (btnLoadCourses) btnLoadCourses.textContent = "Loading...";
                try {
                    const res = await fetch("/api/user-courses", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ token })
                    });
                    if (!res.ok) {
                        const errText = await res.text();
                        throw new Error(`Server returned status ${res.status}: ${errText.slice(0, 100)}`);
                    }
                    const data = await res.json();
                    if (btnLoadCourses) btnLoadCourses.textContent = "Auto-Find";

                    if (data.success && data.courses && selectUserCourse) {
                        selectUserCourse.innerHTML = `<option value="">-- Select a Course (${data.courses.length} Found) --</option>`;
                        data.courses.forEach(c => {
                            const opt = document.createElement("option");
                            opt.value = c.id || c.courseId;
                            opt.textContent = `${c.name} (ID: ${c.id || c.courseId})`;
                            selectUserCourse.appendChild(opt);
                        });
                        addLogLine(`[SYSTEM] Auto-discovered ${data.courses.length} purchased courses for your Access Token!`);
                    } else if (data.error) {
                        alert(data.error);
                    }
                } catch (e) {
                    if (btnLoadCourses) btnLoadCourses.textContent = "Auto-Find";
                    alert(`Error loading courses: ${e.message}`);
                }
            }

            if (btnLoadCourses) {
                btnLoadCourses.addEventListener("click", loadUserCourses);
            }

            if (selectUserCourse) {
                selectUserCourse.addEventListener("change", () => {
                    if (selectUserCourse.value) {
                        courseIdInput.value = selectUserCourse.value;
                    }
                });
            }

            if (authTokenInput) {
                authTokenInput.addEventListener("change", () => {
                    if (authTokenInput.value.trim().length > 20) {
                        loadUserCourses();
                    }
                });
            }

            // Export Links to TXT File
            if (btnExportTxt) {
                btnExportTxt.addEventListener("click", async () => {
                    const token = authTokenInput.value.trim();
                    const courseId = courseIdInput.value.trim();

                    if (!token || !courseId) {
                        alert("Please enter your Access Token and Course ID first.");
                        return;
                    }

                    addLogLine(`[SYSTEM] Exporting course links for Course ID: ${courseId}...`);
                    btnExportTxt.disabled = true;
                    btnExportTxt.textContent = "Exporting...";

                    try {
                        const res = await fetch("/api/export-course-links", {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({ token, course_id: courseId })
                        });
                        if (!res.ok) {
                            const errText = await res.text();
                            throw new Error(`Server returned status ${res.status}: ${errText.slice(0, 100)}`);
                        }
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
            }

            // Batch Download All Videos
            let batchInterval = null;
            if (btnBatchDownload) {
                btnBatchDownload.addEventListener("click", async () => {
                    const token = authTokenInput.value.trim();
                    const courseId = courseIdInput.value.trim();

                    if (!token || !courseId) {
                        alert("Please enter your Access Token and Course ID first.");
                        return;
                    }

                    if (!confirm(`Are you sure you want to download ALL videos in Course ${courseId}?`)) {
                        return;
                    }

                    addLogLine(`[BATCH] Starting sequential batch download for Course ${courseId}...`);
                    btnBatchDownload.disabled = true;

                    try {
                        const res = await fetch("/api/batch-download", {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({
                                token,
                                course_id: courseId,
                                format: outputFormatSelect ? outputFormatSelect.value : "mp4"
                            })
                        });
                        const data = await res.json();

                        if (data.success) {
                            startBatchPolling();
                        } else {
                            btnBatchDownload.disabled = false;
                            alert(data.error || "Batch download start failed.");
                        }
                    } catch (e) {
                        btnBatchDownload.disabled = false;
                        alert(`Batch start error: ${e.message}`);
                    }
                });
            }

            function startBatchPolling() {
                if (batchInterval) clearInterval(batchInterval);

                batchInterval = setInterval(async () => {
                    try {
                        const res = await fetch("/api/batch-status");
                        const status = await res.json();

                        if (status.status_text && progressStatus) {
                            progressStatus.textContent = status.status_text;
                        }

                        if (status.total_videos > 0) {
                            const pct = Math.round((status.current_index / status.total_videos) * 100);
                            setProgress(pct);
                        }

                        if (!status.running) {
                            clearInterval(batchInterval);
                            if (btnBatchDownload) btnBatchDownload.disabled = false;
                            addLogLine(`[BATCH] Finished batch process!`);
                        }
                    } catch (e) {
                        console.error("Batch polling error:", e);
                    }
                }, 2000);
            }
        } catch (domErr) {
            alert("DOM Initialization Error: " + domErr.message + "\nStack: " + domErr.stack);
        }
    });
} catch (globalErr) {
    alert("Global Script Error: " + globalErr.message + "\nStack: " + globalErr.stack);
}
