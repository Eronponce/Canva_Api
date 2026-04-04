# Changelog

## v1.1.0 - 2026-04-03

Release focada em visual improvements, clareza operacional e polish de UX.

### Destaques

- refinamento visual de cards, tabelas, modais e estados vazios
- `selects` ajustados para alto contraste no Windows
- mensagens de erro com scroll, foco automatico e destaque visual
- modulo `Inativos` reorganizado em fluxo vertical com secoes recolhiveis
- explicacoes contextuais por coluna nas tabelas via ajuda embutida
- simplificacao dos placeholders para reduzir erro operacional
- limpeza da exibicao de numero e codigo de curso nas telas operacionais
- checklist completo de QA manual em `docs/manual_test_checklist.md`

### Qualidade

- `pytest`
- `node --check`
- `python -m compileall`

## v1.0.0 - 2026-04-03

Primeira release consolidada do painel operacional para Canvas LMS.

### Destaques

- conexao com Canvas por `.env` ou pela interface
- organizacao de cursos e grupos locais
- comunicados em lote com anexo opcional
- caixa de entrada em lote com anexo opcional
- placeholders seguros para curso e aluno
- modulo de alunos inativos com preview por turma e por aluno
- recorrencia de avisos com agenda, edicao em modal e cancelamento seguro
- relatorios comparativos com delta e alertas executivos
- limpeza total do banco local com confirmacao digitada
- launcher local para iniciar, parar e reiniciar o painel
- auditoria de UI com Playwright e axe cobrindo telas e modais principais

### Qualidade e operacao

- persistencia relacional com SQLAlchemy
- suporte a SQLite local e MySQL
- revisao pre-envio em comunicados, mensagens e inativos
- exportacao de CSV por lote
- tratamento de layout, overflow horizontal e acessibilidade basica

### Documentacao

- README consolidado
- DER em `docs/database_erd.md`
- plano de auditoria visual em `docs/ui_audit_action_plan.md`
