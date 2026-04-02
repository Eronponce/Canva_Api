# Canvas Bulk Panel

Sistema web local para operacoes em lote no Canvas LMS usando apenas endpoints oficiais da API.

## Arquitetura

- Backend: `Python + Flask`
- Frontend: `HTML + CSS + JavaScript`
- Persistencia local: `JSON` para cursos cadastrados, grupos e historico
- Logs: arquivo local + logs por job

Camadas:

- `frontend`: interface, navegacao, formularios, preview e relatorios
- `services`: cliente HTTP do Canvas com retry, timeout e paginacao
- `domain`: regras de negocio para conexao, organizacao de salas, comunicados e mensagens
- `storage`: arquivos JSON locais para grupos, cursos e historico
- `config`: `.env`, caminhos e limites operacionais

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
  - com `is_announcement=true`

Caixa de entrada:

- `POST /api/v1/conversations`

Paginacao:

- suporte ao header oficial `Link`

## Fluxo de dados

1. A interface coleta `base_url`, token e a selecao de grupos.
2. O backend valida as credenciais e resolve os cursos de cada grupo.
3. O cliente Canvas chama somente endpoints oficiais.
4. O processamento roda em background, turma por turma.
5. O frontend faz polling do job e mostra progresso, resumo e CSV.
6. O historico local guarda os ultimos jobs.

## Interface atual

- `Conexao`
  - validacao de ambiente, token e usuario autenticado
- `Organizacao de salas`
  - cadastro simples de cursos por numero
  - cadastro e edicao de grupos por modal
- `Comunicados`
  - selecao de um ou mais grupos, ou todos os grupos
  - preview HTML, dry run, agendamento e bloqueio de comentarios
- `Caixa de entrada`
  - mesma logica de selecao por grupos
  - envio por contexto ou por usuario
- `Configuracoes`
  - resumo operacional
  - editor local do arquivo `.env`
- `Relatorios`
  - historico local, detalhes compactos e download do CSV

## Estrutura de pastas

```text
Canva_Api/
├── app.py
├── README.md
├── .env.example
├── build.ps1
├── requirements.txt
├── requirements-dev.txt
├── data/
│   ├── course_groups.json
│   ├── registered_courses.json
│   ├── history.json
│   └── reports/
├── logs/
├── src/
│   ├── app_factory.py
│   ├── config.py
│   ├── domain/
│   ├── jobs/
│   ├── services/
│   ├── storage/
│   ├── utils/
│   └── web/
├── static/
│   ├── css/
│   └── js/
├── templates/
└── tests/
```

## Instalacao

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Para testes automatizados:

```powershell
python -m pip install -r requirements-dev.txt
```

## Configuracao

Crie o `.env` a partir do exemplo:

```powershell
Copy-Item .env.example .env
```

Voce pode usar qualquer um destes aliases para o token:

- `CANVAS_ACCESS_TOKEN`
- `CANVAS_PERSONAL_ACCESS_TOKEN`
- `CANVAS_API_TOKEN`

Observacoes:

- O token do campo da interface tem prioridade sobre o `.env`.
- O token nao e salvo no navegador.
- A base URL deve ser informada sem `/api/v1` no final.

## Como rodar

```powershell
python app.py
```

Abra:

```text
http://127.0.0.1:5000
```

Atalho local para iniciar e parar o painel:

```powershell
.\panel.bat
.\panel.bat stop
.\panel.bat restart
.\panel.bat status
```

Ou direto no PowerShell:

```powershell
.\panel.ps1 start
.\panel.ps1 stop
```

## Fluxo recomendado de uso

1. Abra `Conexao` e valide `base_url` e token.
2. Entre em `Organizacao de salas`.
3. Cadastre os numeros dos cursos.
4. Crie os grupos que vao receber os recados.
5. Abra `Comunicados` ou `Caixa de entrada`.
6. Escolha entre `grupos salvos` ou `cursos especificos`.
7. Rode primeiro em `Modo teste`.
8. Consulte `Relatorios` e baixe o CSV.

## Testes

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

O projeto inclui `build.ps1` com PyInstaller:

```powershell
.\build.ps1
```

## Exemplos de chamadas da API

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

Enviar mensagem:

```http
POST /api/v1/conversations
Authorization: Bearer <token>
Content-Type: application/x-www-form-urlencoded

recipients[]=1234&subject=Aviso&body=Mensagem&context_code=course_123
```
