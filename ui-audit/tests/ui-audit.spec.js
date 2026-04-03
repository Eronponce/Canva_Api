const fs = require("fs");
const path = require("path");
const { test, expect } = require("@playwright/test");
const AxeBuilder = require("@axe-core/playwright").default;
const { attachMockApi } = require("./mock-api");

const auditSummary = [];
let mockApiState;
const unexpectedApiCalls = [];

function ensureDir(dirPath) {
  fs.mkdirSync(dirPath, { recursive: true });
}

async function collectOverflow(page, scopeSelector) {
  return page.evaluate((scope) => {
    const root = document.querySelector(scope);
    if (!root) return { pageOverflowX: 0, offenders: [] };
    const offenders = [];
    const viewportWidth = window.innerWidth;
    root.querySelectorAll("*").forEach((element) => {
      const style = window.getComputedStyle(element);
      if (style.display === "none" || style.visibility === "hidden") return;
      const rect = element.getBoundingClientRect();
      if (rect.width <= 0 || rect.height <= 0) return;
      const overflowX = element.scrollWidth - element.clientWidth;
      const offscreenRight = rect.right - viewportWidth;
      const offscreenLeft = rect.left < 0 ? Math.abs(rect.left) : 0;
      if (overflowX > 4 || offscreenRight > 4 || offscreenLeft > 4) {
        offenders.push({
          tag: element.tagName.toLowerCase(),
          id: element.id || "",
          className: String(element.className || "").slice(0, 120),
          text: (element.textContent || "").trim().slice(0, 120),
          overflowX,
          offscreenRight,
          offscreenLeft,
          width: rect.width,
        });
      }
    });
    return {
      pageOverflowX: Math.max(0, document.documentElement.scrollWidth - viewportWidth),
      offenders: offenders.slice(0, 12),
    };
  }, scopeSelector);
}

async function runAxe(page, scopeSelector) {
  const builder = new AxeBuilder({ page })
    .include(scopeSelector)
    .disableRules(["region", "landmark-one-main", "page-has-heading-one"]);
  const results = await builder.analyze();
  return results.violations.map((violation) => ({
    id: violation.id,
    impact: violation.impact,
    description: violation.description,
    help: violation.help,
    nodes: violation.nodes.length,
  }));
}

async function captureAudit(page, testInfo, name, scopeSelector, kind) {
  const screenshotDir = path.join(testInfo.outputDir, "screens");
  ensureDir(screenshotDir);
  const screenshotPath = path.join(screenshotDir, `${name}.png`);
  const target = page.locator(scopeSelector);
  await expect(target).toBeVisible();
  await target.screenshot({ path: screenshotPath });
  const overflow = await collectOverflow(page, scopeSelector);
  const accessibility = await runAxe(page, scopeSelector);
  const entry = {
    name,
    kind,
    scopeSelector,
    screenshotPath,
    pageOverflowX: overflow.pageOverflowX,
    overflowOffenders: overflow.offenders,
    accessibilityViolations: accessibility,
  };
  auditSummary.push(entry);
  await testInfo.attach(`${name}.json`, {
    body: JSON.stringify(entry, null, 2),
    contentType: "application/json",
  });
  if (fs.existsSync(screenshotPath)) {
    await testInfo.attach(`${name}.png`, {
      path: screenshotPath,
      contentType: "image/png",
    });
  }
  if (overflow.pageOverflowX > 4 || accessibility.length) {
    // eslint-disable-next-line no-console
    console.log(`[ui-audit] ${name}`, JSON.stringify({
      overflowX: overflow.pageOverflowX,
      offenders: overflow.offenders,
      accessibility,
    }, null, 2));
  }
}

async function openTab(page, id) {
  await page.click(`.tab-button[data-tab="${id}"]`);
  const panel = page.locator(`#tab-${id}`);
  await expect(panel).toHaveClass(/active/);
  return panel;
}

async function checkFirstPickerItem(page, pickerId) {
  const checkbox = page.locator(`#${pickerId} input[data-picker-checkbox="${pickerId}"]`).first();
  await expect(checkbox).toBeVisible();
  await checkbox.check();
  await page.locator(`#${pickerId} .picker-root`).press("Tab");
}

