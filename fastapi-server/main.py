import os
import json
import re
import asyncio
import logging
import random
import time
from pathlib import Path
from datetime import datetime
import httpx  # pyright: ignore[reportMissingImports]
from openai import OpenAI  # pyright: ignore[reportMissingImports]
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Response, status  # pyright: ignore[reportMissingImports]
from fastapi.responses import JSONResponse  # pyright: ignore[reportMissingImports]
from fastapi.exceptions import RequestValidationError  # pyright: ignore[reportMissingImports]
from fastapi import HTTPException as FastAPIHTTPException  # pyright: ignore[reportMissingImports]
from starlette.exceptions import HTTPException as StarletteHTTPException  # pyright: ignore[reportMissingImports]
from fastapi.middleware.cors import CORSMiddleware  # pyright: ignore[reportMissingImports]
from pydantic import BaseModel  # pyright: ignore[reportMissingImports]
from dotenv import load_dotenv  # pyright: ignore[reportMissingImports]

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
from prompts import SYSTEM_GAME_MASTER, CREATE_CASE_TEMPLATE, INTERROGATION_TEMPLATE
from auth_routes import router as auth_router
from auth_utils import decode_access_token
from database import init_db
from game_state import (
    set_case_summary,
    add_clue,
    add_chat_message,
    get_case_summary,
    get_clues,
    get_chat_history,
    get_all_clues_list,
    clear_room_state,
    set_current_turn,
    get_current_turn,
    set_killer_id,
    get_killer_id,
    register_player,
    is_alive,
    kill_player_state,
    get_player_status,
    start_vote,
    submit_vote,
    get_vote_result,
    get_accused_player,
    all_votes_in,
    clear_vote,
    start_interrogation,
    get_interrogated_player,
    clear_interrogation
)

# Persistence layer
from persistence_layer import (
    flush_room_to_db,
    flush_clue_to_db,
    flush_chat_to_db,
    flush_killer_to_db,
    flush_turn_to_db,
    flush_game_end_to_db,
    load_active_rooms,
    get_room_state_snapshot,
)

# Bot memory system
from bot_memory import (
    init_bot_memory,
    add_clue_to_bot,
    update_suspicion_score,
    record_bot_statement,
    select_bot_vote,
    select_bot_kill_target,
    should_bot_respond,
    clear_room_memories,
)

# Rate limiting
from rate_limiter import check_rate_limit, clear_room_limits
from openrouter_client import (
    OPENROUTER_DEFAULT_FALLBACK_MODEL,
    OPENROUTER_DEFAULT_PRIMARY_MODEL,
    call_openrouter,
)

# Turn lock security
_turn_locks: dict[str, dict] = {}  # {room_id: {"player_id": "...", "locked_at": float, "action_taken": bool}}

def is_openrouter_configured() -> bool:
    return bool(os.getenv("OPENROUTER_API_KEY"))


def get_active_ai_provider() -> str:
    return "openrouter"

async def generate_case(prompt_template: str = None):
    """
    Gera um caso de assassinato usando OpenRouter.
    Usa os prompts SYSTEM_GAME_MASTER e CREATE_CASE_TEMPLATE.
    """
    try:
        # Logging detalhado
        logger.info(f"🔄 Iniciando geração de caso...")
        
        # Usa o prompt fornecido ou o template padrão
        user_prompt = prompt_template or CREATE_CASE_TEMPLATE
        
        logger.info(f"🔄 Gerando caso com OpenRouter...")
        result = await call_openrouter(
            [
                {"role": "system", "content": SYSTEM_GAME_MASTER},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.8,
            max_tokens=2000,
            timeout=float(os.getenv("AI_TIMEOUT_SECONDS", "10")),
        )
        if not result:
            return generate_fallback_case()
        logger.info(f"✅ Caso gerado com sucesso: {len(result)} chars")
        
        # ✅ Limpa JSON se necessário (remove markdown backticks)
        result_clean = clean_json_response(result)
        logger.info(f"✅ JSON limpo: {len(result_clean)} chars")
        
        return result_clean
        
    except asyncio.TimeoutError:
        logger.error(f"⏱️ Timeout na API OpenRouter")
        return generate_fallback_case()
    except Exception as e:
        logger.error(f"❌ Erro ao gerar caso: {str(e)}", exc_info=True)
        return generate_fallback_case()


def generate_fallback_case():
    """Gera um caso básico local quando a IA não responde."""
    return json.dumps({
        "case_id": "FALLBACK",
        "descricao": "Um mistério foi revelado... Um assassinato ocorreu e você precisa descobrir o culpado.",
        "historia": "A investigação está em andamento. Reúna pistas e descubra a verdade.",
        "local_corpo": "Local desconhecido",
        "arma_crime": "Desconhecida",
        "suspeitos": [],
        "evidencias": []
    })

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

openrouter_primary_model = os.getenv("OPENROUTER_PRIMARY_MODEL", OPENROUTER_DEFAULT_PRIMARY_MODEL)
openrouter_fallback_model = os.getenv("OPENROUTER_FALLBACK_MODEL", OPENROUTER_DEFAULT_FALLBACK_MODEL)
active_ai_provider = "OpenRouter" if get_active_ai_provider() == "openrouter" else get_active_ai_provider().title()
logger.info(f"[AI_CONFIG] OpenRouter configurado: {'sim' if is_openrouter_configured() else 'não'}")
logger.info(f"[AI_CONFIG] Modelo principal: {openrouter_primary_model}")
logger.info(f"[AI_CONFIG] Modelo fallback: {openrouter_fallback_model}")
logger.info(f"[AI_CONFIG] Provedor principal ativo: {active_ai_provider}")

app = FastAPI()


@app.on_event("startup")
def on_startup():
    init_db()
    # Recupera salas ativas do banco pós-reboot
    try:
        recovered = load_active_rooms()
        ROOMS.update(recovered)
        for rid, rdata in recovered.items():
            ROOMS[rid] = {**ROOMS.get(rid, {}), **rdata}
        if recovered:
            logger.info(f"🔄 {len(recovered)} salas recuperadas do banco de dados")
    except Exception as e:
        logger.warning(f"⚠️ Não foi possível recuperar salas do banco: {e}")

# Habilita CORS para que o frontend possa acessar o backend
# Permite origens dinâmicas via variável de ambiente ou lista fixa
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "")
if allowed_origins_env:
    allowed_origins = [origin.strip() for origin in allowed_origins_env.split(",")]
    print(f"🌐 CORS: Usando origens da variável ALLOWED_ORIGINS: {allowed_origins}")
else:
    allowed_origins = [
        "https://deadlytruth-frontend-production.up.railway.app",
        "https://deadlytruth-production.up.railway.app",
        "http://localhost:5173",
        "http://localhost:3000",
    ]
    print(f"🌐 CORS: Usando origens padrão: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=3600,  # Cache preflight por 1 hora
)

# NOTA DE SEGURANÇA: o middleware CORS manual e os exception handlers que
# refletiam QUALQUER origem (Access-Control-Allow-Origin: <origin> com
# credentials=true) foram removidos. Isso anulava a proteção CORS por completo.
# O CORSMiddleware acima já adiciona os headers corretos em TODAS as respostas,
# incluindo erros (4xx/5xx) e respostas dos exception handlers.


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handler para erros gerais (500).

    NOTA: este handler roda FORA do CORSMiddleware (ServerErrorMiddleware é o
    mais externo), então adicionamos headers CORS manualmente — mas APENAS
    para origens da whitelist, nunca refletindo origem arbitrária.
    """
    import traceback
    logger.error(f"❌ Erro não tratado: {exc}")
    logger.error(traceback.format_exc())
    response = JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Erro interno do servidor"},
    )
    origin = request.headers.get("origin")
    if origin and origin in allowed_origins:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
    return response

app.include_router(auth_router)

# Clientes AI (inicializados lazy)
_openrouter_client = None

# Armazenamento em memória (em produção, usar Redis ou DB)
ROOMS = {}  # {room_id: {"case": {...}, "chat": [...], "nivel": "...", "players": [...], "current_turn": int, "game_active": bool}}
CONNECTIONS = {}  # {room_id: [WebSocket, ...]}
GAME_EVENTS = {}  # {room_id: {"player_action_event": asyncio.Event, "current_player": int}}
CONNECTION_PLAYERS = {}  # {room_id: {id(websocket): {"id": str, "name": str}}}

VALID_PHASES = {
    "lobby",
    "intro",
    "investigation",
    "turn",
    "interrogation",
    "defense",
    "voting",
    "resolution",
    "ended",
}


# ======== Funções auxiliares ========


def get_openrouter_client():
    """Obtém ou cria o cliente OpenRouter (lazy initialization)"""
    global _openrouter_client
    if _openrouter_client is None:
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY não encontrada no .env")
        _openrouter_client = OpenAI(
            api_key=api_key,
            base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        )
    return _openrouter_client


def ai_generate(prompt: str, system: str = None) -> str:
    """
    Gera resposta usando OpenRouter.
    Para OpenRouter, use OPENROUTER_PRIMARY_MODEL (padrão: qwen/qwen3-next-80b-a3b-instruct:free)
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    
    try:
        model = os.getenv("OPENROUTER_PRIMARY_MODEL", OPENROUTER_DEFAULT_PRIMARY_MODEL)
        print(f"🤖 Usando OpenRouter (modelo: {model})...")
        client = get_openrouter_client()
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.8,
            max_tokens=2000
        )
        return completion.choices[0].message.content or ""
    except ValueError as e:
        return f"Erro de configuração (openrouter): {str(e)}"
    except Exception as e:
        print(f"❌ Erro ao chamar OPENROUTER API: {e}")
        return f"Erro ao gerar resposta com openrouter: {str(e)}"


# ======== Sistema de Bots ========

BOT_PERSONALITIES = {
    "Shadow_Hunter": {
        "personality": "Detetive experiente, analítico e direto. Faz perguntas incisivas e observa cada detalhe.",
        "style": "formal e investigativo",
        "traits": ["observador", "lógico", "desconfiado"]
    },
    "Night_Stalker": {
        "personality": "Misterioso e reservado. Fala pouco mas quando fala é profundo. Suspeito em potencial.",
        "style": "enigmático e sussurrado",
        "traits": ["silencioso", "calculista", "misterioso"]
    },
    "Dark_Phoenix": {
        "personality": "Testemunha nervosa que viu algo importante. Hesitante mas honesta.",
        "style": "nervoso e hesitante",
        "traits": ["assustado", "sincero", "detalhista"]
    },
    "Silent_Reaper": {
        "personality": "Figura sombria com passado duvidoso. Respostas curtas e ambíguas.",
        "style": "lacônico e sombrio",
        "traits": ["lacônico", "ameaçador", "enigmático"]
    },
    "Ghost_Whisper": {
        "personality": "Informante que conhece os segredos de todos. Gosta de insinuações.",
        "style": "insinuante e provocativo",
        "traits": ["provocador", "conhecedor", "astuto"]
    },
    "Blood_Moon": {
        "personality": "Intenso e dramático. Vê conspiração em tudo. Extremamente emocional.",
        "style": "dramático e intenso",
        "traits": ["emotivo", "paranóico", "teatral"]
    },
    "Crimson_Blade": {
        "personality": "Mercenário pragmático. Vai direto ao ponto. Não tem paciência para rodeios.",
        "style": "direto e agressivo",
        "traits": ["impaciente", "pragmático", "rude"]
    },
    "Phantom_Eyes": {
        "personality": "Observador silencioso que nota tudo. Calmo e filosófico.",
        "style": "reflexivo e calmo",
        "traits": ["filosófico", "paciente", "sábio"]
    },
    "Raven_Soul": {
        "personality": "Médium espiritual que sente energias. Místico e intuitivo.",
        "style": "místico e etéreo",
        "traits": ["intuitivo", "espiritual", "sensível"]
    },
    "Death_Dealer": {
        "personality": "Ex-criminoso reformado. Conhece o submundo. Cínico mas útil.",
        "style": "cínico e experiente",
        "traits": ["cínico", "experiente", "street-smart"]
    }
}

BOT_PERSONAS = {
    "Shadow_Hunter": {
        "style": "frio, observador, desconfiado",
        "tone": "responde de forma curta, calculada e misteriosa",
        "behavior": "evita se comprometer, mas solta pistas sutis"
    },
    "Night_Stalker": {
        "style": "irônico, provocador e escorregadio",
        "tone": "usa respostas ambíguas e tenta inverter suspeitas",
        "behavior": "questiona os outros jogadores e raramente responde direto"
    },
    "Dark_Phoenix": {
        "style": "emocional, intenso e impulsivo",
        "tone": "fala com urgência e acusa com facilidade",
        "behavior": "reage mal quando é pressionado"
    }
}

DEFAULT_BOT_PERSONA = {
    "style": "cauteloso, desconfiado e atento",
    "tone": "responde com naturalidade e tensão controlada",
    "behavior": "observa contradições e tenta sobreviver sem se expor demais",
}

LOCAL_BOT_FALLBACKS = {
    "defensive": [
        "Não vou aceitar essa acusação sem uma prova concreta.",
        "Você está olhando para a pessoa errada. Pense melhor no que foi dito antes.",
        "Eu respondo, mas não vou servir de distração para o verdadeiro culpado."
    ],
    "suspicious": [
        "Tem algo estranho nessa história. Alguém aqui está omitindo uma parte importante.",
        "Eu reparei numa contradição, mas ainda quero ver quem vai se entregar primeiro.",
        "Essa pergunta parece conveniente demais para ser inocente."
    ],
    "afraid": [
        "Eu não gostei do rumo dessa conversa. Tem alguém tentando manipular todos nós.",
        "Se continuarmos errando, o assassino vai ganhar tempo.",
        "Eu vi algo, mas não sei se devo falar agora."
    ],
    "analytical": [
        "Vamos separar emoção de evidência. A linha do tempo ainda não fecha.",
        "Essa versão tem uma falha: ninguém confirmou esse horário.",
        "Antes de acusar, precisamos comparar quem estava sozinho no momento crítico."
    ],
    "evasive": [
        "Não tenho certeza se essa é a pergunta certa agora.",
        "Prefiro não responder tudo de uma vez. Algumas coisas ainda não fazem sentido.",
        "Você quer uma resposta simples para uma situação que não é simples."
    ]
}

BOT_AI_MEMORY: dict[str, dict[str, dict]] = {}


def clean_json_response(response_text: str) -> str:
    """Remove markdown backticks e limpa JSON"""
    # Remove ```json no início
    response_text = re.sub(r'^```json\s*', '', response_text, flags=re.MULTILINE)
    # Remove ``` no início
    response_text = re.sub(r'^```\s*', '', response_text, flags=re.MULTILINE)
    # Remove ```json no final
    response_text = re.sub(r'\s*```json$', '', response_text, flags=re.MULTILINE)
    # Remove ``` no final
    response_text = re.sub(r'\s*```$', '', response_text, flags=re.MULTILINE)
    return response_text.strip()


