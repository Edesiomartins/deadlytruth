# Snapshot do Projeto (para outra LLM)

## Contexto geral
- Projeto: Deadly Truth (frontend React/Vite + backend FastAPI).
- Deploy no Railway (backend e frontend em serviços separados).
- WebSocket multiplayer ativo.
- Autenticação JWT implementada no backend.

---

## Backend (FastAPI)

### Arquivos adicionados
- `fastapi-server/database.py`
  - SQLAlchemy engine + session, suporta Postgres e SQLite.
  - Ajusta `postgres://` para `postgresql+psycopg2://`.
  - `init_db()` cria as tabelas no startup.
- `fastapi-server/models.py`
  - Modelo `User` com `email`, `hashed_password`, `created_at`.
- `fastapi-server/schemas.py`
  - `UserCreate`, `UserOut`, `Token`.
- `fastapi-server/auth_utils.py`
  - Hash/verify de senha (bcrypt).
  - JWT (HS256).
  - `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`.
- `fastapi-server/auth_routes.py`
  - `/auth/register` (JSON `{email, password}`).
  - `/auth/login` (form-urlencoded via OAuth2PasswordRequestForm).
  - `/auth/me` (Bearer token).
  - `get_current_user` (valida JWT).

### `fastapi-server/main.py`
- Carrega `.env` local quando existe.
- Logs de debug para variáveis GROQ.
- Inicializa DB no startup (`init_db()`).
- CORS via `ALLOWED_ORIGINS`.
- Inclui `auth_router`.
- WebSocket aceita token via query param:
  - `REQUIRE_AUTH_WS=true` bloqueia WS sem token.
  - Se token presente, usa `sub` como label no chat.

### Requirements
`fastapi-server/requirements.txt` inclui:
- `fastapi`, `uvicorn[standard]`, `groq`, `pydantic`, `python-dotenv`, `httpx`
- `sqlalchemy`, `passlib[bcrypt]`, `python-jose[cryptography]`, `psycopg2-binary`
- `python-multipart` (necessário para `OAuth2PasswordRequestForm`)

---

## Frontend (React/Vite)

### Autenticação
Arquivos criados/alterados:
- `deadly-truth-frontend/src/context/AuthContext.jsx`
  - Valida sessão no startup via `/auth/me`.
  - Login `/auth/login` (form-urlencoded).
  - Register `/auth/register` (JSON).
  - `VITE_ALLOW_MOCK_AUTH=true` ativa modo mock (sem backend).
- `deadly-truth-frontend/src/pages/Login.jsx`
- `deadly-truth-frontend/src/pages/Register.jsx`
- `deadly-truth-frontend/src/components/ProtectedRoute.jsx`
- `deadly-truth-frontend/src/pages/Lobby.jsx` (movido do App original)
- `deadly-truth-frontend/src/App.jsx` (rotas + AuthProvider)

### WebSocket
- `Lobby.jsx` conecta com:
  - `VITE_BACKEND_URL` (fallback: `ws://localhost:8000/ws/sala_geral`).
  - Anexa token JWT na query: `?token=...`.

### Estilo
- `tailwind.config.js` atualizado com cores custom (paleta noir).
- `vite.config.js` com `preview.allowedHosts` para Railway.

### Dependencias frontend
- `react-router-dom` instalado.
- `framer-motion`, `lucide-react` usados.

---

## Variáveis de ambiente (Railway)

### Backend
- `DATABASE_URL` (Postgres Railway)
- `SECRET_KEY` (chave forte JWT)
- `ACCESS_TOKEN_EXPIRE_MINUTES` (ex: `60`)
- `REQUIRE_AUTH_WS` (`true`/`false`)
- `ALLOWED_ORIGINS` (URL do frontend)
- `GROQ_API_KEY`
- `PORT` (Railway define automaticamente)

### Frontend
- `VITE_API_URL` (URL do backend HTTP)
- `VITE_BACKEND_URL` (URL WS, ex: `wss://.../ws/sala_geral`)
- `VITE_ALLOW_MOCK_AUTH` (`false` em prod)

---

## Deploy Railway (resumo)

### Backend
- Root Directory: `fastapi-server`
- Procfile: `web: uvicorn main:app --host 0.0.0.0 --port $PORT`
- Runtime: Python 3.12 no Railway

### Frontend
- Root Directory: `deadly-truth-frontend`
- `nixpacks.toml` com Node 20
- `npm run build` / `npm run preview`

---

## Erros resolvidos
- Vite bloqueando host: `allowedHosts` no `vite.config.js`.
- Python 3.11.0 no Railway: ajustado para 3.12.
- Backend crash por `python-multipart` ausente: adicionado.

---

## Observações
- Tabelas são criadas automaticamente no startup (`init_db()`).
- Se quiser migrations, adicionar Alembic.
- Endpoints atuais: `/`, `/health`, `/auth/register`, `/auth/login`, `/auth/me`, `/ws/{room_id}`, `/case/*`.

