# Relatório de Alterações - Deadly Truth

Data: 2026-05-28

## Resumo

Foram feitas correções estruturais no backend FastAPI/WebSocket e ajustes no frontend React/Vite para estabilizar o ciclo da partida, normalizar jogadores, corrigir turnos, acusação, defesa, votação, bots e integração de IA via OpenRouter.

## Backend

Arquivo principal:

- `fastapi-server/main.py`

Principais alterações:

- Implementada máquina de estados com fases explícitas:
  - `lobby`
  - `intro`
  - `investigation`
  - `turn`
  - `interrogation`
  - `defense`
  - `voting`
  - `resolution`
  - `ended`
- Criados/ajustados auxiliares de estado:
  - `normalize_players`
  - `get_alive_players`
  - `get_player_by_id`
  - `set_phase`
  - `start_accusation`
  - `start_voting`
  - `resolve_voting`
  - `advance_to_next_alive_player`
  - `check_win_conditions`
  - `broadcast_game_state`
- Jogadores agora são normalizados com `id` string como identificador oficial.
- Substituído uso inseguro de `status: "online"` por `status: "alive"`.
- O assassino é escolhido exatamente uma vez ao iniciar a partida.
- O evento `you_are_killer` é privado para o jogador assassino humano.
- O assassino não é exposto publicamente no início.
- Removido bloqueio rígido de duração mínima de 30 minutos para vitória.
- Implementados logs de jogo:
  - `[GAME_PHASE]`
  - `[TURN]`
  - `[ACCUSATION]`
  - `[VOTING]`
  - `[INTERROGATION]`
  - `[WIN_CHECK]`

## Fluxo de Turnos

- `turn_start` agora envia `phase`, `player_id`, `player_name` e `time_limit`.
- O backend usa `player["id"]` como identificador oficial.
- O frontend compara `myPlayerId` com `currentTurnPlayerId` como string.
- Ações principais encerram ou avançam o turno conforme o fluxo.
- Timeout de turno envia `time_out` e avança.

## Interrogatório

- Implementado evento novo `interrogation_started`.
- Suporte mantido para evento legado `interrogatorio_iniciado`.
- Bot interrogado responde automaticamente.
- Humano interrogado pode responder via `resposta_interrogatorio`.
- Timeout gera silêncio automático.
- Resultado é enviado por `interrogation_result`.
- Interrogatório é limpo após resposta/timeout.
- O turno avança após conclusão para manter ritmo.

## Acusação, Defesa e Votação

- Acusação agora cria `active_accusation`.
- Nova fase `defense` antes da votação.
- Evento novo `accusation_started`.
- Acusado humano pode enviar `defesa_acusacao`.
- Acusado bot gera defesa automática.
- Timeout de defesa usa: `O acusado permaneceu em silêncio.`
- Após defesa, inicia `voting_started`.
- Votos aceitos:
  - `culpado`
  - `inocente`
  - `abstencao`
- Bots votam automaticamente.
- Timeout de votação registra abstenção para quem não votou.
- Resultado é enviado por `voting_result`.
- Compatibilidade mantida com:
  - `votacao_iniciada`
  - `resultado_votacao`

## Condições de Vitória

- Inocentes vencem se o assassino for condenado.
- Assassino vence se assassinos vivos forem maior ou igual aos inocentes vivos.
- Assassino vence se todos os inocentes forem eliminados.
- `game_end` revela vencedor, motivo, `killer_id` e `killer_name`.

## OpenRouter e IA dos Bots

Arquivos:

- `fastapi-server/openrouter_client.py`
- `fastapi-server/main.py`
- `fastapi-server/env.example`
- `fastapi-server/README_OPENROUTER.md`

Alterações:

- Criado cliente async `call_openrouter`.
- Modelo principal:
  - `qwen/qwen3-next-80b-a3b-instruct:free`
- Modelo fallback:
  - `z-ai/glm-4.5-air:free`
- Timeout configurável via `AI_TIMEOUT_SECONDS`.
- Logs adicionados:
  - `[OPENROUTER] Tentando modelo principal`
  - `[OPENROUTER] Sucesso com modelo principal`
  - `[OPENROUTER] Falha no modelo principal, tentando fallback`
  - `[OPENROUTER] Sucesso com fallback`
  - `[OPENROUTER] Ambos os modelos falharam, usando fallback local`
  - `[BOT_REPLY]`
- Criadas funções:
  - `generate_bot_reply`
  - `generate_bot_defense`
  - `generate_bot_vote`
  - `generate_case_with_ai`
- Criadas personas fixas para bots principais:
  - `Shadow_Hunter`
  - `Night_Stalker`
  - `Dark_Phoenix`