def _bot_id(bot) -> str:
    if isinstance(bot, dict):
        return str(bot.get("id") or bot.get("name") or "bot")
    return str(bot)


def _bot_name(bot) -> str:
    if isinstance(bot, dict):
        return str(bot.get("name") or bot.get("id") or "Bot")
    return str(bot)


def _get_bot_persona(bot_name: str) -> dict:
    return BOT_PERSONAS.get(bot_name, DEFAULT_BOT_PERSONA)


def _get_bot_ai_memory(room_id: str, bot_name: str) -> dict:
    room_memory = BOT_AI_MEMORY.setdefault(room_id, {})
    return room_memory.setdefault(bot_name, {
        "last_replies": [],
        "suspicions": {},
        "known_clues": [],
        "contradictions": [],
    })


def _remember_bot_reply(room_id: str, bot_name: str, reply: str):
    memory = _get_bot_ai_memory(room_id, bot_name)
    memory["last_replies"].append(reply)
    memory["last_replies"] = memory["last_replies"][-6:]


def _build_bot_context(room: dict, extra_context: dict | None = None) -> dict:
    room_id = room.get("room_id", "")
    case_data = room.get("case", {}) or {}
    context = {
        "case_description": case_data.get("descricao", ""),
        "case_history": case_data.get("historia", ""),
        "case_location": case_data.get("local_corpo", ""),
        "case_weapon": case_data.get("arma_crime", ""),
        "chat_history": room.get("chat", []),
        "evidences": get_all_clues_list(room_id) if room_id else case_data.get("evidencias", []),
        "suspects": case_data.get("suspeitos", []),
        "phase": room.get("phase", "turn"),
        "active_accusation": room.get("active_accusation"),
    }
    if extra_context:
        context.update(extra_context)
    return context


def _select_local_fallback(bot_name: str, context: dict, memory: dict, is_killer: bool = False, accused: bool = False) -> str:
    phase = context.get("phase", "turn")
    if accused or phase == "defense":
        categories = ["defensive", "evasive", "suspicious"]
    elif bot_name == "Shadow_Hunter":
        categories = ["analytical", "suspicious", "evasive"]
    elif bot_name == "Night_Stalker":
        categories = ["evasive", "suspicious", "defensive"]
    elif bot_name == "Dark_Phoenix":
        categories = ["afraid", "defensive", "suspicious"]
    elif is_killer:
        categories = ["evasive", "defensive", "suspicious"]
    else:
        categories = ["analytical", "suspicious", "afraid", "evasive"]

    last_replies = set(memory.get("last_replies", []))
    candidates = []
    for category in categories:
        candidates.extend(LOCAL_BOT_FALLBACKS.get(category, []))
    available = [reply for reply in candidates if reply not in last_replies] or candidates
    reply = random.choice(available)
    _remember_bot_reply(context.get("room_id", ""), bot_name, reply)
    return reply


def _clean_bot_reply(reply: str, last_replies: list[str]) -> str:
    cleaned = clean_json_response(reply or "")
    cleaned = re.sub(r"^(Resposta|Bot|Suspeito)\s*:\s*", "", cleaned, flags=re.IGNORECASE).strip()
    if cleaned in last_replies:
        cleaned = f"{cleaned} Há um detalhe nessa linha do tempo que ainda me incomoda."
    return cleaned[:900]


