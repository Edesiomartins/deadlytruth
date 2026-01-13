# 🔧 Corrigir Conexão WebSocket

## ❌ Erro

```
NS_ERROR_WEBSOCKET_CONNECTION_REFUSED
wss://deadlytruth-backend-production.up.railway.app/
```

O WebSocket está tentando conectar na URL base, sem o caminho `/ws/sala_geral`.

---

## ✅ Solução

### No Railway - Serviço Frontend

1. Vá no serviço do **frontend**
2. Clique em **Variables**
3. Verifique a variável `VITE_BACKEND_URL`

**❌ Valor ERRADO:**
```
wss://deadlytruth-backend-production.up.railway.app
```

**✅ Valor CORRETO:**
```
wss://deadlytruth-backend-production.up.railway.app/ws/sala_geral
```

### Passos para Corrigir

1. **Edite a variável `VITE_BACKEND_URL`**
   - Clique no ícone de editar (lápis) ao lado da variável
   - Ou delete e crie novamente

2. **Configure o valor completo:**
   ```
   wss://deadlytruth-backend-production.up.railway.app/ws/sala_geral
   ```
   
   **Importante:**
   - Use `wss://` (não `ws://`) para HTTPS
   - Inclua o caminho completo `/ws/sala_geral`
   - Sem barra no final

3. **Salve** a variável

4. **Aguarde o redeploy automático** (alguns segundos)

5. **Teste novamente** no navegador

---

## 🔍 Verificação

Após configurar, o WebSocket deve conectar em:
```
wss://deadlytruth-backend-production.up.railway.app/ws/sala_geral
```

E não em:
```
wss://deadlytruth-backend-production.up.railway.app/
```

---

## ✅ Checklist

- [ ] Variável `VITE_BACKEND_URL` está no serviço do **frontend** (não backend)
- [ ] Valor usa `wss://` (não `ws://`)
- [ ] Valor inclui o caminho `/ws/sala_geral`
- [ ] Sem barra no final da URL
- [ ] Variável foi salva
- [ ] Aguardou redeploy automático
- [ ] Testou novamente no navegador

---

## 💡 Dica

Se você tiver múltiplos ambientes (desenvolvimento/produção), pode usar:

**Desenvolvimento local:**
```
ws://localhost:8000/ws/sala_geral
```

**Produção (Railway):**
```
wss://deadlytruth-backend-production.up.railway.app/ws/sala_geral
```

O código já tem fallback para desenvolvimento local, então a variável só precisa estar configurada no Railway.
