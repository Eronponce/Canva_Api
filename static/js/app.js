const STORAGE_KEY = "canvas-bulk-panel-ui-v4";

const state = {
  config: null,
  groups: [],
  registeredCourses: [],
  history: [],
  connectionSnapshot: null,
  envLoaded: false,
  envContent: "",
  activeGroupId: null,
  selectedReportId: null,
  pickerSearch: {},
  announcement: {
    mode: "groups",
    groupIds: [],
    courseRefs: [],
    selectAllGroups: false,
  },
  message: {
    mode: "groups",
    groupIds: [],
    courseRefs: [],
    selectAllGroups: false,
  },
  pollers: new Map(),
};

document.addEventListener("DOMContentLoaded", () => {
  bindTabs();
  bindEvents();
  restoreUiState();
  toggleScheduleField();
  updateAnnouncementPreview();
  loadInitialData();
});

function $(selector) {
  return document.querySelector(selector);
}

function bindTabs() {
  document.querySelectorAll(".tab-button").forEach((button) => {
    button.addEventListener("click", () => openTab(button.dataset.tab));
  });
}

function bindEvents() {
  $("#baseUrl").addEventListener("input", () => {
    state.connectionSnapshot = null;
    renderConnectionResult(null);
    persistUiState();
  });
  $("#baseUrl").addEventListener("blur", () => {
    $("#baseUrl").value = normalizeBaseUrlInput($("#baseUrl").value);
    persistUiState();
  });
  $("#tokenType").addEventListener("change", persistUiState);
  $("#testConnectionBtn").addEventListener("click", testConnection);

  $("#registeredCourseInput").addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      addRegisteredCourse();
    }
  });
  $("#addRegisteredCourseBtn").addEventListener("click", addRegisteredCourse);
  $("#registeredCourseList").addEventListener("click", handleRegisteredCourseClick);

  $("#newGroupBtn").addEventListener("click", () => openGroupModal());
  $("#groupList").addEventListener("click", handleGroupClick);
  $("#saveGroupBtn").addEventListener("click", saveGroup);
  $("#closeGroupModalBtn").addEventListener("click", closeGroupModal);
  $("#cancelGroupModalBtn").addEventListener("click", closeGroupModal);
  $("#groupModal").addEventListener("click", (event) => {
    if (event.target.dataset.action === "close-group-modal") {
      closeGroupModal();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !$("#groupModal").classList.contains("hidden")) {
      closeGroupModal();
    }
  });

  $("#announcementAllGroups").addEventListener("change", () => {
    state.announcement.selectAllGroups = $("#announcementAllGroups").checked;
    renderTargetControls("announcement");
    persistUiState();
  });
  $("#messageAllGroups").addEventListener("change", () => {
    state.message.selectAllGroups = $("#messageAllGroups").checked;
    renderTargetControls("message");
    persistUiState();
  });

  document.addEventListener("click", handleDelegatedClick);
  document.addEventListener("input", handleDelegatedInput);
  document.addEventListener("change", handleDelegatedChange);

  $("#publishMode").addEventListener("change", () => {
    toggleScheduleField();
    persistUiState();
  });
  $("#announcementTitle").addEventListener("input", persistUiState);
  $("#announcementMessage").addEventListener("input", () => {
    updateAnnouncementPreview();
    persistUiState();
  });
  $("#announcementScheduleAt").addEventListener("input", persistUiState);
  $("#lockComment").addEventListener("change", persistUiState);
  $("#announcementDryRun").addEventListener("change", persistUiState);
  $("#announcementForm").addEventListener("submit", submitAnnouncementJob);

  $("#messageSubject").addEventListener("input", persistUiState);
  $("#messageBody").addEventListener("input", persistUiState);
  $("#messageStrategy").addEventListener("change", persistUiState);
  $("#messageDedupe").addEventListener("change", persistUiState);
  $("#messageDryRun").addEventListener("change", persistUiState);
  $("#messageForm").addEventListener("submit", submitMessageJob);

  $("#refreshHistoryBtn").addEventListener("click", refreshReports);
  $("#saveEnvBtn").addEventListener("click", saveEnvFile);
}

function handleDelegatedClick(event) {
  const modeButton = event.target.closest("[data-kind][data-mode]");
  if (modeButton) {
    const kind = modeButton.dataset.kind;
    state[kind].mode = modeButton.dataset.mode;
    renderModeSwitch(kind);
    renderTargetControls(kind);
    persistUiState();
    return;
  }

  const removeChip = event.target.closest("[data-picker-remove]");
  if (removeChip) {
    togglePickerValue(removeChip.dataset.pickerRemove, removeChip.dataset.value, false);
    return;
  }

  const openReport = event.target.closest("[data-action='open-report']");
  if (openReport) {
    state.selectedReportId = openReport.dataset.jobId;
    renderReportDetail();
  }
}

function handleDelegatedInput(event) {
  const search = event.target.closest("[data-picker-search]");
  if (!search) return;
  state.pickerSearch[search.dataset.pickerSearch] = search.value.trim().toLowerCase();
  renderPickers();
}

function handleDelegatedChange(event) {
  const checkbox = event.target.closest("[data-picker-checkbox]");
  if (!checkbox) return;
  togglePickerValue(checkbox.dataset.pickerCheckbox, checkbox.value, checkbox.checked);
}

