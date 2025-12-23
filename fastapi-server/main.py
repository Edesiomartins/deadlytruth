import os
import json
import re
import asyncio
from pathlib import Path
from groq import Groq  # pyright: ignore[reportMissingImports]
from fastapi import FastAPI, WebSocket, WebSocketDisconnect  # pyright: ignore[reportMissingImports]
from fastapi.middleware.cors import CORSMiddleware  # pyright: ignore[reportMissingImports]
from pydantic import BaseModel  # pyright: ignore[reportMissingImports]
from dotenv import load_dotenv  # pyright: ignore[reportMissingImports]
from prompts import SYSTEM_GAME_MASTER, CREATE_CASE_TEMPLATE, INTERROGATION_TEMPLATE

# Carrega variáveis de ambiente do arquivo .env
# Usa o diretório do arquivo atual para encontrar .env
env_path = Path(__file__).parent / ".env"

# Debug: verifica se o arquivo existe
if env_path.exists():
    print(f"✅ Arquivo .env encontrado em: {env_path}")
    # Tenta ler o conteúdo para debug (primeiras linhas)
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            print(f"   Primeira linha do arquivo: {first_line[:50]}...")
    except Exception as e:
        print(f"   ⚠️ Erro ao ler arquivo: {e}")
else:
    print(f"⚠️ Arquivo .env NÃO encontrado em: {env_path}")

# Carrega as variáveis de ambiente
load_dotenv(env_path, override=True)

# Debug: verifica se a chave foi carregada
api_key = os.getenv("GROQ_API_KEY")
if api_key:
    print(f"✅ GROQ_API_KEY carregada com sucesso (primeiros 10 caracteres: {api_key[:10]}...)")
else:
    print(f"⚠️ GROQ_API_KEY não encontrada após carregar .env")
    print(f"   Verifique se o arquivo contém: GROQ_API_KEY=sua-chave-aqui")

app = FastAPI()

# Habilita CORS para que o frontend (Vercel) possa acessar o backend (Render)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, substitua pelo link do seu Vercel
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cliente Groq (inicializado lazy)
_client = None

# Armazenamento em memória (em produção, usar Redis ou DB)
ROOMS = {}  # {room_id: {"case": {...}, "chat": [...], "nivel": "...", "players": [...], "current_turn": int, "game_active": bool}}
CONNECTIONS = {}  # {room_id: [WebSocket, ...]}
GAME_EVENTS = {}  # {room_id: {"player_action_event": asyncio.Event, "current_player": int}}


# ======== Funções auxiliares ========

def get_groq_client():
    """Obtém ou cria o cliente Groq (lazy initialization)"""
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            # Verifica se o arquivo .env existe
            env_file = Path(__file__).parent / ".env"
            if env_file.exists():
                raise ValueError(
                    f"GROQ_API_KEY não encontrada no arquivo .env (arquivo existe em: {env_file}). "
                    "Verifique se a chave está definida corretamente no formato: GROQ_API_KEY=sua-chave-aqui"
                )
            else:
                raise ValueError(
                    f"Arquivo .env não encontrado em: {env_file}. "
                    "Crie o arquivo .env na pasta fastapi-server com: GROQ_API_KEY=sua-chave-aqui"
                )
        _client = Groq(api_key=api_key)
    return _client


def groq_generate(prompt: str, system: str = None) -> str:
    """Gera resposta usando Groq com llama-3.3-70b-versatile"""
    messages = []
    
    # Adiciona mensagem do sistema se fornecida
    if system:
        messages.append({
            "role": "system",
            "content": system
        })
    
    # Adiciona mensagem do usuário
    messages.append({
        "role": "user",
        "content": prompt
    })
    
    try:
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
        return f"Erro de configuração: {str(e)}"
    except Exception as e:
        return f"Erro ao gerar resposta: {str(e)}"


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
    """Loop principal do jogo com sistema de turnos de 2 minutos"""
    room = ROOMS.get(room_id)
    if not room:
        return
    
    room["game_active"] = True
    
    while room.get("game_active", False):
        players = room.get("players", [])
        if len(players) < 12:
            # Espera até ter 12 jogadores
            await asyncio.sleep(1)
            continue
        
        current_idx = room.get("current_turn", 0)
        current_player = players[current_idx] if current_idx < len(players) else players[0]
        
        # Notifica todos quem é a vez
        room["turn_start_time"] = asyncio.get_event_loop().time()
        await broadcast(room_id, {
            "type": "turn_start",
            "player": current_player,
            "time_limit": 120  # 2 minutos
        })
        
        # Reseta o evento de ação do jogador
        if room_id in GAME_EVENTS:
            GAME_EVENTS[room_id]["player_action_event"].clear()
        
        # Espera 2 minutos ou até o jogador agir
        try:
            if room_id in GAME_EVENTS:
                await asyncio.wait_for(
                    GAME_EVENTS[room_id]["player_action_event"].wait(),
                    timeout=120.0
                )
                # Jogador agiu antes do timeout
                await broadcast(room_id, {
                    "type": "player_action",
                    "player": current_player
                })
            else:
                await asyncio.sleep(120)
        except asyncio.TimeoutError:
            # Timeout - passa para o próximo jogador
            await broadcast(room_id, {
                "type": "time_out",
                "player": current_player,
                "next_player": True
            })
        
        # Avança para o próximo jogador
        room["current_turn"] = (current_idx + 1) % 12
        await asyncio.sleep(1)  # Pequena pausa entre turnos


@app.websocket("/ws/{room_id}")
async def ws_room(websocket: WebSocket, room_id: str):
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
            "players": [],
            "current_turn": 0,
            "game_active": False,
            "turn_start_time": None
        }
    
    # Adiciona jogador à lista (se ainda não tiver 12)
    room = ROOMS[room_id]
    player_id = len(room.get("players", [])) + 1
    if player_id <= 12 and player_id not in room.get("players", []):
        room["players"].append(player_id)
    
    # Inicializa eventos de jogo se necessário
    if room_id not in GAME_EVENTS:
        GAME_EVENTS[room_id] = {
            "player_action_event": asyncio.Event(),
            "current_player": 0
        }
    
    # Inicia o loop de jogo em background se ainda não estiver rodando
    if not room.get("game_active", False) and len(room.get("players", [])) == 12:
        asyncio.create_task(game_loop(room_id))
    
    # Envia estado inicial
    await websocket.send_text(json.dumps({
        "type": "hello",
        "payload": {
            "room_id": room_id,
            "player_id": player_id,
            "players": len(CONNECTIONS[room_id]),
            "total_players": len(room.get("players", [])),
            "case": room.get("case"),
            "current_turn": room.get("current_turn", 0)
        }
    }))
    
    try:
        while True:
            msg = await websocket.receive_text()
            try:
                data = json.loads(msg)
                msg_type = data.get("type", "chat")
                
                if msg_type == "action" and room_id in GAME_EVENTS:
                    # Jogador realizou uma ação - sinaliza o evento
                    GAME_EVENTS[room_id]["player_action_event"].set()
                    await broadcast(room_id, {
                        "type": "chat",
                        "payload": f"Jogador {player_id} realizou uma ação"
                    })
                else:
                    # Chat colaborativo normal
                    await broadcast(room_id, {
                        "type": "chat",
                        "payload": msg,
                        "player_id": player_id
                    })
            except json.JSONDecodeError:
                # Mensagem de texto simples
                await broadcast(room_id, {
                    "type": "chat",
                    "payload": msg,
                    "player_id": player_id
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
    uvicorn.run(app, host="0.0.0.0", port=8000)
