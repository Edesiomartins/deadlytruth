import os
import json
import re
import asyncio
from pathlib import Path
from groq import Groq  # pyright: ignore[reportMissingImports]
from openai import OpenAI  # pyright: ignore[reportMissingImports]
from fastapi import FastAPI, WebSocket, WebSocketDisconnect  # pyright: ignore[reportMissingImports]
from fastapi.middleware.cors import CORSMiddleware  # pyright: ignore[reportMissingImports]
from pydantic import BaseModel  # pyright: ignore[reportMissingImports]
from dotenv import load_dotenv  # pyright: ignore[reportMissingImports]
from prompts import SYSTEM_GAME_MASTER, CREATE_CASE_TEMPLATE, INTERROGATION_TEMPLATE
from auth_routes import router as auth_router
from auth_utils import decode_access_token
from database import init_db

# Carrega variáveis de ambiente do arquivo .env
# Usa o diretório do arquivo atual para encontrar .env
env_path = Path(__file__).parent / ".env"

# No Railway, as variáveis vêm do ambiente do sistema, não do .env
# Carrega primeiro do .env se existir (desenvolvimento local)
if env_path.exists():
    load_dotenv(env_path, override=True)
    print("✅ .env carregado localmente")
    print(f"📁 Caminho do .env: {env_path}")
else:
    print("ℹ️ Arquivo .env não encontrado (normal no Railway)")

# IMPORTANTE: No Railway, as variáveis vêm diretamente do ambiente do sistema
# Não precisa de load_dotenv() para variáveis do Railway
# Mas vamos tentar carregar do ambiente do sistema também
# (útil se houver um .env que não sobrescreve variáveis do sistema)
load_dotenv(override=False)

# Debug: mostra todas as variáveis de ambiente que começam com GROQ
print("🔍 Variáveis de ambiente relacionadas a GROQ:")
groq_vars_found = False
for key, value in os.environ.items():
    if 'GROQ' in key.upper():
        print(f"   {key} = {'*' * min(len(value), 20)} (tamanho: {len(value)})")
        groq_vars_found = True
if not groq_vars_found:
    print("   (nenhuma variável encontrada)")

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    print("❌ ERRO: GROQ_API_KEY não encontrada!")
    print("🔧 SOLUÇÃO:")
    print("   - Se estiver no Railway:")
    print("     1. Vá no serviço do backend → Variables")
    print("     2. Adicione: GROQ_API_KEY (nome exato, maiúsculas)")
    print("     3. Valor: sua chave API do Groq")
    print("     4. Salve e aguarde redeploy automático")
    print("   - Se estiver localmente: Crie/edite fastapi-server/.env com: GROQ_API_KEY=sua-chave")
    print(f"   - Arquivo .env existe? {env_path.exists()}")
    print("   - Variáveis do sistema disponíveis? Verifique acima")
else:
    print(f"✅ GROQ_API_KEY encontrada (tamanho: {len(api_key)} caracteres)")
    print(f"   Primeiros caracteres: {api_key[:10]}...")

app = FastAPI()


@app.on_event("startup")
def on_startup():
    init_db()

# Habilita CORS para que o frontend possa acessar o backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://deadlytruth-frontend-production.up.railway.app",
        "https://deadlytruth-production.up.railway.app",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)

# Clientes AI (inicializados lazy)
_groq_client = None
_deepseek_client = None

# Armazenamento em memória (em produção, usar Redis ou DB)
ROOMS = {}  # {room_id: {"case": {...}, "chat": [...], "nivel": "...", "players": [...], "current_turn": int, "game_active": bool}}
CONNECTIONS = {}  # {room_id: [WebSocket, ...]}
GAME_EVENTS = {}  # {room_id: {"player_action_event": asyncio.Event, "current_player": int}}


# ======== Funções auxiliares ========

def get_groq_client():
    """Obtém ou cria o cliente Groq (lazy initialization)"""
    global _groq_client
    if _groq_client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY não encontrada no .env")
        _groq_client = Groq(api_key=api_key)
    return _groq_client


