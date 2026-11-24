# Contrato de mensagens (piloto)

Versão: 0.2
Status: rascunho, aguardando aprovação
Alteração em relação à 0.1: transporte MQTT substituído por HTTPS (decisão registrada em `docs/decisoes.md`).

## Transporte

- Protocolo: HTTPS (porta 443), método POST, corpo em JSON.
- Autenticação: token único por dispositivo, enviado no cabeçalho `Authorization: Bearer <token>`.
- Conexão de saída apenas. Nenhuma porta aberta no prédio.
- Os dados são enviados em intervalos regulares, sem canal de comando de volta ao dispositivo.

## Endpoints

| Método | Caminho | Conteúdo | Uso |
|---|---|---|---|
| POST | `/v1/telemetria` | Telemetria agregada | A cada intervalo de agregação |
| POST | `/v1/status` | Heartbeat | A cada 60 segundos |

O host é o domínio da API na Vercel (pendente de definição).

## Identificação do dispositivo

- O token identifica o dispositivo no servidor. Ele mapeia para `condominio`, `casa` e `bomba` no cadastro.
- Por isso o corpo da mensagem não repete os identificadores.
- O token é único por dispositivo e pode ser revogado pelo servidor.

## Respostas esperadas

| Código HTTP | Significado | Comportamento do dispositivo |
|---|---|---|
| 2xx | Aceita | Remove a mensagem do buffer |
| 400, 401, 403, 404, 422 | Recusada | Descarta a mensagem, sem nova tentativa |
| 429 | Limite de requisições | Mantém a mensagem e tenta depois |
| 5xx ou erro de conexão | Falha temporária | Mantém a mensagem e tenta depois |

## Telemetria

Endpoint: `POST /v1/telemetria`

```json
{
  "v": 1,
  "ts": 1732440000,
  "seq": 1234,
  "corrente_rms_a": 12.4,
  "corrente_max_a": 13.1,
  "corrente_min_a": 11.8,
  "amostras": 60,
  "rssi_dbm": -63,
  "fw": "0.1.0"
}
```

| Campo | Tipo | Descrição |
|---|---|---|
| `v` | inteiro | Versão do contrato |
| `ts` | inteiro | Epoch em segundos (UTC). Ausente se o relógio não sincronizou |
| `seq` | inteiro | Número sequencial, cresce a cada mensagem gerada. Usado para deduplicação e para detectar perda |
| `corrente_rms_a` | número | Média das correntes RMS das janelas do intervalo, em ampères |
| `corrente_max_a` | número | Maior RMS de janela no intervalo |
| `corrente_min_a` | número | Menor RMS de janela no intervalo |
| `amostras` | inteiro | Quantidade de janelas agregadas |
| `rssi_dbm` | inteiro | Intensidade do sinal Wi-Fi no momento da geração |
| `fw` | texto | Versão do firmware |

## Status (heartbeat)

Endpoint: `POST /v1/status`, a cada 60 segundos.

```json
{
  "v": 1,
  "ts": 1732440000,
  "uptime_s": 86400,
  "rssi_dbm": -63,
  "pendentes": 0,
  "fw": "0.1.0"
}
```

| Campo | Tipo | Descrição |
|---|---|---|
| `pendentes` | inteiro | Mensagens de telemetria guardadas no dispositivo aguardando envio |

O heartbeat não é guardado no dispositivo. Se não houver conexão, ele simplesmente não é enviado.

## Regras de consumo no servidor (Fase 3)

- Ausência de heartbeat por mais de um intervalo definido indica dispositivo offline. Esse intervalo é pendente de definição.
- Telemetria com `ts` ausente é aceita, mas marcada como sem horário confiável.
- A deduplicação usa `seq` por dispositivo. Como o envio pode repetir após falha, a mesma `seq` pode chegar mais de uma vez.
- O servidor deve responder rapidamente (idealmente em menos de 10 segundos), porque o dispositivo espera a resposta antes de seguir.

## Pendências de definição

- Domínio da API e token por dispositivo (Fase 3).
- Intervalo de agregação da telemetria (proposta de 60 segundos no firmware, a confirmar).
- Limiares de corrente para bomba em seco e sobrecarga (dependem da corrente nominal das bombas).
- Intervalo para considerar um dispositivo offline.
