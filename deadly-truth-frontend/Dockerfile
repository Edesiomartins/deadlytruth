# Dockerfile customizado para evitar problema com NIXPACKS_PATH
FROM node:22-alpine

# Define variável de ambiente que o Nixpacks espera
ENV NIXPACKS_PATH=/nix/store

# Define diretório de trabalho
WORKDIR /app

# Copia arquivos de dependências
COPY package*.json ./

# Instala dependências
RUN npm ci

# Copia código fonte
COPY . .

# Build da aplicação
RUN npm run build

# Expõe porta (será sobrescrita pela variável $PORT)
EXPOSE 3000

# Comando de start (usa variável $PORT do Railway)
CMD sh -c "npm run preview -- --host 0.0.0.0 --port ${PORT:-3000}"