def get_deepseek_client():
    """Obtém ou cria o cliente DeepSeek (lazy initialization)"""
    global _deepseek_client
    if _deepseek_client is None:
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY não encontrada no .env")
        _deepseek_client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )
    return _deepseek_client


def ai_generate(prompt: str, system: str = None) -> str:
    """
    Gera resposta usando o provedor de IA configurado (Groq ou DeepSeek)
    Provedor é escolhido via variável de ambiente AI_PROVIDER (groq ou deepseek)
    Padrão: groq
    """
    provider = os.getenv("AI_PROVIDER", "groq").lower()
    
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    
    try:
        if provider == "deepseek":
            # Usa DeepSeek-V3 (mais recente e poderoso)
            print(f"🤖 Usando DeepSeek-V3...")
            client = get_deepseek_client()
            completion = client.chat.completions.create(
                model="deepseek-chat",  # Usa o modelo mais recente
                messages=messages,
                temperature=0.8,
                max_tokens=2048
            )
            return completion.choices[0].message.content or ""
        else:
            # Usa Groq (padrão)
            print(f"🤖 Usando Groq (Llama 3.3 70B)...")
            client = get_groq_client()
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=1,
                max_completion_tokens=1024,
                top_p=1,
                stream=False,
                stop=None
            )
            return completion.choices[0].message.content or ""
    except ValueError as e:
        return f"Erro de configuração ({provider}): {str(e)}"
    except Exception as e:
        print(f"❌ Erro ao chamar {provider.upper()} API: {e}")
        return f"Erro ao gerar resposta com {provider}: {str(e)}"


def groq_generate(prompt: str, system: str = None) -> str:
    """DEPRECATED: Use ai_generate() - Mantido por compatibilidade"""
    return ai_generate(prompt, system)


def extract_json_from_string(text, validate_with_pydantic=None):
    """Extrai JSON válido de uma string com blocos markdown ```json...```"""
    try:
        # Procurar por blocos ```json...```
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            json_content = match.group(1).strip()
            parsed = json.loads(json_content)
        else:
            # Tentar json.loads() direto
            parsed = json.loads(text.strip())
        
        # Validar com Pydantic se fornecido
        if validate_with_pydantic:
            try:
                validated = validate_with_pydantic(**parsed)
                return validated.model_dump()
            except Exception as e:
                print(f"⚠️ Validação Pydantic falhou: {e}, usando dados brutos")
                return parsed
        
        return parsed
    except (json.JSONDecodeError, ValueError) as e:
        print(f"⚠️ Erro ao extrair JSON: {e}")
        # Se falhar, retornar estrutura básica
        return {
            "case_id": "ERRO",
            "nivel": "Iniciante",
            "descricao": text[:500],
            "suspeitos": [],
            "evidencias": [],
            "timeline": [],
            "hipoteses_iniciais": []
        }


def parse_interrogation_response(response_text):
    """Extrai e estrutura a resposta de interrogatório com validação Pydantic"""
    try:
        parsed = extract_json_from_string(response_text, validate_with_pydantic=InterrogationResponse)
        
        # Garantir que todos os campos existam
        if isinstance(parsed, dict):
            return {
                "suspeito": parsed.get("suspeito", "Desconhecido"),
                "resposta": parsed.get("resposta", response_text[:500]),
                "sinais_nao_verbais": parsed.get("sinais_nao_verbais", "Não detectados"),
                "inconsistencias": parsed.get("inconsistencias", []),
                "pistas_sugeridas": parsed.get("pistas_sugeridas", [])
            }
        return parsed
    except Exception as e:
        print(f"⚠️ Erro ao processar resposta de interrogatório: {e}")
        return {
            "suspeito": "Desconhecido",
            "resposta": response_text[:500],
            "sinais_nao_verbais": "Não detectados",
            "inconsistencias": [],
            "pistas_sugeridas": []
        }


