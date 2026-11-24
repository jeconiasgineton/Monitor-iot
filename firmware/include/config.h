#pragma once

// ============================================================
// CONFIGURAÇÃO DO DISPOSITIVO
// Itens marcados com PENDENTE precisam de definição antes do piloto.
// ============================================================

// ---------- Identificação (PENDENTE: cadastro da Fase 3) ----------
#define CONDOMINIO_ID   "PENDENTE"
#define CASA_ID         "PENDENTE"
#define BOMBA_ID        "PENDENTE"

#define FW_VERSAO       "0.1.0"
#define CONTRATO_V      1

// ---------- Wi-Fi (PENDENTE: credenciais do prédio autorizado) ----------
#define WIFI_SSID       "PENDENTE"
#define WIFI_SENHA      "PENDENTE"

// ---------- API HTTPS (PENDENTE: domínio da API na Vercel, Fase 3) ----------
// Somente o host, sem https:// e sem barra final. Ex.: "api.exemplo.com"
#define API_HOST        "PENDENTE"

// Token único do dispositivo (PENDENTE: gerado pelo cadastro da Fase 3)
#define API_TOKEN       "PENDENTE"

// Certificado CA do host da API em formato PEM.
// PENDENTE: recomendado usar o certificado raiz da cadeia do host, não o certificado de folha.
#define API_CA_CERT    ""

// ---------- Horário ----------
#define NTP_SERVIDOR    "pool.ntp.org"
#define FUSO_SEGUNDOS   (-3 * 3600)   // America/Recife (UTC-3, sem horário de verão)

// ---------- Medição ----------
// Fator de calibração: corrente real (A) / corrente lida (A).
// PENDENTE: definido na Fase 1 com alicate amperímetro. Padrão 1.0 não é válido para piloto.
#define FATOR_CALIBRACAO   1.0f

// Duração de cada janela de medição (ms). Cada janela gera um valor RMS.
#define JANELA_MS          1000

// Intervalo de agregação das janelas antes do envio (ms).
// Proposta de 60 s, a confirmar.
#define INTERVALO_AGREGACAO_MS  60000

// Intervalo do heartbeat (ms).
#define INTERVALO_STATUS_MS     60000

// Capacidade do buffer em RAM para mensagens não enviadas.
// Mensagens são perdidas se o dispositivo reiniciar (ver docs/status.md).
#define BUFFER_CAPACIDADE       120

// ---------- Hardware ----------
#define ADS_ENDERECO            0x48   // ADDR ligado ao GND
#define ADS_CANAL               0      // A0