function restoreUiState() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
    $("#baseUrl").value = saved.baseUrl || "";
    $("#tokenType").value = saved.tokenType || "personal";
    $("#announcementTitle").value = saved.announcementTitle || "";
    $("#announcementMessage").value = saved.announcementMessage || "";
    $("#publishMode").value = saved.publishMode || "publish_now";
    $("#announcementScheduleAt").value = saved.announcementScheduleAt || "";
    $("#lockComment").checked = Boolean(saved.lockComment);
    $("#announcementDryRun").checked = Boolean(saved.announcementDryRun);
    $("#messageSubject").value = saved.messageSubject || "";
    $("#messageBody").value = saved.messageBody || "";
    $("#messageStrategy").value = saved.messageStrategy || "users";
    $("#messageDedupe").checked = saved.messageDedupe !== false;
    $("#messageDryRun").checked = Boolean(saved.messageDryRun);
    state.announcement = { ...state.announcement, ...(saved.announcement || {}) };
    state.message = { ...state.message, ...(saved.message || {}) };
    if (!["groups", "courses"].includes(state.message.mode)) {
      state.message.mode = "groups";
    }
    if (saved.activeTab) {
      openTab(saved.activeTab);
    }
  } catch (error) {
    console.warn("Falha ao restaurar estado local.", error);
  }
}

function persistUiState() {
  const activeTab = document.querySelector(".tab-button.active")?.dataset.tab || "connection";
  localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({
      activeTab,
      baseUrl: $("#baseUrl").value.trim(),
      tokenType: $("#tokenType").value,
      announcementTitle: $("#announcementTitle").value,
      announcementMessage: $("#announcementMessage").value,
      publishMode: $("#publishMode").value,
      announcementScheduleAt: $("#announcementScheduleAt").value,
      lockComment: $("#lockComment").checked,
      announcementDryRun: $("#announcementDryRun").checked,
      messageSubject: $("#messageSubject").value,
      messageBody: $("#messageBody").value,
      messageStrategy: $("#messageStrategy").value,
      messageDedupe: $("#messageDedupe").checked,
      messageDryRun: $("#messageDryRun").checked,
      announcement: state.announcement,
      message: {
        mode: state.message.mode,
        groupIds: state.message.groupIds,
        courseRefs: state.message.courseRefs,
        selectAllGroups: state.message.selectAllGroups,
      },
    }),
  );
}

function openTab(tabName) {
  document.querySelectorAll(".tab-button").forEach((button) => {
    button.classList.toggle("active", button.dataset.tab === tabName);
  });
  document.querySelectorAll(".tab-panel").forEach((panel) => {
    panel.classList.toggle("active", panel.id === `tab-${tabName}`);
  });
  if (tabName === "settings") {
    loadEnvFile(true);
  }
  persistUiState();
}

