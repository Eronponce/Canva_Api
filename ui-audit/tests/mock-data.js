const now = new Date("2026-04-03T18:30:00Z");

function iso(offsetDays, hour = 19, minute = 0) {
  const value = new Date(now.getTime() + offsetDays * 24 * 60 * 60 * 1000);
  value.setUTCHours(hour, minute, 0, 0);
  return value.toISOString();
}

const registeredCourses = [
  {
    course_ref: "34053",
    course_id: 34053,
    course_name: "Gerenciamento de Projetos",
    course_code: "GPR@100",
    term_name: "2026/1",
  },
  {
    course_ref: "33960",
    course_id: 33960,
    course_name: "Metodologia Cientifica",
    course_code: "MET@200",
    term_name: "2026/1",
  },
  {
    course_ref: "34110",
    course_id: 34110,
    course_name: "Empreendedorismo",
    course_code: "EMP@300",
    term_name: "2026/1",
  },
];

const groups = [
  {
    id: "group-extensao-noite",
    name: "Extensao noite",
    description: "Turmas das quintas as 19h",
    course_refs: ["34053", "33960"],
    courses: registeredCourses.filter((course) => ["34053", "33960"].includes(course.course_ref)),
  },
  {
    id: "group-extensao-sabado",
    name: "Extensao sabado",
    description: "Turmas dos encontros especiais",
    course_refs: ["34110"],
    courses: registeredCourses.filter((course) => ["34110"].includes(course.course_ref)),
  },
];

const recurrences = [
  {
    id: "rec-001",
    name: "Encontro semanal quinta 19h",
    title: "Aviso do encontro | {{course_name}}",
    message_html: "<p>Nos vemos hoje as 19h na disciplina {{course_name}}.</p>",
    recurrence_type: "weekly",
    interval_value: 1,
    occurrence_count: 8,
    first_publish_at: iso(1, 18, 30),
    next_publish_at: iso(1, 18, 30),
    target_mode: "groups",
    group_ids: ["group-extensao-noite"],
    course_refs: ["34053", "33960"],
    lock_comment: true,
    is_active: true,
    total_items: 16,
    future_items: 12,
    canceled_items: 0,
    error_items: 0,
    cancel_reason: "",
    last_error: "",
    created_at: iso(-3, 13, 0),
    updated_at: iso(-1, 15, 0),
    items: [
      {
        course_ref: "34053",
        course_name: "Gerenciamento de Projetos",
        scheduled_for: iso(1, 18, 30),
        status: "scheduled",
      },
      {
        course_ref: "33960",
        course_name: "Metodologia Cientifica",
        scheduled_for: iso(1, 18, 30),
        status: "scheduled",
      },
      {
        course_ref: "34053",
        course_name: "Gerenciamento de Projetos",
        scheduled_for: iso(8, 18, 30),
        status: "scheduled",
      },
    ],
  },
  {
    id: "rec-002",
    name: "Lembrete avaliacao semanal",
    title: "Lembrete de atividade | {{course_code}}",
    message_html: "<p>Revise a atividade da semana.</p>",
    recurrence_type: "daily",
    interval_value: 7,
    occurrence_count: 4,
    first_publish_at: iso(2, 8, 0),
    next_publish_at: iso(2, 8, 0),
    target_mode: "courses",
    group_ids: [],
    course_refs: ["34110"],
    lock_comment: false,
    is_active: true,
    total_items: 4,
    future_items: 4,
    canceled_items: 0,
    error_items: 1,
    cancel_reason: "",
    last_error: "1 aviso precisou de reprocessamento",
    created_at: iso(-10, 11, 0),
    updated_at: iso(-2, 9, 0),
    items: [
      {
        course_ref: "34110",
        course_name: "Empreendedorismo",
        scheduled_for: iso(2, 8, 0),
        status: "scheduled",
      },
      {
        course_ref: "34110",
        course_name: "Empreendedorismo",
        scheduled_for: iso(9, 8, 0),
        status: "scheduled",
      },
    ],
  },
];

