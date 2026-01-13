# 🚂 Guia de Deploy no Railway

Este guia explica como fazer deploy do **Deadly Truth** (backend FastAPI + frontend React) no Railway.

## 📋 Pré-requisitos

1. Conta no [Railway](https://railway.app) (pode usar GitHub para login)
2. Projeto no GitHub (se ainda não tiver, veja `GITHUB_SETUP.md`)
3. Chave API do Groq (`GROQ_API_KEY`)

## 🏗️ Estrutura do Projeto

O projeto tem duas partes que serão deployadas separadamente:

- **Backend**: `fastapi-server/` - API FastAPI com WebSocket
- **Frontend**: `deadly-truth-frontend/` - Aplicação React/Vite

## 🚀 Passo 1: Deploy do Backend (FastAPI)

### 1.1 Criar Novo Projeto no Railway

1. Acesse https://railway.app
2. Clique em **"New Project"**
3. Selecione **"Deploy from GitHub repo"**
4. Escolha o repositório `Deadly-Truth`
5. Selecione a branch `main` (ou sua branch principal)

### 1.2 Configurar o Serviço Backend

1. Railway detectará automaticamente o código
2. Clique em **"Add Service"** → **"GitHub Repo"** novamente (se necessário)
3. Na raiz do projeto, configure:
   - **Root Directory**: `fastapi-server`
   - **Build Command**: (deixe em branco, o Railway detectará automaticamente)
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### 1.3 Configurar Variáveis de Ambiente

No painel do serviço backend, vá em **Variables** e adicione:

```
GROQ_API_KEY=sua-chave-groq-aqui
ALLOWED_ORIGINS=https://seu-frontend.up.railway.app
PORT=8000
```

**⚠️ IMPORTANTE**: 
- A variável `PORT` é fornecida automaticamente pelo Railway, mas você pode deixá-la para garantir
- `ALLOWED_ORIGINS` deve ser a URL do seu frontend (você atualizará após fazer deploy do frontend)

### 1.4 Obter URL do Backend

1. Vá em **Settings** → **Networking**
2. Clique em **"Generate Domain"** (ou use o domínio automático)
3. Anote a URL (ex: `https://deadly-truth-backend.up.railway.app`)
4. Para WebSocket, use `wss://` (ex: `wss://deadly-truth-backend.up.railway.app`)

## 🎨 Passo 2: Deploy do Frontend (React/Vite)

### 2.1 Criar Novo Serviço no Mesmo Projeto

1. No mesmo projeto Railway, clique em **"New"** → **"Service"** → **"GitHub Repo"**
2. Selecione o mesmo repositório
3. Configure:
   - **Root Directory**: `deadly-truth-frontend`
   - Railway detectará automaticamente que é um projeto Node.js

### 2.2 Configurar Variáveis de Ambiente do Frontend

No painel do serviço frontend, vá em **Variables** e adicione:

```
VITE_BACKEND_URL=wss://sua-url-backend.up.railway.app/ws/sala_geral
PORT=3000
```

**⚠️ IMPORTANTE**:
- Substitua `sua-url-backend.up.railway.app` pela URL real do seu backend
- Use `wss://` (WebSocket seguro) para produção

### 2.3 Configurar Build e Deploy

O Railway detectará automaticamente o `package.json` e usará:
- **Build**: `npm install && npm run build`
- **Start**: `npm run preview` (configurado para usar `$PORT`)

### 2.4 Obter URL do Frontend

1. Vá em **Settings** → **Networking**
2. Clique em **"Generate Domain"**
3. Anote a URL (ex: `https://deadly-truth-frontend.up.railway.app`)

## 🔄 Passo 3: Atualizar CORS do Backend

Após ter a URL do frontend:

1. Volte ao serviço **backend** no Railway
2. Vá em **Variables**
3. Atualize `ALLOWED_ORIGINS`:
   ```
   ALLOWED_ORIGINS=https://deadly-truth-frontend.up.railway.app
   ```
4. Clique em **"Deploy"** para aplicar as mudanças

## ✅ Passo 4: Verificar Deploy

### Testar Backend

1. Acesse: `https://sua-url-backend.up.railway.app/health`
2. Deve retornar: `{"status": "ok", "message": "Servidor rodando"}`

### Testar Frontend

1. Acesse a URL do frontend
2. Abra o console do navegador (F12)
3. Verifique se há erros de conexão WebSocket
4. O status deve mostrar "Sistema Ativo" (indicador verde)

## 🔧 Solução de Problemas

### Backend não inicia

- Verifique se `GROQ_API_KEY` está configurada
- Veja os logs em **Deployments** → **View Logs**
- Certifique-se de que o `Procfile` está correto

### Frontend não conecta ao backend

- Verifique se `VITE_BACKEND_URL` está correto (use `wss://` para HTTPS)
- Certifique-se de que `ALLOWED_ORIGINS` no backend inclui a URL do frontend
- Verifique os logs do backend para erros de CORS

### WebSocket não funciona

- Certifique-se de usar `wss://` (não `ws://`) em produção
- Verifique se o Railway está expondo a porta corretamente
- Os WebSockets no Railway funcionam normalmente, mas podem ter limitações no plano gratuito

### Erro de build no frontend

- Verifique se todas as dependências estão no `package.json`
- Veja os logs de build em **Deployments**
- Certifique-se de que o Node.js 18+ está sendo usado (configurado no `nixpacks.toml`)

## 💰 Custos

Railway oferece:
- **$5 de crédito grátis** por mês no plano Hobby
- Após os créditos, cobra por uso (geralmente muito barato para projetos pequenos)

Para economizar:
- Configure **"Sleep After"** para suspender serviços não utilizados
- Use variáveis de ambiente ao invés de arquivos `.env`

## 📝 Arquivos Criados para Railway

### Backend (`fastapi-server/`)
- ✅ `Procfile` - Define comando de inicialização
- ✅ `runtime.txt` - Versão do Python (opcional, mas recomendado)
- ✅ `main.py` - Atualizado para usar `$PORT` e variáveis de ambiente

### Frontend (`deadly-truth-frontend/`)
- ✅ `railway.json` - Configurações de build e deploy
- ✅ `nixpacks.toml` - Configuração do ambiente de build (Node.js)
- ✅ `package.json` - Script `preview` atualizado para usar `$PORT`
- ✅ `App.jsx` - Atualizado para usar variável de ambiente `VITE_BACKEND_URL`

## 🔐 Segurança

- **NUNCA** commite arquivos `.env` com chaves reais
- Use variáveis de ambiente do Railway para todas as credenciais
- Configure `ALLOWED_ORIGINS` corretamente (não use `*` em produção se possível)

## 📚 Recursos Adicionais

- [Documentação do Railway](https://docs.railway.app)
- [Railway Discord](https://discord.gg/railway)
- [Railway Status](https://status.railway.app)

---

**Pronto!** Seu jogo Deadly Truth está no ar! 🎮🚂