function normalizeBaseUrlInput(value) {
  const trimmed = String(value || "").trim().replace(/\/+$/, "");
  if (!trimmed) return "";
  return /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`;
}

function clearFieldValidation() {
  document.querySelectorAll(".input-error").forEach((element) => {
    element.classList.remove("input-error");
  });
}

function markInvalid(selector) {
  const element = typeof selector === "string" ? $(selector) : selector;
  if (element) {
    element.classList.add("input-error");
  }
}

function focusField(selector) {
  const element = typeof selector === "string" ? $(selector) : selector;
  if (!element) return;
  element.focus();
  element.scrollIntoView({ behavior: "smooth", block: "center" });
}

function ensureConnectionConfigured() {
  clearFieldValidation();
  const baseUrl = normalizeBaseUrlInput($("#baseUrl").value);
  const accessToken = $("#apiToken").value.trim();
  const envTokenAvailable = Boolean(state.config?.env_token_available);

  if (!baseUrl) {
    openTab("connection");
    markInvalid("#baseUrl");
    focusField("#baseUrl");
    showNotice("Informe a URL base do Canvas antes de continuar.", "error");
    return false;
  }

  if (!accessToken && !envTokenAvailable) {
    openTab("connection");
    markInvalid("#apiToken");
    focusField("#apiToken");
    showNotice("Informe um token de acesso no painel ou no .env.", "error");
    return false;
  }

  $("#baseUrl").value = baseUrl;
  return true;
}

function ensureTargetSelection(kind) {
  const payload = getTargetPayload(kind);
  if (payload.course_refs?.length) return true;
  if (payload.select_all_groups) return state.groups.length > 0;
  if (payload.group_ids?.length) return true;
  openTab(kind === "announcement" ? "announcements" : "messages");
  showNotice("Selecione grupos ou cursos antes de enviar.", "error");
  return false;
}

function getConnectionPayload() {
  return {
    base_url: normalizeBaseUrlInput($("#baseUrl").value),
    access_token: $("#apiToken").value.trim(),
    token_type: $("#tokenType").value,
  };
}

function getTargetPayload(kind) {
  const target = state[kind];
  if (target.mode === "courses") {
    return { course_refs: [...target.courseRefs] };
  }
  return {
    group_ids: target.selectAllGroups ? [] : [...target.groupIds],
    select_all_groups: target.selectAllGroups,
  };
}

async function apiFetch(url, options = {}) {
  const requestOptions = {
    method: options.method || "GET",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  };
  if (options.body !== undefined) {
    requestOptions.body = JSON.stringify(options.body);
  }
  const response = await fetch(url, requestOptions);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || `Falha na requisicao (${response.status})`);
  }
  return data;
}

function showNotice(message, type = "info") {
  const notice = $("#globalNotice");
  notice.textContent = message;
  notice.className = `notice notice-${type}`;
}

function hideNotice() {
  $("#globalNotice").className = "notice hidden";
}

function showModalNotice(message, type = "info") {
  const notice = $("#groupModalNotice");
  notice.textContent = message;
  notice.className = `notice notice-${type}`;
}

function hideModalNotice() {
  $("#groupModalNotice").className = "notice hidden";
}

function setBusy(button, isBusy, busyText = "Processando...") {
  if (!button) return;
  if (!button.dataset.originalText) {
    button.dataset.originalText = button.textContent;
  }
  button.disabled = isBusy;
  button.textContent = isBusy ? busyText : button.dataset.originalText;
}

async function loadInitialData() {
  hideNotice();
  await loadConfig();
  await loadHistory();
  renderConnectionResult(null);
  renderAll();
}

async function loadConfig() {
  const data = await apiFetch("/api/config");
  state.config = data.settings || {};
  state.groups = Array.isArray(data.groups) ? data.groups : [];
  state.registeredCourses = Array.isArray(data.registered_courses) ? data.registered_courses : [];
  if (!$("#baseUrl").value.trim() && state.config.default_base_url) {
    $("#baseUrl").value = state.config.default_base_url;
  }
  pruneSelections();
}

async function loadHistory() {
  const data = await apiFetch("/api/history");
  state.history = Array.isArray(data.items) ? data.items : [];
  if (!state.selectedReportId && state.history[0]) {
    state.selectedReportId = state.history[0].id;
  }
}

async function refreshReports() {
  hideNotice();
  try {
    await loadConfig();
    await loadHistory();
    renderAll();
    showNotice("Relatorios atualizados.", "success");
  } catch (error) {
    showNotice(error.message, "error");
  }
}

function pruneSelections() {
  const validGroupIds = new Set(state.groups.map((group) => group.id));
  state.announcement.groupIds = state.announcement.groupIds.filter((id) => validGroupIds.has(id));
  state.message.groupIds = state.message.groupIds.filter((id) => validGroupIds.has(id));
  const validCourseRefs = new Set(state.registeredCourses.map((item) => item.course_ref));
  state.announcement.courseRefs = state.announcement.courseRefs.filter((ref) => validCourseRefs.has(ref));
  state.message.courseRefs = state.message.courseRefs.filter((ref) => validCourseRefs.has(ref));
}

function renderAll() {
  renderHeaderMetrics();
  renderRegisteredCourses();
  renderGroups();
  renderModeSwitch("announcement");
  renderModeSwitch("message");
  renderTargetControls("announcement");
  renderTargetControls("message");
  renderReports();
  renderSettingsInfo(state.config || {});
  renderConnectionResult(state.connectionSnapshot);
  persistUiState();
}

function renderHeaderMetrics() {
  const registeredMetric = $("#registeredCourseMetric");
  const groupMetric = $("#groupMetric");
  const historyMetric = $("#historyMetric");
  if (registeredMetric) registeredMetric.textContent = String(state.registeredCourses.length);
  if (groupMetric) groupMetric.textContent = String(state.groups.length);
  if (historyMetric) historyMetric.textContent = String(state.history.length);
}

function renderConnectionResult(data) {
  const envTokenAvailable = Boolean(state.config?.env_token_available);
  const badge = $("#connectionStatusBadge");
  if (!data) {
    badge.className = `status-chip ${envTokenAvailable ? "status-info" : "status-warning"}`;
    badge.textContent = envTokenAvailable ? "pronto para testar" : "faltando token";
    $("#connectionResult").innerHTML = `
      <div class="summary-grid">
        <div class="summary-card"><span>Base URL ativa</span><strong class="mono">${escapeHtml(normalizeBaseUrlInput($("#baseUrl").value) || state.config?.default_base_url || "-")}</strong></div>
        <div class="summary-card"><span>Token no .env</span><strong>${envTokenAvailable ? "Disponivel" : "Nao configurado"}</strong></div>
        <div class="summary-card"><span>Origem padrao</span><strong>${escapeHtml(formatEnvTokenSource(state.config?.env_token_source))}</strong></div>
      </div>
    `;
    return;
  }
  badge.className = "status-chip status-success";
  badge.textContent = "conexao validada";
  $("#connectionResult").innerHTML = `
    <div class="summary-grid">
      <div class="summary-card"><span>Base URL</span><strong class="mono">${escapeHtml(data.base_url || "-")}</strong></div>
      <div class="summary-card"><span>Usuario</span><strong>${escapeHtml(data.user?.name || "-")}</strong></div>
      <div class="summary-card"><span>ID</span><strong>${escapeHtml(String(data.user?.id || "-"))}</strong></div>
      <div class="summary-card"><span>Token usado</span><strong>${escapeHtml(data.masked_token || "-")}</strong></div>
      <div class="summary-card"><span>Origem</span><strong>${data.used_env_token ? `.env (${escapeHtml(formatEnvTokenSource(data.env_token_source))})` : "campo da interface"}</strong></div>
      <div class="summary-card"><span>Tipo</span><strong>${data.token_type === "api" ? "API token / access token" : "Token pessoal (PAT)"}</strong></div>
    </div>
  `;
}

async function testConnection() {
  const button = $("#testConnectionBtn");
  setBusy(button, true, "Testando...");
  hideNotice();
  try {
    if (!ensureConnectionConfigured()) return;
    const data = await apiFetch("/api/connection/test", { method: "POST", body: getConnectionPayload() });
    state.connectionSnapshot = data;
    renderConnectionResult(data);
    showNotice("Conexao validada com sucesso.", "success");
  } catch (error) {
    renderConnectionResult(null);
    showNotice(error.message, "error");
  } finally {
    setBusy(button, false);
  }
}

function renderRegisteredCourses() {
  if (!state.registeredCourses.length) {
    $("#registeredCourseList").innerHTML = `<div class="empty-state">Nenhum curso cadastrado.</div>`;
    return;
  }
  $("#registeredCourseList").innerHTML = state.registeredCourses.map((item) => `
    <div class="course-card">
      <div class="compact-header">
        <div>
          <strong>${escapeHtml(item.course_name || `Curso ${item.course_ref}`)}</strong>
          <div class="compact-meta">${escapeHtml(item.course_ref)}${item.course_code ? ` | ${escapeHtml(item.course_code)}` : ""}${item.term_name ? ` | ${escapeHtml(item.term_name)}` : ""}</div>
        </div>
        <button class="mini-btn danger" type="button" data-action="delete-course" data-course-ref="${escapeHtml(item.course_ref)}">Excluir</button>
      </div>
    </div>
  `).join("");
}

async function addRegisteredCourse() {
  const button = $("#addRegisteredCourseBtn");
  setBusy(button, true, "Buscando...");
  hideNotice();
  clearFieldValidation();
  try {
    if (!ensureConnectionConfigured()) return;
    const courseRef = $("#registeredCourseInput").value.trim();
    if (!courseRef) {
      markInvalid("#registeredCourseInput");
      focusField("#registeredCourseInput");
      showNotice("Digite o numero do curso para cadastrar.", "error");
      return;
    }
    const response = await apiFetch("/api/registered-courses", {
      method: "POST",
      body: { ...getConnectionPayload(), course_ref: courseRef },
    });
    $("#registeredCourseInput").value = "";
    await loadConfig();
    renderAll();
    showNotice(`Curso ${response.item.course_name || courseRef} cadastrado com sucesso.`, "success");
  } catch (error) {
    showNotice(error.message, "error");
  } finally {
    setBusy(button, false);
  }
}

async function handleRegisteredCourseClick(event) {
  const button = event.target.closest("[data-action='delete-course']");
  if (!button) return;
  try {
    await apiFetch(`/api/registered-courses/${encodeURIComponent(button.dataset.courseRef)}`, { method: "DELETE" });
    await loadConfig();
    renderAll();
    showNotice("Curso removido do cadastro local.", "success");
  } catch (error) {
    showNotice(error.message, "error");
  }
}

function renderGroups() {
  if (!state.groups.length) {
    $("#groupList").innerHTML = `<div class="empty-state">Nenhum grupo salvo.</div>`;
    return;
  }
  $("#groupList").innerHTML = state.groups.map((group) => `
    <div class="group-card">
      <div class="group-card-header">
        <div>
          <strong>${escapeHtml(group.name)}</strong>
          <div class="compact-meta">${escapeHtml(String(group.course_refs?.length || 0))} curso(s)</div>
        </div>
        <div class="group-card-actions">
          <button class="mini-btn" type="button" data-action="edit-group" data-group-id="${escapeHtml(group.id)}">Editar</button>
          <button class="mini-btn danger" type="button" data-action="delete-group" data-group-id="${escapeHtml(group.id)}">Excluir</button>
        </div>
      </div>
      ${group.description ? `<div class="compact-meta">${escapeHtml(group.description)}</div>` : ""}
      <div class="chips">
        ${(group.courses || []).map((course) => `<span class="chip">${escapeHtml(course.course_name || course.course_ref)} (${escapeHtml(course.course_ref)})</span>`).join("")}
      </div>
    </div>
  `).join("");
}

async function handleGroupClick(event) {
  const button = event.target.closest("[data-group-id]");
  if (!button) return;
  const group = state.groups.find((item) => item.id === button.dataset.groupId);
  if (!group) {
    showNotice("Grupo nao encontrado.", "error");
    return;
  }
  if (button.dataset.action === "edit-group") {
    openGroupModal(group);
    return;
  }
  try {
    await apiFetch(`/api/groups/${group.id}`, { method: "DELETE" });
    await loadConfig();
    renderAll();
    showNotice(`Grupo "${group.name}" excluido.`, "success");
  } catch (error) {
    showNotice(error.message, "error");
  }
}

function openGroupModal(group = null) {
  state.activeGroupId = group?.id || null;
  $("#groupModalTitle").textContent = group ? `Editar grupo: ${group.name}` : "Novo grupo";
  $("#groupName").value = group?.name || "";
  $("#groupDescription").value = group?.description || "";
  renderPicker("groupCoursePicker", coursePickerItems(), group?.course_refs || []);
  hideModalNotice();
  $("#groupModal").classList.remove("hidden");
  $("#groupModal").setAttribute("aria-hidden", "false");
}

function closeGroupModal() {
  state.activeGroupId = null;
  hideModalNotice();
  $("#groupModal").classList.add("hidden");
  $("#groupModal").setAttribute("aria-hidden", "true");
  $("#groupName").value = "";
  $("#groupDescription").value = "";
}

async function saveGroup() {
  const button = $("#saveGroupBtn");
  setBusy(button, true, "Salvando...");
  hideModalNotice();
  clearFieldValidation();
  try {
    const name = $("#groupName").value.trim();
    const description = $("#groupDescription").value.trim();
    const courseRefs = selectedValues("groupCoursePicker");
    if (!name) {
      markInvalid("#groupName");
      focusField("#groupName");
      showModalNotice("Informe um nome para o grupo.", "error");
      return;
    }
    if (!courseRefs.length) {
      showModalNotice("Selecione pelo menos um curso.", "error");
      return;
    }
    await apiFetch(state.activeGroupId ? `/api/groups/${state.activeGroupId}` : "/api/groups", {
      method: state.activeGroupId ? "PUT" : "POST",
      body: { name, description, course_refs: courseRefs },
    });
    await loadConfig();
    renderAll();
    closeGroupModal();
    showNotice("Grupo salvo com sucesso.", "success");
  } catch (error) {
    showModalNotice(error.message, "error");
  } finally {
    setBusy(button, false);
  }
}

function renderModeSwitch(kind) {
  document.querySelectorAll(`.mode-button[data-kind='${kind}']`).forEach((button) => {
    button.classList.toggle("active", button.dataset.mode === state[kind].mode);
  });
}

function renderTargetControls(kind) {
  const target = state[kind];
  const groupsMode = target.mode === "groups";
  const courseMode = target.mode === "courses";
  $(`#${kind}AllGroupsLine`).classList.toggle("hidden", !groupsMode);
  $(`#${kind}GroupPicker`).classList.toggle("hidden", !groupsMode);
  $(`#${kind}CoursePicker`).classList.toggle("hidden", !courseMode);
  $(`#${kind === "announcement" ? "announcementAllGroups" : "messageAllGroups"}`).checked = target.selectAllGroups;
  renderPickers();
  renderTargetSummary(kind);
  if (kind === "message") {
    renderMessageInfoPanel();
  }
}