const historyItems = [
  {
    id: "job-ann-001",
    kind: "announcement",
    title: "Comunicado de alinhamento",
    status: "success",
    created_at: iso(-2, 18, 0),
    report_filename: "job-ann-001.csv",
    result: {
      summary: {
        courses_requested: 2,
        success_count: 2,
        failure_count: 0,
        published_count: 2,
      },
      course_results: [
        {
          course_ref: "34053",
          course_id: 34053,
          course_name: "Gerenciamento de Projetos",
          announcement_id: 871,
          published: true,
          attachment_name: "agenda.pdf",
          status: "success",
          error: "",
        },
        {
          course_ref: "33960",
          course_id: 33960,
          course_name: "Metodologia Cientifica",
          announcement_id: 872,
          published: true,
          attachment_name: "agenda.pdf",
          status: "success",
          error: "",
        },
      ],
    },
  },
  {
    id: "job-msg-001",
    kind: "message",
    title: "Mensagem coletiva de boas-vindas",
    status: "success",
    created_at: iso(-1, 14, 0),
    report_filename: "job-msg-001.csv",
    result: {
      summary: {
        total_students_found: 54,
        unique_recipients: 49,
        recipients_sent: 49,
      },
      course_results: [
        {
          course_ref: "34053",
          course_id: 34053,
          course_name: "Gerenciamento de Projetos",
          students_found: 28,
          recipients_targeted: 25,
          recipients_sent: 25,
          attachment_name: "roteiro.pdf",
          status: "success",
          error: "",
        },
      ],
    },
  },
  {
    id: "job-eng-001",
    kind: "engagement",
    title: "Mensagem para inativos",
    status: "success",
    created_at: iso(-1, 19, 0),
    report_filename: "job-eng-001.csv",
    result: {
      summary: {
        total_students_found: 64,
        total_matched_students: 12,
        total_never_accessed_matches: 5,
        total_incomplete_resources_matches: 7,
      },
      course_results: [
        {
          course_ref: "34053",
          course_id: 34053,
          course_name: "Gerenciamento de Projetos",
          students_found: 28,
          recipients_targeted: 7,
          never_accessed_matches: 3,
          incomplete_resources_matches: 4,
          inactive_days_matches: 2,
          recipients_sent: 7,
          status: "success",
          error: "",
        },
      ],
    },
  },
];

const analytics = {
  executive: {
    alerts: [
      {
        level: "warning",
        title: "Falhas cresceram nas ultimas 24h",
        message: "A recorrencia de lembrete semanal teve 1 erro recente e merece revisao.",
        action: "Verifique a recorrencia ativa com alerta e valide as proximas publicacoes.",
      },
    ],
    highlights: [
      {
        label: "Maior volume",
        value: "Gerenciamento de Projetos",
        helper: "Curso com mais destinatarios no periodo",
        tone: "info",
      },
      {
        label: "Melhor taxa",
        value: "98,4%",
        helper: "Media consolidada dos lotes concluidos",
        tone: "success",
      },
    ],
  },
  overview: {
    days: 30,
    current_start: "2026-03-04",
    current_end: "2026-04-03",
    previous_start: "2026-02-02",
    previous_end: "2026-03-03",
    total_jobs: 14,
    success_rate: 96.4,
    avg_duration_seconds: 18.6,
    total_recipients_sent: 143,
    total_announcements_created: 21,
    total_engagement_jobs: 4,
    active_recurrences: 2,
    comparison: {
      total_jobs: { direction: "up", absolute: 4, percent: 40 },
      success_rate: { direction: "up", absolute: 2.1, percent: 2.2 },
      avg_duration_seconds: { direction: "down", absolute: -2.4, percent: -11.4 },
      total_recipients_sent: { direction: "up", absolute: 37, percent: 34.9 },
      total_announcements_created: { direction: "up", absolute: 6, percent: 40 },
      total_engagement_jobs: { direction: "up", absolute: 1, percent: 33.3 },
      new_recurrences_created: { direction: "flat", absolute: 0, percent: 0 },
    },
  },
  sections: {
    period_comparison: {
      title: "Comparacao de periodo",
      items: [
        { metric: "Lotes", current: 14, previous: 10, delta: 4, delta_percent: 40 },
        { metric: "Destinatarios", current: 143, previous: 106, delta: 37, delta_percent: 34.9 },
      ],
    },
    operational: {
      title: "Operacional",
      items: [
        {
          kind: "announcement",
          current_jobs: 5,
          previous_jobs: 3,
          delta_jobs: 2,
          current_success_rate: 100,
          previous_success_rate: 100,
          current_dry_run: 1,
          previous_dry_run: 0,
        },
        {
          kind: "message",
          current_jobs: 5,
          previous_jobs: 4,
          delta_jobs: 1,
          current_success_rate: 95,
          previous_success_rate: 93,
          current_dry_run: 0,
          previous_dry_run: 1,
        },
      ],
    },
    top_courses: {
      title: "Cursos mais movimentados",
      items: [
        {
          course_name: "Gerenciamento de Projetos",
          course_ref: "34053",
          current_runs: 7,
          previous_runs: 5,
          delta_runs: 2,
          current_success: 7,
          previous_success: 5,
          current_failure: 0,
          previous_failure: 0,
          current_recipients_sent: 63,
          previous_recipients_sent: 41,
          delta_recipients_sent: 22,
        },
      ],
    },
    upcoming_recurrences: {
      title: "Recorrencias previstas",
      items: recurrences.map((item) => ({
        recurrence_id: item.id,
        name: item.name,
        title: item.title,
        first_publish_at: item.first_publish_at,
        occurrence_count: item.occurrence_count,
        future_items: item.future_items,
      })),
    },
    recent_failures: {
      title: "Falhas recentes",
      items: [
        {
          created_at: iso(-1, 16, 0),
          kind: "recurrence",
          course_name: "Empreendedorismo",
          course_ref: "34110",
          status: "error",
          error: "A API do Canvas retornou timeout ao criar um aviso futuro.",
        },
      ],
    },
  },
};

