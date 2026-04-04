const STORAGE_KEY = "canvas-bulk-panel-ui-v6";

const state = {
  config: null,
  groups: [],
  registeredCourses: [],
  courseCatalog: [],
  courseCatalogSelection: [],
  courseCatalogLoaded: false,
  courseCatalogLoading: false,
  history: [],
  reportAnalytics: null,
  reportDays: 30,
  recurrences: [],
  connectionSnapshot: null,
  envLoaded: false,
  envContent: "",
  envVisible: false,
  envRevealTimer: null,
  activeGroupId: null,
  groupModalCourseRefs: [],
  review: {
    kind: null,
    data: null,
  },
  recurrenceCancel: {
    id: null,
    item: null,
  },
  recurrenceReview: {
    mode: null,
    payload: null,
    preview: null,
  },
  selectedReportId: null,
  templateFocusFieldId: null,
  pickerSearch: {},
  pickerReorder: {},
  collapsedCards: {},
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
    previewRecipients: [],
  },
  recurrence: {
    mode: "groups",
    groupIds: [],
    courseRefs: [],
    selectAllGroups: false,
    preview: null,
    previewSignature: "",
    agendaSearch: "",
    agendaWindowDays: 30,
    listSearch: "",
    listStatus: "all",
  },
  recurrenceEdit: {
    id: null,
    mode: "groups",
    groupIds: [],
    courseRefs: [],
    selectAllGroups: false,
    preview: null,
    previewSignature: "",
  },
  engagement: {
    mode: "groups",
    groupIds: [],
    courseRefs: [],
    selectAllGroups: false,
    preview: null,
  },
  pollers: new Map(),
};

document.addEventListener("DOMContentLoaded", () => {
  bindTabs();
  bindEvents();
  restoreUiState();
  toggleScheduleField();
  updateAnnouncementPreview();
  updateMessagePreview();
  updateRecurrenceSamplePreview();
  updateRecurrenceEditSamplePreview();
  updateEngagementMessagePreview();
  window.addEventListener("resize", syncCollapsibleCards);
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
    state.courseCatalog = [];
    state.courseCatalogSelection = [];
    state.courseCatalogLoaded = false;
    clearMessagePreviewRecipients({ updatePreview: false });
    renderConnectionResult(null);
    persistUiState();
  });
  $("#baseUrl").addEventListener("blur", () => {
    $("#baseUrl").value = normalizeBaseUrlInput($("#baseUrl").value);
    persistUiState();
  });
  $("#apiToken").addEventListener("input", () => {
    state.connectionSnapshot = null;
    state.courseCatalog = [];
    state.courseCatalogSelection = [];
    state.courseCatalogLoaded = false;
    clearMessagePreviewRecipients({ updatePreview: false });
    renderConnectionResult(null);
    persistUiState();
  });
  $("#tokenType").addEventListener("change", () => {
    state.connectionSnapshot = null;
    state.courseCatalog = [];
    state.courseCatalogSelection = [];
    state.courseCatalogLoaded = false;
    clearMessagePreviewRecipients({ updatePreview: false });
    renderConnectionResult(null);
    persistUiState();
  });
  $("#testConnectionBtn").addEventListener("click", testConnection);

  $("#registeredCourseInput").addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      addRegisteredCourse();
    }
  });
  $("#courseCatalogSearchInput").addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      loadCourseCatalog();
    }
  });
  $("#addRegisteredCourseBtn").addEventListener("click", addRegisteredCourse);
  $("#loadCourseCatalogBtn").addEventListener("click", loadCourseCatalog);
  $("#registerCatalogSelectionBtn").addEventListener("click", registerSelectedCatalogCourses);
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
  $("#closeSendReviewModalBtn").addEventListener("click", closeSendReviewModal);
  $("#cancelSendReviewBtn").addEventListener("click", closeSendReviewModal);
  $("#confirmSendReviewBtn").addEventListener("click", confirmReviewedSend);
  $("#sendReviewModal").addEventListener("click", (event) => {
    if (event.target.dataset.action === "close-send-review-modal") {
      closeSendReviewModal();
    }
  });
  $("#closeRecurrenceCancelModalBtn").addEventListener("click", closeRecurrenceCancelModal);
  $("#cancelRecurrenceCancelBtn").addEventListener("click", closeRecurrenceCancelModal);
  $("#confirmRecurrenceCancelBtn").addEventListener("click", confirmRecurrenceCancel);
  $("#recurrenceCancelModal").addEventListener("click", (event) => {
    if (event.target.dataset.action === "close-recurrence-cancel-modal") {
      closeRecurrenceCancelModal();
    }
  });
  $("#closeRecurrenceEditModalBtn").addEventListener("click", closeRecurrenceEditModal);
  $("#cancelRecurrenceEditBtn").addEventListener("click", closeRecurrenceEditModal);
  $("#previewRecurrenceEditBtn").addEventListener("click", previewRecurrenceEdit);
  $("#recurrenceEditForm").addEventListener("submit", submitRecurrenceEdit);
  $("#recurrenceEditModal").addEventListener("click", (event) => {
    if (event.target.dataset.action === "close-recurrence-edit-modal") {
      closeRecurrenceEditModal();
    }
  });
  $("#closeRecurrenceReviewModalBtn").addEventListener("click", closeRecurrenceReviewModal);
  $("#cancelRecurrenceReviewBtn").addEventListener("click", closeRecurrenceReviewModal);
  $("#confirmRecurrenceReviewBtn").addEventListener("click", confirmRecurrenceReview);
  $("#recurrenceReviewModal").addEventListener("click", (event) => {
    if (event.target.dataset.action === "close-recurrence-review-modal") {
      closeRecurrenceReviewModal();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !$("#groupModal").classList.contains("hidden")) {
      closeGroupModal();
    }
    if (event.key === "Escape" && !$("#sendReviewModal").classList.contains("hidden")) {
      closeSendReviewModal();
    }
    if (event.key === "Escape" && !$("#recurrenceCancelModal").classList.contains("hidden")) {
      closeRecurrenceCancelModal();
    }
    if (event.key === "Escape" && !$("#recurrenceEditModal").classList.contains("hidden")) {
      closeRecurrenceEditModal();
    }
    if (event.key === "Escape" && !$("#recurrenceReviewModal").classList.contains("hidden")) {
      closeRecurrenceReviewModal();
    }
  });

  $("#announcementAllGroups").addEventListener("change", () => {
    state.announcement.selectAllGroups = $("#announcementAllGroups").checked;
    renderTargetControls("announcement");
    persistUiState();
  });
  $("#messageAllGroups").addEventListener("change", () => {
    state.message.selectAllGroups = $("#messageAllGroups").checked;
    clearMessagePreviewRecipients({ updatePreview: false });
    renderTargetControls("message");
    persistUiState();
  });
  $("#recurrenceAllGroups").addEventListener("change", () => {
    state.recurrence.selectAllGroups = $("#recurrenceAllGroups").checked;
    invalidateRecurrencePreview("recurrence");
    renderTargetControls("recurrence");
    persistUiState();
  });
  $("#recurrenceEditAllGroups").addEventListener("change", () => {
    state.recurrenceEdit.selectAllGroups = $("#recurrenceEditAllGroups").checked;
    invalidateRecurrencePreview("recurrenceEdit");
    renderTargetControls("recurrenceEdit");
  });
  $("#engagementAllGroups").addEventListener("change", () => {
    state.engagement.selectAllGroups = $("#engagementAllGroups").checked;
    state.engagement.preview = null;
    renderEngagementPreview(null);
    renderTargetControls("engagement");
    persistUiState();
  });

  document.addEventListener("click", handleDelegatedClick);
  document.addEventListener("input", handleDelegatedInput);
  document.addEventListener("change", handleDelegatedChange);
  document.addEventListener("focusin", handleDelegatedFocusIn);
  document.addEventListener("focusout", handleDelegatedFocusOut);
  document.addEventListener("dragstart", handleDelegatedDragStart);
  document.addEventListener("dragover", handleDelegatedDragOver);
  document.addEventListener("dragleave", handleDelegatedDragLeave);
  document.addEventListener("dragend", clearTemplateDragState);
  document.addEventListener("drop", handleDelegatedDrop);

  $("#publishMode").addEventListener("change", () => {
    toggleScheduleField();
    renderAnnouncementInfoPanel();
    persistUiState();
  });
  $("#announcementTitle").addEventListener("input", () => {
    updateAnnouncementPreview();
    persistUiState();
  });
  $("#announcementMessage").addEventListener("input", () => {
    updateAnnouncementPreview();
    persistUiState();
  });
  $("#announcementScheduleAt").addEventListener("input", persistUiState);
  $("#announcementScheduleAt").addEventListener("input", renderAnnouncementInfoPanel);
  $("#lockComment").addEventListener("change", () => {
    renderAnnouncementInfoPanel();
    persistUiState();
  });
  $("#announcementDryRun").addEventListener("change", () => {
    renderAnnouncementInfoPanel();
    persistUiState();
  });
  $("#announcementAttachment").addEventListener("change", updateAttachmentMeta);
  $("#announcementForm").addEventListener("submit", submitAnnouncementJob);

  $("#messageSubject").addEventListener("input", () => {
    updateMessagePreview();
    persistUiState();
  });
  $("#messageBody").addEventListener("input", () => {
    updateMessagePreview();
    persistUiState();
  });
  $("#messageStrategy").addEventListener("change", persistUiState);
  $("#messageStrategy").addEventListener("change", renderMessageInfoPanel);
  $("#messageDedupe").addEventListener("change", () => {
    renderMessageInfoPanel();
    persistUiState();
  });
  $("#messageDryRun").addEventListener("change", persistUiState);
  $("#messageDryRun").addEventListener("change", renderMessageInfoPanel);
  $("#messageAttachment").addEventListener("change", updateAttachmentMeta);
  $("#messageForm").addEventListener("submit", submitMessageJob);

  $("#recurrenceName").addEventListener("input", () => {
    invalidateRecurrencePreview("recurrence");
    persistUiState();
  });
  $("#recurrenceTitle").addEventListener("input", () => {
    invalidateRecurrencePreview("recurrence");
    updateRecurrenceSamplePreview();
    persistUiState();
  });
  $("#recurrenceMessage").addEventListener("input", () => {
    invalidateRecurrencePreview("recurrence");
    updateRecurrenceSamplePreview();
    persistUiState();
  });
  $("#recurrenceType").addEventListener("change", () => {
    invalidateRecurrencePreview("recurrence");
    persistUiState();
  });
  $("#recurrenceInterval").addEventListener("input", () => {
    invalidateRecurrencePreview("recurrence");
    persistUiState();
  });
  $("#recurrenceFirstPublishAt").addEventListener("input", () => {
    invalidateRecurrencePreview("recurrence");
    persistUiState();
  });
  $("#recurrenceOccurrences").addEventListener("input", () => {
    invalidateRecurrencePreview("recurrence");
    persistUiState();
  });
  $("#recurrenceLockComment").addEventListener("change", () => {
    invalidateRecurrencePreview("recurrence");
    persistUiState();
  });
  $("#recurrenceAgendaSearch").addEventListener("input", () => {
    state.recurrence.agendaSearch = $("#recurrenceAgendaSearch").value.trim().toLowerCase();
    renderRecurrenceAgenda();
    persistUiState();
  });
  $("#recurrenceAgendaWindow").addEventListener("change", () => {
    state.recurrence.agendaWindowDays = Number($("#recurrenceAgendaWindow").value || 30);
    renderRecurrenceAgenda();
    persistUiState();
  });
  $("#recurrenceListSearch").addEventListener("input", () => {
    state.recurrence.listSearch = $("#recurrenceListSearch").value.trim().toLowerCase();
    renderRecurrences();
    persistUiState();
  });
  $("#recurrenceListStatus").addEventListener("change", () => {
    state.recurrence.listStatus = $("#recurrenceListStatus").value || "all";
    renderRecurrences();
    persistUiState();
  });
  $("#previewRecurrenceBtn").addEventListener("click", previewRecurrence);
  $("#recurrenceForm").addEventListener("submit", submitRecurrence);
  $("#recurrenceEditName").addEventListener("input", () => {
    invalidateRecurrencePreview("recurrenceEdit");
    updateRecurrenceEditSamplePreview();
  });
  $("#recurrenceEditTitle").addEventListener("input", () => {
    invalidateRecurrencePreview("recurrenceEdit");
    updateRecurrenceEditSamplePreview();
  });
  $("#recurrenceEditMessage").addEventListener("input", () => {
    invalidateRecurrencePreview("recurrenceEdit");
    updateRecurrenceEditSamplePreview();
  });
  $("#recurrenceEditType").addEventListener("change", () => {
    invalidateRecurrencePreview("recurrenceEdit");
    updateRecurrenceEditSamplePreview();
  });
  $("#recurrenceEditInterval").addEventListener("input", () => {
    invalidateRecurrencePreview("recurrenceEdit");
    updateRecurrenceEditSamplePreview();
  });
  $("#recurrenceEditFirstPublishAt").addEventListener("input", () => {
    invalidateRecurrencePreview("recurrenceEdit");
    updateRecurrenceEditSamplePreview();
  });
  $("#recurrenceEditOccurrences").addEventListener("input", () => {
    invalidateRecurrencePreview("recurrenceEdit");
    updateRecurrenceEditSamplePreview();
  });
  $("#recurrenceEditLockComment").addEventListener("change", () => {
    invalidateRecurrencePreview("recurrenceEdit");
    updateRecurrenceEditSamplePreview();
  });

  $("#engagementCriteriaMode").addEventListener("change", () => {
    state.engagement.preview = null;
    renderTargetSummary("engagement");
    renderEngagementPreview(null);
    persistUiState();
  });
  $("#engagementMatchMode").addEventListener("change", persistUiState);
  $("#engagementInactiveDays").addEventListener("input", persistUiState);
  $("#engagementMaxActivityMinutes").addEventListener("input", persistUiState);
  $("#engagementOnlyModules").addEventListener("change", persistUiState);
  $("#engagementRequireNeverAccessed").addEventListener("change", persistUiState);
  $("#engagementRequireIncomplete").addEventListener("change", persistUiState);
  $("#engagementSubject").addEventListener("input", () => {
    updateEngagementMessagePreview();
    persistUiState();
  });
  $("#engagementMessage").addEventListener("input", () => {
    updateEngagementMessagePreview();
    persistUiState();
  });
  $("#engagementDryRun").addEventListener("change", () => {
    updateEngagementMessagePreview();
    persistUiState();
  });
  $("#previewEngagementBtn").addEventListener("click", previewEngagementTargets);
  $("#engagementForm").addEventListener("submit", submitEngagementJob);

  $("#refreshHistoryBtn").addEventListener("click", refreshReports);
  $("#refreshAnalyticsBtn").addEventListener("click", refreshReports);
  $("#reportDaysSelect").addEventListener("change", async () => {
    state.reportDays = Number($("#reportDaysSelect").value || 30);
    persistUiState();
    await refreshReports();
  });
  $("#revealEnvBtn").addEventListener("click", revealEnvFileTemporarily);
  $("#saveEnvBtn").addEventListener("click", saveEnvFile);
  $("#wipeDatabaseBtn").addEventListener("click", wipeDatabase);
}

function handleDelegatedClick(event) {
  const tokenChip = event.target.closest("[data-template-token]");
  if (tokenChip) {
    insertTemplateToken(tokenChip.dataset.templateScope, tokenChip.dataset.templateToken);
    return;
  }

  const modeButton = event.target.closest("[data-kind][data-mode]");
  if (modeButton) {
    const kind = modeButton.dataset.kind;
    state[kind].mode = modeButton.dataset.mode;
    if (kind === "message") {
      clearMessagePreviewRecipients({ updatePreview: false });
    }
    if (kind === "engagement") {
      state.engagement.preview = null;
      renderEngagementPreview(null);
    }
    if (kind === "recurrence") {
      invalidateRecurrencePreview("recurrence");
    }
    if (kind === "recurrenceEdit") {
      invalidateRecurrencePreview("recurrenceEdit");
    }
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
    return;
  }

  const recurrenceAction = event.target.closest("[data-recurrence-action]");
  if (recurrenceAction) {
    handleRecurrenceAction(recurrenceAction.dataset.recurrenceAction, recurrenceAction.dataset.recurrenceId);
    return;
  }

  const cardToggle = event.target.closest("[data-card-toggle]");
  if (cardToggle) {
    toggleCardCollapse(cardToggle.dataset.cardToggle);
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
  togglePickerValue(checkbox.dataset.pickerCheckbox, checkbox.value, checkbox.checked, { deferRender: true });
}

function handleDelegatedFocusIn(event) {
  const templateField = event.target.closest("[data-template-scope]");
  if (templateField) {
    state.templateFocusFieldId = templateField.id;
    document.querySelectorAll("[data-template-scope]").forEach((field) => {
      field.classList.toggle("template-target-active", field === templateField);
    });
  }
  const root = event.target.closest("[data-picker-root]");
  if (!root) return;
  const pickerId = root.dataset.pickerRoot;
  state.pickerReorder[pickerId] = false;
}

function handleDelegatedFocusOut(event) {
  const templateField = event.target.closest("[data-template-scope]");
  if (templateField) {
    window.setTimeout(() => {
      const activeField = document.activeElement?.closest?.("[data-template-scope]") || null;
      document.querySelectorAll("[data-template-scope]").forEach((field) => {
        field.classList.toggle("template-target-active", field === activeField);
      });
      state.templateFocusFieldId = activeField?.id || null;
    }, 0);
  }
  const root = event.target.closest("[data-picker-root]");
  if (!root) return;
  const pickerId = root.dataset.pickerRoot;
  const nextFocused = event.relatedTarget instanceof Element ? event.relatedTarget : null;
  if (nextFocused && root.contains(nextFocused)) {
    return;
  }
  window.setTimeout(() => {
    const pickerRoot = document.querySelector(`#${pickerId} [data-picker-root="${pickerId}"]`);
    if (!pickerRoot) return;
    if (pickerRoot.contains(document.activeElement)) return;
    state.pickerReorder[pickerId] = true;
    rerenderPickerById(pickerId);
  }, 40);
}

function handleDelegatedDragStart(event) {
  const tokenChip = event.target.closest("[data-template-token]");
  if (!tokenChip || !event.dataTransfer) return;
  event.dataTransfer.setData("text/template-token", tokenChip.dataset.templateToken || "");
  event.dataTransfer.setData("text/template-scope", tokenChip.dataset.templateScope || "");
  event.dataTransfer.effectAllowed = "copy";
}

function handleDelegatedDragOver(event) {
  const targetField = event.target.closest("[data-template-scope]");
  if (!targetField || !event.dataTransfer?.types?.includes("text/template-token")) return;
  const scope = event.dataTransfer.getData("text/template-scope");
  if (scope && scope !== targetField.dataset.templateScope) return;
  event.preventDefault();
  targetField.classList.add("template-target-dragover");
}

function handleDelegatedDrop(event) {
  const targetField = event.target.closest("[data-template-scope]");
  if (!targetField || !event.dataTransfer) return;
  const token = event.dataTransfer.getData("text/template-token");
  const scope = event.dataTransfer.getData("text/template-scope");
  if (!token || (scope && scope !== targetField.dataset.templateScope)) return;
  event.preventDefault();
  clearTemplateDragState();
  insertTextAtCursor(targetField, token);
  targetField.focus();
  handleTemplateFieldChanged(targetField.dataset.templateScope);
}

function handleDelegatedDragLeave(event) {
  const targetField = event.target.closest("[data-template-scope]");
  if (!targetField) return;
  targetField.classList.remove("template-target-dragover");
}

function clearTemplateDragState() {
  document.querySelectorAll(".template-target-dragover").forEach((field) => {
    field.classList.remove("template-target-dragover");
  });
}

function restoreUiState() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
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
    $("#recurrenceName").value = saved.recurrenceName || "";
    $("#recurrenceTitle").value = saved.recurrenceTitle || "";
    $("#recurrenceMessage").value = saved.recurrenceMessage || "";
    $("#recurrenceType").value = saved.recurrenceType || "weekly";
    $("#recurrenceInterval").value = saved.recurrenceInterval || "1";
    $("#recurrenceFirstPublishAt").value = saved.recurrenceFirstPublishAt || "";
    $("#recurrenceOccurrences").value = saved.recurrenceOccurrences || "8";
    $("#recurrenceLockComment").checked = Boolean(saved.recurrenceLockComment);
    $("#recurrenceAgendaSearch").value = saved.recurrenceAgendaSearch || "";
    $("#recurrenceAgendaWindow").value = saved.recurrenceAgendaWindow || "30";
    $("#recurrenceListSearch").value = saved.recurrenceListSearch || "";
    $("#recurrenceListStatus").value = saved.recurrenceListStatus || "all";
    $("#engagementCriteriaMode").value = saved.engagementCriteriaMode || "never_accessed_or_incomplete_resources";
    $("#engagementMatchMode").value = saved.engagementMatchMode || "or";
    $("#engagementInactiveDays").value = saved.engagementInactiveDays || "";
    $("#engagementMaxActivityMinutes").value = saved.engagementMaxActivityMinutes || "";
    $("#engagementOnlyModules").checked = Boolean(saved.engagementOnlyModules);
    $("#engagementRequireNeverAccessed").checked = Boolean(saved.engagementRequireNeverAccessed);
    $("#engagementRequireIncomplete").checked = Boolean(saved.engagementRequireIncomplete);
    $("#engagementSubject").value = saved.engagementSubject || "";
    $("#engagementMessage").value = saved.engagementMessage || "";
    $("#engagementDryRun").checked = Boolean(saved.engagementDryRun);
    state.reportDays = Number(saved.reportDays || 30);
    if ($("#reportDaysSelect")) {
      $("#reportDaysSelect").value = String(state.reportDays);
    }
    state.announcement = { ...state.announcement, ...(saved.announcement || {}) };
    state.message = { ...state.message, ...(saved.message || {}) };
    state.recurrence = { ...state.recurrence, ...(saved.recurrence || {}), preview: null };
    state.recurrence.agendaSearch = saved.recurrenceAgendaSearch || "";
    state.recurrence.agendaWindowDays = Number(saved.recurrenceAgendaWindow || saved.recurrence?.agendaWindowDays || 30);
    state.recurrence.listSearch = saved.recurrenceListSearch || saved.recurrence?.listSearch || "";
    state.recurrence.listStatus = saved.recurrenceListStatus || saved.recurrence?.listStatus || "all";
    state.engagement = { ...state.engagement, ...(saved.engagement || {}), preview: null };
    state.collapsedCards = { ...(saved.collapsedCards || {}) };
    if (!["groups", "courses"].includes(state.message.mode)) {
      state.message.mode = "groups";
    }
    if (!["groups", "courses"].includes(state.recurrence.mode)) {
      state.recurrence.mode = "groups";
    }
    if (!["groups", "courses"].includes(state.engagement.mode)) {
      state.engagement.mode = "groups";
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
      recurrenceName: $("#recurrenceName").value,
      recurrenceTitle: $("#recurrenceTitle").value,
      recurrenceMessage: $("#recurrenceMessage").value,
      recurrenceType: $("#recurrenceType").value,
      recurrenceInterval: $("#recurrenceInterval").value,
      recurrenceFirstPublishAt: $("#recurrenceFirstPublishAt").value,
      recurrenceOccurrences: $("#recurrenceOccurrences").value,
      recurrenceLockComment: $("#recurrenceLockComment").checked,
      recurrenceAgendaSearch: $("#recurrenceAgendaSearch").value,
      recurrenceAgendaWindow: $("#recurrenceAgendaWindow").value,
      recurrenceListSearch: $("#recurrenceListSearch").value,
      recurrenceListStatus: $("#recurrenceListStatus").value,
      engagementCriteriaMode: $("#engagementCriteriaMode").value,
      engagementMatchMode: $("#engagementMatchMode").value,
      engagementInactiveDays: $("#engagementInactiveDays").value,
      engagementMaxActivityMinutes: $("#engagementMaxActivityMinutes").value,
      engagementOnlyModules: $("#engagementOnlyModules").checked,
      engagementRequireNeverAccessed: $("#engagementRequireNeverAccessed").checked,
      engagementRequireIncomplete: $("#engagementRequireIncomplete").checked,
      engagementSubject: $("#engagementSubject").value,
      engagementMessage: $("#engagementMessage").value,
      engagementDryRun: $("#engagementDryRun").checked,
      reportDays: state.reportDays,
      announcement: state.announcement,
      message: {
        mode: state.message.mode,
        groupIds: state.message.groupIds,
        courseRefs: state.message.courseRefs,
        selectAllGroups: state.message.selectAllGroups,
      },
      recurrence: {
        mode: state.recurrence.mode,
        groupIds: state.recurrence.groupIds,
        courseRefs: state.recurrence.courseRefs,
        selectAllGroups: state.recurrence.selectAllGroups,
        agendaSearch: state.recurrence.agendaSearch,
        agendaWindowDays: state.recurrence.agendaWindowDays,
        listSearch: state.recurrence.listSearch,
        listStatus: state.recurrence.listStatus,
      },
      engagement: {
        mode: state.engagement.mode,
        groupIds: state.engagement.groupIds,
        courseRefs: state.engagement.courseRefs,
        selectAllGroups: state.engagement.selectAllGroups,
      },
      collapsedCards: state.collapsedCards,
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
  if (tabName !== "settings") {
    hideEnvFile();
  }
  window.setTimeout(syncCollapsibleCards, 0);
  persistUiState();
  if (tabName === "organization") {
    maybeAutoLoadCourseCatalog();
  }
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
  const tabPanel = element.closest(".tab-panel");
  if (tabPanel && !tabPanel.classList.contains("active")) {
    openTab(tabPanel.id.replace(/^tab-/, ""));
  }
  element.focus();
  element.scrollIntoView({ behavior: "smooth", block: "center" });
}

function ensureConnectionConfigured() {
  clearFieldValidation();
  const baseUrl = normalizeBaseUrlInput($("#baseUrl").value);
  const effectiveBaseUrl = baseUrl || normalizeBaseUrlInput(state.config?.default_base_url || "");
  const accessToken = $("#apiToken").value.trim();
  const envTokenAvailable = Boolean(state.config?.env_token_available);

  if (!effectiveBaseUrl) {
    openTab("connection");
    markInvalid("#baseUrl");
    focusField("#baseUrl");
    showNotice("Informe a URL base do Canvas ou configure a `CANVAS_BASE_URL` no `.env`.", "error");
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
  const tabMap = {
    announcement: "announcements",
    recurrence: "recurrence",
    recurrenceEdit: "recurrence",
    message: "messages",
    engagement: "engagement",
  };
  openTab(tabMap[kind] || "organization");
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
    headers: { ...(options.headers || {}) },
  };
  if (options.body !== undefined) {
    if (options.body instanceof FormData) {
      requestOptions.body = options.body;
    } else {
      requestOptions.headers["Content-Type"] = "application/json";
      requestOptions.body = JSON.stringify(options.body);
    }
  }
  const response = await fetch(url, requestOptions);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || `Falha na requisicao (${response.status})`);
  }
  return data;
}

