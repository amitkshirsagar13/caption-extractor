// app.js

// --- Tab Navigation ---
document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document
      .querySelectorAll(".tab-btn")
      .forEach((b) => b.classList.remove("active"));
    document
      .querySelectorAll(".tab-content")
      .forEach((c) => c.classList.remove("active"));
    (c) => (c.style.display = "none"); // reset all

    btn.classList.add("active");
    const targetId = btn.getAttribute("data-target");
    const target = document.getElementById(targetId);
    target.classList.add("active");

    document
      .querySelectorAll(".tab-content")
      .forEach((c) => (c.style.display = "none"));
    target.style.display = "flex";

    if (targetId === "tab-jobs") {
      fetchJobs();
    } else if (targetId === "tab-api") {
      fetchPerformance();
    }
  });
});

// Initialize display for tabs
document.querySelectorAll(".tab-content").forEach((c) => {
  if (!c.classList.contains("active")) {
    c.style.display = "none";
  }
});

// --- Existing Process Image Tester ---
document
  .getElementById("process-form")
  ?.addEventListener("submit", async function (e) {
    e.preventDefault();

    const btn = document.getElementById("process-btn");
    const loader = document.getElementById("loader");
    const resultArea = document.getElementById("result-area");
    const formData = new FormData(this);

    if (!formData.get("vision_model")) formData.delete("vision_model");
    if (!formData.get("text_model")) formData.delete("text_model");

    btn.disabled = true;
    btn.textContent = "Processing...";
    loader.style.display = "block";
    resultArea.textContent = "Processing...";
    resultArea.removeAttribute("data-highlighted");

    try {
      const response = await fetch("/process", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) throw new Error(await response.text());

      const data = await response.json();
      resultArea.textContent = JSON.stringify(data, null, 2);
      Prism.highlightElement(resultArea);
    } catch (error) {
      resultArea.textContent = "Error: " + error.message;
    } finally {
      btn.disabled = false;
      btn.textContent = "AI Image Extract";
      loader.style.display = "none";
    }
  });

document.getElementById("image-file")?.addEventListener("change", function (e) {
  const file = e.target.files[0];
  const previewContainer = document.getElementById("preview-container");
  const previewImage = document.getElementById("image-preview");

  if (file) {
    const reader = new FileReader();
    reader.onload = function (e) {
      previewImage.src = e.target.result;
      previewContainer.style.display = "block";
    };
    reader.readAsDataURL(file);
  } else {
    previewContainer.style.display = "none";
    previewImage.src = "";
  }
});

document.getElementById("copy-btn")?.addEventListener("click", function () {
  const resultText = document.getElementById("result-area").textContent;
  navigator.clipboard.writeText(resultText).then(() => {
    const originalText = this.textContent;
    this.textContent = "Copied!";
    setTimeout(() => (this.textContent = originalText), 2000);
  });
});

// --- Browse Folders & Images ---

let currentFolderImages = [];
let currentFolders = [];
let currentSlideshowIndex = 0;
let currentPath = localStorage.getItem("browsePath") || "/media/data/";
let allJobs = [];

document.getElementById("refresh-browse-btn")?.addEventListener("click", () => {
  loadPath(currentPath);
});

document
  .getElementById("search-folder-input")
  ?.addEventListener("input", (e) => {
    const term = e.target.value.toLowerCase();
    const filteredFolders = currentFolders.filter((f) =>
      f.name.toLowerCase().includes(term),
    );
    renderFolders(filteredFolders);
  });

document
  .getElementById("sort-folder-select")
  ?.addEventListener("change", sortFolders);
document
  .getElementById("sort-folder-order")
  ?.addEventListener("change", sortFolders);
document
  .getElementById("sort-image-select")
  ?.addEventListener("change", sortImages);
document
  .getElementById("sort-image-order")
  ?.addEventListener("change", sortImages);
document
  .getElementById("size-folder-select")
  ?.addEventListener("change", updateTileSize);

function updateTileSize() {
  const size = document.getElementById("size-folder-select").value;
  const foldersContainer = document.getElementById("folder-tiles-container");
  const imagesContainer = document.getElementById("image-tiles-container");

  foldersContainer.style.gridTemplateColumns = `repeat(auto-fill, ${size})`;
  foldersContainer.style.gridAutoRows = size;

  imagesContainer.style.gridTemplateColumns = `repeat(auto-fill, ${size})`;
  imagesContainer.style.gridAutoRows = size;
}