- Criada memória curta por bot:
  - `last_replies`
  - `suspicions`
  - `known_clues`
  - `contradictions`
- Criado fallback local variado com categorias:
  - `defensive`
  - `suspicious`
  - `afraid`
  - `analytical`
  - `evasive`

## Remoção do Groq

Após decisão de manter somente OpenRouter:

- Removido import `from groq import Groq`.
- Removidos clientes Groq.
- Removidas leituras de `GROQ_API_KEY`.
- Removidas referências a Groq em logs e documentação.
- Removido pacote `groq` de `fastapi-server/requirements.txt`.
- Removido `README_DEEPSEEK.md` por conter documentação legada com Groq/DeepSeek.
- O backend não depende mais de `GROQ_API_KEY`.

Variáveis esperadas agora:

```env
OPENROUTER_API_KEY=sua_chave_aqui
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_SITE_URL=http://localhost:5173
OPENROUTER_APP_NAME=Deadly Truth
OPENROUTER_PRIMARY_MODEL=qwen/qwen3-next-80b-a3b-instruct:free
OPENROUTER_FALLBACK_MODEL=z-ai/glm-4.5-air:free
AI_TIMEOUT_SECONDS=10
```

## Correção do `random`

Problema corrigido:

```text
UnboundLocalError: cannot access local variable 'random' where it is not associated with a value
```

Causa:

- Existia `import random` local dentro de `game_loop`.
- Isso fazia Python tratar `random` como variável local na função inteira.
- `killer = random.choice(participantes)` quebrava antes do import local.

Correção:

- Mantido apenas `import random` global no topo de `main.py`.
- Removidos imports locais de `random`.
- Adicionados logs:

```python
logger.info(f"🎲 Escolhendo assassino entre {len(participantes)} participantes")
logger.info(f"🔪 Assassino escolhido internamente: {killer.get('name')} ID={killer.get('id')}")
```

## Frontend

Arquivos:

- `deadly-truth-frontend/src/pages/Game.jsx`
- `deadly-truth-frontend/src/pages/Lobby.jsx`

Alterações em `Game.jsx`:

- Adicionados handlers para:
  - `turn_start`
  - `interrogation_started`
  - `interrogation_result`
  - `interrogation_timeout`
  - `accusation_started`
  - `voting_started`
  - `vote_registered`
  - `voting_result`
  - `player_death`
  - `game_end`
- Mantida compatibilidade com eventos legados.
- Fase atual exibida no topo.
- Ações bloqueadas fora da fase correta.
- Painel de defesa para acusado.
- Modal de votação.
- Resultado de votação no chat.
- Tela final com vencedor, motivo e assassino revelado.
- Exibição discreta da origem da IA:
  - `openrouter`
  - `fallback_model`
  - `local_fallback`

Alterações em `Lobby.jsx`:

- Bots entram instantaneamente.
- IA não é chamada na entrada dos bots.
- Bots são enviados com estrutura compatível:

```js
{
  id: String(index),
  name: botName,
  numeric_id: index,
  status: "alive",
  isBot: true,
  is_bot: true
}
```

- Removida frase repetitiva:

```text
Interessante... vamos ver o que aconteceu.
```

## Validações Executadas

Backend:

```powershell
python -m py_compile fastapi-server\main.py fastapi-server\openrouter_client.py
```

Frontend:

```powershell
cd deadly-truth-frontend
npm run build
```

Busca de referências removidas:

```powershell
rg -n "groq|GROQ|Groq|llama-3.3|AI_PROVIDER|deepseek|DeepSeek|DEEPSEEK" fastapi-server deadly-truth-frontend -S
```

Resultado:

- Nenhuma referência restante a Groq, DeepSeek ou `AI_PROVIDER`.
- Compilação Python passou.
- Build Vite passou.

## Como Testar Localmente

Backend:

```powershell
cd C:\Users\DrEdesio\Documents\PROJETOS\Deadly-Truth\fastapi-server
uvicorn main:app --reload
```

Frontend:

```powershell
cd C:\Users\DrEdesio\Documents\PROJETOS\Deadly-Truth\deadly-truth-frontend
npm run dev
```

Fluxo recomendado:

1. Entrar com 1 humano.
2. Adicionar bots até pelo menos 3 jogadores.
3. Iniciar partida.
4. Confirmar que o caso é gerado via OpenRouter.
5. Confirmar que a partida avança para `turn`.
6. Interrogar `Shadow_Hunter`.
7. Interrogar `Night_Stalker`.
8. Acusar `Dark_Phoenix`.
9. Confirmar defesa automática.
10. Votar.
11. Confirmar votos dos bots.
12. Confirmar resultado e possível fim de jogo.

