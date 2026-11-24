// Firmware do piloto: lê corrente com SCT-013 via ADS1115, agrega em RMS e envia por HTTPS.
// ATENÇÃO: código escrito sem compilação nem teste em hardware.

#include <Arduino.h>
#include <Wire.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Adafruit_ADS1X15.h>
#include <time.h>
#include "config.h"

Adafruit_ADS1115 ads;

// ---------- Endpoints ----------
String urlTelemetria;
String urlStatus;

// ---------- Estado ----------
uint32_t seqTelemetria = 0;
uint32_t inicioAgregacao = 0;
uint32_t ultimoStatus = 0;

// Agregação
float somaRms = 0, maxRms = 0, minRms = 1e9;
uint16_t janelasAgregadas = 0;

// Buffer em RAM para telemetria não enviada (fila circular).
// Só telemetria entra no buffer. O heartbeat não é guardado.
struct Mensagem {
  String payload;
};
Mensagem buffer[BUFFER_CAPACIDADE];
uint16_t bufferInicio = 0;
uint16_t bufferQtd = 0;

// Quantas mensagens do buffer tentar enviar por ciclo do loop.
#define ENVIOS_POR_CICLO 5

// ---------- Buffer ----------
void enfileirar(const String& payload) {
  uint16_t pos = (bufferInicio + bufferQtd) % BUFFER_CAPACIDADE;
  if (bufferQtd == BUFFER_CAPACIDADE) {
    // Buffer cheio: descarta a mensagem mais antiga
    bufferInicio = (bufferInicio + 1) % BUFFER_CAPACIDADE;
    pos = (bufferInicio + bufferQtd - 1) % BUFFER_CAPACIDADE;
  } else {
    bufferQtd++;
  }
  buffer[pos].payload = payload;
}

// Envia um JSON por HTTPS POST. Retorna o código HTTP, ou -1 em erro de conexão.
int enviarJson(const String& url, const String& payload) {
  if (WiFi.status() != WL_CONNECTED) return -1;

  WiFiClientSecure cliente;
  cliente.setCACert(API_CA_CERT);

  HTTPClient http;
  http.setTimeout(10000);
  if (!http.begin(cliente, url)) return -1;
  http.addHeader("Content-Type", "application/json");
  http.addHeader("Authorization", String("Bearer ") + API_TOKEN);

  int codigo = http.POST(payload);
  http.end();
  return codigo;
}

// Envia mensagens do buffer em ordem.
// 2xx: removida. 4xx (exceto 429): descartada, pois o servidor recusou o conteúdo.
// Erro de conexão, 429 ou 5xx: mantida para nova tentativa.
void descarregarBuffer() {
  uint8_t enviadas = 0;
  while (bufferQtd > 0 && enviadas < ENVIOS_POR_CICLO) {
    int codigo = enviarJson(urlTelemetria, buffer[bufferInicio].payload);
    enviadas++;

    bool recusadaDefinitivamente = (codigo >= 400 && codigo < 500 && codigo != 429);
    if (codigo >= 200 && codigo < 300) {
      // enviada com sucesso
    } else if (recusadaDefinitivamente) {
      Serial.printf("Mensagem recusada pelo servidor (HTTP %d), descartada.\n", codigo);
    } else {
      break; // mantém na fila e tenta no próximo ciclo
    }
    bufferInicio = (bufferInicio + 1) % BUFFER_CAPACIDADE;
    bufferQtd--;
  }
}

// ---------- Rede ----------
void conectarWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_SENHA);
  uint32_t t0 = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t0 < 15000) {
    delay(250);
  }
}

void sincronizarHorario() {
  configTime(FUSO_SEGUNDOS, 0, NTP_SERVIDOR);
}

bool horarioValido() {
  time_t agora = time(nullptr);
  return agora > 1700000000; // após 14/11/2023
}

