# 🤖 Configuração do DeepSeek AI

## O que mudou?

Agora o backend suporta **dois provedores de IA**:
- ✅ **Groq** (Llama 3.3 70B) - Rápido e poderoso
- ✅ **DeepSeek** (DeepSeek-V3/Chat) - Muito inteligente e barato

## Como configurar?

### 1. Adicione as variáveis no `.env`:

```bash
# Escolha qual provedor usar: "groq" ou "deepseek"
AI_PROVIDER=deepseek

# Chave da API DeepSeek (https://platform.deepseek.com/)
DEEPSEEK_API_KEY=sk-sua_chave_aqui

# Se quiser usar Groq (opcional)
GROQ_API_KEY=gsk_sua_chave_aqui
```

### 2. Obtenha sua chave do DeepSeek:

1. Acesse: https://platform.deepseek.com/
2. Crie uma conta
3. Vá em **API Keys**
4. Copie sua chave (começa com `sk-`)

### 3. Instale as dependências atualizadas:

```bash
cd fastapi-server
pip install -r requirements.txt
```

### 4. Reinicie o servidor:

```bash
python main.py
# ou
uvicorn main:app --reload
```

## Qual provedor escolher?

| Provedor | Modelo | Velocidade | Inteligência | Preço |
|----------|--------|------------|--------------|-------|
| **Groq** | Llama 3.3 70B | ⚡⚡⚡ Muito rápido | 🧠🧠🧠 Bom | 💰 Grátis (limite) |
| **DeepSeek** | DeepSeek-V3 | ⚡⚡ Rápido | 🧠🧠🧠🧠 Excelente | 💰 Muito barato |

### Recomendação:
- **DeepSeek** é melhor para:
  - 📝 Histórias complexas
  - 🎭 Personagens detalhados
  - 🧩 Pistas elaboradas
  - 💬 Diálogos naturais

- **Groq** é melhor para:
  - ⚡ Respostas super rápidas
  - 🎮 Interações em tempo real
  - 💸 Economia (grátis)

## Como funciona?

O código detecta automaticamente qual provedor usar baseado na variável `AI_PROVIDER` no `.env`:

```python
# Se AI_PROVIDER=deepseek
ai_generate(prompt, system)  # Usa DeepSeek

# Se AI_PROVIDER=groq (ou não definido)
ai_generate(prompt, system)  # Usa Groq (padrão)
```

## Migração

Todas as chamadas antigas `groq_generate()` continuam funcionando! Elas agora chamam `ai_generate()` automaticamente.

## Testes

Para testar, faça uma requisição ao `/gerar_caso` e veja qual provedor está sendo usado no log do servidor:

```
🤖 Usando DeepSeek-V3...
```

ou

```
🤖 Usando Groq (Llama 3.3 70B)...
```

## Preços do DeepSeek (2026)

- **DeepSeek-V3**: $0.27 / 1M tokens input, $1.10 / 1M tokens output
- **DeepSeek-Chat**: $0.14 / 1M tokens input, $0.28 / 1M tokens output

Exemplo: Uma história completa (~1000 tokens) custa **menos de $0.001** 🤑

## Suporte

Problemas? Verifique:
1. ✅ `DEEPSEEK_API_KEY` está no `.env`
2. ✅ Chave é válida (teste em https://platform.deepseek.com/)
3. ✅ `openai` foi instalado: `pip install openai`
4. ✅ Servidor foi reiniciado

---

**Pronto para criar histórias incríveis com DeepSeek! 🚀**
