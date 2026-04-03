# UI Audit Action Plan

Ultima bateria executada em `2026-04-03` usando:

- `Playwright`
- `@axe-core/playwright`
- mocks seguros de API para nao tocar no Canvas real

Status atual da rodada:

- `8 telas` auditadas
- `7 modais` auditados
- `0 violacoes automaticas` restantes de overflow horizontal
- `0 violacoes automaticas` restantes de acessibilidade na varredura configurada

## Ajustes concluidos nesta rodada

- correcao do overflow horizontal causado pelos `toggle switches`
- nomes acessiveis adicionados aos filtros de `Recorrencia`
- regioes rolaveis da `Recorrencia` ficaram acessiveis por teclado
- infraestrutura de auditoria visual e de acessibilidade instalada no projeto

## Plano por tela

### Conexao

- manter como tela de entrada e reduzir qualquer ruido visual secundario
- opcional: exibir um selo mais explicito quando o sistema estiver usando `.env`

### Organizacao

- melhorar a leitura do bloco de cursos retornados do Canvas quando a lista for muito grande
- opcional: adicionar contador de selecionados e de ja cadastrados mais evidente

### Comunicados

- reforcar visualmente o estado `rascunho/agendado/imediato`
- opcional: destacar anexo e modo teste em uma faixa curta acima do preview

### Recorrencia

- melhorar a leitura da agenda com agrupamento visual ainda mais forte por dia
- opcional: destacar no topo quando uma recorrencia tem mudancas pendentes de preview
- opcional: inserir micro-resumo no card de cada recorrencia com `turmas + proxima publicacao`

### Caixa de entrada

- reforcar visualmente quando `{{student_name}}` mudar a estrategia para envio por usuario
- opcional: destacar deduplicacao e anexo no proprio preview, nao so no resumo

### Inativos

- opcional: permitir recolher a tabela detalhada de alunos quando o usuario quiser ver so o resumo por turma
- opcional: destacar ainda mais a `turma foco` no topo do preview

### Configuracoes

- opcional: mostrar contador regressivo visual mais claro durante os `10s` de exibicao do `.env`
- opcional: separar ainda mais a zona de perigo das configuracoes comuns

### Relatorios

- opcional: melhorar a leitura de tabelas longas com primeira coluna mais destacada
- opcional: adicionar filtros rapidos prontos de periodo (`7`, `15`, `30`, `90 dias`)

## Plano por modal

### Grupo

- opcional: sticky footer em telas menores para deixar `Salvar` sempre visivel

### Revisao de envio

- opcional: destacar o bloco `impacto` no topo com mais contraste
- opcional: manter a amostra de destinatarios recolhivel quando o lote for muito grande

### Edicao de recorrencia

- opcional: dar mais separacao entre `configuracao` e `impacto da edicao`

### Revisao de recorrencia

- opcional: colocar um resumo mais compacto do diff por turma antes da agenda completa

### Cancelamento de recorrencia

- opcional: explicitar melhor quantos avisos futuros ainda serao removidos

## Proximo passo recomendado

Se a ideia agora for polimento fino de UX, a ordem que mais faz sentido e:

1. `Recorrencia`
2. `Caixa de entrada`
3. `Inativos`
4. `Relatorios`

Se a ideia for estabilidade operacional, o sistema ja esta em um ponto bem forte para considerar o ciclo `Supreme Operation` funcionalmente encerrado, ficando o restante como lapidacao de experiencia.
