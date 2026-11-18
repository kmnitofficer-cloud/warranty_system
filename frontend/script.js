/**
 * EquipGuard - Device Warranty Management & Notification System
 * Modern SaaS Frontend Logic, Chart.js Visualizations, and Streamlit Bridge
 */

// Global State
const state = {
  user: null,
  devices: [],
  notifications: [],
  analytics: {},
  cloudSync: { configured: false, email: null, status: "Local Storage" },
  activeTab: "dashboard",
  filters: {
    category: "all",
    department: "all",
    status: "all",
    search: "",
    warrantyHorizon: "all"
  },
  charts: {
    statusDoughnut: null,
    categoryBar: null,
    departmentBar: null
  },
  isStreamlitConnected: false
};

// =========================================================================
// Streamlit Custom Component Protocol Bridge
// =========================================================================

function sendComponentReady() {
  window.parent.postMessage({
    isStreamlitMessage: true,
    type: "streamlit:componentReady",
    apiVersion: 1
  }, "*");
}

function sendToStreamlit(action, payload = {}) {
  // Always ping componentReady before sending value to ensure handshake
  sendComponentReady();

  const message = {
    isStreamlitMessage: true,
    type: "streamlit:setComponentValue",
    dataType: "json",
    value: {
      action: action,
      payload: payload,
      timestamp: Date.now()
    }
  };
  window.parent.postMessage(message, "*");
}

function notifyFrameHeight() {
  const height = Math.max(
    document.documentElement.scrollHeight,
    document.body.scrollHeight,
    window.innerHeight || 850
  );
  window.parent.postMessage({
    isStreamlitMessage: true,
    type: "streamlit:setFrameHeight",
    height: height
  }, "*");
}

// Listen for incoming state from Streamlit backend
window.addEventListener("message", function(event) {
  if (event.data && event.data.type === "streamlit:render") {
    state.isStreamlitConnected = true;
    if (window._readyPingInterval) {
      clearInterval(window._readyPingInterval);
      window._readyPingInterval = null;
    }
    const { args } = event.data;
    if (args) {
      handleBackendSync(args);
    }
  }
});

// Send initial componentReady and keep pinging until Streamlit acknowledges
sendComponentReady();
window._readyPingInterval = setInterval(() => {
  if (state.isStreamlitConnected) {
    clearInterval(window._readyPingInterval);
    window._readyPingInterval = null;
  } else {
    sendComponentReady();
  }
}, 250);

setTimeout(() => {
  if (window._readyPingInterval) {
    clearInterval(window._readyPingInterval);
    window._readyPingInterval = null;
  }
}, 20000);

// =========================================================================
// Initialization & Demo Mock Data (Standalone Fallback)
// =========================================================================

document.addEventListener("DOMContentLoaded", function() {
  initEventListeners();
  notifyFrameHeight();
  showLoginView();
});

function handleBackendSync(args) {
  if (args.user) {
    state.user = args.user;
    hideLoginAlert();
    showAppView();
  } else if (!state.user) {
    showLoginView();
  }

  // Handle server-side authentication error feedback
  if (args.auth_error) {
    showLoginAlert(args.auth_error);
    const submitBtn = document.getElementById("btn-login-submit");
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerText = "Sign In to Dashboard";
    }
  }

  if (args.devices) {
    state.devices = args.devices;
  }
  if (args.notifications) {
    state.notifications = args.notifications;
  }
  if (args.analytics) {
    state.analytics = args.analytics;
  }
  if (args.cloud_sync) {
    state.cloudSync = args.cloud_sync;
  }

  // Handle direct file download requested from backend
  if (args.download_payload && args.download_payload.data) {
    downloadBase64File(
      args.download_payload.data,
      args.download_payload.filename,
      args.download_payload.mime
    );
    sendToStreamlit("clear_download_payload");
  }

  updateCloudSyncUI();
  updateUserInfoUI();
  renderDashboard();
  renderDevicesTable();
  renderWarrantiesTable();
  renderNotificationsList();
  renderReportsView();
  notifyFrameHeight();
}

// =========================================================================
// Event Listeners Setup
// =========================================================================