function sortFolders() {
  const order = document.getElementById("sort-folder-order").value;
  const sorted = [...currentFolders].sort((a, b) => {
    if (order === "asc") return a.name.localeCompare(b.name);
    return b.name.localeCompare(a.name);
  });
  renderFolders(sorted);
}

function sortImages() {
  const order = document.getElementById("sort-image-order").value;
  const sorted = [...currentFolderImages].sort((a, b) => {
    if (order === "asc") return a.name.localeCompare(b.name);
    return b.name.localeCompare(a.name);
  });
  renderImages(sorted);
}

async function loadPath(path) {
  currentPath = path;
  localStorage.setItem("browsePath", path);
  updateBreadcrumb(path);

  // Load Folders
  try {
    const res = await fetch(`/folders?path=${encodeURIComponent(path)}`);
    const data = await res.json();
    currentFolders = data.folders || [];
    sortFolders(); // will call renderFolders
    fetchJobs(); // fetch jobs after rendering folders to update overlays
  } catch (e) {
    console.error("Failed to list folders", e);
    renderFolders([]);
  }

  // Load Images
  loadFolderImages(path);
}

function updateBreadcrumb(path) {
  const container = document.getElementById("breadcrumb-container");
  container.innerHTML = "";

  // Split path and create clickable segments
  // Handle Windows/Linux paths gracefully, default to /media/data
  const parts = path.split("/").filter((p) => p);
  let currentAccPath = path.startsWith("/") ? "/" : "";

  if (parts.length === 0) {
    container.innerHTML = "<span>/</span>";
    return;
  }

  parts.forEach((part, index) => {
    currentAccPath += part + "/";
    const span = document.createElement("span");
    span.textContent = part;
    span.style.cursor = "pointer";
    span.style.color = "#fff";

    const pathToLoad = currentAccPath.slice(0, -1);
    span.addEventListener("click", () => loadPath(pathToLoad));

    container.appendChild(span);

    if (index < parts.length - 1) {
      const separator = document.createElement("span");
      separator.textContent = " / ";
      separator.style.color = "#555";
      separator.style.margin = "0 5px";
      container.appendChild(separator);
    }
  });
}

function renderFolders(folders) {
  const container = document.getElementById("folder-tiles-container");
  container.innerHTML = "";

  if (folders.length === 0) {
    container.innerHTML =
      '<p style="grid-column: 1/-1; opacity: 0.7;">No folders found.</p>';
    return;
  }

  folders.forEach((f) => {
    const tile = document.createElement("div");
    tile.className = "tile folder-tile";
    tile.style.backgroundColor = "#1e2025";
    tile.style.borderColor = "#333";
    tile.style.padding = "0";
    tile.style.border = "1px solid #444";
    tile.style.overflow = "hidden";
    tile.style.display = "flex";
    tile.style.flexDirection = "column";

    let thumbContent = '<span style="font-size: 3rem;">📁</span>';
    if (f.first_image) {
      thumbContent = `<img src="/image?path=${encodeURIComponent(f.first_image)}" style="width: 100%; height: 100%; object-fit: cover;" onerror="this.outerHTML='<span style=\\'font-size: 3rem;\\'>📁</span>';">`;
    }
    tile.innerHTML = `
            <div style="background-color: #2a2d35; width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; position: relative;">
                ${thumbContent}
                <div class="job-overlay-container" data-path="${f.path}" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none;"></div>
                <div style="position: absolute; bottom: 0; left: 0; right: 0; background: linear-gradient(transparent, rgba(0,0,0,0.8)); padding: 5px 8px; color: #fff; font-size: 0.8rem; text-align: left; display: flex; align-items: center; justify-content: space-between;">
                    <span style="font-weight: bold; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${f.name}</span>
                    <span style="color: #aaa; font-size: 0.7rem; white-space: nowrap; background: rgba(0,0,0,0.5); padding: 2px 4px; border-radius: 3px;">📁 ${f.image_count || 0}</span>
                </div>
            </div>
        `;

    tile.addEventListener("click", () => {
      loadPath(f.path);
    });

    container.appendChild(tile);
  });
}

async function loadFolderImages(path) {
  document.getElementById("selected-folder-name").textContent = path
    .split("/")
    .pop();
  try {
    const res = await fetch(`/folders/images?path=${encodeURIComponent(path)}`);
    const data = await res.json();
    currentFolderImages = data.images || [];
    document.getElementById("selected-folder-count").textContent =
      `(${currentFolderImages.length})`;
    renderImages(currentFolderImages);
  } catch (e) {
    console.error("Failed to list images", e);
    document.getElementById("selected-folder-count").textContent = "(0)";
    renderImages([]);
  }
}

