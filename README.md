# Canvas Bulk Panel

Painel web local para operar em lote no Canvas LMS usando apenas endpoints oficiais da API.

## O que o sistema faz

- valida conexao com o Canvas usando `base_url` e token vindos da tela ou do `.env`
- alterna entre ambiente real e ambiente de teste do Canvas direto na aba de conexao
- organiza cursos cadastrados e grupos de turmas
- busca no Canvas os cursos acessiveis e permite cadastrar varios de uma vez
- destaca o codigo curto da disciplina em seletores e filtros, por exemplo `GPR@100Avisos` aparece como `GPR | 100Avisos`
- publica comunicados em lote
- publica comunicados em lote com anexo opcional
- cria recorrencias de avisos no proprio Canvas
- conduz `Recorrencia` por modal guiado e `Inativos` por tela continua com relatorio salvo
- permite placeholders seguros por disciplina e aluno (`{{course_name}}`, `{{student_name}}`)
- valida placeholders com blocos arrastaveis em comunicados, recorrencia e caixa de entrada
- envia mensagens pela caixa de entrada do Canvas em lote com anexo opcional
- envia mensagens para alunos inativos ou com atividade objetiva/atividade integradora pendente
- prioriza turmas e alunos inativos por nivel de risco no preview antes do envio
- revisa o alvo antes do envio em comunicados, caixa de entrada e inativos
- compara periodo atual vs periodo anterior equivalente nos relatorios
- gera alertas executivos e destaques operacionais na aba de relatorios
- registra historico, resultados por turma e exportacao em CSV
- permite editar comunicados ja criados no Canvas a partir do detalhe do relatorio
- permite limpar todo o banco local com confirmacao digitada

## Modulos da interface

1. `Conexao`
   teste de acesso ao Canvas
2. `Organizacao`
   cursos cadastrados, catalogo do Canvas e grupos
3. `Comunicados`
   anuncios pontuais por grupos salvos ou cursos especificos, com anexo opcional
4. `Recorrencia`
   cria varios avisos futuros no Canvas de uma vez
5. `Caixa de entrada`
   mensagens em lote por grupos salvos ou cursos especificos, com anexo opcional e preview
6. `Inativos`
   mensagem para alunos inativos ou com atividade objetiva/atividade integradora pendente
7. `Configuracoes`
   resumo operacional, editor do `.env` e zona de perigo
8. `Relatorios`
   historico, analitico comparativo e download de CSV

## Fluxos refinados da interface

### Comunicados

- resumo operacional do lote antes do envio
- preview com placeholders por disciplina
- revisao final antes de enfileirar
- erros com foco automatico no campo necessario

### Caixa de entrada

- resumo operacional com estrategia final, deduplicacao e anexo
- indica quando `{{student_name}}` forÃ§a personalizacao por aluno
- revisao final antes de enfileirar
- erros com foco automatico no campo necessario

### Recorrencia

- criacao pelo fluxo guiado em modal
- edicao em modal separado
- preview obrigatorio e revisao final antes de criar ou salvar
- agenda das proximas publicacoes
- lista com filtros por status e linha temporal
- erros com foco automatico no campo necessario

### Inativos

- busca direta, sem modal intermediario antes do relatorio
- filtro simplificado, sem regras avancadas ocultas
- fluxo vertical com `Resumo da selecao`, `Relatorio de inativos`, `Mensagem` e `Resultado do envio`
- secoes recolhiveis com animacao suave
- recolhimento rapido pelos controles do topo e do rodape das secoes mais longas
- relatorio consolidado sem duplicata por aluno
- graficos com percentual de quem fez tudo, quem nunca entrou, quem ficou abaixo dos minutos e quem nao realizou atividade objetiva ou integradora
- possibilidade de salvar a busca na aba `Relatorios` e carregar a analise novamente na aba `Inativos`

## Revisao antes do envio

Antes de disparar um lote real, o painel abre uma revisao com:

- resumo do envio
- turmas alvo
- amostra de destinatarios quando aplicavel
- mensagem que sera enviada
- modo de publicacao, estrategia, criterio e anexo

Isso vale para:

- `Comunicados`
- `Caixa de entrada`
- `Inativos`