// ---------- Medição ----------
// Converte leitura do ADS1115 para tensão em volts.
float lerTensao() {
  int16_t bruto = ads.readADC_SingleEnded(ADS_CANAL);
  return ads.computeVolts(bruto);
}

// Amostras de uma janela: 860 SPS * 1 s = 860; buffer com folga.
#define MAX_AMOSTRAS_JANELA 1024
static float amostrasJanela[MAX_AMOSTRAS_JANELA];

// Mede o RMS de uma janela de JANELA_MS, removendo o nível DC (média da janela).
float medirRmsJanela() {
  const uint32_t t0 = millis();
  uint16_t n = 0;
  double soma = 0;
  while (millis() - t0 < JANELA_MS && n < MAX_AMOSTRAS_JANELA) {
    float v = lerTensao();
    amostrasJanela[n++] = v;
    soma += v;
  }
  if (n == 0) return 0;

  double mediaTensao = soma / n;
  double somaQuad = 0;
  for (uint16_t i = 0; i < n; i++) {
    double v = amostrasJanela[i] - mediaTensao;
    somaQuad += v * v;
  }
  double rmsTensao = sqrt(somaQuad / n);
  return (float)(rmsTensao * FATOR_CALIBRACAO);
}

// ---------- Publicação ----------
void montarTelemetria() {
  float media = janelasAgregadas ? somaRms / janelasAgregadas : 0;

  JsonDocument doc;
  doc["v"] = CONTRATO_V;
  if (horarioValido()) doc["ts"] = (uint32_t)time(nullptr);
  doc["seq"] = ++seqTelemetria;
  doc["corrente_rms_a"] = serialized(String(media, 2));
  doc["corrente_max_a"] = serialized(String(maxRms, 2));
  doc["corrente_min_a"] = serialized(String(minRms, 2));
  doc["amostras"] = janelasAgregadas;
  doc["rssi_dbm"] = WiFi.RSSI();
  doc["fw"] = FW_VERSAO;

  String payload;
  serializeJson(doc, payload);
  enfileirar(payload);

  somaRms = 0; maxRms = 0; minRms = 1e9; janelasAgregadas = 0;
}

void enviarStatus() {
  JsonDocument doc;
  doc["v"] = CONTRATO_V;
  if (horarioValido()) doc["ts"] = (uint32_t)time(nullptr);
  doc["uptime_s"] = millis() / 1000;
  doc["rssi_dbm"] = WiFi.RSSI();
  doc["pendentes"] = bufferQtd;
  doc["fw"] = FW_VERSAO;

  String payload;
  serializeJson(doc, payload);
  // Heartbeat não é guardado: se não houver conexão, não há o que reportar.
  enviarJson(urlStatus, payload);
}

// ---------- Ciclo principal ----------
void setup() {
  Serial.begin(115200);
  Wire.begin();

  if (!ads.begin(ADS_ENDERECO)) {
    Serial.println("ADS1115 não encontrado. Verificar I2C.");
  }
  ads.setGain(GAIN_TWO); // ±2,048 V
  ads.setDataRate(RATE_ADS1115_860SPS);

  String base = String("https://") + API_HOST + "/v1";
  urlTelemetria = base + "/telemetria";
  urlStatus     = base + "/status";

  conectarWiFi();
  sincronizarHorario();

  inicioAgregacao = millis();
  ultimoStatus = millis();
}

void loop() {
  conectarWiFi();
  descarregarBuffer();

  // Medição: uma janela por vez
  float rms = medirRmsJanela();
  somaRms += rms;
  if (rms > maxRms) maxRms = rms;
  if (rms < minRms) minRms = rms;
  janelasAgregadas++;

  if (millis() - inicioAgregacao >= INTERVALO_AGREGACAO_MS) {
    montarTelemetria();
    inicioAgregacao = millis();
  }

  if (millis() - ultimoStatus >= INTERVALO_STATUS_MS) {
    enviarStatus();
    ultimoStatus = millis();
  }
}