function renderImages(images) {
  const container = document.getElementById("image-tiles-container");
  container.innerHTML = "";

  if (images.length === 0) {
    container.innerHTML =
      '<p style="grid-column: 1/-1; opacity: 0.7;">No images found in folder.</p>';
    return;
  }

  images.forEach((img, idx) => {
    const tile = document.createElement("div");
    tile.className = "tile image-tile";
    tile.style.backgroundColor = "#1e2025";
    tile.style.borderColor = "#333";
    tile.style.padding = "0";
    tile.style.overflow = "hidden";

    tile.innerHTML = `
            <div style="width: 100%; height: 100%; background-color: #2a2d35; display: flex; align-items: center; justify-content: center; position: relative;">
                <img src="/image?path=${encodeURIComponent(img.path)}" style="width: 100%; height: 100%; object-fit: contain;" onerror="this.outerHTML='<span style=\\'font-size: 3rem; opacity: 0.5;\\'>🖼️</span>';">
                ${img.has_caption ? '<div class="caption-indicator" style="position: absolute; top: 5px; right: 5px; background: rgba(0,0,0,0.7); border-radius: 4px; padding: 2px;">📝</div>' : ""}
                <div style="position: absolute; bottom: 0; left: 0; right: 0; background: linear-gradient(transparent, rgba(0,0,0,0.8)); padding: 5px; color: #ccc; font-size: 0.8rem; text-align: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                    ${img.name}
                </div>
            </div>
        `;

    tile.addEventListener("click", () => openSlideshow(idx));
    container.appendChild(tile);
  });
}

// Initialize on first tab show
document
  .querySelector('.tab-btn[data-target="tab-folders"]')
  ?.addEventListener("click", () => {
    if (currentFolders.length === 0 && currentFolderImages.length === 0) {
      loadPath(currentPath);
    }
  });

// --- Jobs & Folder Overlays ---
function updateFolderJobsUI() {
  const containers = document.querySelectorAll(".job-overlay-container");
  containers.forEach((container) => {
    const path = container.getAttribute("data-path");
    const folderJobs = allJobs
      .filter((j) => j.folder_path === path)
      .sort((a, b) => b.created_at - a.created_at);
    const latestJob = folderJobs.length > 0 ? folderJobs[0] : null;

    // Common styling shared by action control elements
    const baseActionBtnStyle = `width: 18px; height: 18px; display: flex; align-items: center; justify-content: center; font-size: 10px; border-radius: 3px; cursor: pointer; pointer-events: auto; border: none; color: white;`;

    // 1. Construct the persistent Clean folder button action asset
    const cleanBtnHtml = `<button class="clean-folder-tile-btn" data-path="${path}" title="Clean Image YML Sidecars" style="${baseActionBtnStyle} background: #d9534f; margin-right: 4px;">🧹</button>`;

    let overlayHtml = "";
    if (!latestJob) {
      overlayHtml = `
        <div style="position: absolute; top: 5px; right: 5px; display: flex; gap: 4px;">
            ${cleanBtnHtml}
            <button class="start-job-btn" title="Start Job" style="${baseActionBtnStyle} background: #0066ff;">▶</button>
        </div>`;
    } else {
      let statusColor = "#888";
      if (latestJob.status === "running") statusColor = "#4ec9b0";
      else if (latestJob.status === "queued") statusColor = "#007acc";
      else if (latestJob.status === "paused") statusColor = "#ce9178";
      else if (latestJob.status === "completed") statusColor = "#4ec9b0";
      else if (latestJob.status === "cancelled") statusColor = "#f48771";

      let btnHtml = "";
      if (latestJob.status === "completed" || latestJob.status === "cancelled") {
        btnHtml = `<button class="start-job-btn" title="Restart Job" style="${baseActionBtnStyle} background: #0066ff;">🔁</button>`;
      } else if (latestJob.status === "running") {
        btnHtml = `<button class="pause-job-btn" data-id="${latestJob.job_id}" title="Pause" style="${baseActionBtnStyle} background: #ce9178;">⏸</button>`;
      } else if (latestJob.status === "paused") {
        btnHtml = `<button class="resume-job-btn" data-id="${latestJob.job_id}" title="Resume" style="${baseActionBtnStyle} background: #4ec9b0;">▶</button>`;
      } else {
        btnHtml = `<span title="${latestJob.status}" style="${baseActionBtnStyle} background: ${statusColor}; cursor: default;">⏳</span>`;
      }

      let statusIcon = "⏳";
      if (latestJob.status === "running") statusIcon = "🔄";
      else if (latestJob.status === "queued") statusIcon = "⏳";
      else if (latestJob.status === "paused") statusIcon = "⏸️";
      else if (latestJob.status === "completed") statusIcon = "✅";
      else if (latestJob.status === "cancelled") statusIcon = "❌";

      overlayHtml = `
            <div style="position: absolute; top: 5px; left: 5px; background: rgba(0,0,0,0.7); border: 1px solid ${statusColor}; color: white; font-size: 0.8rem; padding: 2px 5px; border-radius: 3px; pointer-events: auto; display: flex; gap: 4px; align-items: center;">
                <span>${statusIcon}</span> ${latestJob.progress_percent && latestJob.status !== "completed" && latestJob.status !== "cancelled" ? "<span>" + Math.round(latestJob.progress_percent) + "%</span>" : ""}
            </div>
            <div style="position: absolute; top: 5px; right: 5px; display: flex; gap: 4px;">
                ${cleanBtnHtml}
                ${btnHtml}
            </div>
        `;
    }

    container.innerHTML = overlayHtml;

    // 2. Attach Event Binds for the newly injected elements
    const cleanBtn = container.querySelector(".clean-folder-tile-btn");
    if (cleanBtn) {
      cleanBtn.addEventListener("click", (e) => {
        e.stopPropagation(); // Stop navigation click events bubble up to container row tile
        const targetPath = cleanBtn.getAttribute("data-path");
        window.cleanFolderSidecarYmls(targetPath);
      });
    }

    const startBtn = container.querySelector(".start-job-btn");
    if (startBtn) {
      startBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        startFolderJob(path);
      });
    }
    const pauseBtn = container.querySelector(".pause-job-btn");
    if (pauseBtn) {
      pauseBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        window.pauseJob(pauseBtn.getAttribute("data-id"));
      });
    }
    const resumeBtn = container.querySelector(".resume-job-btn");
    if (resumeBtn) {
      resumeBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        window.resumeJob(resumeBtn.getAttribute("data-id"));
      });
    }
  });
}