async function fillAnnouncementForm(page) {
  await checkFirstPickerItem(page, "announcementGroupPicker");
  await page.fill("#announcementTitle", "Aviso semanal | {{course_name}}");
  await page.fill("#announcementMessage", "<p>Ola turma {{course_code}}, nosso encontro sera hoje.</p>");
}

async function fillMessageForm(page, options = {}) {
  await checkFirstPickerItem(page, "messageGroupPicker");
  const subject = options.studentName ? "Ola {{student_name}}" : "Aviso importante";
  const body = options.studentName
    ? "Ola {{student_name}}, este e um lembrete da disciplina {{course_name}}."
    : "Ola turma, este e um lembrete da disciplina {{course_name}}.";
  await page.fill("#messageSubject", subject);
  await page.fill("#messageBody", body);
}

async function fillRecurrenceForm(page) {
  await checkFirstPickerItem(page, "recurrenceGroupPicker");
  await page.fill("#recurrenceName", "Encontro semanal quinta 19h");
  await page.fill("#recurrenceTitle", "Aviso recorrente | {{course_name}}");
  await page.fill("#recurrenceMessage", "<p>O encontro da disciplina {{course_name}} sera hoje as 19h.</p>");
  await page.fill("#recurrenceFirstPublishAt", "2026-04-04T18:30");
  await page.fill("#recurrenceOccurrences", "4");
}

async function fillEngagementScreen(page) {
  await checkFirstPickerItem(page, "engagementGroupPicker");
  await page.click("#previewEngagementBtn");
  await expect(page.locator("#engagementPreviewCard .summary-grid")).toBeVisible();
  await page.fill("#engagementSubject", "Acompanhamento | {{student_name}}");
  await page.fill(
    "#engagementMessage",
    "Ola {{student_name}}, vimos que em {{course_name}} voce esta com o status {{reason}}.",
  );
}

test.beforeEach(async ({ page }) => {
  mockApiState = await attachMockApi(page);
  await page.goto("/");
  await page.waitForLoadState("networkidle");
});

test.afterEach(() => {
  if (mockApiState?.unexpected?.length) {
    unexpectedApiCalls.push(...mockApiState.unexpected);
  }
});

test.afterAll(async () => {
  ensureDir(path.join(__dirname, "..", "report"));
  const report = {
    generated_at: new Date().toISOString(),
    entries: auditSummary,
    unexpected_api_calls: unexpectedApiCalls,
  };
  fs.writeFileSync(path.join(__dirname, "..", "report", "summary.json"), JSON.stringify(report, null, 2), "utf-8");
});

test("audita todas as telas principais", async ({ page }, testInfo) => {
  await page.click("#testConnectionBtn");
  await expect(page.locator("#connectionResult .summary-grid")).toBeVisible();
  await captureAudit(page, testInfo, "screen-01-connection", "#tab-connection", "screen");

  await openTab(page, "organization");
  await page.click("#loadCourseCatalogBtn");
  await expect(page.locator("#courseCatalogPicker .picker-root")).toBeVisible();
  await captureAudit(page, testInfo, "screen-02-organization", "#tab-organization", "screen");

  await openTab(page, "announcements");
  await fillAnnouncementForm(page);
  await captureAudit(page, testInfo, "screen-03-announcements", "#tab-announcements", "screen");

  await openTab(page, "recurrence");
  await fillRecurrenceForm(page);
  await page.click("#previewRecurrenceBtn");
  await expect(page.locator("#recurrencePreviewSummary .summary-card").first()).toBeVisible();
  await captureAudit(page, testInfo, "screen-04-recurrence", "#tab-recurrence", "screen");

  await openTab(page, "messages");
  await fillMessageForm(page);
  await captureAudit(page, testInfo, "screen-05-messages", "#tab-messages", "screen");

  await openTab(page, "engagement");
  await fillEngagementScreen(page);
  await captureAudit(page, testInfo, "screen-06-engagement", "#tab-engagement", "screen");

  await openTab(page, "settings");
  await captureAudit(page, testInfo, "screen-07-settings", "#tab-settings", "screen");

  await openTab(page, "reports");
  await captureAudit(page, testInfo, "screen-08-reports", "#tab-reports", "screen");
});

