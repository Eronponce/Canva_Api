# Manual Test Checklist

Roteiro de teste manual completo do `Canvas Bulk Panel`.

Data de referencia: `2026-04-03`

## Objetivo

Validar manualmente todos os fluxos principais do sistema, confirmando:

- funcionamento da interface
- integracao com o Canvas
- persistencia local
- resultados por lote
- seguranca operacional basica

## Ambiente recomendado

- usar primeiro um ambiente `test` do Canvas
- usar um token com permissao real para os cursos de teste
- abrir o painel em `http://127.0.0.1:5000`
- de preferencia usar um navegador em aba anonima ou fazer `Ctrl+F5`

## Massa de teste sugerida

Antes de testar, tente separar:

- `2 a 3 cursos` pequenos, com poucos alunos
- `1 curso` com requisitos de modulos configurados
- `1 curso` sem requisitos de modulos
- `1 aluno` que voce consiga acompanhar pela Inbox do Canvas
- `1 grupo` com pelo menos `2 cursos`
- `1 arquivo pequeno` para anexo, por exemplo `PDF` ou `TXT`

Se possivel, inclua:

- `1 aluno` matriculado em mais de um curso, para validar deduplicacao

## Convencoes deste roteiro

Em cada caso:

- `Passos`: o que fazer no painel
- `Esperado no painel`: o que deve acontecer na interface
- `Esperado no Canvas`: o que deve existir do outro lado

---

## 1. Inicializacao do painel

### 1.1 Subida pelo launcher

Passos:

1. Execute `panel.bat`.
2. Use a mini interface para iniciar o sistema.
3. Abra o painel no navegador.

Esperado no painel:

- a aplicacao abre normalmente
- a navbar superior mostra `Conexao`, `Organizacao`, `Comunicados`, `Recorrencia`, `Caixa de entrada`, `Inativos`, `Configuracoes`, `Relatorios`

Esperado no sistema:

- o servidor responde em `http://127.0.0.1:5000`
- o launcher permite `iniciar`, `parar`, `reiniciar` e `status`

### 1.2 Estado inicial limpo

Passos:

1. Recarregue a pagina com `Ctrl+F5`.
2. Navegue por todas as abas sem executar nenhuma acao.

Esperado no painel:

- sem scroll horizontal exagerado
- sem textos cortados
- sem erros visiveis de layout
- modais fecham corretamente
- nenhum painel quebra ao trocar de aba

---

## 2. Conexao

### 2.1 Conexao usando `.env`

Passos:

1. Deixe `Base URL` vazia.
2. Deixe `Token de acesso` vazio.
3. Clique em `Testar conexao`.

Esperado no painel:

- o sistema usa os valores do `.env`
- o resultado informa sucesso
- aparece usuario autenticado
- aparece a origem do token ou indicacao de uso do `.env`

Esperado no Canvas:

- a validacao passa em `users/self`

### 2.2 Conexao usando valores digitados

Passos:

1. Preencha `Base URL`.
2. Preencha `Token de acesso`.
3. Clique em `Testar conexao`.

Esperado no painel:

- o resultado mostra sucesso
- o badge muda para estado positivo

### 2.3 Falha de autenticacao

Passos:

1. Preencha um token invalido.
2. Clique em `Testar conexao`.

Esperado no painel:

- mensagem clara de erro
- status `401` ou equivalente
- nenhuma outra tela deve quebrar

---

## 3. Organizacao

### 3.1 Cadastrar curso manualmente

Passos:

1. Digite um numero de curso valido.
2. Clique em `Adicionar curso`.

Esperado no painel:

- o curso entra na lista local com `nome`, `codigo` e `numero`
- se o numero for invalido, aparece erro claro

Esperado no Canvas:

- o nome do curso e resolvido pela API oficial

### 3.2 Buscar catalogo do Canvas

Passos:

1. Entre em `Organizacao`.
2. Clique em `Buscar no Canvas`.
3. Filtre pelo campo de busca.

Esperado no painel:

- os cursos acessiveis aparecem
- cursos ja cadastrados ficam identificados
- a busca filtra por nome, codigo ou numero

### 3.3 Cadastrar varios cursos do catalogo

Passos:

1. Marque varios cursos no catalogo.
2. Clique em `Cadastrar selecionados`.

Esperado no painel:

- todos entram na lista de cursos cadastrados
- nao cria duplicados indevidos

### 3.4 Criar grupo de turmas

Passos:

1. Clique em `Novo grupo`.
2. Informe nome e descricao.
3. Selecione cursos.
4. Salve.

Esperado no painel:

- o grupo aparece na lista
- os cursos ficam associados corretamente

### 3.5 Editar grupo