function initEventListeners() {
  // Login Form Submission
  const loginForm = document.getElementById("login-form");
  if (loginForm) {
    loginForm.addEventListener("submit", handleLoginSubmit);
  }

  // Logout Button
  const logoutBtn = document.getElementById("btn-logout");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", handleLogout);
  }

  // Navigation Items
  document.querySelectorAll(".nav-item").forEach(item => {
    item.addEventListener("click", () => {
      const tab = item.getAttribute("data-tab");
      if (tab) switchTab(tab);
    });
  });

  // Global Search Input
  const searchInput = document.getElementById("global-search-input");
  if (searchInput) {
    searchInput.addEventListener("input", (e) => {
      state.filters.search = e.target.value;
      if (state.activeTab !== "devices" && state.activeTab !== "warranties") {
        switchTab("devices");
      }
      renderDevicesTable();
      renderWarrantiesTable();
    });
  }

  // Device Filters
  const catFilter = document.getElementById("device-filter-category");
  const deptFilter = document.getElementById("device-filter-department");
  const statusFilter = document.getElementById("device-filter-status");

  if (catFilter) catFilter.addEventListener("change", (e) => { state.filters.category = e.target.value; renderDevicesTable(); });
  if (deptFilter) deptFilter.addEventListener("change", (e) => { state.filters.department = e.target.value; renderDevicesTable(); });
  if (statusFilter) statusFilter.addEventListener("change", (e) => { state.filters.status = e.target.value; renderDevicesTable(); });

  // Warranty Horizon Quick Filters
  document.querySelectorAll(".warranty-quick-filter").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".warranty-quick-filter").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      state.filters.warrantyHorizon = btn.getAttribute("data-filter");
      renderWarrantiesTable();
    });
  });

  // Header Add Device Button
  const headerAddBtn = document.getElementById("btn-header-add-device");
  if (headerAddBtn) headerAddBtn.addEventListener("click", openAddDeviceModal);

  // Device Form Submission
  const deviceForm = document.getElementById("device-form");
  if (deviceForm) deviceForm.addEventListener("submit", handleDeviceFormSubmit);

  // Notification Bell Drawer Toggle
  const notifBell = document.getElementById("btn-notification-bell");
  const notifDrawer = document.getElementById("notification-drawer");
  if (notifBell && notifDrawer) {
    notifBell.addEventListener("click", (e) => {
      e.stopPropagation();
      notifDrawer.classList.toggle("show");
    });
    document.addEventListener("click", (e) => {
      if (!notifDrawer.contains(e.target) && e.target !== notifBell) {
        notifDrawer.classList.remove("show");
      }
    });
  }

  // Mark All Notifications Read
  const markAllBtn = document.getElementById("btn-mark-all-read");
  if (markAllBtn) markAllBtn.addEventListener("click", handleMarkAllNotificationsRead);

  // Browser Notifications Request Button
  const browserNotifBtn = document.getElementById("btn-browser-notif");
  if (browserNotifBtn) browserNotifBtn.addEventListener("click", requestBrowserNotificationPermission);

  // Export Buttons
  const btnExportExcel = document.getElementById("btn-export-excel");
  const btnExportPdf = document.getElementById("btn-export-pdf");
  if (btnExportExcel) btnExportExcel.addEventListener("click", () => triggerExport("excel"));
  if (btnExportPdf) btnExportPdf.addEventListener("click", () => triggerExport("pdf"));

  // Edit from Details Modal Button
  const btnEditFromDetails = document.getElementById("btn-edit-from-details");
  if (btnEditFromDetails) {
    btnEditFromDetails.addEventListener("click", () => {
      const devId = btnEditFromDetails.getAttribute("data-device-id");
      closeDeviceDetailsModal();
      if (devId) openEditDeviceModal(devId);
    });
  }
}

// =========================================================================
// Navigation & Views
// =========================================================================

function switchTab(tabName) {
  state.activeTab = tabName;
  document.querySelectorAll(".nav-item").forEach(item => {
    if (item.getAttribute("data-tab") === tabName) {
      item.classList.add("active");
    } else {
      item.classList.remove("active");
    }
  });

  document.querySelectorAll(".tab-content").forEach(content => {
    content.style.display = "none";
  });

  const targetTab = document.getElementById(`tab-${tabName}`);
  if (targetTab) {
    targetTab.style.display = "block";
  }

  if (tabName === "dashboard") {
    renderDashboardCharts();
  } else if (tabName === "reports") {
    renderDepartmentChart();
  }

  notifyFrameHeight();
}

function showLoginView() {
  document.getElementById("login-view").style.display = "flex";
  document.getElementById("app-view").style.display = "none";
  notifyFrameHeight();
}

function showAppView() {
  document.getElementById("login-view").style.display = "none";
  document.getElementById("app-view").style.display = "block";
  switchTab(state.activeTab || "dashboard");
  notifyFrameHeight();
}

// =========================================================================
// Authentication Handlers (Streamlit Python Backend Driven)
// =========================================================================

function hideLoginAlert() {
  const alertBox = document.getElementById("login-alert");
  if (alertBox) {
    alertBox.style.display = "none";
    alertBox.innerHTML = "";
  }
}

function showLoginAlert(msg) {
  const alertBox = document.getElementById("login-alert");
  if (alertBox) {
    alertBox.innerHTML = `
      <div style="display: flex; align-items: flex-start; gap: 8px; text-align: left;">
        <span style="font-size: 16px;">⚠️</span>
        <div style="flex: 1; font-size: 13px; line-height: 1.4; word-break: break-word;">${msg}</div>
      </div>
    `;
    alertBox.style.display = "block";
  }
}

