/**
 * EquipGuard - Enterprise Device Warranty & Asset Intelligence
 * Premium SaaS Frontend Logic, Modern Visualizations, and Streamlit Bridge
 * Designed to Linear, Stripe & Vercel design aesthetics.
 */

// =========================================================================
// Global Application State
// =========================================================================

const state = {
  authenticated: false,
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
    warrantyHorizon: "all",
    upcomingFilter: "all"
  },
  charts: {
    statusDoughnut: null,
    categoryBar: null,
    departmentBar: null
  },
  lastSeenToastId: null,
  autoLoginAttempted: false,
  isStreamlitConnected: false,
  theme: "light",
  sidebarCollapsed: false
};

// =========================================================================
// Streamlit Custom Component Protocol Bridge
// =========================================================================

function sendToStreamlit(action, payload = {}) {
  const message = {
    isStreamlitMessage: true,
    type: "streamlit:setComponentValue",
    value: {
      action: action,
      payload: payload,
      requestId: Date.now() + "_" + Math.random().toString(36).substring(2, 9),
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
    height: Math.max(height, 850)
  }, "*");
}

// Listen for incoming state updates from Streamlit Python backend
window.addEventListener("message", function(event) {
  if (!event.data) return;
  if (event.data.type === "streamlit:render") {
    state.isStreamlitConnected = true;
    const args = event.data.args || {};
    const serverState = args.state || args.args || args;
    applyServerState(serverState);
  }
});

window.addEventListener("load", function() {
  window.parent.postMessage({
    isStreamlitMessage: true,
    type: "streamlit:componentReady",
    apiVersion: 1
  }, "*");
  notifyFrameHeight();
});

document.addEventListener("DOMContentLoaded", function() {
  initTheme();
  initSidebar();
  initEventListeners();
  notifyFrameHeight();
  if (!state.authenticated && !state.user) {
    showLoginView();
  }
});

// =========================================================================
// State Synchronization & Rendering Engine
// =========================================================================

function applyServerState(serverState) {
  if (!serverState) return;

  state.authenticated = !!serverState.authenticated;
  state.user = serverState.user || null;

  if (serverState.devices) state.devices = serverState.devices;
  if (serverState.notifications) state.notifications = serverState.notifications;
  if (serverState.analytics) state.analytics = serverState.analytics;
  if (serverState.cloud_sync) state.cloudSync = serverState.cloud_sync;

  // Persist session token if authenticated
  if (state.authenticated && state.user && state.user.token) {
    try {
      localStorage.setItem("equipguard_session_token", state.user.token);
    } catch(e) {}
  }

  // Handle server-side errors
  if (serverState.error) {
    try {
      localStorage.removeItem("equipguard_session_token");
    } catch(e) {}
    showLoginAlert(serverState.error);
    const submitBtn = document.getElementById("btn-login-submit");
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerHTML = `<span>Sign In to Dashboard</span><svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"/></svg>`;
    }
  } else {
    hideLoginAlert();
  }

  // Handle toast notifications without duplication
  if (serverState.toast) {
    const tId = serverState.toast_id || serverState.toast;
    if (tId !== state.lastSeenToastId) {
      state.lastSeenToastId = tId;
      showToast(serverState.toast, "info");
    }
  }

  // Handle direct file download requested from backend
  if (serverState.download_payload && serverState.download_payload.data) {
    downloadBase64File(
      serverState.download_payload.data,
      serverState.download_payload.filename,
      serverState.download_payload.mime
    );
    sendToStreamlit("clear_download_payload");
  }

  // Auto-login check if not authenticated yet and saved session token exists
  if (!state.authenticated && !state.autoLoginAttempted) {
    state.autoLoginAttempted = true;
    try {
      const savedToken = localStorage.getItem("equipguard_session_token");
      if (savedToken) {
        const submitBtn = document.getElementById("btn-login-submit");
        if (submitBtn) {
          submitBtn.disabled = true;
          submitBtn.innerHTML = `<span>Restoring session...</span>`;
        }
        sendToStreamlit("login", { idToken: savedToken });
        return;
      }
    } catch(e) {}
  }

  // Render proper view based on authentication status
  if (state.authenticated && state.user) {
    showAppView();
    updateUserInfoUI();
    updateCloudSyncUI();
    try { renderDashboard(); } catch (e) { console.warn("renderDashboard:", e); }
    try { renderDevicesTable(); } catch (e) { console.warn("renderDevicesTable:", e); }
    try { renderWarrantiesTable(); } catch (e) { console.warn("renderWarrantiesTable:", e); }
    try { renderNotificationsList(); } catch (e) { console.warn("renderNotificationsList:", e); }
    try { renderReportsView(); } catch (e) { console.warn("renderReportsView:", e); }
  } else {
    showLoginView();
  }

  notifyFrameHeight();
}

// =========================================================================
// Theme Management (Light & Dark Mode)
// =========================================================================

function initTheme() {
  let savedTheme = null;
  try {
    savedTheme = localStorage.getItem("equipguard_theme");
  } catch(e) {}

  if (!savedTheme) {
    const prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    savedTheme = prefersDark ? "dark" : "light";
  }

  setTheme(savedTheme, false);
}

