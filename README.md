# Monitor-iot

Monitoramento de bombas de recalque de condomínios (piloto).

- `backend/`: API FastAPI, regras de alerta e esquema do banco (Neon). Ver `backend/README.md`.
- `firmware/`: firmware do ESP32 com pinça SCT-013 e ADS1115 (PlatformIO). Não compilado ainda.
- `docs/`: contrato de mensagens, decisões e status.

Dados fictícios estão marcados no código e no `backend/README.md`.