function handleLoginSubmit(e) {
  if (e) e.preventDefault();
  const emailInput = document.getElementById("login-email");
  const pwdInput = document.getElementById("login-password");

  const email = (emailInput ? emailInput.value : "").trim().toLowerCase();
  const password = pwdInput ? pwdInput.value : "";

  if (!email || !password) {
    showLoginAlert("Please enter both email and password.");
    return;
  }

  const submitBtn = document.getElementById("btn-login-submit");
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.innerText = "Signing in via Streamlit Backend...";
  }
  hideLoginAlert();

  // Send authentication request directly to Streamlit Python Backend
  sendToStreamlit("login", { email: email, password: password });

  // Timeout guard to re-enable button if network takes time
  setTimeout(() => {
    if (submitBtn && submitBtn.disabled && !state.user) {
      submitBtn.disabled = false;
      submitBtn.innerText = "Sign In to Dashboard";
    }
  }, 12000);
}

function handleLogout() {
  localStorage.removeItem("equipguard_user");
  state.user = null;
  sendToStreamlit("logout");
  showLoginView();
  showToast("Logged out successfully.", "info");
}

function updateUserInfoUI() {
  if (!state.user) return;
  const avatar = document.getElementById("sidebar-user-avatar");
  const name = document.getElementById("sidebar-user-name");
  const role = document.getElementById("sidebar-user-role");

  if (avatar) avatar.src = state.user.avatar || `https://api.dicebear.com/7.x/initials/svg?seed=${state.user.display_name}`;
  if (name) name.innerText = state.user.display_name || state.user.email;
  if (role) role.innerText = state.user.role || "Administrator";
}

function updateCloudSyncUI() {
  const pill = document.getElementById("cloud-sync-pill");
  const text = document.getElementById("cloud-sync-text");
  const settingsStatus = document.getElementById("settings-drive-status");
  const settingsEmail = document.getElementById("settings-drive-email");
  const copyBtn = document.getElementById("btn-copy-sa-email");
  const headerBadge = document.getElementById("drive-header-status-badge");
  const isConfigured = state.cloudSync && state.cloudSync.configured;
  const emailVal = state.cloudSync ? state.cloudSync.email : null;

  if (isConfigured) {
    if (pill) {
      pill.classList.add("connected");
      pill.innerHTML = `<span class="pulse-beacon"></span><span>Drive Synced</span>`;
      pill.title = `Google Drive connected (${emailVal || ''})`;
    }
    if (headerBadge) {
      headerBadge.innerHTML = `<span class="badge badge-success" style="background: rgba(16, 185, 129, 0.2); color: #34d399; font-size: 12px;">🟢 Cloud Synced Active</span>`;
    }
    if (settingsStatus) {
      settingsStatus.innerHTML = `<span class="pulse-beacon"></span><span style="color: var(--success);">Google Drive Connected & Synchronized</span>`;
    }
    if (settingsEmail) {
      settingsEmail.innerText = emailVal || "Service Account Connected";
      settingsEmail.style.color = "var(--primary)";
    }
    if (copyBtn && emailVal) {
      copyBtn.style.display = "inline-flex";
    }
    const fileIdEl = document.getElementById("settings-drive-fileid");
    const btnOpenDrive = document.getElementById("btn-open-in-drive");
    if (state.cloudSync.file_id) {
      const driveUrl = `https://drive.google.com/file/d/${state.cloudSync.file_id}/view`;
      if (fileIdEl) {
        fileIdEl.innerHTML = `File ID: <a href="${driveUrl}" target="_blank" style="color: var(--primary); text-decoration: underline; font-family: monospace; font-weight: 600;">${state.cloudSync.file_id}</a> ↗ (Live in Google Drive)`;
      }
      if (btnOpenDrive) {
        btnOpenDrive.href = driveUrl;
        btnOpenDrive.style.display = "inline-flex";
      }
    }
  } else {
    if (pill) {
      pill.classList.remove("connected");
      pill.innerHTML = `<span class="status-indicator-dot" style="background: #ef4444;"></span><span style="color: #ef4444;">Drive Disconnected</span>`;
      pill.title = "Google Drive Disconnected. Connect Google Drive in Settings.";
    }
    if (headerBadge) {
      headerBadge.innerHTML = `<span class="badge badge-danger" style="background: rgba(239, 68, 68, 0.2); color: #f87171; font-size: 12px;">⚠️ Google Drive Disconnected</span>`;
    }
    if (settingsStatus) {
      settingsStatus.innerHTML = `<span class="status-indicator-dot" style="background: #ef4444;"></span><span style="color: #ef4444;">Google Drive Disconnected (Cloud Database Offline)</span>`;
    }
    if (settingsEmail) {
      settingsEmail.innerText = "No valid Google Service Account connected. Paste your Service Account JSON below or configure Streamlit Secrets.";
      settingsEmail.style.color = "var(--text-muted)";
    }
    if (copyBtn) {
      copyBtn.style.display = "none";
    }
  }
}

function copyServiceAccountEmail() {
  const email = state.cloudSync ? state.cloudSync.email : null;
  if (!email) return;

  navigator.clipboard.writeText(email).then(() => {
    showToast("Service Account Email copied to clipboard!", "success");
  }).catch(() => {
    // Fallback for iframe copy
    const temp = document.createElement("textarea");
    temp.value = email;
    document.body.appendChild(temp);
    temp.select();
    document.execCommand("copy");
    document.body.removeChild(temp);
    showToast("Service Account Email copied to clipboard!", "success");
  });
}