function setTheme(theme, rerenderCharts = true) {
  state.theme = theme;
  const isDark = theme === "dark";

  if (isDark) {
    document.documentElement.classList.add("dark-mode");
    document.body.classList.add("dark-mode");
  } else {
    document.documentElement.classList.remove("dark-mode");
    document.body.classList.remove("dark-mode");
  }

  try {
    localStorage.setItem("equipguard_theme", theme);
  } catch(e) {}

  // Update theme icons
  const iconSun = document.getElementById("theme-icon-sun");
  const iconMoon = document.getElementById("theme-icon-moon");
  if (iconSun && iconMoon) {
    if (isDark) {
      iconSun.style.display = "none";
      iconMoon.style.display = "block";
    } else {
      iconSun.style.display = "block";
      iconMoon.style.display = "none";
    }
  }

  // Re-render charts to adapt colors
  if (rerenderCharts && state.authenticated) {
    try { renderDashboardCharts(); } catch(e) {}
    try { renderDepartmentChart(); } catch(e) {}
  }
}

function toggleTheme() {
  const newTheme = state.theme === "dark" ? "light" : "dark";
  setTheme(newTheme, true);
  showToast(`Switched to ${newTheme} mode`, "info");
}

// =========================================================================
// Collapsible Sidebar Management
// =========================================================================

function initSidebar() {
  let saved = null;
  try {
    saved = localStorage.getItem("equipguard_sidebar_collapsed");
  } catch(e) {}

  if (saved === "true") {
    state.sidebarCollapsed = true;
    const sidebar = document.getElementById("main-sidebar");
    if (sidebar) sidebar.classList.add("collapsed");
  }
}

function toggleSidebar() {
  state.sidebarCollapsed = !state.sidebarCollapsed;
  const sidebar = document.getElementById("main-sidebar");
  if (sidebar) {
    sidebar.classList.toggle("collapsed", state.sidebarCollapsed);
  }
  try {
    localStorage.setItem("equipguard_sidebar_collapsed", state.sidebarCollapsed ? "true" : "false");
  } catch(e) {}
  notifyFrameHeight();
}

// =========================================================================
// Animated Count-Up for Metric Numbers
// =========================================================================

function animateCountUp(elementId, targetValue, duration = 600) {
  const el = document.getElementById(elementId);
  if (!el) return;

  const target = Number(targetValue) || 0;
  const start = 0;
  const startTime = performance.now();

  function updateCount(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    // Ease-out cubic
    const ease = 1 - Math.pow(1 - progress, 3);
    const current = Math.floor(start + (target - start) * ease);

    el.innerText = current.toLocaleString();

    if (progress < 1) {
      requestAnimationFrame(updateCount);
    } else {
      el.innerText = target.toLocaleString();
    }
  }

  requestAnimationFrame(updateCount);
}

// =========================================================================
// Event Listeners Setup
// =========================================================================

function initEventListeners() {
  // Theme Toggle Button
  const themeToggleBtn = document.getElementById("btn-theme-toggle");
  if (themeToggleBtn) {
    themeToggleBtn.addEventListener("click", toggleTheme);
  }

  // Sidebar Collapse Button
  const sidebarToggleBtn = document.getElementById("btn-toggle-sidebar");
  if (sidebarToggleBtn) {
    sidebarToggleBtn.addEventListener("click", toggleSidebar);
  }

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

  // Global Search Input with Ctrl+K shortcut
  const searchInput = document.getElementById("global-search-input");
  const searchDropdown = document.getElementById("search-results-dropdown");

  if (searchInput) {
    searchInput.addEventListener("input", (e) => {
      const query = e.target.value.trim();
      state.filters.search = query;
      handleGlobalSearchInput(query);
    });

    searchInput.addEventListener("focus", (e) => {
      if (e.target.value.trim()) {
        handleGlobalSearchInput(e.target.value.trim());
      }
    });
  }

  // Close search dropdown on click outside
  document.addEventListener("click", (e) => {
    if (searchDropdown && !searchDropdown.contains(e.target) && e.target !== searchInput) {
      searchDropdown.classList.remove("show");
    }
  });

  // Close modals when clicking directly on backdrop
  document.querySelectorAll(".modal-backdrop").forEach(backdrop => {
    backdrop.addEventListener("click", (e) => {
      if (e.target === backdrop) {
        closeDeviceModal();
        closeDeviceDetailsModal();
      }
    });
  });

  // Window resize handler to maintain accurate frame height
  window.addEventListener("resize", () => {
    notifyFrameHeight();
  });

  // Keyboard shortcut: Ctrl+K or / to focus search, Escape to close modals
  window.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      if (searchInput) {
        searchInput.focus();
        searchInput.select();
      }
    } else if (e.key === "/" && document.activeElement !== searchInput && !["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName)) {
      e.preventDefault();
      if (searchInput) {
        searchInput.focus();
        searchInput.select();
      }
    } else if (e.key === "Escape") {
      closeDeviceModal();
      closeDeviceDetailsModal();
      if (searchDropdown) searchDropdown.classList.remove("show");
      const notifDrawer = document.getElementById("notification-drawer");
      if (notifDrawer) notifDrawer.classList.remove("show");
    }
  });

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

  // Upcoming Warranty Expirations Filter Pills
  document.querySelectorAll(".upcoming-filter-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".upcoming-filter-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      state.filters.upcomingFilter = btn.getAttribute("data-filter");
      renderUpcomingList();
    });
  });

  // Header Add Device Button
  const headerAddBtn = document.getElementById("btn-header-add-device");
  if (headerAddBtn) headerAddBtn.addEventListener("click", openAddDeviceModal);

  // Header Export Button
  const headerExportBtn = document.getElementById("btn-header-export");
  if (headerExportBtn) {
    headerExportBtn.addEventListener("click", () => triggerExport("excel"));
  }

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
// Global Search Live Dropdown Logic
// =========================================================================

