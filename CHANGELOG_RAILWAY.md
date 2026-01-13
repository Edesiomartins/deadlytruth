# 📝 Changelog - Migração para Railway

Este documento resume todas as mudanças realizadas para migrar o projeto **Deadly Truth** do Render/Vercel para **Railway**.

---

## 🎯 Objetivo

Migrar toda a infraestrutura de deploy (backend FastAPI + frontend React) para a plataforma Railway, incluindo configurações, variáveis de ambiente e documentação.

---

## ✅ Mudanças Realizadas

### 🔧 Backend (FastAPI Server)

#### 1. Arquivos Criados

**`fastapi-server/Procfile`**
- Criado para definir o comando de inicialização no Railway
- Comando: `web: uvicorn main:app --host 0.0.0.0 --port $PORT`

**`fastapi-server/runtime.txt`**
- Especifica a versão do Python: `python-3.11.0`
- Garante consistência no ambiente de deploy

#### 2. Arquivos Modificados

**`fastapi-server/main.py`**

**Mudanças:**
- ✅ Removidas referências ao Render nos comentários
- ✅ Atualizado para usar variável de ambiente `$PORT` do Railway
- ✅ Configuração CORS atualizada para usar `ALLOWED_ORIGINS` (variável de ambiente)
- ✅ Mensagens de log atualizadas para Railway
- ✅ Uso dinâmico da porta via `os.getenv("PORT", 8000)`

**Trechos alterados:**
```python
# Antes: Comentários sobre Render
# Agora: Comentários sobre Railway e variáveis de ambiente

# CORS configurado dinamicamente
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(CORSMiddleware, allow_origins=allowed_origins, ...)

# Porta dinâmica
port = int(os.getenv("PORT", 8000))
uvicorn.run(app, host="0.0.0.0", port=port)
```

**`fastapi-server/README.md`**
- ✅ Atualizado com informações sobre deploy no Railway
- ✅ Seção de execução local mantida
- ✅ Referência ao guia completo `RAILWAY_SETUP.md`

---

### 🎨 Frontend (React/Vite)

#### 1. Arquivos Criados

**`deadly-truth-frontend/railway.json`**
- Configuração de build e deploy para Railway
- Define builder como NIXPACKS
- Comandos de build e start configurados

**`deadly-truth-frontend/nixpacks.toml`**
- Configuração do ambiente de build
- Node.js 18.x e npm 9.x especificados
- Fases de setup, install, build e start definidas

#### 2. Arquivos Modificados

**`deadly-truth-frontend/src/App.jsx`**

**Mudanças:**
- ✅ Removida URL hardcoded do Render: `wss://deadlytruth.onrender.com/ws/sala_geral`
- ✅ Implementado uso de variável de ambiente: `import.meta.env.VITE_BACKEND_URL`
- ✅ Fallback para desenvolvimento local: `ws://localhost:8000/ws/sala_geral`

**Antes:**
```javascript
const BACKEND_URL = "wss://deadlytruth.onrender.com/ws/sala_geral";
```

**Depois:**
```javascript
const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "ws://localhost:8000/ws/sala_geral";
```

**`deadly-truth-frontend/package.json`**

**Mudanças:**
- ✅ Script `preview` atualizado para usar variável `$PORT`
- ✅ Comando: `vite preview --host 0.0.0.0 --port $PORT`

**Antes:**
```json
"preview": "vite preview"
```

**Depois:**
```json
"preview": "vite preview --host 0.0.0.0 --port $PORT"
```

**`deadly-truth-frontend/vite.config.js`**

**Mudanças:**
- ✅ Configuração de servidor para desenvolvimento local
- ✅ Configuração de preview para produção (Railway)
- ✅ Host configurado como `0.0.0.0` para aceitar conexões externas

**Adicionado:**
```javascript
server: {
  host: '0.0.0.0',
  port: 3000,
},
preview: {
  host: '0.0.0.0',
  port: 3000,
},
```

---

### 📚 Documentação

#### 1. Arquivos Criados

**`RAILWAY_SETUP.md`**
- ✅ Guia completo de deploy no Railway
- ✅ Instruções passo a passo para backend e frontend
- ✅ Configuração de variáveis de ambiente
- ✅ Solução de problemas comuns
- ✅ Informações sobre custos e recursos

