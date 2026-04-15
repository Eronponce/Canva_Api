# Operacao Docker

Esta stack Docker foi configurada para **encerrar o container automaticamente depois de 3 horas sem uso**.

## Regra atual

- o service `panel` grava a ultima atividade real do operador
- o healthcheck de Docker em `/healthz` **nao** conta como uso
- depois de `10800` segundos sem atividade, o entrypoint encerra o processo do painel
- a policy de restart ficou em `on-failure`, entao uma parada limpa por ociosidade **nao sobe de novo sozinha**

## Variaveis de idle shutdown

Estas variaveis ficam no `docker-compose.yml` e devem ser reaproveitadas em qualquer service HTTP novo da stack:

- `PANEL_IDLE_SHUTDOWN_ENABLED=true`
- `PANEL_IDLE_TIMEOUT_SECONDS=10800`
- `PANEL_IDLE_CHECK_INTERVAL_SECONDS=60`
- `PANEL_IDLE_ACTIVITY_FILE=/tmp/canvas-bulk-panel.last-activity`

## Operacao recomendada

- para subir: `docker compose up -d --build`
- para verificar: `docker compose ps`
- para logs: `docker compose logs -f panel`
- se for ficar sem usar por horas, **pode deixar o idle shutdown agir**
- se quiser desligar na hora: `docker compose stop`
- para religar depois: `docker compose up -d`

## Regra para o proximo operador

Se nao houver uso por 3 horas, o esperado e o container parar sozinho.
Nao troque essa politica para `unless-stopped` sem revisar o watchdog, porque isso faria o container voltar logo depois da parada por ociosidade.

