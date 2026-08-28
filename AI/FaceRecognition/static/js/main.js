/**
 * Face Recognition Photo Analyzer — Asynchronous Client Application Logic
 */

let appState = {
    folderPath: null,
    photoCount: 0,
    recursive: false,
    activeJobId: null,
    clusters: [],
    selectedTargetIdx: 0,
    currentPhotos: {
        with_target: [],
        without_target: [],
        no_faces: []
    },
    previewList: [],
    previewIndex: 0,
    jobsPollInterval: null,
    thumbSize: 280,
    currentBrowsePath: null,
    currentBrowseParent: null
};

// Modals
let jobsModal = null;
let historyModal = null;
let previewModal = null;
let folderPickerModal = null;

document.addEventListener("DOMContentLoaded", () => {
    jobsModal = new bootstrap.Modal(document.getElementById("jobsModal"));
    historyModal = new bootstrap.Modal(document.getElementById("historyModal"));
    previewModal = new bootstrap.Modal(document.getElementById("previewModal"));
    folderPickerModal = new bootstrap.Modal(document.getElementById("folderPickerModal"));

    // Size selector change
    const sizeSelect = document.getElementById("sizeSelect");
    if (sizeSelect) {
        sizeSelect.addEventListener("change", (e) => {
            appState.thumbSize = parseInt(e.target.value);
            document.documentElement.style.setProperty("--thumb-size", `${appState.thumbSize}px`);
        });
    }

    // Keyboard navigation for preview modal
    document.addEventListener("keydown", (e) => {
        const modalEl = document.getElementById("previewModal");
        if (modalEl && modalEl.classList.contains("show")) {
            if (e.key === "ArrowLeft") {
                navigatePreview(-1);
            } else if (e.key === "ArrowRight") {
                navigatePreview(1);
            }
        }
    });

    // Start global jobs status poll
    fetchJobsList();
    appState.jobsPollInterval = setInterval(fetchJobsList, 1500);
});

/**
 * Recursive scan toggle — keeps the two switches (banner + picker) in sync
 */
function setRecursive(value) {
    appState.recursive = !!value;
    ["chkRecursive", "chkRecursiveModal"].forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.checked = appState.recursive;
    });

    // Refresh the photo count of the folder being browsed, if the picker is open
    const picker = document.getElementById("folderPickerModal");
    if (picker && picker.classList.contains("show") && appState.currentBrowsePath) {
        browseNavigate(appState.currentBrowsePath);
    }
}

/**
 * Instantly open Folder Chooser Modal
 */
function selectFolder() {
    openFolderPickerModal(appState.folderPath || "/mnt/Dati4/Workspace/PythonExamples");
}

/**
 * Open Native Subprocess Dialog (Zenity)
 */
async function triggerNativeDialog() {
    folderPickerModal.hide();
    try {
        const res = await fetch("/api/select-folder", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ native: true, recursive: appState.recursive })
        });
        const data = await res.json();
        if (data.success) {
            appState.folderPath = data.folder_path;
            appState.photoCount = data.photo_count;

            document.getElementById("lblActivePath").textContent = data.folder_path;
            document.getElementById("btnStartScan").disabled = false;

            startScan();
            return;
        }
    } catch (err) {
        console.warn("Dialog nativo annullato o non completato.");
    }
    folderPickerModal.show();
}

/**
 * In-Browser Folder Picker Modal Logic
 */
async function openFolderPickerModal(startPath = null) {
    folderPickerModal.show();
    browseNavigate(startPath || appState.folderPath || "/mnt/Dati4/Workspace/PythonExamples");
}