function handleGlobalSearchInput(query) {
  const searchDropdown = document.getElementById("search-results-dropdown");
  if (!searchDropdown) return;

  if (!query || query.length === 0) {
    searchDropdown.classList.remove("show");
    searchDropdown.innerHTML = "";
    return;
  }

  const q = query.toLowerCase();
  const matches = state.devices.filter(d => 
    (d.Device_Name || "").toLowerCase().includes(q) ||
    (d.Serial_Number || "").toLowerCase().includes(q) ||
    (d.Device_ID || "").toLowerCase().includes(q) ||
    (d.Brand || "").toLowerCase().includes(q) ||
    (d.Model_Number || "").toLowerCase().includes(q) ||
    (d.Assigned_User || "").toLowerCase().includes(q) ||
    (d.Department || "").toLowerCase().includes(q)
  ).slice(0, 6);

  if (matches.length === 0) {
    searchDropdown.innerHTML = `
      <div style="padding: 16px; text-align: center; color: var(--text-muted); font-size: 13px;">
        No hardware matching "<strong>${escapeHtml(query)}</strong>"
      </div>
    `;
    searchDropdown.classList.add("show");
    return;
  }

  searchDropdown.innerHTML = matches.map(d => {
    let statusClass = "status-active";
    if (d.status === "Expired") statusClass = "status-expired";
    else if (d.status === "Expiring Soon") statusClass = "status-expiring";

    return `
      <div class="search-result-item" onclick="selectSearchResult('${d.Device_ID}')">
        <div class="search-res-info">
          <div class="search-res-name">${escapeHtml(d.Device_Name)}</div>
          <div style="font-size: 11.5px; color: var(--text-muted);">
            S/N: <code>${escapeHtml(d.Serial_Number)}</code> • ${escapeHtml(d.Category)} • ${escapeHtml(d.Department || 'IT')}
          </div>
        </div>
        <div style="text-align: right;">
          <span class="status-pill ${statusClass}" style="font-size: 11px; padding: 2px 8px;">${d.status}</span>
        </div>
      </div>
    `;
  }).join("");

  searchDropdown.classList.add("show");
}

function selectSearchResult(deviceId) {
  const searchDropdown = document.getElementById("search-results-dropdown");
  if (searchDropdown) searchDropdown.classList.remove("show");
  openDeviceDetails(deviceId);
}

// =========================================================================
// Navigation & Views
// =========================================================================

function switchTab(tabName) {
  try {
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
  } catch (e) {
    console.error("switchTab error:", e);
  }
  notifyFrameHeight();
}

function showLoginView() {
  try {
    const loginView = document.getElementById("login-view");
    const appView = document.getElementById("app-view");
    if (loginView) loginView.style.setProperty("display", "flex", "important");
    if (appView) appView.style.setProperty("display", "none", "important");
    const pwdInput = document.getElementById("login-password");
    if (pwdInput) pwdInput.value = "";
    const submitBtn = document.getElementById("btn-login-submit");
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerHTML = `<span>Sign In to Dashboard</span><svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"/></svg>`;
    }
  } catch (e) {
    console.error("showLoginView error:", e);
  }
  notifyFrameHeight();
}

function showAppView() {
  try {
    const loginView = document.getElementById("login-view");
    const appView = document.getElementById("app-view");
    if (loginView) loginView.style.setProperty("display", "none", "important");
    if (appView) appView.style.setProperty("display", "block", "important");
    switchTab(state.activeTab || "dashboard");
  } catch (e) {
    console.error("showAppView error:", e);
  }
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
      <div style="display: flex; align-items: flex-start; gap: 10px; text-align: left;">
        <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24" style="flex-shrink: 0; color: #ef4444;"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
        <div style="flex: 1; font-size: 13px; line-height: 1.4; word-break: break-word;">${escapeHtml(msg)}</div>
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
    submitBtn.innerHTML = `<span>Signing in via Backend...</span>`;
  }
  hideLoginAlert();

  // Send authentication request directly to Streamlit Python Backend
  sendToStreamlit("login", { email: email, password: password });

  // Timeout guard to re-enable button if network takes time
  setTimeout(() => {
    if (submitBtn && submitBtn.disabled && !state.user) {
      submitBtn.disabled = false;
      submitBtn.innerHTML = `<span>Sign In to Dashboard</span><svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"/></svg>`;
    }
  }, 12000);
}

function handleLogout() {
  try {
    localStorage.removeItem("equipguard_session_token");
    localStorage.removeItem("equipguard_token");
    localStorage.removeItem("equipguard_user");
    localStorage.clear();
    sessionStorage.clear();
  } catch(e) {}
  state.authenticated = false;
  state.user = null;
  sendToStreamlit("logout", {});
  showLoginView();
  showToast("Signed out successfully.", "info");
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
  const isConfigured = state.cloudSync && state.cloudSync.configured;
  const emailVal = state.cloudSync ? state.cloudSync.email : null;

  if (isConfigured) {
    if (pill) {
      pill.classList.add("connected");
      pill.innerHTML = `<span class="pulse-beacon"></span><span>Drive Synced</span>`;
      pill.title = `Google Drive connected (${emailVal || ''})`;
    }
  } else {
    if (pill) {
      pill.classList.remove("connected");
      pill.innerHTML = `<span class="status-indicator-dot" style="background: #ef4444;"></span><span style="color: #ef4444;">Drive Disconnected</span>`;
      pill.title = "Google Drive Disconnected. Configure Streamlit Secrets.";
    }
  }
}

// =========================================================================
// Executive Dashboard Rendering & Visual Health Score
// =========================================================================