# ======== Modelos Pydantic ========

class CreateCaseRequest(BaseModel):
    nivel: str = "Iniciante"
    cenario: str = "Mansão"  # Mansão, Praia, Parque, Teatro, Hotel-Cassino


class InterrogationRequest(BaseModel):
    suspeito: str
    pergunta: str


# Modelos para validação de respostas da IA
class PlayerProfile(BaseModel):
    id: int
    nome: str
    ocupacao: str
    segredo: str


class CaseData(BaseModel):
    case_id: str = ""
    nivel: str = "Iniciante"
    cenario: str = "Mansão"
    descricao: str = ""  # Descrição inicial do caso
    historia: str = ""  # História detalhada do crime
    culpado_id: int = 0
    jogadores: list[PlayerProfile] = []
    pistas_iniciais: list[str] = []
    local_corpo: str = ""
    arma_crime: str = ""
    suspeitos: list = []
    evidencias: list = []
    timeline: list = []
    hipoteses_iniciais: list = []


class InterrogationResponse(BaseModel):
    suspeito: str = "Desconhecido"
    resposta: str = ""
    sinais_nao_verbais: str = "Não detectados"
    inconsistencias: list[str] = []
    pistas_sugeridas: list[str] = []


# ======== Endpoints REST ========

@app.get("/")
def root():
    return {"msg": "Servidor Deadly Truth ativo 🦙"}


@app.get("/health")
def health():
    return {"status": "ok", "message": "Servidor rodando"}


@app.get("/debug/env")
def debug_env():
    """Endpoint de debug para verificar variáveis de ambiente"""
    env_path = Path(__file__).parent / ".env"
    api_key = os.getenv("GROQ_API_KEY")
    
    return {
        "env_file_exists": env_path.exists(),
        "env_file_path": str(env_path),
        "groq_api_key_set": bool(api_key),
        "groq_api_key_preview": api_key[:10] + "..." if api_key else None,
        "groq_api_key_length": len(api_key) if api_key else 0
    }


@app.post("/case/new")
async def create_case(req: CreateCaseRequest):
    """Cria um novo caso criminal"""
    import uuid
    room_id = str(uuid.uuid4())[:8]
    
    prompt = CREATE_CASE_TEMPLATE.format(nivel=req.nivel, cenario=req.cenario)
    case_json = groq_generate(prompt, system=SYSTEM_GAME_MASTER)
    
    # Usar a função melhorada para extrair JSON com validação Pydantic
    case = extract_json_from_string(case_json, validate_with_pydantic=CaseData)
    
    # Garantir que o case_id, nivel e cenario estejam corretos
    if case.get("case_id") == "ERRO" or not case.get("case_id"):
        case["case_id"] = room_id
    if not case.get("nivel"):
        case["nivel"] = req.nivel
    if not case.get("cenario"):
        case["cenario"] = req.cenario
    
    # Inicializar estrutura de jogo
    ROOMS[room_id] = {
        "case": case,
        "chat": [],
        "nivel": req.nivel,
        "cenario": req.cenario,
        "players": [],  # Lista de IDs de jogadores conectados (1-12)
        "current_turn": 0,  # Índice do jogador atual
        "game_active": False,  # Será ativado quando houver 12 jogadores
        "turn_start_time": None
    }
    
    # Inicializar eventos de jogo
    GAME_EVENTS[room_id] = {
        "player_action_event": asyncio.Event(),
        "current_player": 0
    }
    
    return {
        "room_id": room_id,
        "case": case
    }


