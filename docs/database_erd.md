# DER Relacional

## Visao geral

O painel usa uma camada relacional pronta para `SQLite` local e `MySQL`, concentrando:

- cursos cadastrados
- grupos
- vinculos entre grupos e cursos
- jobs
- alvos resolvidos por job
- logs de execucao
- resultados por curso

## Entidades principais

### `courses`

- `id`
- `course_ref`
- `canvas_course_id`
- `course_name`
- `course_code`
- `term_name`
- `workflow_state`
- `source_type`
- `notes`
- `metadata_json`
- `last_synced_at`
- `is_active`
- `is_deleted`
- `created_at`
- `updated_at`
- `activated_at`
- `deactivated_at`
- `deleted_at`

### `course_groups`

- `id`
- `public_id`
- `name`
- `description`
- `notes`
- `is_active`
- `is_deleted`
- `created_at`
- `updated_at`
- `activated_at`
- `deactivated_at`
- `deleted_at`

### `group_courses`

- `id`
- `group_id`
- `course_id`
- `position`
- `added_at`
- `removed_at`
- `is_active`
- `is_deleted`
- `created_at`
- `updated_at`
- `activated_at`
- `deactivated_at`
- `deleted_at`

### `job_runs`

- `id`
- `public_id`
- `kind`
- `title`
- `status`
- `base_url`
- `canvas_user_id`
- `canvas_user_name`
- `request_token_source`
- `request_payload_json`
- `summary_json`
- `result_json`
- `error_message`
- `report_filename`
- `requested_strategy`
- `effective_strategy`
- `dry_run`
- `dedupe`
- `progress_current`
- `progress_total`
- `progress_percent`
- `progress_step`
- `created_at`
- `updated_at`
- `started_at`
- `finished_at`

### `job_logs`

- `id`
- `job_run_id`
- `level`
- `message`
- `data_json`
- `created_at`

### `job_target_groups`

- `id`
- `job_run_id`
- `group_id`
- `group_public_id`
- `group_name_snapshot`
- `created_at`

### `job_target_courses`

- `id`
- `job_run_id`
- `course_id`
- `course_ref_snapshot`
- `course_name_snapshot`
- `created_at`

### `job_course_results`

- `id`
- `job_run_id`
- `course_id`
- `course_ref_snapshot`
- `course_name_snapshot`
- `status`
- `strategy_requested`
- `strategy_used`
- `students_found`
- `manual_matches`
- `duplicates_skipped`
- `recipients_targeted`
- `recipients_sent`
- `batch_count`
- `announcement_id`
- `announcement_url`
- `conversation_ids_json`
- `published`
- `delayed_post_at`
- `dry_run`
- `messageable_context`
- `manual_recipients`
- `error_message`
- `raw_result_json`
- `created_at`
- `updated_at`
- `started_at`
- `finished_at`

## Relacionamentos

- `courses 1:N group_courses`
- `course_groups 1:N group_courses`
- `job_runs 1:N job_logs`
- `job_runs 1:N job_target_groups`
- `job_runs 1:N job_target_courses`
- `job_runs 1:N job_course_results`
- `courses 1:N job_target_courses`
- `courses 1:N job_course_results`
- `course_groups 1:N job_target_groups`

## Politica atual de exclusao

Campos de soft delete continuam presentes no modelo para historico e evolucao futura, mas o comportamento atual do produto e:

- excluir curso: `hard delete`
- excluir grupo: `hard delete`
- apagar banco via configuracoes: `hard delete` de todas as tabelas operacionais

Os snapshots de jobs existem justamente para preservar rastreabilidade mesmo quando curso ou grupo deixa de existir.

## Relatorios suportados pelo modelo

### Consolidados

- operacional por periodo
- volume diario de lotes
- taxa de sucesso por tipo
- duracao media de execucao

### Operacionais

- cursos mais acionados
- grupos mais usados
- falhas recentes
- comparativo dry run x envio real

### Auditoria

- historico completo por job
- logs por etapa
- resultados por curso
- estrategia pedida x estrategia efetivamente usada

## Secoes recolhiveis recomendadas

- Visao geral
- Operacional por periodo
- Volume diario
- Cursos mais movimentados
- Grupos mais usados
- Falhas recentes
- Historico detalhado