function togglePasteJsonBox() {
  const container = document.getElementById("paste-json-container");
  if (!container) return;
  container.style.display = (container.style.display === "none" || container.style.display === "") ? "block" : "none";
}

function handleDriveFileSelected(event) {
  const file = event.target.files && event.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = function(e) {
    const content = e.target.result;
    processDriveJsonContent(content);
  };
  reader.readAsText(file);
}

function handlePasteJsonSubmit() {
  const textarea = document.getElementById("paste-json-textarea");
  if (!textarea) return;
  const content = textarea.value.trim();
  if (!content) {
    alert("Please paste your service account JSON contents.");
    return;
  }
  processDriveJsonContent(content);
}

function processDriveJsonContent(rawContent) {
  try {
    const parsed = JSON.parse(rawContent);
    if (!parsed.client_email || parsed.type !== "service_account") {
      alert("Invalid JSON format. The file must be a Google Cloud Service Account key containing 'client_email' and 'type': 'service_account'.");
      return;
    }

    sendToStreamlit("save_drive_credentials", { json_content: rawContent });
    showToast(`Connecting Service Account (${parsed.client_email})...`, "info");
  } catch (err) {
    alert("Invalid JSON syntax: " + err.message);
  }
}

// =========================================================================
// Dashboard Rendering & Charts
// =========================================================================

function renderDashboard() {
  const analytics = state.analytics || {};
  const total = analytics.total_devices || state.devices.length;
  const active = analytics.active_warranties || 0;
  const activePct = analytics.active_percentage || (total > 0 ? ((active / total) * 100).toFixed(1) : 0);
  const expiring = analytics.expiring_soon || 0;
  const expired = analytics.expired_warranties || 0;
  const unreadNotifs = analytics.unread_notifications || 0;

  document.getElementById("metric-total-devices").innerText = total;
  document.getElementById("metric-active-warranties").innerText = active;
  document.getElementById("metric-active-percent").innerText = `${activePct}% active coverage`;
  document.getElementById("metric-expiring-soon").innerText = expiring;
  document.getElementById("metric-expired-warranties").innerText = expired;
  document.getElementById("metric-unread-notifs").innerText = unreadNotifs;

  // Sidebar badge for expiring
  const sidebarBadge = document.getElementById("sidebar-expiring-badge");
  if (sidebarBadge) {
    if (expiring > 0) {
      sidebarBadge.innerText = expiring;
      sidebarBadge.style.display = "inline-block";
    } else {
      sidebarBadge.style.display = "none";
    }
  }

  renderUpcomingList();
  renderActivityTimeline();
  renderDashboardCharts();
}

function renderUpcomingList() {
  const container = document.getElementById("upcoming-expirations-list");
  if (!container) return;

  const urgent = (state.analytics.upcoming_expirations || []).slice(0, 5);
  if (urgent.length === 0) {
    container.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 18px; font-size: 13px;">No expiring equipment detected. All active warranties are healthy!</div>`;
    return;
  }

  container.innerHTML = urgent.map(dev => `
    <div class="expiring-item" onclick="openDeviceDetails('${dev.Device_ID}')" style="cursor: pointer;">
      <div class="expiring-device-info">
        <img src="${dev.Image_URL || 'https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=300'}" class="device-thumb" alt="${dev.Device_Name}">
        <div>
          <div class="expiring-device-name">${dev.Device_Name}</div>
          <div class="expiring-device-sub">S/N: ${dev.Serial_Number} • ${dev.Department}</div>
        </div>
      </div>
      <div style="text-align: right;">
        <span class="badge ${dev.badge_class || 'badge-warning'}">${dev.countdown_text || 'Expiring Soon'}</span>
        <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">${dev.Warranty_End_Date}</div>
      </div>
    </div>
  `).join("");
}

function renderActivityTimeline() {
  const container = document.getElementById("activity-timeline");
  if (!container) return;

  const logs = (state.analytics.activity_logs || []).slice(0, 6);
  if (logs.length === 0) {
    container.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 18px; font-size: 13px;">No recent activity logs.</div>`;
    return;
  }

  container.innerHTML = logs.map(log => {
    let dateStr = log.Timestamp || "";
    try {
      const dt = new Date(log.Timestamp);
      dateStr = dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + " • " + dt.toLocaleDateString();
    } catch(e) {}

    return `
      <div class="activity-item">
        <div class="activity-dot"></div>
        <div class="activity-content">
          <div class="activity-title">${log.Action} <span style="font-weight: 400; color: var(--text-muted);">(${log.Device_ID})</span></div>
          <div class="activity-desc">${log.Details}</div>
          <div class="activity-time">${dateStr} • By ${log.User_Email}</div>
        </div>
      </div>
    `;
  }).join("");
}