function presentNotice(element, message, type = "info") {
  if (!element) return;
  element.textContent = message;
  element.className = `notice notice-${type}`;
  element.classList.remove("hidden", "is-flash");
  void element.offsetWidth;
  element.classList.add("is-flash");
  if (type === "error") {
    element.scrollIntoView({ behavior: "smooth", block: "center" });
  }
}

function hideNoticeElement(element) {
  if (!element) return;
  element.className = "notice hidden";
  element.textContent = "";
}

function showNotice(message, type = "info") {
  presentNotice($("#globalNotice"), message, type);
}

function hideNotice() {
  hideNoticeElement($("#globalNotice"));
}

function showModalNotice(message, type = "info") {
  presentNotice($("#groupModalNotice"), message, type);
}

function hideModalNotice() {
  hideNoticeElement($("#groupModalNotice"));
}

function showSendReviewNotice(message, type = "info") {
  presentNotice($("#sendReviewNotice"), message, type);
}

function hideSendReviewNotice() {
  hideNoticeElement($("#sendReviewNotice"));
}

function showRecurrenceCancelNotice(message, type = "info") {
  presentNotice($("#recurrenceCancelNotice"), message, type);
}

function hideRecurrenceCancelNotice() {
  hideNoticeElement($("#recurrenceCancelNotice"));
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
  await loadAnalytics();
  renderConnectionResult(null);
  renderAll();
  if (document.querySelector(".tab-button.active")?.dataset.tab === "organization") {
    await maybeAutoLoadCourseCatalog();
  }
}

async function loadConfig() {
  const data = await apiFetch("/api/config");
  state.config = data.settings || {};
  state.groups = Array.isArray(data.groups) ? data.groups : [];
  state.registeredCourses = Array.isArray(data.registered_courses) ? data.registered_courses : [];
  state.recurrences = Array.isArray(data.announcement_recurrences) ? data.announcement_recurrences : [];
  syncCatalogWithRegisteredCourses();
  pruneSelections();
}

async function loadHistory() {
  const data = await apiFetch("/api/history");
  state.history = Array.isArray(data.items) ? data.items : [];
  if (!state.selectedReportId && state.history[0]) {
    state.selectedReportId = state.history[0].id;
  }
}

async function loadAnalytics() {
  const params = new URLSearchParams({ days: String(state.reportDays || 30) });
  state.reportAnalytics = await apiFetch(`/api/reports/analytics?${params.toString()}`);
}

