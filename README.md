# Canvas Bulk Panel

Painel web local para operar em lote no Canvas LMS usando somente endpoints oficiais da API.

## O que o sistema faz

- testa a conexao com o Canvas usando `base_url` e token vindos da tela ou do `.env`
- organiza cursos e grupos de turmas
- busca no Canvas todos os cursos acessiveis e permite cadastrar varios de uma vez
- publica comunicados em lote
- envia mensagens da caixa de entrada em lote
- registra historico, resultados por curso e exportacao em CSV
- oferece limpeza total do banco local com confirmacao digitada

## Stack

- Backend: `Python + Flask`
- Frontend: `HTML + CSS + JavaScript`
- Persistencia principal: `SQLAlchemy`
- Banco padrao local: `SQLite`
- Banco suportado para evolucao: `MySQL`

## Arquitetura atual

- `src/web`
  rotas HTTP e respostas JSON
- `src/domain`
  regras de negocio de conexao, organizacao, comunicados, mensagens e `.env`
- `src/services`
  cliente da API do Canvas com retry, timeout e paginacao
- `src/database`
  modelos, sessao, repositorios e importador legado opcional
- `src/jobs`
  gerenciamento de jobs em background e historico
- `static` e `templates`
  interface do painel

## Endpoints oficiais do Canvas usados

Conexao e cursos:

- `GET /api/v1/users/self`
- `GET /api/v1/courses`
- `GET /api/v1/courses/:course_id`

Alunos e destinatarios:

- `GET /api/v1/courses/:course_id/users?enrollment_type[]=student`
- `GET /api/v1/search/recipients`

Comunicados:

- `POST /api/v1/courses/:course_id/discussion_topics`
  com `is_announcement=true`

Caixa de entrada:

- `POST /api/v1/conversations`

## Fluxo principal da interface

1. `Conexao`
   teste de acesso ao ambiente do Canvas
2. `Organizacao`
   cadastro manual de cursos, busca no catalogo do Canvas e grupos
3. `Comunicados`
   envio por grupos salvos ou cursos especificos
4. `Caixa de entrada`
   envio por grupos salvos ou cursos especificos
5. `Configuracoes`
   editor do `.env`, resumo operacional e zona de perigo
6. `Relatorios`
   analitico, historico detalhado e download de CSV

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

Observacoes:

- se `DATABASE_URL` ficar vazio, o painel usa `SQLite` em `data/canvas_bulk_panel.db`
- o SQLite e a fonte principal quando ele estiver em uso
- a importacao dos JSONs antigos ficou opcional e desligada por padrao
- para importar legados uma unica vez, use `ENABLE_LEGACY_JSON_IMPORT=true`

## Como os dados ficam guardados

- banco local: cursos, grupos, jobs, logs e resultados
- `.env`: configuracao sensivel local
- `data/reports/*.csv`: exportacoes
- `logs/`: logs do servidor e do app

## Exclusao e limpeza

- excluir curso: `hard delete`
- excluir grupo: `hard delete`
- apagar banco em `Configuracoes`: `hard delete` das tabelas operacionais do app
- `.env` nao entra nessa limpeza

Campos de soft delete continuam no modelo para historico e expansao futura, mas os botoes atuais de exclusao de curso e grupo removem os registros de verdade.

## Estrutura de pastas

```text
Canva_Api/
├── app.py
├── README.md
├── .env.example
├── panel.bat
├── panel.ps1
├── build.ps1
├── requirements.txt
├── requirements-dev.txt
├── docs/
│   └── database_erd.md
├── src/
│   ├── app_factory.py
│   ├── config.py
│   ├── database/
│   ├── domain/
│   ├── jobs/
│   ├── services/
│   ├── utils/
│   └── web/
├── static/
│   ├── css/
│   └── js/
├── templates/
├── data/
└── logs/
```

## Instalacao

Com ambiente virtual normal:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Com seu ambiente Conda:

```powershell
conda create -n canvas-bulk-panel python=3.12 -y
conda activate canvas-bulk-panel
python -m pip install -r requirements.txt
```

Para testes automatizados:

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
- se a `Base URL` da tela ficar vazia, o painel usa a `CANVAS_BASE_URL` do `.env`
- o campo de token da tela fica vazio por seguranca, mesmo com token no `.env`
- o `.env` nao e recriado nem resetado ao iniciar o painel

## Como rodar

Direto com Python:

```powershell
python app.py
```

Ou com os atalhos locais:

```powershell
.\panel.bat
.\panel.bat stop
.\panel.bat restart
.\panel.bat status
```

No PowerShell:

```powershell
.\panel.ps1 start
.\panel.ps1 stop
```

Acesse:

```text
http://127.0.0.1:5000
```

## Como testar o fluxo

1. abra `Conexao` e valide o acesso ao Canvas
2. abra `Organizacao`
3. cadastre cursos manualmente ou use `Catalogo do Canvas`
4. crie grupos com os cursos desejados
5. rode um `Modo teste` em `Comunicados`
6. rode um `Modo teste` em `Caixa de entrada`
7. confira `Relatorios` e baixe o CSV

## Relatorios disponiveis

- visao geral por periodo
- operacional por periodo
- volume diario
- cursos mais movimentados
- grupos mais usados
- falhas recentes
- historico detalhado por job

As secoes analiticas sao recolhiveis para usar melhor o espaco da tela.

## Testes do projeto

Sintaxe:

```powershell
python -m compileall app.py src tests
node --check static\js\app.js
```

Automatizados:

```powershell
pytest
```

## Empacotamento

Build local com PyInstaller:

```powershell
.\build.ps1
```

## Exemplos reais de chamadas da API

Criar comunicado:

```http
POST /api/v1/courses/123/discussion_topics
Authorization: Bearer <token>
Content-Type: application/x-www-form-urlencoded

title=Aviso&message=<p>Mensagem</p>&is_announcement=true&published=true
```

Buscar alunos:

```http
GET /api/v1/courses/123/users?enrollment_type[]=student
Authorization: Bearer <token>
```

Buscar destinatarios:

```http
GET /api/v1/search/recipients?search=Curso&type=context&permissions[]=send_messages
Authorization: Bearer <token>
```

Enviar mensagem:

```http
POST /api/v1/conversations
Authorization: Bearer <token>
Content-Type: application/x-www-form-urlencoded

recipients[]=1234&subject=Aviso&body=Mensagem&context_code=course_123
```