// 3. Register Global Handler for execution tasks
window.cleanFolderSidecarYmls = async (folderPath) => {
  const folderDisplay = folderPath.split("/").pop();
  if (!confirm(`Are you sure you want to clean up ONLY image-generated YML sidecars inside folder "${folderDisplay}"?`)) return;

  try {
    const response = await fetch("/folders/clean", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: folderPath })
    });
    
    if (!response.ok) throw new Error(await response.text());
    
    const data = await response.json();
    alert(`Cleaned up ${data.deleted_files_count || 0} valid sidecar files from folder grid layout successfully.`);
    
    // Dynamically refresh the folder's image display status cards if viewing inside it
    if (typeof currentPath !== "undefined" && currentPath === folderPath) {
        loadPath(currentPath);
    } else {
        fetchJobs(); // Force redrawing layout assets state
    }
  } catch (err) {
    console.error("Cleanup routine failed completely:", err);
    alert(`Error cleaning files: ${err.message}`);
  }
};

async function fetchJobs() {
  try {
    const res = await fetch("/jobs");
    const data = await res.json();
    allJobs = data.jobs || [];
    renderJobs(allJobs);
    if (document.getElementById("tab-folders")?.classList.contains("active")) {
      updateFolderJobsUI();
    }
  } catch (e) {
    console.error("Failed to fetch jobs", e);
  }
}

document
  .getElementById("refresh-jobs-btn")
  ?.addEventListener("click", fetchJobs);