function renderDashboardCharts() {
  if (typeof Chart === "undefined") return;

  // Chart 1: Warranty Status Doughnut Chart
  const ctxStatus = document.getElementById("chart-warranty-status");
  if (ctxStatus) {
    const dist = state.analytics.status_distribution || { "Active": 5, "Expiring Soon": 2, "Expired": 1 };
    if (state.charts.statusDoughnut) state.charts.statusDoughnut.destroy();

    state.charts.statusDoughnut = new Chart(ctxStatus, {
      type: "doughnut",
      data: {
        labels: ["Active", "Expiring Soon", "Expired"],
        datasets: [{
          data: [dist["Active"] || 0, dist["Expiring Soon"] || 0, dist["Expired"] || 0],
          backgroundColor: ["#10b981", "#f59e0b", "#ef4444"],
          borderWidth: 2,
          borderColor: "#ffffff"
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "bottom", labels: { boxWidth: 12, font: { family: "Inter", size: 12 } } }
        },
        cutout: "70%"
      }
    });
  }

  // Chart 2: Devices by Category Bar Chart
  const ctxCategory = document.getElementById("chart-devices-category");
  if (ctxCategory) {
    const catDist = state.analytics.category_distribution || {};
    const labels = Object.keys(catDist);
    const dataVals = Object.values(catDist);

    if (state.charts.categoryBar) state.charts.categoryBar.destroy();

    state.charts.categoryBar = new Chart(ctxCategory, {
      type: "bar",
      data: {
        labels: labels,
        datasets: [{
          label: "Registered Devices",
          data: dataVals,
          backgroundColor: "#3b82f6",
          borderRadius: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false }
        },
        scales: {
          y: { beginAtZero: true, ticks: { stepSize: 1, font: { family: "Inter" } }, grid: { color: "#f1f5f9" } },
          x: { ticks: { font: { family: "Inter", size: 11 } }, grid: { display: false } }
        }
      }
    });
  }
}

// =========================================================================
// Device Inventory Table Rendering & Search
// =========================================================================

function renderDevicesTable() {
  const tbody = document.getElementById("devices-table-body");
  if (!tbody) return;

  const filtered = filterDevices(state.devices);
  document.getElementById("devices-count-label").innerText = filtered.length;

  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; padding: 36px; color: var(--text-muted);">No devices match your filter criteria.</td></tr>`;
    return;
  }

  tbody.innerHTML = filtered.map(d => `
    <tr>
      <td>
        <div style="display: flex; align-items: center; gap: 12px;">
          <img src="${d.Image_URL || 'https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=300'}" style="width: 38px; height: 38px; border-radius: 6px; object-fit: cover;" alt="Device">
          <div>
            <div style="font-weight: 600; color: var(--text-main);">${d.Device_Name}</div>
            <div style="font-size: 11px; color: var(--text-muted);">${d.Brand || ''} ${d.Model_Number || ''} • <strong>${d.Device_ID}</strong></div>
          </div>
        </div>
      </td>
      <td><span class="badge badge-secondary">${d.Category}</span></td>
      <td><code style="background: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-size: 12px;">${d.Serial_Number}</code></td>
      <td>${d.Assigned_User || 'Unassigned'}</td>
      <td>${d.Department || 'IT'}</td>
      <td>
        <div>${d.Warranty_End_Date}</div>
        <div style="font-size: 11px; color: var(--text-muted);">${d.countdown_text || ''}</div>
      </td>
      <td><span class="badge ${d.badge_class || 'badge-success'}">${d.status || 'Active'}</span></td>
      <td style="text-align: right;">
        <div class="action-btns" style="justify-content: flex-end;">
          <button type="button" class="action-btn" title="Inspect Specs" onclick="openDeviceDetails('${d.Device_ID}')">👁 View</button>
          <button type="button" class="action-btn" title="Edit Record" onclick="openEditDeviceModal('${d.Device_ID}')">✏ Edit</button>
          <button type="button" class="action-btn action-btn-danger" title="Delete Device" onclick="deleteDevice('${d.Device_ID}')">🗑</button>
        </div>
      </td>
    </tr>
  `).join("");
}

function filterDevices(devicesList) {
  return devicesList.filter(d => {
    // Search filter
    if (state.filters.search) {
      const q = state.filters.search.toLowerCase();
      const match = (
        (d.Device_Name || "").toLowerCase().includes(q) ||
        (d.Serial_Number || "").toLowerCase().includes(q) ||
        (d.Device_ID || "").toLowerCase().includes(q) ||
        (d.Brand || "").toLowerCase().includes(q) ||
        (d.Model_Number || "").toLowerCase().includes(q) ||
        (d.Assigned_User || "").toLowerCase().includes(q)
      );
      if (!match) return false;
    }

    // Category filter
    if (state.filters.category !== "all" && d.Category !== state.filters.category) return false;

    // Department filter
    if (state.filters.department !== "all" && d.Department !== state.filters.department) return false;

    // Status filter
    if (state.filters.status !== "all" && d.status !== state.filters.status) return false;

    return true;
  });
}

// =========================================================================
// Warranty Management Center Table
// =========================================================================

