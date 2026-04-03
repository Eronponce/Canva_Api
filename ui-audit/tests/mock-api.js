const mockData = require("./mock-data");

function fulfillJson(route, payload, status = 200) {
  return route.fulfill({
    status,
    contentType: "application/json; charset=utf-8",
    body: JSON.stringify(payload),
  });
}

async function handleApiRoute(route, request, state) {
  const url = new URL(request.url());
  const { pathname } = url;
  const method = request.method().toUpperCase();

  if (pathname === "/api/config" && method === "GET") {
    return fulfillJson(route, mockData.configResponse);
  }

  if (pathname === "/api/connection/test" && method === "POST") {
    return fulfillJson(route, mockData.connectionTest);
  }

  if (pathname === "/api/courses/catalog" && method === "POST") {
    return fulfillJson(route, mockData.courseCatalog);
  }

  if (pathname === "/api/settings/env" && method === "GET") {
    return fulfillJson(route, mockData.envResponse);
  }

  if (pathname === "/api/settings/env" && method === "PUT") {
    const body = request.postDataJSON() || {};
    return fulfillJson(route, {
      path: mockData.envResponse.path,
      content: body.content || mockData.envResponse.content,
    });
  }

  if (pathname === "/api/history" && method === "GET") {
    return fulfillJson(route, mockData.historyResponse);
  }

  if (pathname === "/api/reports/analytics" && method === "GET") {
    return fulfillJson(route, mockData.analyticsResponse);
  }

  if (pathname === "/api/announcements/preflight" && method === "POST") {
    return fulfillJson(route, mockData.announcementPreflight);
  }

  if (pathname === "/api/messages/recipients" && method === "POST") {
    return fulfillJson(route, mockData.messageRecipients);
  }

  if (pathname === "/api/engagement/inactive-targets" && method === "POST") {
    return fulfillJson(route, mockData.engagementTargets);
  }

  if (pathname === "/api/announcement-recurrences/preview" && method === "POST") {
    const body = request.postDataJSON() || {};
    const payload = body.recurrence_id ? mockData.recurrenceEditPreview : mockData.recurrencePreview;
    return fulfillJson(route, payload);
  }

  if (pathname === "/api/groups" && method === "POST") {
    return fulfillJson(route, {
      id: "group-created",
      name: "Grupo criado no audit",
      description: "",
      course_refs: ["34053"],
    }, 201);
  }

  if (/^\/api\/groups\/.+$/.test(pathname) && method === "PUT") {
    return fulfillJson(route, { ok: true });
  }

  if (/^\/api\/groups\/.+$/.test(pathname) && method === "DELETE") {
    return fulfillJson(route, { ok: true });
  }

  if (/^\/api\/announcement-recurrences\/[^/]+$/.test(pathname) && method === "PUT") {
    return fulfillJson(route, {
      recurrence: {
        ...mockData.configResponse.announcement_recurrences[0],
        updated_at: new Date().toISOString(),
      },
    });
  }

  if (/^\/api\/announcement-recurrences\/[^/]+\/cancel$/.test(pathname) && method === "POST") {
    return fulfillJson(route, {
      canceled_items: 4,
      recurrence_id: "rec-001",
    });
  }

  if (pathname === "/api/announcement-recurrences" && method === "POST") {
    return fulfillJson(route, {
      recurrence: {
        ...mockData.configResponse.announcement_recurrences[0],
        id: "rec-created",
      },
    }, 201);
  }

  state.unexpected.push({
    method,
    pathname,
  });
  return fulfillJson(route, {
    error: `Unexpected mocked request: ${method} ${pathname}`,
  }, 501);
}

async function attachMockApi(page) {
  const state = { unexpected: [] };
  await page.route("**/api/**", (route, request) => handleApiRoute(route, request, state));
  return state;
}

module.exports = {
  attachMockApi,
  mockData,
};