No modulo `Recorrencia`, o fluxo tambem ficou protegido:

- o preview precisa estar atualizado
- qualquer mudanca em turmas, datas ou conteudo invalida o preview anterior
- antes de criar ou salvar, o painel abre uma revisao final com o impacto esperado

## Blocos de variaveis

Nos modulos `Comunicados`, `Recorrencia` e `Caixa de entrada` existe uma barra de variaveis seguras.

- clique ou arraste os blocos para inserir placeholders
- o sistema valida automaticamente se as variaveis usadas sao reconhecidas
- variaveis invalidas bloqueiam o envio
- a interface mostra uma amostra com a primeira turma selecionada

Variaveis suportadas:

- `{{course_name}}`
- `{{student_name}}`

No modulo `Inativos`, o foco tambem ficou em:

- `{{student_name}}`
- `{{course_name}}`

Os placeholders tecnicos antigos de numero e codigo de curso foram removidos da interface para reduzir ruido visual e erro operacional.

## Como funciona a Recorrencia

O modulo `Recorrencia` e focado em `avisos`.

Na criacao, o botao `Abrir fluxo guiado` abre um modal em etapas: primeiro valida destino, depois conteudo e agenda, depois gera o relatorio final com turmas e total de avisos. O operador so consegue abrir a revisao final depois que o preview estiver atualizado.

Em vez de depender de um scheduler local, ele:

1. resolve os cursos alvo
2. calcula as datas da recorrencia
3. cria todos os avisos futuros no Canvas usando `Discussion Topics`
4. usa `delayed_post_at` em cada aviso futuro
5. guarda localmente os `topic_id` criados para permitir cancelamento depois

### O que isso significa na pratica

- depois que a recorrencia e criada, o Canvas publica os avisos sozinho
- o painel nao precisa ficar ligado para os avisos futuros sairem
- cancelar a recorrencia tenta apagar do Canvas apenas os avisos futuros ainda nao publicados
- avisos ja publicados nao sao removidos automaticamente

### Frequencias suportadas

- `Semanal`
- `Diaria`

### Quando mudar o dia da reuniao

O fluxo recomendado e:

1. abrir `Editar` na recorrencia
2. ajustar turmas, datas, intervalo ou quantidade no modal
3. clicar em `Prever impacto`
4. revisar o que entra, sai ou continua
5. salvar a edicao

Se a mudanca for total e voce preferir recomecar:

1. usar `Duplicar base`
2. ajustar a configuracao no formulario principal
3. prever datas
4. criar uma nova recorrencia

## O modulo Inativos

O modulo `Inativos` foi feito para o fluxo:

1. escolher grupos salvos ou cursos especificos
2. escolher um ou mais filtros: `Nunca entrou`, `Menos que X minutos`, `Nao realizou a atividade objetiva` e `Nao realizou a atividade integradora`
3. clicar em `Buscar inativos`
4. descer na propria tela para ver graficos, consolidado por aluno e resumo por turma
5. baixar o CSV ou abrir a mesma busca na aba `Relatorios`
6. revisar as duas mensagens possiveis e o envio final

O uso comum fica concentrado nos filtros escolhidos e no relatorio salvo da busca. O preview mostra primeiro o resumo geral, depois os graficos e as tabelas consolidadas, sem duplicar o mesmo aluno em varias linhas do relatorio principal.

### Criterios suportados

- `Nunca entrou`
  usa `page_views = 0` e `participations = 0` no analytics do Canvas
- `Menos que X minutos`
  usa `total_activity_time` dos enrollments e o limite de minutos informado
- `Nao realizou a atividade objetiva`
  busca automaticamente as atividades objetivas publicadas e avaliativas de cada disciplina e marca quem deixou pelo menos uma sem submissao feita
- `Nao realizou a atividade integradora`
  busca automaticamente as atividades integradoras publicadas, avaliadas e com entrega online rastreavel de cada disciplina e marca quem deixou pelo menos uma sem submissao feita

### Importante