function renderWarrantiesTable() {
  const tbody = document.getElementById("warranties-table-body");
  if (!tbody) return;

  let list = [...state.devices];

  // Apply horizon filter
  if (state.filters.warrantyHorizon === "7") {
    list = list.filter(d => d.days_remaining !== null && d.days_remaining >= 0 && d.days_remaining <= 7);
  } else if (state.filters.warrantyHorizon === "30") {
    list = list.filter(d => d.days_remaining !== null && d.days_remaining >= 0 && d.days_remaining <= 30);
  } else if (state.filters.warrantyHorizon === "expired") {
    list = list.filter(d => d.days_remaining !== null && d.days_remaining < 0);
  } else if (state.filters.warrantyHorizon === "active") {
    list = list.filter(d => d.status === "Active");
  }

  // Sort by Expiration Date ascending (most urgent first)
  list.sort((a, b) => (a.days_remaining || 0) - (b.days_remaining || 0));

  if (list.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 36px; color: var(--text-muted);">No warranty records in this horizon.</td></tr>`;
    return;
  }

  tbody.innerHTML = list.map(d => `
    <tr>
      <td>
        <div style="font-weight: 600;">${d.Device_Name}</div>
        <div style="font-size: 11px; color: var(--text-muted);">${d.Category} • ${d.Device_ID}</div>
      </td>
      <td><code>${d.Serial_Number}</code></td>
      <td>${d.Assigned_User} (${d.Department})</td>
      <td>${d.Warranty_Start_Date || 'N/A'} → <strong>${d.Warranty_End_Date}</strong></td>
      <td>
        <span class="badge ${d.badge_class || 'badge-secondary'}">${d.countdown_text}</span>
      </td>
      <td><span class="badge ${d.badge_class || 'badge-secondary'}">${d.status}</span></td>
      <td style="text-align: right;">
        <button type="button" class="btn-secondary" style="padding: 4px 10px; font-size: 12px;" onclick="openEditDeviceModal('${d.Device_ID}')">Renew / Update</button>
      </td>
    </tr>
  `).join("");
}

// =========================================================================
// Device Modal Handlers (Add / Edit / Delete / Inspect)
// =========================================================================

function recalculateDuration() {
  const startVal = document.getElementById("form-warranty-start").value;
  const endVal = document.getElementById("form-warranty-end").value;
  const durationField = document.getElementById("form-duration");

  if (!startVal || !endVal) return;
  const start = new Date(startVal);
  const end = new Date(endVal);

  if (end >= start) {
    const months = (end.getFullYear() - start.getFullYear()) * 12 + (end.getMonth() - start.getMonth());
    durationField.value = Math.max(1, months);
  } else {
    durationField.value = 0;
  }
}

function openAddDeviceModal() {
  document.getElementById("device-modal-title").innerText = "Register New Device";
  document.getElementById("form-is-edit").value = "false";
  document.getElementById("form-device-id").value = "DEV-Auto";
  document.getElementById("device-form").reset();

  const todayStr = new Date().toISOString().split("T")[0];
  document.getElementById("form-warranty-start").value = todayStr;
  
  // Set default 1 year end date
  const nextYear = new Date();
  nextYear.setFullYear(nextYear.getFullYear() + 1);
  document.getElementById("form-warranty-end").value = nextYear.toISOString().split("T")[0];
  recalculateDuration();

  document.getElementById("device-modal").classList.add("show");
}

function openEditDeviceModal(deviceId) {
  const device = state.devices.find(d => d.Device_ID === deviceId);
  if (!device) return;

  document.getElementById("device-modal-title").innerText = `Edit Device (${device.Device_ID})`;
  document.getElementById("form-is-edit").value = "true";
  document.getElementById("form-device-id").value = device.Device_ID;
  document.getElementById("form-device-name").value = device.Device_Name || "";
  document.getElementById("form-category").value = device.Category || "Laptop";
  document.getElementById("form-brand").value = device.Brand || "";
  document.getElementById("form-model").value = device.Model_Number || "";
  document.getElementById("form-serial").value = device.Serial_Number || "";
  document.getElementById("form-user").value = device.Assigned_User || "";
  document.getElementById("form-department").value = device.Department || "IT";
  document.getElementById("form-purchase-date").value = device.Purchase_Date || "";
  document.getElementById("form-price").value = device.Purchase_Price || "";
  document.getElementById("form-supplier").value = device.Supplier || "";
  document.getElementById("form-warranty-start").value = device.Warranty_Start_Date || "";
  document.getElementById("form-warranty-end").value = device.Warranty_End_Date || "";
  document.getElementById("form-invoice").value = device.Invoice_Number || "";
  document.getElementById("form-image-url").value = device.Image_URL || "";
  document.getElementById("form-notes").value = device.Notes || "";

  recalculateDuration();
  document.getElementById("device-modal").classList.add("show");
}

function closeDeviceModal() {
  document.getElementById("device-modal").classList.remove("show");
}