@app.post("/case/{room_id}/ask")
async def ask_interrogation(room_id: str, req: InterrogationRequest):
    """Faz uma pergunta a um suspeito"""
    room = ROOMS.get(room_id)
    if not room:
        return {"error": "room_not_found"}
    
    # Pequeno resumo do caso para manter contexto curto
    case_summary = json.dumps(room.get("case", {}))[:2000]
    
    prompt = INTERROGATION_TEMPLATE.format(
        case_summary=case_summary,
        suspeito=req.suspeito,
        pergunta=req.pergunta,
        nivel=room.get("nivel", "Iniciante")
    )
    
    answer = groq_generate(prompt, system=SYSTEM_GAME_MASTER)
    
    # Estrutura a resposta corretamente
    structured_answer = parse_interrogation_response(answer)
    
    # Guarda no histórico
    entry = {
        "suspeito": req.suspeito,
        "pergunta": req.pergunta,
        "resposta": structured_answer.get("resposta", answer),
        "sinais_nao_verbais": structured_answer.get("sinais_nao_verbais", ""),
        "inconsistencias": structured_answer.get("inconsistencias", []),
        "pistas_sugeridas": structured_answer.get("pistas_sugeridas", [])
    }
    room["chat"].append(entry)
    
    # Broadcast via WebSocket para a sala
    for ws in CONNECTIONS.get(room_id, []):
        try:
            ws_data = {
                "type": "interrogation",
                "payload": entry
            }
            await ws.send_text(json.dumps(ws_data))
        except Exception as e:
            print(f"Failed to send to WebSocket: {e}")
    
    return entry


# ======== WebSockets (multiplayer por sala) ========

async def broadcast(room_id: str, message: dict):
    """Envia mensagem para todos os WebSockets conectados na sala"""
    for ws in CONNECTIONS.get(room_id, []):
        try:
            await ws.send_text(json.dumps(message))
        except Exception as e:
            print(f"Failed to send to WebSocket: {e}")


async def game_loop(room_id: str):
    room = ROOMS.get(room_id)
    if not room: return
    
    participantes = room.get("players", [])
    num_jogadores = len(participantes)
    room["game_active"] = True
    
    await broadcast(room_id, {"type": "status", "msg": "O Mestre está tecendo a história..."})
    
    # Gerar o caso
    prompt_dinamico = CREATE_CASE_TEMPLATE.format(
        cenario=room.get("cenario", "Hotel-Cassino"),
        nivel=room.get("nivel", "Iniciante"),
        num_jogadores=num_jogadores
    )
    
    case_json = groq_generate(prompt_dinamico, system=SYSTEM_GAME_MASTER)
    case_data = extract_json_from_string(case_json, validate_with_pydantic=CaseData)
    
    # SALVAR NA SALA (Importante para quem entrar depois)
    room["case"] = case_data 

    # Enviar para todos com o campo 'content' e 'case' padronizados
    await broadcast(room_id, {
        "type": "game_start",
        "payload": {
            "msg": "O mistério começou!",
            "case": case_data  # O React vai ler isso aqui
        }
    })

    # 2. Inicia a sequência de turnos
    while room.get("game_active", False):
        for idx, player_id in enumerate(participantes):
            room["current_turn"] = idx
            
            await broadcast(room_id, {
                "type": "turn_start",
                "player": player_id,
                "time_limit": 120
            })
            
            if room_id in GAME_EVENTS:
                GAME_EVENTS[room_id]["player_action_event"].clear()
                try:
                    await asyncio.wait_for(
                        GAME_EVENTS[room_id]["player_action_event"].wait(),
                        timeout=120.0
                    )
                except asyncio.TimeoutError:
                    await broadcast(room_id, {"type": "time_out", "player": player_id})

    room["game_active"] = False