- o envio acontece pela `Inbox` do Canvas usando `Conversations`
- nao e um envio direto de email
- o aluno pode receber notificacao por email se as preferencias dele no Canvas estiverem configuradas para isso
- existem dois blocos de mensagem: um para `Inatividade` (`Nunca entrou` e `Menos que X minutos`) e outro para `Atividade objetiva/integradora pendente`
- o mesmo aluno pode receber os dois comunicados se cair nos dois grupos de filtro
- nao precisa colar link de atividade; o painel lista as atividades avaliativas e quizzes publicados de cada turma antes de checar as submissoes
- para evitar falsos positivos em massa, `Nao realizou a atividade integradora` ignora item sem entrega online rastreavel (`none`, `on_paper`, `online_quiz`), item `not_graded`, rascunho e atividade de zero ponto
- atividade entregue, mesmo ainda sem correcao/nota, e considerada feita quando o Canvas retorna `submitted_at`, estado de submissao ou conteudo enviado como anexo, URL ou texto
- `Nao realizou a atividade objetiva` ignora atividade objetiva de treino ou pesquisa nao avaliativa
- se uma turma tiver 4 quizzes publicados, o aluno entra no alvo se deixou qualquer um desses quizzes sem fazer
- cada busca de `Inativos` feita pela interface cria uma `Previa de inativos` na aba `Relatorios`, com CSV consolidado por aluno para conferencia manual antes do envio
- o proprio card de preview em `Inativos` mostra `Baixar CSV da previa` e `Abrir previa em Relatorios` logo apos a busca
- a aba `Relatorios` permite reabrir a analise de `Inativos` na propria tela de `Inativos`, mantendo os graficos e o consolidado acessiveis
- falhas transitorias de rede do Canvas, como `Read timed out` e quedas de conexao, agora usam retry automatico com backoff conforme `CANVAS_RETRY_MAX_ATTEMPTS` e `CANVAS_RETRY_BASE_DELAY`

### Como ler os indicadores

- `Nunca entrou`
  aluno sem page views e sem participacoes no analytics do Canvas
- `Poucos minutos`
  aluno abaixo do limite de minutos informado
- `Ativ. objetiva`
  quantidade de alunos com pelo menos uma atividade objetiva publicada sem submissao feita
- `Ativ. integradora`
  quantidade de alunos com pelo menos uma atividade integradora publicada sem submissao feita
- `Comunicados`
  quantidade de mensagens previstas; pode ser maior que o total de alunos alvo quando alguem cai nos dois grupos
- `Atividades`
  total de atividades avaliativas ou quizzes avaliativos que o painel verificou na disciplina
- `Faltando`
  nomes das atividades publicadas que ainda nao aparecem como feitas para o aluno

## Anexos nativos no Canvas

O painel agora suporta anexos nativos nos modulos:

- `Comunicados`
  o arquivo vai junto na criacao do `Discussion Topic`
- `Caixa de entrada`
  o arquivo e enviado uma vez para os arquivos do usuario no Canvas e depois reutilizado via `attachment_ids[]`

### Como o fluxo funciona

#### Comunicados

1. o navegador envia o formulario e o arquivo para o painel
2. o painel guarda um arquivo temporario local
3. cada turma recebe o comunicado com o campo `attachment`
4. o arquivo temporario e limpo ao final do job

#### Caixa de entrada

1. o navegador envia o formulario e o arquivo para o painel
2. o painel guarda um arquivo temporario local
3. o painel inicia o upload oficial em `users/self/files`
4. o painel conclui o upload seguindo o fluxo oficial de `File Uploads`
5. o `file_id` retornado entra em `attachment_ids[]` das `Conversations`
6. o arquivo temporario e limpo antes do envio em lote

### Limitacao atual

- nesta rodada o painel aceita `1 arquivo por lote` em `Comunicados`
- nesta rodada o painel aceita `1 arquivo por lote` em `Caixa de entrada`

## Stack

- Backend: `Python + Flask`
- Frontend: `HTML + CSS + JavaScript`
- Persistencia principal: `SQLAlchemy`
- Banco padrao local: `SQLite`
- Banco suportado: `MySQL`

## Arquitetura

- `src/web`
  rotas HTTP e respostas JSON
- `src/domain`
  regras de negocio de conexao, cursos, grupos, comunicados, recorrencias, mensagens, inativos e `.env`
- `src/services`
  cliente da API do Canvas com retry, timeout e paginacao
- `src/database`
  modelos, sessao e repositorios