function handleDeviceFormSubmit(e) {
  e.preventDefault();
  const isEdit = document.getElementById("form-is-edit").value === "true";
  const deviceId = document.getElementById("form-device-id").value;

  const payload = {
    Device_ID: isEdit ? deviceId : undefined,
    Device_Name: document.getElementById("form-device-name").value.trim(),
    Category: document.getElementById("form-category").value,
    Brand: document.getElementById("form-brand").value.trim(),
    Model_Number: document.getElementById("form-model").value.trim(),
    Serial_Number: document.getElementById("form-serial").value.trim(),
    Assigned_User: document.getElementById("form-user").value.trim(),
    Department: document.getElementById("form-department").value,
    Purchase_Date: document.getElementById("form-purchase-date").value,
    Purchase_Price: document.getElementById("form-price").value,
    Supplier: document.getElementById("form-supplier").value.trim(),
    Warranty_Start_Date: document.getElementById("form-warranty-start").value,
    Warranty_End_Date: document.getElementById("form-warranty-end").value,
    Invoice_Number: document.getElementById("form-invoice").value.trim(),
    Image_URL: document.getElementById("form-image-url").value.trim(),
    Notes: document.getElementById("form-notes").value.trim()
  };

  if (new Date(payload.Warranty_End_Date) < new Date(payload.Warranty_Start_Date)) {
    alert("Warranty End Date cannot be earlier than Warranty Start Date!");
    return;
  }

  // Prevent duplicate serial check on client
  const existingDup = state.devices.find(d => 
    d.Serial_Number.trim().toUpperCase() === payload.Serial_Number.trim().toUpperCase() &&
    (!isEdit || d.Device_ID !== deviceId)
  );
  if (existingDup) {
    alert(`A device with Serial Number "${payload.Serial_Number}" already exists (Device ID: ${existingDup.Device_ID}). Duplicate records are prevented.`);
    return;
  }

  const actionName = isEdit ? "update_device" : "add_device";
  sendToStreamlit(actionName, payload);

  closeDeviceModal();
  showToast(isEdit ? "Updating device record..." : "Saving new device...", "info");
}

function deleteDevice(deviceId) {
  if (confirm(`Are you sure you want to delete device ${deviceId}? This action will be audited.`)) {
    sendToStreamlit("delete_device", { Device_ID: deviceId });
    showToast(`Deleting ${deviceId}...`, "warning");
  }
}

function openDeviceDetails(deviceId) {
  const d = state.devices.find(item => item.Device_ID === deviceId);
  if (!d) return;

  const container = document.getElementById("device-details-body");
  const editBtn = document.getElementById("btn-edit-from-details");
  if (editBtn) editBtn.setAttribute("data-device-id", d.Device_ID);

  container.innerHTML = `
    <div style="display: flex; gap: 20px; margin-bottom: 20px;">
      <img src="${d.Image_URL || 'https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=300'}" style="width: 140px; height: 140px; border-radius: 10px; object-fit: cover; border: 1px solid var(--border-color);" alt="${d.Device_Name}">
      <div style="flex: 1;">
        <div style="display: flex; align-items: center; gap: 8px;">
          <span class="badge ${d.badge_class || 'badge-success'}">${d.status}</span>
          <span class="badge badge-secondary">${d.Category}</span>
        </div>
        <h2 style="font-size: 20px; font-weight: 700; color: var(--text-main); margin: 6px 0;">${d.Device_Name}</h2>
        <div style="font-size: 13px; color: var(--text-muted);">${d.Brand || ''} ${d.Model_Number || ''}</div>
        <div style="margin-top: 10px; font-size: 13px; font-weight: 600; color: var(--primary);">
          ${d.countdown_text}
        </div>
      </div>
    </div>

    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; font-size: 13px; background: #f8fafc; padding: 16px; border-radius: 8px; border: 1px solid var(--border-color); margin-bottom: 16px;">
      <div><strong>Device ID:</strong> ${d.Device_ID}</div>
      <div><strong>Hardware S/N:</strong> <code>${d.Serial_Number}</code></div>
      <div><strong>Assigned User:</strong> ${d.Assigned_User || 'Unassigned'}</div>
      <div><strong>Department:</strong> ${d.Department || 'IT'}</div>
      <div><strong>Warranty Period:</strong> ${d.Warranty_Start_Date} → ${d.Warranty_End_Date}</div>
      <div><strong>Duration:</strong> ${d.Warranty_Duration_Months || '12'} Months</div>
      <div><strong>Purchase Price:</strong> $${d.Purchase_Price ? Number(d.Purchase_Price).toFixed(2) : '0.00'}</div>
      <div><strong>Supplier:</strong> ${d.Supplier || 'N/A'}</div>
      <div><strong>Invoice #:</strong> ${d.Invoice_Number || 'N/A'}</div>
      <div><strong>Last Audit:</strong> ${d.Updated_At ? d.Updated_At.substring(0, 10) : 'N/A'}</div>
    </div>

    ${d.Notes ? `<div style="font-size: 13px; color: var(--text-muted); padding: 10px 0;"><strong>Remarks:</strong> ${d.Notes}</div>` : ''}
  `;

  document.getElementById("device-details-modal").classList.add("show");
}

function closeDeviceDetailsModal() {
  document.getElementById("device-details-modal").classList.remove("show");
}

// =========================================================================
// Notification Drawer & Browser Notifications
// =========================================================================