Passos:

1. Clique em `Editar` em um grupo.
2. Abra o modal.
3. Adicione e remova cursos.
4. Salve.

Esperado no painel:

- o modal abre separado da tela principal
- a selecao funciona sem subir a lista abruptamente enquanto ainda esta em foco
- ao salvar, a lista do grupo reflete a edicao

### 3.6 Excluir grupo

Passos:

1. Exclua um grupo.

Esperado no painel:

- o grupo sai da lista
- os cursos individuais continuam cadastrados

---

## 4. Comunicados

### 4.1 Envio por grupos salvos

Passos:

1. Entre em `Comunicados`.
2. Deixe `Grupos salvos` ativo.
3. Selecione um ou mais grupos.
4. Preencha titulo e mensagem.
5. Clique em `Publicar`.

Esperado no painel:

- aparece resumo operacional
- aparece preview da mensagem
- abre revisao final antes do envio
- depois do envio, o bloco `Logs do lote` mostra resultado por turma

Esperado no Canvas:

- cada curso selecionado recebe um `announcement`
- o titulo e a mensagem batem com o informado

### 4.2 Envio por cursos especificos

Passos:

1. Troque para `Cursos especificos`.
2. Marque cursos diretamente.
3. Preencha titulo e mensagem.
4. Publique.

Esperado no painel:

- o resumo operacional muda para o modo de cursos
- o envio contempla apenas os cursos marcados

### 4.3 Placeholder por disciplina

Passos:

1. Use `{{course_name}}`, `{{course_ref}}` e `{{course_code}}` no titulo e no corpo.
2. Clique nos chips para inserir, sem digitar manualmente.
3. Veja a pre-visualizacao.

Esperado no painel:

- os chips inserem placeholders validos
- o preview mostra a resolucao com a primeira turma selecionada
- placeholders invalidos bloqueiam o envio

Esperado no Canvas:

- cada curso recebe seu proprio nome/codigo resolvido no texto

### 4.4 Anexo em comunicado

Passos:

1. Selecione um arquivo.
2. Publique um comunicado.

Esperado no painel:

- o resumo mostra que ha anexo
- o lote conclui sem quebrar o restante do payload

Esperado no Canvas:

- o anexo aparece no anuncio

### 4.5 Modo de publicacao

Passos:

1. Teste `Publicar imediatamente`.
2. Teste `Salvar como rascunho`.
3. Teste `Agendar data e hora`.

Esperado no painel:

- o resumo e a revisao refletem o modo escolhido

Esperado no Canvas:

- imediato: anuncio publicado
- rascunho: anuncio nao publicado
- agendado: anuncio com `delayed_post_at`

### 4.6 Bloquear comentarios

Passos:

1. Ative `Bloquear comentarios`.
2. Publique um aviso.

Esperado no Canvas:

- o anuncio fica com comentarios bloqueados

### 4.7 Modo teste

Passos:

1. Ative `Modo teste`.
2. Execute o envio.

Esperado no painel:

- o sistema simula o lote
- aparece relatorio
- nao cria anuncio real

Esperado no Canvas:

- nenhum comunicado novo deve ser criado

---

## 5. Recorrencia

### 5.1 Criar recorrencia semanal

Passos:

1. Entre em `Recorrencia`.
2. Escolha grupos ou cursos.
3. Preencha titulo e mensagem.
4. Escolha frequencia semanal.
5. Defina inicio, intervalo e quantidade.
6. Clique em `Prever datas`.
7. Clique em `Criar recorrencia`.

Esperado no painel:

- o preview mostra todas as datas previstas
- abre revisao final
- a recorrencia aparece na lista
- a agenda mostra as proximas publicacoes

Esperado no Canvas:

- varios avisos futuros sao criados com `delayed_post_at`

### 5.2 Criar recorrencia diaria

Passos:

1. Repita o fluxo escolhendo frequencia diaria.

Esperado no painel:

- datas calculadas de forma coerente

### 5.3 Preview obrigatorio

Passos:

1. Gere preview.
2. Altere qualquer campo importante, por exemplo turma, titulo ou data.
3. Tente salvar sem prever de novo.

Esperado no painel:

- o sistema invalida o preview anterior
- ele exige nova previsao antes de criar ou salvar

### 5.4 Editar recorrencia em modal

Passos:

1. Clique em `Editar` numa recorrencia existente.
2. No modal, remova uma turma e adicione outra.
3. Clique em `Prever impacto`.
4. Salve.

Esperado no painel:

- o modal abre separado da tela principal
- o diff mostra o que entra, sai ou permanece
- a agenda e a lista sao atualizadas apos salvar

Esperado no Canvas:

- avisos futuros das turmas removidas sao apagados
- avisos futuros das turmas novas sao criados
- avisos ja publicados permanecem

### 5.5 Cancelar avisos futuros

Passos:

1. Clique em `Cancelar`.
2. No modal, confirme conforme solicitado.

Esperado no painel:

- cancelamento seguro por modal
- a recorrencia muda de estado

Esperado no Canvas:

- apenas avisos futuros ainda nao publicados devem ser removidos

### 5.6 Agenda das proximas publicacoes

Passos:

1. Veja a agenda.
2. Use busca e janela de dias.

Esperado no painel:

- itens aparecem em ordem cronologica
- filtros afetam a agenda
- destaque visual para hoje, amanha ou proximos dias

---

## 6. Caixa de entrada

### 6.1 Envio por grupos

Passos:

1. Entre em `Caixa de entrada`.
2. Selecione grupos salvos.
3. Preencha assunto e mensagem.
4. Envie.

Esperado no painel:

- aparece resumo operacional
- abre revisao final
- o resultado do envio aparece abaixo

Esperado no Canvas:

- a mensagem chega na Inbox dos alunos

### 6.2 Envio por cursos especificos

Passos:

1. Troque para `Cursos especificos`.
2. Marque cursos.
3. Envie.

Esperado no painel:

- so os cursos selecionados entram no lote

### 6.3 Placeholder de aluno

Passos:

1. Use `{{student_name}}` na mensagem.
2. Veja o preview e a revisao.
3. Envie.

Esperado no painel:

- o resumo avisa que a estrategia passa a ser por usuario
- o preview usa uma amostra de aluno

Esperado no Canvas:

- cada aluno recebe a mensagem personalizada com o proprio nome

### 6.4 Placeholders de curso

Passos:

1. Use `{{course_name}}`, `{{course_ref}}` e `{{course_code}}`.

Esperado no Canvas:

- cada aluno recebe o contexto correto do curso

### 6.5 Anexo na caixa de entrada

Passos:

1. Selecione um arquivo.
2. Envie a mensagem.

Esperado no painel:

- resumo operacional mostra anexo
- lote conclui com sucesso ou erro claro de upload

Esperado no Canvas:

- a mensagem chega com o anexo vinculado

### 6.6 Evitar duplicidade entre turmas

Passos:

1. Escolha cursos com um aluno em comum.
2. Ative `Evitar duplicidade entre turmas`.
3. Envie.

Esperado no painel:

- o resumo mostra deduplicacao
- a contagem final de destinatarios cai quando houver duplicados

Esperado no Canvas:

- o mesmo aluno nao recebe varias mensagens iguais

### 6.7 Modo teste

Passos:

1. Ative `Modo teste`.
2. Execute.

Esperado no painel:

- aparece resultado simulado

Esperado no Canvas:

- nenhuma conversa nova deve ser criada

Observacao:

- o envio e pela `Inbox` do Canvas
- notificacao por email depende das preferencias do aluno

---

## 7. Inativos

### 7.1 Buscar por curso ou grupo

Passos:

1. Entre em `Inativos`.
2. Escolha grupos ou cursos.
3. Selecione o criterio.
4. Clique em `Buscar quantidade por turma`.

Esperado no painel:

- o resumo da selecao e preenchido
- a lista `Quem vai receber` mostra turmas e alunos encontrados

### 7.2 Testar criterios

Passos:

1. Teste `Sem acesso nenhum`.
2. Teste `Com recursos pendentes`.
3. Teste `Sem acesso nenhum ou com recursos pendentes`.
4. Teste `Sem atividade ha X dias`.
5. Teste `Atividade total ate X minutos`.

Esperado no painel:

- os totais mudam de acordo com o criterio
- cursos sem requisitos de modulos devem refletir essa limitacao no preview

### 7.3 Variaveis seguras

Passos:

1. Use os chips para inserir:
   - `{{student_name}}`
   - `{{course_name}}`
   - `{{course_ref}}`
   - `{{course_code}}`
   - `{{reason}}`
2. Veja o preview.

Esperado no painel:

- preview com aluno e motivo de exemplo
- placeholders invalidos bloqueiam o envio

### 7.4 Envio real

Passos:

1. Depois do preview, clique em enviar.

Esperado no painel:

- revisao final antes do envio
- resultado do envio abaixo da lista

Esperado no Canvas:

- os alunos encontrados recebem mensagem na Inbox

### 7.5 Modo teste

Passos:

1. Ative `Modo teste`.
2. Execute.

Esperado no Canvas:

- nenhuma mensagem real deve ser enviada

---

## 8. Configuracoes

### 8.1 Editor do `.env`

Passos:

1. Entre em `Configuracoes`.
2. Revele o `.env`.
3. Aguarde.

Esperado no painel:

- os valores aparecem mascarados/protegidos visualmente
- a exibicao some automaticamente apos cerca de `10 segundos`

### 8.2 Salvar configuracoes do `.env`

Passos:

1. Ajuste `CANVAS_BASE_URL` ou token.
2. Salve.
3. Volte para `Conexao` e teste.

Esperado no painel:

- o `.env` e salvo
- a conexao passa a usar os novos valores

### 8.3 Configuracao operacional

Passos:

1. Revise os blocos de configuracao operacional.

Esperado no painel:

- o estado atual do sistema aparece sem quebrar layout

### 8.4 Zona de perigo

Passos:

1. Use a limpeza total do banco apenas se voce aceitar perder cursos, grupos e historico.
2. Digite a confirmacao exigida.
3. Execute.

Esperado no painel:

- confirmacao digitada obrigatoria
- o banco local e limpo

Esperado no sistema:

- cursos, grupos, historico e resultados somem do painel
- `.env` nao deve ser apagado

---

## 9. Relatorios

### 9.1 Analitico por periodo

Passos:

1. Entre em `Relatorios`.
2. Teste periodos diferentes.

Esperado no painel:

- cards com volume atual
- comparacao com periodo anterior equivalente
- deltas coerentes

### 9.2 Historico de envios

Passos:

1. Execute alguns lotes antes.
2. Veja a lista de historico.
3. Abra o detalhe de um relatorio.

Esperado no painel:

- os jobs aparecem em ordem util
- o detalhe mostra resumo, resultados por curso e falhas

### 9.3 CSV

Passos:

1. Baixe um CSV de um relatorio.

Esperado no sistema:

- o arquivo baixa corretamente
- o conteudo corresponde ao job selecionado

---

## 10. Modais

### 10.1 Modal de grupo

Passos:

1. Abra criacao e edicao de grupo.

Esperado no painel:

- foco visual claro
- fechamento normal
- selecao de cursos sem salto abrupto enquanto ainda esta em foco

### 10.2 Modal de revisao de envio

Passos:

1. Dispare revisao em `Comunicados`, `Caixa de entrada` e `Inativos`.

Esperado no painel:

- resumo do alvo
- mensagem ou anuncio
- informacao de anexo, criterio ou estrategia quando aplicavel

### 10.3 Modal de edicao de recorrencia

Passos:

1. Abra `Editar` em uma recorrencia.

Esperado no painel:

- layout separado do formulario de criacao
- preview de impacto funcional

### 10.4 Modal de cancelamento de recorrencia

Passos:

1. Abra `Cancelar`.

Esperado no painel:

- o modal explica que so os avisos futuros serao removidos
- a confirmacao e segura

---

## 11. Verificacao no Canvas

Depois de cada fluxo real, confira no Canvas:

- `Comunicados`: anuncio criado na turma certa, com titulo, corpo, anexo, estado publicado/rascunho/agendado e bloqueio de comentarios quando marcado
- `Recorrencia`: varios anuncios futuros criados
- `Caixa de entrada`: mensagem criada na Inbox dos alunos
- `Inativos`: mensagem criada na Inbox apenas para o subconjunto filtrado

Observacao importante:

- `Caixa de entrada` e `Inativos` usam `Conversations`
- isso significa Inbox do Canvas, nao email direto
- o email depende das preferencias de notificacao do aluno

---

## 12. Sinais de problema

Trate como bug se ocorrer qualquer um destes:

- scroll horizontal grande sem motivo
- modal que nao fecha ou perde foco
- lista que reordena de forma agressiva enquanto voce ainda seleciona
- preview diferente do que foi realmente enviado
- placeholder literal aparecendo no Canvas sem ser resolvido
- modo teste criando registro real no Canvas
- exclusao em `Zona de perigo` apagando `.env`
- agenda de recorrencia nao atualizando depois de editar
- erro silencioso sem mensagem clara para o usuario

---

## 13. Ordem recomendada de execucao

Se quiser fazer uma rodada completa, use esta ordem:

1. `Conexao`
2. `Organizacao`
3. `Comunicados`
4. `Recorrencia`
5. `Caixa de entrada`
6. `Inativos`
7. `Configuracoes`
8. `Relatorios`
9. `Verificacao final no Canvas`

---

## 14. Evidencias recomendadas

Durante o teste, vale guardar:

- print da tela antes do envio
- print da revisao final
- print do resultado do lote
- print do Canvas mostrando o efeito real
- CSV exportado de pelo menos um job

Isso ajuda muito a comparar `preview x execucao x resultado real`.
