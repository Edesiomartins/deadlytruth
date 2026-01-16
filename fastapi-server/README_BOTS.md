# 🤖 Sistema de Bots com IA

## O que foi implementado?

Agora o jogo suporta **bots controlados por IA** que podem jogar sozinhos ou com jogadores reais!

### ✨ Funcionalidades:

1. **10 Bots com Personalidades Únicas**
   - Cada bot tem personalidade, estilo de fala e características próprias
   - Respostas geradas por IA (Groq ou DeepSeek)
   - Comportamento natural e imersivo

2. **Sistema de Turnos Automático**
   - Bots aguardam 2-5 segundos antes de responder (parecer humano)
   - Geram respostas baseadas no contexto do jogo
   - Passam o turno automaticamente

3. **Mínimo de Jogadores Reduzido**
   - Antes: 6 jogadores mínimo
   - Agora: **3 jogadores mínimo** (permite jogar sozinho com bots!)

4. **Integração Completa**
   - Backend processa bots automaticamente
   - Frontend tem botões para adicionar bots
   - Identificação visual (badge "BOT")

---

## 🎭 Personalidades dos Bots:

### 1. **Shadow_Hunter** 🔍
- **Tipo:** Detetive analítico
- **Estilo:** Formal e investigativo
- **Características:** Observador, lógico, desconfiado
- **Exemplo:** *"Hmm... preciso investigar isso mais a fundo."*

### 2. **Night_Stalker** 🌙
- **Tipo:** Suspeito misterioso
- **Estilo:** Enigmático e sussurrado
- **Características:** Silencioso, calculista, misterioso
- **Exemplo:** *"..."*

### 3. **Dark_Phoenix** 🔥
- **Tipo:** Testemunha nervosa
- **Estilo:** Nervoso e hesitante
- **Características:** Assustado, sincero, detalhista
- **Exemplo:** *"Eu... eu não sei o que dizer..."*

### 4. **Silent_Reaper** 💀
- **Tipo:** Figura sombria
- **Estilo:** Lacônico e sombrio
- **Características:** Lacônico, ameaçador, enigmático
- **Exemplo:** *"Irrelevante."*

### 5. **Ghost_Whisper** 👻
- **Tipo:** Informante astuto
- **Estilo:** Insinuante e provocativo
- **Características:** Provocador, conhecedor, astuto
- **Exemplo:** *"Ah, isso é interessante..."*

### 6. **Blood_Moon** 🌕
- **Tipo:** Conspirador dramático
- **Estilo:** Dramático e intenso
- **Características:** Emotivo, paranóico, teatral
- **Exemplo:** *"Isso não pode ser coincidência!"*

### 7. **Crimson_Blade** ⚔️
- **Tipo:** Mercenário pragmático
- **Estilo:** Direto e agressivo
- **Características:** Impaciente, pragmático, rude
- **Exemplo:** *"Vamos ao ponto."*

### 8. **Phantom_Eyes** 👁️
- **Tipo:** Observador filosófico
- **Estilo:** Reflexivo e calmo
- **Características:** Filosófico, paciente, sábio
- **Exemplo:** *"Deixe-me refletir sobre isso."*

### 9. **Raven_Soul** 🐦‍⬛
- **Tipo:** Médium espiritual
- **Estilo:** Místico e etéreo
- **Características:** Intuitivo, espiritual, sensível
- **Exemplo:** *"Sinto uma energia estranha aqui..."*

### 10. **Death_Dealer** 💼
- **Tipo:** Ex-criminoso reformado
- **Estilo:** Cínico e experiente
- **Características:** Cínico, experiente, street-smart
- **Exemplo:** *"Já vi isso antes."*

---

## 🎮 Como funciona?

### No Frontend:

1. **Jogador entra no lobby** - Aparece como jogador 1
2. **Clica "Adicionar Bot"** - Adiciona 1 bot por vez
3. **Ou clica "🤖 Completar com Bots"** - Preenche até 10 jogadores
4. **Clica "Iniciar Partida"** - Envia lista de jogadores para o backend

