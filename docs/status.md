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
- Não compilado após a troca de MQTT para HTTPS. Confirmar a compilação com as bibliotecas do PlatformIO.

## Fase 3: Backend e nuvem
- Rascunho em `backend/`, com 15 testes passando. Usa dados fictícios, marcados em `backend/README.md`.
- Feito: API `/v1/telemetria` e `/v1/status` com autenticação por token, deduplicação por `seq`, regras de bomba em seco, sobrecarga e offline, alertas com deduplicação, esquema SQL para Neon.
- Repositório para PostgreSQL/Neon escrito (`backend/app/repositorio_postgres.py`) e testado contra PostgreSQL 16 local. Os 20 testes passam.
- Esquema `backend/sql/schema.sql` aplicado e testado localmente. `backend/sql/timescale.sql` ainda não testado, pois o TimescaleDB não está instalado no ambiente de teste.
- Neon (projeto Monitor-iot, id `floral-waterfall-24496607`, região `aws-sa-east-1`, PostgreSQL 18): esquema aplicado, TimescaleDB ativo com `telemetria` como hypertable, dados fictícios carregados. Hash do token verificado contra o backend.
- Deploy de produção na Vercel: `https://monitor-iot-wh18.vercel.app` (projeto `monitor-iot-wh18`, time FielSoft Team). Rotas `/docs`, `/v1/status` e `/v1/telemetria` respondem.
- Teste de `POST /v1/status` com token fictício e corpo válido: resposta `{"status": "aceita"}`. Antes, o campo `v` foi enviado como texto e a API retornou 422, o que confirmou a validação do schema.
- Projeto `monitor-iot-n5qm` também existe na Vercel, com a mesma API. Não é o oficial e pode ser removido.
- Pendente: confirmar `DATABASE_URL` nas variáveis de ambiente do projeto `monitor-iot-wh18`, conectar a integração GitHub, e implementar a leitura de alertas para o painel e o app.
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