function renderPickers() {
  renderPicker("groupCoursePicker", coursePickerItems(), selectedValues("groupCoursePicker"));
  renderPicker("announcementGroupPicker", groupPickerItems(), state.announcement.groupIds);
  renderPicker("announcementCoursePicker", coursePickerItems(), state.announcement.courseRefs);
  renderPicker("messageGroupPicker", groupPickerItems(), state.message.groupIds);
  renderPicker("messageCoursePicker", coursePickerItems(), state.message.courseRefs);
}

function renderPicker(pickerId, items, selectedIds) {
  const target = $(`#${pickerId}`);
  if (!target) return;
  const searchText = state.pickerSearch[pickerId] || "";
  const selectedSet = new Set(selectedIds);
  const filtered = items.filter((item) => item.search.includes(searchText));
  target.innerHTML = `
    <div class="picker-toolbar">
      <input type="text" data-picker-search="${pickerId}" placeholder="Buscar..." value="${escapeHtml(searchText)}">
      <div class="picker-selected">
        ${selectedIds.length ? selectedIds.map((value) => {
          const item = items.find((entry) => entry.id === value);
          return `<button class="chip" type="button" data-picker-remove="${pickerId}" data-value="${escapeHtml(value)}">${escapeHtml(item?.shortLabel || item?.label || value)} ×</button>`;
        }).join("") : `<span class="picker-help">Nenhum item selecionado.</span>`}
      </div>
    </div>
    <div class="picker-options">
      ${filtered.length ? filtered.map((item) => `
        <label class="picker-option">
          <input type="checkbox" data-picker-checkbox="${pickerId}" value="${escapeHtml(item.id)}" ${selectedSet.has(item.id) ? "checked" : ""}>
          <div>
            <strong>${escapeHtml(item.label)}</strong>
            <small>${escapeHtml(item.meta || "")}</small>
          </div>
        </label>
      `).join("") : `<div class="picker-empty">Nenhum item encontrado.</div>`}
    </div>
  `;
}

