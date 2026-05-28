# OpenRouter no Deadly Truth

O backend usa OpenRouter como motor principal das falas dos bots, com um único modelo principal e um único fallback externo.

## Variáveis

```bash
OPENROUTER_API_KEY=sua_chave_aqui
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_SITE_URL=http://localhost:5173
OPENROUTER_APP_NAME=Deadly Truth
OPENROUTER_PRIMARY_MODEL=qwen/qwen3-next-80b-a3b-instruct:free
OPENROUTER_FALLBACK_MODEL=z-ai/glm-4.5-air:free
AI_TIMEOUT_SECONDS=10
```

## Ordem de tentativa

1. `qwen/qwen3-next-80b-a3b-instruct:free`
2. `z-ai/glm-4.5-air:free`
3. fallback local variado do jogo

Os bots não chamam IA ao entrar no lobby. A IA só é chamada quando o bot precisa falar, defender, votar ou responder interrogatório.

## Logs

Procure por:

```text
[OPENROUTER] Tentando modelo principal
[OPENROUTER] Sucesso com modelo principal
[OPENROUTER] Falha no modelo principal, tentando fallback
[OPENROUTER] Sucesso com fallback
[BOT_REPLY] bot=Shadow_Hunter source=openrouter
```