function renderDashboard() {
  const analytics = state.analytics || {};
  const total = analytics.total_devices !== undefined ? analytics.total_devices : state.devices.length;
  const active = analytics.active_warranties || 0;
  const activePct = analytics.active_percentage || (total > 0 ? ((active / total) * 100).toFixed(1) : 0);
  const expiring = analytics.expiring_soon || 0;
  const expired = analytics.expired_warranties || 0;
  const unreadNotifs = analytics.unread_notifications || 0;

  // Animated KPI numbers
  animateCountUp("metric-total-devices", total);
  animateCountUp("metric-active-warranties", active);
  animateCountUp("metric-expiring-soon", expiring);
  animateCountUp("metric-expired-warranties", expired);
  animateCountUp("metric-unread-notifs", unreadNotifs);

  const activePercentEl = document.getElementById("metric-active-percent");
  if (activePercentEl) {
    activePercentEl.innerText = `${activePct}% active coverage`;
  }

  // Sidebar badge for expiring warranties
  const sidebarBadge = document.getElementById("sidebar-expiring-badge");
  if (sidebarBadge) {
    const urgentCount = expiring + expired;
    if (urgentCount > 0) {
      sidebarBadge.innerText = urgentCount;
      sidebarBadge.style.display = "inline-block";
    } else {
      sidebarBadge.style.display = "none";
    }
  }

  // Update Fleet Health Score Circular Gauge
  updateFleetHealthScore(active, total);

  // Update Action Required Alert Banner
  updateActionAlertBanner(expired, expiring);

  renderUpcomingList();
  renderActivityTimeline();
  renderDashboardCharts();
}

function updateFleetHealthScore(activeCount, totalCount) {
  const scoreCircle = document.getElementById("health-score-circle");
  const scoreLabel = document.getElementById("health-score-label");
  const scoreStatus = document.getElementById("health-score-status");

  if (!scoreCircle || !scoreLabel || !scoreStatus) return;

  const score = totalCount > 0 ? Math.round((activeCount / totalCount) * 100) : 100;
  scoreLabel.innerText = `${score}%`;

  // Stroke-dashoffset for circular SVG meter
  const offset = 100 - score;
  scoreCircle.style.strokeDashoffset = offset;

  if (score >= 80) {
    scoreCircle.setAttribute("stroke", "#10B981");
    scoreStatus.innerText = "Good Condition";
    scoreStatus.style.color = "#10B981";
  } else if (score >= 50) {
    scoreCircle.setAttribute("stroke", "#F59E0B");
    scoreStatus.innerText = "Review Recommended";
    scoreStatus.style.color = "#F59E0B";
  } else {
    scoreCircle.setAttribute("stroke", "#EF4444");
    scoreStatus.innerText = "Critical Attention";
    scoreStatus.style.color = "#EF4444";
  }
}

function updateActionAlertBanner(expired, expiring) {
  const banner = document.getElementById("action-alert-banner");
  const text = document.getElementById("action-alert-text");
  if (!banner || !text) return;

  if (expired > 0 || expiring > 0) {
    const parts = [];
    if (expired > 0) parts.push(`<strong>${expired}</strong> ${expired === 1 ? 'warranty' : 'warranties'} expired`);
    if (expiring > 0) parts.push(`<strong>${expiring}</strong> expiring soon`);

    text.innerHTML = parts.join(" and ") + " — immediate renewal or maintenance recommended.";
    banner.style.display = "flex";
  } else {
    banner.style.display = "none";
  }
}

function dismissActionAlert() {
  const banner = document.getElementById("action-alert-banner");
  if (banner) banner.style.display = "none";
}

// =========================================================================
// Upcoming Expirations Cards (with Urgency Progress Bar)
// =========================================================================

function renderUpcomingList() {
  const container = document.getElementById("upcoming-expirations-list");
  if (!container) return;

  let urgent = [...(state.analytics.upcoming_expirations || [])];

  // Apply upcoming filter (all, soon, expired)
  const filter = state.filters.upcomingFilter || "all";
  if (filter === "soon") {
    urgent = urgent.filter(d => d.days_remaining !== null && d.days_remaining >= 0);
  } else if (filter === "expired") {
    urgent = urgent.filter(d => d.days_remaining !== null && d.days_remaining < 0);
  }

  urgent = urgent.slice(0, 6);

  if (urgent.length === 0) {
    container.innerHTML = `
      <div style="text-align: center; color: var(--text-muted); padding: 28px 16px; font-size: 13px;">
        <svg width="32" height="32" fill="none" stroke="currentColor" viewBox="0 0 24 24" style="margin: 0 auto 8px; color: #10B981; opacity: 0.8;"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
        <div>No matching warranty expirations in this horizon. Fleet is healthy!</div>
      </div>
    `;
    return;
  }

  container.innerHTML = urgent.map(dev => {
    const days = dev.days_remaining !== undefined ? dev.days_remaining : 0;
    const isExpired = days < 0;
    const isSoon = days >= 0 && days <= 30;

    // Determine status pill and progress bar color
    let statusClass = "status-active";
    let fillClass = "fill-green";
    let progressPct = 100;
    let labelRight = `${days} days left`;

    if (isExpired) {
      statusClass = "status-expired";
      fillClass = "fill-red";
      progressPct = 100;
      labelRight = `Expired ${Math.abs(days)}d ago`;
    } else if (isSoon) {
      statusClass = "status-expiring";
      fillClass = "fill-amber";
      progressPct = Math.max(10, Math.round(((30 - days) / 30) * 100));
      labelRight = `${days}d remaining`;
    } else {
      progressPct = Math.min(100, Math.max(15, Math.round((days / 365) * 100)));
    }

    // Category SVG fallback icon
    const categoryIcon = getCategorySvg(dev.Category);

    return `
      <div class="expiring-item">
        <div class="expiring-item-top">
          <div class="expiring-device-info">
            <div class="device-avatar-chip">
              ${categoryIcon}
            </div>
            <div class="device-title-wrap">
              <span class="device-title-name">${escapeHtml(dev.Device_Name)}</span>
              <span class="device-title-meta">
                S/N: <code>${escapeHtml(dev.Serial_Number)}</code> • <span class="badge-dept">${escapeHtml(dev.Department || 'IT')}</span>
              </span>
            </div>
          </div>
          <div style="display: flex; align-items: center; gap: 8px;">
            <span class="status-pill ${statusClass}">${dev.countdown_text || labelRight}</span>
            <div class="expiring-actions">
              <button type="button" class="btn-action-mini" title="Renew Warranty" onclick="openEditDeviceModal('${dev.Device_ID}')">Renew</button>
              <button type="button" class="btn-action-mini" title="View Full Specs" onclick="openDeviceDetails('${dev.Device_ID}')">Specs</button>
            </div>
          </div>
        </div>

        <div class="warranty-progress-wrap">
          <div class="warranty-progress-bar">
            <div class="warranty-progress-fill ${fillClass}" style="width: ${progressPct}%;"></div>
          </div>
          <div class="warranty-progress-labels">
            <span>Exp: <strong>${dev.Warranty_End_Date}</strong></span>
            <span>${labelRight}</span>
          </div>
        </div>
      </div>
    `;
  }).join("");
}