test("audita todos os modais principais", async ({ page }, testInfo) => {
  await openTab(page, "organization");
  await page.click("#newGroupBtn");
  await captureAudit(page, testInfo, "modal-group", "#groupModal .modal-dialog", "modal");
  await page.click("#closeGroupModalBtn");

  await openTab(page, "announcements");
  await fillAnnouncementForm(page);
  await page.locator("#announcementForm button[type='submit']").click();
  await expect(page.locator("#sendReviewModal")).toBeVisible();
  await captureAudit(page, testInfo, "modal-review-announcement", "#sendReviewModal .modal-dialog", "modal");
  await page.click("#closeSendReviewModalBtn");

  await openTab(page, "messages");
  await fillMessageForm(page, { studentName: true });
  await page.locator("#messageForm button[type='submit']").click();
  await expect(page.locator("#sendReviewModal")).toBeVisible();
  await captureAudit(page, testInfo, "modal-review-message", "#sendReviewModal .modal-dialog", "modal");
  await page.click("#closeSendReviewModalBtn");

  await openTab(page, "engagement");
  await fillEngagementScreen(page);
  await page.locator("#engagementForm button[type='submit']").click();
  await expect(page.locator("#sendReviewModal")).toBeVisible();
  await captureAudit(page, testInfo, "modal-review-engagement", "#sendReviewModal .modal-dialog", "modal");
  await page.click("#closeSendReviewModalBtn");

  await openTab(page, "recurrence");
  await page.locator('[data-recurrence-action="edit"]').first().click();
  await expect(page.locator("#recurrenceEditModal")).toBeVisible();
  await captureAudit(page, testInfo, "modal-recurrence-edit", "#recurrenceEditModal .modal-dialog", "modal");
  await page.evaluate(() => {
    const request = {
      recurrence_id: "rec-001",
      title: "Aviso do encontro | {{course_name}}",
      message_html: "<p>Nos vemos hoje as 19h na disciplina {{course_name}}.</p>",
      target_mode: "groups",
      group_ids: ["group-extensao-noite"],
    };
    const preview = {
      summary: {
        courses: 2,
        occurrences_per_course: 4,
        total_announcements: 8,
        last_publish_at: "2026-04-25T18:30:00.000Z",
        recurrence_type: "weekly",
      },
      edit_diff: {
        added_courses: 1,
        removed_courses: 1,
        updated_courses: 1,
        unchanged_courses: 0,
        delete_items_expected: 4,
        create_items_expected: 8,
        course_changes: [
          { course_ref: "34110", course_name: "Empreendedorismo", action: "add", future_items: 0, new_occurrences: 4 },
          { course_ref: "33960", course_name: "Metodologia Cientifica", action: "remove", future_items: 4, new_occurrences: 0 },
          { course_ref: "34053", course_name: "Gerenciamento de Projetos", action: "update", future_items: 4, new_occurrences: 4 },
        ],
      },
      schedule: [
        { occurrence_index: 1, publish_at: "2026-04-04T18:30:00.000Z" },
        { occurrence_index: 2, publish_at: "2026-04-11T18:30:00.000Z" },
      ],
    };
    openRecurrenceReviewModal("edit", request, preview);
  });
  await expect(page.locator("#recurrenceReviewModal")).toBeVisible();
  await captureAudit(page, testInfo, "modal-recurrence-review", "#recurrenceReviewModal .modal-dialog", "modal");
  await page.click("#closeRecurrenceReviewModalBtn");
  await page.click("#cancelRecurrenceEditBtn");

  await page.locator('[data-recurrence-action="cancel"]').first().click();
  await expect(page.locator("#recurrenceCancelModal")).toBeVisible();
  await captureAudit(page, testInfo, "modal-recurrence-cancel", "#recurrenceCancelModal .modal-dialog", "modal");
  await page.click("#closeRecurrenceCancelModalBtn");
});