const courseCatalog = {
  items: [
    ...registeredCourses.map((course) => ({ ...course, already_registered: true })),
    {
      course_ref: "34199",
      course_id: 34199,
      course_name: "Comunicacao Organizacional",
      course_code: "COM@400",
      term_name: "2026/1",
      already_registered: false,
    },
  ],
};

const connectionTest = {
  ok: true,
  base_url: "https://canvas.mock.invalid",
  user: { id: 9981, name: "Operador Supremo" },
  masked_token: "ui-a...oken",
  used_env_token: true,
  env_token_source: "access_token",
  token_type: "api",
};

const announcementPreflight = {
  summary: {
    courses_requested: 2,
    success_count: 2,
    failure_count: 0,
    publish_mode: "publish_now",
    dry_run: false,
    attachment_name: "agenda.pdf",
  },
  courses: [
    {
      course_ref: "34053",
      course_id: 34053,
      course_name: "Gerenciamento de Projetos",
      course_code: "GPR@100",
      status: "ok",
    },
    {
      course_ref: "33960",
      course_id: 33960,
      course_name: "Metodologia Cientifica",
      course_code: "MET@200",
      status: "ok",
    },
  ],
};

const messageRecipients = {
  total_students_found: 54,
  unique_recipients: 49,
  courses: [
    {
      course_ref: "34053",
      course_id: 34053,
      course_name: "Gerenciamento de Projetos",
      students_found: 28,
    },
    {
      course_ref: "33960",
      course_id: 33960,
      course_name: "Metodologia Cientifica",
      students_found: 26,
    },
  ],
  items: [
    { user_id: 201, student_name: "Ana Silva", course_ref: "34053", course_name: "Gerenciamento de Projetos" },
    { user_id: 202, student_name: "Bruno Costa", course_ref: "34053", course_name: "Gerenciamento de Projetos" },
    { user_id: 203, student_name: "Carla Souza", course_ref: "33960", course_name: "Metodologia Cientifica" },
    { user_id: 204, student_name: "Diego Lima", course_ref: "33960", course_name: "Metodologia Cientifica" },
  ],
};