function togglePickerValue(pickerId, value, checked) {
  const target = pickerTarget(pickerId);
  const nextValues = checked
    ? unique([...(target.values || []), value])
    : (target.values || []).filter((item) => item !== value);
  target.set(nextValues);
  if (target.kind) {
    renderTargetControls(target.kind);
    persistUiState();
    return;
  }
  renderPicker("groupCoursePicker", coursePickerItems(), nextValues);
}

function pickerTarget(pickerId) {
  const map = {
    groupCoursePicker: {
      values: selectedValues("groupCoursePicker"),
      set(next) {
        renderPicker("groupCoursePicker", coursePickerItems(), next);
      },
    },
    announcementGroupPicker: {
      kind: "announcement",
      values: state.announcement.groupIds,
      set(next) {
        state.announcement.groupIds = next;
      },
    },
    announcementCoursePicker: {
      kind: "announcement",
      values: state.announcement.courseRefs,
      set(next) {
        state.announcement.courseRefs = next;
      },
    },
    messageGroupPicker: {
      kind: "message",
      values: state.message.groupIds,
      set(next) {
        state.message.groupIds = next;
      },
    },
    messageCoursePicker: {
      kind: "message",
      values: state.message.courseRefs,
      set(next) {
        state.message.courseRefs = next;
      },
    },
  };
  return map[pickerId];
}

function selectedValues(pickerId) {
  if (pickerId === "groupCoursePicker") {
    return Array.from(document.querySelectorAll(`#${pickerId} [data-picker-checkbox]:checked`)).map((input) => input.value);
  }
  if (pickerId === "announcementGroupPicker") return state.announcement.groupIds;
  if (pickerId === "announcementCoursePicker") return state.announcement.courseRefs;
  if (pickerId === "messageGroupPicker") return state.message.groupIds;
  if (pickerId === "messageCoursePicker") return state.message.courseRefs;
  return [];
}

function groupPickerItems() {
  return state.groups.map((group) => ({
    id: group.id,
    label: group.name,
    shortLabel: group.name,
    meta: `${group.course_refs.length} curso(s) | ${(group.courses || []).map((course) => course.course_name || course.course_ref).slice(0, 2).join(" | ")}`,
    search: `${group.name} ${(group.courses || []).map((course) => `${course.course_ref} ${course.course_name || ""}`).join(" ")}`.toLowerCase(),
  }));
}

function coursePickerItems() {
  return state.registeredCourses.map((course) => ({
    id: course.course_ref,
    label: course.course_name || `Curso ${course.course_ref}`,
    shortLabel: course.course_ref,
    meta: `${course.course_ref}${course.course_code ? ` | ${course.course_code}` : ""}${course.term_name ? ` | ${course.term_name}` : ""}`,
    search: `${course.course_ref} ${course.course_name || ""} ${course.course_code || ""} ${course.term_name || ""}`.toLowerCase(),
  }));
}

