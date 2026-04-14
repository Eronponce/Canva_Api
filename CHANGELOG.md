# Changelog

## Unreleased

## v1.3.1 - 2026-04-14

### Robustez de envio

- timeouts e erros transitorios de rede do Canvas agora tambem entram no retry automatico do cliente HTTP
- retries com upload reaproveitam o arquivo corretamente entre tentativas para evitar falha por ponteiro consumido

## v1.3.0 - 2026-04-10

### Conexao

- adicionado switch entre ambiente real e ambiente de teste na aba `Conexao`
- adicionadas variaveis `.env` `CANVAS_BASE_URL_TEST` e `CANVAS_ACCESS_TOKEN_TEST` para credenciais de teste
- adicionado indicador no topo com ambiente ativo, base efetiva e origem do token
- filtros dos seletores de cursos/grupos agora aplicam apos 3 segundos sem digitar, Enter ou saida do campo, evitando perda de foco a cada tecla

### Organizacao

- codigos de disciplina no formato `GPR@100Avisos` agora aparecem como codigo curto `GPR` nos filtros, seletores e lista de cursos

### Recorrencia e Inativos

- `Recorrencia` segue com fluxo guiado por modal antes da revisao final
- `Inativos` agora permite selecionar os filtros `Nunca entrou`, `Menos que X minutos`, `Nao realizou a atividade objetiva` e `Nao realizou a atividade integradora`
- removidos os campos avancados de modulos, dias sem atividade e combinacao `E/OU` do painel de `Inativos`
- adicionada busca automatica de quizzes e atividades avaliativas publicados de cada disciplina antes de verificar as submissoes no Canvas
- adicionados dois modelos de mensagem para `Inativos`: um comunicado de inatividade e outro de atividade objetiva/integradora pendente, com preview antes do envio
- filtro de `Nao realizou a atividade integradora` agora ignora atividades sem entrega online rastreavel, nao avaliadas, rascunhos e itens de zero ponto para reduzir falsos positivos em massa
- filtro de `Nao realizou a atividade objetiva` agora ignora atividades objetivas de treino ou pesquisa nao avaliativa e pede ao Canvas a submissao associada ao quiz
- `Inativos` passou a abrir o relatorio na propria tela, sem modal intermediario na etapa de busca
- cada busca de `Inativos` agora salva uma analise consolidada sem duplicata por aluno, com percentuais e detalhamento por turma
- o relatorio de `Inativos` agora mostra graficos de `fez tudo`, `nunca entrou`, `menos de X minutos`, `atividade objetiva` e `atividade integradora`
- a aba `Relatorios` agora consegue recarregar a analise salva novamente na aba `Inativos`
- os blocos recolhiveis de `Inativos` agora aceitam clique na faixa direita do cabecalho e tambem no rodape da secao

### Relatorios

- adicionada edicao de comunicados ja criados no Canvas a partir do detalhe do relatorio
- adicionada edicao em massa dos avisos editaveis de um lote de comunicados
- cada busca de `Inativos` pela interface agora gera uma `Previa de inativos` na aba `Relatorios`, com CSV consolidado por aluno para conferencia manual
- o preview de `Inativos` agora oferece botoes diretos para baixar o CSV da previa e abrir esse item em `Relatorios`
- registros de dry-run, falha ou sem `announcement_id` ficam protegidos contra edicao
- historico local passa a marcar titulo, mensagem e horario da ultima edicao do comunicado

## v1.2.0 - 2026-04-08

### Infra e operacao

- adicionados `Dockerfile`, `.dockerignore` e `docker-compose.yml` para subir o painel em container
- persistencia de `data/`, `logs/` e `.env` mantida via bind mounts locais
- README atualizado com fluxo de uso em Docker e exemplo pensado para WSL Debian

### Customizacao para Codex

- adicionados `AGENTS.md`, `src/AGENTS.md` e `static/AGENTS.md` com orientacoes persistentes do projeto
- adicionadas skills de repositório para QA manual e fluxo de release
- documentado o modelo de customizacao em `docs/codex_customization.md`

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