### No Backend:

1. **Recebe lista de jogadores** via WebSocket
2. **Gera o caso/mistério** usando IA
3. **Inicia loop de turnos:**
   - Se for bot: chama `process_bot_turn()`
   - Se for humano: aguarda ação do jogador
4. **Bot responde automaticamente:**
   - Aguarda 2-5 segundos
   - Gera resposta usando IA baseado na personalidade
   - Envia para todos via WebSocket
   - Passa para próximo turno

---

## 🧠 Como o Bot Pensa?

Quando é a vez de um bot, o sistema:

1. **Coleta o contexto:**
   - Descrição do caso
   - Evidências reveladas
   - Histórico do chat (últimas 5 mensagens)

2. **Monta o prompt para IA:**
   ```
   Você é [Nome do Bot], um personagem com [personalidade]
   
   CASO: [descrição]
   EVIDÊNCIAS: [lista]
   CONVERSA: [histórico]
   
   Faça uma observação relevante (2-3 frases):
   ```

3. **IA gera resposta** (Groq ou DeepSeek)

4. **Bot "fala"** no chat

---

## 🔧 Arquitetura Técnica:

### Backend (`main.py`):

```python
# Personalidades definidas
BOT_PERSONALITIES = {
    "Shadow_Hunter": {...},
    "Night_Stalker": {...},
    ...
}

# Gera resposta do bot
async def bot_generate_response(bot_name, context, question=None):
    # 1. Pega personalidade
    # 2. Monta contexto
    # 3. Chama ai_generate()
    # 4. Retorna resposta
    
# Processa turno do bot
async def process_bot_turn(room_id):
    # 1. Aguarda 2-5s
    # 2. Gera resposta
    # 3. Envia via WebSocket
    # 4. Avança turno
    # 5. Se próximo for bot, repete
```

### Frontend (`Lobby.jsx`):

```javascript
// Lista de jogadores (humanos + bots)
const [players, setPlayers] = useState([...]);

// Adiciona 1 bot
const addBot = () => { ... }

// Preenche com bots
const fillWithBots = () => { ... }

// Envia para backend ao iniciar
onClick={() => {
  ws.send({
    type: "start",
    players: players // inclui isBot: true/false
  })
}}
```

---

## 📝 Próximas Melhorias Sugeridas:

1. **Memória de Conversa:**
   - Bots lembram do que foi dito antes
   - Referências a conversas anteriores

2. **Nível de Inteligência:**
   - Bots "Fácil" cometem erros
   - Bots "Difícil" são mais perspicazes

3. **Interação entre Bots:**
   - Bots perguntam uns aos outros
   - Formam alianças ou rivalidades

4. **Comportamento Adaptativo:**
   - Bots aprendem com o jogador
   - Ajustam estratégia baseado no contexto

---

## 🎯 Exemplo de Jogo:

**Turno 1 - Jogador (você):**
> "Alguém viu algo suspeito no corredor?"

**Turno 2 - Shadow_Hunter (bot):**
> *Aguarda 3 segundos...*
> "Interessante... Preciso investigar as pegadas que encontrei. Alguém esteve lá recentemente."

**Turno 3 - Night_Stalker (bot):**
> *Aguarda 4 segundos...*
> "..."

**Turno 4 - Dark_Phoenix (bot):**
> *Aguarda 2 segundos...*
> "Eu... eu vi alguém com uma capa vermelha! Mas não consegui ver o rosto..."

---

## 🚀 Como Testar:

1. **Entre no lobby:** `http://localhost:3000/`
2. **Clique "Completar com Bots"**
3. **Clique "Iniciar Partida"**
4. **Veja os bots jogarem sozinhos!**

---

**Sistema completo e funcional!** 🎉

Os bots criam uma experiência imersiva mesmo jogando sozinho!
