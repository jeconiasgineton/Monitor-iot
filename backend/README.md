# Backend do piloto

Status: rascunho com testes passando (15 testes). Usa **dados fictícios** em tudo que depende do condomínio real.

## Como rodar os testes

```
cd backend

# Sem banco: regras, API e repositório em memória
python3 -m pytest -q

# Com PostgreSQL: também testa o repositório real.
# ATENÇÃO: apaga o schema public do banco indicado. Usar só banco de teste.
TEST_DATABASE_URL="postgresql://usuario:senha@host:5432/banco_teste" python3 -m pytest -q
```

Resultado atual: 20 testes passando (15 sem banco, 5 com PostgreSQL local 16).

## Como aplicar no Neon

```
export DATABASE_URL="postgresql://..."   # conexão do Neon (usar a URL com pooler, se disponível)
python3 -m app.banco schema              # cria as tabelas
python3 -m app.banco timescale           # ativa o TimescaleDB (requer extensão disponível no Neon)
python3 -m app.banco seed                # carrega os dados FICTÍCIOS
```

Com `DATABASE_URL` definida, a API usa o Neon. Sem ela, usa a memória com dados fictícios.

## Estrutura

- `app/schemas.py`: modelos de entrada conforme `docs/contrato-mensagens.md` (v0.2).
- `app/regras.py`: regras de bomba em seco, sobrecarga e offline. Lógica pura, sem banco.
- `app/repositorio.py`: repositório em memória, usado nos testes e sem `DATABASE_URL`.
- `app/repositorio_postgres.py`: repositório para PostgreSQL (Neon), mesma interface.
- `app/banco.py`: comandos para aplicar o esquema e carregar os dados fictícios.
- `app/main.py`: API FastAPI com `POST /v1/telemetria` e `POST /v1/status`, autenticação por token.
- `app/seed_ficticio.py`: cadastro fictício para testes e desenvolvimento.
- `sql/schema.sql`: tabelas do piloto, sem extensões. Testado no PostgreSQL 16 local.
- `sql/timescale.sql`: transforma `telemetria` em hypertable. **Não testado localmente**, pois o TimescaleDB não está instalado aqui.
- `tests/`: testes das regras, da API e do repositório PostgreSQL.

## Dados FICTÍCIOS (substituir quando houver dados reais)

| Item | Onde está | Valor fictício | Fonte do dado real |
|---|---|---|---|
| Corrente de bomba em seco | `app/regras.py`, `Limites.corrente_seca_a` | 2,0 A | Calibração no local (Fase 1 e Fase 6) |
| Corrente de sobrecarga | `app/regras.py`, `Limites.corrente_sobrecarga_a` | 16,0 A | Placa do motor e calibração |
| Leituras para confirmar bomba em seco | `app/regras.py`, `Limites.leituras_confirmacao` | 2 | Definir após os primeiros dias de operação |
| Tempo para considerar offline | `app/regras.py`, `Limites.offline_s` | 300 s | Pergunta pendente do plano |
| Condomínio, casa e bomba | `app/seed_ficticio.py` | `condominio-ficticio-alfa`, `casa-ficticia-01`, `bomba-ficticia-01` | Cadastro real (Fase 3) |
| Token de teste | `app/seed_ficticio.py` | `TOKEN-FICTICIO-NAO-USAR-EM-PRODUCAO` | Gerado no cadastro. Nunca versionar |
| Modelo, corrente nominal, fases e acionamento | `sql/schema.sql` (tabela `bomba`) | Não preenchido | Placa do motor e quadro (visita ao local) |

## O que é real (observado nas fotos do condomínio)

- Casas de máquinas com conjuntos de bombas centrífugas, em alguns casos com dois ou três motores.
- Inversores WEG CFW500 em um dos painéis fotografados. **Não está confirmado** se cada bomba tem inversor.
- Tubulação de cor vermelha, provavelmente de incêndio, que não entra no escopo do piloto.

Nada disso foi confirmado para o piloto. As fotos ajudam a planejar a instalação, mas não substituem a visita técnica.

## Pendências técnicas

1. Aplicar `sql/timescale.sql` no Neon e confirmar que a hypertable foi criada (não testado localmente).
2. Verificar com a Vercel o formato de deploy de FastAPI (função serverless) e o limite de tempo de resposta.
3. Substituir os valores fictícios pelos valores calibrados.
4. Definir o processo de geração e revogação de tokens por dispositivo.
5. Adicionar leitura de alertas e de histórico para o painel e o app (Fases 4 e 5).
