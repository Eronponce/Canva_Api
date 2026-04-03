# Canvas Bulk Panel

Painel web local para operar em lote no Canvas LMS usando apenas endpoints oficiais da API.

## O que o sistema faz

- valida conexao com o Canvas usando `base_url` e token vindos da tela ou do `.env`
- organiza cursos cadastrados e grupos de turmas
- busca no Canvas os cursos acessiveis e permite cadastrar varios de uma vez
- publica comunicados em lote
- envia mensagens pela caixa de entrada do Canvas em lote
- envia mensagens para alunos inativos com base em analytics e progresso de modulos
- registra historico, resultados por turma e exportacao em CSV
- permite limpar todo o banco local com confirmacao digitada

## Modulos da interface

1. `Conexao`
   teste de acesso ao Canvas
2. `Organizacao`
   cursos cadastrados, catalogo do Canvas e grupos
3. `Comunicados`
   anuncios por grupos salvos ou cursos especificos
4. `Caixa de entrada`
   mensagens em lote por grupos salvos ou cursos especificos
5. `Inativos`
   mensagem para alunos sem acesso nenhum ou com recursos pendentes
6. `Configuracoes`
   resumo operacional, editor do `.env` e zona de perigo
7. `Relatorios`
   historico, analitico e download de CSV

## O modulo Inativos

O modulo `Inativos` foi feito para o fluxo:

1. escolher grupos salvos ou cursos especificos
2. escolher o criterio
3. buscar a quantidade por turma
4. revisar quem vai receber
5. enviar a mensagem

### Criterios suportados

- `Sem acesso nenhum`
  usa `page_views = 0` e `participations = 0`
- `Com recursos pendentes`
  usa requisitos de modulos nao concluidos
- `Sem acesso nenhum ou com recursos pendentes`

### Importante

- o envio acontece pela `Inbox` do Canvas usando `Conversations`
- nao e um envio direto de email
- o aluno pode receber notificacao por email se as preferencias dele no Canvas estiverem configuradas para isso
- o criterio de `recursos pendentes` depende de requisitos de modulos configurados no curso

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
  regras de negocio de conexao, cursos, grupos, comunicados, mensagens, inativos e `.env`
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

### Comunicados

- `POST /api/v1/courses/:course_id/discussion_topics`
  com `is_announcement=true`

### Caixa de entrada

- `POST /api/v1/conversations`

### Inativos

- `GET /api/v1/courses/:course_id/analytics/student_summaries`
- `GET /api/v1/courses/:course_id/bulk_user_progress`
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
- `.env`: configuracao sensivel local
- `data/reports/*.csv`: exportacoes de relatorio
- `logs/`: logs do servidor e do app

### Exclusao e limpeza

- excluir curso: `hard delete`
- excluir grupo: `hard delete`
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
ENABLE_LEGACY_JSON_IMPORT=false
HISTORY_LIMIT=25
```

Regras importantes:

- o token digitado na interface tem prioridade sobre o `.env`
- se a `Base URL` da tela ficar vazia, o painel usa `CANVAS_BASE_URL` do `.env`
- o campo de token da tela fica vazio por seguranca, mesmo com token no `.env`
- o `.env` nao e recriado nem resetado ao iniciar o painel

## Como rodar

### Direto com Python

```powershell
python app.py
```

### Com os atalhos locais

```powershell
.\panel.bat
.\panel.bat stop
.\panel.bat restart
.\panel.bat status
```

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
2. abra `Organizacao`
3. use o `Catalogo do Canvas` para carregar e cadastrar os cursos
4. crie grupos com os cursos desejados
5. rode `Modo teste` em `Comunicados`, se necessario
6. rode `Modo teste` em `Caixa de entrada`, se necessario
7. abra `Inativos`
8. selecione os grupos ou cursos
9. clique em `Buscar quantidade por turma`
10. confira o preview
11. rode `Modo teste` ou envie de verdade
12. confira `Relatorios` e baixe o CSV

## Como validar em ambiente de teste do Canvas

Para validar o modulo `Inativos` com seguranca:

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
- falhas recentes
- historico detalhado por job

Os jobs de `Comunicados`, `Caixa de entrada` e `Inativos` entram no mesmo historico.

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

## Empacotamento

Build local com PyInstaller:

```powershell
.\build.ps1
```

## Estrutura de pastas

```text
Canva_Api/
|-- app.py
|-- README.md
|-- .env.example
|-- panel.bat
|-- panel.ps1
|-- build.ps1
|-- requirements.txt
|-- requirements-dev.txt
|-- docs/
|   `-- database_erd.md
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

### Buscar analytics dos alunos

```http
GET /api/v1/courses/123/analytics/student_summaries
Authorization: Bearer <token>
```

### Buscar progresso de modulos

```http
GET /api/v1/courses/123/bulk_user_progress
Authorization: Bearer <token>
```