async def _generate_bot_text(bot, room, question=None, context=None, purpose="reply", accusation=None):
    room_id = room.get("room_id", "")
    bot_name = _bot_name(bot)
    persona = _get_bot_persona(bot_name)
    bot_is_killer = bool(bot.get("is_killer")) if isinstance(bot, dict) else False
    memory = _get_bot_ai_memory(room_id, bot_name)
    merged_context = _build_bot_context(room, context)
    merged_context["room_id"] = room_id
    chat_history = merged_context.get("chat_history", [])[-8:]
    recent_chat = "\n".join(f"{m.get('player', '?')}: {m.get('text', '')}" for m in chat_history) or "Sem debate recente."
    evidences = merged_context.get("evidences", [])[-8:]
    evidence_text = "\n".join(f"- {item}" for item in evidences) or "Nenhuma pista concreta revelada."
    last_replies = memory.get("last_replies", [])
    accusation_text = json.dumps(accusation or merged_context.get("active_accusation") or {}, ensure_ascii=False)

    system_prompt = f"""Você interpreta {bot_name}, um jogador de investigação criminal em Deadly Truth.
Estilo: {persona['style']}.
Tom: {persona['tone']}.
Comportamento: {persona['behavior']}.
Regras obrigatórias:
- responda em português brasileiro;
- use no máximo 2 a 4 frases;
- nunca repita a última frase nem frases genéricas;
- mantenha a personalidade do bot;
- inclua pista, contradição, suspeita ou reação emocional quando fizer sentido;
- não revele diretamente se você é o assassino;
- se você for assassino, defenda-se e manipule suspeitas sutilmente;
- se for inocente, colabore, mas pode desconfiar, errar ou se contradizer."""

    user_prompt = f"""Fase do jogo: {merged_context.get('phase')}.
Você é assassino? {"sim" if bot_is_killer else "não"}.
Finalidade da fala: {purpose}.
Pergunta/situação: {question or "fale no seu turno sem ser genérico"}.
Acusação ativa: {accusation_text}.
Pistas conhecidas:
{evidence_text}
Debate recente:
{recent_chat}
Últimas respostas suas que NÃO podem ser repetidas:
{json.dumps(last_replies[-4:], ensure_ascii=False)}

Responda apenas com a fala final de {bot_name}."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    text = await call_openrouter(messages, temperature=0.85, max_tokens=220, timeout=float(os.getenv("AI_TIMEOUT_SECONDS", "10")))
    meta = getattr(call_openrouter, "last_result", {}) or {}
    if text:
        reply = _clean_bot_reply(text, last_replies)
        _remember_bot_reply(room_id, bot_name, reply)
        logger.info(f"[BOT_REPLY] bot={bot_name} source={meta.get('source')} model={meta.get('model')}")
        return reply, meta

    fallback_reply = _select_local_fallback(
        bot_name,
        merged_context,
        memory,
        is_killer=bot_is_killer,
        accused=purpose == "defense",
    )
    meta = getattr(call_openrouter, "last_result", {}) or {"source": "local_fallback", "model": None}
    logger.info(f"[BOT_REPLY] bot={bot_name} source=local_fallback reason={meta.get('error') or 'openrouter_failed'}")
    return fallback_reply, {"source": "local_fallback", "model": None, "reason": meta.get("error")}


async def generate_bot_reply(bot, room, question=None, context=None):
    reply, _meta = await _generate_bot_text(bot, room, question=question, context=context, purpose="reply")
    return reply


async def generate_bot_defense(bot, accusation, room):
    reply, _meta = await _generate_bot_text(
        bot,
        room,
        question="Você foi acusado de ser o assassino. Apresente uma defesa curta, tensa e coerente.",
        context={"phase": "defense"},
        purpose="defense",
        accusation=accusation,
    )
    return reply


async def generate_bot_vote(bot, accusation, room):
    reply, meta = await _generate_bot_text(
        bot,
        room,
        question="Vote apenas com uma palavra: culpado, inocente ou abstencao. Considere sua personalidade e suspeitas.",
        context={"phase": "voting"},
        purpose="vote",
        accusation=accusation,
    )
    lowered = (reply or "").lower()
    if "culpado" in lowered:
        return "culpado"
    if "absten" in lowered:
        return "abstencao"
    if "inocente" in lowered:
        return "inocente"
    accused = str((accusation or {}).get("accused_id", ""))
    alive = get_alive_players(room)
    return select_bot_vote(
        room_id=room.get("room_id", ""),
        bot_name=_bot_name(bot),
        accused=accused,
        bot_is_killer=bool(bot.get("is_killer")) if isinstance(bot, dict) else False,
        alive_players=[p.get("name") for p in alive],
    )


async def generate_case_with_ai(theme=None):
    prompt = CREATE_CASE_TEMPLATE
    if theme:
        prompt = f"{CREATE_CASE_TEMPLATE}\n\nTema solicitado: {theme}"
    messages = [
        {"role": "system", "content": SYSTEM_GAME_MASTER},
        {"role": "user", "content": prompt},
    ]
    text = await call_openrouter(messages, temperature=0.8, max_tokens=2000, timeout=float(os.getenv("AI_TIMEOUT_SECONDS", "10")))
    return text or generate_fallback_case()


async def bot_generate_response(bot_name: str, context: dict, question: str = None) -> str:
    """Compatibilidade: usa o novo motor OpenRouter dos bots com fallback local."""
    room = {
        "room_id": context.get("room_id", ""),
        "case": {
            "descricao": context.get("case_description", ""),
            "historia": context.get("case_history", ""),
            "local_corpo": context.get("case_location", ""),
            "arma_crime": context.get("case_weapon", ""),
            "evidencias": context.get("evidences", []),
            "suspeitos": context.get("suspects", []),
        },
        "chat": context.get("chat_history", []),
        "phase": context.get("phase", "turn"),
        "players": context.get("players", []),
    }
    return await generate_bot_reply({"name": bot_name, "id": bot_name}, room, question=question, context=context)


async def process_bot_turn(room_id: str, current_turn: int, current_player: dict):
    """
    Processa o turno de um bot.
    - Gera resposta usando IA e a registra em sua memória.
    - Envia para todos os jogadores.
    """
    if room_id not in ROOMS:
        return
    
    room = ROOMS[room_id]
    room["room_id"] = room_id
    bot_name = current_player.get("name", "Bot")
    bot_id = str(current_player.get("id") or bot_name)
    
    # Aguarda 2-4 segundos para parecer natural
    await asyncio.sleep(random.uniform(2, 4))
    
    # Prepara o contexto completo para o bot (com todas as pistas acumuladas)
    case_data = room.get("case", {})
    context = {
        "room_id": room_id,
        "case_description": case_data.get("descricao", ""),
        "case_history": case_data.get("historia", ""),
        "case_location": case_data.get("local_corpo", ""),
        "case_weapon": case_data.get("arma_crime", ""),
        "chat_history": room.get("chat", []),
        "evidences": get_all_clues_list(room_id),
        "suspects": case_data.get("suspeitos", [])
    }
    
    # Gera resposta do bot usando OpenRouter
    bot_response, ai_meta = await _generate_bot_text(current_player, room, context=context, purpose="reply")
    
    # Registra declaração do bot para consistência e evitar contradições
    record_bot_statement(room_id, bot_name, bot_response, context="turn_speech")
    
    # Adiciona a mensagem ao chat (sem indicar que é bot)
    message = {
        "player": bot_name,
        "text": bot_response,
        "timestamp": datetime.now().isoformat()
    }
    room.setdefault("chat", []).append(message)
    add_chat_message(room_id, bot_name, bot_response)
    
    # Verifica se o bot está morto
    bot_status = get_player_status(room_id, bot_id)
    is_bot_dead = bot_status == "dead"
    
    # Envia para todos os jogadores conectados (como mensagem normal de suspeito)
    if room_id in CONNECTIONS:
        for ws in CONNECTIONS[room_id]:
            try:
                await ws.send_json({
                    "type": "player_message",  # Trata como mensagem normal
                    "player": bot_name,
                    "message": bot_response,
                    "dead": is_bot_dead,
                    "ai_source": ai_meta.get("source"),
                    "ai_model": ai_meta.get("model")
                })
            except:
                pass


async def process_bot_interrogation_reply(room_id: str, bot_name: str, question: str):
    """Gera resposta de interrogatório para o bot usando a API da IA e limpa o estado de interrogatório."""
    # Pausa dramática para parecer mais natural (1.5 a 3 segundos)
    await asyncio.sleep(random.uniform(1.5, 3.0))
    
    room = ROOMS.get(room_id)
    if not room:
        return
    room["room_id"] = room_id
        
    case_data = room.get("case", {})
    context = {
        "case_description": case_data.get("descricao", ""),
        "case_history": case_data.get("historia", ""),
        "case_location": case_data.get("local_corpo", ""),
        "case_weapon": case_data.get("arma_crime", ""),
        "chat_history": room.get("chat", []),
        "evidences": get_all_clues_list(room_id),
        "suspects": case_data.get("suspeitos", [])
    }
    
    bot_info = get_player_by_id(room, bot_name)
    if not bot_info:
        for p in room.get("players", []):
            if isinstance(p, dict) and p.get("name") == bot_name:
                bot_info = p
                break
            
    bot_is_killer = bot_info.get("is_killer", False) if bot_info else False
    bot_display_name = bot_info.get("name", bot_name) if bot_info else bot_name
    
    try:
        full_reply, ai_meta = await _generate_bot_text(
            bot_info or {"id": bot_name, "name": bot_display_name, "is_killer": bot_is_killer},
            room,
            question=f"Você está sendo interrogado. Pergunta recebida: {question}",
            context={**context, "phase": "interrogation"},
            purpose="interrogation",
        )
        sinais = ""
        
        # Se for o assassino e a IA não gerou sinais nervosos, insere por padrão para dar pistas
        if bot_is_killer and (not sinais or "não" in sinais.lower() or "nenhum" in sinais.lower()):
            sinais = "Desvia o olhar com inquietação e limpa o suor das mãos."
            
        if bot_is_killer and "ação" not in full_reply.lower() and "olhar" not in full_reply.lower():
            full_reply += " *(Desvia o olhar por um instante antes de responder.)*"
            
        # Registra na consistência do bot
        record_bot_statement(room_id, bot_display_name, full_reply, context="interrogation_reply")
        await submit_interrogation_result(room_id, str(bot_info.get("id") if bot_info else bot_name), full_reply, metadata=ai_meta)
        
    except Exception as e:
        logger.error(f"❌ Erro no interrogatório do bot {bot_name}: {e}")
        memory = _get_bot_ai_memory(room_id, bot_display_name)
        fallback_reply = _select_local_fallback(bot_display_name, {**context, "room_id": room_id, "phase": "interrogation"}, memory, is_killer=bot_is_killer)
        await submit_interrogation_result(
            room_id,
            str(bot_info.get("id") if bot_info else bot_name),
            fallback_reply,
            metadata={"source": "local_fallback", "model": None, "reason": str(e)},
        )


def extract_json_from_string(text, validate_with_pydantic=None):
    """Extrai JSON válido de uma string com blocos markdown ```json...```"""
    try:
        # Procurar por blocos ```json...```
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            json_content = match.group(1).strip()
        else:
            json_content = text.strip()
            
        # Limpar zeros à esquerda de números inteiros para evitar erros de sintaxe JSON
        json_content = re.sub(r'([:\s,\[])0+(\d+)', r'\1\2', json_content)
        
        parsed = json.loads(json_content)
        
        # Validar com Pydantic se fornecido
        if validate_with_pydantic:
            try:
                # Se parsed não for dict, tenta converter
                if not isinstance(parsed, dict):
                    print(f"⚠️ parsed não é dict, tipo: {type(parsed)}")
                    if isinstance(parsed, str):
                        parsed = json.loads(parsed)
                    else:
                        parsed = {"descricao": str(parsed)[:500]}
                
                validated = validate_with_pydantic(**parsed)
                result = validated.model_dump()
                # Garante que o resultado seja um dict
                if not isinstance(result, dict):
                    print(f"⚠️ Resultado da validação não é dict, tipo: {type(result)}")
                    return parsed
                return result
            except Exception as e:
                print(f"⚠️ Validação Pydantic falhou: {e}, usando dados brutos")
                # Garante que parsed seja um dict
                if not isinstance(parsed, dict):
                    if isinstance(parsed, str):
                        try:
                            parsed = json.loads(parsed)
                        except:
                            parsed = {"descricao": parsed[:500]}
                    else:
                        parsed = {"descricao": str(parsed)[:500]}
                return parsed
        
        # Garante que o resultado seja sempre um dict
        if not isinstance(parsed, dict):
            if isinstance(parsed, str):
                try:
                    parsed = json.loads(parsed)
                except:
                    parsed = {"descricao": parsed[:500]}
            else:
                parsed = {"descricao": str(parsed)[:500]}
        
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


def _debug_endpoints_enabled() -> bool:
    """Endpoints de debug só ficam disponíveis fora de produção (ou com DEBUG_ENDPOINTS=true)."""
    if os.getenv("DEBUG_ENDPOINTS", "").lower() == "true":
        return True
    return os.getenv("ENVIRONMENT", "development").lower() != "production"


@app.get("/debug/env")
def debug_env():
    """Endpoint de debug para verificar variáveis de ambiente (desabilitado em produção)"""
    if not _debug_endpoints_enabled():
        raise FastAPIHTTPException(status_code=404, detail="Not Found")
    env_path = Path(__file__).parent / ".env"
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    return {
        "env_file_exists": env_path.exists(),
        "env_file_path": str(env_path),
        "openrouter_api_key_set": bool(api_key),
        "openrouter_primary_model": os.getenv("OPENROUTER_PRIMARY_MODEL", OPENROUTER_DEFAULT_PRIMARY_MODEL),
        "openrouter_fallback_model": os.getenv("OPENROUTER_FALLBACK_MODEL", OPENROUTER_DEFAULT_FALLBACK_MODEL),
    }


@app.get("/debug/cors")
def debug_cors(request: Request):
    """Endpoint de debug para verificar configuração CORS (desabilitado em produção)"""
    if not _debug_endpoints_enabled():
        raise FastAPIHTTPException(status_code=404, detail="Not Found")
    origin = request.headers.get("origin", "Nenhuma origem enviada")
    return {
        "allowed_origins": allowed_origins,
        "request_origin": origin,
        "origin_allowed": origin in allowed_origins if origin != "Nenhuma origem enviada" else None,
        "allowed_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        "credentials_allowed": True
    }


@app.get("/room/{room_id}/state")
async def get_room_state(room_id: str):
    """
    Endpoint de recuperação de estado para clientes reconectados.
    Retorna o snapshot do estado da sala persistido no banco.
    """
    try:
        snapshot = get_room_state_snapshot(room_id)
        if not snapshot:
            # Tenta obter da memória
            room = ROOMS.get(room_id)
            if not room:
                return JSONResponse(
                    status_code=404,
                    content={"error": "Sala não encontrada"}
                )
            snapshot = {
                "room_id": room_id,
                "game_active": room.get("game_active", False),
                "current_turn_player_id": room.get("current_turn"),
                "case": room.get("case", {}),
                "players": to_public_players(room.get("players", [])),
                "clues": get_all_clues_list(room_id),
                "recent_chat": room.get("chat", [])[-30:],
            }
        else:
            # Snapshot do banco também precisa ser sanitizado (contém is_killer)
            if isinstance(snapshot, dict) and "players" in snapshot:
                snapshot["players"] = to_public_players(snapshot.get("players", []))
            if isinstance(snapshot, dict):
                snapshot.pop("killer_id", None)
        return JSONResponse(content={"success": True, "state": snapshot})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Erro ao recuperar estado: {str(e)[:100]}"}
        )


@app.post("/case/new")
async def create_case(req: CreateCaseRequest):
    """Cria um novo caso criminal"""
    import uuid
    room_id = str(uuid.uuid4())[:8]
    
    prompt = CREATE_CASE_TEMPLATE.format(nivel=req.nivel, cenario=req.cenario)
    # Usa a nova função generate_case
    case_json = await generate_case(prompt)
    
    # Salva o resumo do caso no game_state (alinhado com a dinâmica: todos são suspeitos, um é assassino)
    set_case_summary(room_id, case_json)
    
    # Extrai pistas básicas do texto do caso (linhas que contêm "pista:")
    for line in case_json.splitlines():
        if "pista:" in line.lower() or "pista" in line.lower():
            pista_extraida = line.strip()
            if pista_extraida:
                add_clue(room_id, pista_extraida)
    
    # Usar a função melhorada para extrair JSON com validação Pydantic
    case = extract_json_from_string(case_json, validate_with_pydantic=CaseData)
    
    # Garantir que o case_id, nivel e cenario estejam corretos
    if case.get("case_id") == "ERRO" or not case.get("case_id"):
        case["case_id"] = room_id
    if not case.get("nivel"):
        case["nivel"] = req.nivel
    if not case.get("cenario"):
        case["cenario"] = req.cenario
    
    # Atualiza o game_state com o resumo formatado do caso
    case_summary = f"{case.get('descricao', '')} {case.get('historia', '')}"
    set_case_summary(room_id, case_summary)
    
    # Adiciona evidências do caso ao game_state
    evidencias = case.get("evidencias", [])
    for evidencia in evidencias:
        add_clue(room_id, evidencia)
    
    # Inicializar estrutura de jogo
    ROOMS[room_id] = {
        "room_id": room_id,
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
    
    answer = await call_openrouter(
        [
            {"role": "system", "content": SYSTEM_GAME_MASTER},
            {"role": "user", "content": prompt}
        ],
        temperature=0.8,
        max_tokens=500,
        timeout=float(os.getenv("AI_TIMEOUT_SECONDS", "10")),
    )
    if not answer:
        answer = ai_generate(prompt, system=SYSTEM_GAME_MASTER)
    
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
    
    # Adiciona pistas sugeridas ao game_state
    pistas_sugeridas = structured_answer.get("pistas_sugeridas", [])
    for pista in pistas_sugeridas:
        add_clue(room_id, pista)
    
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


# ======== Sanitização de dados (anticheat) ========
# Campos que NUNCA podem ser enviados em broadcast: revelam o assassino
# ou expõem dados pessoais (email) de outros jogadores.
_PRIVATE_PLAYER_FIELDS = {"is_killer", "email"}


def to_public_player(player) -> dict:
    """Retorna versão pública de um jogador, sem campos sensíveis (is_killer, email)."""
    if not isinstance(player, dict):
        return {"id": str(player), "name": str(player)}
    return {k: v for k, v in player.items() if k not in _PRIVATE_PLAYER_FIELDS}


def to_public_players(players) -> list:
    """Sanitiza uma lista de jogadores para broadcast."""
    return [to_public_player(p) for p in (players or [])]


async def broadcast_players(room_id: str):
    """Envia lista atualizada de jogadores para todos os conectados na sala"""
    room = ROOMS.get(room_id)
    if not room:
        return
    
    # Pega a lista de jogadores da sala e do game_state
    players_list = room.get("players", [])
    
    # Formata a lista para enviar
    formatted_players = []
    for p in players_list:
        if isinstance(p, dict):
            player_id = p.get("id") or p.get("name") or "Jogador"
            player_status = get_player_status(room_id, player_id)
            formatted_players.append({
                "id": str(player_id),
                "name": p.get("name") or player_id,
                "nickname": p.get("name") or player_id,
                "numeric_id": p.get("numeric_id"),
                "status": player_status if player_status != "unknown" else p.get("status", "alive"),
                "is_alive": (player_status if player_status != "unknown" else p.get("status", "alive")) == "alive",
                "isBot": p.get("isBot") or p.get("is_bot", False),
                "is_bot": p.get("isBot") or p.get("is_bot", False),
                "is_connected": p.get("is_connected", True),
            })
    
    # Envia para todos
    await broadcast(room_id, {
        "type": "jogadores",
        "players": formatted_players
    })


def normalize_players(players):
    """Normaliza jogadores em uma estrutura única e usa id string como identificador oficial."""
    normalized = []
    seen_ids = set()
    for index, raw in enumerate(players or [], start=1):
        if isinstance(raw, dict):
            numeric_id = raw.get("numeric_id") or raw.get("id") or index
            try:
                numeric_id = int(numeric_id)
            except (TypeError, ValueError):
                numeric_id = index
            player_id = str(raw.get("id") or numeric_id)
            if not player_id.strip():
                player_id = str(index)
            if player_id in seen_ids:
                player_id = str(index)
            name = str(raw.get("name") or raw.get("nickname") or f"Jogador {numeric_id}")
            status_value = raw.get("status", "alive")
            status_value = "dead" if status_value == "dead" else "alive"
            is_bot = bool(raw.get("is_bot") or raw.get("isBot"))
            is_connected = bool(raw.get("is_connected", not is_bot))
        else:
            numeric_id = index
            player_id = str(index)
            name = str(raw or f"Jogador {index}")
            status_value = "alive"
            is_bot = False
            is_connected = True

        seen_ids.add(player_id)
        normalized.append({
            "id": player_id,
            "name": name,
            "numeric_id": numeric_id,
            "status": status_value,
            "is_bot": is_bot,
            "isBot": is_bot,
            "is_killer": bool(raw.get("is_killer", False)) if isinstance(raw, dict) else False,
            "is_connected": is_connected,
            "email": raw.get("email") if isinstance(raw, dict) else None,
        })
    return normalized


def get_alive_players(room):
    return [p for p in room.get("players", []) if isinstance(p, dict) and p.get("status") == "alive"]


def get_player_by_id(room, player_id):
    player_id = str(player_id)
    return next((p for p in room.get("players", []) if str(p.get("id")) == player_id), None)


def resolve_player_id(room, identifier):
    """Resolve nome, id antigo ou numeric_id para o id oficial string."""
    if identifier is None:
        return ""
    ident = str(identifier)
    for p in room.get("players", []):
        if not isinstance(p, dict):
            continue
        if ident in {str(p.get("id")), str(p.get("name")), str(p.get("numeric_id"))}:
            return str(p.get("id"))
    return ident


def set_phase(room_id, phase):
    if phase not in VALID_PHASES:
        raise ValueError(f"Fase inválida: {phase}")
    room = ROOMS.get(room_id)
    if not room:
        return
    room["phase"] = phase
    logger.info(f"[GAME_PHASE] room={room_id} phase={phase}")


async def broadcast_game_state(room_id):
    room = ROOMS.get(room_id)
    if not room:
        return
    await broadcast(room_id, {
        "type": "game_state",
        "phase": room.get("phase", "lobby"),
        "current_turn_player_id": str(room.get("current_turn_player_id") or ""),
        "players": to_public_players(room.get("players", [])),
        "active_accusation": room.get("active_accusation"),
        "active_interrogation": room.get("active_interrogation"),
    })


async def send_private_to_player(room_id, player_id, message):
    """Entrega mensagem privada a humanos conectados cujo nome/id mapeia para player_id."""
    room = ROOMS.get(room_id)
    if not room:
        return
    target = get_player_by_id(room, player_id)
    target_names = {str(player_id)}
    if target:
        target_names.add(str(target.get("name")))
    for ws in CONNECTIONS.get(room_id, []):
        conn = CONNECTION_PLAYERS.get(room_id, {}).get(id(ws), {})
        if str(conn.get("id")) in target_names or str(conn.get("name")) in target_names:
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                pass


def _player_public_name(room, player_id):
    player = get_player_by_id(room, player_id)
    return player.get("name", str(player_id)) if player else str(player_id)


async def send_private_message(room_id: str, player_id: str, message: dict):
    """Envia mensagem privada para um jogador específico"""
    # Encontra o WebSocket do jogador pelo player_id ou nome
    if room_id in CONNECTIONS:
        for ws in CONNECTIONS[room_id]:
            # Nota: Precisamos mapear player_id para websocket
            # Por enquanto, enviaremos para todos e o frontend filtra
            try:
                await ws.send_text(json.dumps(message))
            except:
                pass


def generate_clue_from_murder(victim_name: str, victim_info: dict, case_context: dict) -> str:
    """
    Gera uma pista após um assassinato usando OpenRouter.
    Analisa a morte e gera uma pista contextual.
    """
    try:
        prompt = f"""Você é o Mestre do Jogo 'Deadly Truth'. Um assassinato acabou de ocorrer.

VÍTIMA: {victim_name}
CONTEXTO DO CASO: {case_context.get('descricao', '')} {case_context.get('historia', '')}
LOCAL DO CRIME: {case_context.get('local_corpo', '')}
ARMA DO CRIME: {case_context.get('arma_crime', '')}

Gere UMA pista forense ou investigativa que foi encontrada no corpo ou na cena do crime.
A pista deve ser útil para os investigadores, mas não deve revelar diretamente o assassino.
Seja criativo e misterioso.

Formato: "Pista encontrada: [descrição da pista]"

Exemplo: "Pista encontrada: Fragmentos de tecido vermelho foram encontrados perto do corpo, sugerindo uma luta."