@app.websocket("/ws/{room_id}")
async def ws_room(websocket: WebSocket, room_id: str):
    token = websocket.query_params.get("token")
    user_email = None
    if token:
        payload = decode_access_token(token)
        if payload:
            user_email = payload.get("sub")

    require_auth_ws = os.getenv("REQUIRE_AUTH_WS", "false").lower() == "true"
    if require_auth_ws and not user_email:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    
    if room_id not in CONNECTIONS:
        CONNECTIONS[room_id] = []
    CONNECTIONS[room_id].append(websocket)
    
    # Inicializa estrutura de jogo se necessário
    if room_id not in ROOMS:
        ROOMS[room_id] = {
            "case": {},
            "chat": [],
            "nivel": "Iniciante",
            "cenario": "Hotel-Cassino",
            "players": [],
            "current_turn": 0,
            "game_active": False,
            "turn_start_time": None
        }
    
    # Adiciona jogador à lista (limite de 12 jogadores)
    room = ROOMS[room_id]
    player_id = len(room.get("players", [])) + 1
    if player_id not in room.get("players", []) and player_id <= 12:
        room["players"].append(player_id)
    
    # Inicializa eventos de jogo se necessário
    if room_id not in GAME_EVENTS:
        GAME_EVENTS[room_id] = {
            "player_action_event": asyncio.Event(),
            "current_player": 0
        }
    
    # O jogo pode começar se tiver entre 6 e 12
    num_atual = len(room.get("players", []))
    
    # O jogo pode começar se tiver entre 6 e 12
    if not room.get("game_active") and 6 <= num_atual <= 12:
        # Opcional: Você pode disparar o início automaticamente ao chegar em 12
        # ou criar um comando "start" que o primeiro jogador envia
        if num_atual == 12: 
            asyncio.create_task(game_loop(room_id))
    
    # NOVIDADE: Se o jogo já estiver rolando, envia os dados atuais para o novo player
    if room.get("game_active") and room.get("case"):
        await websocket.send_text(json.dumps({
            "type": "game_start",
            "payload": {
                "msg": "Você chegou tarde à cena do crime, mas a investigação continua!",
                "case": room["case"],
                "total_players": len(room.get("players", [])),
                "player_id": player_id,
                "game_active": True
            }
        }))
    
    # Envia estado inicial
    await websocket.send_text(json.dumps({
        "type": "hello",
        "payload": {
            "room_id": room_id,
            "player_id": player_id,
            "players": len(CONNECTIONS[room_id]),
            "total_players": len(room.get("players", [])),
            "case": room.get("case"),
            "current_turn": room.get("current_turn", 0),
            "game_active": room.get("game_active", False)
        }
    }))
    
    try:
        while True:
            msg = await websocket.receive_text()
            try:
                data = json.loads(msg)
                msg_type = data.get("type")
                
                if msg_type == "start":
                    # Lógica de início manual
                    num_atual = len(room.get("players", []))
                    if num_atual >= 3:  # Mudado de 6 para 3
                        asyncio.create_task(game_loop(room_id))
                    else:
                        await websocket.send_text(json.dumps({
                            "type": "error", 
                            "msg": f"Mínimo de 3 jogadores necessário. Atual: {num_atual}"
                        }))
                
                elif msg_type == "action":
                    if room_id in GAME_EVENTS:
                        GAME_EVENTS[room_id]["player_action_event"].set()
                    
                    # Envia como um chat normal para aparecer na lista
                    sender_label = user_email or f"Suspeito {player_id}"
                    await broadcast(room_id, {
                        "type": "chat",
                        "player_id": sender_label,
                        "content": data.get("content", "Realizou uma ação")
                    })
            except Exception as e:
                # Se for texto puro, encapsula no padrão
                sender_label = user_email or f"Suspeito {player_id}"
                await broadcast(room_id, {
                    "type": "chat",
                    "player_id": sender_label,
                    "content": msg
                })
    except WebSocketDisconnect:
        CONNECTIONS[room_id].remove(websocket)
        # Remove jogador da lista
        if player_id in room.get("players", []):
            room["players"].remove(player_id)
        if not CONNECTIONS[room_id]:  # Remove sala vazia
            del CONNECTIONS[room_id]
            if room_id in GAME_EVENTS:
                del GAME_EVENTS[room_id]
            room["game_active"] = False


if __name__ == "__main__":
    import uvicorn  # pyright: ignore[reportMissingImports]
    # Railway fornece a porta via variável de ambiente PORT
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
