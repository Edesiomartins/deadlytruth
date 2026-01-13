# 🚂 Setup Railway - Deadly Truth

Guia passo a passo para configurar o projeto no Railway.

---

## 📋 Pré-requisitos

- ✅ Projeto criado no Railway
- ✅ Repositório conectado ao GitHub
- ✅ Chave API do Groq (`GROQ_API_KEY`)

---

## 🔧 Passo 1: Configurar Backend (FastAPI)

### 1.1 Adicionar Serviço Backend

1. No projeto Railway, clique em **"New"** → **"Service"** → **"GitHub Repo"**
2. Selecione o repositório `deadlytruth`
3. Railway detectará automaticamente o código

### 1.2 Configurar Root Directory

1. Clique no serviço recém-criado
2. Vá em **Settings** → **Service**
3. No campo **Root Directory**, digite: `fastapi-server`
4. Salve

### 1.3 Verificar Start Command

1. Vá em **Settings** → **Deploy**
2. Campo **Start Command** deve estar **VAZIO** (usa o Procfile automaticamente)
3. Se não estiver vazio, limpe o campo

### 1.4 Configurar Porta

1. Vá em **Settings** → **Networking**
2. Campo **Port** deve estar **VAZIO** (Railway usa `$PORT` automaticamente)

### 1.5 Adicionar Variáveis de Ambiente

1. Vá em **Variables** (ou **Variables & Secrets**)
2. Clique em **+ New Variable**
3. Adicione:

   **Variável 1:**
   - Nome: `GROQ_API_KEY`
   - Valor: Sua chave API do Groq (ex: `gsk_...`)
   - Clique em **Add**

   **Variável 2 (opcional por enquanto):**
   - Nome: `ALLOWED_ORIGINS`
   - Valor: `*` (temporário, atualize depois com URL do frontend)
   - Clique em **Add**

### 1.6 Obter URL do Backend

1. Vá em **Settings** → **Networking**
2. Clique em **"Generate Domain"** (se ainda não tiver)
3. Anote a URL (ex: `https://deadly-truth-backend-production.up.railway.app`)
4. Para WebSocket, use `wss://` (ex: `wss://deadly-truth-backend-production.up.railway.app`)

### 1.7 Verificar Deploy

1. Vá em **Deployments**
2. Aguarde o deploy completar
3. Veja os logs - deve aparecer:
   - ✅ `GROQ_API_KEY encontrada`
   - ✅ `Application startup complete`
   - ✅ `Uvicorn running on http://0.0.0.0:XXXX`

4. Teste acessando: `https://sua-url-backend.up.railway.app/health`
   - Deve retornar: `{"status": "ok", "message": "Servidor rodando"}`

---

## 🎨 Passo 2: Configurar Frontend (React/Vite)

### 2.1 Adicionar Serviço Frontend

1. No mesmo projeto Railway, clique em **"New"** → **"Service"** → **"GitHub Repo"**
2. Selecione o mesmo repositório `deadlytruth`
3. Railway detectará automaticamente o código

### 2.2 Configurar Root Directory

1. Clique no serviço do frontend
2. Vá em **Settings** → **Service**
3. No campo **Root Directory**, digite: `deadly-truth-frontend`
4. Salve

### 2.3 Verificar Build e Start

1. Vá em **Settings** → **Deploy**
2. Railway detectará automaticamente:
   - **Build Command**: `npm install && npm run build`
   - **Start Command**: `npm run preview` (usa `$PORT` automaticamente)

### 2.4 Configurar Porta

1. Vá em **Settings** → **Networking**
2. Campo **Port** deve estar **VAZIO** (Railway usa `$PORT` automaticamente)

### 2.5 Adicionar Variável de Ambiente

1. Vá em **Variables**
2. Clique em **+ New Variable**
3. Adicione:

   **Variável:**
   - Nome: `VITE_BACKEND_URL`
   - Valor: `wss://sua-url-backend.up.railway.app/ws/sala_geral`
     - ⚠️ Substitua `sua-url-backend.up.railway.app` pela URL real do backend
     - ⚠️ Use `wss://` (não `ws://`) para HTTPS
   - Clique em **Add**

### 2.6 Obter URL do Frontend

1. Vá em **Settings** → **Networking**
2. Clique em **"Generate Domain"**
3. Anote a URL (ex: `https://deadly-truth-frontend-production.up.railway.app`)

### 2.7 Verificar Deploy

1. Vá em **Deployments**
2. Aguarde o deploy completar
3. Veja os logs - deve aparecer:
   - ✅ Build completo
   - ✅ Servidor iniciado

4. Teste acessando a URL do frontend no navegador

---

## 🔄 Passo 3: Atualizar CORS do Backend

Após ter a URL do frontend:

1. Volte ao serviço do **backend**
2. Vá em **Variables**
3. Edite a variável `ALLOWED_ORIGINS`:
   - Valor: `https://sua-url-frontend.up.railway.app`
     - ⚠️ Substitua pela URL real do frontend
4. Salve
5. Aguarde o redeploy automático

---

## ✅ Passo 4: Verificar Tudo

### Backend
- [ ] URL acessível: `https://sua-url-backend.up.railway.app/health`
- [ ] Retorna: `{"status": "ok"}`
- [ ] Logs mostram servidor rodando

### Frontend
- [ ] URL acessível no navegador
- [ ] Página carrega sem erros
- [ ] Console do navegador não mostra erros de conexão

### Integração
- [ ] Frontend conecta ao backend via WebSocket
- [ ] Status mostra "Sistema Ativo" (indicador verde)
- [ ] Funcionalidades do jogo funcionam

---

## 🔍 Troubleshooting

### Backend não inicia
- Verifique se `GROQ_API_KEY` está configurada
- Veja os logs de deploy para erros
- Verifique se Root Directory está como `fastapi-server`

### Frontend não conecta ao backend
- Verifique se `VITE_BACKEND_URL` está correto (use `wss://`)
- Verifique se `ALLOWED_ORIGINS` no backend inclui a URL do frontend
- Veja o console do navegador para erros

### Erro 502 ou "Application failed to respond"
- Veja os logs de deploy completos
- Verifique se o servidor realmente iniciou
- Verifique Root Directory e Start Command

---

## 📝 Checklist Final

### Backend
- [ ] Root Directory: `fastapi-server`
- [ ] Start Command: vazio
- [ ] Port: vazio
- [ ] `GROQ_API_KEY` configurada
- [ ] `ALLOWED_ORIGINS` configurada (com URL do frontend)
- [ ] URL do backend anotada

### Frontend
- [ ] Root Directory: `deadly-truth-frontend`
- [ ] Port: vazio
- [ ] `VITE_BACKEND_URL` configurada (com URL do backend)
- [ ] URL do frontend anotada

### Integração
- [ ] CORS atualizado no backend
- [ ] Frontend conecta ao backend
- [ ] Tudo funcionando

---

## 🎉 Pronto!

Seu projeto está no ar! Acesse a URL do frontend e comece a jogar.

---

## 💡 Dicas

- **Logs**: Sempre verifique os logs de deploy para diagnosticar problemas
- **Variáveis**: Use variáveis de ambiente, nunca hardcode chaves no código
- **Redeploy**: Após mudar variáveis, o Railway faz redeploy automático
- **Domínios**: Você pode gerar domínios personalizados em Settings → Networking