// Category SVG Helper
function getCategorySvg(category) {
  const cat = (category || "").toLowerCase();
  if (cat.includes("laptop") || cat.includes("notebook")) {
    return `<svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/></svg>`;
  } else if (cat.includes("desktop") || cat.includes("pc")) {
    return `<svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/></svg>`;
  } else if (cat.includes("monitor")) {
    return `<svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z"/></svg>`;
  } else if (cat.includes("printer")) {
    return `<svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4H7v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"/></svg>`;
  } else if (cat.includes("router") || cat.includes("switch")) {
    return `<svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0"/></svg>`;
  } else {
    return `<svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"/></svg>`;
  }
}

// =========================================================================
// Recent Activity Timeline (Vertical Connected Timeline)
// =========================================================================

function renderActivityTimeline() {
  const container = document.getElementById("activity-timeline");
  if (!container) return;

  const logs = (state.analytics.activity_logs || []).slice(0, 6);
  if (logs.length === 0) {
    container.innerHTML = `
      <div style="text-align: center; color: var(--text-muted); padding: 24px 16px; font-size: 13px;">
        No recent activity records found.
      </div>
    `;
    return;
  }

  container.innerHTML = logs.map(log => {
    const rawAction = (log.Action || "").toUpperCase();
    let dotClass = "dot-auth";

    if (rawAction.includes("CREATE") || rawAction.includes("ADD")) {
      dotClass = "dot-create";
    } else if (rawAction.includes("UPDATE") || rawAction.includes("RENEW")) {
      dotClass = "dot-update";
    } else if (rawAction.includes("DELETE") || rawAction.includes("ALERT") || rawAction.includes("EXPIRE")) {
      dotClass = "dot-alert";
    }

    const relTime = formatRelativeTime(log.Timestamp);

    return `
      <div class="activity-item">
        <div class="activity-dot ${dotClass}"></div>
        <div class="activity-header-line">
          <span class="activity-action-name">${escapeHtml(log.Action)} <span style="font-weight: 400; color: var(--text-muted);">(${escapeHtml(log.Device_ID || 'System')})</span></span>
          <span class="activity-time-rel" title="${escapeHtml(log.Timestamp || '')}">${relTime}</span>
        </div>
        <div class="activity-details-text">${escapeHtml(log.Details || '')}</div>
        <div style="font-size: 11px; color: var(--text-muted); margin-top: 3px;">
          By <strong>${escapeHtml(log.User_Email || 'System')}</strong>
        </div>
      </div>
    `;
  }).join("");
}

// Relative Time Formatting Helper
function formatRelativeTime(timestamp) {
  if (!timestamp) return "Just now";
  try {
    const now = new Date();
    const date = new Date(timestamp);
    const diffMs = now - date;
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHour = Math.floor(diffMin / 60);
    const diffDay = Math.floor(diffHour / 24);

    if (diffSec < 45) return "Just now";
    if (diffMin < 60) return `${diffMin} min${diffMin > 1 ? 's' : ''} ago`;
    if (diffHour < 24) return `${diffHour} hr${diffHour > 1 ? 's' : ''} ago`;
    if (diffDay === 1) return "Yesterday";
    if (diffDay < 7) return `${diffDay} days ago`;
    return date.toLocaleDateString();
  } catch(e) {
    return timestamp;
  }
}

// =========================================================================
// Chart.js Visualizations (Donut Center Text & Category Gradients)
// =========================================================================

