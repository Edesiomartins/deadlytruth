# 🔧 Solução para Erro 502 no Railway

## ✅ Checklist de Verificação

Se você já configurou a `GROQ_API_KEY` mas o erro 502 persiste, verifique:

### 1. Root Directory está correto?

**No Railway:**
1. Vá no serviço do backend
2. **Settings** → **Service**
3. Verifique o campo **Root Directory**
4. Deve ser: `fastapi-server` (sem barra no final)

**❌ Errado:**
- `/fastapi-server`
- `fastapi-server/`
- (vazio)

**✅ Correto:**
- `fastapi-server`

---

### 2. Procfile está no lugar certo?

O `Procfile` deve estar em:
```
fastapi-server/Procfile
```

**Conteúdo do Procfile:**
```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

**Verifique:**
- [ ] Arquivo existe em `fastapi-server/Procfile`
- [ ] Conteúdo está correto (sem espaços extras)
- [ ] Está commitado no Git

---

### 3. Verifique os Logs de Deploy

**No Railway:**
1. Vá em **Deployments**
2. Clique no deployment mais recente
3. Veja os logs de **Build** e **Runtime**

**Procure por:**
- ✅ `Application startup complete` - Servidor iniciou
- ✅ `Uvicorn running on http://0.0.0.0:XXXX` - Servidor está escutando
- ❌ `ModuleNotFoundError` - Dependência faltando
- ❌ `ImportError` - Erro de importação
- ❌ `SyntaxError` - Erro de sintaxe no código
- ❌ `FileNotFoundError` - Arquivo não encontrado

---

### 4. Verifique o Start Command

**No Railway:**
1. Vá no serviço do backend
2. **Settings** → **Deploy**
3. Verifique o campo **Start Command**

**Deve estar:**
- Vazio (deixar o Railway usar o Procfile)
- OU: `uvicorn main:app --host 0.0.0.0 --port $PORT`

**❌ Não use:**
- `python main.py`
- `uvicorn main:app` (sem host e port)

---

### 5. Verifique a Porta

**No Railway:**
1. Vá no serviço do backend
2. **Settings** → **Networking**
3. Campo **Port**

**Opções:**
- Deixe em **branco** (recomendado - Railway usa `$PORT` automaticamente)
- OU configure: `8000`

---

### 6. Verifique se o código está atualizado

**Certifique-se de que:**
- [ ] Código foi commitado no Git
- [ ] Push foi feito para o repositório
- [ ] Railway está conectado ao branch correto (geralmente `main`)

**Force um novo deploy:**
1. Vá em **Deployments**
2. Clique nos três pontos (...) do deployment
3. Selecione **Redeploy**

---

### 7. Verifique Dependências

**Certifique-se de que `requirements.txt` está completo:**

```txt
fastapi
uvicorn[standard]
groq
pydantic
python-dotenv
httpx
```

**Verifique nos logs de build:**
- Deve aparecer: `Successfully installed fastapi uvicorn groq...`

---

### 8. Teste Localmente Primeiro

**Antes de fazer deploy, teste localmente:**

```bash
cd fastapi-server
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

**Se funcionar localmente mas não no Railway:**
- Problema de configuração do Railway
- Verifique Root Directory e Start Command

**Se não funcionar localmente:**
- Problema no código
- Verifique os erros no terminal

---

## 🚨 Erros Comuns e Soluções

### Erro: "ModuleNotFoundError: No module named 'groq'"
**Solução:** Verifique se `requirements.txt` contém todas as dependências

### Erro: "Address already in use"
**Solução:** Railway gerencia a porta automaticamente, não configure manualmente

### Erro: "FileNotFoundError: Procfile"
**Solução:** Certifique-se de que o Procfile está em `fastapi-server/Procfile`

### Erro: "Root Directory not found"
**Solução:** Configure Root Directory como `fastapi-server` (sem barra)

---

## 📋 Checklist Final

Antes de reportar o problema, verifique:

- [ ] Root Directory: `fastapi-server`
- [ ] Procfile existe e está correto
- [ ] Start Command está vazio ou correto
- [ ] Port está vazio ou configurado como `8000`
- [ ] GROQ_API_KEY está configurada no Railway
- [ ] Código foi commitado e push feito
- [ ] Logs de deploy foram verificados
- [ ] Teste local funciona

---

## 🔍 Como Ver os Logs Completos

1. **No Railway:**
   - Vá em **Deployments**
   - Clique no deployment
   - Veja aba **Build Logs** e **Deploy Logs**

2. **Copie os logs completos** e verifique:
   - Se há erros em vermelho
   - Se o servidor realmente iniciou
   - Qual porta está sendo usada

---

## 💡 Dica Final

Se nada funcionar, tente:

1. **Criar um novo serviço** no Railway
2. **Configurar tudo do zero**
3. **Copiar a configuração que funcionou**

Às vezes, recomeçar do zero resolve problemas de configuração.