async function browseNavigate(targetPath) {
    try {
        const res = await fetch("/api/browse-folder", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ path: targetPath, recursive: appState.recursive })
        });
        const data = await res.json();
        if (data.success) {
            appState.currentBrowsePath = data.current_path;
            appState.currentBrowseParent = data.parent_path;

            document.getElementById("folderPathInput").value = data.current_path;
            const scope = data.recursive ? " (sottocartelle incluse)" : "";
            document.getElementById("folderPreviewInfo").textContent = `📁 ${data.current_path}  ·  📸 ${data.photo_count} foto trovate${scope}`;

            const listEl = document.getElementById("subfolderList");
            listEl.innerHTML = "";

            if (!data.subfolders || data.subfolders.length === 0) {
                listEl.innerHTML = `<div class="p-3 text-secondary text-center">Nessuna sottocartella in questo percorso</div>`;
                return;
            }

            data.subfolders.forEach((sdir) => {
                const fullSubPath = `${data.current_path}/${sdir}`.replace("//", "/");
                const item = document.createElement("div");
                item.className = "folder-item d-flex align-items-center justify-content-between p-2 mb-1 border-bottom border-secondary text-light rounded bg-dark";
                item.innerHTML = `
                    <span class="fw-medium text-truncate">📁 ${sdir}</span>
                    <div>
                        <button class="btn btn-outline-primary btn-sm me-1 px-2 py-0" onclick="event.stopPropagation(); browseNavigate('${fullSubPath}')">Apri 📁</button>
                        <button class="btn btn-primary btn-sm px-2 py-0 fw-bold" onclick="event.stopPropagation(); selectPathDirectly('${fullSubPath}')">Seleziona ✅</button>
                    </div>
                `;
                item.onclick = () => browseNavigate(fullSubPath);
                listEl.appendChild(item);
            });
        }
    } catch (err) {
        console.error("Errore navigazione cartella:", err);
    }
}

function browseGoUp() {
    if (appState.currentBrowseParent) {
        browseNavigate(appState.currentBrowseParent);
    }
}

async function selectPathDirectly(path) {
    document.getElementById("folderPathInput").value = path;
    confirmFolderSelection();
}

async function confirmFolderSelection() {
    const selectedPath = document.getElementById("folderPathInput").value;
    folderPickerModal.hide();

    const res = await fetch("/api/select-folder", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: selectedPath, recursive: appState.recursive })
    });
    const data = await res.json();
    if (data.success) {
        appState.folderPath = data.folder_path;
        appState.photoCount = data.photo_count;

        document.getElementById("lblActivePath").textContent = data.folder_path;
        document.getElementById("btnStartScan").disabled = false;

        startScan();
    } else {
        alert(data.error || "Cartella non valida");
    }
}

/**
 * Start Asynchronous Scan Job
 */
async function startScan() {
    if (!appState.folderPath) return;

    try {
        const res = await fetch("/api/scan", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ folder_path: appState.folderPath, recursive: appState.recursive })
        });
        const data = await res.json();
        if (data.success) {
            appState.activeJobId = data.job_id;
            fetchJobsList();
            openJobsModal();
        } else {
            alert(data.error || "Errore avvio scansione");
        }
    } catch (err) {
        console.error("Errore avvio scansione:", err);
    }
}

/**
 * Fetch and Render Jobs List (Asynchronous Dashboard)
 */
async function fetchJobsList() {
    try {
        const res = await fetch("/api/jobs");
        const data = await res.json();
        if (data.success) {
            document.getElementById("jobsCountBadge").textContent = data.jobs.length;
            renderJobsContainer(data.jobs);
        }
    } catch (err) {
        console.error("Errore recupero jobs:", err);
    }
}

function openJobsModal() {
    fetchJobsList();
    jobsModal.show();
}

function renderJobsContainer(jobs) {
    const container = document.getElementById("jobsListContainer");
    if (!container) return;
    container.innerHTML = "";

    if (!jobs || jobs.length === 0) {
        container.innerHTML = `<div class="p-5 text-center text-secondary">Nessuna scansione avviata. Seleziona una cartella e fai clic su <strong>Analizza</strong>.</div>`;
        return;
    }

    jobs.forEach((job) => {
        const card = document.createElement("div");
        card.className = "card bg-body-tertiary border-secondary mb-3 p-3";

        let badgeStatus = "";
        let actionBtn = "";

        if (job.status === "scanning") {
            badgeStatus = `<span class="badge bg-primary me-2">⏳ In Corso (${job.progress.pct}%)</span>`;
            actionBtn = `<button class="btn btn-outline-primary btn-sm disabled fw-bold">Analisi in corso...</button>`;
        } else if (job.status === "completed") {
            badgeStatus = `<span class="badge bg-success me-2">🟢 Completata</span>`;
            actionBtn = `<button class="btn btn-success btn-sm fw-bold px-3" onclick="loadJobResults('${job.id}')">👁️ Apri Risultati</button>`;
        } else {
            badgeStatus = `<span class="badge bg-danger me-2">❌ Errore</span>`;
            actionBtn = `<button class="btn btn-outline-secondary btn-sm disabled">Fallito</button>`;
        }

        const progBar = (job.status === "scanning") ? `
            <div class="progress bg-secondary mt-2" style="height: 6px;">
                <div class="progress-bar progress-bar-striped progress-bar-animated bg-primary" style="width: ${job.progress.pct}%"></div>
            </div>
            <div class="text-secondary small font-monospace mt-1">${job.progress.current_file}</div>
        ` : '';

        card.innerHTML = `
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <h6 class="fw-bold text-white mb-1">${job.folder_name} ${badgeStatus}</h6>
                    <div class="text-secondary small font-monospace">📍 ${job.folder_path}</div>
                    <div class="text-secondary small mt-1">📸 ${job.total_photos} foto ${job.recursive ? '<span class="badge bg-secondary">🔁 sottocartelle</span>' : ''}  ·  Ora: ${job.date_str}</div>
                </div>
                <div>
                    ${actionBtn}
                </div>
            </div>
            ${progBar}
        `;

        container.appendChild(card);
    });
}