- `src/jobs`
  gerenciamento de jobs, historico e progresso
- `static` e `templates`
  interface do painel

## Endpoints oficiais do Canvas usados

### Conexao e cursos

- `GET /api/v1/users/self`
- `GET /api/v1/courses`
- `GET /api/v1/courses/:course_id`

### Alunos e destinatarios

- `GET /api/v1/courses/:course_id/users?enrollment_type[]=student`
- `GET /api/v1/search/recipients`

### Comunicados e recorrencia

- `POST /api/v1/courses/:course_id/discussion_topics`
  com `is_announcement=true`
- `PUT /api/v1/courses/:course_id/discussion_topics/:topic_id`
  para corrigir titulo, mensagem e bloqueio de comentarios de comunicados ja criados
- `DELETE /api/v1/courses/:course_id/discussion_topics/:topic_id`

### Caixa de entrada

- `POST /api/v1/users/self/files`
- `POST /api/v1/conversations`

### Inativos

- `GET /api/v1/courses/:course_id/analytics/student_summaries`
- `GET /api/v1/courses/:course_id/enrollments?type[]=StudentEnrollment`
- `GET /api/v1/courses/:course_id/assignments`
- `GET /api/v1/courses/:course_id/quizzes`
- `GET /api/v1/courses/:course_id/assignments/:assignment_id/submissions`
- `GET /api/v1/courses/:course_id/quizzes/:quiz_id/submissions?include[]=submission`
- `POST /api/v1/conversations`

## Persistencia de dados

O app usa o banco definido em `DATABASE_URL`.

Exemplo com SQLite local:

```env
DATABASE_URL=sqlite:///data/canvas_bulk_panel.db
```

Exemplo com MySQL:

```env
DATABASE_URL=mysql+pymysql://usuario:senha@localhost:3306/canvas_bulk_panel
```

### Onde os dados ficam

- banco local: cursos, grupos, jobs, logs e resultados
- banco local: recorrencias de avisos e itens futuros criados no Canvas
- `.env`: configuracao sensivel local
- `data/reports/*.csv`: exportacoes de relatorio
- `logs/`: logs do servidor e do app

### Exclusao e limpeza

- excluir curso: `hard delete`
- excluir grupo: `hard delete`
- cancelar recorrencia: desativa a recorrencia e tenta apagar os avisos futuros no Canvas
- apagar banco em `Configuracoes`: `hard delete` das tabelas operacionais
- `.env` nao entra nessa limpeza

## Instalacao

### Com ambiente virtual

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### Com Conda

```powershell
conda create -n canvas-bulk-panel python=3.12 -y
conda activate canvas-bulk-panel
python -m pip install -r requirements.txt
```

### Com Docker

O repositorio agora inclui `Dockerfile` e `docker-compose.yml` para subir o painel em container mantendo:

- `.env` editavel pelo proprio painel
- `data/` persistente para SQLite, JSONs e CSVs
- `logs/` persistente para diagnostico local

No WSL Debian, entre na pasta montada:

```bash
cd /mnt/c/Eron_Lab/Canva_Api
cp .env.example .env
docker compose up --build -d
```

Para acompanhar:

```bash
docker compose ps
docker compose logs -f panel
```

### Para testes automatizados

```powershell
python -m pip install -r requirements-dev.txt
```

## Configuracao

Crie o `.env`:

```powershell
Copy-Item .env.example .env
```

Variaveis principais:

```env
DATABASE_URL=
CANVAS_BASE_URL=
CANVAS_ACCESS_TOKEN=
CANVAS_PERSONAL_ACCESS_TOKEN=
CANVAS_API_TOKEN=
CANVAS_BASE_URL_TEST=
CANVAS_ACCESS_TOKEN_TEST=
CANVAS_PERSONAL_ACCESS_TOKEN_TEST=
CANVAS_API_TOKEN_TEST=
CANVAS_ENVIRONMENT=real
ENABLE_LEGACY_JSON_IMPORT=false
HISTORY_LIMIT=25
```

Regras importantes:

- o token digitado na interface tem prioridade sobre o `.env`
- se a `Base URL` da tela ficar vazia, o painel usa a variavel do ambiente selecionado: `CANVAS_BASE_URL` para real ou `CANVAS_BASE_URL_TEST` para teste
- o switch da aba `Conexao` alterna entre ambiente real e teste, e envia `canvas_environment` para todos os fluxos que usam o Canvas
- `CANVAS_ENVIRONMENT=test` pode iniciar o painel ja no ambiente de teste, mas o operador ainda pode trocar pela interface
- o topo do painel mostra o ambiente ativo, a base efetiva e a origem do token
- o campo de token da tela fica vazio por seguranca, mesmo com token no `.env`
- o `.env` nao e recriado nem resetado ao iniciar o painel

## Como rodar

### Direto com Python

```powershell
python app.py
```

### Com Docker Compose

Depois de criar o `.env`, suba o painel:

```bash
docker compose up --build -d
```

Para parar sem apagar dados locais:

```bash
docker compose down
```

Persistencia e configuracao no modo Docker:

- `./.env` fica montado em `/app/.env`
- `./data` fica montado em `/app/data`
- `./logs` fica montado em `/app/logs`
- o `docker-compose.yml` ja publica a porta `5000` e sobrescreve `FLASK_HOST` para `0.0.0.0`

### Com os atalhos locais

```powershell
.\panel.bat
.\panel.bat stop
.\panel.bat restart
.\panel.bat status
```

Ao abrir `.\panel.bat` sem argumentos, o sistema agora mostra um mini launcher com botoes para:

- iniciar
- parar
- reiniciar
- checar status
- abrir o painel
- abrir logs

### No PowerShell

```powershell
.\panel.ps1 start
.\panel.ps1 stop
```

Acesse:

```text
http://127.0.0.1:5000
```

## Fluxo recomendado de uso

1. abra `Conexao` e valide o acesso ao Canvas
2. use o switch para confirmar se o ambiente ativo e `Real` ou `Teste`
3. abra `Organizacao`
4. use o `Catalogo do Canvas` para carregar e cadastrar os cursos
5. crie grupos com os cursos desejados
6. use `Comunicados` para avisos pontuais
7. use `Recorrencia` para gerar varios avisos futuros de uma vez
8. use `Caixa de entrada` para mensagens em lote
9. use `Inativos` para campanhas direcionadas a quem precisa de acompanhamento
10. confira `Relatorios` e baixe o CSV quando necessario

## Como validar em ambiente de teste do Canvas

### Recorrencia

1. use um curso pequeno de teste
2. crie uma recorrencia com poucas ocorrencias
3. confira no curso se os avisos futuros foram criados com agendamento
4. cancele a recorrencia
5. confira se os avisos futuros foram removidos do Canvas

### Inativos

1. use um curso pequeno de teste
2. selecione um criterio
3. rode primeiro em `Modo teste`
4. confira o preview e o resumo por turma
5. faca um envio real para um aluno controlado por voce
6. valide a mensagem na `Inbox` do Canvas desse aluno

Observacoes:

- em `test` ou `beta` do Canvas, a melhor validacao e pela Inbox e pelo relatorio do painel
- notificacoes por email dependem das preferencias do aluno no Canvas

## Relatorios disponiveis

- visao geral por periodo
- operacional por periodo
- volume diario
- cursos mais movimentados
- grupos mais usados
- recorrencias ativas
- falhas recentes
- historico detalhado por job
- edicao de comunicados criados com sucesso no Canvas

Os jobs de `Comunicados`, `Caixa de entrada` e `Inativos` entram no mesmo historico.

### Editar comunicado pelo relatorio

No detalhe de um lote de `Comunicados`, cada turma criada com sucesso e fora de `Modo teste` mostra a acao `Editar`.
O topo do detalhe tambem mostra `Editar avisos do lote` quando ha mais de um comunicado elegivel para correcao rapida.

O painel abre um modal com o titulo e a mensagem finais. Na edicao por lote, cada turma aparece em um card proprio com status de salvamento. Ao salvar, ele atualiza os `Discussion Topics` existentes no Canvas usando os `announcement_id` registrados no historico local.

Observacoes:

- anexos antigos permanecem como estavam
- registros de `Modo teste`, falhas e linhas sem `announcement_id` nao podem ser editados
- a edicao usa o token informado na aba `Conexao` ou o token configurado no `.env`

