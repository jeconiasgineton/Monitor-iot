-- Ativa o TimescaleDB na tabela de telemetria. Aplicar depois de schema.sql.
-- Requer a extensão timescaledb disponível no banco (no Neon, use as funcionalidades Apache-2).

CREATE EXTENSION IF NOT EXISTS timescaledb;

SELECT create_hypertable('telemetria', 'recebido_em', if_not_exists => TRUE);