/**
 * Load Results for selected Job ID
 */
async function loadJobResults(jobId, targetIdx = 0) {
    try {
        jobsModal.hide();
        appState.activeJobId = jobId;
        appState.selectedTargetIdx = targetIdx;

        const res = await fetch(`/api/results?job_id=${jobId}&target_idx=${targetIdx}`);
        const data = await res.json();

        if (data.success) {
            appState.folderPath = data.folder_path;
            setRecursive(data.recursive);
            appState.clusters = data.clusters;
            appState.currentPhotos = data.photos;

            document.getElementById("lblActivePath").textContent = data.folder_path;
            document.getElementById("welcomeView").classList.add("d-none");
            document.getElementById("mainContentView").classList.remove("d-none");

            renderSidebar();
            renderStats(data);
            renderGrids();
        }
    } catch (err) {
        console.error("Errore caricamento risultati job:", err);
    }
}

/**
 * Render Sidebar with detected face cards
 */
function renderSidebar() {
    const container = document.getElementById("facesList");
    container.innerHTML = "";

    if (!appState.clusters || appState.clusters.length === 0) {
        container.innerHTML = `<div class="p-3 text-secondary text-center">Nessun volto rilevato.</div>`;
        return;
    }

    appState.clusters.forEach((c) => {
        const activeClass = (c.idx === appState.selectedTargetIdx) ? "active" : "";
        const card = document.createElement("div");
        card.className = `card face-card bg-dark text-light mb-2 p-2 ${activeClass}`;

        const starBadge = c.is_top ? `<span class="badge bg-warning text-dark me-1">⭐ Più Frequente</span>` : "";

        card.innerHTML = `
            <div class="d-flex align-items-center">
                <img src="/api/face-thumb/${c.idx}?job_id=${appState.activeJobId}" class="rounded me-3" style="width: 60px; height: 60px; object-fit: cover;" alt="Face">
                <div>
                    <h6 class="mb-1 fw-bold">Persona ${c.idx + 1}</h6>
                    <div class="text-secondary small mb-1">📸 ${c.photo_count} foto</div>
                    ${starBadge}
                </div>
            </div>
        `;

        card.onclick = () => loadJobResults(appState.activeJobId, c.idx);
        container.appendChild(card);
    });
}

/**
 * Render stats bar
 */
function renderStats(data) {
    const total = data.total_photos;
    const withT = data.photos.with_target.length;
    const withoutT = data.photos.without_target.length;
    const noF = data.photos.no_faces.length;
    const person = (data.selected_target !== null) ? `Persona ${data.selected_target + 1}` : "—";

    document.getElementById("statsSummary").innerHTML = `
        📊 <strong>${total}</strong> foto totali &nbsp;·&nbsp; 
        Filtro: <span class="badge bg-primary">${person}</span> &nbsp;·&nbsp; 
        ✅ <strong>${withT}</strong> con persona &nbsp;·&nbsp; 
        ❌ <strong>${withoutT}</strong> senza persona &nbsp;·&nbsp; 
        🚫 <strong>${noF}</strong> senza volti
    `;

    document.getElementById("countWith").textContent = withT;
    document.getElementById("countWithout").textContent = withoutT;
    document.getElementById("countNoFaces").textContent = noF;
}

/**
 * Render Photo Grids for all 3 categories
 */
function renderGrids() {
    renderSingleGrid("gridWith", appState.currentPhotos.with_target);
    renderSingleGrid("gridWithout", appState.currentPhotos.without_target);
    renderSingleGrid("gridNoFaces", appState.currentPhotos.no_faces);
}

