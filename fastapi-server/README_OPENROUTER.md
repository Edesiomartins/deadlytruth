# 🌐 Configuração do OpenRouter AI

## O que é OpenRouter?

O **OpenRouter** é uma plataforma que oferece acesso a **múltiplos modelos de IA** através de uma única API, incluindo:
- Meta Llama 3.3 70B
- GPT-4, GPT-3.5
- Claude (Anthropic)
- Gemini (Google)
- E muitos outros!

## Como configurar?

### 1. Adicione as variáveis no `.env`:

```bash
# Escolha qual provedor usar: "groq", "deepseek" ou "openrouter"
AI_PROVIDER=openrouter

# Chave da API OpenRouter (https://openrouter.ai/)
OPENROUTER_API_KEY=sk-or-v1-sua_chave_aqui

# Modelo a ser usado (opcional, padrão: meta-llama/llama-3.3-70b-instruct)
OPENROUTER_MODEL=meta-llama/llama-3.3-70b-instruct
```

### 2. Obtenha sua chave do OpenRouter:

1. Acesse: https://openrouter.ai/
2. Crie uma conta ou faça login
3. Vá em **Keys** (no menu lateral)
4. Clique em **Create Key**
5. Copie sua chave (começa com `sk-or-v1-`)

### 3. Escolha um modelo:

Você pode usar qualquer modelo disponível no OpenRouter. Alguns recomendados:

**Para qualidade máxima:**
- `meta-llama/llama-3.3-70b-instruct` (padrão)
- `anthropic/claude-3.5-sonnet`
- `openai/gpt-4-turbo`

**Para velocidade:**
- `meta-llama/llama-3.1-8b-instruct`
- `google/gemini-pro-1.5`

**Para economia:**
- `meta-llama/llama-3.1-8b-instruct`
- `mistralai/mistral-7b-instruct`

Veja todos os modelos disponíveis em: https://openrouter.ai/models

### 4. Configure no Railway:

1. Vá no serviço do backend → **Variables**
2. Adicione:
   - `AI_PROVIDER` = `openrouter`
   - `OPENROUTER_API_KEY` = sua chave (começa com `sk-or-v1-`)
   - `OPENROUTER_MODEL` = modelo desejado (opcional)
3. Salve e aguarde redeploy automático

## Comparação de Provedores

| Provedor | Modelos | Velocidade | Qualidade | Preço |
|----------|---------|------------|-----------|-------|
| **Groq** | Llama 3.3 70B | ⚡⚡⚡ Muito rápido | 🧠🧠🧠 Bom | 💰 Grátis (limite) |
| **DeepSeek** | DeepSeek-V3 | ⚡⚡ Rápido | 🧠🧠🧠🧠 Excelente | 💰 Muito barato |
| **OpenRouter** | 100+ modelos | ⚡⚡⚡ Variável | 🧠🧠🧠🧠🧠 Máxima | 💰 Variável |

### Vantagens do OpenRouter:

✅ **Acesso a múltiplos modelos** - Escolha o melhor para cada tarefa  
✅ **Flexibilidade** - Mude de modelo sem mudar código  
✅ **Modelos premium** - GPT-4, Claude, Gemini  
✅ **Preços competitivos** - Compare preços entre modelos  
✅ **Fallback automático** - Se um modelo falhar, tenta outro  

## Como funciona?

O código detecta automaticamente qual provedor usar baseado na variável `AI_PROVIDER`:

```python
# Se AI_PROVIDER=openrouter
generate_case()  # Usa OpenRouter com modelo configurado
ai_generate()    # Usa OpenRouter

# Se AI_PROVIDER=groq (ou não definido)
generate_case()  # Usa Groq
ai_generate()    # Usa Groq (padrão)
```

## Exemplos de Modelos OpenRouter

### Para casos de jogo (recomendado):
```bash
OPENROUTER_MODEL=meta-llama/llama-3.3-70b-instruct
```

### Para máxima qualidade:
```bash
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet
```

### Para velocidade:
```bash
OPENROUTER_MODEL=meta-llama/llama-3.1-8b-instruct
```

### Para economia:
```bash
OPENROUTER_MODEL=mistralai/mistral-7b-instruct
```

## Migração

Todas as funções existentes (`generate_case()`, `ai_generate()`) agora suportam OpenRouter automaticamente. Basta configurar as variáveis de ambiente!

## Troubleshooting

**Erro: "OPENROUTER_API_KEY não encontrada"**
- Verifique se a variável está configurada no `.env` ou Railway
- Certifique-se de que o nome está correto: `OPENROUTER_API_KEY`

**Erro: "Model not found"**
- Verifique se o modelo existe em https://openrouter.ai/models
- Use o nome exato do modelo (ex: `meta-llama/llama-3.3-70b-instruct`)

**Erro: "Insufficient credits"**
- Adicione créditos na sua conta OpenRouter
- Verifique os limites de uso em https://openrouter.ai/activity