async function refreshReports() {
  hideNotice();
  try {
    await loadConfig();
    await loadHistory();
    await loadAnalytics();
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
  state.recurrence.groupIds = state.recurrence.groupIds.filter((id) => validGroupIds.has(id));
  state.recurrenceEdit.groupIds = state.recurrenceEdit.groupIds.filter((id) => validGroupIds.has(id));
  state.engagement.groupIds = state.engagement.groupIds.filter((id) => validGroupIds.has(id));
  const validCourseRefs = new Set(state.registeredCourses.map((item) => item.course_ref));
  state.announcement.courseRefs = state.announcement.courseRefs.filter((ref) => validCourseRefs.has(ref));
  state.message.courseRefs = state.message.courseRefs.filter((ref) => validCourseRefs.has(ref));
  state.recurrence.courseRefs = state.recurrence.courseRefs.filter((ref) => validCourseRefs.has(ref));
  state.recurrenceEdit.courseRefs = state.recurrenceEdit.courseRefs.filter((ref) => validCourseRefs.has(ref));
  state.engagement.courseRefs = state.engagement.courseRefs.filter((ref) => validCourseRefs.has(ref));
  const selectableCatalogRefs = new Set(
    state.courseCatalog
      .filter((item) => !item.already_registered)
      .map((item) => String(item.course_ref || item.id)),
  );
  state.courseCatalogSelection = state.courseCatalogSelection.filter((ref) => selectableCatalogRefs.has(ref));
}

function renderAll() {
  renderHeaderMetrics();
  renderRegisteredCourses();
  renderGroups();
  renderModeSwitch("announcement");
  renderModeSwitch("recurrence");
  renderModeSwitch("recurrenceEdit");
  renderModeSwitch("message");
  renderModeSwitch("engagement");
  renderTargetControls("announcement");
  renderTargetControls("recurrence");
  renderTargetControls("recurrenceEdit");
  renderTargetControls("message");
  renderTargetControls("engagement");
  renderCatalogCourseSummary();
  renderAnnouncementInfoPanel();
  renderMessageInfoPanel();
  renderRecurrenceInfoPanel();
  renderRecurrenceEditInfoPanel();
  renderRecurrencePreview(state.recurrence.preview);
  renderRecurrenceEditPreview(state.recurrenceEdit.preview);
  renderRecurrences();
  renderRecurrenceAgenda();
  renderEngagementPreview(state.engagement.preview);
  renderReports();
  renderSettingsInfo(state.config || {});
  renderTemplateAssistants();
  updateAnnouncementPreview();
  updateMessagePreview();
  updateRecurrenceSamplePreview();
  updateEngagementMessagePreview();
  updateAttachmentMeta({ target: $("#announcementAttachment") });
  updateAttachmentMeta({ target: $("#messageAttachment") });
  renderEnvEditorState();
  renderConnectionResult(state.connectionSnapshot);
  syncCollapsibleCards();
  persistUiState();
}

function syncCollapsibleCards() {
  document.querySelectorAll("[data-collapsible-card]").forEach((card) => {
    const cardId = card.dataset.collapsibleCard;
    const body = card.querySelector(`[data-card-body="${cardId}"]`);
    const button = card.querySelector(`[data-card-toggle="${cardId}"]`);
    if (!body || !button) return;
    const collapsed = Boolean(state.collapsedCards[cardId]);
    card.classList.toggle("is-collapsed", collapsed);
    button.setAttribute("aria-expanded", collapsed ? "false" : "true");
    button.textContent = collapsed ? "Expandir" : "Recolher";
    body.style.maxHeight = collapsed ? "0px" : `${body.scrollHeight}px`;
  });
}

function toggleCardCollapse(cardId) {
  state.collapsedCards[cardId] = !state.collapsedCards[cardId];
  syncCollapsibleCards();
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
    if (document.querySelector(".tab-button.active")?.dataset.tab === "organization") {
      await maybeAutoLoadCourseCatalog({ force: true });
    }
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

function renderCatalogCourseSummary() {
  const summary = $("#courseCatalogSummary");
  const picker = $("#courseCatalogPicker");
  if (!summary || !picker) return;

  const selectedCount = state.courseCatalogSelection.length;
  const availableCount = state.courseCatalog.filter((item) => !item.already_registered).length;
  const alreadyRegisteredCount = state.courseCatalog.filter((item) => item.already_registered).length;

  summary.innerHTML = `
    <div class="summary-card"><span>Catalogo carregado</span><strong>${escapeHtml(String(state.courseCatalog.length))}</strong></div>
    <div class="summary-card"><span>Disponiveis</span><strong>${escapeHtml(String(availableCount))}</strong></div>
    <div class="summary-card"><span>Ja cadastrados</span><strong>${escapeHtml(String(alreadyRegisteredCount))}</strong></div>
    <div class="summary-card"><span>Selecionados</span><strong>${escapeHtml(String(selectedCount))}</strong></div>
  `;

  if (!state.courseCatalog.length) {
    picker.innerHTML = `<div class="picker-empty">Clique em "Buscar no Canvas" para carregar os cursos que voce tem acesso.</div>`;
  }
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

async function loadCourseCatalog() {
  return loadCourseCatalogInternal({ silent: false, force: true });
}

async function loadCourseCatalogInternal(options = {}) {
  const button = $("#loadCourseCatalogBtn");
  const silent = Boolean(options.silent);
  const force = Boolean(options.force);
  if (state.courseCatalogLoading) return;
  if (!force && state.courseCatalogLoaded) return;
  state.courseCatalogLoading = true;
  if (button && !silent) {
    setBusy(button, true, "Buscando...");
  }
  if (!silent) {
    hideNotice();
    clearFieldValidation();
  }
  try {
    if (!hasUsableConnection()) return;
    const response = await apiFetch("/api/courses/catalog", {
      method: "POST",
      body: {
        ...getConnectionPayload(),
        search_term: $("#courseCatalogSearchInput").value.trim(),
      },
    });
    state.courseCatalog = Array.isArray(response.items) ? response.items : [];
    state.courseCatalogLoaded = true;
    syncCatalogWithRegisteredCourses();
    renderAll();
    if (!silent) {
      showNotice(`${response.total_found || state.courseCatalog.length} curso(s) carregado(s) do Canvas.`, "success");
    }
  } catch (error) {
    if (!silent) {
      showNotice(error.message, "error");
    }
  } finally {
    state.courseCatalogLoading = false;
    if (button && !silent) {
      setBusy(button, false);
    }
  }
}

function hasUsableConnection() {
  const baseUrl = normalizeBaseUrlInput($("#baseUrl").value);
  const effectiveBaseUrl = baseUrl || normalizeBaseUrlInput(state.config?.default_base_url || "");
  const accessToken = $("#apiToken").value.trim();
  const envTokenAvailable = Boolean(state.config?.env_token_available);
  return Boolean(effectiveBaseUrl && (accessToken || envTokenAvailable));
}

async function maybeAutoLoadCourseCatalog(options = {}) {
  const force = Boolean(options.force);
  if (state.courseCatalogLoading) return;
  if (!force && state.courseCatalogLoaded) return;
  if (!hasUsableConnection()) return;
  await loadCourseCatalogInternal({ silent: true, force: true });
}

async function registerSelectedCatalogCourses() {
  const button = $("#registerCatalogSelectionBtn");
  setBusy(button, true, "Cadastrando...");
  hideNotice();
  clearFieldValidation();
  try {
    if (!ensureConnectionConfigured()) return;
    if (!state.courseCatalogSelection.length) {
      showNotice("Selecione pelo menos um curso do catalogo para cadastrar.", "error");
      return;
    }
    const response = await apiFetch("/api/registered-courses/bulk", {
      method: "POST",
      body: {
        ...getConnectionPayload(),
        course_refs: state.courseCatalogSelection,
      },
    });
    await loadConfig();
    renderAll();
    showNotice(
      `${response.created_count || 0} curso(s) novo(s) cadastrado(s) e ${response.updated_count || 0} atualizado(s).`,
      "success",
    );
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

function syncCatalogWithRegisteredCourses() {
  if (!state.courseCatalog.length) return;
  const registeredRefs = new Set(state.registeredCourses.map((item) => item.course_ref));
  state.courseCatalog = state.courseCatalog.map((item) => ({
    ...item,
    course_ref: String(item.course_ref || item.id || ""),
    already_registered: registeredRefs.has(String(item.course_ref || item.id || "")),
  }));
  state.courseCatalogSelection = state.courseCatalogSelection.filter((ref) => !registeredRefs.has(ref));
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
        ${(group.courses || []).map((course) => `<span class="chip">${escapeHtml(course.course_name || course.course_ref)}</span>`).join("")}
      </div>
    </div>
  `).join("");
}

function renderRecurrencePreview(preview, options = {}) {
  const summary = $(options.summarySelector || "#recurrencePreviewSummary");
  const schedule = $(options.scheduleSelector || "#recurrenceSchedulePreview");
  const emptyText = options.emptyText || "Selecione as turmas e clique em prever datas.";
  if (!summary || !schedule) return;
  if (!preview) {
    summary.innerHTML = "";
    schedule.innerHTML = `<div class="empty-state">${escapeHtml(emptyText)}</div>`;
    return;
  }
  summary.innerHTML = `
    <div class="summary-card"><span>Turmas</span><strong>${escapeHtml(String(preview.summary?.courses || 0))}</strong></div>
    <div class="summary-card"><span>Ocorrencias por turma</span><strong>${escapeHtml(String(preview.summary?.occurrences_per_course || 0))}</strong></div>
    <div class="summary-card"><span>Total de avisos</span><strong>${escapeHtml(String(preview.summary?.total_announcements || 0))}</strong></div>
    <div class="summary-card"><span>Ultima publicacao</span><strong>${escapeHtml(formatDate(preview.summary?.last_publish_at || ""))}</strong></div>
    ${preview.edit_diff ? `
      <div class="summary-card"><span>Turmas novas</span><strong>${escapeHtml(String(preview.edit_diff.added_courses || 0))}</strong></div>
      <div class="summary-card"><span>Turmas removidas</span><strong>${escapeHtml(String(preview.edit_diff.removed_courses || 0))}</strong></div>
      <div class="summary-card"><span>Turmas atualizadas</span><strong>${escapeHtml(String(preview.edit_diff.updated_courses || 0))}</strong></div>
      <div class="summary-card"><span>Sem mudanca</span><strong>${escapeHtml(String(preview.edit_diff.unchanged_courses || 0))}</strong></div>
      <div class="summary-card"><span>Avisos que saem</span><strong>${escapeHtml(String(preview.edit_diff.delete_items_expected || 0))}</strong></div>
      <div class="summary-card"><span>Avisos que entram</span><strong>${escapeHtml(String(preview.edit_diff.create_items_expected || 0))}</strong></div>
    ` : ""}
  `;
  const editDiffBlock = preview.edit_diff ? `
    <div class="history-item">
      <div class="history-item-header">
        <div>
          <strong>Impacto por turma</strong>
          <div class="compact-meta">Confira o que sera mantido, removido ou recriado ao salvar.</div>
        </div>
      </div>
      <div class="chips">
        ${(preview.edit_diff.course_changes || []).map((item) => {
          const labelMap = { add: "entra", remove: "sai", update: "atualiza", keep: "mantem" };
          return `<span class="chip">${escapeHtml(item.course_name || item.course_ref)} | ${escapeHtml(labelMap[item.action] || item.action)}${item.future_items ? ` | ${escapeHtml(String(item.future_items))} futuro(s)` : ""}${item.new_occurrences ? ` | +${escapeHtml(String(item.new_occurrences))}` : ""}</span>`;
        }).join("")}
      </div>
    </div>
  ` : "";
  schedule.innerHTML = editDiffBlock + (preview.schedule || []).map((item) => `
    <div class="history-item">
      <div class="history-item-header">
        <div>
          <strong>Ocorrencia ${escapeHtml(String(item.occurrence_index || "-"))}</strong>
          <div class="compact-meta">${escapeHtml(formatDate(item.publish_at))}</div>
        </div>
        <div class="history-actions"><span class="chip">${escapeHtml(preview.summary?.recurrence_type || "-")}</span></div>
      </div>
    </div>
  `).join("");
}

function renderRecurrences() {
  const container = $("#recurrenceList");
  const summary = $("#recurrenceListSummary");
  if (!container) return;
  const items = filterRecurrenceListItems(state.recurrences);
  const activeCount = items.filter((item) => item.is_active).length;
  const futureCount = items.reduce((total, item) => total + Number(item.future_items || 0), 0);
  const errorCount = items.filter((item) => Number(item.error_items || 0) > 0 || item.last_error).length;
  if (summary) {
    summary.innerHTML = `
      <div class="summary-card"><span>Visiveis</span><strong>${escapeHtml(String(items.length))}</strong></div>
      <div class="summary-card"><span>Ativas</span><strong>${escapeHtml(String(activeCount))}</strong></div>
      <div class="summary-card"><span>Publicacoes futuras</span><strong>${escapeHtml(String(futureCount))}</strong></div>
      <div class="summary-card"><span>Com erro</span><strong>${escapeHtml(String(errorCount))}</strong></div>
    `;
  }
  if (!state.recurrences.length) {
    container.innerHTML = `<div class="empty-state">Nenhuma recorrencia criada.</div>`;
    return;
  }
  if (!items.length) {
    container.innerHTML = `<div class="empty-state">Nenhuma recorrencia corresponde aos filtros atuais.</div>`;
    return;
  }
  container.innerHTML = items.map((item) => `
    <div class="group-card">
      <div class="group-card-header">
        <div>
          <strong>${escapeHtml(item.name || item.title || "Recorrencia")}</strong>
          <div class="compact-meta">${escapeHtml(item.title || "-")} | ${escapeHtml(item.recurrence_type || "-")} a cada ${escapeHtml(String(item.interval_value || 1))}</div>
        </div>
        <div class="group-card-actions">
          <button class="mini-btn" type="button" data-recurrence-action="edit" data-recurrence-id="${escapeHtml(item.id)}">Editar</button>
          <button class="mini-btn" type="button" data-recurrence-action="reuse" data-recurrence-id="${escapeHtml(item.id)}">Duplicar base</button>
          <button class="mini-btn danger" type="button" data-recurrence-action="cancel" data-recurrence-id="${escapeHtml(item.id)}">${item.is_active ? "Cancelar futuros" : "Tentar cancelar"}</button>
        </div>
      </div>
      <div class="summary-grid">
        <div class="summary-card"><span>Total</span><strong>${escapeHtml(String(item.total_items || 0))}</strong></div>
        <div class="summary-card"><span>Futuros</span><strong>${escapeHtml(String(item.future_items || 0))}</strong></div>
        <div class="summary-card"><span>Cancelados</span><strong>${escapeHtml(String(item.canceled_items || 0))}</strong></div>
        <div class="summary-card"><span>Proximo</span><strong>${escapeHtml(formatDate(item.next_publish_at || ""))}</strong></div>
      </div>
      <div class="recurrence-timeline">
        ${timelinePill("Criada", item.created_at)}
        ${timelinePill("Atualizada", item.updated_at)}
        ${item.canceled_at ? timelinePill("Cancelada", item.canceled_at, "warn") : ""}
        ${item.last_error ? `<span class="timeline-pill danger">Erro recente</span>` : ""}
        <span class="timeline-pill">${escapeHtml(recurrenceStatusLabel(item))}</span>
      </div>
      ${item.cancel_reason ? `<div class="compact-meta">Cancelamento: ${escapeHtml(item.cancel_reason)}</div>` : ""}
      ${item.last_error ? `<div class="compact-meta text-danger">${escapeHtml(item.last_error)}</div>` : ""}
      <div class="chips">
        ${(item.items || []).slice(0, 6).map((row) => `<span class="chip">${escapeHtml(row.course_name || row.course_ref)} | ${escapeHtml(formatDate(row.scheduled_for || ""))} | ${escapeHtml(row.status || "-")}</span>`).join("")}
      </div>
    </div>
  `).join("");
}

function filterRecurrenceListItems(items) {
  const search = String(state.recurrence.listSearch || "").trim().toLowerCase();
  const status = state.recurrence.listStatus || "all";
  return items.filter((item) => {
    const haystack = [
      item.name,
      item.title,
      item.recurrence_type,
      item.cancel_reason,
      item.last_error,
      ...(item.items || []).flatMap((entry) => [entry.course_name, entry.course_ref, entry.status]),
    ].join(" ").toLowerCase();
    if (search && !haystack.includes(search)) return false;
    if (status === "active" && !item.is_active) return false;
    if (status === "inactive" && item.is_active) return false;
    if (status === "error" && !(Number(item.error_items || 0) > 0 || item.last_error)) return false;
    if (status === "upcoming" && !(Number(item.future_items || 0) > 0)) return false;
    if (status === "canceled" && !(Number(item.canceled_items || 0) > 0 || item.canceled_at)) return false;
    return true;
  });
}

function renderRecurrenceAgenda() {
  const summary = $("#recurrenceAgendaSummary");
  const list = $("#recurrenceAgendaList");
  if (!summary || !list) return;
  const items = buildRecurrenceAgendaItems();
  const uniqueRecurrences = unique(items.map((item) => item.recurrence_id));
  const uniqueCourses = unique(items.map((item) => item.course_ref));
  const nextItem = items[0] || null;
  const todayCount = items.filter((item) => item.day_bucket === "today").length;
  const nextSevenDaysCount = items.filter((item) => item.day_offset >= 0 && item.day_offset <= 6).length;
  const recentChangeCount = unique(items.filter((item) => item.change_label).map((item) => item.recurrence_id)).length;
  summary.innerHTML = `
    <div class="summary-card"><span>Publicacoes</span><strong>${escapeHtml(String(items.length))}</strong></div>
    <div class="summary-card"><span>Recorrencias</span><strong>${escapeHtml(String(uniqueRecurrences.length))}</strong></div>
    <div class="summary-card"><span>Turmas</span><strong>${escapeHtml(String(uniqueCourses.length))}</strong></div>
    <div class="summary-card"><span>Hoje</span><strong>${escapeHtml(String(todayCount))}</strong></div>
    <div class="summary-card"><span>Proximos 7 dias</span><strong>${escapeHtml(String(nextSevenDaysCount))}</strong></div>
    <div class="summary-card"><span>Ajustadas recente</span><strong>${escapeHtml(String(recentChangeCount))}</strong></div>
    <div class="summary-card"><span>Proxima</span><strong>${escapeHtml(nextItem ? formatDateTime(nextItem.scheduled_for) : "-")}</strong></div>
  `;
  if (!items.length) {
    list.classList.add("empty-state");
    list.innerHTML = "Nenhuma publicacao futura encontrada com os filtros atuais.";
    return;
  }
  list.classList.remove("empty-state");
  const groups = groupRecurrenceAgendaByDay(items);
  list.innerHTML = groups.map((group) => `
    <div class="history-item">
      <div class="history-item-header">
        <div>
          <strong>${escapeHtml(group.label)}</strong>
          <div class="compact-meta">${escapeHtml(String(group.items.length))} publicacao(oes)</div>
        </div>
      </div>
      <div class="dashboard-list">
        ${group.items.map((item) => `
          <div class="dashboard-item agenda-item ${item.day_bucket === "today" ? "agenda-item-today" : ""}">
            <div class="compact-header">
              <div>
                <strong>${escapeHtml(item.recurrence_name || item.title || "Recorrencia")}</strong>
                <div class="compact-meta">${escapeHtml(item.title || "-")}</div>
              </div>
              <div class="history-actions">
                <span class="chip">${escapeHtml(item.time_label)}</span>
                <span class="timeline-pill">${escapeHtml(item.relative_label)}</span>
                ${statusChip(item.status || "scheduled")}
              </div>
            </div>
            <div class="compact-meta">${escapeHtml(item.course_name || item.course_ref || "-")} | ${escapeHtml(item.course_ref || "-")}</div>
            <div class="recurrence-timeline">
              ${item.change_label ? `<span class="timeline-pill info">${escapeHtml(item.change_label)}</span>` : ""}
              ${item.created_at ? timelinePill("Criada", item.created_at) : ""}
              ${item.updated_at && item.updated_at !== item.created_at ? timelinePill("Atualizada", item.updated_at) : ""}
            </div>
          </div>
        `).join("")}
      </div>
    </div>
  `).join("");
}

function buildRecurrenceAgendaItems() {
  const search = state.recurrence.agendaSearch || "";
  const windowDays = Number(state.recurrence.agendaWindowDays || 30);
  const now = new Date();
  const limit = new Date(now.getTime() + windowDays * 24 * 60 * 60 * 1000);
  return state.recurrences.flatMap((recurrence) => {
    return (recurrence.items || []).map((item) => ({
      recurrence_id: recurrence.id,
      recurrence_name: recurrence.name || recurrence.title || "",
      title: recurrence.title || "",
      course_name: item.course_name || "",
      course_ref: item.course_ref || "",
      scheduled_for: item.scheduled_for,
      status: item.status || "scheduled",
      created_at: recurrence.created_at || "",
      updated_at: recurrence.updated_at || "",
      change_label: recurrenceChangeLabel(recurrence),
      search: `${recurrence.name || ""} ${recurrence.title || ""} ${item.course_name || ""} ${item.course_ref || ""}`.toLowerCase(),
    }));
  }).filter((item) => {
    const scheduled = new Date(item.scheduled_for);
    if (Number.isNaN(scheduled.getTime())) return false;
    if (scheduled < now || scheduled > limit) return false;
    if (!["scheduled", "created"].includes(String(item.status || "").toLowerCase())) return false;
    if (search && !item.search.includes(search)) return false;
    return true;
  }).sort((left, right) => new Date(left.scheduled_for).getTime() - new Date(right.scheduled_for).getTime()).map((item) => ({
    ...item,
    time_label: formatAgendaTime(item.scheduled_for),
    relative_label: formatRelativeAgendaDay(item.scheduled_for),
    day_offset: dayOffsetFromNow(item.scheduled_for),
    day_bucket: classifyAgendaDay(item.scheduled_for),
  }));
}

function groupRecurrenceAgendaByDay(items) {
  const formatter = new Intl.DateTimeFormat("pt-BR", {
    weekday: "short",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
  const groups = [];
  const map = new Map();
  items.forEach((item) => {
    const date = new Date(item.scheduled_for);
    const key = `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}`;
    if (!map.has(key)) {
      const dayOffset = dayOffsetFromNow(item.scheduled_for);
      const entry = { key, label: formatAgendaGroupLabel(date, formatter, dayOffset), items: [] };
      map.set(key, entry);
      groups.push(entry);
    }
    map.get(key).items.push(item);
  });
  return groups;
}

function formatAgendaTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "--:--";
  return date.toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function applyRecurrenceToForm(item) {
  openTab("recurrence");
  $("#recurrenceName").value = item.name || "";
  $("#recurrenceTitle").value = item.title || "";
  $("#recurrenceMessage").value = item.message_html || "";
  $("#recurrenceType").value = item.recurrence_type || "weekly";
  $("#recurrenceInterval").value = String(item.interval_value || 1);
  $("#recurrenceOccurrences").value = String(item.occurrence_count || 1);
  $("#recurrenceLockComment").checked = Boolean(item.lock_comment);
  $("#recurrenceFirstPublishAt").value = formatLocalDateTimeInput(item.first_publish_at);
  state.recurrence.mode = item.target_mode === "courses" ? "courses" : "groups";
  state.recurrence.groupIds = [...((item.target_config_json || {}).group_ids || [])];
  state.recurrence.courseRefs = [...((item.target_config_json || {}).course_refs || [])];
  state.recurrence.selectAllGroups = Boolean((item.target_config_json || {}).select_all_groups);
  state.recurrence.preview = null;
  renderTargetControls("recurrence");
  renderRecurrencePreview(null);
  persistUiState();
  showNotice(`Recorrencia "${item.name || item.title}" carregada como base no formulario.`, "success");
}

function openRecurrenceEditModal(item) {
  state.recurrenceEdit.id = item.id;
  state.recurrenceEdit.mode = item.target_mode === "courses" ? "courses" : "groups";
  state.recurrenceEdit.groupIds = [...((item.target_config_json || {}).group_ids || [])];
  state.recurrenceEdit.courseRefs = [...((item.target_config_json || {}).course_refs || [])];
  state.recurrenceEdit.selectAllGroups = Boolean((item.target_config_json || {}).select_all_groups);
  state.recurrenceEdit.preview = null;
  state.recurrenceEdit.previewSignature = "";
  $("#recurrenceEditModalTitle").textContent = `Editar recorrencia: ${item.name || item.title || "Recorrencia"}`;
  $("#recurrenceEditName").value = item.name || "";
  $("#recurrenceEditTitle").value = item.title || "";
  $("#recurrenceEditMessage").value = item.message_html || "";
  $("#recurrenceEditType").value = item.recurrence_type || "weekly";
  $("#recurrenceEditInterval").value = String(item.interval_value || 1);
  $("#recurrenceEditFirstPublishAt").value = formatLocalDateTimeInput(item.first_publish_at);
  $("#recurrenceEditOccurrences").value = String(item.occurrence_count || 1);
  $("#recurrenceEditLockComment").checked = Boolean(item.lock_comment);
  hideRecurrenceEditNotice();
  renderModeSwitch("recurrenceEdit");
  renderTargetControls("recurrenceEdit");
  updateRecurrenceEditSamplePreview();
  renderRecurrenceEditPreview(null);
  $("#recurrenceEditModal").classList.remove("hidden");
  $("#recurrenceEditModal").setAttribute("aria-hidden", "false");
  focusField("#recurrenceEditName");
}

function closeRecurrenceEditModal() {
  state.recurrenceEdit = {
    id: null,
    mode: "groups",
    groupIds: [],
    courseRefs: [],
    selectAllGroups: false,
    preview: null,
    previewSignature: "",
  };
  hideRecurrenceEditNotice();
  $("#recurrenceEditModal").classList.add("hidden");
  $("#recurrenceEditModal").setAttribute("aria-hidden", "true");
  $("#recurrenceEditModalTitle").textContent = "Editar recorrencia";
  $("#recurrenceEditName").value = "";
  $("#recurrenceEditTitle").value = "";
  $("#recurrenceEditMessage").value = "";
  $("#recurrenceEditType").value = "weekly";
  $("#recurrenceEditInterval").value = "1";
  $("#recurrenceEditFirstPublishAt").value = "";
  $("#recurrenceEditOccurrences").value = "8";
  $("#recurrenceEditLockComment").checked = false;
  updateRecurrenceEditSamplePreview();
  renderRecurrenceEditPreview(null);
}

function showRecurrenceEditNotice(message, type = "info") {
  presentNotice($("#recurrenceEditNotice"), message, type);
}

function hideRecurrenceEditNotice() {
  hideNoticeElement($("#recurrenceEditNotice"));
}

function openRecurrenceReviewModal(mode, payload, preview) {
  state.recurrenceReview = { mode, payload, preview };
  const editing = mode === "edit";
  $("#recurrenceReviewTitle").textContent = editing ? "Revisar atualizacao da recorrencia" : "Revisar nova recorrencia";
  $("#recurrenceReviewSubtitle").textContent = editing
    ? "Confira o impacto nas turmas antes de substituir os avisos futuros no Canvas."
    : "Confira o impacto antes de criar os avisos recorrentes no Canvas.";
  $("#confirmRecurrenceReviewBtn").textContent = editing ? "Salvar recorrencia" : "Criar recorrencia";
  $("#recurrenceReviewSummary").innerHTML = renderRecurrenceReviewSummary(preview, editing);
  $("#recurrenceReviewTargets").innerHTML = renderRecurrenceReviewTargets(payload);
  $("#recurrenceReviewSchedule").innerHTML = renderRecurrenceReviewSchedule(preview);
  hideRecurrenceReviewNotice();
  $("#recurrenceReviewModal").classList.remove("hidden");
  $("#recurrenceReviewModal").setAttribute("aria-hidden", "false");
}

function closeRecurrenceReviewModal() {
  state.recurrenceReview = { mode: null, payload: null, preview: null };
  hideRecurrenceReviewNotice();
  $("#recurrenceReviewModal").classList.add("hidden");
  $("#recurrenceReviewModal").setAttribute("aria-hidden", "true");
  $("#recurrenceReviewSummary").innerHTML = "";
  $("#recurrenceReviewTargets").innerHTML = "Nenhuma turma carregada.";
  $("#recurrenceReviewSchedule").innerHTML = "Nenhuma previsao carregada.";
}

function showRecurrenceReviewNotice(message, type = "info") {
  presentNotice($("#recurrenceReviewNotice"), message, type);
}

function hideRecurrenceReviewNotice() {
  hideNoticeElement($("#recurrenceReviewNotice"));
}

function renderRecurrenceReviewSummary(preview, editing) {
  const summary = preview?.summary || {};
  const cards = [
    metricCard("Turmas", summary.courses || 0),
    metricCard("Ocorrencias por turma", summary.occurrences_per_course || 0),
    metricCard("Total de avisos", summary.total_announcements || 0),
    metricCard("Ultima publicacao", formatDate(summary.last_publish_at || "") || "-"),
  ];
  if (editing && preview?.edit_diff) {
    cards.push(
      metricCard("Turmas novas", preview.edit_diff.added_courses || 0),
      metricCard("Turmas removidas", preview.edit_diff.removed_courses || 0),
      metricCard("Turmas atualizadas", preview.edit_diff.updated_courses || 0),
      metricCard("Avisos que saem", preview.edit_diff.delete_items_expected || 0),
      metricCard("Avisos que entram", preview.edit_diff.create_items_expected || 0),
    );
  }
  return cards.join("");
}

function renderRecurrenceReviewTargets(payload) {
  const groups = resolveRecurrenceReviewGroups(payload);
  const courses = resolveRecurrenceReviewCourses(payload);
  const modeLabel = payload?.target_mode === "courses" ? "Cursos especificos" : "Grupos salvos";
  return `
    <div class="summary-grid">
      <div class="summary-card"><span>Modo</span><strong>${escapeHtml(modeLabel)}</strong></div>
      <div class="summary-card"><span>Grupos</span><strong>${escapeHtml(payload?.target_mode === "groups" ? String(groups.length || 0) : "-")}</strong></div>
      <div class="summary-card"><span>Turmas</span><strong>${escapeHtml(String(courses.length || 0))}</strong></div>
    </div>
    ${groups.length ? `<div class="chips">${groups.map((group) => `<span class="chip">${escapeHtml(group.name)}</span>`).join("")}</div>` : ""}
    ${courses.length ? `<div class="chips">${courses.map((course) => `<span class="chip">${escapeHtml(course.course_name || course.course_ref)}</span>`).join("")}</div>` : `<div class="empty-state">Nenhuma turma carregada.</div>`}
  `;
}

function renderRecurrenceReviewSchedule(preview) {
  if (!preview) return "Nenhuma previsao carregada.";
  const blocks = [];
  if (preview.edit_diff?.course_changes?.length) {
    blocks.push(`
      <div class="history-item">
        <div class="history-item-header">
          <div>
            <strong>Impacto por turma</strong>
            <div class="compact-meta">Entradas, saidas e atualizacoes que serao aplicadas.</div>
          </div>
        </div>
        <div class="chips">
          ${(preview.edit_diff.course_changes || []).map((item) => {
            const labelMap = { add: "entra", remove: "sai", update: "atualiza", keep: "mantem" };
            return `<span class="chip">${escapeHtml(item.course_name || item.course_ref)} | ${escapeHtml(labelMap[item.action] || item.action)}</span>`;
          }).join("")}
        </div>
      </div>
    `);
  }
  blocks.push(
    ...(preview.schedule || []).slice(0, 12).map((item) => `
      <div class="history-item">
        <div class="history-item-header">
          <div>
            <strong>Ocorrencia ${escapeHtml(String(item.occurrence_index || "-"))}</strong>
            <div class="compact-meta">${escapeHtml(formatDateTime(item.publish_at || ""))}</div>
          </div>
          <div class="history-actions"><span class="chip">${escapeHtml(preview.summary?.recurrence_type || "-")}</span></div>
        </div>
      </div>
    `),
  );
  return blocks.join("");
}

function resolveRecurrenceReviewGroups(payload) {
  if (!payload || payload.target_mode === "courses") return [];
  if (payload.select_all_groups) return [...state.groups];
  const selectedIds = new Set(payload.group_ids || []);
  return state.groups.filter((group) => selectedIds.has(group.id));
}

function resolveRecurrenceReviewCourses(payload) {
  if (!payload) return [];
  if (payload.target_mode === "courses") {
    const refs = new Set(payload.course_refs || []);
    return state.registeredCourses.filter((course) => refs.has(course.course_ref));
  }
  const groups = resolveRecurrenceReviewGroups(payload);
  const seen = new Set();
  return groups.flatMap((group) => group.courses || []).filter((course) => {
    if (seen.has(course.course_ref)) return false;
    seen.add(course.course_ref);
    return true;
  });
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
  state.groupModalCourseRefs = [...(group?.course_refs || [])];
  $("#groupModalTitle").textContent = group ? `Editar grupo: ${group.name}` : "Novo grupo";
  $("#groupName").value = group?.name || "";
  $("#groupDescription").value = group?.description || "";
  renderPicker("groupCoursePicker", coursePickerItems(), state.groupModalCourseRefs);
  hideModalNotice();
  $("#groupModal").classList.remove("hidden");
  $("#groupModal").setAttribute("aria-hidden", "false");
}

function closeGroupModal() {
  state.activeGroupId = null;
  state.groupModalCourseRefs = [];
  hideModalNotice();
  $("#groupModal").classList.add("hidden");
  $("#groupModal").setAttribute("aria-hidden", "true");
  $("#groupName").value = "";
  $("#groupDescription").value = "";
}

function openSendReviewModal(kind, data) {
  state.review = { kind, data };
  $("#sendReviewTitle").textContent = reviewTitle(kind);
  $("#sendReviewSubtitle").textContent = reviewSubtitle(kind);
  $("#sendReviewTargetSubtitle").textContent = reviewTargetSubtitle(kind);
  $("#sendReviewMessageSubtitle").textContent = reviewMessageSubtitle(kind);
  $("#confirmSendReviewBtn").textContent = reviewConfirmLabel(kind);
  $("#sendReviewSummary").innerHTML = renderReviewSummary(kind, data);
  $("#sendReviewTargets").innerHTML = renderReviewTargets(kind, data);
  $("#sendReviewMessage").innerHTML = renderReviewMessage(kind, data);
  hideSendReviewNotice();
  $("#sendReviewModal").classList.remove("hidden");
  $("#sendReviewModal").setAttribute("aria-hidden", "false");
}

function closeSendReviewModal() {
  state.review = { kind: null, data: null };
  hideSendReviewNotice();
  $("#sendReviewModal").classList.add("hidden");
  $("#sendReviewModal").setAttribute("aria-hidden", "true");
  $("#sendReviewSummary").innerHTML = "";
  $("#sendReviewTargets").innerHTML = "Nenhum alvo carregado.";
  $("#sendReviewMessage").innerHTML = "Nenhum conteudo carregado.";
}

function openRecurrenceCancelModal(item) {
  state.recurrenceCancel = { id: item.id, item };
  $("#recurrenceCancelReason").value = item.cancel_reason || "Mudanca de agenda";
  $("#recurrenceCancelConfirm").value = "";
  $("#recurrenceCancelSummary").innerHTML = [
    metricCard("Recorrencia", item.name || item.title || "-"),
    metricCard("Futuros", item.future_items || 0),
    metricCard("Cancelados", item.canceled_items || 0),
    metricCard("Proximo", formatDate(item.next_publish_at || "") || "-"),
  ].join("");
  hideRecurrenceCancelNotice();
  $("#recurrenceCancelModal").classList.remove("hidden");
  $("#recurrenceCancelModal").setAttribute("aria-hidden", "false");
}

function closeRecurrenceCancelModal() {
  state.recurrenceCancel = { id: null, item: null };
  hideRecurrenceCancelNotice();
  $("#recurrenceCancelModal").classList.add("hidden");
  $("#recurrenceCancelModal").setAttribute("aria-hidden", "true");
  $("#recurrenceCancelSummary").innerHTML = "";
  $("#recurrenceCancelReason").value = "";
  $("#recurrenceCancelConfirm").value = "";
}

function reviewTitle(kind) {
  if (kind === "announcement") return "Revisar comunicado";
  if (kind === "message") return "Revisar caixa de entrada";
  return "Revisar mensagem para inativos";
}

function reviewSubtitle(kind) {
  if (kind === "announcement") return "Confira turmas, agendamento e conteudo antes de criar o lote.";
  if (kind === "message") return "Confira turmas, destinatarios e estrategia antes de disparar.";
  return "Confira o filtro de inatividade e os alunos alvo antes de enviar.";
}

function reviewTargetSubtitle(kind) {
  if (kind === "announcement") return "Turmas que receberao o comunicado.";
  if (kind === "message") return "Turmas e alunos que entrarao no lote.";
  return "Turmas e alunos inativos encontrados.";
}

function reviewMessageSubtitle(kind) {
  if (kind === "announcement") return "HTML, modo de publicacao e anexo.";
  if (kind === "message") return "Assunto, corpo e anexo opcional.";
  return "Assunto, corpo e criterio aplicado.";
}

function reviewConfirmLabel(kind) {
  if (kind === "announcement") return "Confirmar comunicado";
  if (kind === "message") return "Confirmar envio";
  return "Confirmar envio para inativos";
}

function messageReviewStrategyLabel(request = {}) {
  if (messageUsesStudentName(request)) return "Usuarios individualmente";
  return request.strategy === "context" ? "Contexto" : "Usuarios";
}

function messageUsesStudentName(request = {}) {
  return [request.subject, request.message].some((value) => /{{\s*student_name\s*}}/i.test(String(value || "")));
}

function renderReviewSummary(kind, data) {
  const summary = data?.summary || {};
  const request = data?.request || {};
  let cards = [];
  if (kind === "announcement") {
    cards = [
      metricCard("Turmas", summary.courses_requested || 0),
      metricCard("Resolvidas", summary.success_count || 0),
      metricCard("Falhas", summary.failure_count || 0),
      metricCard("Publicacao", formatPublishMode(summary.publish_mode || request.publish_mode || "publish_now")),
      metricCard("Anexo", summary.attachment_name || request.attachment_name || "Sem anexo"),
      metricCard("Modo teste", (summary.dry_run || request.dry_run) ? "Sim" : "Nao"),
    ];
  } else if (kind === "message") {
    cards = [
      metricCard("Turmas", (data.courses || []).length),
      metricCard("Alunos encontrados", summary.total_students_found || 0),
      metricCard("Destinatarios unicos", summary.unique_recipients || 0),
      metricCard("Estrategia", messageReviewStrategyLabel(request)),
      metricCard("Deduplicar", request.dedupe ? "Sim" : "Nao"),
      metricCard("Anexo", request.attachment_name || "Sem anexo"),
    ];
  } else {
    cards = [
      metricCard("Turmas", (data.courses || []).length),
      metricCard("Alunos analisados", summary.total_students_found || 0),
      metricCard("Alvos", summary.total_matched_students || 0),
      metricCard("Sem acesso", summary.total_never_accessed_matches || 0),
      metricCard("Pendencias", summary.total_incomplete_resources_matches || 0),
      metricCard("Criterio", formatCriteriaMode(request.criteria_mode || "")),
    ];
  }
  return cards.join("");
}

function renderReviewTargets(kind, data) {
  if (kind === "announcement") {
    const courses = data.courses || [];
    if (!courses.length) return `<div class="empty-state">Nenhuma turma encontrada.</div>`;
    return courses.map((course) => `
      <div class="history-item">
        <div class="history-item-header">
          <div>
            <strong>${escapeHtml(course.course_name || course.course_ref || "-")}</strong>
          </div>
          <div class="history-actions">${statusChip(course.status === "ok" ? "success" : "error")}</div>
        </div>
        ${course.error ? `<div class="compact-meta text-danger">${escapeHtml(course.error)}</div>` : ""}
      </div>
    `).join("");
  }

  if (kind === "message") {
    const courses = data.courses || [];
    if (!courses.length) return `<div class="empty-state">Nenhuma turma encontrada.</div>`;
    return courses.map((course) => `
      <div class="history-item">
        <div class="history-item-header">
          <div>
            <strong>${escapeHtml(course.course_name || course.course_ref || "-")}</strong>
          </div>
          <div class="history-actions"><span class="chip">${escapeHtml(String(course.students_found || 0))} aluno(s)</span></div>
        </div>
      </div>
    `).join("") + renderReviewRecipientsSample(data.items || []);
  }

  const courses = data.courses || [];
  if (!courses.length) return `<div class="empty-state">Nenhuma turma encontrada.</div>`;
  return courses.map((course) => `
    <div class="history-item">
      <div class="history-item-header">
        <div>
          <strong>${escapeHtml(course.course_name || course.course_ref || "-")}</strong>
        </div>
        <div class="history-actions"><span class="chip">${escapeHtml(String(course.matched_students || 0))} alvo(s)</span></div>
      </div>
      <div class="review-target-meta">
        <span>Sem acesso: ${escapeHtml(String(course.never_accessed_matches || 0))}</span>
        <span>Pendentes: ${escapeHtml(String(course.incomplete_resources_matches || 0))}</span>
        <span>Sem atividade: ${escapeHtml(String(course.inactive_days_matches || 0))}</span>
      </div>
    </div>
  `).join("") + renderReviewRecipientsSample(data.items || []);
}

function renderReviewRecipientsSample(items) {
  if (!items.length) return "";
  const sample = items.slice(0, 12);
  return `
    <div class="history-item">
      <div class="history-item-header">
        <div>
          <strong>Amostra de destinatarios</strong>
          <div class="compact-meta">${escapeHtml(String(sample.length))} exibido(s)</div>
        </div>
      </div>
      <div class="chips">${sample.map((item) => `<span class="chip">${escapeHtml(item.student_name || item.name || `Usuario ${item.user_id || "-"}`)}</span>`).join("")}</div>
    </div>
  `;
}

function renderRecurrenceEditPreview(preview) {
  renderTargetSummary("recurrenceEdit");
  renderRecurrencePreview(preview, {
    summarySelector: "#recurrenceEditPreviewSummary",
    scheduleSelector: "#recurrenceEditSchedulePreview",
    emptyText: "Clique em prever impacto para ver o que muda nas publicacoes futuras.",
  });
}

function invalidateRecurrencePreview(kind) {
  if (!state[kind]) return;
  state[kind].preview = null;
  state[kind].previewSignature = "";
  if (kind === "recurrence") {
    renderRecurrencePreview(null);
    renderTargetSummary("recurrence");
    renderRecurrenceInfoPanel();
    return;
  }
  if (kind === "recurrenceEdit") {
    renderRecurrenceEditPreview(null);
    renderRecurrenceEditInfoPanel();
  }
}

function renderRecurrencePreviewState() {
  const target = $("#recurrencePreviewState");
  if (!target) return;
  const payload = buildRecurrenceRequestBody();
  const hasSelection = Boolean(getTargetPayload("recurrence").course_refs?.length || getTargetPayload("recurrence").group_ids?.length || getTargetPayload("recurrence").select_all_groups);
  if (!hasSelection) {
    target.textContent = "Selecione as turmas para liberar a previsao da recorrencia.";
    return;
  }
  target.textContent = recurrencePreviewIsCurrent("recurrence", payload)
    ? "Preview atualizado e pronto para a revisao final."
    : "Altere turmas, datas ou conteudo? Gere um preview novo antes de revisar e criar.";
}

function renderRecurrenceEditPreviewState() {
  const target = $("#recurrenceEditPreviewState");
  if (!target) return;
  if (!state.recurrenceEdit.id) {
    target.textContent = "Abra uma recorrencia para editar e gerar o preview do impacto.";
    return;
  }
  const payload = buildRecurrenceEditRequestBody();
  target.textContent = recurrencePreviewIsCurrent("recurrenceEdit", payload)
    ? "Preview atualizado e pronto para salvar a edicao."
    : "Sempre que houver mudanca, gere um preview novo antes de salvar.";
}

function renderReviewMessage(kind, data) {
  const request = data?.request || {};
  if (kind === "announcement") {
    const sampleCourse = firstReviewCourse(data?.courses || []);
    const previewTitle = renderCourseTemplate(request.title || "-", sampleCourse);
    const previewMessage = renderCourseTemplate(request.message_html || "<p></p>", sampleCourse);
    return `
      <div class="message-block">
        <strong>${escapeHtml(previewTitle)}</strong>
        <div class="compact-meta">${escapeHtml(formatPublishMode(request.publish_mode || "publish_now"))}${request.schedule_at_local ? ` | ${escapeHtml(formatDateTime(request.schedule_at_local))}` : ""}${sampleCourse ? ` | previa com ${escapeHtml(sampleCourse.course_name || sampleCourse.course_ref || "-")}` : ""}</div>
      </div>
      <div class="message-block message-html">${previewMessage || "<p></p>"}</div>
      <div class="message-block">
        <div class="review-target-meta">
          <span>Bloquear comentarios: ${request.lock_comment ? "Sim" : "Nao"}</span>
          <span>Modo teste: ${request.dry_run ? "Sim" : "Nao"}</span>
          <span>Anexo: ${escapeHtml(request.attachment_name || "Sem anexo")}</span>
        </div>
      </div>
    `;
  }

  if (kind === "message") {
    const sampleCourse = firstReviewCourse(data?.courses || []);
    const sampleRecipient = Array.isArray(data?.items) && data.items.length
      ? data.items[0]
      : firstMessagePreviewRecipient();
    const sampleStudentName = sampleRecipient?.name || sampleRecipient?.student_name || "Nome do aluno";
    const previewSubject = renderCourseTemplate(request.subject || "-", sampleCourse, {
      student_name: sampleStudentName,
    });
    const previewBody = renderCourseTemplate(request.message || "", sampleCourse, {
      student_name: sampleStudentName,
    });
    return `
      <div class="message-block">
        <strong>${escapeHtml(previewSubject)}</strong>
        <div class="review-target-meta">
          <span>Estrategia: ${escapeHtml(messageUsesStudentName(request) ? "Usuarios individualmente" : (request.strategy === "context" ? "Contexto da turma" : "Usuarios"))}</span>
          <span>Deduplicar: ${request.dedupe ? "Sim" : "Nao"}</span>
          <span>Modo teste: ${request.dry_run ? "Sim" : "Nao"}</span>
          <span>Anexo: ${escapeHtml(request.attachment_name || "Sem anexo")}</span>
          <span>${sampleCourse ? `Turma: ${escapeHtml(sampleCourse.course_name || sampleCourse.course_ref || "-")}` : "Sem turma para amostra"}</span>
          <span>Aluno: ${escapeHtml(sampleStudentName)}</span>
        </div>
      </div>
      <div class="message-block"><pre>${escapeHtml(previewBody)}</pre></div>
    `;
  }

  if (kind === "engagement") {
    const sampleRecipient = Array.isArray(data?.items) && data.items.length
      ? data.items[0]
      : firstEngagementPreviewRecipient();
    const sampleCourse = sampleRecipient
      ? findCourseByRef(sampleRecipient.course_ref || sampleRecipient.course_id)
      : firstTargetCourse("engagement");
    const previewSubject = renderCourseTemplate(request.subject || "-", sampleCourse, {
      student_name: sampleRecipient?.student_name || "Nome do aluno",
    });
    const previewBody = renderCourseTemplate(request.message || "", sampleCourse, {
      student_name: sampleRecipient?.student_name || "Nome do aluno",
    });
    return `
      <div class="message-block">
        <strong>${escapeHtml(previewSubject)}</strong>
        <div class="review-target-meta">
          <span>Criterio: ${escapeHtml(formatCriteriaMode(request.criteria_mode || ""))}</span>
          <span>Modo teste: ${request.dry_run ? "Sim" : "Nao"}</span>
          <span>${sampleCourse ? `Turma: ${escapeHtml(sampleCourse.course_name || sampleCourse.course_ref || "-")}` : "Sem turma para amostra"}</span>
          <span>Aluno: ${escapeHtml(sampleRecipient?.student_name || "Nome do aluno")}</span>
        </div>
      </div>
      <div class="message-block"><pre>${escapeHtml(previewBody)}</pre></div>
    `;
  }

  return `
    <div class="message-block">
      <strong>${escapeHtml(request.subject || "-")}</strong>
      <div class="review-target-meta">
        <span>Criterio: ${escapeHtml(formatCriteriaMode(request.criteria_mode || ""))}</span>
        <span>Modo teste: ${request.dry_run ? "Sim" : "Nao"}</span>
      </div>
    </div>
    <div class="message-block"><pre>${escapeHtml(request.message || "")}</pre></div>
  `;
}

function formatPublishMode(mode) {
  if (mode === "draft") return "Rascunho";
  if (mode === "schedule") return "Agendado";
  return "Imediato";
}

function formatCriteriaMode(mode) {
  if (mode === "never_accessed") return "Sem acesso nenhum";
  if (mode === "incomplete_resources") return "Com recursos pendentes";
  if (mode === "never_accessed_or_incomplete_resources") return "Sem acesso ou pendencias";
  return mode || "-";
}

async function saveGroup() {
  const button = $("#saveGroupBtn");
  setBusy(button, true, "Salvando...");
  hideModalNotice();
  clearFieldValidation();
  try {
    const name = $("#groupName").value.trim();
    const description = $("#groupDescription").value.trim();
    const courseRefs = [...state.groupModalCourseRefs];
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

async function handleRecurrenceAction(action, recurrenceId) {
  const recurrence = state.recurrences.find((item) => item.id === recurrenceId);
  if (!recurrence) {
    showNotice("Recorrencia nao encontrada.", "error");
    return;
  }
  if (action === "edit") {
    openRecurrenceEditModal(recurrence);
    return;
  }
  if (action === "reuse") {
    applyRecurrenceToForm(recurrence);
    return;
  }
  if (action !== "cancel") {
    return;
  }
  openRecurrenceCancelModal(recurrence);
}

async function confirmRecurrenceCancel() {
  if (!ensureConnectionConfigured()) return;
  const recurrence = state.recurrenceCancel.item;
  if (!recurrence) {
    closeRecurrenceCancelModal();
    return;
  }
  const confirmValue = $("#recurrenceCancelConfirm").value.trim().toUpperCase();
  if (confirmValue !== "CANCELAR") {
    showRecurrenceCancelNotice("Digite CANCELAR para confirmar a remocao dos avisos futuros.", "error");
    $("#recurrenceCancelConfirm").focus();
    return;
  }
  const button = $("#confirmRecurrenceCancelBtn");
  setBusy(button, true, "Cancelando...");
  hideRecurrenceCancelNotice();
  hideNotice();
  try {
    const response = await apiFetch(`/api/announcement-recurrences/${recurrence.id}/cancel`, {
      method: "POST",
      body: {
        ...getConnectionPayload(),
        cancel_reason: $("#recurrenceCancelReason").value.trim(),
      },
    });
    await loadConfig();
    renderAll();
    closeRecurrenceCancelModal();
    showNotice(`Recorrencia cancelada. ${response.canceled_count || 0} aviso(s) futuro(s) removido(s) do Canvas.`, response.failure_count ? "info" : "success");
  } catch (error) {
    showRecurrenceCancelNotice(error.message, "error");
  } finally {
    setBusy(button, false);
  }
}

function renderModeSwitch(kind) {
  document.querySelectorAll(`.mode-button[data-kind='${kind}']`).forEach((button) => {
    button.classList.toggle("active", button.dataset.mode === state[kind].mode);
  });
}

function renderTargetControls(kind, options = {}) {
  const target = state[kind];
  if (!target) return;
  const groupsMode = target.mode === "groups";
  const courseMode = target.mode === "courses";
  $(`#${kind}AllGroupsLine`)?.classList.toggle("hidden", !groupsMode);
  $(`#${kind}GroupPicker`)?.classList.toggle("hidden", !groupsMode);
  $(`#${kind}CoursePicker`)?.classList.toggle("hidden", !courseMode);
  const allGroupsInput = $(`#${kind}AllGroups`);
  if (allGroupsInput) {
    allGroupsInput.checked = target.selectAllGroups;
  }
  renderPickers(options);
  renderTargetSummary(kind);
  if (kind === "message") {
    renderMessageInfoPanel();
  }
  if (kind === "announcement") {
    renderAnnouncementInfoPanel();
  }
  if (kind === "recurrence") {
    renderRecurrenceInfoPanel();
  }
  if (kind === "recurrenceEdit") {
    renderRecurrenceEditInfoPanel();
  }
  updateTemplatePreviewsForKind(kind);
}

function renderPickers(options = {}) {
  renderPicker("groupCoursePicker", coursePickerItems(), state.groupModalCourseRefs, {
    preserveScroll: options.preservePickerId === "groupCoursePicker",
  });
  renderPicker("courseCatalogPicker", catalogCoursePickerItems(), state.courseCatalogSelection, {
    preserveScroll: options.preservePickerId === "courseCatalogPicker",
  });
  renderPicker("announcementGroupPicker", groupPickerItems(), state.announcement.groupIds, {
    preserveScroll: options.preservePickerId === "announcementGroupPicker",
  });
  renderPicker("announcementCoursePicker", coursePickerItems(), state.announcement.courseRefs, {
    preserveScroll: options.preservePickerId === "announcementCoursePicker",
  });
  renderPicker("recurrenceGroupPicker", groupPickerItems(), state.recurrence.groupIds, {
    preserveScroll: options.preservePickerId === "recurrenceGroupPicker",
  });
  renderPicker("recurrenceCoursePicker", coursePickerItems(), state.recurrence.courseRefs, {
    preserveScroll: options.preservePickerId === "recurrenceCoursePicker",
  });
  renderPicker("recurrenceEditGroupPicker", groupPickerItems(), state.recurrenceEdit.groupIds, {
    preserveScroll: options.preservePickerId === "recurrenceEditGroupPicker",
  });
  renderPicker("recurrenceEditCoursePicker", coursePickerItems(), state.recurrenceEdit.courseRefs, {
    preserveScroll: options.preservePickerId === "recurrenceEditCoursePicker",
  });
  renderPicker("messageGroupPicker", groupPickerItems(), state.message.groupIds, {
    preserveScroll: options.preservePickerId === "messageGroupPicker",
  });
  renderPicker("messageCoursePicker", coursePickerItems(), state.message.courseRefs, {
    preserveScroll: options.preservePickerId === "messageCoursePicker",
  });
  renderPicker("engagementGroupPicker", groupPickerItems(), state.engagement.groupIds, {
    preserveScroll: options.preservePickerId === "engagementGroupPicker",
  });
  renderPicker("engagementCoursePicker", coursePickerItems(), state.engagement.courseRefs, {
    preserveScroll: options.preservePickerId === "engagementCoursePicker",
  });
  renderCatalogCourseSummary();
}

function renderPicker(pickerId, items, selectedIds, options = {}) {
  const target = $(`#${pickerId}`);
  if (!target) return;
  const previousScrollTop = options.preserveScroll ? getPickerScrollTop(pickerId) : null;
  const searchText = state.pickerSearch[pickerId] || "";
  const selectedSet = new Set(selectedIds);
  const filtered = sortPickerItems(
    items.filter((item) => item.search.includes(searchText)),
    selectedSet,
    shouldReorderSelected(pickerId),
  );
  target.innerHTML = `
    <div class="picker-root" data-picker-root="${pickerId}">
      <div class="picker-toolbar">
        <input type="text" data-picker-search="${pickerId}" placeholder="Buscar..." value="${escapeHtml(searchText)}">
        <div class="picker-selected">
          ${selectedIds.length ? selectedIds.map((value) => {
            const item = items.find((entry) => entry.id === value);
            return `<button class="chip" type="button" data-picker-remove="${pickerId}" data-value="${escapeHtml(value)}">${escapeHtml(item?.shortLabel || item?.label || value)} x</button>`;
          }).join("") : `<span class="picker-help">Nenhum item selecionado.</span>`}
        </div>
      </div>
      <div class="picker-options">
        ${filtered.length ? filtered.map((item) => `
          <label class="picker-option ${selectedSet.has(item.id) ? "is-selected" : ""} ${item.disabled ? "is-disabled" : ""}">
            <input type="checkbox" data-picker-checkbox="${pickerId}" value="${escapeHtml(item.id)}" ${selectedSet.has(item.id) ? "checked" : ""} ${item.disabled ? "disabled" : ""}>
            <div>
              <strong>${escapeHtml(item.label)}${item.badge ? ` <span class="inline-badge">${escapeHtml(item.badge)}</span>` : ""}</strong>
              <small>${escapeHtml(item.meta || "")}</small>
            </div>
          </label>
        `).join("") : `<div class="picker-empty">Nenhum item encontrado.</div>`}
      </div>
    </div>
  `;
  if (previousScrollTop !== null) {
    restorePickerScrollTop(pickerId, previousScrollTop);
  }
}

function rerenderPickerById(pickerId, options = {}) {
  const pickers = {
    groupCoursePicker: () => renderPicker("groupCoursePicker", coursePickerItems(), selectedValues("groupCoursePicker"), options),
    courseCatalogPicker: () => renderPicker("courseCatalogPicker", catalogCoursePickerItems(), state.courseCatalogSelection, options),
    announcementGroupPicker: () => renderPicker("announcementGroupPicker", groupPickerItems(), state.announcement.groupIds, options),
    announcementCoursePicker: () => renderPicker("announcementCoursePicker", coursePickerItems(), state.announcement.courseRefs, options),
    recurrenceGroupPicker: () => renderPicker("recurrenceGroupPicker", groupPickerItems(), state.recurrence.groupIds, options),
    recurrenceCoursePicker: () => renderPicker("recurrenceCoursePicker", coursePickerItems(), state.recurrence.courseRefs, options),
    recurrenceEditGroupPicker: () => renderPicker("recurrenceEditGroupPicker", groupPickerItems(), state.recurrenceEdit.groupIds, options),
    recurrenceEditCoursePicker: () => renderPicker("recurrenceEditCoursePicker", coursePickerItems(), state.recurrenceEdit.courseRefs, options),
    messageGroupPicker: () => renderPicker("messageGroupPicker", groupPickerItems(), state.message.groupIds, options),
    messageCoursePicker: () => renderPicker("messageCoursePicker", coursePickerItems(), state.message.courseRefs, options),
    engagementGroupPicker: () => renderPicker("engagementGroupPicker", groupPickerItems(), state.engagement.groupIds, options),
    engagementCoursePicker: () => renderPicker("engagementCoursePicker", coursePickerItems(), state.engagement.courseRefs, options),
  };
  pickers[pickerId]?.();
}

function getPickerScrollTop(pickerId) {
  const options = document.querySelector(`#${pickerId} .picker-options`);
  return options ? options.scrollTop : 0;
}

function restorePickerScrollTop(pickerId, scrollTop) {
  window.requestAnimationFrame(() => {
    const options = document.querySelector(`#${pickerId} .picker-options`);
    if (options) {
      options.scrollTop = scrollTop;
    }
  });
}

function shouldReorderSelected(pickerId) {
  return state.pickerReorder[pickerId] !== false;
}

function sortPickerItems(items, selectedSet, reorderSelected) {
  return [...items].sort((left, right) => {
    if (reorderSelected) {
      const leftRank = selectedSet.has(left.id) ? 0 : 1;
      const rightRank = selectedSet.has(right.id) ? 0 : 1;
      if (leftRank !== rightRank) {
        return leftRank - rightRank;
      }
    }
    return String(left.label || "").localeCompare(String(right.label || ""), "pt-BR", { sensitivity: "base" });
  });
}

function togglePickerValue(pickerId, value, checked, options = {}) {
  const target = pickerTarget(pickerId);
  const nextValues = checked
    ? unique([...(target.values || []), value])
    : (target.values || []).filter((item) => item !== value);
  state.pickerReorder[pickerId] = false;
  target.set(nextValues);
  if (target.kind) {
    if (target.kind === "engagement") {
      state.engagement.preview = null;
      renderEngagementPreview(null);
    }
    renderTargetSummary(target.kind);
    if (target.kind === "message") {
      clearMessagePreviewRecipients({ updatePreview: false });
      renderMessageInfoPanel();
    }
    updateTemplatePreviewsForKind(target.kind);
    persistUiState();
    if (!options.deferRender) {
      renderTargetControls(target.kind, { preservePickerId: pickerId });
    }
    return;
  }
  renderCatalogCourseSummary();
  if (target.render) {
    if (!options.deferRender) {
      target.render(nextValues, { preserveScroll: true });
    }
    return;
  }
  rerenderPickerById(pickerId);
}

function pickerTarget(pickerId) {
  const map = {
    groupCoursePicker: {
      values: state.groupModalCourseRefs,
      set(next) {
        state.groupModalCourseRefs = next;
      },
      render(next, options = {}) {
        renderPicker("groupCoursePicker", coursePickerItems(), next, options);
      },
    },
    courseCatalogPicker: {
      values: state.courseCatalogSelection,
      set(next) {
        state.courseCatalogSelection = next;
        renderCatalogCourseSummary();
      },
      render(next, options = {}) {
        renderCatalogCourseSummary();
        renderPicker("courseCatalogPicker", catalogCoursePickerItems(), next, options);
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
    recurrenceGroupPicker: {
      kind: "recurrence",
      values: state.recurrence.groupIds,
      set(next) {
        state.recurrence.groupIds = next;
        state.recurrence.preview = null;
        state.recurrence.previewSignature = "";
      },
    },
    recurrenceCoursePicker: {
      kind: "recurrence",
      values: state.recurrence.courseRefs,
      set(next) {
        state.recurrence.courseRefs = next;
        state.recurrence.preview = null;
        state.recurrence.previewSignature = "";
      },
    },
    recurrenceEditGroupPicker: {
      kind: "recurrenceEdit",
      values: state.recurrenceEdit.groupIds,
      set(next) {
        state.recurrenceEdit.groupIds = next;
        state.recurrenceEdit.preview = null;
        state.recurrenceEdit.previewSignature = "";
      },
    },
    recurrenceEditCoursePicker: {
      kind: "recurrenceEdit",
      values: state.recurrenceEdit.courseRefs,
      set(next) {
        state.recurrenceEdit.courseRefs = next;
        state.recurrenceEdit.preview = null;
        state.recurrenceEdit.previewSignature = "";
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
    engagementGroupPicker: {
      kind: "engagement",
      values: state.engagement.groupIds,
      set(next) {
        state.engagement.groupIds = next;
        state.engagement.preview = null;
      },
    },
    engagementCoursePicker: {
      kind: "engagement",
      values: state.engagement.courseRefs,
      set(next) {
        state.engagement.courseRefs = next;
        state.engagement.preview = null;
      },
    },
  };
  return map[pickerId];
}

function selectedValues(pickerId) {
  if (pickerId === "groupCoursePicker") return state.groupModalCourseRefs;
  if (pickerId === "courseCatalogPicker") return state.courseCatalogSelection;
  if (pickerId === "announcementGroupPicker") return state.announcement.groupIds;
  if (pickerId === "announcementCoursePicker") return state.announcement.courseRefs;
  if (pickerId === "recurrenceGroupPicker") return state.recurrence.groupIds;
  if (pickerId === "recurrenceCoursePicker") return state.recurrence.courseRefs;
  if (pickerId === "recurrenceEditGroupPicker") return state.recurrenceEdit.groupIds;
  if (pickerId === "recurrenceEditCoursePicker") return state.recurrenceEdit.courseRefs;
  if (pickerId === "messageGroupPicker") return state.message.groupIds;
  if (pickerId === "messageCoursePicker") return state.message.courseRefs;
  if (pickerId === "engagementGroupPicker") return state.engagement.groupIds;
  if (pickerId === "engagementCoursePicker") return state.engagement.courseRefs;
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
    shortLabel: course.course_name || `Curso ${course.course_ref}`,
    meta: `${course.term_name ? `${course.term_name}` : "Curso cadastrado"}`,
    search: `${course.course_ref} ${course.course_name || ""} ${course.course_code || ""} ${course.term_name || ""}`.toLowerCase(),
  }));
}

function catalogCoursePickerItems() {
  return state.courseCatalog.map((course) => ({
    id: String(course.course_ref || course.id),
    label: course.name || `Curso ${course.course_ref || course.id}`,
    shortLabel: course.name || `Curso ${course.course_ref || course.id}`,
    meta: `${course.term_name ? `${course.term_name}` : "Curso do Canvas"}`,
    search: `${course.course_ref || course.id} ${course.name || ""} ${course.course_code || ""} ${course.term_name || ""}`.toLowerCase(),
    disabled: Boolean(course.already_registered),
    badge: course.already_registered ? "ja cadastrado" : "",
  }));
}

function renderTargetSummary(kind) {
  const target = state[kind];
  const summaryEl = $(`#${kind}TargetSummary`);
  if (!target || !summaryEl) return;
  const courses = target.mode === "groups"
    ? selectedGroups(kind).flatMap((group) => group.courses || [])
    : selectedCourses(kind);
  const modeLabelMap = {
    groups: "Grupos salvos",
    courses: "Cursos especificos",
  };
  const uniqueCourseRefs = unique(courses.map((course) => course.course_ref));
  if (kind === "recurrence" || kind === "recurrenceEdit") {
    const previewSummary = state[kind].preview?.summary || null;
    summaryEl.innerHTML = `
      <div class="summary-card"><span>Modo</span><strong>${modeLabelMap[target.mode] || "-"}</strong></div>
      <div class="summary-card"><span>Grupos</span><strong>${target.mode === "groups" ? (target.selectAllGroups ? "Todos" : String(selectedGroups(kind).length)) : "-"}</strong></div>
      <div class="summary-card"><span>Turmas selecionadas</span><strong>${escapeHtml(String(uniqueCourseRefs.length))}</strong></div>
      <div class="summary-card"><span>Ocorrencias por turma</span><strong>${escapeHtml(String(previewSummary?.occurrences_per_course || 0))}</strong></div>
      <div class="summary-card"><span>Total de avisos</span><strong>${escapeHtml(String(previewSummary?.total_announcements || 0))}</strong></div>
      <div class="summary-card"><span>Ultima data</span><strong>${escapeHtml(formatDate(previewSummary?.last_publish_at || ""))}</strong></div>
    `;
    return;
  }
  if (kind === "engagement") {
    const previewSummary = state.engagement.preview?.summary || null;
    summaryEl.innerHTML = `
      <div class="summary-card"><span>Modo</span><strong>${modeLabelMap[target.mode] || "-"}</strong></div>
      <div class="summary-card"><span>Grupos</span><strong>${target.mode === "groups" ? (target.selectAllGroups ? "Todos" : String(selectedGroups(kind).length)) : "-"}</strong></div>
      <div class="summary-card"><span>Turmas selecionadas</span><strong>${escapeHtml(String(uniqueCourseRefs.length))}</strong></div>
      <div class="summary-card"><span>Preview carregado</span><strong>${previewSummary ? "Sim" : "Nao"}</strong></div>
      <div class="summary-card"><span>Alunos analisados</span><strong>${escapeHtml(String(previewSummary?.total_students_found || 0))}</strong></div>
      <div class="summary-card"><span>Alunos alvo</span><strong>${escapeHtml(String(previewSummary?.total_matched_students || 0))}</strong></div>
    `;
    return;
  }
  summaryEl.innerHTML = `
    <div class="summary-card"><span>Modo</span><strong>${modeLabelMap[target.mode] || "-"}</strong></div>
    <div class="summary-card"><span>Grupos</span><strong>${target.mode === "groups" ? (target.selectAllGroups ? "Todos" : String(selectedGroups(kind).length)) : "-"}</strong></div>
    <div class="summary-card"><span>Cursos</span><strong>${escapeHtml(String(uniqueCourseRefs.length))}</strong></div>
    <div class="summary-card"><span>Em foco</span><strong>${escapeHtml(courses.slice(0, 2).map((course) => course.course_name || course.course_ref).join(" | ") || "Nenhuma")}${courses.length > 2 ? "..." : ""}</strong></div>
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
  const request = buildMessageRequestBody();
  $("#messageInfoPanel").innerHTML = courses.length ? `
    <div class="summary-grid">
      <div class="summary-card"><span>Turmas resolvidas</span><strong>${escapeHtml(String(courses.length))}</strong></div>
      <div class="summary-card"><span>Modo</span><strong>${state.message.mode === "courses" ? "Cursos especificos" : "Grupos salvos"}</strong></div>
      <div class="summary-card"><span>Grupos</span><strong>${state.message.mode === "groups" ? (state.message.selectAllGroups ? "Todos" : String(selectedGroups("message").length)) : "-"}</strong></div>
      <div class="summary-card"><span>Cursos</span><strong>${escapeHtml(String(unique(courses.map((course) => course.course_ref)).length))}</strong></div>
      <div class="summary-card"><span>Estrategia final</span><strong>${escapeHtml(messageReviewStrategyLabel(request))}</strong></div>
      <div class="summary-card"><span>Modo teste</span><strong>${request.dry_run ? "Sim" : "Nao"}</strong></div>
    </div>
    <div class="chips">
      <span class="chip">${escapeHtml(request.dedupe ? "Sem duplicidade entre turmas" : "Duplicidade permitida")}</span>
      <span class="chip">${escapeHtml($("#messageAttachment").files?.[0]?.name || "Sem anexo")}</span>
      ${messageUsesStudentName(request) ? `<span class="chip">Personalizacao por aluno ativa</span>` : ""}
      ${unique(courses.map((course) => `${course.course_name || course.course_ref}`)).slice(0, 10).map((label) => `<span class="chip">${escapeHtml(label)}</span>`).join("")}
    </div>
  ` : "Defina o destino para ver aqui o resumo operacional do envio.";
}

function renderAnnouncementInfoPanel() {
  const panel = $("#announcementInfoPanel");
  if (!panel) return;
  const courses = state.announcement.mode === "groups"
    ? selectedGroups("announcement").flatMap((group) => group.courses || [])
    : selectedCourses("announcement");
  const request = buildAnnouncementRequestBody();
  panel.innerHTML = courses.length ? `
    <div class="summary-grid">
      <div class="summary-card"><span>Turmas resolvidas</span><strong>${escapeHtml(String(unique(courses.map((course) => course.course_ref)).length))}</strong></div>
      <div class="summary-card"><span>Publicacao</span><strong>${escapeHtml(formatPublishMode(request.publish_mode))}</strong></div>
      <div class="summary-card"><span>Bloquear comentarios</span><strong>${request.lock_comment ? "Sim" : "Nao"}</strong></div>
      <div class="summary-card"><span>Modo teste</span><strong>${request.dry_run ? "Sim" : "Nao"}</strong></div>
    </div>
    <div class="chips">
      <span class="chip">${escapeHtml($("#announcementAttachment").files?.[0]?.name || "Sem anexo")}</span>
      ${request.publish_mode === "schedule" && request.schedule_at_local ? `<span class="chip">Agenda para ${escapeHtml(formatLocalDateTimeLabel(request.schedule_at_local))}</span>` : ""}
      ${unique(courses.map((course) => `${course.course_name || course.course_ref}`)).slice(0, 8).map((label) => `<span class="chip">${escapeHtml(label)}</span>`).join("")}
    </div>
  ` : "Defina o destino para ver o resumo operacional do comunicado.";
}

function renderRecurrenceInfoPanel() {
  const panel = $("#recurrenceInfoPanel");
  if (!panel) return;
  const payload = buildRecurrenceRequestBody();
  const courses = payload.target_mode === "courses"
    ? selectedCourses("recurrence")
    : selectedGroups("recurrence").flatMap((group) => group.courses || []);
  const uniqueCourses = unique(courses.map((course) => course.course_ref));
  const previewCurrent = recurrencePreviewIsCurrent("recurrence", payload);
  panel.innerHTML = uniqueCourses.length ? `
    <div class="summary-grid">
      <div class="summary-card"><span>Turmas</span><strong>${escapeHtml(String(uniqueCourses.length))}</strong></div>
      <div class="summary-card"><span>Frequencia</span><strong>${escapeHtml($("#recurrenceType").value === "daily" ? "Diaria" : "Semanal")}</strong></div>
      <div class="summary-card"><span>Intervalo</span><strong>${escapeHtml(String($("#recurrenceInterval").value || 1))}</strong></div>
      <div class="summary-card"><span>Ocorrencias</span><strong>${escapeHtml(String($("#recurrenceOccurrences").value || 0))}</strong></div>
    </div>
    <div class="chips">
      <span class="chip">${escapeHtml(previewCurrent ? "Preview atualizado" : "Preview pendente")}</span>
      <span class="chip">${escapeHtml($("#recurrenceLockComment").checked ? "Comentarios bloqueados" : "Comentarios liberados")}</span>
      ${payload.first_publish_at_local ? `<span class="chip">Primeira publicacao em ${escapeHtml(formatLocalDateTimeLabel(payload.first_publish_at_local))}</span>` : ""}
    </div>
  ` : "Defina o destino e gere a previsao antes de abrir a revisao final.";
  renderRecurrencePreviewState();
}

function renderRecurrenceEditInfoPanel() {
  const panel = $("#recurrenceEditInfoPanel");
  if (!panel || !state.recurrenceEdit.id) {
    if (panel) {
        panel.innerHTML = "Atualize a previsao antes de salvar a edicao da recorrencia.";
    }
    renderRecurrenceEditPreviewState();
    return;
  }
  const payload = buildRecurrenceEditRequestBody();
  const courses = payload.target_mode === "courses"
    ? selectedCourses("recurrenceEdit")
    : selectedGroups("recurrenceEdit").flatMap((group) => group.courses || []);
  const uniqueCourses = unique(courses.map((course) => course.course_ref));
  const previewCurrent = recurrencePreviewIsCurrent("recurrenceEdit", payload);
  panel.innerHTML = `
    <div class="summary-grid">
      <div class="summary-card"><span>Turmas</span><strong>${escapeHtml(String(uniqueCourses.length))}</strong></div>
      <div class="summary-card"><span>Frequencia</span><strong>${escapeHtml($("#recurrenceEditType").value === "daily" ? "Diaria" : "Semanal")}</strong></div>
      <div class="summary-card"><span>Intervalo</span><strong>${escapeHtml(String($("#recurrenceEditInterval").value || 1))}</strong></div>
      <div class="summary-card"><span>Ocorrencias</span><strong>${escapeHtml(String($("#recurrenceEditOccurrences").value || 0))}</strong></div>
    </div>
    <div class="chips">
      <span class="chip">${escapeHtml(previewCurrent ? "Preview atualizado" : "Preview pendente")}</span>
      <span class="chip">${escapeHtml($("#recurrenceEditLockComment").checked ? "Comentarios bloqueados" : "Comentarios liberados")}</span>
      ${payload.first_publish_at_local ? `<span class="chip">Primeira publicacao em ${escapeHtml(formatLocalDateTimeLabel(payload.first_publish_at_local))}</span>` : ""}
    </div>
  `;
  renderRecurrenceEditPreviewState();
}

function clearMessagePreviewRecipients(options = {}) {
  state.message.previewRecipients = [];
  if (options.updatePreview !== false) {
    updateMessagePreview();
  }
}

function renderEngagementPreview(data) {
  const target = $("#engagementPreviewCard");
  if (!target) return;
  renderTargetSummary("engagement");
  if (!data) {
    target.innerHTML = "Selecione as turmas e clique em buscar para ver quem entra no envio.";
    target.classList.add("empty-state");
    syncCollapsibleCards();
    return;
  }

  target.classList.remove("empty-state");
  const summary = data.summary || {};
  const courses = Array.isArray(data.courses) ? data.courses : [];
  const items = Array.isArray(data.items) ? data.items : [];
  const notices = [];
  if (summary.courses_without_module_requirements) {
    notices.push(`${summary.courses_without_module_requirements} curso(s) sem requisitos de modulos configurados.`);
  }
  if (summary.analytics_unavailable_courses) {
    notices.push(`${summary.analytics_unavailable_courses} curso(s) sem analytics disponivel.`);
  }
  if (summary.progress_unavailable_courses) {
    notices.push(`${summary.progress_unavailable_courses} curso(s) sem progresso de modulos disponivel.`);
  }

  target.innerHTML = `
    <div class="summary-grid">
      <div class="summary-card"><span>Cursos</span><strong>${escapeHtml(String(summary.total_courses || 0))}</strong></div>
      <div class="summary-card"><span>Alunos analisados</span><strong>${escapeHtml(String(summary.total_students_found || 0))}</strong></div>
      <div class="summary-card"><span>Alunos que receberao</span><strong>${escapeHtml(String(summary.total_matched_students || 0))}</strong></div>
      <div class="summary-card"><span>Sem acesso nenhum</span><strong>${escapeHtml(String(summary.total_never_accessed_matches || 0))}</strong></div>
      <div class="summary-card"><span>Recursos pendentes</span><strong>${escapeHtml(String(summary.total_incomplete_resources_matches || 0))}</strong></div>
      <div class="summary-card"><span>Sem atividade</span><strong>${escapeHtml(String(summary.total_inactive_days_matches || 0))}</strong></div>
      <div class="summary-card"><span>Baixa atividade</span><strong>${escapeHtml(String(summary.total_low_activity_matches || 0))}</strong></div>
      <div class="summary-card"><span>Turma foco</span><strong>${escapeHtml(summary.top_priority_course_name || "-")}</strong></div>
      <div class="summary-card"><span>Criterio</span><strong>${escapeHtml(formatEngagementCriteria(summary.criteria_mode || $("#engagementCriteriaMode").value))}</strong></div>
    </div>
    ${notices.length ? `<div class="chips">${notices.map((item) => `<span class="chip dim">${escapeHtml(item)}</span>`).join("")}</div>` : ""}
    <details class="table-guide" open>
      <summary>Como ler estes dados</summary>
      <div class="table-guide-grid">
        <div class="table-guide-item"><strong>Sem acesso</strong><span>Canvas marcou page_views = 0 e participations = 0 para o aluno.</span></div>
        <div class="table-guide-item"><strong>Pendentes</strong><span>O aluno ainda nao concluiu requisitos de modulos configurados no curso.</span></div>
        <div class="table-guide-item"><strong>Sem atividade</strong><span>O last_activity_at ficou alem do limite configurado na busca.</span></div>
        <div class="table-guide-item"><strong>Baixa atividade</strong><span>O total_activity_time ficou abaixo do teto em minutos informado.</span></div>
        <div class="table-guide-item"><strong>Recebimento</strong><span>A mensagem vai pela Inbox do Canvas; email depende das notificacoes do aluno.</span></div>
      </div>
    </details>
    ${courses.length ? renderTable(engagementCourseColumns(), courses) : `<div class="empty-state">Nenhum curso entrou no preview.</div>`}
    ${items.length ? renderTable(engagementPreviewColumns(), items) : `<div class="empty-state">Nenhum aluno corresponde ao criterio selecionado.</div>`}
  `;
  syncCollapsibleCards();
}

function engagementCourseColumns() {
  return [
    { label: "Turma", format: (row) => escapeHtml(row.course_name || "-") },
    { label: "Prioridade", format: (row) => priorityPill(row.priority_level, row.urgency_score) },
    { label: "Alunos", format: (row) => escapeHtml(String(row.students_found || 0)) },
    { label: "Alvo", format: (row) => escapeHtml(String(row.matched_students || 0)) },
    { label: "Cobertura", format: (row) => `${escapeHtml(formatSummaryValue(row.matched_ratio || 0))}%` },
    { label: "Sem acesso", format: (row) => escapeHtml(String(row.never_accessed_matches || 0)) },
    { label: "Pendentes", format: (row) => escapeHtml(String(row.incomplete_resources_matches || 0)) },
    { label: "Sem atividade", format: (row) => escapeHtml(String(row.inactive_days_matches || 0)) },
    { label: "Baixa atividade", format: (row) => escapeHtml(String(row.low_activity_matches || 0)) },
    { label: "Modulo", format: (row) => row.has_module_requirements ? "Sim" : "Nao" },
    { label: "Status API", format: (row) => `${row.analytics_available ? "Analytics ok" : "Analytics indisponivel"}<div class="subtle">${row.progress_available ? "Progress ok" : "Progress indisponivel"} | ${row.enrollment_activity_available ? "Enrollments ok" : "Enrollments indisponivel"}</div>` },
  ];
}

function engagementPreviewColumns() {
  return [
    { label: "Turma", format: (row) => escapeHtml(row.course_name || "-") },
    { label: "Aluno", format: (row) => `${escapeHtml(row.student_name || "-")}<div class="subtle mono">${escapeHtml(String(row.user_id || "-"))}</div>` },
    { label: "Prioridade", format: (row) => priorityPill(row.priority_level, row.urgency_score) },
    { label: "Acessos", format: (row) => `${escapeHtml(String(row.page_views || 0))} visualizacoes<div class="subtle">${escapeHtml(String(row.participations || 0))} participacoes</div>` },
    { label: "Atividade", format: (row) => `${escapeHtml(formatDateTime(row.last_activity_at))}<div class="subtle">${escapeHtml(String(Math.round((row.total_activity_time_seconds || 0) / 60)))} min</div>` },
    { label: "Recursos", format: (row) => `${escapeHtml(String(row.requirement_completed_count || 0))}/${escapeHtml(String(row.requirement_count || 0))}` },
    { label: "Motivo", format: (row) => escapeHtml(row.reasons_label || "-") },
  ];
}

const TEMPLATE_SCOPE_CONFIG = {
  announcement: {
    fields: [
      { id: "announcementTitle", label: "Titulo" },
      { id: "announcementMessage", label: "Mensagem" },
    ],
    tokens: [
      { token: "{{course_name}}", label: "Nome da disciplina" },
    ],
  },
  recurrence: {
    fields: [
      { id: "recurrenceTitle", label: "Titulo do aviso" },
      { id: "recurrenceMessage", label: "Mensagem" },
    ],
    tokens: [
      { token: "{{course_name}}", label: "Nome da disciplina" },
    ],
  },
  recurrenceEdit: {
    fields: [
      { id: "recurrenceEditTitle", label: "Titulo do aviso" },
      { id: "recurrenceEditMessage", label: "Mensagem" },
    ],
    tokens: [
      { token: "{{course_name}}", label: "Nome da disciplina" },
    ],
  },
  message: {
    fields: [
      { id: "messageSubject", label: "Assunto" },
      { id: "messageBody", label: "Mensagem" },
    ],
    tokens: [
      { token: "{{student_name}}", label: "Nome do aluno" },
      { token: "{{course_name}}", label: "Nome da disciplina" },
    ],
  },
  engagement: {
    fields: [
      { id: "engagementSubject", label: "Assunto" },
      { id: "engagementMessage", label: "Mensagem" },
    ],
    tokens: [
      { token: "{{student_name}}", label: "Nome do aluno" },
      { token: "{{course_name}}", label: "Nome da disciplina" },
    ],
  },
};

function renderTemplateAssistants() {
  ["announcement", "recurrence", "recurrenceEdit", "message", "engagement"].forEach((scope) => {
    renderTokenPalette(scope);
    renderTemplateStatus(scope);
  });
}

function renderTokenPalette(scope) {
  const container = $(`#${scope}TokenPalette`);
  const config = TEMPLATE_SCOPE_CONFIG[scope];
  if (!container || !config) return;
  container.innerHTML = config.tokens.map((item) => `
    <button
      class="token-chip"
      type="button"
      draggable="true"
      data-template-scope="${escapeHtml(scope)}"
      data-template-token="${escapeHtml(item.token)}"
      title="Clique ou arraste para inserir"
    >
      <span>${escapeHtml(item.token)}</span>
      <small>${escapeHtml(item.label)}</small>
    </button>
  `).join("");
}

function renderTemplateStatus(scope) {
  const container = $(`#${scope}TemplateStatus`);
  const config = TEMPLATE_SCOPE_CONFIG[scope];
  if (!container || !config) return;
  const allowedTokens = new Set(config.tokens.map((item) => item.token));
  const rows = config.fields.map((field) => {
    const value = $(`#${field.id}`)?.value || "";
    const tokens = extractTemplateTokens(value);
    const invalid = tokens.filter((token) => !allowedTokens.has(token));
    const valid = tokens.filter((token) => allowedTokens.has(token));
    const stateLine = invalid.length
      ? `<div class="template-status-help text-danger">Variaveis invalidas bloqueiam o envio.</div>`
      : `<div class="template-status-help">${tokens.length ? "Variaveis reconhecidas com sucesso." : "Nenhuma variavel usada neste campo."}</div>`;
    const pills = [
      ...valid.map((token) => `<span class="template-token-pill valid">${escapeHtml(token)}</span>`),
      ...invalid.map((token) => `<span class="template-token-pill invalid">${escapeHtml(token)}</span>`),
    ];
    return `
      <div class="template-status-row">
        <strong>${escapeHtml(field.label)}</strong>
        ${stateLine}
        <div class="template-token-list">
          ${pills.length ? pills.join("") : `<span class="template-token-pill empty">Sem variaveis</span>`}
        </div>
      </div>
    `;
  });
  container.innerHTML = `<div class="template-status-grid">${rows.join("")}</div>`;
}

function extractTemplateTokens(text) {
  const matches = String(text || "").match(/{{\s*[a-zA-Z0-9_]+\s*}}/g) || [];
  return unique(matches.map((token) => token.replace(/\s+/g, "")));
}

function hasInvalidTemplateTokens(scope) {
  const config = TEMPLATE_SCOPE_CONFIG[scope];
  if (!config) return false;
  const allowedTokens = new Set(config.tokens.map((item) => item.token));
  return config.fields.some((field) => {
    const value = $(`#${field.id}`)?.value || "";
    return extractTemplateTokens(value).some((token) => !allowedTokens.has(token));
  });
}

function insertTemplateToken(scope, token) {
  const config = TEMPLATE_SCOPE_CONFIG[scope];
  if (!config) return;
  const activeField = state.templateFocusFieldId ? document.getElementById(state.templateFocusFieldId) : null;
  const targetField = activeField?.dataset?.templateScope === scope
    ? activeField
    : document.getElementById(config.fields[config.fields.length - 1].id);
  if (!targetField) return;
  insertTextAtCursor(targetField, token);
  targetField.focus();
  handleTemplateFieldChanged(scope);
}

function insertTextAtCursor(element, text) {
  const start = typeof element.selectionStart === "number" ? element.selectionStart : element.value.length;
  const end = typeof element.selectionEnd === "number" ? element.selectionEnd : element.value.length;
  const value = element.value || "";
  element.value = `${value.slice(0, start)}${text}${value.slice(end)}`;
  const nextCaret = start + text.length;
  if (typeof element.setSelectionRange === "function") {
    element.setSelectionRange(nextCaret, nextCaret);
  }
}

function handleTemplateFieldChanged(scope) {
  renderTemplateStatus(scope);
  updateTemplatePreviewsForKind(scope);
  persistUiState();
}

function updateTemplatePreviewsForKind(kind) {
  if (kind === "announcement") {
    updateAnnouncementPreview();
    return;
  }
  if (kind === "message") {
    updateMessagePreview();
    return;
  }
  if (kind === "recurrence") {
    updateRecurrenceSamplePreview();
    return;
  }
  if (kind === "recurrenceEdit") {
    updateRecurrenceEditSamplePreview();
    return;
  }
  if (kind === "engagement") {
    updateEngagementMessagePreview();
  }
}

function collectEngagementCriteriaConfig() {
  return {
    match_mode: $("#engagementMatchMode").value,
    inactive_days: $("#engagementInactiveDays").value ? Number($("#engagementInactiveDays").value) : null,
    max_total_activity_minutes: $("#engagementMaxActivityMinutes").value ? Number($("#engagementMaxActivityMinutes").value) : null,
    only_with_module_requirements: $("#engagementOnlyModules").checked,
    require_never_accessed: $("#engagementRequireNeverAccessed").checked,
    require_incomplete_resources: $("#engagementRequireIncomplete").checked,
  };
}

function buildMessageRequestBody() {
  return {
    ...getConnectionPayload(),
    ...getTargetPayload("message"),
    subject: $("#messageSubject").value.trim(),
    message: $("#messageBody").value.trim(),
    strategy: $("#messageStrategy").value,
    dedupe: $("#messageDedupe").checked,
    dry_run: $("#messageDryRun").checked,
  };
}

function buildAnnouncementRequestBody() {
  return {
    ...getConnectionPayload(),
    ...getTargetPayload("announcement"),
    title: $("#announcementTitle").value.trim(),
    message_html: $("#announcementMessage").value.trim(),
    publish_mode: $("#publishMode").value,
    schedule_at_local: $("#announcementScheduleAt").value,
    client_timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    lock_comment: $("#lockComment").checked,
    dry_run: $("#announcementDryRun").checked,
  };
}

function validateAnnouncementForm() {
  if (!ensureConnectionConfigured() || !ensureTargetSelection("announcement")) return false;
  if (hasInvalidTemplateTokens("announcement")) {
    showNotice("Existem variaveis invalidas no comunicado. Use apenas os blocos reconhecidos.", "error");
    focusField("#announcementTitle");
    return false;
  }
  if (!$("#announcementTitle").value.trim()) {
    markInvalid("#announcementTitle");
    focusField("#announcementTitle");
    showNotice("Informe o titulo do comunicado.", "error");
    return false;
  }
  if (!$("#announcementMessage").value.trim()) {
    markInvalid("#announcementMessage");
    focusField("#announcementMessage");
    showNotice("Informe a mensagem HTML do comunicado.", "error");
    return false;
  }
  if ($("#publishMode").value === "schedule" && !$("#announcementScheduleAt").value) {
    markInvalid("#announcementScheduleAt");
    focusField("#announcementScheduleAt");
    showNotice("Informe a data e hora do agendamento.", "error");
    return false;
  }
  return true;
}

function buildEngagementRequestBody() {
  return {
    ...getConnectionPayload(),
    ...getTargetPayload("engagement"),
    criteria_mode: $("#engagementCriteriaMode").value,
    criteria_config: collectEngagementCriteriaConfig(),
    subject: $("#engagementSubject").value.trim(),
    message: $("#engagementMessage").value.trim(),
    dry_run: $("#engagementDryRun").checked,
  };
}

function validateMessageForm() {
  if (!ensureConnectionConfigured() || !ensureTargetSelection("message")) return false;
  if (hasInvalidTemplateTokens("message")) {
    showNotice("Existem variaveis invalidas na caixa de entrada. Use apenas os blocos reconhecidos.", "error");
    focusField("#messageSubject");
    return false;
  }
  if (!$("#messageSubject").value.trim()) {
    markInvalid("#messageSubject");
    focusField("#messageSubject");
    showNotice("Informe o assunto da mensagem.", "error");
    return false;
  }
  if (!$("#messageBody").value.trim()) {
    markInvalid("#messageBody");
    focusField("#messageBody");
    showNotice("Informe o corpo da mensagem.", "error");
    return false;
  }
  return true;
}

function validateEngagementForm() {
  if (!ensureConnectionConfigured() || !ensureTargetSelection("engagement")) return false;
  if (!state.engagement.preview) {
    showNotice("Busque primeiro a quantidade de alunos por turma antes de enviar a mensagem para inativos.", "error");
    openTab("engagement");
    focusField("#previewEngagementBtn");
    return false;
  }
  if (hasInvalidTemplateTokens("engagement")) {
    showNotice("Existem variaveis invalidas na mensagem para inativos. Use apenas os blocos reconhecidos.", "error");
    focusField("#engagementSubject");
    return false;
  }
  if (!$("#engagementSubject").value.trim()) {
    markInvalid("#engagementSubject");
    focusField("#engagementSubject");
    showNotice("Informe o assunto da mensagem para inativos.", "error");
    return false;
  }
  if (!$("#engagementMessage").value.trim()) {
    markInvalid("#engagementMessage");
    focusField("#engagementMessage");
    showNotice("Informe a mensagem para os alunos inativos.", "error");
    return false;
  }
  return true;
}

function validateRecurrenceForm() {
  if (!ensureConnectionConfigured() || !ensureTargetSelection("recurrence")) return false;
  if (hasInvalidTemplateTokens("recurrence")) {
    showNotice("Existem variaveis invalidas na recorrencia. Use apenas os blocos reconhecidos.", "error");
    focusField("#recurrenceTitle");
    return false;
  }
  if (!$("#recurrenceTitle").value.trim()) {
    markInvalid("#recurrenceTitle");
    focusField("#recurrenceTitle");
    showNotice("Informe o titulo da recorrencia de avisos.", "error");
    return false;
  }
  if (!$("#recurrenceMessage").value.trim()) {
    markInvalid("#recurrenceMessage");
    focusField("#recurrenceMessage");
    showNotice("Informe a mensagem HTML da recorrencia.", "error");
    return false;
  }
  if (!$("#recurrenceFirstPublishAt").value) {
    markInvalid("#recurrenceFirstPublishAt");
    focusField("#recurrenceFirstPublishAt");
    showNotice("Informe a primeira publicacao da recorrencia.", "error");
    return false;
  }
  return true;
}

function validateRecurrenceEditForm() {
  if (!state.recurrenceEdit.id) {
    showRecurrenceEditNotice("Selecione uma recorrencia valida para editar.", "error");
    return false;
  }
  if (!ensureConnectionConfigured()) return false;
  const targetPayload = getTargetPayload("recurrenceEdit");
  if (!targetPayload.course_refs?.length && !targetPayload.select_all_groups && !targetPayload.group_ids?.length) {
    showRecurrenceEditNotice("Selecione grupos ou cursos antes de salvar a recorrencia.", "error");
    return false;
  }
  if (hasInvalidTemplateTokens("recurrenceEdit")) {
    showRecurrenceEditNotice("Existem variaveis invalidas na recorrencia. Use apenas os blocos reconhecidos.", "error");
    focusField("#recurrenceEditTitle");
    return false;
  }
  if (!$("#recurrenceEditTitle").value.trim()) {
    markInvalid("#recurrenceEditTitle");
    focusField("#recurrenceEditTitle");
    showRecurrenceEditNotice("Informe o titulo da recorrencia de avisos.", "error");
    return false;
  }
  if (!$("#recurrenceEditMessage").value.trim()) {
    markInvalid("#recurrenceEditMessage");
    focusField("#recurrenceEditMessage");
    showRecurrenceEditNotice("Informe a mensagem HTML da recorrencia.", "error");
    return false;
  }
  if (!$("#recurrenceEditFirstPublishAt").value) {
    markInvalid("#recurrenceEditFirstPublishAt");
    focusField("#recurrenceEditFirstPublishAt");
    showRecurrenceEditNotice("Informe a primeira publicacao da recorrencia.", "error");
    return false;
  }
  return true;
}

function buildRecurrenceRequestBody() {
  return {
    ...getConnectionPayload(),
    ...getTargetPayload("recurrence"),
    target_mode: state.recurrence.mode,
    name: $("#recurrenceName").value.trim(),
    title: $("#recurrenceTitle").value.trim(),
    message_html: $("#recurrenceMessage").value.trim(),
    recurrence_type: $("#recurrenceType").value,
    interval_value: Number($("#recurrenceInterval").value || 1),
    first_publish_at_local: $("#recurrenceFirstPublishAt").value,
    occurrence_count: Number($("#recurrenceOccurrences").value || 1),
    client_timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
    lock_comment: $("#recurrenceLockComment").checked,
  };
}

function buildRecurrenceEditRequestBody() {
  return {
    ...getConnectionPayload(),
    ...getTargetPayload("recurrenceEdit"),
    recurrence_id: state.recurrenceEdit.id || "",
    target_mode: state.recurrenceEdit.mode,
    name: $("#recurrenceEditName").value.trim(),
    title: $("#recurrenceEditTitle").value.trim(),
    message_html: $("#recurrenceEditMessage").value.trim(),
    recurrence_type: $("#recurrenceEditType").value,
    interval_value: Number($("#recurrenceEditInterval").value || 1),
    first_publish_at_local: $("#recurrenceEditFirstPublishAt").value,
    occurrence_count: Number($("#recurrenceEditOccurrences").value || 1),
    client_timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
    lock_comment: $("#recurrenceEditLockComment").checked,
  };
}

function buildRecurrencePreviewSignature(payload) {
  return JSON.stringify({
    recurrence_id: payload.recurrence_id || "",
    target_mode: payload.target_mode || "groups",
    group_ids: [...(payload.group_ids || [])].sort(),
    course_refs: [...(payload.course_refs || [])].sort(),
    select_all_groups: Boolean(payload.select_all_groups),
    name: payload.name || "",
    title: payload.title || "",
    message_html: payload.message_html || "",
    recurrence_type: payload.recurrence_type || "",
    interval_value: Number(payload.interval_value || 0),
    first_publish_at_local: payload.first_publish_at_local || "",
    occurrence_count: Number(payload.occurrence_count || 0),
    lock_comment: Boolean(payload.lock_comment),
  });
}

function recurrencePreviewIsCurrent(kind, payload) {
  return Boolean(state[kind].preview && state[kind].previewSignature && state[kind].previewSignature === buildRecurrencePreviewSignature(payload));
}

async function previewRecurrence() {
  const button = $("#previewRecurrenceBtn");
  setBusy(button, true, "Calculando...");
  hideNotice();
  clearFieldValidation();
  try {
    if (!validateRecurrenceForm()) return;
    const requestBody = buildRecurrenceRequestBody();
    const response = await apiFetch("/api/announcement-recurrences/preview", {
      method: "POST",
      body: requestBody,
    });
    state.recurrence.preview = response;
    state.recurrence.previewSignature = buildRecurrencePreviewSignature(requestBody);
    renderTargetSummary("recurrence");
    renderRecurrenceInfoPanel();
    renderRecurrencePreview(response);
    showNotice("Previsao da recorrencia carregada.", "success");
  } catch (error) {
    state.recurrence.preview = null;
    state.recurrence.previewSignature = "";
    renderTargetSummary("recurrence");
    renderRecurrenceInfoPanel();
    renderRecurrencePreview(null);
    showNotice(error.message, "error");
  } finally {
    setBusy(button, false);
  }
}

async function previewRecurrenceEdit() {
  const button = $("#previewRecurrenceEditBtn");
  setBusy(button, true, "Calculando...");
  hideRecurrenceEditNotice();
  clearFieldValidation();
  try {
    if (!validateRecurrenceEditForm()) return;
    const requestBody = buildRecurrenceEditRequestBody();
    const response = await apiFetch("/api/announcement-recurrences/preview", {
      method: "POST",
      body: requestBody,
    });
    state.recurrenceEdit.preview = response;
    state.recurrenceEdit.previewSignature = buildRecurrencePreviewSignature(requestBody);
    renderRecurrenceEditInfoPanel();
    renderRecurrenceEditPreview(response);
    showRecurrenceEditNotice("Impacto da edicao carregado com sucesso.", "success");
  } catch (error) {
    state.recurrenceEdit.preview = null;
    state.recurrenceEdit.previewSignature = "";
    renderRecurrenceEditInfoPanel();
    renderRecurrenceEditPreview(null);
    showRecurrenceEditNotice(error.message, "error");
  } finally {
    setBusy(button, false);
  }
}

async function previewEngagementTargets() {
  const button = $("#previewEngagementBtn");
  setBusy(button, true, "Carregando...");
  hideNotice();
  clearFieldValidation();
  try {
    if (!ensureConnectionConfigured() || !ensureTargetSelection("engagement")) return;
    const response = await apiFetch("/api/engagement/inactive-targets", {
      method: "POST",
      body: {
        ...getConnectionPayload(),
        ...getTargetPayload("engagement"),
        criteria_mode: $("#engagementCriteriaMode").value,
        criteria_config: collectEngagementCriteriaConfig(),
      },
    });
    state.engagement.preview = response;
    renderTargetSummary("engagement");
    renderEngagementPreview(response);
    updateEngagementMessagePreview();
    showNotice("Quantidade de alunos inativos por turma carregada com sucesso.", "success");
  } catch (error) {
    state.engagement.preview = null;
    renderTargetSummary("engagement");
    renderEngagementPreview(null);
    updateEngagementMessagePreview();
    showNotice(error.message, "error");
  } finally {
    setBusy(button, false);
  }
}

function toggleScheduleField() {
  $("#scheduleField").classList.toggle("hidden", $("#publishMode").value !== "schedule");
}

function updateAnnouncementPreview() {
  const previewCourse = firstTargetCourse("announcement");
  const titlePreview = $("#announcementPreviewTitle");
  const renderedTitle = renderCourseTemplate($("#announcementTitle").value.trim() || "Titulo do comunicado", previewCourse);
  renderAnnouncementInfoPanel();
  if (titlePreview) {
    titlePreview.textContent = previewCourse
      ? `${renderedTitle} | amostra com ${previewCourse.course_name || previewCourse.course_ref}`
      : "Selecione uma turma para gerar a amostra do comunicado.";
  }
  $("#announcementPreview").srcdoc = renderCourseTemplate($("#announcementMessage").value.trim() || "<p></p>", previewCourse) || "<p></p>";
  renderTemplateStatus("announcement");
}

function updateMessagePreview() {
  const preview = $("#messagePreviewPanel");
  if (!preview) return;
  const previewCourse = firstTargetCourse("message");
  const previewRecipient = firstMessagePreviewRecipient();
  renderTemplateStatus("message");
  renderMessageInfoPanel();
  if (!previewCourse) {
    preview.classList.add("empty-state");
    preview.innerHTML = "Selecione uma turma para gerar a amostra da caixa de entrada.";
    return;
  }
  preview.classList.remove("empty-state");
  const renderedSubject = renderCourseTemplate(
    $("#messageSubject").value.trim() || "Assunto da mensagem",
    previewCourse,
    { student_name: previewRecipient?.name || "Nome do aluno" },
  );
  const renderedBody = escapeHtml(
    renderCourseTemplate(
      $("#messageBody").value.trim() || "Mensagem da caixa de entrada.",
      previewCourse,
      { student_name: previewRecipient?.name || "Nome do aluno" },
    ),
  ).replaceAll("\n", "<br>");
  preview.innerHTML = `
    <div class="message-preview-block">
      <strong>${escapeHtml(renderedSubject)}</strong>
      <div class="compact-meta">Amostra com ${escapeHtml(previewCourse.course_name || previewCourse.course_ref || "-")} | ${escapeHtml(previewRecipient?.name || "Nome do aluno")}</div>
    </div>
    <div class="message-preview-block message-preview-html">${renderedBody}</div>
  `;
}

function updateRecurrenceSamplePreview() {
  const preview = $("#recurrenceMessagePreview");
  if (!preview) return;
  const previewCourse = firstTargetCourse("recurrence");
  renderTemplateStatus("recurrence");
  renderRecurrenceInfoPanel();
  renderRecurrencePreviewState();
  if (!previewCourse) {
    preview.classList.add("empty-state");
    preview.innerHTML = "Selecione as turmas para gerar a amostra da recorrencia.";
    return;
  }
  preview.classList.remove("empty-state");
  const renderedTitle = renderCourseTemplate($("#recurrenceTitle").value.trim() || "Titulo da recorrencia", previewCourse);
  const renderedBody = renderCourseTemplate($("#recurrenceMessage").value.trim() || "<p></p>", previewCourse);
  preview.innerHTML = `
    <div class="message-preview-block">
      <strong>${escapeHtml(renderedTitle)}</strong>
      <div class="compact-meta">Amostra com ${escapeHtml(previewCourse.course_name || previewCourse.course_ref || "-")}</div>
    </div>
    <div class="message-preview-block message-preview-html">${renderedBody}</div>
  `;
}

function updateRecurrenceEditSamplePreview() {
  const preview = $("#recurrenceEditMessagePreview");
  if (!preview) return;
  const previewCourse = firstTargetCourse("recurrenceEdit");
  renderTemplateStatus("recurrenceEdit");
  renderRecurrenceEditInfoPanel();
  renderRecurrenceEditPreviewState();
  if (!previewCourse) {
    preview.classList.add("empty-state");
    preview.innerHTML = "Selecione as turmas para gerar a amostra da edicao.";
    return;
  }
  preview.classList.remove("empty-state");
  const renderedTitle = renderCourseTemplate($("#recurrenceEditTitle").value.trim() || "Titulo da recorrencia", previewCourse);
  const renderedBody = renderCourseTemplate($("#recurrenceEditMessage").value.trim() || "<p></p>", previewCourse);
  preview.innerHTML = `
    <div class="message-preview-block">
      <strong>${escapeHtml(renderedTitle)}</strong>
      <div class="compact-meta">Amostra com ${escapeHtml(previewCourse.course_name || previewCourse.course_ref || "-")}</div>
    </div>
    <div class="message-preview-block message-preview-html">${renderedBody}</div>
  `;
}

function updateEngagementMessagePreview() {
  const preview = $("#engagementMessagePreview");
  if (!preview) return;
  renderTemplateStatus("engagement");
  const sampleRecipient = firstEngagementPreviewRecipient();
  const sampleCourse = sampleRecipient
    ? findCourseByRef(sampleRecipient.course_ref || sampleRecipient.course_id)
    : firstTargetCourse("engagement");
  if (!sampleCourse) {
    preview.classList.add("empty-state");
    preview.innerHTML = "Selecione as turmas, carregue o alvo e gere a amostra da mensagem para inativos.";
    syncCollapsibleCards();
    return;
  }
  preview.classList.remove("empty-state");
  const renderedSubject = renderCourseTemplate(
    $("#engagementSubject").value.trim() || "Acompanhamento de acesso ao curso",
    sampleCourse,
    {
      student_name: sampleRecipient?.student_name || "Nome do aluno",
    },
  );
  const renderedBody = escapeHtml(
    renderCourseTemplate(
      $("#engagementMessage").value.trim() || "Ola {{student_name}}, estamos acompanhando sua atividade no curso {{course_name}}.",
      sampleCourse,
      {
        student_name: sampleRecipient?.student_name || "Nome do aluno",
      },
    ),
  ).replaceAll("\n", "<br>");
  preview.innerHTML = `
    <div class="message-preview-block">
      <strong>${escapeHtml(renderedSubject)}</strong>
      <div class="compact-meta">Amostra com ${escapeHtml(sampleRecipient?.student_name || "Nome do aluno")} | ${escapeHtml(sampleCourse.course_name || sampleCourse.course_ref || "-")}</div>
    </div>
    <div class="message-preview-block message-preview-html">${renderedBody}</div>
  `;
  syncCollapsibleCards();
}

function updateAttachmentMeta(event) {
  const input = event?.target;
  if (!input) return;
  const file = input.files?.[0] || null;
  if (input.id === "announcementAttachment") {
    $("#announcementAttachmentMeta").textContent = file
      ? `${file.name} | ${formatFileSize(file.size)}`
      : "O Canvas aceita o anexo direto na criacao do comunicado.";
    renderAnnouncementInfoPanel();
  }
  if (input.id === "messageAttachment") {
    $("#messageAttachmentMeta").textContent = file
      ? `${file.name} | ${formatFileSize(file.size)}`
      : "O arquivo sera enviado para o Canvas e reaproveitado no lote da caixa de entrada.";
    renderMessageInfoPanel();
  }
}

function formatFileSize(bytes) {
  const size = Number(bytes || 0);
  if (!size) return "0 B";
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function firstReviewCourse(courses) {
  return (courses || []).find((item) => item.status === "ok") || courses?.[0] || null;
}

function firstTargetCourse(kind) {
  const groupsCourses = selectedGroups(kind).flatMap((group) => group.courses || []);
  const directCourses = selectedCourses(kind);
  const pool = state[kind]?.mode === "courses" ? directCourses : groupsCourses;
  return pool[0] || null;
}

function firstMessagePreviewRecipient() {
  return state.message.previewRecipients?.[0] || null;
}

function firstEngagementPreviewRecipient() {
  return state.engagement.preview?.items?.[0] || null;
}

function findCourseByRef(ref) {
  if (!ref) return null;
  const normalized = String(ref);
  const fromRegistered = state.registeredCourses.find((course) => String(course.course_ref) === normalized);
  if (fromRegistered) return fromRegistered;
  const fromGroups = state.groups.flatMap((group) => group.courses || []).find((course) => String(course.course_ref) === normalized);
  if (fromGroups) return fromGroups;
  return state.engagement.preview?.courses?.find((course) => String(course.course_ref || course.course_id) === normalized) || null;
}

function renderCourseTemplate(template, course, extraContext = {}) {
  const context = {
    course_name: course?.course_name || "Nome da disciplina",
    ...extraContext,
  };
  let rendered = String(template || "");
  Object.entries(context).forEach(([key, value]) => {
    rendered = rendered.replace(new RegExp(`{{\\s*${key}\\s*}}`, "g"), String(value || ""));
  });
  return rendered;
}

function buildMultipartPayload(payload, fileInputSelector) {
  const formData = new FormData();
  formData.append("payload_json", JSON.stringify(payload));
  const file = $(fileInputSelector)?.files?.[0];
  if (file) {
    formData.append("attachment", file);
  }
  return formData;
}

async function submitAnnouncementJob(event) {
  event.preventDefault();
  const button = $("#announcementForm button[type='submit']");
  setBusy(button, true, "Revisando...");
  hideNotice();
  clearFieldValidation();
  try {
    if (!validateAnnouncementForm()) return;
    const requestBody = buildAnnouncementRequestBody();
    const response = await apiFetch("/api/announcements/preflight", {
      method: "POST",
      body: buildMultipartPayload(requestBody, "#announcementAttachment"),
    });
    openSendReviewModal("announcement", {
      ...response,
      request: {
        ...requestBody,
        attachment_name: $("#announcementAttachment").files?.[0]?.name || "",
      },
    });
  } catch (error) {
    showNotice(error.message, "error");
  } finally {
    setBusy(button, false);
  }
}

async function submitMessageJob(event) {
  event.preventDefault();
  const button = $("#messageForm button[type='submit']");
  setBusy(button, true, "Revisando...");
  hideNotice();
  clearFieldValidation();
  try {
    if (!validateMessageForm()) return;
    const requestBody = buildMessageRequestBody();
    const response = await apiFetch("/api/messages/recipients", {
      method: "POST",
      body: requestBody,
    });
    state.message.previewRecipients = Array.isArray(response.items) ? response.items : [];
    updateMessagePreview();
    openSendReviewModal("message", {
      ...response,
      request: {
        ...requestBody,
        attachment_name: $("#messageAttachment").files?.[0]?.name || "",
      },
      summary: {
        total_students_found: response.total_students_found || 0,
        unique_recipients: response.unique_recipients || 0,
      },
    });
  } catch (error) {
    showNotice(error.message, "error");
  } finally {
    setBusy(button, false);
  }
}

async function submitEngagementJob(event) {
  event.preventDefault();
  const button = $("#engagementForm button[type='submit']");
  setBusy(button, true, "Revisando...");
  hideNotice();
  clearFieldValidation();
  try {
    if (!validateEngagementForm()) return;
    const requestBody = buildEngagementRequestBody();
    const response = await apiFetch("/api/engagement/inactive-targets", {
      method: "POST",
      body: {
        ...getConnectionPayload(),
        ...getTargetPayload("engagement"),
        criteria_mode: $("#engagementCriteriaMode").value,
        criteria_config: collectEngagementCriteriaConfig(),
      },
    });
    state.engagement.preview = response;
    renderTargetSummary("engagement");
    renderEngagementPreview(response);
    openSendReviewModal("engagement", {
      ...response,
      request: requestBody,
    });
  } catch (error) {
    showNotice(error.message, "error");
  } finally {
    setBusy(button, false);
  }
}

async function confirmReviewedSend() {
  const button = $("#confirmSendReviewBtn");
  setBusy(button, true, "Enviando...");
  hideSendReviewNotice();
  try {
    if (state.review.kind === "announcement") {
      await executeAnnouncementJob();
    } else if (state.review.kind === "message") {
      await executeMessageJob();
    } else if (state.review.kind === "engagement") {
      await executeEngagementJob();
    }
    closeSendReviewModal();
  } catch (error) {
    showSendReviewNotice(error.message, "error");
  } finally {
    setBusy(button, false);
  }
}

async function executeAnnouncementJob() {
  const response = await apiFetch("/api/announcements/jobs", {
    method: "POST",
    body: buildMultipartPayload(buildAnnouncementRequestBody(), "#announcementAttachment"),
  });
  renderAnnouncementJob(response.job);
  startPolling(response.job.id, "announcement");
  showNotice("Lote de comunicados enfileirado.", "success");
}

async function executeMessageJob() {
  const response = await apiFetch("/api/messages/jobs", {
    method: "POST",
    body: buildMultipartPayload(buildMessageRequestBody(), "#messageAttachment"),
  });
  renderMessageJob(response.job);
  startPolling(response.job.id, "message");
  showNotice("Lote de caixa de entrada enfileirado.", "success");
}

async function executeEngagementJob() {
  const response = await apiFetch("/api/engagement/jobs", {
    method: "POST",
    body: buildEngagementRequestBody(),
  });
  renderEngagementJob(response.job);
  startPolling(response.job.id, "engagement");
  showNotice("Lote de mensagens para alunos inativos enfileirado.", "success");
}

async function submitRecurrence(event) {
  event.preventDefault();
  const button = $("#recurrenceForm button[type='submit']");
  hideNotice();
  clearFieldValidation();
  try {
    if (!validateRecurrenceForm()) return;
    const requestBody = buildRecurrenceRequestBody();
    if (!recurrencePreviewIsCurrent("recurrence", requestBody)) {
      showNotice("Clique em prever datas novamente antes de criar a recorrencia. A revisao precisa estar atualizada.", "error");
      focusField("#previewRecurrenceBtn");
      return;
    }
    openRecurrenceReviewModal("create", requestBody, state.recurrence.preview);
  } catch (error) {
    showNotice(error.message, "error");
  }
}

async function submitRecurrenceEdit(event) {
  event.preventDefault();
  hideRecurrenceEditNotice();
  clearFieldValidation();
  try {
    if (!validateRecurrenceEditForm()) return;
    const requestBody = buildRecurrenceEditRequestBody();
    if (!recurrencePreviewIsCurrent("recurrenceEdit", requestBody)) {
      showRecurrenceEditNotice("Clique em prever impacto novamente antes de salvar. A revisao precisa estar atualizada.", "error");
      focusField("#previewRecurrenceEditBtn");
      return;
    }
    openRecurrenceReviewModal("edit", requestBody, state.recurrenceEdit.preview);
  } catch (error) {
    showRecurrenceEditNotice(error.message, "error");
  }
}

async function confirmRecurrenceReview() {
  const button = $("#confirmRecurrenceReviewBtn");
  setBusy(button, true, state.recurrenceReview.mode === "edit" ? "Salvando..." : "Criando...");
  hideRecurrenceReviewNotice();
  try {
    const { mode, payload } = state.recurrenceReview;
    if (!mode || !payload) {
      closeRecurrenceReviewModal();
      return;
    }
    if (mode === "create") {
      const response = await apiFetch("/api/announcement-recurrences", {
        method: "POST",
        body: payload,
      });
      state.recurrence.preview = null;
      state.recurrence.previewSignature = "";
      await loadConfig();
      renderAll();
      closeRecurrenceReviewModal();
      showNotice(
        `Recorrencia criada com ${response.created_count || 0} aviso(s) agendado(s) no Canvas.`,
        response.failure_count ? "info" : "success",
      );
      return;
    }
    const recurrenceId = payload.recurrence_id;
    const response = await apiFetch(`/api/announcement-recurrences/${recurrenceId}`, {
      method: "PUT",
      body: payload,
    });
    state.recurrenceEdit.preview = null;
    state.recurrenceEdit.previewSignature = "";
    await loadConfig();
    renderAll();
    closeRecurrenceReviewModal();
    closeRecurrenceEditModal();
    showNotice(
      `Recorrencia atualizada. ${response.created_count || 0} aviso(s) futuro(s) criado(s) e ${response.replaced_count || 0} ajustado(s).`,
      response.failure_count ? "info" : "success",
    );
  } catch (error) {
    showRecurrenceReviewNotice(error.message, "error");
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
      if (kind === "engagement") renderEngagementJob(job);
      if (["completed", "failed"].includes(job.status)) {
        stopPolling(kind);
        await loadConfig();
        await loadHistory();
        await loadAnalytics();
        renderAll();
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
    { label: "Turma", format: (row) => escapeHtml(row.course_name || "-") },
    { label: "Status", format: (row) => statusChip(row.status) },
    { label: "ID", format: (row) => escapeHtml(String(row.announcement_id || "-")) },
    { label: "Publicado", format: (row) => row.published ? "Sim" : "Nao" },
    { label: "Anexo", format: (row) => escapeHtml(row.attachment_name || "-") },
    { label: "Erro", format: (row) => escapeHtml(row.error || "-") },
  ]);
  syncCollapsibleCards();
}

function renderMessageJob(job) {
  $("#messageJobCard").innerHTML = renderJobLayout(job, [
    { label: "Turma", format: (row) => escapeHtml(row.course_name || "-") },
    { label: "Estrategia", format: (row) => escapeHtml(row.strategy_used || "-") },
    { label: "Alunos", format: (row) => escapeHtml(String(row.students_found || 0)) },
    { label: "Alvo", format: (row) => escapeHtml(String(row.recipients_targeted || 0)) },
    { label: "Enviados", format: (row) => escapeHtml(String(row.recipients_sent || 0)) },
    { label: "Anexo", format: (row) => escapeHtml(row.attachment_name || "-") },
    { label: "Status", format: (row) => statusChip(row.status) },
    { label: "Erro", format: (row) => escapeHtml(row.error || "-") },
  ]);
  syncCollapsibleCards();
}

function renderEngagementJob(job) {
  $("#engagementJobCard").innerHTML = renderJobLayout(job, [
    { label: "Turma", format: (row) => escapeHtml(row.course_name || "-") },
    { label: "Alunos", format: (row) => escapeHtml(String(row.students_found || 0)) },
    { label: "Alvo", format: (row) => escapeHtml(String(row.recipients_targeted || 0)) },
    { label: "Sem acesso", format: (row) => escapeHtml(String(row.never_accessed_matches || 0)) },
    { label: "Pendentes", format: (row) => escapeHtml(String(row.incomplete_resources_matches || 0)) },
    { label: "Sem atividade", format: (row) => escapeHtml(String(row.inactive_days_matches || 0)) },
    { label: "Enviados", format: (row) => escapeHtml(String(row.recipients_sent || 0)) },
    { label: "Status", format: (row) => statusChip(row.status) },
    { label: "Erro", format: (row) => escapeHtml(row.error || "-") },
  ]);
  syncCollapsibleCards();
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
  renderExecutiveSummary();
  renderReportMetrics();
  renderReportAnalytics();
  renderHistoryList();
  renderReportDetail();
}

function renderExecutiveSummary() {
  const executive = state.reportAnalytics?.executive || {};
  const alerts = executive.alerts || [];
  const highlights = executive.highlights || [];
  const alertsContainer = $("#reportExecutiveAlerts");
  const highlightsContainer = $("#reportExecutiveHighlights");
  if (!alertsContainer || !highlightsContainer) return;

  alertsContainer.innerHTML = alerts.length
    ? alerts.map((item) => `
      <article class="executive-alert ${escapeHtml(item.level || "info")}">
        <div class="executive-alert-head">
          <span class="executive-alert-level">${escapeHtml(alertLabel(item.level))}</span>
          <strong>${escapeHtml(item.title || "Alerta")}</strong>
        </div>
        <p>${escapeHtml(item.message || "-")}</p>
        <small>${escapeHtml(item.action || "")}</small>
      </article>
    `).join("")
    : `<div class="empty-state">Nenhum alerta executivo para o periodo atual.</div>`;

  highlightsContainer.innerHTML = highlights.length
    ? highlights.map((item) => `
      <article class="executive-highlight ${escapeHtml(item.tone || "info")}">
        <span>${escapeHtml(item.label || "Destaque")}</span>
        <strong>${escapeHtml(item.value || "-")}</strong>
        <small>${escapeHtml(item.helper || "")}</small>
      </article>
    `).join("")
    : "";
}

function renderReportMetrics() {
  const overview = state.reportAnalytics?.overview || {};
  const comparison = overview.comparison || {};
  $("#reportMetrics").innerHTML = [
    metricCard(
      "Janela atual",
      formatDateRangeCompact(overview.current_start, overview.current_end) || `${overview.days || state.reportDays || 30} dias`,
      null,
      overview.previous_start ? `Anterior: ${formatDateRangeCompact(overview.previous_start, overview.previous_end)}` : "",
    ),
    metricCard("Lotes", overview.total_jobs || 0, comparison.total_jobs),
    metricCard("Taxa de sucesso", `${formatSummaryValue(overview.success_rate || 0)}%`, comparison.success_rate),
    metricCard("Duracao media", `${formatSummaryValue(overview.avg_duration_seconds || 0)}s`, comparison.avg_duration_seconds),
    metricCard("Mensagens enviadas", overview.total_recipients_sent || 0, comparison.total_recipients_sent),
    metricCard("Comunicados criados", overview.total_announcements_created || 0, comparison.total_announcements_created),
    metricCard("Inativos", overview.total_engagement_jobs || 0, comparison.total_engagement_jobs),
    metricCard("Recorrencias ativas", overview.active_recurrences || 0, comparison.new_recurrences_created, "Ativas agora"),
  ].join("");
}

function renderReportAnalytics() {
  const container = $("#reportAnalyticsSections");
  const sections = state.reportAnalytics?.sections || {};
  const entries = Object.entries(sections);
  if (!entries.length) {
    container.innerHTML = `<div class="empty-state">Nenhum analitico disponivel para o periodo selecionado.</div>`;
    return;
  }

  container.innerHTML = entries.map(([key, section], index) => `
    <details class="report-section" ${index < 2 ? "open" : ""}>
      <summary>
        <span>${escapeHtml(section.title || toTitle(key))}</span>
        <span class="report-section-meta">${escapeHtml(String((section.items || []).length))} item(ns)</span>
      </summary>
      <div class="report-section-body">
        ${(section.items || []).length ? renderTable(reportAnalyticsColumns(key), section.items) : `<div class="empty-state">Sem dados para esta secao.</div>`}
      </div>
    </details>
  `).join("");
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
  if (kind === "engagement") {
    return [
      { label: "Turma", format: (row) => escapeHtml(row.course_name || "-") },
      { label: "Alunos", format: (row) => escapeHtml(String(row.students_found || 0)) },
      { label: "Alvo", format: (row) => escapeHtml(String(row.recipients_targeted || 0)) },
      { label: "Sem acesso", format: (row) => escapeHtml(String(row.never_accessed_matches || 0)) },
      { label: "Pendentes", format: (row) => escapeHtml(String(row.incomplete_resources_matches || 0)) },
      { label: "Sem atividade", format: (row) => escapeHtml(String(row.inactive_days_matches || 0)) },
      { label: "Enviados", format: (row) => escapeHtml(String(row.recipients_sent || 0)) },
      { label: "Status", format: (row) => statusChip(row.status) },
      { label: "Erro", format: (row) => escapeHtml(row.error || "-") },
    ];
  }
  if (kind === "message") {
    return [
      { label: "Turma", format: (row) => escapeHtml(row.course_name || "-") },
      { label: "Alunos", format: (row) => escapeHtml(String(row.students_found || 0)) },
      { label: "Alvo", format: (row) => escapeHtml(String(row.recipients_targeted || 0)) },
      { label: "Enviados", format: (row) => escapeHtml(String(row.recipients_sent || 0)) },
      { label: "Anexo", format: (row) => escapeHtml(row.attachment_name || "-") },
      { label: "Status", format: (row) => statusChip(row.status) },
      { label: "Erro", format: (row) => escapeHtml(row.error || "-") },
    ];
  }
  return [
    { label: "Turma", format: (row) => escapeHtml(row.course_name || "-") },
    { label: "ID", format: (row) => escapeHtml(String(row.announcement_id || "-")) },
    { label: "Publicado", format: (row) => row.published ? "Sim" : "Nao" },
    { label: "Anexo", format: (row) => escapeHtml(row.attachment_name || "-") },
    { label: "Status", format: (row) => statusChip(row.status) },
    { label: "Erro", format: (row) => escapeHtml(row.error || "-") },
  ];
}

function reportAnalyticsColumns(sectionKey) {
  if (sectionKey === "period_comparison") {
    return [
      { label: "Indicador", format: (row) => escapeHtml(row.metric || "-") },
      { label: "Atual", format: (row) => escapeHtml(formatSummaryValue(row.current)) },
      { label: "Anterior", format: (row) => escapeHtml(formatSummaryValue(row.previous)) },
      { label: "Delta", format: (row) => deltaPill(row.delta, row.delta_percent) },
    ];
  }
  if (sectionKey === "operational") {
    return [
      { label: "Tipo", format: (row) => escapeHtml(row.kind || "-") },
      { label: "Lotes atuais", format: (row) => escapeHtml(String(row.current_jobs || 0)) },
      { label: "Lotes anteriores", format: (row) => escapeHtml(String(row.previous_jobs || 0)) },
      { label: "Delta", format: (row) => deltaPill(row.delta_jobs) },
      { label: "Taxa atual", format: (row) => escapeHtml(`${formatSummaryValue(row.current_success_rate || 0)}%`) },
      { label: "Taxa anterior", format: (row) => escapeHtml(`${formatSummaryValue(row.previous_success_rate || 0)}%`) },
      { label: "Dry run", format: (row) => `${escapeHtml(String(row.current_dry_run || 0))}<div class="subtle">ant.: ${escapeHtml(String(row.previous_dry_run || 0))}</div>` },
    ];
  }
  if (sectionKey === "daily_volume") {
    return [
      { label: "Data", format: (row) => escapeHtml(row.date || "-") },
      { label: "Comunicados", format: (row) => escapeHtml(String(row.announcement || 0)) },
      { label: "Mensagens", format: (row) => escapeHtml(String(row.message || 0)) },
      { label: "Inativos", format: (row) => escapeHtml(String(row.engagement || 0)) },
      { label: "Concluidos", format: (row) => escapeHtml(String(row.completed || 0)) },
      { label: "Falhas", format: (row) => escapeHtml(String(row.failed || 0)) },
    ];
  }
  if (sectionKey === "top_courses") {
    return [
      { label: "Curso", format: (row) => escapeHtml(row.course_name || "-") },
      { label: "Execucoes", format: (row) => `${escapeHtml(String(row.current_runs || 0))}<div class="subtle">ant.: ${escapeHtml(String(row.previous_runs || 0))}</div>` },
      { label: "Delta exec.", format: (row) => deltaPill(row.delta_runs) },
      { label: "Sucesso", format: (row) => `${escapeHtml(String(row.current_success || 0))}<div class="subtle">ant.: ${escapeHtml(String(row.previous_success || 0))}</div>` },
      { label: "Falha", format: (row) => `${escapeHtml(String(row.current_failure || 0))}<div class="subtle">ant.: ${escapeHtml(String(row.previous_failure || 0))}</div>` },
      { label: "Mensagens", format: (row) => `${escapeHtml(String(row.current_recipients_sent || 0))}<div class="subtle">ant.: ${escapeHtml(String(row.previous_recipients_sent || 0))}</div>` },
      { label: "Delta msg.", format: (row) => deltaPill(row.delta_recipients_sent) },
    ];
  }
  if (sectionKey === "top_groups") {
    return [
      { label: "Grupo", format: (row) => `${escapeHtml(row.group_name || "-")}<div class="subtle mono">${escapeHtml(String(row.group_id || "-"))}</div>` },
      { label: "Execucoes", format: (row) => `${escapeHtml(String(row.current_jobs || 0))}<div class="subtle">ant.: ${escapeHtml(String(row.previous_jobs || 0))}</div>` },
      { label: "Delta", format: (row) => deltaPill(row.delta_jobs) },
    ];
  }
  if (sectionKey === "active_recurrences") {
    return [
      { label: "Recorrencia", format: (row) => `${escapeHtml(row.name || "-")}<div class="subtle mono">${escapeHtml(String(row.recurrence_id || "-"))}</div>` },
      { label: "Avisos", format: (row) => escapeHtml(String(row.total_items || 0)) },
      { label: "Futuros", format: (row) => escapeHtml(String(row.future_items || 0)) },
      { label: "Cancelados", format: (row) => escapeHtml(String(row.canceled_items || 0)) },
    ];
  }
  if (sectionKey === "upcoming_recurrences") {
    return [
      { label: "Recorrencia", format: (row) => `${escapeHtml(row.name || "-")}<div class="subtle">${escapeHtml(row.title || "-")}</div>` },
      { label: "Primeira", format: (row) => escapeHtml(formatDateTime(row.first_publish_at)) },
      { label: "Ocorrencias", format: (row) => escapeHtml(String(row.occurrence_count || 0)) },
      { label: "Futuros", format: (row) => escapeHtml(String(row.future_items || 0)) },
    ];
  }
  if (sectionKey === "recent_failures") {
    return [
      { label: "Data", format: (row) => escapeHtml(formatDate(row.created_at)) },
      { label: "Tipo", format: (row) => escapeHtml(row.kind || "-") },
      { label: "Curso", format: (row) => escapeHtml(row.course_name || "-") },
      { label: "Status", format: (row) => statusChip(row.status || "error") },
      { label: "Erro", format: (row) => escapeHtml(row.error || "-") },
    ];
  }
  return [
    { label: "Chave", format: (_row) => "-" },
  ];
}

const TABLE_COLUMN_HELP = {
  Turma: "Nome da disciplina ou curso no Canvas que entrou no lote ou na analise.",
  Curso: "Curso do Canvas relacionado ao registro exibido.",
  Recorrencia: "Nome interno da base recorrente salva no painel.",
  Grupo: "Grupo local de turmas salvo no painel.",
  Prioridade: "Pontuacao interna do painel para destacar onde agir primeiro.",
  Alunos: "Quantidade total de alunos encontrados no curso para aquele contexto.",
  Alvo: "Quantidade de alunos ou registros que realmente entram no criterio atual.",
  Cobertura: "Percentual do curso que entrou no alvo, calculado sobre alunos encontrados.",
  "Sem acesso": "Aluno com page_views = 0 e participations = 0 no analytics do Canvas. Mesmo assim a mensagem pode chegar pela Inbox do Canvas e por email so se a notificacao estiver ativa.",
  Pendentes: "Quantidade de alunos com requisitos de modulos ainda nao concluidos no Canvas.",
  "Sem atividade": "Quantidade de alunos cujo last_activity_at ficou alem do limite configurado.",
  "Baixa atividade": "Quantidade de alunos com total_activity_time abaixo do limite configurado.",
  Modulo: "Indica se o curso tem requisitos de modulos configurados para medir pendencias.",
  "Status API": "Mostra se analytics, progresso de modulos e atividade de enrollments vieram disponiveis do Canvas.",
  Aluno: "Nome do aluno que entrou no preview ou no lote.",
  Acessos: "Visualizacoes e participacoes retornadas pelo analytics do Canvas para o aluno.",
  Atividade: "Ultima atividade registrada e tempo total de atividade acumulado pelo Canvas.",
  Recursos: "Quantidade de requisitos concluidos sobre o total de requisitos configurados no curso.",
  Motivo: "Resumo do por que o aluno entrou no filtro atual de inatividade.",
  Estrategia: "Forma usada para enviar a mensagem: por usuarios ou por contexto da turma.",
  Enviados: "Quantidade que o painel conseguiu enviar de fato naquele registro.",
  Anexo: "Arquivo anexado ao comunicado ou a mensagem daquele lote, quando existir.",
  Publicado: "Indica se o aviso foi publicado no Canvas ou ficou como rascunho/agendado.",
  Status: "Estado final do processamento daquele item no painel.",
  Erro: "Mensagem retornada pelo painel ou pelo Canvas quando houve falha.",
  ID: "Identificador retornado pelo Canvas para o recurso criado.",
  Indicador: "Metrica agregada usada no comparativo entre periodos.",
  Atual: "Valor do periodo atual.",
  Anterior: "Valor do periodo anterior equivalente.",
  Delta: "Diferenca entre o periodo atual e o periodo anterior equivalente.",
  Tipo: "Tipo de job, evento ou operacao registrada.",
  "Lotes atuais": "Quantidade de lotes no periodo atual.",
  "Lotes anteriores": "Quantidade de lotes no periodo anterior equivalente.",
  "Taxa atual": "Taxa de sucesso do periodo atual.",
  "Taxa anterior": "Taxa de sucesso do periodo anterior equivalente.",
  "Dry run": "Quantidade de execucoes em modo teste, sem envio real.",
  Data: "Data consolidada do registro ou do agregado exibido.",
  Comunicados: "Quantidade de comunicados processados no periodo ou na data.",
  Mensagens: "Quantidade de mensagens de Inbox processadas no periodo ou na data.",
  Inativos: "Quantidade de execucoes do modulo de alunos inativos.",
  Concluidos: "Quantidade de jobs concluídos com sucesso.",
  Falhas: "Quantidade de jobs que terminaram com erro.",
  Execucoes: "Quantidade de execucoes para aquele curso ou grupo.",
  "Delta exec.": "Variacao de execucoes em relacao ao periodo anterior.",
  Sucesso: "Quantidade de execucoes ou envios bem-sucedidos.",
  Falha: "Quantidade de execucoes ou envios com falha.",
  "Delta msg.": "Variacao no volume de mensagens enviadas em relacao ao periodo anterior.",
  Primeira: "Primeira publicacao prevista ou registrada para a recorrencia.",
  Ocorrencias: "Quantidade total de repeticoes configuradas na recorrencia.",
  Futuros: "Quantidade de itens futuros ainda pendentes no Canvas.",
  Cancelados: "Quantidade de itens cancelados no Canvas ou no controle local.",
};

function renderTableHeader(column) {
  const help = column.help || TABLE_COLUMN_HELP[column.label] || "";
  return `
    <div class="table-head-wrap">
      <span>${escapeHtml(column.label)}</span>
      ${help ? `
        <details class="table-help">
          <summary aria-label="Explicar ${escapeHtml(column.label)}">?</summary>
          <div class="table-help-popover">${escapeHtml(help)}</div>
        </details>
      ` : ""}
    </div>
  `;
}

function renderTable(columns, rows) {
  return `
    <div class="table-wrap">
      <table>
        <thead><tr>${columns.map((column) => `<th>${renderTableHeader(column)}</th>`).join("")}</tr></thead>
        <tbody>${rows.map((row) => `<tr>${columns.map((column) => `<td>${column.format(row)}</td>`).join("")}</tr>`).join("")}</tbody>
      </table>
    </div>
  `;
}

function metricCard(label, value, comparison = null, helper = "") {
  const comparisonHtml = comparison ? `<small class="metric-trend ${escapeHtml(comparison.direction || "flat")}">${escapeHtml(renderMetricTrend(comparison))}</small>` : "";
  const helperHtml = helper ? `<small class="metric-helper">${escapeHtml(helper)}</small>` : "";
  return `<div class="overview-card"><span>${escapeHtml(label)}</span><strong>${escapeHtml(String(value))}</strong>${helperHtml}${comparisonHtml}</div>`;
}

function timelinePill(label, value, tone = "default") {
  if (!value) return "";
  return `<span class="timeline-pill ${escapeHtml(tone)}">${escapeHtml(label)}: ${escapeHtml(formatDateTime(value))}</span>`;
}

function recurrenceStatusLabel(item) {
  if (item.last_error || Number(item.error_items || 0) > 0) return "Com alerta";
  if (!item.is_active && (item.canceled_at || Number(item.canceled_items || 0) > 0)) return "Cancelada";
  if (!item.is_active) return "Inativa";
  if (Number(item.future_items || 0) > 0) return "Ativa";
  return "Sem futuros";
}

function recurrenceChangeLabel(item) {
  const createdAt = parseDateSafe(item.created_at);
  const updatedAt = parseDateSafe(item.updated_at);
  if (createdAt && updatedAt && Math.abs(updatedAt.getTime() - createdAt.getTime()) < 60_000 && isRecentWithinDays(createdAt, 3)) {
    return "Nova recorrencia";
  }
  if (updatedAt && createdAt && updatedAt.getTime() - createdAt.getTime() >= 60_000 && isRecentWithinDays(updatedAt, 3)) {
    return "Ajustada recentemente";
  }
  return "";
}

function parseDateSafe(value) {
  if (!value) return null;
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function isRecentWithinDays(value, days) {
  const parsed = value instanceof Date ? value : parseDateSafe(value);
  if (!parsed) return false;
  const now = new Date();
  const threshold = now.getTime() - Number(days || 0) * 24 * 60 * 60 * 1000;
  return parsed.getTime() >= threshold;
}

function dayOffsetFromNow(value) {
  const parsed = parseDateSafe(value);
  if (!parsed) return 0;
  const now = new Date();
  const startNow = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startTarget = new Date(parsed.getFullYear(), parsed.getMonth(), parsed.getDate());
  return Math.round((startTarget.getTime() - startNow.getTime()) / (24 * 60 * 60 * 1000));
}

function classifyAgendaDay(value) {
  const offset = dayOffsetFromNow(value);
  if (offset <= 0) return "today";
  if (offset === 1) return "tomorrow";
  if (offset <= 6) return "week";
  return "future";
}

function formatRelativeAgendaDay(value) {
  const offset = dayOffsetFromNow(value);
  if (offset <= 0) return "Hoje";
  if (offset === 1) return "Amanha";
  if (offset === 2) return "Em 2 dias";
  if (offset <= 6) return `Em ${offset} dias`;
  if (offset <= 13) return "Na proxima semana";
  return `Em ${offset} dias`;
}

function formatAgendaGroupLabel(date, formatter, dayOffset) {
  if (dayOffset <= 0) return `Hoje | ${formatter.format(date)}`;
  if (dayOffset === 1) return `Amanha | ${formatter.format(date)}`;
  return formatter.format(date);
}

function deltaPill(delta, deltaPercent = null) {
  const numericDelta = Number(delta || 0);
  const direction = numericDelta > 0 ? "up" : numericDelta < 0 ? "down" : "flat";
  const sign = numericDelta > 0 ? "+" : "";
  const percentPart = deltaPercent === null || deltaPercent === undefined ? "" : ` <span>${sign}${formatSummaryValue(deltaPercent)}%</span>`;
  return `<span class="delta-pill ${escapeHtml(direction)}">${escapeHtml(`${sign}${formatSummaryValue(numericDelta)}`)}${percentPart}</span>`;
}

function priorityPill(level, score = null) {
  const normalized = String(level || "baixa").toLowerCase();
  const labelMap = {
    critica: "Critica",
    alta: "Alta",
    media: "Media",
    baixa: "Baixa",
  };
  const scorePart = score === null || score === undefined ? "" : ` <span>${escapeHtml(String(score))}</span>`;
  return `<span class="priority-pill ${escapeHtml(normalized)}">${escapeHtml(labelMap[normalized] || normalized)}${scorePart}</span>`;
}

function renderMetricTrend(comparison) {
  if (!comparison) return "";
  const current = Number(comparison.current || 0);
  const previous = Number(comparison.previous || 0);
  const delta = Number(comparison.delta || 0);
  const sign = delta > 0 ? "+" : "";
  if (comparison.baseline_empty && previous === 0 && current > 0) {
    return `${sign}${formatSummaryValue(delta)} sobre base zero`;
  }
  const deltaText = `${sign}${formatSummaryValue(delta)}`;
  const percentText = comparison.delta_percent === null || comparison.delta_percent === undefined
    ? ""
    : ` (${sign}${formatSummaryValue(comparison.delta_percent)}%)`;
  return `${deltaText} vs ${formatSummaryValue(previous)} anterior${percentText}`;
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
    <div class="dashboard-item"><strong>Banco de dados</strong><div class="compact-meta mono">${escapeHtml(settings.database_backend || "-")} | ${escapeHtml(settings.database_url_masked || "-")}</div></div>
    <div class="dashboard-item"><strong>Retry e timeout</strong><div class="compact-meta">${escapeHtml(String(settings.retry_max_attempts || 0))} tentativa(s) | atraso base ${escapeHtml(String(settings.retry_base_delay || 0))}s | timeout ${escapeHtml(String(settings.request_timeout || 0))}s</div></div>
    <div class="dashboard-item"><strong>Arquivo .env</strong><div class="compact-meta mono">${escapeHtml(settings.env_file_path || "-")}</div></div>
  `;
}

function renderEnvEditorState() {
  $("#envPath").textContent = state.config?.env_file_path || "-";
  const shell = $("#envEditorShell");
  const editor = $("#envEditor");
  const status = $("#envVisibilityStatus");
  const saveButton = $("#saveEnvBtn");
  if (!shell || !editor || !status || !saveButton) return;

  shell.classList.toggle("is-masked", !state.envVisible);
  editor.disabled = !state.envVisible;
  saveButton.disabled = !state.envVisible;

  if (state.envVisible) {
    status.textContent = "Visivel por 10s";
  } else {
    status.textContent = "Oculto";
    editor.value = "";
    editor.placeholder = "Clique em revelar para visualizar por 10 segundos.";
  }
}

function clearEnvRevealTimer() {
  if (state.envRevealTimer) {
    window.clearTimeout(state.envRevealTimer);
    state.envRevealTimer = null;
  }
}

function hideEnvFile() {
  clearEnvRevealTimer();
  state.envVisible = false;
  state.envLoaded = false;
  state.envContent = "";
  renderEnvEditorState();
}

async function revealEnvFileTemporarily() {
  const button = $("#revealEnvBtn");
  setBusy(button, true, "Revelando...");
  try {
    await loadEnvFile(true);
    state.envVisible = true;
    $("#envEditor").value = state.envContent;
    renderEnvEditorState();
    clearEnvRevealTimer();
    state.envRevealTimer = window.setTimeout(() => {
      hideEnvFile();
    }, 10000);
    showNotice("Conteudo do .env revelado por 10 segundos.", "info");
  } catch (error) {
    showNotice(error.message, "error");
  } finally {
    setBusy(button, false);
  }
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
    if (!state.envVisible) {
      showNotice("Revele o .env antes de editar ou salvar.", "error");
      return;
    }
    const response = await apiFetch("/api/settings/env", { method: "PUT", body: { content: $("#envEditor").value } });
    state.envLoaded = true;
    state.envContent = response.content || "";
    $("#envPath").textContent = response.path || "-";
    await loadConfig();
    renderAll();
    showNotice("Arquivo .env salvo com sucesso.", "success");
    hideEnvFile();
  } catch (error) {
    showNotice(error.message, "error");
  } finally {
    setBusy(button, false);
  }
}

function renderWipeDatabaseResult(payload = null) {
  const target = $("#wipeDatabaseResult");
  if (!target) return;
  if (!payload) {
    target.textContent = "";
    target.classList.add("hidden");
    return;
  }

  const counts = payload.deleted_counts || {};
  const fragments = Object.entries(counts)
    .map(([key, value]) => `${toTitle(key)}: ${value}`)
    .join(" | ");
  target.textContent = `${payload.message || "Banco limpo com sucesso."}${fragments ? ` ${fragments}` : ""}`;
  target.classList.remove("hidden");
}

async function wipeDatabase() {
  const button = $("#wipeDatabaseBtn");
  const confirmation = ($("#wipeDatabaseConfirm").value || "").trim().toUpperCase();
  hideNotice();
  renderWipeDatabaseResult(null);

  if (confirmation !== "EXCLUIR") {
    markInvalid("#wipeDatabaseConfirm");
    focusField("#wipeDatabaseConfirm");
    showNotice("Digite EXCLUIR para apagar todo o banco do painel.", "error");
    return;
  }

  setBusy(button, true, "Apagando...");
  try {
    const response = await apiFetch("/api/settings/database/wipe", {
      method: "POST",
      body: { confirmation_text: confirmation },
    });
    stopPolling("announcement");
    stopPolling("message");
    stopPolling("engagement");
    state.connectionSnapshot = null;
    state.selectedReportId = null;
    state.history = [];
    state.groups = [];
    state.registeredCourses = [];
    state.recurrences = [];
    state.recurrence.preview = null;
    state.reportAnalytics = null;
    state.engagement.preview = null;
    $("#wipeDatabaseConfirm").value = "";
    await loadConfig();
    await loadHistory();
    await loadAnalytics();
    renderAll();
    renderWipeDatabaseResult(response);
    showNotice("Banco SQLite do painel apagado com sucesso.", "success");
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

function formatDateTime(value) {
  return formatDate(value);
}

function formatDateRangeCompact(startValue, endValue) {
  if (!startValue || !endValue) return "";
  const start = new Date(startValue);
  const end = new Date(endValue);
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return "";
  const formatter = new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "short",
  });
  return `${formatter.format(start)} - ${formatter.format(end)}`;
}

function formatLocalDateTimeInput(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  return `${year}-${month}-${day}T${hours}:${minutes}`;
}

function formatLocalDateTimeLabel(value) {
  if (!value) return "-";
  const isoValue = String(value).includes("T") && !String(value).includes("Z")
    ? `${value}:00`
    : value;
  const date = new Date(isoValue);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
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

function formatEngagementCriteria(value) {
  const map = {
    never_accessed: "Somente sem acesso nenhum",
    incomplete_resources: "Somente com recursos pendentes",
    never_accessed_or_incomplete_resources: "Sem acesso nenhum ou com recursos pendentes",
  };
  return map[value] || value || "-";
}

function alertLabel(value) {
  const map = {
    success: "Estavel",
    info: "Acompanhar",
    warning: "Atencao",
    error: "Critico",
  };
  return map[value] || "Alerta";
}