function formatETA(seconds) {
    if (!seconds || seconds <= 0) return "Calculating...";
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}m ${s}s remaining`;
}

function renderJobs(jobs) {
  const container = document.getElementById("jobs-list");
  container.innerHTML = "";

  if (jobs.length === 0) {
    container.innerHTML = '<p style="opacity: 0.7;">No jobs.</p>';
    return;
  }

  // Sort jobs by created_at desc
  jobs.sort((a, b) => b.created_at - a.created_at);

  jobs.forEach((job) => {
    const jobCard = document.createElement("div");
    jobCard.className = "job-card";

    const statusColors = {
      queued: "var(--vscode-accent)",
      running: "var(--vscode-success)",
      paused: "#ce9178",
      completed: "#4ec9b0",
      cancelled: "var(--vscode-error)",
    };
    const sColor = statusColors[job.status] || "gray";
    const canDelete = ["completed", "cancelled", "paused"].includes(job.status);
    const etaString = job.status === "running" ? `<span style="margin-left: 10px; color: #aaa;">⏱️ ETA: ${formatETA(job.eta_seconds)}</span>` : "";
    
    const processedImages = job.processed_images || [];
    const processedCount = processedImages.length;
    let totalCount = job.total_images;
    
    if (!totalCount && job.progress_percent > 0) {
        totalCount = Math.round(processedCount / (job.progress_percent / 100));
    } else if (!totalCount || job.status === "completed") {
        totalCount = processedCount;
    }

    // --- Contextual Circular Slider Queues ---
    let sequentialQueue = [];
    let last5Html = "";
    let next5Html = "";

    if (job.status === "running") {
        // 1. Map Last 5 Processed
        const last5Array = processedImages.slice(-5);
        const last5Mapped = last5Array.map(path => ({ path, name: path.split("/").pop() }));

        // 2. Map Current Active Image
        const currentImgObj = job.current_image ? { path: job.current_image, name: job.current_image.split("/").pop() } : null;

        // 3. Map Next 5 Up from Python backend response
        const next5Array = job.queued_images || [];
        const next5Mapped = next5Array.map(path => ({ path, name: path.split("/").pop() }));

        // Combine all valid items into the active sequential slideshow viewer scope
        sequentialQueue = [...last5Mapped];
        if (currentImgObj) sequentialQueue.push(currentImgObj);
        sequentialQueue = [...sequentialQueue, ...next5Mapped];

        // Generate Last 5 Row
        if (last5Mapped.length > 0) {
            last5Html = last5Mapped.map(img => `
                <div class="seq-thumb-trigger" data-img-path="${img.path}" style="width: 60px; text-align: center; cursor: pointer;">
                    <div style="width: 60px; height: 60px; background: #121216; border: 1px solid #444; border-radius: 4px; overflow: hidden; display: flex; align-items: center; justify-content: center;">
                        <img src="/image?path=${encodeURIComponent(img.path)}" style="width: 100%; height: 100%; object-fit: cover;" onerror="this.outerHTML='<span>🖼️</span>';">
                    </div>
                    <div style="font-size: 0.65rem; color: #888; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-top: 2px;" title="${img.name}">${img.name}</div>
                </div>
            `).join('');
        } else {
            last5Html = `<span style="font-size: 0.75rem; color: #555; font-style: italic;">None yet</span>`;
        }

        // Generate Next 5 Row using genuine backend pending array elements
        if (next5Mapped.length > 0) {
            next5Html = next5Mapped.map(img => `
                <div class="seq-thumb-trigger" data-img-path="${img.path}" style="width: 60px; text-align: center; cursor: pointer;">
                    <div style="width: 60px; height: 60px; background: #121216; border: 1px solid #333; border-radius: 4px; overflow: hidden; display: flex; align-items: center; justify-content: center; opacity: 0.6;">
                        <img src="/image?path=${encodeURIComponent(img.path)}" style="width: 100%; height: 100%; object-fit: cover;" onerror="this.outerHTML='<span>⏳</span>';">
                    </div>
                    <div style="font-size: 0.65rem; color: #666; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-top: 2px;" title="${img.name}">${img.name}</div>
                </div>
            `).join('');
        } else {
            next5Html = `<span style="font-size: 0.75rem; color: #555; font-style: italic;">Queue empty</span>`;
        }
    }

    jobCard.innerHTML = `
            <div class="job-header">
              <div>
                  <strong>Folder:</strong> ${job.folder_path.split("/").pop()}
                  <span style="font-size: 0.8rem; opacity: 0.7; margin-left: 10px;">ID: ${job.job_id}</span>
                  ${etaString}
              </div>
              <div style="display: flex; align-items: center; gap: 10px;">
                  <span style="color: ${sColor}; font-weight: bold; text-transform: capitalize;">
                      <span class="status-dot" style="background-color: ${sColor};"></span> ${job.status}
                  </span>
                  ${job.status === "running" || job.status === "queued" ? `<button onclick="pauseJob('${job.job_id}')" style="padding: 2px 8px;">Pause</button>` : ""}
                  ${job.status === "paused" ? `<button onclick="resumeJob('${job.job_id}')" style="padding: 2px 8px;">Resume</button>` : ""}
                  ${(job.status === "running" || job.status === "queued" || job.status === "paused") ? `<button onclick="cancelJob('${job.job_id}')" style="padding: 2px 8px; color: #f48771; border-color: #f48771;">Stop</button>` : ""}
                  ${canDelete ? `<button onclick="deleteJobRecord('${job.job_id}')" style="padding: 2px 8px; color: #ff4d4d; border-color: #ff4d4d;">Delete</button>` : ""}
              </div>
            </div>
            
            ${job.status === "running" && job.current_image ? `
            <div class="seq-thumb-trigger" data-img-path="${job.current_image}" style="font-size: 0.78rem; color: #aaa; margin-bottom: 12px; padding: 6px 10px; background: rgba(78,201,176,0.06); border-left: 3px solid #4ec9b0; border-radius: 4px; display: flex; align-items: center; gap: 12px; cursor: pointer; transition: background 0.2s;" onmouseenter="this.style.background='rgba(78,201,176,0.12)'" onmouseleave="this.style.background='rgba(78,201,176,0.06)'">
                <div style="width: 42px; height: 42px; background-color: #2a2d35; border: 1px solid #444; border-radius: 4px; display: flex; align-items: center; justify-content: center; overflow: hidden; flex-shrink: 0;">
                    <img src="/image?path=${encodeURIComponent(job.current_image)}" style="width: 100%; height: 100%; object-fit: cover;" onerror="this.outerHTML='<span style=\\'font-size: 1.2rem;\\'>🖼️</span>';">
                </div>
                <div style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                    <span style="display: block; font-size: 0.7rem; opacity: 0.6; text-transform: uppercase; letter-spacing: 0.5px; display: flex; align-items: center; gap: 4px;">Currently Processing <span style="font-size: 0.6rem;">🔍 Click to track loop timeline</span></span>
                    <span style="color: #4ec9b0; font-family: monospace; font-weight: bold; font-size: 0.85rem;">${job.current_image.split("/").pop()}</span>
                </div>
            </div>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 15px; background: rgba(0,0,0,0.15); padding: 8px; border-radius: 4px;">
                <div>
                    <div style="font-size: 0.7rem; color: #888; font-weight: bold; margin-bottom: 5px; text-transform: uppercase;">⏮️ Last 5 Processed</div>
                    <div style="display: flex; gap: 8px; flex-wrap: nowrap; overflow-x: auto;">${last5Html}</div>
                </div>
                <div>
                    <div style="font-size: 0.7rem; color: #888; font-weight: bold; margin-bottom: 5px; text-transform: uppercase;">⏭️ Next 5 Up</div>
                    <div style="display: flex; gap: 8px; flex-wrap: nowrap; overflow-x: auto;">${next5Html}</div>
                </div>
            </div>
            ` : ""}

            <div class="job-progress">
                <div class="progress-bar-bg">
                    <div class="progress-bar-fill" style="width: ${job.progress_percent || 0}%; background-color: ${sColor};"></div>
                </div>
                <div style="text-align: right; font-size: 0.8rem; margin-top: 5px;">
                    ${Math.round(job.progress_percent || 0)}% (${processedCount}/${totalCount} processed)
                </div>
            </div>
        `;

    // Connect click handlers to all generated real thumbnail paths
    jobCard.querySelectorAll(".seq-thumb-trigger").forEach((element) => {
        element.addEventListener("click", () => {
            const targetedPath = element.getAttribute("data-img-path");
            currentFolderImages = sequentialQueue;
            const indexMatch = sequentialQueue.findIndex(img => img.path === targetedPath);
            if (indexMatch !== -1) {
                openSlideshow(indexMatch);
            }
        });
    });

    container.appendChild(jobCard);
  });
}

// Register the global delete caller helper
window.deleteJobRecord = async (jobId) => {
    if (!confirm("Remove this job from history tracking log?")) return;
    await fetch(`/jobs/${jobId}`, { method: "DELETE" });
    fetchJobs(); // Update listing view
};

window.pauseJob = async (jobId) => {
  await fetch(`/jobs/${jobId}/pause`, { method: "POST" });
  fetchJobs();
};

window.resumeJob = async (jobId) => {
  await fetch(`/jobs/${jobId}/resume`, { method: "POST" });
  fetchJobs();
};

window.cancelJob = async (jobId) => {
  await fetch(`/jobs/${jobId}/cancel`, { method: "POST" });
  fetchJobs();
};

window.startFolderJob = async (path) => {
  try {
    await fetch("/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ folder_path: path }),
    });
    fetchJobs();
  } catch (e) {
    console.error("Failed to start job", e);
  }
};

// --- Slideshow ---
const slideshowOverlay = document.getElementById("slideshow-overlay");
const slideshowImg = document.getElementById("slideshow-img");
const captionPanel = document.getElementById("slideshow-caption-panel");
const captionContent = document.getElementById("slideshow-caption-content");

function openSlideshow(index) {
  if (!currentFolderImages[index]) return;
  currentSlideshowIndex = index;
  slideshowOverlay.style.display = "flex";
  updateSlideshow();
}

async function loadYmlForCurrentImage() {
  const imgData = currentFolderImages[currentSlideshowIndex];
  if (!imgData) return;

  captionContent.textContent = "Loading extraction data...";

  try {
    const res = await fetch(`/image/yml?path=${encodeURIComponent(imgData.path)}`);
    if (res.ok) {
      const yamlText = await res.text();
      captionContent.textContent = yamlText;
      Prism.highlightElement(captionContent);
    } else if (res.status === 404) {
      captionContent.textContent = "No extraction data available for this image.";
    } else {
      captionContent.textContent = `Error loading data: HTTP ${res.status}`;
    }
  } catch (e) {
    captionContent.textContent = "Failed to load extraction data.";
  }
}

function updateSlideshow() {
  const imgData = currentFolderImages[currentSlideshowIndex];
  if (!imgData) return;

  const titleEl = document.getElementById("slideshow-title");
  if (titleEl) titleEl.textContent = imgData.name;

  slideshowImg.alt = `Image: ${imgData.name}`;
  slideshowImg.src = `/image?path=${encodeURIComponent(imgData.path)}`;

  // Only reload YML if caption panel is currently visible
  if (captionPanel && captionPanel.style.display !== "none") {
    loadYmlForCurrentImage();
  } else {
    captionContent.textContent = "";
  }
}

document.getElementById("slideshow-close")?.addEventListener("click", () => {
  slideshowOverlay.style.display = "none";
});

document.getElementById("slideshow-prev")?.addEventListener("click", () => {
  currentSlideshowIndex =
    (currentSlideshowIndex - 1 + currentFolderImages.length) %
    currentFolderImages.length;
  updateSlideshow();
});

document.getElementById("slideshow-next")?.addEventListener("click", () => {
  currentSlideshowIndex =
    (currentSlideshowIndex + 1) % currentFolderImages.length;
  updateSlideshow();
});

document.getElementById("toggle-caption-btn")?.addEventListener("click", () => {
  const captionPanel = document.getElementById("slideshow-caption-panel");
  const resizeHandle = document.getElementById("slideshow-resize-handle");
  if (captionPanel) {
    const isNowVisible = captionPanel.style.display === "none";
    captionPanel.style.display = isNowVisible ? "flex" : "none";
    if (resizeHandle) resizeHandle.style.display = isNowVisible ? "block" : "none";
    if (isNowVisible) {
      loadYmlForCurrentImage();
    }
  }
});

// --- Sidebar Resize Handle Logic ---
(function () {
  const handle = document.getElementById("slideshow-resize-handle");
  const handleInner = document.getElementById("resize-handle-inner");
  const panel = document.getElementById("slideshow-caption-panel");
  if (!handle || !panel) return;

  let isResizing = false;
  let startX = 0;
  let startWidth = 0;

  handle.addEventListener("mouseenter", () => {
    if (handleInner) {
      handleInner.style.background = "#0066ff";
      handleInner.style.width = "4px";
    }
  });
  handle.addEventListener("mouseleave", () => {
    if (!isResizing && handleInner) {
      handleInner.style.background = "#333";
      handleInner.style.width = "2px";
    }
  });

  handle.addEventListener("mousedown", (e) => {
    isResizing = true;
    startX = e.clientX;
    startWidth = panel.offsetWidth;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    if (handleInner) {
      handleInner.style.background = "#0066ff";
      handleInner.style.width = "4px";
    }
    e.preventDefault();
  });

  document.addEventListener("mousemove", (e) => {
    if (!isResizing) return;
    // Dragging left increases width; right decreases it
    const delta = startX - e.clientX;
    const newWidth = Math.min(
      Math.max(startWidth + delta, 180),
      window.innerWidth * 0.8
    );
    panel.style.width = newWidth + "px";
  });

  document.addEventListener("mouseup", () => {
    if (!isResizing) return;
    isResizing = false;
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
    if (handleInner) {
      handleInner.style.background = "#333";
      handleInner.style.width = "2px";
    }
  });
})();

window.addEventListener("keydown", (e) => {
  if (slideshowOverlay.style.display === "flex") {
    if (e.key === "Escape") slideshowOverlay.style.display = "none";
    if (e.key === "ArrowRight")
      document.getElementById("slideshow-next").click();
    if (e.key === "ArrowLeft")
      document.getElementById("slideshow-prev").click();
  }
});

// --- API Stats / Existing code ---
let timeLeft = 60;
const timerDisplay = document.getElementById("refresh-timer");

async function fetchPerformance() {
  try {
    const response = await fetch("/performance/summary");
    if (!response.ok) return;
    const data = await response.json();
    renderPerformance(data);
  } catch (e) {
    console.error("Failed to fetch performance stats", e);
  }
}

document
  .getElementById("force-refresh-btn")
  ?.addEventListener("click", function () {
    fetchPerformance();
    timeLeft = 60;
    if (timerDisplay) timerDisplay.textContent = `Refreshes in ${timeLeft}s`;
  });

function renderPerformance(data) {
  const perfBody = document.querySelector("#perf-table tbody");
  const modelBody = document.querySelector("#model-table tbody");
  if (!perfBody || !modelBody) return;

  let generalHtml = "";
  if (data.total_requests !== undefined) {
    generalHtml += `<tr><td>Total Requests</td><td>${data.total_requests}</td></tr>`;
    generalHtml += `<tr><td>Server Uptime</td><td>${formatUptime(data.uptime_seconds)}</td></tr>`;
  } else {
    generalHtml = '<tr><td colspan="2">No data available</td></tr>';
  }
  perfBody.innerHTML = generalHtml;

  if (data.request_types && Array.isArray(data.request_types)) {
    let modelHtml = "";
    data.request_types.forEach((rt) => {
      const typeClass = `type-${rt.request_type.toLowerCase()}`;
      modelHtml += `
                <tr class="group-header ${typeClass}">
                    <td colspan="5">
                        ${rt.request_type.toUpperCase()} 
                        <span style="font-weight: normal; font-size: 0.8rem; color: var(--vscode-fg); margin-left: 10px;">
                            (${rt.total_requests} requests)
                        </span>
                    </td>
                </tr>
            `;
      if (rt.model_breakdown && Array.isArray(rt.model_breakdown)) {
        rt.model_breakdown.forEach((m) => {
          modelHtml += `
                        <tr class="sub-row">
                            <td class="${typeClass}" style="padding-left: 20px;">${m.model}</td>
                            <td>${m.count}</td>
                            <td>${m.avg_time.toFixed(3)}</td>
                            <td>${m.min_time.toFixed(3)}</td>
                            <td>${m.max_time.toFixed(3)}</td>
                        </tr>
                    `;
        });
      }
    });
    modelBody.innerHTML =
      modelHtml || '<tr><td colspan="5">No model usage yet</td></tr>';
  } else {
    modelBody.innerHTML =
      '<tr><td colspan="5">No detailed model stats available</td></tr>';
  }
}

function formatUptime(seconds) {
  if (!seconds) return "0s";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  return `${h}h ${m}m ${s}s`;
}

// Auto-refresh loop for performance
setInterval(() => {
  if (document.getElementById("tab-api")?.classList.contains("active")) {
    timeLeft--;
    if (timeLeft <= 0) {
      fetchPerformance();
      timeLeft = 60;
    }
    if (timerDisplay) timerDisplay.textContent = `Refreshes in ${timeLeft}s`;
  }
}, 1000);

// Also poll jobs if jobs tab is active
setInterval(() => {
  if (document.getElementById("tab-jobs")?.classList.contains("active")) {
    fetchJobs();
  }
}, 3000);

async function cleanCurrentFolder(folderPath) {
    if (!confirm(`Are you sure you want to delete all generated sidecar .yml files inside: ${folderPath}?`)) return;
    
    try {
        const response = await fetch("/folders/clean", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ path: folderPath })
        });
        const data = await response.json();
        alert(`Cleaned up ${data.deleted_files_count || 0} sidecar files successfully.`);
        loadPath(folderPath); // Refresh UI layout
    } catch (e) {
        console.error("Failed to clean sidecar collection assets", e);
    }
}