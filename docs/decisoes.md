# Decisões tomadas (piloto)

Registro das respostas dadas às perguntas do plano, uma por vez.

| # | Pergunta | Resposta |
|---|---|---|
| 1 | Quantas bombas no piloto? | 1 bomba |
| 2 | Inversor ou partida direta? | Não sei (verificar no quadro) |
| 3 | Modelo e corrente nominal? | Não sei (verificar placa do motor) |
| 4 | Monofásica ou trifásica? | Não sei (verificar no local) |
| 5 | Wi-Fi testado na casa de máquinas? | Não testado |
| 6 | 4G entra no piloto? | Wi-Fi e 4G no piloto |
| 7 | Canal de alerta? | App no celular (fora das opções oferecidas) |
| 7a | Tipo de app? | App nativo (Android e iOS, publicação nas lojas, push) |
| 8 | Quem desenvolve? | Eu sozinho |
| 9 | Quem acessa painel e app? | Zelador, administradora e síndico |
| 10 | Quem atende alertas e prazo? | Definir durante o piloto |
| 11 | Autorização do condomínio? | Ainda não |
| 12 | Como definir limiares? | Calibração no local |

## Pendências

- Pergunta 8 (linguagem, framework e hospedagem): ainda não feita.
- Dados da bomba (perguntas 2, 3 e 4): precisam de visita ao local.
- Teste de Wi-Fi (pergunta 5): precisa de visita ao local.
- Autorização do condomínio (pergunta 11).

## Impactos nas fases

- 4G no piloto: acrescenta módulo celular e chip de dados ao hardware, e lógica de troca de conexão no firmware.
- App nativo: a Fase 4 passa a incluir Android e iOS, publicação nas lojas e notificações push. Aumenta o esforço em relação ao plano aprovado.
- Desenvolvimento individual: o cronograma das fases de app e firmware precisa considerar a capacidade de uma pessoa.

## Pergunta 8 (respondida)

| Tema | Resposta |
|---|---|
| Stack | Opção 1: Flutter (app, Dart) + Python com FastAPI (backend) |
| Código e CI | GitHub |
| Hospedagem | Vercel (a confirmar, ver pendência abaixo) |

### Pendência de hospedagem
- Vercel executa funções sob demanda, com tempo limite. Não mantém conexão MQTT permanente.
- O assinante MQTT (ingestão) precisa de um processo sempre ativo, que não roda na Vercel.
- Banco PostgreSQL com TimescaleDB também não roda na Vercel. Precisa de serviço gerenciado ou servidor próprio.
- O broker Mosquitto também precisa de servidor próprio ou serviço gerenciado.

### Decisão de transporte (após a pergunta sobre ingestão)

| Tema | Resposta |
|---|---|
| Hospedagem | Vercel (API e painel) + Neon (banco) |
| Ingestão | HTTPS direto do ESP32 para a API, sem broker MQTT |

Consequências:
- Contrato atualizado para a versão 0.2 (`docs/contrato-mensagens.md`).
- Firmware trocado de MQTT para HTTPS POST (`firmware/src/main.cpp`), com a mesma lógica de buffer.
- Não é mais preciso manter broker nem processo de ingestão rodando em servidor próprio.
- Sem canal de comando de volta ao dispositivo. Isso não afeta o MVP, que só alerta.
- Neon suporta o TimescaleDB com as funcionalidades Apache-2 (sem compressão), segundo a documentação do Neon consultada em 2026-11-24.