function renderTargetSummary(kind) {
  const target = state[kind];
  const summaryEl = $(`#${kind}TargetSummary`);
  const courses = target.mode === "groups"
    ? selectedGroups(kind).flatMap((group) => group.courses || [])
    : selectedCourses(kind);
  const modeLabelMap = {
    groups: "Grupos salvos",
    courses: "Cursos especificos",
  };
  const uniqueCourseRefs = unique(courses.map((course) => course.course_ref));
  summaryEl.innerHTML = `
    <div class="summary-card"><span>Modo</span><strong>${modeLabelMap[target.mode] || "-"}</strong></div>
    <div class="summary-card"><span>Grupos</span><strong>${target.mode === "groups" ? (target.selectAllGroups ? "Todos" : String(selectedGroups(kind).length)) : "-"}</strong></div>
    <div class="summary-card"><span>Cursos</span><strong>${escapeHtml(String(uniqueCourseRefs.length))}</strong></div>
    <div class="summary-card"><span>Selecao</span><strong>${escapeHtml(courses.slice(0, 2).map((course) => course.course_name || course.course_ref).join(" | ") || "Nenhuma")}${courses.length > 2 ? "..." : ""}</strong></div>
  `;
}

function selectedGroups(kind) {
  const target = state[kind];
  if (target.selectAllGroups && target.mode === "groups") return [...state.groups];
  const selectedIds = new Set(target.groupIds);
  return state.groups.filter((group) => selectedIds.has(group.id));
}

function selectedCourses(kind) {
  const refs = state[kind].courseRefs;
  return state.registeredCourses.filter((course) => refs.includes(course.course_ref));
}

function renderMessageInfoPanel() {
  const courses = state.message.mode === "groups"
    ? selectedGroups("message").flatMap((group) => group.courses || [])
    : selectedCourses("message");
  $("#messageInfoPanel").innerHTML = courses.length ? `
    <div class="summary-grid">
      <div class="summary-card"><span>Turmas resolvidas</span><strong>${escapeHtml(String(courses.length))}</strong></div>
      <div class="summary-card"><span>Modo</span><strong>${state.message.mode === "courses" ? "Cursos especificos" : "Grupos salvos"}</strong></div>
      <div class="summary-card"><span>Grupos</span><strong>${state.message.mode === "groups" ? (state.message.selectAllGroups ? "Todos" : String(selectedGroups("message").length)) : "-"}</strong></div>
      <div class="summary-card"><span>Cursos</span><strong>${escapeHtml(String(unique(courses.map((course) => course.course_ref)).length))}</strong></div>
    </div>
    <div class="chips">
      ${unique(courses.map((course) => `${course.course_name || course.course_ref} (${course.course_ref})`)).slice(0, 10).map((label) => `<span class="chip">${escapeHtml(label)}</span>`).join("")}
    </div>
  ` : "Escolha grupos salvos ou cursos especificos para ver o resumo aqui.";
}

function toggleScheduleField() {
  $("#scheduleField").classList.toggle("hidden", $("#publishMode").value !== "schedule");
}

function updateAnnouncementPreview() {
  $("#announcementPreview").srcdoc = $("#announcementMessage").value.trim() || "<p></p>";
}

async function submitAnnouncementJob(event) {
  event.preventDefault();
  const button = $("#announcementForm button[type='submit']");
  setBusy(button, true, "Enfileirando...");
  hideNotice();
  clearFieldValidation();
  try {
    if (!ensureConnectionConfigured() || !ensureTargetSelection("announcement")) return;
    if (!$("#announcementTitle").value.trim()) {
      markInvalid("#announcementTitle");
      focusField("#announcementTitle");
      showNotice("Informe o titulo do comunicado.", "error");
      return;
    }
    if (!$("#announcementMessage").value.trim()) {
      markInvalid("#announcementMessage");
      focusField("#announcementMessage");
      showNotice("Informe a mensagem HTML do comunicado.", "error");
      return;
    }
    if ($("#publishMode").value === "schedule" && !$("#announcementScheduleAt").value) {
      markInvalid("#announcementScheduleAt");
      focusField("#announcementScheduleAt");
      showNotice("Informe a data e hora do agendamento.", "error");
      return;
    }
    const response = await apiFetch("/api/announcements/jobs", {
      method: "POST",
      body: {
        ...getConnectionPayload(),
        ...getTargetPayload("announcement"),
        title: $("#announcementTitle").value.trim(),
        message_html: $("#announcementMessage").value.trim(),
        publish_mode: $("#publishMode").value,
        schedule_at_local: $("#announcementScheduleAt").value,
        client_timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        lock_comment: $("#lockComment").checked,
        dry_run: $("#announcementDryRun").checked,
      },
    });
    renderAnnouncementJob(response.job);
    startPolling(response.job.id, "announcement");
    showNotice("Lote de comunicados enfileirado.", "success");
  } catch (error) {
    showNotice(error.message, "error");
  } finally {
    setBusy(button, false);
  }
}

async function submitMessageJob(event) {
  event.preventDefault();
  const button = $("#messageForm button[type='submit']");
  setBusy(button, true, "Enfileirando...");
  hideNotice();
  clearFieldValidation();
  try {
    if (!ensureConnectionConfigured() || !ensureTargetSelection("message")) return;
    if (!$("#messageSubject").value.trim()) {
      markInvalid("#messageSubject");
      focusField("#messageSubject");
      showNotice("Informe o assunto da mensagem.", "error");
      return;
    }
    if (!$("#messageBody").value.trim()) {
      markInvalid("#messageBody");
      focusField("#messageBody");
      showNotice("Informe o corpo da mensagem.", "error");
      return;
    }
    const response = await apiFetch("/api/messages/jobs", {
      method: "POST",
      body: {
        ...getConnectionPayload(),
        ...getTargetPayload("message"),
        subject: $("#messageSubject").value.trim(),
        message: $("#messageBody").value.trim(),
        strategy: $("#messageStrategy").value,
        dedupe: $("#messageDedupe").checked,
        dry_run: $("#messageDryRun").checked,
      },
    });
    renderMessageJob(response.job);
    startPolling(response.job.id, "message");
    showNotice("Lote de caixa de entrada enfileirado.", "success");
  } catch (error) {
    showNotice(error.message, "error");
  } finally {
    setBusy(button, false);
  }
}