// Custom Chart.js Plugin to draw bold total in Donut center
const centerTextPlugin = {
  id: "centerTextPlugin",
  beforeDraw: function(chart) {
    if (chart.config.type !== "doughnut") return;
    const { width, height, ctx } = chart;
    ctx.restore();

    const isDark = document.documentElement.classList.contains("dark-mode");
    const numColor = isDark ? "#F1F5F9" : "#0F172A";
    const labelColor = isDark ? "#94A3B8" : "#64748B";

    const total = state.analytics.total_devices !== undefined ? state.analytics.total_devices : state.devices.length;

    // Draw total number
    const fontSizeNum = Math.min(Math.round(height / 6.5), 32);
    ctx.font = `800 ${fontSizeNum}px Inter, sans-serif`;
    ctx.textBaseline = "middle";
    ctx.textAlign = "center";
    ctx.fillStyle = numColor;
    const textX = width / 2;
    const textY = height / 2 - 8;
    ctx.fillText(total.toString(), textX, textY);

    // Draw label "TOTAL"
    const fontSizeLabel = Math.min(Math.round(height / 19), 11);
    ctx.font = `600 ${fontSizeLabel}px Inter, sans-serif`;
    ctx.fillStyle = labelColor;
    ctx.fillText("DEVICES", textX, textY + fontSizeNum * 0.7);

    ctx.save();
  }
};

function renderDashboardCharts() {
  if (typeof Chart === "undefined") return;

  const isDark = document.documentElement.classList.contains("dark-mode");
  const textColor = isDark ? "#94A3B8" : "#64748B";
  const gridColor = isDark ? "rgba(255, 255, 255, 0.05)" : "#F1F5F9";

  // Chart 1: Warranty Status Donut Chart with Center Total
  try {
    const ctxStatus = document.getElementById("chart-warranty-status");
    if (ctxStatus) {
      const existing1 = Chart.getChart(ctxStatus);
      if (existing1) existing1.destroy();
      if (state.charts.statusDoughnut) {
        try { state.charts.statusDoughnut.destroy(); } catch(e){}
      }

      const dist = state.analytics.status_distribution || { "Active": 0, "Expiring Soon": 0, "Expired": 0 };
      const activeCount = dist["Active"] || 0;
      const expiringCount = dist["Expiring Soon"] || 0;
      const expiredCount = dist["Expired"] || 0;

      state.charts.statusDoughnut = new Chart(ctxStatus, {
        type: "doughnut",
        data: {
          labels: ["Active", "Expiring Soon", "Expired"],
          datasets: [{
            data: [activeCount, expiringCount, expiredCount],
            backgroundColor: ["#10B981", "#F59E0B", "#EF4444"],
            borderWidth: 2,
            borderColor: isDark ? "#111B3A" : "#FFFFFF",
            borderRadius: 6,
            spacing: 2
          }]
        },
        plugins: [centerTextPlugin],
        options: {
          responsive: true,
          maintainAspectRatio: false,
          cutout: "74%",
          plugins: {
            legend: {
              position: "bottom",
              labels: {
                boxWidth: 10,
                boxHeight: 10,
                usePointStyle: true,
                pointStyle: "circle",
                color: textColor,
                font: { family: "Inter", size: 12, weight: "500" },
                padding: 16
              }
            },
            tooltip: {
              callbacks: {
                label: function(context) {
                  const val = context.raw || 0;
                  const total = (context.dataset.data || []).reduce((a, b) => a + b, 0);
                  const pct = total > 0 ? Math.round((val / total) * 100) : 0;
                  return ` ${context.label}: ${val} (${pct}%)`;
                }
              }
            }
          }
        }
      });
    }
  } catch (e) {
    console.warn("chart-warranty-status error:", e);
  }

  // Chart 2: Devices by Category Bar Chart
  try {
    const ctxCategory = document.getElementById("chart-devices-category");
    if (ctxCategory) {
      const existing2 = Chart.getChart(ctxCategory);
      if (existing2) existing2.destroy();
      if (state.charts.categoryBar) {
        try { state.charts.categoryBar.destroy(); } catch(e){}
      }

      const catDist = state.analytics.category_distribution || {};
      const labels = Object.keys(catDist);
      const dataVals = Object.values(catDist);

      state.charts.categoryBar = new Chart(ctxCategory, {
        type: "bar",
        data: {
          labels: labels,
          datasets: [{
            label: "Registered Equipment",
            data: dataVals,
            backgroundColor: "#2563EB",
            borderRadius: { topLeft: 6, topRight: 6 },
            borderSkipped: false
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                label: function(ctx) {
                  return ` Devices: ${ctx.raw}`;
                }
              }
            }
          },
          scales: {
            y: {
              beginAtZero: true,
              ticks: { stepSize: 1, color: textColor, font: { family: "Inter", size: 11 } },
              grid: { color: gridColor }
            },
            x: {
              ticks: { color: textColor, font: { family: "Inter", size: 11 } },
              grid: { display: false }
            }
          }
        }
      });
    }
  } catch (e) {
    console.warn("chart-devices-category error:", e);
  }
}

// =========================================================================
// Device Inventory Table Rendering & Search
// =========================================================================

