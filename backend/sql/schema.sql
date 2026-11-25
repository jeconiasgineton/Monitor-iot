-- Esquema do piloto para PostgreSQL (Neon).
-- Aplicar antes de timescale.sql. Não depende de extensões.
-- Valores de exemplo marcados como FICTÍCIO devem ser substituídos.

CREATE TABLE IF NOT EXISTS condominio (
    id          TEXT PRIMARY KEY,
    nome        TEXT NOT NULL,        -- FICTÍCIO no seed
    criado_em   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS casa_maquinas (
    id              TEXT PRIMARY KEY,
    condominio_id   TEXT NOT NULL REFERENCES condominio(id),
    descricao       TEXT
);

CREATE TABLE IF NOT EXISTS bomba (
    id                  TEXT PRIMARY KEY,
    casa_id             TEXT NOT NULL REFERENCES casa_maquinas(id),
    -- Preenchidos na Fase 1 e Fase 6 a partir da placa do motor. Vazios até lá.
    modelo              TEXT,
    corrente_nominal_a  NUMERIC(6,2),
    fases               SMALLINT CHECK (fases IN (1, 3)),
    acionamento         TEXT CHECK (acionamento IN ('inversor', 'partida_direta'))
);

CREATE TABLE IF NOT EXISTS dispositivo (
    id              TEXT PRIMARY KEY,
    bomba_id        TEXT NOT NULL REFERENCES bomba(id),
    token_hash      TEXT NOT NULL UNIQUE,     -- SHA-256 do token; o token em si não é armazenado
    ativo           BOOLEAN NOT NULL DEFAULT TRUE,
    ultimo_seq      BIGINT NOT NULL DEFAULT -1,
    ultimo_status   TIMESTAMPTZ
);

-- Telemetria: série temporal. Vira hypertable em timescale.sql quando o TimescaleDB estiver disponível.
CREATE TABLE IF NOT EXISTS telemetria (
    dispositivo_id      TEXT NOT NULL REFERENCES dispositivo(id),
    recebido_em         TIMESTAMPTZ NOT NULL DEFAULT now(),
    medido_em           TIMESTAMPTZ,              -- ts do dispositivo; NULL se sem horário
    seq                 BIGINT NOT NULL,
    corrente_rms_a      NUMERIC(7,3) NOT NULL,
    corrente_max_a      NUMERIC(7,3) NOT NULL,
    corrente_min_a      NUMERIC(7,3) NOT NULL,
    amostras            INTEGER NOT NULL,
    rssi_dbm            SMALLINT,
    fw                  TEXT NOT NULL,
    PRIMARY KEY (dispositivo_id, seq, recebido_em)
);

CREATE INDEX IF NOT EXISTS telemetria_dispositivo_tempo
    ON telemetria (dispositivo_id, recebido_em DESC);

CREATE TABLE IF NOT EXISTS alerta (
    id              BIGSERIAL PRIMARY KEY,
    dispositivo_id  TEXT NOT NULL REFERENCES dispositivo(id),
    tipo            TEXT NOT NULL,
    severidade      TEXT NOT NULL CHECK (severidade IN ('critica', 'atencao', 'informativa')),
    mensagem        TEXT NOT NULL,
    aberto_em       TIMESTAMPTZ NOT NULL DEFAULT now(),
    fechado_em      TIMESTAMPTZ
);

-- Um alerta aberto por tipo e dispositivo (deduplicação no banco)
CREATE UNIQUE INDEX IF NOT EXISTS alerta_aberto_unico
    ON alerta (dispositivo_id, tipo) WHERE fechado_em IS NULL;

-- Usuários do painel e do app (login por e-mail e senha).
CREATE TABLE IF NOT EXISTS usuario (
    id          BIGSERIAL PRIMARY KEY,
    email       TEXT NOT NULL UNIQUE,            -- sempre em minúsculas
    senha_hash  TEXT NOT NULL,                   -- scrypt; a senha em si não é armazenada
    perfil      TEXT NOT NULL CHECK (perfil IN ('administrador', 'zelador')),
    ativo       BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Quais condomínios um zelador pode ver. Administrador vê todos.
CREATE TABLE IF NOT EXISTS usuario_condominio (
    usuario_id      BIGINT NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
    condominio_id   TEXT NOT NULL REFERENCES condominio(id),
    PRIMARY KEY (usuario_id, condominio_id)
);

-- Sessões de login. Guarda só o hash do token.
CREATE TABLE IF NOT EXISTS sessao (
    token_hash  TEXT PRIMARY KEY,
    usuario_id  BIGINT NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
    expira_em   TIMESTAMPTZ NOT NULL
);