## Testes do projeto

### Validacao estatica

```powershell
python -m compileall app.py src tests
node --check static\js\app.js
```

### Testes automatizados

```powershell
pytest
```

### Auditoria de interface

Suite de UI com screenshots, navegacao em todas as abas e varredura de acessibilidade nos modais principais:

```powershell
npm install
npx playwright install chromium
npm run ui:audit
```

Arquivos gerados:

- relatorio HTML: `ui-audit/report/html/index.html`
- resumo consolidado: `ui-audit/report/summary.json`
- plano de acao: `docs/ui_audit_action_plan.md`
- checklist manual: `docs/manual_test_checklist.md`

Importante:

- a auditoria usa mocks de API em `ui-audit/tests`
- ela nao envia nada para o Canvas real
- o app sobe isolado em `http://127.0.0.1:5070`

## Codex customization

O repositorio agora inclui customizacao nativa para Codex:

- `AGENTS.md` no root com regras persistentes do projeto
- `src/AGENTS.md` e `static/AGENTS.md` com orientacoes proximas do codigo
- skills de repositorio em `.agents/skills` para QA manual e release

Veja os detalhes em `docs/codex_customization.md`.
## Empacotamento

Build local com PyInstaller:

```powershell
.\build.ps1
```

## Estrutura de pastas

```text
Canva_Api/
|-- app.py
|-- CHANGELOG.md
|-- README.md
|-- .env.example
|-- panel.bat
|-- panel.ps1
|-- build.ps1
|-- package.json
|-- playwright.config.js
|-- requirements.txt
|-- requirements-dev.txt
|-- docs/
|   |-- database_erd.md
|   |-- manual_test_checklist.md
|   `-- ui_audit_action_plan.md
|-- src/
|   |-- app_factory.py
|   |-- config.py
|   |-- database/
|   |-- domain/
|   |-- jobs/
|   |-- services/
|   |-- utils/
|   `-- web/
|-- static/
|   |-- css/
|   `-- js/
|-- templates/
|-- ui-audit/
|   |-- .env.ui
|   `-- tests/
|-- data/
`-- logs/
```

## Exemplos reais de chamadas da API

### Criar comunicado

```http
POST /api/v1/courses/123/discussion_topics
Authorization: Bearer <token>
Content-Type: application/x-www-form-urlencoded

title=Aviso&message=<p>Mensagem</p>&is_announcement=true&published=true
```

### Criar comunicado agendado

```http
POST /api/v1/courses/123/discussion_topics
Authorization: Bearer <token>
Content-Type: application/x-www-form-urlencoded

title=Encontro semanal&message=<p>Lembrete</p>&is_announcement=true&published=true&delayed_post_at=2030-05-01T22:00:00Z
```

### Cancelar aviso futuro

```http
DELETE /api/v1/courses/123/discussion_topics/9999
Authorization: Bearer <token>
```

### Buscar alunos

```http
GET /api/v1/courses/123/users?enrollment_type[]=student
Authorization: Bearer <token>
```

### Buscar destinatarios

```http
GET /api/v1/search/recipients?search=Curso&type=context&permissions[]=send_messages
Authorization: Bearer <token>
```

### Enviar mensagem

```http
POST /api/v1/conversations
Authorization: Bearer <token>
Content-Type: application/x-www-form-urlencoded

recipients[]=1234&subject=Aviso&body=Mensagem&context_code=course_123
```

### Buscar acesso e minutos de inativos

```http
GET /api/v1/courses/123/analytics/student_summaries
Authorization: Bearer <token>
```

```http
GET /api/v1/courses/123/enrollments?type[]=StudentEnrollment
Authorization: Bearer <token>
```

### Buscar atividades de inativos

```http
GET /api/v1/courses/123/assignments
Authorization: Bearer <token>
```

```http
GET /api/v1/courses/123/quizzes
Authorization: Bearer <token>
```

### Buscar submissao de assign ou quiz

```http
GET /api/v1/courses/123/assignments/456/submissions
Authorization: Bearer <token>
```

```http
GET /api/v1/courses/123/quizzes/789/submissions?include[]=submission
Authorization: Bearer <token>
```
