# Criacao do banco (Railway Postgres)

Este projeto usa PostgreSQL no Railway. As tabelas sao criadas automaticamente no startup do backend.

## Passo a passo no Railway
1. No projeto, clique em **Add** e crie um **PostgreSQL**.
2. Abra o servico do **backend** e va em **Variables**.
3. Adicione/garanta as variaveis:
   - `DATABASE_URL` (o Railway cria automaticamente ao linkar o Postgres)
   - `SECRET_KEY` (chave forte e secreta)
   - `ACCESS_TOKEN_EXPIRE_MINUTES` (ex: `60`)
   - `REQUIRE_AUTH_WS` (`true` para exigir token no WebSocket)
4. Salve e aguarde o redeploy.

## Criacao das tabelas
As tabelas sao criadas automaticamente ao subir o backend (via `init_db()`).
Nao e necessario rodar comandos manualmente.

## Verificar se o banco esta ok
Teste o endpoint:
- `GET /health`

E depois:
- `POST /auth/register`

Se registrar funcionar, a tabela `users` foi criada.

## Local (opcional)
Se quiser rodar localmente:
1. Crie `fastapi-server/.env` com:
   - `DATABASE_URL=postgresql://usuario:senha@host:porta/banco`
   - `SECRET_KEY=uma_chave_forte`
2. Inicie o backend.