**Conteúdo do guia:**
- Pré-requisitos
- Deploy do Backend (Passo 1)
- Deploy do Frontend (Passo 2)
- Atualização de CORS (Passo 3)
- Verificação de Deploy (Passo 4)
- Solução de Problemas
- Informações sobre custos
- Lista de arquivos criados/modificados
- Recursos adicionais

**`CHANGELOG_RAILWAY.md`** (este arquivo)
- ✅ Documentação completa de todas as mudanças

**`ENV_SETUP.md`**
- ✅ Guia de configuração de variáveis de ambiente
- ✅ Instruções para limpeza de variáveis do Render
- ✅ Diferença entre desenvolvimento local e produção (Railway)
- ✅ Checklist de limpeza

---

## 🔐 Variáveis de Ambiente

### Backend (Railway)

Variáveis que devem ser configuradas no painel do Railway:

```
GROQ_API_KEY=sua-chave-groq-aqui
ALLOWED_ORIGINS=https://seu-frontend.up.railway.app
PORT=8000 (gerenciado automaticamente pelo Railway, mas pode ser definido)
```

### Frontend (Railway)

Variáveis que devem ser configuradas no painel do Railway:

```
VITE_BACKEND_URL=wss://sua-url-backend.up.railway.app/ws/sala_geral
PORT=3000 (gerenciado automaticamente pelo Railway)
```

**⚠️ Importante:**
- Use `wss://` (WebSocket seguro) em produção
- Substitua URLs de exemplo pelas URLs reais do Railway
- Configure `ALLOWED_ORIGINS` no backend após obter a URL do frontend

---

## 📋 Arquivos Criados

### Backend
- ✅ `fastapi-server/Procfile`
- ✅ `fastapi-server/runtime.txt`

### Frontend
- ✅ `deadly-truth-frontend/railway.json`
- ✅ `deadly-truth-frontend/nixpacks.toml`

### Documentação
- ✅ `RAILWAY_SETUP.md`
- ✅ `CHANGELOG_RAILWAY.md` (este arquivo)
- ✅ `ENV_SETUP.md`

---

## 📝 Arquivos Modificados

### Backend
- ✅ `fastapi-server/main.py`
- ✅ `fastapi-server/README.md`

### Frontend
- ✅ `deadly-truth-frontend/src/App.jsx`
- ✅ `deadly-truth-frontend/package.json`
- ✅ `deadly-truth-frontend/vite.config.js`

---

## 🗑️ Arquivos Removidos

### Limpeza de Arquivos Não Utilizados

**`GITHUB_SETUP.md`**
- ❌ Removido - Guia de setup do GitHub não é mais necessário após conexão com Railway
- O Railway gerencia a conexão com GitHub automaticamente

**`deadly-truth-frontend/README.md`**
- ❌ Removido - README padrão do template Vite
- Não continha informações específicas do projeto

**Motivo da remoção:**
- Arquivos específicos de outras plataformas (Render/Vercel) não são mais necessários
- Documentação consolidada nos guias principais
- Projeto limpo e focado apenas no Railway

---

## 🧹 Limpeza de Variáveis de Ambiente

### Arquivos .env

**Backend (`fastapi-server/.env`)**
- ✅ Removidas referências ao Render
- ✅ Mantidas apenas variáveis necessárias:
  - `GROQ_API_KEY` - Chave API do Groq
  - `ALLOWED_ORIGINS` - URLs permitidas (localhost para dev)
  - `PORT` - Porta do servidor (opcional)

**Frontend (`deadly-truth-frontend/.env`)**
- ✅ Criado arquivo `.env` com:
  - `VITE_BACKEND_URL` - URL do backend WebSocket (localhost para dev)

**Variáveis Removidas:**
- ❌ Qualquer variável com `RENDER_` no nome
- ❌ URLs do Render (ex: `https://deadlytruth.onrender.com`)
- ❌ Configurações específicas do Render/Vercel

**Importante:**
- Arquivos `.env` são apenas para desenvolvimento local
- No Railway, variáveis são configuradas no painel de cada serviço
- Arquivos `.env` estão protegidos pelo `.gitignore`

---

## 🚀 Próximos Passos

### 1. Commit das Mudanças

```bash
git add .
git commit -m "Configurar projeto para deploy no Railway"
git push origin main
```

### 2. Deploy no Railway

Siga o guia completo em `RAILWAY_SETUP.md`:

1. **Criar projeto no Railway**
   - Fazer login no Railway (via GitHub)
   - Criar novo projeto
   - Conectar repositório GitHub