function startPolling(jobId, kind) {
  stopPolling(kind);
  const poll = async () => {
    try {
      const job = await apiFetch(`/api/jobs/${jobId}`);
      if (kind === "announcement") renderAnnouncementJob(job);
      if (kind === "message") renderMessageJob(job);
      if (["completed", "failed"].includes(job.status)) {
        stopPolling(kind);
        await loadHistory();
        renderReports();
      }
    } catch (error) {
      stopPolling(kind);
      showNotice(error.message, "error");
    }
  };
  poll();
  state.pollers.set(kind, window.setInterval(poll, 1500));
}

function stopPolling(kind) {
  const current = state.pollers.get(kind);
  if (current) {
    window.clearInterval(current);
    state.pollers.delete(kind);
  }
}

function renderAnnouncementJob(job) {
  $("#announcementJobCard").innerHTML = renderJobLayout(job, [
    { label: "Turma", format: (row) => `${escapeHtml(row.course_name || "-")}<div class="subtle mono">${escapeHtml(String(row.course_id || row.course_ref || "-"))}</div>` },
    { label: "Status", format: (row) => statusChip(row.status) },
    { label: "ID", format: (row) => escapeHtml(String(row.announcement_id || "-")) },
    { label: "Publicado", format: (row) => row.published ? "Sim" : "Nao" },
    { label: "Erro", format: (row) => escapeHtml(row.error || "-") },
  ]);
}

function renderMessageJob(job) {
  $("#messageJobCard").innerHTML = renderJobLayout(job, [
    { label: "Turma", format: (row) => `${escapeHtml(row.course_name || "-")}<div class="subtle mono">${escapeHtml(String(row.course_id || row.course_ref || "-"))}</div>` },
    { label: "Estrategia", format: (row) => escapeHtml(row.strategy_used || "-") },
    { label: "Alunos", format: (row) => escapeHtml(String(row.students_found || 0)) },
    { label: "Alvo", format: (row) => escapeHtml(String(row.recipients_targeted || 0)) },
    { label: "Enviados", format: (row) => escapeHtml(String(row.recipients_sent || 0)) },
    { label: "Status", format: (row) => statusChip(row.status) },
    { label: "Erro", format: (row) => escapeHtml(row.error || "-") },
  ]);
}

function renderJobLayout(job, columns) {
  const progress = job.progress || { percent: 0, current: 0, total: 0, step: "-" };
  const summaryEntries = Object.entries(job.result?.summary || {}).filter(([, value]) => typeof value !== "object");
  const reportLink = job.report_filename ? `<a class="btn btn-secondary" href="/api/history/${job.id}/csv">Baixar CSV</a>` : "";
  return `
    <div class="progress-shell">
      <div class="progress-track"><div class="progress-bar" style="width:${escapeHtml(String(progress.percent || 0))}%"></div></div>
      <div class="progress-meta"><span>${escapeHtml(progress.step || "-")}</span><span>${escapeHtml(String(progress.current || 0))} / ${escapeHtml(String(progress.total || 0))}</span></div>
    </div>
    <div class="status-line">${statusChip(job.status)}${job.error ? `<span>${escapeHtml(job.error)}</span>` : ""}</div>
    <div class="summary-grid">${summaryEntries.slice(0, 6).map(([key, value]) => `<div class="summary-card"><span>${escapeHtml(toTitle(key))}</span><strong>${escapeHtml(formatSummaryValue(value))}</strong></div>`).join("")}</div>
    <div class="button-row">${reportLink}</div>
    ${job.result?.course_results?.length ? renderTable(columns, job.result.course_results) : `<div class="empty-state">Aguardando detalhes do processamento...</div>`}
  `;
}

function renderReports() {
  renderReportMetrics();
  renderHistoryList();
  renderReportDetail();
}

function renderReportMetrics() {
  const completed = state.history.filter((item) => item.status === "completed").length;
  const failed = state.history.filter((item) => item.status === "failed").length;
  const last = state.history[0];
  $("#reportMetrics").innerHTML = [
    metricCard("Relatorios salvos", state.history.length),
    metricCard("Concluidos", completed),
    metricCard("Com falha", failed),
    metricCard("Ultimo tipo", last?.kind || "-"),
  ].join("");
}

function renderHistoryList() {
  if (!state.history.length) {
    $("#historyList").innerHTML = `<div class="empty-state">Nenhum relatorio encontrado.</div>`;
    return;
  }
  $("#historyList").innerHTML = state.history.map((item) => `
    <div class="history-item">
      <div class="history-item-header">
        <div>
          <strong>${escapeHtml(item.title || item.kind || "Relatorio")}</strong>
          <div class="compact-meta">${escapeHtml(formatDate(item.created_at))}</div>
        </div>
        <div class="history-actions">
          ${statusChip(item.status)}
          <button class="mini-btn" type="button" data-action="open-report" data-job-id="${escapeHtml(item.id)}">Abrir</button>
        </div>
      </div>
      <div class="chips">${summaryChips(item.result?.summary || {})}</div>
    </div>
  `).join("");
}