Responda APENAS com a pista, sem explicações adicionais:"""
        
        client = get_openrouter_client()
        model = os.getenv("OPENROUTER_PRIMARY_MODEL", OPENROUTER_DEFAULT_PRIMARY_MODEL)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_GAME_MASTER},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=500
        )
        
        clue = response.choices[0].message.content.strip()
        # Limpa a resposta
        clue = clue.replace("Pista encontrada:", "").strip()
        if not clue.startswith("Pista encontrada:"):
            clue = f"Pista encontrada: {clue}"
        
        return clue
    except Exception as e:
        print(f"❌ Erro ao gerar pista do assassinato: {e}")
        return f"Pista encontrada: Vestígios de luta foram encontrados na cena do crime."


async def check_win_conditions(room_id: str) -> dict:
    """
    Verifica condições de vitória do jogo.
    Retorna: {"game_ended": bool, "winner": str, "reason": str}
    """
    room = ROOMS.get(room_id)
    if not room:
        return {"game_ended": False}
    
    players = room.get("players", [])
    alive_players = get_alive_players(room)
    alive_killers = [p for p in alive_players if p.get("is_killer")]
    alive_innocents = [p for p in alive_players if not p.get("is_killer")]
    killer = next((p for p in players if isinstance(p, dict) and p.get("is_killer")), None)

    logger.info(
        f"[WIN_CHECK] room={room_id} alive={len(alive_players)} killers={len(alive_killers)} innocents={len(alive_innocents)}"
    )

    if not killer:
        return {"game_ended": False}

    if len(alive_killers) == 0:
        return {
            "game_ended": True,
            "winner": "inocentes",
            "winner_name": "Inocentes",
            "reason": "O assassino foi eliminado.",
            "killer_id": str(killer.get("id")),
            "killer_name": killer.get("name", "Assassino"),
        }

    if len(alive_innocents) == 0:
        return {
            "game_ended": True,
            "winner": "assassino",
            "winner_name": killer.get("name", "Assassino"),
            "reason": "Todos os inocentes foram eliminados.",
            "killer_id": str(killer.get("id")),
            "killer_name": killer.get("name", "Assassino"),
        }

    if len(alive_killers) >= len(alive_innocents):
        return {
            "game_ended": True,
            "winner": "assassino",
            "winner_name": killer.get("name", "Assassino"),
            "reason": "O número de assassinos vivos alcançou o número de inocentes.",
            "killer_id": str(killer.get("id")),
            "killer_name": killer.get("name", "Assassino"),
        }

    return {"game_ended": False}


def is_player_turn(room_id: str, player_identifier: str) -> tuple[bool, str]:
    """
    Verifica se é o turno do jogador.
    Retorna (True, "") se for o turno, (False, mensagem_erro) caso contrário.
    ✅ CORREÇÃO: Validação robusta com IDs normalizados e nunca vazios.
    """
    room = ROOMS.get(room_id)
    if not room:
        return (False, "Sala não encontrada.")
    player_identifier = resolve_player_id(room, player_identifier)
    current_turn_id = room.get("current_turn_player_id") or get_current_turn(room_id)
    if not current_turn_id:
        logger.warning(f"⚠️ current_turn_id está vazio para sala {room_id}")
        return (True, "")  # Se não há turno definido, permite
    
    # ✅ CORREÇÃO: Normalizar para string e validar que não estão vazios
    p_id = str(player_identifier).strip() if player_identifier else ""
    c_id = str(current_turn_id).strip() if current_turn_id else ""
    
    # Validar que não estão vazios
    if not p_id or not c_id:
        logger.warning(f"⚠️ IDs vazios: player_id={p_id}, current_turn={c_id}")
        return (False, f"⛔ Erro: IDs de turno inválidos. (Você: {p_id}, Turno atual: {c_id})")
    
    # Normaliza identificadores para comparação (case-insensitive)
    current_turn_normalized = c_id.lower()
    player_identifier_normalized = p_id.lower()
    
    # Compara diretamente
    if current_turn_normalized == player_identifier_normalized:
        logger.info(f"✅ Validação de turno: {p_id} == {c_id} ? True")
        return (True, "")
    
    logger.info(f"❌ Validação de turno: {p_id} == {c_id} ? False")
    return (False, f"⛔ Não é sua vez. Aguarde o próximo turno. (Turno atual: {c_id}, Você: {p_id})")


async def kill_player(room_id: str, killer_id: str, target_id: str) -> dict:
    """
    Assassina um jogador. Valida se quem chamou é o assassino e se é seu turno.
    Usa game_state para controle centralizado.
    
    Returns: {"success": bool, "message": str, "clue": str}
    """
    room = ROOMS.get(room_id)
    if not room:
        return {"success": False, "message": "Sala não encontrada"}
    killer_id = resolve_player_id(room, killer_id)
    target_id = resolve_player_id(room, target_id)
    
    # 🔒 Verifica se é o assassino usando game_state
    killer_id_from_state = get_killer_id(room_id)
    if killer_id_from_state and killer_id != killer_id_from_state:
        # Tenta encontrar pelo nome também
        players = room.get("players", [])
        killer_found = False
        for p in players:
            if isinstance(p, dict) and p.get("is_killer") and (p.get("name") == killer_id or p.get("id") == killer_id):
                killer_found = True
                break
        if not killer_found:
            return {"success": False, "message": "Apenas o assassino pode matar"}
    
    # ⏳ Verifica turno usando game_state
    current_turn_id = get_current_turn(room_id)
    if current_turn_id and killer_id != current_turn_id:
        # Verifica também pelo nome
        players = room.get("players", [])
        current_player = None
        for p in players:
            if isinstance(p, dict):
                player_name = p.get("name", "")
                if player_name == current_turn_id or p.get("id") == current_turn_id:
                    current_player = p
                    break
        
        if current_player and current_player.get("name") != killer_id:
            return {"success": False, "message": "Não é o seu turno"}
    
    # ☠️ Verifica se o alvo está vivo usando game_state
    if not is_alive(room_id, target_id):
        return {"success": False, "message": "Este jogador já está morto"}
    
    players = room.get("players", [])
    target = get_player_by_id(room, target_id)
    
    if not target:
        return {"success": False, "message": "Alvo não encontrado"}
    
    if target.get("is_killer"):
        return {"success": False, "message": "O assassino não pode se matar"}
    
    # Verifica limite de mortes por rodada (1 morte por rodada)
    kills_this_round = room.get("kills_this_round", 0)
    if kills_this_round >= 1:
        return {"success": False, "message": "Limite de 1 morte por rodada atingido"}
    
    # 💀 Mata o jogador (atualiza tanto no room quanto no game_state)
    target["status"] = "dead"
    kill_player_state(room_id, target_id)  # Atualiza game_state
    room["kills_this_round"] = kills_this_round + 1
    
    # Gera pista após a morte
    case_data = room.get("case", {})
    clue = generate_clue_from_murder(
        target.get("name", "Jogador"),
        target,
        case_data
    )
    
    # Adiciona pista ao game_state e propaga para a memória dos bots
    add_clue(room_id, clue)
    for p in players:
        if isinstance(p, dict) and (p.get("is_bot") or p.get("isBot")):
            add_clue_to_bot(room_id, p.get("name"), clue)
    
    # Anuncia a morte publicamente
    death_message = f"💀 {target.get('name', 'Jogador')} foi encontrado morto!"
    
    await broadcast(room_id, {
        "type": "player_death",
        "victim_id": str(target_id),
        "victim": target.get("name", "Jogador"),
        "message": death_message,
        "clue": clue
    })
    
    # Envia pista como mensagem separada tipo "pista"
    await broadcast(room_id, {
        "type": "pista",
        "text": clue
    })
    
    # Adiciona mensagem ao chat
    room.setdefault("chat", []).append({
        "player": "Sistema",
        "text": death_message,
        "timestamp": datetime.now().isoformat()
    })
    
    add_chat_message(room_id, "Sistema", death_message)
    add_chat_message(room_id, "Sistema", clue)
    
    # Sistema de análise de comportamento (opcional)
    # analyze_bot_behavior(room_id, killer_id, target_id)
    
    # Verifica condições de vitória
    win_check = await check_win_conditions(room_id)
    if win_check.get("game_ended"):
        await finish_game(room_id, win_check)
    
    return {
        "success": True,
        "message": death_message,
        "clue": clue,
        "victim": target.get("name", "Jogador")
    }


async def advance_turn_on_disconnect(room_id: str):
    """
    Acorda o loop de jogo quando o jogador da vez se desconecta.
    """
    logger.info(f"🔌 Acordando loop de jogo após desconexão na sala {room_id}")
    if room_id in GAME_EVENTS:
        GAME_EVENTS[room_id]["player_action_event"].set()


async def check_and_process_vote_results(room_id: str):
    """
    Verifica se todos os votos foram coletados e apura o resultado.
    Evita travamentos chamando centralizadamente para bots e humanos.
    """
    room = ROOMS.get(room_id)
    if not room:
        return
        
    accused = get_accused_player(room_id)
    if not accused:
        return
        
    players = room.get("players", [])
    alive_players = [p for p in players if isinstance(p, dict) and p.get("status") != "dead"]
    alive_identifiers = []
    for p in alive_players:
        if isinstance(p, dict):
            pid = p.get("id") or p.get("name")
            if pid:
                alive_identifiers.append(pid)
                
    if all_votes_in(room_id, alive_identifiers):
        culpa, inoc = get_vote_result(room_id)
        killer_id = get_killer_id(room_id)
        
        resultado_msg = f"🗳️ Votação encerrada: {culpa} votaram 'culpado', {inoc} votaram 'inocente'."
        
        # Se maioria votou 'culpado'
        if culpa > inoc:
            if accused == killer_id:
                resultado_msg += f"\n🎉 O assassino era {accused}! Os inocentes venceram!"
                await broadcast(room_id, {
                    "type": "game_end",
                    "winner": "inocentes",
                    "winner_name": "Inocentes",
                    "reason": f"Descobriram que {accused} era o assassino!",
                    "accused": accused,
                    "was_killer": True
                })
                room["game_active"] = False
                clear_room_state(room_id)
            else:
                resultado_msg += f"\n❌ {accused} era inocente e foi eliminado. O jogo continua..."
                
                # Elimina o jogador no estado
                kill_player_state(room_id, accused)
                for p in room.get("players", []):
                    if isinstance(p, dict) and (str(p.get("id")) == str(accused) or str(p.get("name")) == str(accused)):
                        p["status"] = "dead"
                        
                # Avisa a todos sobre a eliminação
                await broadcast(room_id, {
                    "type": "player_death",
                    "victim": accused,
                    "message": f"💀 {accused} foi eliminado pelo tribunal (era inocente)!",
                    "clue": "Nenhuma pista adicional gerada pelo erro do tribunal."
                })
                
                await broadcast(room_id, {
                    "type": "resultado_votacao",
                    "message": resultado_msg,
                    "accused": accused,
                    "was_killer": False,
                    "guilt_votes": culpa,
                    "innocent_votes": inoc
                })
                clear_vote(room_id)
                
                # Verifica condições de vitória após eliminação
                win_check = await check_win_conditions(room_id)
                if win_check.get("game_ended"):
                    await broadcast(room_id, {
                        "type": "game_end",
                        "winner": win_check.get("winner"),
                        "winner_name": win_check.get("winner_name"),
                        "reason": win_check.get("reason")
                    })
                    room["game_active"] = False
        else:
            resultado_msg += "\n🔄 A maioria votou 'inocente'. O jogo continua..."
            await broadcast(room_id, {
                "type": "resultado_votacao",
                "message": resultado_msg,
                "accused": accused,
                "was_killer": False,
                "guilt_votes": culpa,
                "innocent_votes": inoc
            })
            clear_vote(room_id)
            
        add_chat_message(room_id, "Sistema", resultado_msg)
        room.setdefault("chat", []).append({
            "player": "Sistema",
            "text": resultado_msg,
            "timestamp": datetime.now().isoformat()
        })
        
        # Avança o turno automaticamente
        if room_id in GAME_EVENTS:
            logger.info(f"🗳️ Votação concluída na sala {room_id}. Avançando o turno.")
            GAME_EVENTS[room_id]["player_action_event"].set()


async def process_bot_votes(room_id: str):
    """
    Bots votam automaticamente após 2 segundos de uma votação iniciada.
    Bots votam estrategicamente baseados em memórias/suspeita.
    """
    await asyncio.sleep(2)  # Aguarda 2 segundos
    
    room = ROOMS.get(room_id)
    if not room:
        return
    
    accused = get_accused_player(room_id)
    if not accused:
        return  # Nenhuma votação em andamento
    
    players = room.get("players", [])
    alive_players = [p for p in players if isinstance(p, dict) and p.get("status") != "dead"]
    
    for player in alive_players:
        if isinstance(player, dict):
            is_bot = player.get("isBot", False) or player.get("is_bot", False)
            player_id = str(player.get("id") or player.get("name", ""))
            
            if is_bot and is_alive(room_id, player_id):
                try:
                    bot_is_killer = player.get("is_killer") or player.get("isKiller", False)
                    # Incrementa suspeição no acusado para bots inocentes (pressão social)
                    if not bot_is_killer:
                        update_suspicion_score(room_id, player_id, accused, 0.15)
                    
                    # Decide o voto inteligentemente via select_bot_vote
                    vote = select_bot_vote(
                        room_id=room_id,
                        bot_name=player_id,
                        accused=accused,
                        bot_is_killer=bot_is_killer,
                        alive_players=[p.get("name") for p in alive_players if isinstance(p, dict)]
                    )
                    
                    # Registra o voto
                    submit_vote(room_id, player_id, vote)
                    
                    # Notifica sobre o voto do bot
                    await broadcast(room_id, {
                        "type": "voto_registrado",
                        "player_name": player.get("name", "Bot"),
                        "voto": vote,
                        "message": f"🤖 {player.get('name', 'Bot')} votou: {vote}"
                    })
                    
                    logger.info(f"Bot {player_id} votou {vote} na votação de {accused}")
                except Exception as e:
                    logger.error(f"Erro ao processar voto do bot {player_id}: {e}")
                    
    # Apura resultados da votação
    await check_and_process_vote_results(room_id)


async def advance_to_next_alive_player(room_id: str):
    room = ROOMS.get(room_id)
    if not room:
        return
    players = room.get("players", [])
    if not get_alive_players(room):
        return
    current_index = int(room.get("current_turn", 0))
    for step in range(1, len(players) + 1):
        next_index = (current_index + step) % len(players)
        candidate = players[next_index]
        if isinstance(candidate, dict) and candidate.get("status") == "alive":
            room["current_turn"] = next_index
            room["current_turn_player_id"] = str(candidate.get("id"))
            set_current_turn(room_id, str(candidate.get("id")))
            logger.info(f"[TURN] room={room_id} next_player={candidate.get('id')} name={candidate.get('name')}")
            break
    if room_id in GAME_EVENTS:
        GAME_EVENTS[room_id]["player_action_event"].set()


async def finish_game(room_id: str, result: dict):
    room = ROOMS.get(room_id)
    if not room:
        return
    killer = next((p for p in room.get("players", []) if isinstance(p, dict) and p.get("is_killer")), None)
    payload = {
        "type": "game_end",
        "winner": result.get("winner"),
        "winner_name": result.get("winner_name"),
        "reason": result.get("reason"),
        "killer_id": result.get("killer_id") or (str(killer.get("id")) if killer else ""),
        "killer_name": result.get("killer_name") or (killer.get("name") if killer else ""),
    }
    set_phase(room_id, "ended")
    room["game_active"] = False
    await broadcast(room_id, payload)
    flush_game_end_to_db(room_id)
    if room_id in GAME_EVENTS:
        GAME_EVENTS[room_id]["player_action_event"].set()


async def submit_interrogation_result(room_id: str, responder_id: str, response_text: str, timed_out: bool = False, metadata: dict | None = None):
    room = ROOMS.get(room_id)
    if not room or not room.get("active_interrogation"):
        return
    active = room["active_interrogation"]
    if str(active.get("target_id")) != str(responder_id):
        return
    if timed_out:
        await broadcast(room_id, {
            "type": "interrogation_timeout",
            "message": "O interrogado permaneceu em silêncio.",
        })
    target_name = _player_public_name(room, responder_id)
    add_chat_message(room_id, target_name, response_text)
    room.setdefault("chat", []).append({
        "player": target_name,
        "text": response_text,
        "timestamp": datetime.now().isoformat(),
    })
    await broadcast(room_id, {
        "type": "interrogation_result",
        "interrogator_id": active.get("interrogator_id"),
        "target_id": active.get("target_id"),
        "question": active.get("question"),
        "message": response_text,
        "player": target_name,
        "ai_source": (metadata or {}).get("source"),
        "ai_model": (metadata or {}).get("model"),
    })
    await broadcast(room_id, {
        "type": "resposta_interrogatorio",
        "player": target_name,
        "message": response_text,
        "ai_source": (metadata or {}).get("source"),
        "ai_model": (metadata or {}).get("model"),
    })
    room["active_interrogation"] = None
    clear_interrogation(room_id)
    set_phase(room_id, "turn")
    await advance_to_next_alive_player(room_id)


async def interrogation_timeout_task(room_id: str, target_id: str, started_at: float):
    await asyncio.sleep(45)
    room = ROOMS.get(room_id)
    active = room.get("active_interrogation") if room else None
    if active and str(active.get("target_id")) == str(target_id) and active.get("created_at") == started_at:
        logger.info(f"[INTERROGATION] room={room_id} timeout target={target_id}")
        await submit_interrogation_result(room_id, target_id, "O interrogado permaneceu em silêncio.", timed_out=True)


async def start_interrogation_phase(room_id: str, interrogator_id: str, target_id: str, question: str):
    room = ROOMS.get(room_id)
    if not room:
        return {"success": False, "message": "Sala não encontrada."}
    if room.get("phase") != "turn":
        return {"success": False, "message": "Interrogatório só pode ser iniciado no turno."}
    if str(room.get("current_turn_player_id")) != str(interrogator_id):
        return {"success": False, "message": "Não é sua vez."}
    target = get_player_by_id(room, target_id)
    if not target or target.get("status") != "alive":
        return {"success": False, "message": "Alvo inválido ou morto."}
    started_at = time.time()
    room["active_interrogation"] = {
        "interrogator_id": str(interrogator_id),
        "target_id": str(target_id),
        "question": question,
        "created_at": started_at,
    }
    start_interrogation(room_id, str(interrogator_id), str(target_id), question)
    set_phase(room_id, "interrogation")
    logger.info(f"[INTERROGATION] room={room_id} interrogator={interrogator_id} target={target_id}")
    await broadcast(room_id, {
        "type": "interrogation_started",
        "phase": "interrogation",
        "interrogator_id": str(interrogator_id),
        "target_id": str(target_id),
        "question": question,
        "timeout": 45,
    })
    await broadcast(room_id, {
        "type": "interrogatorio_iniciado",
        "interrogator": str(interrogator_id),
        "target": str(target_id),
        "question": question,
        "message": f"{_player_public_name(room, interrogator_id)} está interrogando {_player_public_name(room, target_id)}.",
    })
    if target.get("is_bot"):
        asyncio.create_task(process_bot_interrogation_reply(room_id, str(target_id), question))
    else:
        asyncio.create_task(interrogation_timeout_task(room_id, str(target_id), started_at))
    return {"success": True}


async def start_accusation(room_id: str, accuser_id: str, accused_id: str):
    room = ROOMS.get(room_id)
    if not room:
        return {"success": False, "message": "Sala não encontrada."}
    if room.get("phase") != "turn":
        return {"success": False, "message": "Acusação só pode ser feita no turno."}
    if str(room.get("current_turn_player_id")) != str(accuser_id):
        return {"success": False, "message": "Não é sua vez."}
    accused = get_player_by_id(room, accused_id)
    if not accused or accused.get("status") != "alive":
        return {"success": False, "message": "Acusado inválido ou morto."}
    if str(accuser_id) == str(accused_id):
        return {"success": False, "message": "Você não pode se acusar."}
    room["active_accusation"] = {
        "accuser_id": str(accuser_id),
        "accused_id": str(accused_id),
        "defense_text": None,
        "created_at": time.time(),
    }
    room["votes"] = {}
    set_phase(room_id, "defense")
    message = f"Jogador {_player_public_name(room, accuser_id)} acusou {_player_public_name(room, accused_id)}. O acusado tem direito a defesa."
    logger.info(f"[ACCUSATION] room={room_id} accuser={accuser_id} accused={accused_id}")
    await broadcast(room_id, {
        "type": "accusation_started",
        "phase": "defense",
        "accuser_id": str(accuser_id),
        "accused_id": str(accused_id),
        "message": message,
        "defense_timeout": 45,
    })
    add_chat_message(room_id, "Sistema", message)
    if accused.get("is_bot"):
        asyncio.create_task(bot_defense_task(room_id, str(accused_id), room["active_accusation"]["created_at"]))
    else:
        asyncio.create_task(defense_timeout_task(room_id, str(accused_id), room["active_accusation"]["created_at"]))
    return {"success": True}


async def bot_defense_task(room_id: str, accused_id: str, created_at: float):
    await asyncio.sleep(random.uniform(1.5, 3.0))
    room = ROOMS.get(room_id)
    if not room or not room.get("active_accusation") or room["active_accusation"].get("created_at") != created_at:
        return
    room["room_id"] = room_id
    accused = get_player_by_id(room, accused_id)
    case_data = room.get("case", {})
    context = {
        "case_description": case_data.get("descricao", ""),
        "case_history": case_data.get("historia", ""),
        "chat_history": room.get("chat", []),
        "evidences": get_all_clues_list(room_id),
        "suspects": case_data.get("suspeitos", []),
    }
    defense = await generate_bot_defense(accused, room.get("active_accusation"), room)
    await submit_defense(room_id, accused_id, defense)


async def defense_timeout_task(room_id: str, accused_id: str, created_at: float):
    await asyncio.sleep(45)
    room = ROOMS.get(room_id)
    active = room.get("active_accusation") if room else None
    if active and str(active.get("accused_id")) == str(accused_id) and active.get("created_at") == created_at and active.get("defense_text") is None:
        logger.info(f"[ACCUSATION] room={room_id} defense_timeout accused={accused_id}")
        await submit_defense(room_id, accused_id, "O acusado permaneceu em silêncio.")


async def submit_defense(room_id: str, accused_id: str, defense_text: str):
    room = ROOMS.get(room_id)
    active = room.get("active_accusation") if room else None
    if not active or str(active.get("accused_id")) != str(accused_id):
        return {"success": False, "message": "Nenhuma defesa pendente para este jogador."}
    active["defense_text"] = defense_text
    accused_name = _player_public_name(room, accused_id)
    add_chat_message(room_id, accused_name, defense_text)
    room.setdefault("chat", []).append({
        "player": accused_name,
        "text": defense_text,
        "timestamp": datetime.now().isoformat(),
    })
    await start_voting(room_id)
    return {"success": True}


async def start_voting(room_id: str):
    room = ROOMS.get(room_id)
    active = room.get("active_accusation") if room else None
    if not active:
        return
    set_phase(room_id, "voting")
    room["votes"] = {}
    eligible_voters = [str(p.get("id")) for p in get_alive_players(room)]
    logger.info(f"[VOTING] room={room_id} accused={active.get('accused_id')} voters={eligible_voters}")
    await broadcast(room_id, {
        "type": "voting_started",
        "phase": "voting",
        "accused_id": active.get("accused_id"),
        "accuser_id": active.get("accuser_id"),
        "defense_text": active.get("defense_text"),
        "eligible_voters": eligible_voters,
        "voting_timeout": 30,
    })
    await broadcast(room_id, {
        "type": "votacao_iniciada",
        "accused": active.get("accused_id"),
        "accuser": active.get("accuser_id"),
        "message": f"Votação iniciada contra {_player_public_name(room, active.get('accused_id'))}.",
    })
    asyncio.create_task(auto_bot_votes(room_id, active.get("created_at")))
    asyncio.create_task(voting_timeout_task(room_id, active.get("created_at")))


async def auto_bot_votes(room_id: str, accusation_created_at: float):
    await asyncio.sleep(1.5)
    room = ROOMS.get(room_id)
    active = room.get("active_accusation") if room else None
    if not active or active.get("created_at") != accusation_created_at or room.get("phase") != "voting":
        return
    accused_id = str(active.get("accused_id"))
    alive = get_alive_players(room)
    for player in alive:
        player_id = str(player.get("id"))
        if not player.get("is_bot") or player_id in room.get("votes", {}):
            continue
        room["room_id"] = room_id
        try:
            vote = await generate_bot_vote(player, active, room)
        except Exception as exc:
            logger.warning(f"[BOT_REPLY] bot={player.get('name', player_id)} source=local_fallback reason=vote_ai_error:{exc}")
            vote = select_bot_vote(
                room_id=room_id,
                bot_name=player.get("name", player_id),
                accused=accused_id,
                bot_is_killer=bool(player.get("is_killer")),
                alive_players=[p.get("name") for p in alive],
            )
        await register_vote(room_id, player_id, vote)


async def voting_timeout_task(room_id: str, accusation_created_at: float):
    await asyncio.sleep(30)
    room = ROOMS.get(room_id)
    active = room.get("active_accusation") if room else None
    if not active or active.get("created_at") != accusation_created_at or room.get("phase") != "voting":
        return
    for player in get_alive_players(room):
        player_id = str(player.get("id"))
        if player_id not in room.get("votes", {}):
            room["votes"][player_id] = "abstencao"
            await broadcast(room_id, {
                "type": "vote_registered",
                "player_id": player_id,
                "vote": "abstencao",
            })
    logger.info(f"[VOTING] room={room_id} timeout")
    await resolve_voting(room_id)


async def register_vote(room_id: str, player_id: str, vote: str):
    room = ROOMS.get(room_id)
    if not room or room.get("phase") != "voting" or not room.get("active_accusation"):
        return {"success": False, "message": "Nenhuma votação em andamento."}
    if vote not in {"culpado", "inocente", "abstencao"}:
        return {"success": False, "message": "Voto inválido."}
    player = get_player_by_id(room, player_id)
    if not player or player.get("status") != "alive":
        return {"success": False, "message": "Jogadores mortos não votam."}
    room.setdefault("votes", {})[str(player_id)] = vote
    logger.info(f"[VOTING] room={room_id} voter={player_id} vote={vote}")
    await broadcast(room_id, {
        "type": "vote_registered",
        "player_id": str(player_id),
        "vote": vote,
    })
    eligible = {str(p.get("id")) for p in get_alive_players(room)}
    if eligible and eligible.issubset(set(room.get("votes", {}).keys())):
        await resolve_voting(room_id)
    return {"success": True}


async def resolve_voting(room_id: str):
    room = ROOMS.get(room_id)
    active = room.get("active_accusation") if room else None
    if not active:
        return
    set_phase(room_id, "resolution")
    votes = room.get("votes", {})
    guilty_votes = sum(1 for v in votes.values() if v == "culpado")
    innocent_votes = sum(1 for v in votes.values() if v == "inocente")
    abstentions = sum(1 for v in votes.values() if v == "abstencao")
    accused_id = str(active.get("accused_id"))
    accused = get_player_by_id(room, accused_id)
    was_killer = bool(accused and accused.get("is_killer"))
    convicted = guilty_votes > (len(get_alive_players(room)) / 2)
    if convicted and was_killer:
        message = f"{_player_public_name(room, accused_id)} era o assassino. Os inocentes venceram."
    elif convicted:
        accused["status"] = "dead"
        kill_player_state(room_id, accused_id)
        message = f"{_player_public_name(room, accused_id)} era inocente e foi eliminado. O jogo continua."
        await broadcast(room_id, {
            "type": "player_death",
            "victim_id": accused_id,
            "victim": accused.get("name", accused_id),
            "message": message,
            "clue": "Nenhuma pista adicional foi revelada pela execução.",
        })
    else:
        message = f"{_player_public_name(room, accused_id)} sobreviveu à votação."

    logger.info(f"[VOTING] room={room_id} result accused={accused_id} guilty={guilty_votes} innocent={innocent_votes} abstentions={abstentions} convicted={convicted}")
    payload = {
        "type": "voting_result",
        "accused_id": accused_id,
        "guilty_votes": guilty_votes,
        "innocent_votes": innocent_votes,
        "abstentions": abstentions,
        "was_killer": was_killer,
        "message": message,
    }
    await broadcast(room_id, payload)
    await broadcast(room_id, {
        "type": "resultado_votacao",
        "accused": accused_id,
        "was_killer": was_killer,
        "guilt_votes": guilty_votes,
        "innocent_votes": innocent_votes,
        "abstentions": abstentions,
        "message": message,
    })
    add_chat_message(room_id, "Sistema", message)

    room["active_accusation"] = None
    room["votes"] = {}
    if convicted and was_killer:
        await finish_game(room_id, {
            "winner": "inocentes",
            "winner_name": "Inocentes",
            "reason": "O assassino foi condenado em votação.",
        })
        return
    win_check = await check_win_conditions(room_id)
    if win_check.get("game_ended"):
        await finish_game(room_id, win_check)
        return
    set_phase(room_id, "turn")
    await advance_to_next_alive_player(room_id)


async def start_game_safe(room_id: str):
    """
    Inicia o jogo com tratamento robusto de erros.
    Versão segura que valida estado antes de iniciar.
    """
    room = ROOMS.get(room_id)
    if not room:
        logger.warning(f"⚠️ Sala {room_id} não encontrada em start_game_safe")
        return
    
    if room.get("game_active"):
        logger.warning(f"⚠️ Jogo em {room_id} já está ativo")
        return
    
    try:
        logger.info(f"🎮 Iniciando jogo seguro em {room_id}")
        
        # Marca como ativo ANTES de gerar caso
        room["game_active"] = True
        
        # Chama game_loop que já tem toda a lógica
        await game_loop(room_id)
        
        logger.info(f"✅ Jogo iniciado com sucesso em {room_id}")
        
    except Exception as e:
        logger.exception(f"❌ Erro ao iniciar jogo seguro em {room_id}: {e}")
        room["game_active"] = False
        await broadcast(room_id, {
            "type": "error",
            "message": f"Erro ao iniciar jogo: {str(e)[:100]}"
        })


async def game_loop(room_id: str):
    """Loop principal do jogo - gera o caso pelo provedor de IA ativo e gerencia os turnos."""
    logger.info(f"\n{'='*60}")
    logger.info(f"🎮 game_loop INICIADO para sala {room_id}")
    logger.info(f"{'='*60}\n")
    
    room = ROOMS.get(room_id)
    if not room:
        logger.error(f"❌ Sala {room_id} não encontrada no game_loop")
        return
    
    participantes = normalize_players(room.get("players", []))
    room["players"] = participantes
    num_jogadores = len(participantes)
    logger.info(f"👥 Número de participantes: {num_jogadores}")
    
    if num_jogadores < 3:
        logger.error(f"❌ Número insuficiente de jogadores: {num_jogadores} (mínimo: 3)")
        room["game_active"] = False
        await broadcast(room_id, {
            "type": "error",
            "message": f"Número insuficiente de jogadores: {num_jogadores} (mínimo: 3)"
        })
        return
    
    room["game_active"] = True
    room["active_accusation"] = None
    room["active_interrogation"] = None
    room["votes"] = {}
    set_phase(room_id, "intro")
    logger.info(f"✅ Jogo ativado para sala {room_id}\n")
    
    for p in participantes:
        p["is_killer"] = False
        register_player(room_id, str(p["id"]))
        if p.get("is_bot"):
            init_bot_memory(room_id, p.get("name"), personality=BOT_PERSONALITIES.get(p.get("name"), {}).get("personality", "neutral"))
            logger.info(f"🧠 Memória do Bot {p.get('name')} inicializada na sala {room_id}")

    logger.info(f"🎲 Escolhendo assassino entre {len(participantes)} participantes")
    killer = random.choice(participantes)
    killer["is_killer"] = True
    killer_id = str(killer["id"])
    killer_name = killer.get("name", "Assassino")
    logger.info(f"🔪 Assassino escolhido internamente: {killer.get('name')} ID={killer.get('id')}")
    room["killer_id"] = killer_id
    set_killer_id(room_id, killer_id)
    flush_killer_to_db(room_id, killer_id)
    logger.info(f"[GAME_PHASE] room={room_id} killer_chosen id={killer_id} name={killer_name}")
    if not killer.get("is_bot"):
        await send_private_to_player(room_id, killer_id, {
            "type": "you_are_killer",
            "player_id": killer_id,
            "player_name": killer_name,
            "message": "Você é o ASSASSINO. Elimine os inocentes sem ser condenado.",
            "secret": True,
        })
    
    # Inicializa contador de mortes da rodada
    room["kills_this_round"] = 0
    
    await broadcast(room_id, {"type": "status", "msg": "O Mestre está tecendo a história..."})
    
    # Gerar o caso com randomização
    cenarios = ["Hotel-Cassino", "Mansão", "Praia", "Parque", "Teatro"]
    niveis = ["Iniciante", "Intermediário", "Avançado"]
    
    # Randomiza cenário e nível para cada jogo
    cenario_escolhido = room.get("cenario") or random.choice(cenarios)
    nivel_escolhido = room.get("nivel") or random.choice(niveis)
    
    # Adiciona um ID único para cada caso
    import uuid
    case_id_unique = f"CASE-{uuid.uuid4().hex[:8].upper()}"
    
    print(f"🎲 Gerando caso: {cenario_escolhido} - {nivel_escolhido} (ID: {case_id_unique})")
    
    prompt_dinamico = CREATE_CASE_TEMPLATE.format(
        cenario=cenario_escolhido,
        nivel=nivel_escolhido,
        num_jogadores=num_jogadores
    )
    
    active_provider = get_active_ai_provider()
    # Usa o provedor principal ativo para gerar o caso
    print(f"🔄 Iniciando geração de caso pelo MOTOR MESTRE ({active_provider})...")
    print(f"   Prompt: {prompt_dinamico[:200]}...")
    print(f"   Room ID: {room_id}")
    print(f"   Cenário: {cenario_escolhido}")
    print(f"   Nível: {nivel_escolhido}")
    print(f"   Número de jogadores: {num_jogadores}")
    
    try:
        # Chama o motor mestre para gerar o caso
        logger.info(f"🔄 Chamando generate_case() para sala {room_id}...")
        case_json = await generate_case(prompt_dinamico)
        
        if not case_json:
            raise ValueError("generate_case retornou None ou vazio")
        
        logger.info(f"✅ Resposta do MOTOR MESTRE recebida (tamanho: {len(case_json)} caracteres)")
        logger.debug(f"   Primeiros 300 chars: {case_json[:300]}...")
        
        # ✅ CORREÇÃO: Parsear a string JSON para um objeto Python ANTES de usar
        if isinstance(case_json, str):
            try:
                # Tenta extrair JSON de markdown se necessário
                json_str = case_json
                if '```json' in json_str:
                    match = re.search(r'```json\s*(.*?)\s*```', json_str, re.DOTALL)
                    if match:
                        json_str = match.group(1).strip()
                        logger.info("📝 JSON extraído de bloco markdown")
                
                # Limpar zeros à esquerda de números inteiros para evitar erros de sintaxe JSON
                json_str = re.sub(r'([:\s,\[])0+(\d+)', r'\1\2', json_str)
                
                # Parseia para dict Python
                case_data = json.loads(json_str)
                logger.info(f"✅ Caso parseado de string JSON para objeto Python (tipo: {type(case_data)})")
            except json.JSONDecodeError as e:
                logger.error(f"❌ Erro ao parsear JSON do caso: {e}")
                logger.error(f"   Conteúdo recebido: {case_json[:500]}")
                # Usa extract_json_from_string como fallback
                case_data = extract_json_from_string(case_json, validate_with_pydantic=CaseData)
        elif isinstance(case_json, dict):
            # Já é um dict, usa diretamente
            case_data = case_json
            logger.info("✅ Caso já é um objeto Python (dict)")
        else:
            logger.warning(f"⚠️ Tipo inesperado de case_json: {type(case_json)}")
            case_data = extract_json_from_string(str(case_json), validate_with_pydantic=CaseData)
        
    except Exception as e:
        print(f"❌ Erro ao chamar generate_case (Motor Mestre): {e}")
        print(f"   Tipo do erro: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        
        logger.warning(
            f"⚠️ Falha ao gerar caso com provedor ativo={active_provider}. "
            f"OpenRouter configurado={'sim' if is_openrouter_configured() else 'não'}"
        )
        
        # Usa um caso de fallback
        case_json = json.dumps({
            "case_id": case_id_unique,
            "descricao": "Um mistério foi revelado... Um assassinato ocorreu e você precisa descobrir o culpado.",
            "historia": "A investigação está em andamento. Reúna pistas e descubra a verdade.",
            "local_corpo": cenario_escolhido,
            "arma_crime": "Desconhecida",
            "suspeitos": [],
            "evidencias": []
        })
        logger.warning(f"⚠️ Usando caso de fallback (MOTOR MESTRE não funcionou) para sala {room_id}")
        # ✅ CORREÇÃO: Parsear o fallback também para dict
        case_data = json.loads(case_json)
    
    # ✅ CORREÇÃO: Garantir que case_data seja sempre um dict Python ANTES de usar
    if not isinstance(case_data, dict):
        logger.error(f"❌ case_data não é dict após parse, tipo: {type(case_data)}")
        if isinstance(case_data, str):
            try:
                case_data = json.loads(case_data)
            except:
                case_data = extract_json_from_string(case_data, validate_with_pydantic=CaseData)
        else:
            case_data = extract_json_from_string(str(case_data), validate_with_pydantic=CaseData)
    
    logger.info(f"✅ Caso parseado e validado para sala {room_id} (tipo: {type(case_data)}, case_id: {case_data.get('case_id', 'N/A')})")
    
    # Salva o resumo do caso no game_state (alinhado com a dinâmica: todos são suspeitos, um é assassino)
    case_summary_text = json.dumps(case_data) if isinstance(case_data, dict) else str(case_data)
    set_case_summary(room_id, case_summary_text)
    
    # Extrai pistas básicas do texto do caso (linhas que contêm "pista:")
    case_text = json.dumps(case_data) if isinstance(case_data, dict) else str(case_data)
    for line in case_text.splitlines():
        if "pista:" in line.lower() or "pista" in line.lower():
            pista_extraida = line.strip()
            if pista_extraida:
                add_clue(room_id, pista_extraida)
    
    # Inicializa variável para pistas extraídas
    frases_importantes = []
    
    try:
        # ✅ CORREÇÃO: case_data já é um dict Python, não precisa parsear novamente
        # case_data = extract_json_from_string(case_json, validate_with_pydantic=CaseData)  # REMOVIDO
        
        # 🔍 Extrai pistas automáticas a partir do caso gerado
        historia = case_data.get("historia", "")
        descricao = case_data.get("descricao", "")
        
        # Gera pistas automáticas a partir de palavras-chave
        texto_completo = f"{historia} {descricao}".lower()
        
        for linha in (historia + " " + descricao).split("."):
            linha_lower = linha.lower().strip()
            if any(palavra in linha_lower for palavra in ["encontrado", "pista", "objeto", "vestígio", "sangue", "arma", "pegada", "impressão", "documento", "carta", "nota", "marca", "cicatriz", "tatuagem", "anél", "relógio", "foto", "vídeo"]):
                if len(linha_lower) > 10:  # Ignora frases muito curtas
                    pista_extraida = linha.strip()
                    if pista_extraida and pista_extraida not in frases_importantes:
                        frases_importantes.append(pista_extraida)
                        add_clue(room_id, pista_extraida)
        
        print(f"🔍 {len(frases_importantes)} pistas extraídas automaticamente do caso")
        
        # Garante que case_data seja um dict
        if not isinstance(case_data, dict):
            print(f"⚠️ case_data não é dict, convertendo... Tipo: {type(case_data)}")
            if isinstance(case_data, str):
                try:
                    case_data = json.loads(case_data)
                except:
                    case_data = {"descricao": case_data[:500]}
        
        # Garante que o case_id seja único
        if not case_data.get("case_id") or case_data.get("case_id") == "ERRO":
            case_data["case_id"] = case_id_unique
        case_data["nivel"] = nivel_escolhido
        case_data["cenario"] = cenario_escolhido
        
        # Garante que todos os campos necessários existam
        if "descricao" not in case_data:
            case_data["descricao"] = case_data.get("descricao", "Um mistério foi revelado...")
        if "historia" not in case_data:
            case_data["historia"] = case_data.get("historia", "")
        if "local_corpo" not in case_data:
            case_data["local_corpo"] = case_data.get("local_corpo", "")
        if "arma_crime" not in case_data:
            case_data["arma_crime"] = case_data.get("arma_crime", "")
        if "suspeitos" not in case_data:
            case_data["suspeitos"] = case_data.get("suspeitos", [])
        if "evidencias" not in case_data:
            case_data["evidencias"] = case_data.get("evidencias", [])
            
        print(f"✅ Caso gerado com sucesso: {case_data.get('case_id')}")
        print(f"   Descrição: {case_data.get('descricao', '')[:100]}...")
        
    except Exception as e:
        print(f"❌ Erro ao processar caso: {e}")
        print(f"   case_json (primeiros 500 chars): {case_json[:500]}")
        # Cria um caso de fallback
        case_data = {
            "case_id": case_id_unique,
            "nivel": nivel_escolhido,
            "cenario": cenario_escolhido,
            "descricao": "Um mistério foi revelado... Um assassinato ocorreu e você precisa descobrir o culpado.",
            "historia": case_json[:1000] if len(case_json) > 0 else "História do caso em análise...",
            "local_corpo": cenario_escolhido,
            "arma_crime": "Desconhecida",
            "suspeitos": [],
            "evidencias": []
        }
    
    # SALVAR NA SALA (Importante para quem entrar depois)
    room["case"] = case_data 

    # Atualiza o game_state com o resumo formatado do caso
    case_summary = f"{case_data.get('descricao', '')} {case_data.get('historia', '')}"
    set_case_summary(room_id, case_summary)
    
    # Envia mensagem tipo "caso" com o caso processado (já como objeto JSON)
    # IMPORTANTE: Envia como string JSON para o handler "caso" no frontend
    await broadcast(room_id, {
        "type": "caso",
        "text": json.dumps(case_data)  # Envia como JSON string do objeto processado
    })
    
    # Log para debug
    print(f"📤 Mensagem 'caso' enviada (tipo: caso, text: JSON string)")
    
    # Adiciona evidências iniciais ao game_state, propaga para bots e envia como pistas
    evidencias = case_data.get("evidencias", [])
    for evidencia in evidencias:
        add_clue(room_id, evidencia)
        for p in participantes:
            if isinstance(p, dict) and (p.get("is_bot") or p.get("isBot")):
                add_clue_to_bot(room_id, p.get("name"), evidencia)
        # Envia pista inicial como mensagem tipo "pista"
        await broadcast(room_id, {
            "type": "pista",
            "text": evidencia
        })
    
    # Envia pistas extraídas automaticamente e propaga para bots
    for pista in frases_importantes:
        for p in participantes:
            if isinstance(p, dict) and (p.get("is_bot") or p.get("isBot")):
                add_clue_to_bot(room_id, p.get("name"), pista)
        await broadcast(room_id, {
            "type": "pista",
            "text": pista
        })

    # Validação final: garante que case_data seja um dict válido antes de enviar
    if not isinstance(case_data, dict):
        print(f"⚠️ case_data não é dict antes de enviar, tipo: {type(case_data)}")
        if isinstance(case_data, str):
            try:
                case_data = json.loads(case_data)
                print(f"✅ case_data convertido de string para dict")
            except Exception as e:
                print(f"⚠️ Erro ao converter: {e}")
                case_data = {"descricao": case_data[:500]}
        else:
            case_data = {
                "case_id": case_id_unique,
                "descricao": str(case_data)[:500] if case_data else "Um mistério foi revelado...",
                "historia": "",
                "local_corpo": cenario_escolhido,
                "arma_crime": "",
                "suspeitos": [],
                "evidencias": []
            }
    
    print(f"📤 Enviando caso para jogadores (case_id: {case_data.get('case_id')})")
    print(f"   Tipo: {type(case_data)}, Keys: {list(case_data.keys())[:5] if isinstance(case_data, dict) else 'N/A'}...")

    # ✅ CORREÇÃO: Garantir que case_data seja um dict Python antes de enviar
    if not isinstance(case_data, dict):
        logger.error(f"❌ case_data não é dict antes de game_start, tipo: {type(case_data)}")
        if isinstance(case_data, str):
            try:
                case_data = json.loads(case_data)
            except:
                case_data = {"descricao": case_data[:500]}
        else:
            case_data = {"descricao": str(case_data)[:500]}
    
    # ✅ CORREÇÃO: Enviar game_start com dados estruturados e completos
    game_start_payload = {
        "type": "game_start",
        "status": "game_started",
        "phase": "intro",
        "case": case_data,  # ✅ Dict Python, não string JSON
        "players": [
            {
                "id": str(p.get("id")),
                "nickname": p.get("name", "Jogador"),
                "name": p.get("name", "Jogador"),
                "numeric_id": p.get("numeric_id"),
                "status": p.get("status", "alive"),
                "is_alive": p.get("status") == "alive",
                "is_bot": p.get("is_bot", False),
                "isBot": p.get("is_bot", False),
                "is_connected": p.get("is_connected", True)
            }
            for p in participantes if isinstance(p, dict)
        ],
        "current_turn_player_id": str(get_current_turn(room_id) or ""),
        "game_duration_minutes": 120,
        "timestamp": time.time()
    }
    
    logger.info(f"📤 Enviando game_start para {len(participantes)} jogadores em {room_id}")
    await broadcast(room_id, game_start_payload)
    
    logger.info(f"✅ Mensagem 'game_start' enviada com sucesso (case_id: {case_data.get('case_id', 'N/A')})")
    set_phase(room_id, "investigation")

    # 2. Inicia a sequência de turnos com controle de tempo
    game_start_time = time.time()
    game_min_duration = 0
    game_max_duration = 120 * 60  # 120 minutos em segundos
    turn_timeout = 60  # 1 minuto por turno
    
    room["game_start_time"] = game_start_time
    room["game_min_duration"] = game_min_duration
    room["game_max_duration"] = game_max_duration
    room["current_turn"] = 0
    room["round_number"] = 0
    
    while room.get("game_active", False):
        # Verifica tempo total do jogo
        elapsed_time = time.time() - game_start_time
        
        # Se passou do tempo máximo, força fim do jogo
        if elapsed_time >= game_max_duration:
            await broadcast(room_id, {
                "type": "game_end",
                "winner": "tempo_esgotado",
                "winner_name": "Tempo máximo atingido",
                "reason": "O jogo atingiu o tempo máximo de 120 minutos."
            })
            room["game_active"] = False
            break
        
        participantes = room.get("players", participantes)
        alive_players = get_alive_players(room)
        if not alive_players:
            break
            
        # Pega o jogador da vez pelo índice central
        idx = room.get("current_turn", 0)
        if idx >= len(participantes):
            idx = 0
            room["current_turn"] = 0
            
        # Controla o número de rodadas e reseta mortes no início de cada rodada
        if idx == 0:
            round_number = room.get("round_number", 0) + 1
            room["round_number"] = round_number
            room["kills_this_round"] = 0  # Reset contador de mortes por rodada
            
        player_data = participantes[idx]
        
        # Pula se o jogador estiver morto
        if isinstance(player_data, dict) and player_data.get("status") == "dead":
            room["current_turn"] = (idx + 1) % len(participantes)
            continue
            
        # Verifica se é um bot
        is_bot = player_data.get("isBot", False) if isinstance(player_data, dict) else False
        player_name = player_data.get("name", f"Jogador {idx+1}") if isinstance(player_data, dict) else str(player_data)
        is_killer = player_data.get("is_killer", False) if isinstance(player_data, dict) else False
        
        player_identifier = str(player_data.get("id")) if isinstance(player_data, dict) else str(idx + 1)
        player_id = player_identifier

        # Atualiza o turno atual no game_state (sempre como string)
        room["current_turn_player_id"] = player_identifier
        set_current_turn(room_id, player_identifier)
        flush_turn_to_db(room_id, player_identifier)
        set_phase(room_id, "turn")
        
        # Verifica se já passou o tempo mínimo
        can_end_game = elapsed_time >= game_min_duration
        game_time_remaining = max(0, game_max_duration - elapsed_time)
        
        if not player_identifier:
            player_identifier = str(player_id) if player_id else player_name
            logger.warning(f"⚠️ player_identifier estava vazio, definido para {player_identifier}")
            
        # Envia início de turno
        turn_payload = {
            "type": "turn_start",
            "phase": "turn",
            "turnoAtual": str(player_identifier),
            "player": player_name,
            "player_name": player_name,
            "player_id": str(player_id),
            "player_identifier": str(player_identifier),
            "turn_index": idx,
            "time_limit": turn_timeout,
            "game_time_remaining": int(game_time_remaining),
            "game_elapsed_time": int(elapsed_time),
            "can_end_game": can_end_game,
            "is_bot": is_bot,
            "is_killer": is_killer
        }
        
        logger.info(f"📤 Enviando turn_start: turnoAtual={turn_payload['turnoAtual']}, player={player_name}")
        logger.info(f"[TURN] room={room_id} player_id={player_identifier} name={player_name}")
        await broadcast(room_id, turn_payload)
        
        await broadcast(room_id, {
            "type": "turno",
            "player_id": str(player_identifier)
        })
        
        # Se for bot:
        if is_bot:
            if is_killer:
                # Bot assassino decide se mata (30% de chance se houver alvos)
                alive_targets = [p for p in participantes if isinstance(p, dict) and
                                p.get("status") == "alive" and not p.get("is_killer")]
                if alive_targets and random.random() < 0.3:
                    # Uses strategy from bot memory
                    target = select_bot_kill_target(room_id, player_name, alive_targets)
                    if target:
                        target_id = target.get("id") if isinstance(target, dict) else str(target)
                        result = await kill_player(room_id, player_identifier, target_id)
                        if result.get("success"):
                            await asyncio.sleep(2)  # Pausa dramática
                            
            # Processa o turno do bot de forma síncrona
            await process_bot_turn(room_id, idx, player_data)
            
            # Avança o turno e continua
            room["current_turn"] = (idx + 1) % len(participantes)
            continue
            
        # Se for jogador humano, aguarda ação (1 minuto de timeout)
        if room_id in GAME_EVENTS:
            GAME_EVENTS[room_id]["player_action_event"].clear()
            turn_start_time = time.time()
            
            # Envia atualizações de tempo a cada 10 segundos
            async def send_time_updates():
                while time.time() - turn_start_time < turn_timeout:
                    await asyncio.sleep(10)
                    if not room.get("game_active", False):
                        break
                    elapsed_turn = time.time() - turn_start_time
                    remaining_turn = max(0, turn_timeout - elapsed_turn)
                    elapsed_game = time.time() - game_start_time
                    remaining_game = max(0, game_max_duration - elapsed_game)
                    
                    await broadcast(room_id, {
                        "type": "time_update",
                        "turn_time_remaining": int(remaining_turn),
                        "game_time_remaining": int(remaining_game),
                        "game_elapsed_time": int(elapsed_game),
                        "can_end_game": elapsed_game >= game_min_duration
                    })
            
            # Inicia task de atualização de tempo
            time_update_task = asyncio.create_task(send_time_updates())
            
            try:
                while room.get("game_active", False):
                    wait_timeout = turn_timeout if room.get("phase") == "turn" else 90
                    await asyncio.wait_for(
                        GAME_EVENTS[room_id]["player_action_event"].wait(),
                        timeout=wait_timeout
                    )
                    break
                time_update_task.cancel()  # Cancela atualizações se o jogador agiu
            except asyncio.TimeoutError:
                time_update_task.cancel()
                if room.get("phase") == "turn":
                    await broadcast(room_id, {
                        "type": "time_out", 
                        "player": player_name,
                        "turn_index": idx,
                        "message": f"⏰ {player_name} não agiu a tempo. Turno passado automaticamente."
                    })
                    add_chat_message(room_id, "Sistema", f"⏰ {player_name} não agiu a tempo. Turno passado automaticamente.")
                else:
                    logger.warning(f"[TURN] room={room_id} phase={room.get('phase')} exceeded expected phase timeout; forcing next turn")
                    set_phase(room_id, "turn")
                
        # Se o jogador se desconectou durante o turno dele
        if not player_data.get("is_connected", True):
            logger.info(f"⏭️ Turno de {player_name} encerrado devido à desconexão.")
            
        # Verifica condições de vitória após cada ação/timeout
        win_check = await check_win_conditions(room_id)
        if win_check.get("game_ended"):
            await finish_game(room_id, win_check)
            break
                
        # Avança para o próximo jogador
        room["current_turn"] = (idx + 1) % len(participantes)

    room["game_active"] = False


@app.websocket("/ws/{room_id}")
async def ws_room(websocket: WebSocket, room_id: str):
    token = websocket.query_params.get("token")
    user_email = None
    user_nickname = None
    if token:
        payload = decode_access_token(token)
        if payload:
            user_email = payload.get("sub")
            # Busca nickname do usuário no banco
            from database import SessionLocal
            from models import User
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.email == user_email).first()
                if user and user.nickname:
                    user_nickname = user.nickname
            finally:
                db.close()

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
            "room_id": room_id,
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
    
    # ✅ CORREÇÃO: Garantir que player_identifier seja sempre string
    player_identifier = str(user_nickname or (user_email.split("@")[0] if user_email else f"Jogador {len(room.get('players', [])) + 1}"))
    
    logger.info(f"🔌 WebSocket conectado: {websocket.client.host if websocket.client else 'N/A'}:{websocket.client.port if websocket.client else 'N/A'} para sala {room_id}, player: {player_identifier}")
    
    # Verifica se o jogador já está na lista
    existing_player = None
    player_numeric_id = None
    for idx, p in enumerate(room.get("players", [])):
        if isinstance(p, dict):
            if str(p.get("name", "")) == player_identifier or str(p.get("id", "")) == player_identifier:
                existing_player = p
                # ✅ Extrair ID numérico do jogador existente
                player_numeric_id = p.get("numeric_id", idx + 1)
                break
    
    # Se não existe, adiciona à lista
    if not existing_player:
        # ✅ CORREÇÃO: Criar ID numérico baseado no índice (1, 2, 3, ...)
        player_numeric_id = len(room.get("players", [])) + 1
        player_data = {
            "id": str(player_numeric_id),
            "name": str(player_identifier),  # ✅ Nome do jogador
            "numeric_id": player_numeric_id,  # ✅ ID NUMÉRICO (1, 2, 3, ...)
            "status": "alive",
            "isBot": False,
            "is_bot": False,
            "is_killer": False,
            "is_connected": True,
            "email": user_email
        }
        if "players" not in room:
            room["players"] = []
        room["players"].append(player_data)
        logger.info(f"✅ Jogador {player_identifier} adicionado à sala {room_id} com ID numérico: {player_numeric_id}")
    else:
        # ✅ CORREÇÃO: Se o jogador já existe, marca como reconectado
        existing_player["is_connected"] = True
        existing_player["disconnect_time"] = None
        # Garante que tem numeric_id
        if "numeric_id" not in existing_player:
            existing_player["numeric_id"] = player_numeric_id or (room.get("players", []).index(existing_player) + 1)
        player_numeric_id = existing_player.get("numeric_id", player_numeric_id)
        logger.info(f"🔄 Jogador {player_identifier} reconectado na sala {room_id} com ID numérico: {player_numeric_id}")
    CONNECTION_PLAYERS.setdefault(room_id, {})[id(websocket)] = {
        "id": str(existing_player.get("id") if existing_player else player_data.get("id")),
        "name": str(player_identifier),
    }
    
    # Registra o jogador no game_state
    register_player(room_id, player_identifier)
    
    # Notifica todos os jogadores sobre a atualização da lista
    await broadcast(room_id, {
        "type": "players_update",
        "players": to_public_players(room.get("players", [])),
        "new_player": player_identifier
    })
    
    # Envia lista atualizada de jogadores usando a nova função
    await broadcast_players(room_id)
    
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
                "player_id": player_identifier,
                "game_active": True
            }
        }))
    
    # ✅ CORREÇÃO: Enviar player_id NUMÉRICO no "hello"
    # Garante que player_numeric_id está definido
    if player_numeric_id is None:
        # Busca o ID numérico do jogador na lista
        for idx, p in enumerate(room.get("players", [])):
            if isinstance(p, dict) and (str(p.get("name", "")) == player_identifier or str(p.get("id", "")) == player_identifier):
                player_numeric_id = p.get("numeric_id", idx + 1)
                break
        if player_numeric_id is None:
            player_numeric_id = len(room.get("players", []))
    
    # Envia estado inicial com lista de jogadores
    await websocket.send_text(json.dumps({
        "type": "hello",
        "payload": {
            "room_id": room_id,
            "player_id": player_numeric_id,  # ✅ ID NUMÉRICO (1, 2, 3, ...)
            "player_name": player_identifier,  # ✅ Nome do jogador
            "players": len(CONNECTIONS[room_id]),
            "total_players": len(room.get("players", [])),
            "case": room.get("case"),
            "current_turn": room.get("current_turn", 0),
            "game_active": room.get("game_active", False)
        },
        "players_list": to_public_players(room.get("players", []))  # Envia lista completa de jogadores (sanitizada)
    }))
    
    logger.info(f"✅ Hello enviado com player_id numérico: {player_numeric_id} para {player_identifier}")

    connected_player = existing_player if existing_player else player_data
    if room.get("game_active") and connected_player and connected_player.get("is_killer") and not connected_player.get("is_bot"):
        await websocket.send_text(json.dumps({
            "type": "you_are_killer",
            "player_id": str(connected_player.get("id")),
            "player_name": connected_player.get("name", player_identifier),
            "message": "Você é o ASSASSINO. Elimine os inocentes sem ser condenado.",
            "secret": True,
        }))
    
    # Envia atualização de jogadores para sincronizar
    await broadcast(room_id, {
        "type": "players_update",
        "players": to_public_players(room.get("players", [])),
        "new_player": player_identifier
    })
    
    try:
        while True:
            msg = await websocket.receive_text()
            try:
                data = json.loads(msg)
                msg_type = data.get("type")
                
                if msg_type == "start":
                    logger.info(f"📨 Recebido 'start' de {player_identifier} na sala {room_id}. Iniciando game_loop process.")
                    
                    # ✅ Valida que a sala existe
                    if room_id not in ROOMS:
                        await websocket.send_json({
                            "type": "error",
                            "message": "Sala não encontrada"
                        })
                        continue
                    
                    # Recebe a lista de jogadores (incluindo bots) do frontend
                    players_data = data.get("players", [])
                    if players_data:
                        room["players"] = normalize_players(players_data)
                        logger.info(f"🎮 Jogadores recebidos: {len(players_data)} ({sum(1 for p in players_data if p.get('isBot')) } bots)")
                    
                    num_atual = len(room.get("players", []))
                    
                    # ✅ CORREÇÃO: Validar número mínimo de jogadores
                    if num_atual < 3:
                        await websocket.send_json({
                            "type": "error", 
                            "message": f"Mínimo de 3 jogadores necessário. Atual: {num_atual}"
                        })
                        continue
                    
                    # ✅ CORREÇÃO: Enviar confirmação ANTES de iniciar
                    await websocket.send_json({
                        "type": "game_starting",
                        "message": "Jogo iniciando em 2 segundos...",
                        "status": "preparing"
                    })
                    
                    # Notifica todos os jogadores
                    await broadcast(room_id, {
                        "type": "game_starting",
                        "message": f"🎮 {player_identifier} iniciou o jogo! Preparando...",
                        "status": "preparing"
                    })
                    
                    # Aguardar 2 segundos para garantir que frontend recebeu
                    await asyncio.sleep(2)
                    
                    # ✅ AGORA iniciar o jogo
                    try:
                        logger.info(f"🎮 Iniciando game_loop para sala {room_id}")
                        asyncio.create_task(game_loop(room_id))
                        logger.info(f"✅ Task game_loop criada com sucesso para sala {room_id}")
                    except Exception as e:
                        logger.exception(f"❌ Erro crítico ao iniciar game_loop para sala {room_id}: {e}")
                        await broadcast(room_id, {
                            "type": "error",
                            "message": f"Erro interno ao iniciar jogo: {str(e)[:100]}"
                        })
                
                elif msg_type == "kill_player" or msg_type == "kill":
                    # Ação de assassinar um jogador
                    target_id = data.get("target_id") or data.get("target")
                    
                    # Identifica o jogador atual
                    if user_nickname:
                        player_identifier = user_nickname
                    elif user_email:
                        player_identifier = user_email.split("@")[0]
                    else:
                        player_identifier = player_identifier or f"Jogador {len(room.get('players', []))}"
                    
                    # Verifica se é o turno do jogador antes de processar
                    actor_id = resolve_player_id(room, player_identifier)
                    is_turn, turn_error_msg = is_player_turn(room_id, actor_id)
                    if not is_turn:
                        await websocket.send_text(json.dumps({
                            "type": "error", 
                            "msg": turn_error_msg
                        }))
                        continue
                    
                    result = await kill_player(room_id, actor_id, target_id)
                    
                    if result.get("success"):
                        await websocket.send_text(json.dumps({
                            "type": "kill_success",
                            "message": result.get("message"),
                            "clue": result.get("clue")
                        }))
                    else:
                        await websocket.send_text(json.dumps({
                            "type": "kill_error",
                            "message": result.get("message", "Erro ao executar assassinato")
                        }))
                
                elif msg_type == "acusar" or (msg_type == "action" and data.get("action") == "acusar"):
                    # Ação de acusar um suspeito
                    accused_id = resolve_player_id(room, data.get("target") or data.get("target_id") or data.get("accused"))
                    
                    if not accused_id:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "msg": "⛔ Você precisa especificar quem está acusando."
                        }))
                        continue
                    
                    # Identifica o jogador atual
                    if user_nickname:
                        player_identifier = user_nickname
                    elif user_email:
                        player_identifier = user_email.split("@")[0]
                    else:
                        player_identifier = player_identifier or f"Jogador {len(room.get('players', []))}"
                    
                    actor_id = resolve_player_id(room, player_identifier)
                    result = await start_accusation(room_id, actor_id, accused_id)
                    if not result.get("success"):
                        await websocket.send_text(json.dumps({"type": "error", "msg": result.get("message")}))
                
                elif msg_type == "voto" or msg_type == "vote":
                    vote = data.get("value") or data.get("vote")
                    # Identifica o jogador atual
                    if user_nickname:
                        player_identifier = user_nickname
                    elif user_email:
                        player_identifier = user_email.split("@")[0]
                    else:
                        player_identifier = player_identifier or f"Jogador {len(room.get('players', []))}"
                    
                    actor_id = resolve_player_id(room, player_identifier)
                    result = await register_vote(room_id, actor_id, vote)
                    if not result.get("success"):
                        await websocket.send_text(json.dumps({"type": "error", "msg": result.get("message")}))

                elif msg_type == "pass_turn" or msg_type == "passar_vez":
                    # Identifica o jogador atual
                    if user_nickname:
                        player_identifier = user_nickname
                    elif user_email:
                        player_identifier = user_email.split("@")[0]
                    else:
                        player_identifier = player_identifier or f"Jogador {len(room.get('players', []))}"
                        
                    # Verifica se é o turno do jogador
                    actor_id = resolve_player_id(room, player_identifier)
                    is_turn, turn_error_msg = is_player_turn(room_id, actor_id)
                    if not is_turn:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "msg": turn_error_msg
                        }))
                        continue
                        
                    logger.info(f"⏭️ Jogador {player_identifier} passou a vez na sala {room_id}")
                    if room_id in GAME_EVENTS:
                        GAME_EVENTS[room_id]["player_action_event"].set()

                elif msg_type == "interrogar":
                    target_id = resolve_player_id(room, data.get("target") or data.get("target_id"))
                    question_text = data.get("question")
                    
                    if not target_id or not question_text:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "msg": "⛔ Você precisa especificar quem está interrogando e qual é a pergunta."
                        }))
                        continue
                        
                    # Identifica o jogador atual
                    if user_nickname:
                        player_identifier = user_nickname
                    elif user_email:
                        player_identifier = user_email.split("@")[0]
                    else:
                        player_identifier = player_identifier or f"Jogador {len(room.get('players', []))}"
                        
                    actor_id = resolve_player_id(room, player_identifier)
                    result = await start_interrogation_phase(room_id, actor_id, target_id, question_text)
                    if not result.get("success"):
                        await websocket.send_text(json.dumps({"type": "error", "msg": result.get("message")}))
                        continue

                    add_chat_message(room_id, actor_id, f"🔍 (Interrogando {target_id}) {question_text}")
                    room.setdefault("chat", []).append({
                        "player": _player_public_name(room, actor_id),
                        "text": f"🔍 (Interrogando {target_id}) {question_text}",
                        "timestamp": datetime.now().isoformat()
                    })

                elif msg_type == "resposta_interrogatorio":
                    # Identifica o jogador atual
                    if user_nickname:
                        player_identifier = user_nickname
                    elif user_email:
                        player_identifier = user_email.split("@")[0]
                    else:
                        player_identifier = player_identifier or f"Jogador {len(room.get('players', []))}"
                        
                    actor_id = resolve_player_id(room, player_identifier)
                    active_interrogation = room.get("active_interrogation")
                    target_id = active_interrogation.get("target_id") if active_interrogation else None
                    
                    # Verifica se este jogador é de fato o alvo do interrogatório ativo
                    if not target_id or str(target_id) != str(actor_id):
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "msg": "⛔ Você não é o alvo do interrogatório ativo no momento."
                        }))
                        continue
                        
                    response_text = data.get("message") or data.get("text")
                    if not response_text:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "msg": "⛔ A resposta não pode ser vazia."
                        }))
                        continue
                        
                    await submit_interrogation_result(room_id, actor_id, response_text)

                elif msg_type == "defesa_acusacao":
                    actor_id = resolve_player_id(room, player_identifier)
                    defense_text = data.get("message") or data.get("text")
                    if not defense_text:
                        await websocket.send_text(json.dumps({"type": "error", "msg": "⛔ A defesa não pode ser vazia."}))
                        continue
                    result = await submit_defense(room_id, actor_id, defense_text)
                    if not result.get("success"):
                        await websocket.send_text(json.dumps({"type": "error", "msg": result.get("message")}))
                
                elif msg_type == "message" or msg_type == "action":
                    # Processa mensagem de chat ou ação do jogador
                    
                    # Identifica o jogador atual
                    if user_nickname:
                        sender_label = user_nickname
                        player_identifier = user_nickname
                    elif user_email:
                        sender_label = user_email.split("@")[0]
                        player_identifier = user_email.split("@")[0]
                    else:
                        sender_label = player_identifier or f"Jogador {len(room.get('players', []))}"
                        if not player_identifier:
                            player_identifier = sender_label
                    
                    # Verifica se o jogador está morto
                    actor_id = resolve_player_id(room, player_identifier)
                    actor_player = get_player_by_id(room, actor_id)
                    if not actor_player or actor_player.get("status") != "alive":
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "msg": "Você está morto e não pode mais interagir!"
                        }))
                        continue
                    
                    message_text = data.get("text") or data.get("content", "Realizou uma ação")
                    
                    # Adiciona ao histórico do chat da sala (sem indicar se é bot ou humano)
                    if room_id in ROOMS:
                        ROOMS[room_id].setdefault("chat", []).append({
                            "player": sender_label,
                            "text": message_text,
                            "timestamp": datetime.now().isoformat()
                        })
                    
                    # Atualiza o game_state com a mensagem (garante que room_id está correto)
                    if room_id and room_id in ROOMS:
                        add_chat_message(room_id, sender_label, message_text)
                    else:
                        print(f"⚠️ room_id inválido ao adicionar mensagem: {room_id}")
                    
                    # Verifica se o jogador está morto
                    is_dead = bool(actor_player and actor_player.get("status") == "dead")
                    
                    # Broadcast para todos os jogadores (sem indicar se é bot ou humano)
                    await broadcast(room_id, {
                        "type": "player_message",
                        "player": sender_label,
                        "message": message_text,
                        "dead": is_dead
                    })
                    
                    # 🔸 Bot entra em ação após cada mensagem recebida (se houver bots na sala)
                    if room_id in ROOMS:
                        room = ROOMS[room_id]
                        players = room.get("players", [])
                        # Verifica se há bots na sala
                        bots_in_room = [p for p in players if isinstance(p, dict) and (p.get("isBot") or p.get("is_bot"))]
                        
                        if bots_in_room and room.get("game_active", False):
                            # Seleciona um bot aleatório para responder (30% de chance)
                            if random.random() < 0.3:  # 30% de chance de um bot responder
                                responding_bot = random.choice(bots_in_room)
                                bot_name = responding_bot.get("name", "Bot")
                                
                                # Obtém contexto do caso e pistas
                                case_data = room.get("case", {})
                                case_summary = get_case_summary(room_id)
                                if not case_summary:
                                    # Cria resumo do caso se não existir
                                    case_summary = f"{case_data.get('descricao', '')} {case_data.get('historia', '')}"
                                    set_case_summary(room_id, case_summary)
                                
                                clues = get_clues(room_id)
                                chat_history = get_chat_history(room_id)
                                
                                # Prepara contexto completo para o bot
                                context = {
                                    "case_description": case_data.get("descricao", ""),
                                    "case_history": case_data.get("historia", ""),
                                    "case_location": case_data.get("local_corpo", ""),
                                    "case_weapon": case_data.get("arma_crime", ""),
                                    "chat_history": room.get("chat", []),
                                    "evidences": case_data.get("evidencias", []),
                                    "suspects": case_data.get("suspeitos", [])
                                }
                                
                                # Aguarda um tempo aleatório antes de responder (1-3 segundos)
                                await asyncio.sleep(random.uniform(1, 3))
                                
                                # Gera resposta do bot usando OpenRouter
                                try:
                                    room["room_id"] = room_id
                                    bot_reply, ai_meta = await _generate_bot_text(
                                        responding_bot,
                                        room,
                                        question=f"Jogador {sender_label} disse: {message_text}",
                                        context={**context, "room_id": room_id, "phase": room.get("phase", "turn")},
                                        purpose="reply",
                                    )
                                    
                                    # Adiciona ao histórico do chat (sem indicar que é bot)
                                    if room_id in ROOMS:
                                        ROOMS[room_id].setdefault("chat", []).append({
                                            "player": bot_name,
                                            "text": bot_reply,
                                            "timestamp": datetime.now().isoformat()
                                        })
                                    
                                    # Atualiza game_state
                                    add_chat_message(room_id, bot_name, bot_reply)
                                    
                                    # Verifica se o bot está morto
                                    bot_status = get_player_status(room_id, bot_name)
                                    is_bot_dead = bot_status == "dead"
                                    
                                    # Envia resposta do bot como mensagem normal (todos são suspeitos)
                                    await broadcast(room_id, {
                                        "type": "player_message",  # Trata como mensagem normal
                                        "player": bot_name,
                                        "message": bot_reply,
                                        "dead": is_bot_dead,
                                        "ai_source": ai_meta.get("source"),
                                        "ai_model": ai_meta.get("model")
                                    })
                                except Exception as e:
                                    print(f"❌ Erro ao gerar resposta do bot {bot_name}: {e}")
            except Exception as e:
                # Se for texto puro, encapsula no padrão
                if user_nickname:
                    sender_label = user_nickname
                elif user_email:
                    sender_label = user_email.split("@")[0]
                else:
                    sender_label = player_identifier or f"Suspeito {len(room.get('players', []))}"
                    if not player_identifier:
                        player_identifier = sender_label
                await broadcast(room_id, {
                    "type": "chat",
                    "player_id": sender_label,
                    "content": msg
                })
    except WebSocketDisconnect:
        logger.info(f"🔌 WebSocket desconectado: {player_identifier} da sala {room_id}")
        
        if websocket in CONNECTIONS.get(room_id, []):
            CONNECTIONS[room_id].remove(websocket)
        CONNECTION_PLAYERS.get(room_id, {}).pop(id(websocket), None)
        
        # Marca jogador como "away" em vez de remover completamente
        room = ROOMS.get(room_id)
        if room:
            players = room.get("players", [])
            disconnected_player = None
            
            for p in players:
                if isinstance(p, dict):
                    if p.get("name") == player_identifier or p.get("email") == user_email:
                        disconnected_player = p
                        # Marca como desconectado, mas mantém na lista
                        p["is_connected"] = False
                        p["disconnect_time"] = time.time()
                        p["status"] = p.get("status", "alive")  # Mantém status (alive/dead)
                        break
            
            # Se for o turno dele, passa para o próximo
            current_turn_id = get_current_turn(room_id)
            if disconnected_player and current_turn_id:
                player_id_str = str(disconnected_player.get("id") or disconnected_player.get("name", ""))
                if str(current_turn_id).lower() == player_id_str.lower():
                    logger.info(f"⏭️ Jogador {player_identifier} desconectou durante seu turno. Passando para próximo.")
                    # ✅ CORREÇÃO: Avança o turno de fato
                    await broadcast(room_id, {
                        "type": "player_disconnected",
                        "player": player_identifier,
                        "message": f"⚠️ {player_identifier} desconectou. Turno será passado."
                    })
                    # Avança para o próximo jogador vivo
                    await advance_turn_on_disconnect(room_id)
            
            # Notifica todos sobre a desconexão (mas não remove)
            await broadcast(room_id, {
                "type": "players_update",
                "players": to_public_players(room.get("players", [])),
                "disconnected_player": player_identifier
            })
            
            # Envia lista atualizada de jogadores
            await broadcast_players(room_id)
        if not CONNECTIONS[room_id]:  # Remove sala vazia
            del CONNECTIONS[room_id]
            if room_id in GAME_EVENTS:
                del GAME_EVENTS[room_id]
            if room_id in CONNECTION_PLAYERS:
                del CONNECTION_PLAYERS[room_id]
            room["game_active"] = False


if __name__ == "__main__":
    import uvicorn  # pyright: ignore[reportMissingImports]
    # Railway fornece a porta via variável de ambiente PORT
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
