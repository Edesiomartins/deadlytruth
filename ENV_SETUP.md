# 🔐 Configuração de Variáveis de Ambiente

## 📝 Arquivo .env para Desenvolvimento Local

O arquivo `.env` é usado **apenas para desenvolvimento local**. No Railway, as variáveis são configuradas diretamente no painel.

---

## 🔧 Backend (`fastapi-server/.env`)

Remova qualquer referência ao **Render** e mantenha apenas:

```env
# Chave API do Groq (obrigatória)
GROQ_API_KEY=sua-chave-groq-aqui

# URLs permitidas para CORS (separadas por vírgula)
# Para desenvolvimento local
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173

# Porta do servidor (opcional - padrão: 8000)
PORT=8000
```

### ❌ Remover do .env (se existir):
- Qualquer variável com `RENDER_` no nome
- URLs do Render (ex: `https://deadlytruth.onrender.com`)
- Configurações específicas do Render

### ✅ Manter apenas:
- `GROQ_API_KEY` - Sua chave da API Groq
- `ALLOWED_ORIGINS` - URLs do frontend (localhost para dev)
- `PORT` - Porta local (opcional)

---

## 🎨 Frontend (`deadly-truth-frontend/.env`)

Crie um arquivo `.env` na pasta `deadly-truth-frontend/` com:

```env
# URL do Backend WebSocket
# Para desenvolvimento local
VITE_BACKEND_URL=ws://localhost:8000/ws/sala_geral
```

### ⚠️ Importante:
- Use `ws://` (não seguro) para desenvolvimento local
- Use `wss://` (seguro) apenas no Railway (produção)
- Não inclua URLs do Render ou Vercel

---

## 🚂 Variáveis no Railway

### Backend (Serviço Backend)
Configure no painel do Railway:
```
GROQ_API_KEY=sua-chave-groq-aqui
ALLOWED_ORIGINS=https://seu-frontend.up.railway.app
```

### Frontend (Serviço Frontend)
Configure no painel do Railway:
```
VITE_BACKEND_URL=wss://sua-url-backend.up.railway.app/ws/sala_geral
```

---

## ✅ Checklist de Limpeza

- [ ] Remover variáveis do Render do `.env` do backend
- [ ] Remover URLs do Render do `.env` do backend
- [ ] Criar `.env` no frontend (se não existir)
- [ ] Verificar que não há referências ao Render/Vercel
- [ ] Configurar variáveis no Railway (produção)

---

## 🔒 Segurança

- **NUNCA** commite arquivos `.env` com chaves reais
- O `.gitignore` já protege arquivos `.env`
- Use variáveis de ambiente do Railway para produção
- Mantenha `.env` apenas para desenvolvimento local