function renderDevicesTable() {
  const tbody = document.getElementById("devices-table-body");
  if (!tbody) return;

  const filtered = filterDevices(state.devices);
  const countLabel = document.getElementById("devices-count-label");
  if (countLabel) countLabel.innerText = filtered.length;

  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; padding: 48px 16px; color: var(--text-muted);">No devices match your filter criteria.</td></tr>`;
    return;
  }

  tbody.innerHTML = filtered.map(d => {
    let statusClass = "status-active";
    if (d.status === "Expired") statusClass = "status-expired";
    else if (d.status === "Expiring Soon") statusClass = "status-expiring";

    return `
      <tr>
        <td>
          <div style="display: flex; align-items: center; gap: 12px;">
            <div class="device-avatar-chip" style="width: 36px; height: 36px;">
              ${getCategorySvg(d.Category)}
            </div>
            <div>
              <div style="font-weight: 600; color: var(--text-primary); font-size: 13.5px;">${escapeHtml(d.Device_Name)}</div>
              <div style="font-size: 11.5px; color: var(--text-muted);">${escapeHtml(d.Brand || '')} ${escapeHtml(d.Model_Number || '')} • <strong>${escapeHtml(d.Device_ID)}</strong></div>
            </div>
          </div>
        </td>
        <td><span class="badge badge-secondary">${escapeHtml(d.Category)}</span></td>
        <td><code style="background: var(--bg-card-subtle); padding: 2px 7px; border-radius: 4px; font-size: 12px; border: 1px solid var(--border-subtle);">${escapeHtml(d.Serial_Number)}</code></td>
        <td>${escapeHtml(d.Assigned_User || 'Unassigned')}</td>
        <td>${escapeHtml(d.Department || 'IT')}</td>
        <td>
          <div style="font-weight: 500;">${d.Warranty_End_Date}</div>
          <div style="font-size: 11px; color: var(--text-muted);">${d.countdown_text || ''}</div>
        </td>
        <td><span class="status-pill ${statusClass}">${d.status || 'Active'}</span></td>
        <td style="text-align: right;">
          <div class="action-btns" style="justify-content: flex-end;">
            <button type="button" class="action-btn" title="Inspect Full Specifications" onclick="openDeviceDetails('${d.Device_ID}')">View</button>
            <button type="button" class="action-btn" title="Edit Device Record" onclick="openEditDeviceModal('${d.Device_ID}')">Edit</button>
            <button type="button" class="action-btn action-btn-danger" title="Delete Device" onclick="deleteDevice('${d.Device_ID}')">Delete</button>
          </div>
        </td>
      </tr>
    `;
  }).join("");
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
        (d.Assigned_User || "").toLowerCase().includes(q) ||
        (d.Department || "").toLowerCase().includes(q)
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
    tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 48px 16px; color: var(--text-muted);">No warranty records in this horizon.</td></tr>`;
    return;
  }

  tbody.innerHTML = list.map(d => {
    let statusClass = "status-active";
    if (d.status === "Expired") statusClass = "status-expired";
    else if (d.status === "Expiring Soon") statusClass = "status-expiring";

    return `
      <tr>
        <td>
          <div style="font-weight: 600; font-size: 13.5px; color: var(--text-primary);">${escapeHtml(d.Device_Name)}</div>
          <div style="font-size: 11.5px; color: var(--text-muted);">${escapeHtml(d.Category)} • ${escapeHtml(d.Device_ID)}</div>
        </td>
        <td><code style="background: var(--bg-card-subtle); padding: 2px 7px; border-radius: 4px; font-size: 12px; border: 1px solid var(--border-subtle);">${escapeHtml(d.Serial_Number)}</code></td>
        <td>${escapeHtml(d.Assigned_User || 'Unassigned')} (${escapeHtml(d.Department || 'IT')})</td>
        <td>${d.Warranty_Start_Date || 'N/A'} → <strong>${d.Warranty_End_Date}</strong></td>
        <td>
          <span class="status-pill ${statusClass}">${d.countdown_text}</span>
        </td>
        <td><span class="status-pill ${statusClass}">${d.status}</span></td>
        <td style="text-align: right;">
          <button type="button" class="btn-secondary" style="padding: 4px 12px; font-size: 12px;" onclick="openEditDeviceModal('${d.Device_ID}')">Renew / Update</button>
        </td>
      </tr>
    `;
  }).join("");
}

// =========================================================================
// Device Modal Handlers (Add / Edit / Delete / Inspect - All 17 Fields)
// =========================================================================