function renderNotificationsList() {
  const container = document.getElementById("notif-items-list");
  const badge = document.getElementById("notif-count-badge");
  const unreadCount = state.notifications.filter(n => n.Status === "unread").length;

  if (badge) {
    if (unreadCount > 0) {
      badge.innerText = unreadCount;
      badge.style.display = "inline-block";
    } else {
      badge.style.display = "none";
    }
  }

  if (!container) return;

  if (state.notifications.length === 0) {
    container.innerHTML = `<div style="padding: 24px; text-align: center; color: var(--text-muted); font-size: 13px;">No notifications. All warranties up to date.</div>`;
    return;
  }

  container.innerHTML = state.notifications.map(n => `
    <div class="notif-item ${n.Status === 'unread' ? 'unread' : ''}" onclick="handleNotificationClick('${n.Notification_ID}')">
      <div class="notif-icon-box" style="background: ${n.Urgency === 'critical' ? '#fee2e2' : '#fef3c7'}; color: ${n.Urgency === 'critical' ? '#ef4444' : '#f59e0b'};">
        ${n.Urgency === 'critical' ? '🛑' : '⚠️'}
      </div>
      <div style="flex: 1;">
        <div class="notif-text">${n.Message}</div>
        <div class="notif-time">${n.formatted_date || n.Notification_Date || ''} • <strong>${n.Device_ID}</strong></div>
      </div>
    </div>
  `).join("");
}

function handleNotificationClick(notifId) {
  sendToStreamlit("mark_notification_read", { Notification_ID: notifId });
}

function handleMarkAllNotificationsRead() {
  sendToStreamlit("mark_all_notifications_read");
  showToast("All notifications marked as read.", "success");
}

function requestBrowserNotificationPermission() {
  if (!("Notification" in window)) {
    alert("This browser does not support desktop notifications.");
    return;
  }

  Notification.requestPermission().then(permission => {
    if (permission === "granted") {
      showToast("Desktop browser notifications enabled!", "success");
      new Notification("EquipGuard Warranty Alert", {
        body: "Browser notifications successfully registered for expiring equipment.",
        icon: "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=100"
      });
    } else {
      showToast("Notification permission denied or dismissed.", "warning");
    }
  });
}

// =========================================================================
// Reports & Analytics View
// =========================================================================

function renderReportsView() {
  const analytics = state.analytics || {};
  document.getElementById("report-metric-this-month").innerText = analytics.expiring_this_month || 0;
  document.getElementById("report-metric-30d").innerText = analytics.expiring_30_days || 0;
  document.getElementById("report-metric-60d").innerText = analytics.expiring_60_days || 0;
  document.getElementById("report-metric-90d").innerText = analytics.expiring_90_days || 0;

  const assetVal = analytics.total_asset_value || 0;
  document.getElementById("report-total-asset-val").innerText = `$${Number(assetVal).toLocaleString('en-US', { minimumFractionDigits: 2 })}`;

  renderDepartmentChart();
}

function renderDepartmentChart() {
  const ctxDept = document.getElementById("chart-department-status");
  if (!ctxDept || typeof Chart === "undefined") return;

  const matrix = state.analytics.department_status_matrix || {};
  const labels = Object.keys(matrix);
  const activeData = labels.map(l => (matrix[l] && matrix[l].Active) || 0);
  const expiringData = labels.map(l => (matrix[l] && matrix[l]["Expiring Soon"]) || 0);
  const expiredData = labels.map(l => (matrix[l] && matrix[l].Expired) || 0);

  if (state.charts.departmentBar) state.charts.departmentBar.destroy();

  state.charts.departmentBar = new Chart(ctxDept, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [
        { label: "Active", data: activeData, backgroundColor: "#10b981" },
        { label: "Expiring Soon", data: expiringData, backgroundColor: "#f59e0b" },
        { label: "Expired", data: expiredData, backgroundColor: "#ef4444" }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { stacked: true, grid: { display: false } },
        y: { stacked: true, grid: { color: "#f1f5f9" } }
      },
      plugins: {
        legend: { position: "top", labels: { boxWidth: 12, font: { family: "Inter", size: 11 } } }
      }
    }
  });
}

function triggerExport(format) {
  sendToStreamlit(`export_${format}`, {
    filters: state.filters
  });
  showToast(`Generating ${format.toUpperCase()} export...`, "info");
}

function downloadBase64File(base64Data, filename, mimeType) {
  try {
    const byteCharacters = atob(base64Data);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
      byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    const blob = new Blob([byteArray], { type: mimeType });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    setTimeout(() => {
      document.body.removeChild(link);
      URL.revokeObjectURL(link.href);
    }, 100);
    showToast(`Export ready: ${filename}`, "success");
  } catch (err) {
    console.error("Base64 download error:", err);
    showToast("Download failed: " + err.message, "danger");
  }
}

// =========================================================================
// Toast Alerts
// =========================================================================

function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <span>${type === 'success' ? '✓' : type === 'warning' ? '⚠' : type === 'danger' ? '🛑' : 'ℹ'}</span>
    <span>${message}</span>
  `;

  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(100%)";
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}