function renderSingleGrid(gridId, photoPaths) {
    const grid = document.getElementById(gridId);
    grid.innerHTML = "";

    if (!photoPaths || photoPaths.length === 0) {
        grid.innerHTML = `<div class="p-5 text-center text-secondary fw-bold">Nessuna foto in questa categoria.</div>`;
        return;
    }

    photoPaths.forEach((path, idx) => {
        const card = document.createElement("div");
        card.className = "photo-card";

        // With a recursive scan the file name alone is ambiguous: show the
        // path relative to the analyzed folder instead.
        const prefix = appState.folderPath ? appState.folderPath.replace(/\/$/, "") + "/" : "";
        const fileName = (prefix && path.startsWith(prefix)) ? path.slice(prefix.length) : path.split("/").pop();

        card.innerHTML = `
            <div class="photo-card-img-wrapper">
                <img src="/api/image?path=${encodeURIComponent(path)}&size=280" loading="lazy" alt="${fileName}">
            </div>
            <div class="photo-card-body" title="${fileName}">${fileName}</div>
        `;

        card.ondblclick = () => openPreviewModal(photoPaths, idx);
        card.onclick = () => openPreviewModal(photoPaths, idx);

        grid.appendChild(card);
    });
}

/**
 * Open Image Preview Modal
 */
function openPreviewModal(paths, index) {
    appState.previewList = paths;
    appState.previewIndex = index;
    renderPreview();
    previewModal.show();
}

function renderPreview() {
    const path = appState.previewList[appState.previewIndex];
    if (!path) return;

    const fileName = path.split("/").pop();
    const total = appState.previewList.length;

    document.getElementById("previewCounter").textContent = `${appState.previewIndex + 1} / ${total}`;
    document.getElementById("previewFilename").textContent = fileName;
    document.getElementById("previewImg").src = `/api/image?path=${encodeURIComponent(path)}&size=full`;

    document.getElementById("btnPrevImage").disabled = (appState.previewIndex <= 0);
    document.getElementById("btnNextImage").disabled = (appState.previewIndex >= total - 1);
}

function navigatePreview(delta) {
    const newIdx = appState.previewIndex + delta;
    if (newIdx >= 0 && newIdx < appState.previewList.length) {
        appState.previewIndex = newIdx;
        renderPreview();
    }
}

/**
 * History Modal Functions (DB persisted scans)
 */
async function openHistoryModal() {
    try {
        const res = await fetch("/api/history");
        const data = await res.json();
        const container = document.getElementById("historyListContainer");
        container.innerHTML = "";

        if (!data.history || data.history.length === 0) {
            container.innerHTML = `<div class="p-5 text-center text-secondary">Nessuna scansione salvata in cronologia DB.</div>`;
            historyModal.show();
            return;
        }

        data.history.forEach((item) => {
            const fileName = item.path.split("/").pop() || item.path;
            const card = document.createElement("div");
            card.className = "card bg-body-tertiary border-secondary mb-2 p-3";

            card.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <h6 class="fw-bold text-white mb-1">${fileName}</h6>
                        <div class="text-secondary small font-monospace">📍 ${item.path}</div>
                        <div class="text-secondary small mt-1">📸 ${item.photo_count} Foto · 👥 ${item.clusters_count} Personaggi · Data: ${item.date_str}</div>
                    </div>
                    <div class="d-flex gap-2">
                        ${item.exists ? `<button class="btn btn-primary btn-sm fw-bold" onclick="reloadFromHistory('${item.path}')">🔄 Avvia Scansione</button>` : ''}
                        <button class="btn btn-outline-danger btn-sm" onclick="deleteHistoryItem('${item.path}')">❌</button>
                    </div>
                </div>
            `;
            container.appendChild(card);
        });

        historyModal.show();
    } catch (err) {
        console.error("Errore recupero cronologia DB:", err);
    }
}

async function reloadFromHistory(path) {
    historyModal.hide();
    appState.folderPath = path;
    document.getElementById("lblActivePath").textContent = path;
    startScan();
}

async function deleteHistoryItem(path) {
    await fetch(`/api/history?path=${encodeURIComponent(path)}`, { method: "DELETE" });
    openHistoryModal();
}

async function clearAllHistory() {
    if (confirm("Vuoi cancellare tutta la cronologia DB?")) {
        await fetch("/api/history", { method: "DELETE" });
        openHistoryModal();
    }
}

function copyActivePath() {
    if (appState.folderPath) {
        navigator.clipboard.writeText(appState.folderPath);
        alert(`Percorso copiato negli appunti:\n${appState.folderPath}`);
    }
}