const engagementTargets = {
  summary: {
    total_courses: 2,
    total_students_found: 54,
    total_matched_students: 11,
    total_never_accessed_matches: 4,
    total_incomplete_resources_matches: 7,
    total_inactive_days_matches: 3,
    total_low_activity_matches: 5,
    courses_without_module_requirements: 1,
    analytics_unavailable_courses: 0,
    progress_unavailable_courses: 0,
    criteria_mode: "never_accessed_or_incomplete_resources",
    top_priority_course_name: "Gerenciamento de Projetos",
    top_priority_course_ref: "34053",
  },
  courses: [
    {
      course_ref: "34053",
      course_id: 34053,
      course_name: "Gerenciamento de Projetos",
      priority_level: "critical",
      urgency_score: 98,
      students_found: 28,
      matched_students: 7,
      matched_ratio: 25,
      never_accessed_matches: 3,
      incomplete_resources_matches: 4,
      inactive_days_matches: 2,
      low_activity_matches: 3,
      has_module_requirements: true,
      analytics_available: true,
      progress_available: true,
      enrollment_activity_available: true,
    },
    {
      course_ref: "33960",
      course_id: 33960,
      course_name: "Metodologia Cientifica",
      priority_level: "medium",
      urgency_score: 61,
      students_found: 26,
      matched_students: 4,
      matched_ratio: 15.4,
      never_accessed_matches: 1,
      incomplete_resources_matches: 3,
      inactive_days_matches: 1,
      low_activity_matches: 2,
      has_module_requirements: false,
      analytics_available: true,
      progress_available: true,
      enrollment_activity_available: true,
    },
  ],
  items: [
    {
      course_ref: "34053",
      course_id: 34053,
      course_name: "Gerenciamento de Projetos",
      user_id: 201,
      student_name: "Ana Silva",
      priority_level: "critical",
      urgency_score: 98,
      page_views: 0,
      participations: 0,
      last_activity_at: iso(-14, 10, 0),
      total_activity_time_seconds: 120,
      requirement_completed_count: 0,
      requirement_count: 6,
      reasons_label: "Sem acesso nenhum | Recursos pendentes",
    },
    {
      course_ref: "33960",
      course_id: 33960,
      course_name: "Metodologia Cientifica",
      user_id: 203,
      student_name: "Carla Souza",
      priority_level: "medium",
      urgency_score: 61,
      page_views: 2,
      participations: 0,
      last_activity_at: iso(-8, 11, 30),
      total_activity_time_seconds: 600,
      requirement_completed_count: 2,
      requirement_count: 5,
      reasons_label: "Recursos pendentes",
    },
  ],
};

const recurrencePreview = {
  summary: {
    courses: 2,
    occurrences_per_course: 4,
    total_announcements: 8,
    last_publish_at: iso(22, 18, 30),
    recurrence_type: "weekly",
  },
  schedule: [
    { occurrence_index: 1, publish_at: iso(1, 18, 30) },
    { occurrence_index: 2, publish_at: iso(8, 18, 30) },
    { occurrence_index: 3, publish_at: iso(15, 18, 30) },
    { occurrence_index: 4, publish_at: iso(22, 18, 30) },
  ],
};

const recurrenceEditPreview = {
  ...recurrencePreview,
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
};

const envResponse = {
  path: "ui-audit/.env.ui",
  content: "CANVAS_BASE_URL=https://canvas.mock.invalid\nCANVAS_ACCESS_TOKEN=ui-audit-token\n",
};

module.exports = {
  configResponse: {
    settings: {
      default_base_url: "https://canvas.mock.invalid",
      env_token_available: true,
      env_token_source: "access_token",
      database_backend: "sqlite",
      database_url_masked: "sqlite:///ui-audit/runtime-data/canvas_bulk_panel.db",
      request_timeout: 30,
      retry_max_attempts: 4,
      retry_base_delay: 1.5,
      history_limit: 25,
      legacy_json_import_enabled: false,
      env_file_path: "ui-audit/.env.ui",
      env_file_name: ".env.ui",
    },
    groups,
    registered_courses: registeredCourses,
    announcement_recurrences: recurrences,
  },
  courseCatalog,
  connectionTest,
  announcementPreflight,
  messageRecipients,
  engagementTargets,
  recurrencePreview,
  recurrenceEditPreview,
  historyResponse: { items: historyItems },
  analyticsResponse: analytics,
  envResponse,
};
