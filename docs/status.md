# Status do desenvolvimento do piloto

Atualizado: 2026-11-24

## Fase 0: Definições e levantamento
- Pendente. Depende das respostas às 12 perguntas do plano.

## Fase 1: Hardware em bancada
- Pendente. Não iniciada. Falta definir a faixa da pinça (corrente nominal das bombas).
- Calibração: `FATOR_CALIBRACAO` está em 1.0 e não deve ser usado no piloto.

## Fase 2: Firmware
- Rascunho escrito em `firmware/src/main.cpp` e `firmware/include/config.h`.
- Não compilado. Não testado em hardware.
- Implementado no rascunho: leitura do ADS1115, cálculo de RMS por janela com remoção de offset DC, agregação (média, máximo, mínimo), envio em JSON, reconexão Wi-Fi e MQTT, heartbeat com RSSI, buffer circular em RAM.
- Limitação conhecida: o buffer fica em RAM. Mensagens não enviadas se perdem em reinício. A versão com armazenamento em flash (LittleFS) fica para depois dos testes.
- Transporte: HTTPS POST para a API (sem MQTT), com token por dispositivo. Trocado após a decisão de hospedagem.
- Pendências no `config.h`: identificadores, Wi-Fi, host e token da API, certificado CA, fator de calibração.
- Compilação verificada após a troca de MQTT para HTTPS: `pio run -e esp32dev` passa no GitHub Actions (workflow `.github/workflows/firmware.yml`, roda a cada push em `firmware/`). Não foi possível compilar no ambiente de desenvolvimento, porque o proxy bloqueia a plataforma `espressif32`. Binário disponível como artefato do workflow.

## Fase 3: Backend e nuvem
- Rascunho em `backend/`, com 15 testes passando. Usa dados fictícios, marcados em `backend/README.md`.
- Feito: API `/v1/telemetria` e `/v1/status` com autenticação por token, deduplicação por `seq`, regras de bomba em seco, sobrecarga e offline, alertas com deduplicação, esquema SQL para Neon.
- Repositório para PostgreSQL/Neon escrito (`backend/app/repositorio_postgres.py`) e testado contra PostgreSQL 16 local. Os 20 testes passam.
- Esquema `backend/sql/schema.sql` aplicado e testado localmente. `backend/sql/timescale.sql` ainda não testado, pois o TimescaleDB não está instalado no ambiente de teste.
- Neon (projeto Monitor-iot, id `floral-waterfall-24496607`, região `aws-sa-east-1`, PostgreSQL 18): esquema aplicado, TimescaleDB ativo com `telemetria` como hypertable, dados fictícios carregados. Hash do token verificado contra o backend.
- Deploy de produção oficial na Vercel: `https://monitor-iot-seven.vercel.app` (projeto `monitor-iot`, time FielSoft Team). Rotas `/docs`, `/v1/status` e `/v1/telemetria` respondem.
- Gravação no Neon confirmada: após configurar `DATABASE_URL` nas variáveis de ambiente do projeto e fazer redeploy, o `POST /v1/status` de teste foi gravado em `dispositivo.ultimo_status`. O `ts` de teste (1790000000) aparece como 2026-09-21 14:13:20+00; é um valor fictício.
- Teste de `POST /v1/status` com token fictício e corpo válido: resposta `{"status": "aceita"}`. Antes, o campo `v` foi enviado como texto e a API retornou 422, o que confirmou a validação do schema.
- Projetos de teste `monitor-iot-n5qm` e `monitor-iot-wh18` foram removidos.
- Integração GitHub conectada ao projeto `monitor-iot`, com Root Directory `backend` e framework FastAPI. Deploy com essa configuração gravou status no Neon.
- Leitura para painel e app implementada: `GET /v1/dispositivos/{id}/alertas` (padrão: só abertos; `?somente_abertos=false` traz todos) e `GET /v1/dispositivos/{id}/telemetria?limite=N`. Exigem o token de leitura da variável `API_LEITURA_TOKEN`; sem ela, respondem 503.
- Testes: 24 passando, incluindo PostgreSQL. As consultas de leitura no Postgres foram validadas em banco de teste.
- Pendente: definir como painel e app se autenticam em produção (token de leitura único ou login por usuário), e configurar `API_LEITURA_TOKEN` na Vercel.
- Stack definida: Python com FastAPI na Vercel, banco PostgreSQL com TimescaleDB no Neon, código e CI no GitHub.
- Ingestão por HTTPS direto do ESP32 (sem broker MQTT). Ver `docs/decisoes.md`.
- Contrato de mensagens em `docs/contrato-mensagens.md` (versão 0.2).

## Fases 4 a 7
- Não iniciadas.

## Itens que travam o avanço
1. Corrente nominal e modelo das bombas (Fase 1 e limiares).
2. Credenciais do Wi-Fi autorizado e identificadores do piloto (Fase 2).
3. Provedor de hospedagem definido (Vercel). Pendente: confirmar a integração GitHub e a `DATABASE_URL` no projeto oficial (Fase 3).
4. Dados da bomba: inversor, modelo, corrente nominal e fases (Fase 1 e limiares). Exigem visita ao local.
5. Teste de Wi-Fi na casa de máquinas (Fase 2). Exige visita ao local.
6. Autorização do condomínio piloto (Fase 6).
7. Intervalo de agregação, confirmado ou ajustado (Fase 2).
8. Linguagem, framework e hospedagem do app e da nuvem (Fases 3 e 4). Pergunta 8 ainda não foi feita.

## Decisões registradas (ver `docs/decisoes.md`)
- Piloto com 1 bomba, Wi-Fi e 4G.
- Canal de alerta: app nativo (Android e iOS).
- Desenvolvimento individual.
- Acesso para zelador, administradora e síndico.
- Limiares definidos por calibração no local.