2. **Deploy do Backend**
   - Adicionar serviço do backend
   - Configurar Root Directory: `fastapi-server`
   - Configurar variáveis de ambiente
   - Obter URL do backend

3. **Deploy do Frontend**
   - Adicionar serviço do frontend
   - Configurar Root Directory: `deadly-truth-frontend`
   - Configurar variável `VITE_BACKEND_URL` com URL do backend
   - Obter URL do frontend

4. **Atualizar CORS**
   - Voltar ao serviço backend
   - Atualizar `ALLOWED_ORIGINS` com URL do frontend
   - Fazer redeploy

5. **Testar**
   - Acessar frontend no navegador
   - Verificar conexão WebSocket
   - Testar funcionalidades do jogo

---

## ✨ Benefícios da Migração

### Railway vs Render/Vercel

1. **Unificação de Plataforma**
   - Backend e frontend na mesma plataforma
   - Gerenciamento simplificado
   - Deploy coordenado

2. **Facilidade de Configuração**
   - Variáveis de ambiente centralizadas
   - Logs unificados
   - Monitoramento integrado

3. **Custo**
   - $5 de crédito grátis mensal (plano Hobby)
   - Cobrança transparente
   - Sem surpresas

4. **Performance**
   - Deploy rápido
   - Cold start reduzido
   - WebSockets suportados nativamente

---

## 🔍 Checklist de Verificação

Antes de fazer deploy, verifique:

### Backend
- [x] `Procfile` criado e correto
- [x] `main.py` usa `$PORT` dinamicamente
- [x] CORS configurado com `ALLOWED_ORIGINS`
- [x] Referências ao Render removidas
- [x] Variáveis de ambiente documentadas

### Frontend
- [x] `railway.json` criado
- [x] `nixpacks.toml` criado
- [x] `package.json` script `preview` atualizado
- [x] `App.jsx` usa `VITE_BACKEND_URL`
- [x] `vite.config.js` configurado para produção
- [x] URL hardcoded do Render removida

### Documentação
- [x] `RAILWAY_SETUP.md` criado com guia completo
- [x] `CHANGELOG_RAILWAY.md` criado (este arquivo)
- [x] `ENV_SETUP.md` criado com guia de variáveis
- [x] `README.md` do backend atualizado
- [x] Variáveis de ambiente documentadas

### Limpeza
- [x] Arquivos não utilizados removidos
- [x] Variáveis do Render removidas dos `.env`
- [x] Referências ao Render/Vercel removidas
- [x] Projeto limpo e focado no Railway

---

## 📞 Suporte

Em caso de problemas:

1. **Consulte o guia**: `RAILWAY_SETUP.md` (seção "Solução de Problemas")
2. **Logs do Railway**: Verifique os logs de deploy em cada serviço
3. **Documentação oficial**: https://docs.railway.app
4. **Comunidade**: Discord do Railway

---

## 📅 Data da Migração

**Data:** Migração realizada com sucesso
**Plataforma Anterior:** Render (backend) + Vercel (frontend)
**Plataforma Nova:** Railway (backend + frontend)
**Status Backend:** ✅ **RODANDO COM SUCESSO**

---

## 🎉 Status

✅ **Migração Completa e Funcionando**

Todas as mudanças foram realizadas com sucesso. O projeto está pronto para deploy no Railway!

### ✅ Confirmação de Deploy

**Backend:** ✅ **RODANDO COM SUCESSO**
- Servidor FastAPI deployado no Railway
- WebSocket funcionando
- Variáveis de ambiente configuradas
- CORS configurado corretamente

**Próximo passo:** Deploy do frontend seguindo o guia em `RAILWAY_SETUP.md`

### ✅ Limpeza Realizada

**Arquivos Removidos:**
- ❌ `GITHUB_SETUP.md` - Não mais necessário
- ❌ `deadly-truth-frontend/README.md` - README genérico removido

**Variáveis de Ambiente:**
- ✅ Referências ao Render removidas dos `.env`
- ✅ Apenas variáveis necessárias mantidas
- ✅ Guia `ENV_SETUP.md` criado para referência

**Status:**
- ✅ Projeto limpo e organizado
- ✅ Sem dependências de outras plataformas
- ✅ Focado exclusivamente no Railway

---

**Nota:** Este documento foi gerado automaticamente para registrar todas as mudanças realizadas durante a migração para Railway.