function renderReportDetail() {
  const item = state.history.find((entry) => entry.id === state.selectedReportId) || state.history[0];
  if (!item) {
    $("#historyDetail").innerHTML = `<div class="empty-state">Selecione um relatorio para ver os detalhes.</div>`;
    return;
  }
  const reportLink = item.report_filename ? `<a class="btn btn-secondary" href="/api/history/${item.id}/csv">Baixar CSV</a>` : "";
  const summaryEntries = Object.entries(item.result?.summary || {}).filter(([, value]) => typeof value !== "object");
  $("#historyDetail").innerHTML = `
    <div class="status-line">
      ${statusChip(item.status)}
      <span>${escapeHtml(item.title || item.kind || "Relatorio")} - ${escapeHtml(formatDate(item.created_at))}</span>
    </div>
    <div class="summary-grid">${summaryEntries.slice(0, 8).map(([key, value]) => `<div class="summary-card"><span>${escapeHtml(toTitle(key))}</span><strong>${escapeHtml(formatSummaryValue(value))}</strong></div>`).join("")}</div>
    <div class="button-row">${reportLink}</div>
    ${(item.result?.course_results || []).length ? renderTable(reportColumns(item.kind), item.result.course_results) : `<div class="empty-state">Este relatorio ainda nao possui resultados detalhados.</div>`}
  `;
}

function reportColumns(kind) {
  if (kind === "message") {
    return [
      { label: "Turma", format: (row) => `${escapeHtml(row.course_name || "-")}<div class="subtle mono">${escapeHtml(String(row.course_id || row.course_ref || "-"))}</div>` },
      { label: "Alunos", format: (row) => escapeHtml(String(row.students_found || 0)) },
      { label: "Alvo", format: (row) => escapeHtml(String(row.recipients_targeted || 0)) },
      { label: "Enviados", format: (row) => escapeHtml(String(row.recipients_sent || 0)) },
      { label: "Status", format: (row) => statusChip(row.status) },
      { label: "Erro", format: (row) => escapeHtml(row.error || "-") },
    ];
  }
  return [
    { label: "Turma", format: (row) => `${escapeHtml(row.course_name || "-")}<div class="subtle mono">${escapeHtml(String(row.course_id || row.course_ref || "-"))}</div>` },
    { label: "ID", format: (row) => escapeHtml(String(row.announcement_id || "-")) },
    { label: "Publicado", format: (row) => row.published ? "Sim" : "Nao" },
    { label: "Status", format: (row) => statusChip(row.status) },
    { label: "Erro", format: (row) => escapeHtml(row.error || "-") },
  ];
}

function renderTable(columns, rows) {
  return `
    <div class="table-wrap">
      <table>
        <thead><tr>${columns.map((column) => `<th>${escapeHtml(column.label)}</th>`).join("")}</tr></thead>
        <tbody>${rows.map((row) => `<tr>${columns.map((column) => `<td>${column.format(row)}</td>`).join("")}</tr>`).join("")}</tbody>
      </table>
    </div>
  `;
}

function metricCard(label, value) {
  return `<div class="overview-card"><span>${escapeHtml(label)}</span><strong>${escapeHtml(String(value))}</strong></div>`;
}

function summaryChips(summary) {
  const entries = Object.entries(summary).filter(([, value]) => typeof value !== "object").slice(0, 4);
  if (!entries.length) return `<span class="chip dim">Sem resumo</span>`;
  return entries.map(([key, value]) => `<span class="chip">${escapeHtml(toTitle(key))}: ${escapeHtml(formatSummaryValue(value))}</span>`).join("");
}

function renderSettingsInfo(settings) {
  $("#settingsInfo").innerHTML = `
    <div class="dashboard-item"><strong>Base URL padrao</strong><div class="compact-meta mono">${escapeHtml(settings.default_base_url || "nao configurada")}</div></div>
    <div class="dashboard-item"><strong>Token no .env</strong><div class="compact-meta">${settings.env_token_available ? `Disponivel como ${escapeHtml(formatEnvTokenSource(settings.env_token_source))}.` : "Nao configurado."}</div></div>
    <div class="dashboard-item"><strong>Retry e timeout</strong><div class="compact-meta">${escapeHtml(String(settings.retry_max_attempts || 0))} tentativa(s) | atraso base ${escapeHtml(String(settings.retry_base_delay || 0))}s | timeout ${escapeHtml(String(settings.request_timeout || 0))}s</div></div>
    <div class="dashboard-item"><strong>Arquivo .env</strong><div class="compact-meta mono">${escapeHtml(settings.env_file_path || "-")}</div></div>
  `;
}

async function loadEnvFile(force = false) {
  if (state.envLoaded && !force) return;
  try {
    const data = await apiFetch("/api/settings/env");
    state.envLoaded = true;
    state.envContent = data.content || "";
    $("#envEditor").value = state.envContent;
    $("#envPath").textContent = data.path || "-";
  } catch (error) {
    showNotice(error.message, "error");
  }
}

async function saveEnvFile() {
  const button = $("#saveEnvBtn");
  setBusy(button, true, "Salvando...");
  try {
    const response = await apiFetch("/api/settings/env", { method: "PUT", body: { content: $("#envEditor").value } });
    state.envLoaded = true;
    state.envContent = response.content || "";
    $("#envPath").textContent = response.path || "-";
    await loadConfig();
    renderAll();
    showNotice("Arquivo .env salvo com sucesso.", "success");
  } catch (error) {
    showNotice(error.message, "error");
  } finally {
    setBusy(button, false);
  }
}

function statusChip(status) {
  const value = String(status || "info").toLowerCase();
  return `<span class="status-chip status-${escapeHtml(value)}">${escapeHtml(value)}</span>`;
}

function unique(values) {
  return [...new Set(values.filter(Boolean).map((value) => String(value).trim()).filter(Boolean))];
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function toTitle(value) {
  return String(value).replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatSummaryValue(value) {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "boolean") return value ? "Sim" : "Nao";
  return String(value);
}

function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("pt-BR");
}

function formatEnvTokenSource(value) {
  const map = {
    access_token: "CANVAS_ACCESS_TOKEN",
    personal_access_token: "CANVAS_PERSONAL_ACCESS_TOKEN",
    api_token: "CANVAS_API_TOKEN",
    none: "nao configurado",
  };
  return map[value] || value || "token";
}