function recalculateDuration() {
  const startVal = document.getElementById("form-warranty-start").value;
  const endVal = document.getElementById("form-warranty-end").value;
  const durationField = document.getElementById("form-duration");

  if (!startVal || !endVal || !durationField) return;
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

  const modalBody = document.querySelector("#device-modal .modal-body");
  if (modalBody) modalBody.scrollTop = 0;

  document.getElementById("device-modal").classList.add("show");
  notifyFrameHeight();
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

  const modalBody = document.querySelector("#device-modal .modal-body");
  if (modalBody) modalBody.scrollTop = 0;

  document.getElementById("device-modal").classList.add("show");
  notifyFrameHeight();
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

  let statusClass = "status-active";
  if (d.status === "Expired") statusClass = "status-expired";
  else if (d.status === "Expiring Soon") statusClass = "status-expiring";

  container.innerHTML = `
    <div style="display: flex; gap: 20px; margin-bottom: 20px; align-items: center;">
      <div class="device-avatar-chip" style="width: 72px; height: 72px; border-radius: 14px;">
        ${getCategorySvg(d.Category)}
      </div>
      <div style="flex: 1;">
        <div style="display: flex; align-items: center; gap: 8px;">
          <span class="status-pill ${statusClass}">${d.status}</span>
          <span class="badge badge-secondary">${d.Category}</span>
        </div>
        <h2 style="font-size: 20px; font-weight: 700; color: var(--text-primary); margin: 6px 0;">${escapeHtml(d.Device_Name)}</h2>
        <div style="font-size: 13px; color: var(--text-muted);">${escapeHtml(d.Brand || '')} ${escapeHtml(d.Model_Number || '')}</div>
        <div style="margin-top: 6px; font-size: 13px; font-weight: 600; color: var(--primary);">
          ${d.countdown_text}
        </div>
      </div>
    </div>

    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; font-size: 13px; background: var(--bg-card-subtle); padding: 18px; border-radius: 12px; border: 1px solid var(--border-subtle); margin-bottom: 16px;">
      <div><strong>Device ID:</strong> ${escapeHtml(d.Device_ID)}</div>
      <div><strong>Hardware S/N:</strong> <code>${escapeHtml(d.Serial_Number)}</code></div>
      <div><strong>Assigned User:</strong> ${escapeHtml(d.Assigned_User || 'Unassigned')}</div>
      <div><strong>Department:</strong> ${escapeHtml(d.Department || 'IT')}</div>
      <div><strong>Warranty Period:</strong> ${d.Warranty_Start_Date} → ${d.Warranty_End_Date}</div>
      <div><strong>Duration:</strong> ${d.Warranty_Duration_Months || '12'} Months</div>
      <div><strong>Purchase Price:</strong> $${d.Purchase_Price ? Number(d.Purchase_Price).toFixed(2) : '0.00'}</div>
      <div><strong>Supplier:</strong> ${escapeHtml(d.Supplier || 'N/A')}</div>
      <div><strong>Invoice #:</strong> ${escapeHtml(d.Invoice_Number || 'N/A')}</div>
      <div><strong>Last Audit:</strong> ${d.Updated_At ? d.Updated_At.substring(0, 10) : 'N/A'}</div>
    </div>

    ${d.Notes ? `<div style="font-size: 13px; color: var(--text-secondary); padding: 8px 0;"><strong>Remarks:</strong> ${escapeHtml(d.Notes)}</div>` : ''}
  `;

  const modalBody = document.querySelector("#device-details-modal .modal-body");
  if (modalBody) modalBody.scrollTop = 0;

  document.getElementById("device-details-modal").classList.add("show");
  notifyFrameHeight();
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
      <div class="notif-icon-box" style="background: ${n.Urgency === 'critical' ? 'rgba(239, 68, 68, 0.15)' : 'rgba(245, 158, 11, 0.15)'}; color: ${n.Urgency === 'critical' ? '#ef4444' : '#f59e0b'};">
        <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
      </div>
      <div style="flex: 1;">
        <div class="notif-text">${escapeHtml(n.Message)}</div>
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
// Reports & Department Analytics View
// =========================================================================

function renderReportsView() {
  const analytics = state.analytics || {};
  animateCountUp("report-metric-this-month", analytics.expiring_this_month || 0);
  animateCountUp("report-metric-30d", analytics.expiring_30_days || 0);
  animateCountUp("report-metric-60d", analytics.expiring_60_days || 0);
  animateCountUp("report-metric-90d", analytics.expiring_90_days || 0);

  const assetVal = analytics.total_asset_value || 0;
  const assetValEl = document.getElementById("report-total-asset-val");
  if (assetValEl) {
    assetValEl.innerText = `$${Number(assetVal).toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
  }

  renderDepartmentChart();
}

function renderDepartmentChart() {
  const ctxDept = document.getElementById("chart-department-status");
  if (!ctxDept || typeof Chart === "undefined") return;

  const isDark = document.documentElement.classList.contains("dark-mode");
  const textColor = isDark ? "#94A3B8" : "#64748B";
  const gridColor = isDark ? "rgba(255, 255, 255, 0.05)" : "#F1F5F9";

  try {
    const existing = Chart.getChart(ctxDept);
    if (existing) existing.destroy();
    if (state.charts.departmentBar) {
      try { state.charts.departmentBar.destroy(); } catch(e){}
    }

    const matrix = state.analytics.department_status_matrix || {};
    const labels = Object.keys(matrix);
    const activeData = labels.map(l => (matrix[l] && matrix[l].Active) || 0);
    const expiringData = labels.map(l => (matrix[l] && matrix[l]["Expiring Soon"]) || 0);
    const expiredData = labels.map(l => (matrix[l] && matrix[l].Expired) || 0);

    state.charts.departmentBar = new Chart(ctxDept, {
      type: "bar",
      data: {
        labels: labels,
        datasets: [
          { label: "Active", data: activeData, backgroundColor: "#10B981" },
          { label: "Expiring Soon", data: expiringData, backgroundColor: "#F59E0B" },
          { label: "Expired", data: expiredData, backgroundColor: "#EF4444" }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { stacked: true, grid: { display: false }, ticks: { color: textColor, font: { family: "Inter", size: 11 } } },
          y: { stacked: true, grid: { color: gridColor }, ticks: { color: textColor, font: { family: "Inter", size: 11 } } }
        },
        plugins: {
          legend: {
            position: "top",
            labels: {
              boxWidth: 10,
              boxHeight: 10,
              usePointStyle: true,
              pointStyle: "circle",
              color: textColor,
              font: { family: "Inter", size: 11 }
            }
          }
        }
      }
    });
  } catch (e) {
    console.warn("renderDepartmentChart error:", e);
  }
}

// =========================================================================
// Export Handlers
// =========================================================================

function triggerExport(format) {
  sendToStreamlit(`export_${format}`, {
    filters: state.filters
  });
  showToast(`Generating ${format.toUpperCase()} compliance export...`, "info");
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

  let iconSvg = `<svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`;
  if (type === "success") {
    iconSvg = `<svg width="16" height="16" fill="none" stroke="#10B981" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>`;
  } else if (type === "warning") {
    iconSvg = `<svg width="16" height="16" fill="none" stroke="#F59E0B" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>`;
  } else if (type === "danger" || type === "error") {
    iconSvg = `<svg width="16" height="16" fill="none" stroke="#EF4444" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>`;
  }

  toast.innerHTML = `
    <span>${iconSvg}</span>
    <span>${escapeHtml(message)}</span>
  `;

  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(12px)";
    setTimeout(() => toast.remove(), 250);
  }, 3500);
}

// Utility: HTML Sanitizer
function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
