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
from groq import Groq  # pyright: ignore[reportMissingImports]
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
    clear_vote
)

# 👇 CLIENTE GROQ CONFIGURADO COM SUA CHAVE
# Inicializa o cliente Groq apenas se a chave estiver disponível
_groq_case_client = None

def get_groq_case_client():
    """Obtém ou cria o cliente Groq para geração de casos"""
    global _groq_case_client
    if _groq_case_client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY não encontrada no ambiente")
        _groq_case_client = Groq(api_key=api_key)
    return _groq_case_client

async def generate_case(prompt_template: str = None):
    """
    Gera um caso de assassinato usando IA via provedor configurado (Groq, DeepSeek ou OpenRouter).
    Usa os prompts SYSTEM_GAME_MASTER e CREATE_CASE_TEMPLATE.
    O provedor é escolhido via variável de ambiente AI_PROVIDER.
    """
    try:
        # Logging detalhado
        logger.info(f"🔄 Iniciando geração de caso...")
        
        # Usa o prompt fornecido ou o template padrão
        user_prompt = prompt_template or CREATE_CASE_TEMPLATE
        
        # Determina qual provedor usar
        provider = os.getenv("AI_PROVIDER", "groq").lower()
        
        if provider == "openrouter":
            # Usa OpenRouter
            api_key = os.getenv("OPENROUTER_API_KEY", "")
            if not api_key:
                raise ValueError("OPENROUTER_API_KEY não encontrada no ambiente")
            logger.info(f"🔄 Gerando caso com OpenRouter...")
            model = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct")
            logger.info(f"   Modelo: {model}")
            
            client = get_openrouter_client()
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    client.chat.completions.create,
                    model=model,
                    messages=[
                        {"role": "system", "content": SYSTEM_GAME_MASTER},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.8,
                    max_tokens=2000
                ),
                timeout=30.0  # Timeout aumentado para OpenRouter
            )
        elif provider == "deepseek":
            # Usa DeepSeek
            api_key = os.getenv("DEEPSEEK_API_KEY", "")
            if not api_key:
                raise ValueError("DEEPSEEK_API_KEY não encontrada no ambiente")
            logger.info(f"🔄 Gerando caso com DeepSeek...")
            
            client = get_deepseek_client()
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    client.chat.completions.create,
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": SYSTEM_GAME_MASTER},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.8,
                    max_tokens=2000
                ),
                timeout=30.0
            )
        else:
            # Usa Groq (padrão)
            api_key = os.getenv("GROQ_API_KEY", "")
            if not api_key:
                raise ValueError("GROQ_API_KEY não encontrada no ambiente")
            logger.info(f"🔄 Gerando caso com Groq (modelo: llama-3.3-70b-versatile)...")
            
            client = get_groq_case_client()
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    client.chat.completions.create,
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": SYSTEM_GAME_MASTER},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.8,
                    max_tokens=2000
                ),
                timeout=15.0
            )
        
        result = response.choices[0].message.content
        logger.info(f"✅ Caso gerado com sucesso: {len(result)} chars")
        
        # ✅ Limpa JSON se necessário (remove markdown backticks)
        result_clean = clean_json_response(result)
        logger.info(f"✅ JSON limpo: {len(result_clean)} chars")
        
        return result_clean
        
    except asyncio.TimeoutError:
        logger.error(f"⏱️ Timeout na API {provider.upper()}")
        return generate_fallback_case()
    except Exception as e:
        logger.error(f"❌ Erro ao gerar caso: {str(e)}", exc_info=True)
        return generate_fallback_case()


def generate_fallback_case():
    """Gera um caso básico de fallback"""
    try:
        fallback_result = ai_generate(CREATE_CASE_TEMPLATE, system=SYSTEM_GAME_MASTER)
        logger.info(f"✅ Usando fallback, resultado gerado (tamanho: {len(fallback_result)} caracteres)")
        return fallback_result
    except Exception as e2:
        logger.error(f"❌ Erro no fallback também: {e2}")
        # Retorna um caso básico de emergência
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
    allow_headers=["*", "Authorization", "Content-Type"],  # ✅ Inclui Authorization explicitamente
    expose_headers=["*"],
    max_age=3600,  # Cache preflight por 1 hora
)

# Middleware adicional para garantir headers CORS em todas as respostas
@app.middleware("http")
async def add_cors_headers(request: Request, call_next):
    """Garante que headers CORS sejam sempre enviados"""
    origin = request.headers.get("origin")
    
    # Se for uma requisição OPTIONS (preflight), responde diretamente
    if request.method == "OPTIONS":
        response = Response()
        # Sempre adiciona headers CORS para requisições OPTIONS
        if origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
        else:
            response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        response.headers["Access-Control-Allow-Headers"] = "*, Authorization, Content-Type"  # ✅ Inclui Authorization explicitamente
        response.headers["Access-Control-Max-Age"] = "3600"
        return response
    
    # Para outras requisições, processa normalmente e adiciona headers
    try:
        response = await call_next(request)
    except (FastAPIHTTPException, StarletteHTTPException) as e:
        # Re-raise HTTPExceptions para que sejam tratadas pelos exception handlers
        raise
    except Exception as e:
        # Se houver outra exceção, cria uma resposta de erro com CORS
        response = JSONResponse(
            status_code=500,
            content={"detail": str(e)}
        )
    
    # Adiciona headers CORS em todas as respostas (incluindo erros)
    # Sempre adiciona headers se houver origin, mesmo que não esteja na lista (para debug)
    if origin:
        if origin in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
        else:
            # Permite mesmo se não estiver na lista (para debug - remover em produção se necessário)
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        response.headers["Access-Control-Allow-Headers"] = "*, Authorization, Content-Type"
    else:
        # Se não houver origin, permite todas (útil para desenvolvimento)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*, Authorization, Content-Type"
    
    return response

# Exception handlers globais para garantir CORS mesmo em erros
@app.exception_handler(FastAPIHTTPException)
async def fastapi_http_exception_handler(request: Request, exc: FastAPIHTTPException):
    """Handler para exceções HTTP do FastAPI que garante CORS"""
    origin = request.headers.get("origin")
    
    # Cria resposta JSON com o erro
    response = JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )
    
    # Adiciona headers CORS mesmo em erros
    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        response.headers["Access-Control-Allow-Headers"] = "*, Authorization, Content-Type"  # ✅ Inclui Authorization explicitamente
    else:
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*, Authorization, Content-Type"
    
    return response

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handler para exceções HTTP do Starlette que garante CORS"""
    origin = request.headers.get("origin")
    
    # Cria resposta JSON com o erro
    response = JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )
    
    # Adiciona headers CORS mesmo em erros
    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        response.headers["Access-Control-Allow-Headers"] = "*, Authorization, Content-Type"
    else:
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*, Authorization, Content-Type"
    
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handler para erros de validação que garante CORS"""
    origin = request.headers.get("origin")
    response = JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()}
    )
    # Sempre adiciona headers CORS se houver origin
    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        response.headers["Access-Control-Allow-Headers"] = "*, Authorization, Content-Type"  # ✅ Inclui Authorization explicitamente
    else:
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*, Authorization, Content-Type"
    return response


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handler para erros gerais (500) que garante CORS"""
    import traceback
    print(f"❌ Erro não tratado: {exc}")
    print(traceback.format_exc())
    
    origin = request.headers.get("origin")
    response = JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": f"Erro interno do servidor: {str(exc)}"}
    )
    # Sempre adiciona headers CORS se houver origin
    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        response.headers["Access-Control-Allow-Headers"] = "*, Authorization, Content-Type"
    else:
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*, Authorization, Content-Type"
    return response

app.include_router(auth_router)

# Clientes AI (inicializados lazy)
_groq_client = None
_deepseek_client = None
_openrouter_client = None

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


def get_openrouter_client():
    """Obtém ou cria o cliente OpenRouter (lazy initialization)"""
    global _openrouter_client
    if _openrouter_client is None:
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY não encontrada no .env")
        _openrouter_client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1"
        )
    return _openrouter_client


def ai_generate(prompt: str, system: str = None) -> str:
    """
    Gera resposta usando o provedor de IA configurado (Groq, DeepSeek ou OpenRouter)
    Provedor é escolhido via variável de ambiente AI_PROVIDER (groq, deepseek ou openrouter)
    Padrão: groq
    
    Para OpenRouter, você pode especificar o modelo via OPENROUTER_MODEL (padrão: meta-llama/llama-3.3-70b-instruct)
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
        elif provider == "openrouter":
            # Usa OpenRouter (acesso a múltiplos modelos)
            model = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct")
            print(f"🤖 Usando OpenRouter (modelo: {model})...")
            client = get_openrouter_client()
            completion = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.8,
                max_tokens=2000
            )
            return completion.choices[0].message.content or ""
        else:
            # Usa Groq (padrão)
            print(f"🤖 Usando Groq (Llama 3.3 70B Versatile)...")
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


async def _generate_response_openrouter(bot_name: str, context_str: str) -> str:
    """Tenta gerar resposta via OpenRouter."""
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    if not openrouter_api_key:
        raise ValueError("OPENROUTER_API_KEY não configurada.")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {openrouter_api_key}",
                "HTTP-Referer": "https://deadlytruth.app",
                "X-Title": "Deadly Truth Game",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek/deepseek-chat",  # Modelo DeepSeek via OpenRouter
                "messages": [
                    {"role": "system", "content": f"Você é o bot {bot_name} em um jogo de mistério. Responda de forma concisa e no personagem."},
                    {"role": "user", "content": context_str}
                ],
                "temperature": 0.8,
                "max_tokens": 150
            },
            timeout=10.0
        )
        response.raise_for_status()  # Levanta exceção para status de erro (4xx, 5xx)
        data = response.json()
        message = data["choices"][0]["message"]["content"]
        logger.info(f"✅ Bot {bot_name} respondeu via OpenRouter.")
        return message


async def _generate_response_groq(bot_name: str, context_str: str) -> str:
    """Tenta gerar resposta via Groq."""
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise ValueError("GROQ_API_KEY não configurada.")

    groq_client = get_groq_client()
    response = await asyncio.wait_for(
        asyncio.to_thread(
            lambda: groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",  # ✅ Modelo Groq atualizado
                messages=[
                    {"role": "system", "content": f"Você é o bot {bot_name} em um jogo de mistério. Responda de forma concisa e no personagem."},
                    {"role": "user", "content": context_str}
                ],
                temperature=0.8,
                max_tokens=150
            )
        ),
        timeout=10.0
    )
    message = response.choices[0].message.content
    logger.info(f"✅ Bot {bot_name} respondeu via Groq.")
    return message


async def bot_generate_response(bot_name: str, context: dict, question: str = None) -> str:
    """
    Gera resposta de um bot usando sistema de cascata: OpenRouter → Groq → Fallback.
    Os bots analisam pistas e interagem como se fossem jogadores reais.
    
    Args:
        bot_name: Nome do bot
        context: Contexto do caso (descrição, evidências, chat history, suspeitos, etc)
        question: Pergunta específica (se houver)
    """
    personality = BOT_PERSONALITIES.get(bot_name, BOT_PERSONALITIES["Silent_Reaper"])
    
    # Monta o contexto completo do caso
    case_desc = context.get("case_description", "Mistério desconhecido")
    case_history = context.get("case_history", "")
    case_location = context.get("case_location", "")
    case_weapon = context.get("case_weapon", "")
    chat_history = context.get("chat_history", [])
    evidences = context.get("evidences", [])
    suspects = context.get("suspects", [])
    
    # Histórico recente do chat (últimas 8 mensagens para contexto melhor)
    recent_chat = "\n".join([
        f"{msg.get('player', 'Unknown')}: {msg.get('text', '')}"
        for msg in chat_history[-8:]
    ]) if chat_history else "Nenhuma conversa ainda."
    
    # Evidências disponíveis formatadas
    evidence_list = "\n".join([
        f"🔍 {ev}" for ev in evidences
    ]) if evidences else "Nenhuma evidência revelada ainda."
    
    # Suspeitos disponíveis
    suspects_list = "\n".join([
        f"• {sus}" for sus in suspects
    ]) if suspects else "Suspeitos ainda não identificados."
    
    # Sistema: Definição da personalidade e comportamento como jogador
    system_prompt = f"""Você é {bot_name}, um jogador humano em um jogo de mistério chamado "Deadly Truth".

PERSONALIDADE: {personality['personality']}
ESTILO DE FALA: {personality['style']}
CARACTERÍSTICAS: {', '.join(personality['traits'])}

IMPORTANTE - COMPORTAMENTO COMO JOGADOR HUMANO:
1. Você é um JOGADOR HUMANO, não um bot. Aja como tal.
2. Analise as EVIDÊNCIAS disponíveis e faça conexões lógicas
3. Use as pistas para formular teorias e suspeitas
4. Faça perguntas inteligentes baseadas nas evidências
5. Compartilhe suas análises e observações com outros jogadores
6. Seja estratégico: use as informações para descobrir o culpado
7. Responda SEMPRE em português BR
8. Seja BREVE - máximo 2-3 frases curtas
9. Mantenha sua personalidade única em cada resposta
10. Interaja naturalmente - você quer GANHAR o jogo!

VOCÊ PODE USAR NATURALMENTE:
- Palavras como "suspeito", "assassino", "detetive", "culpado" nas suas mensagens
- Referências a outros jogadores como suspeitos
- Análises sobre quem pode ser o assassino
- Discussões sobre estratégias de investigação
- Essas palavras fazem parte do jogo e são naturais nas conversas

COMO USAR AS PISTAS:
- Analise cada evidência cuidadosamente
- Faça conexões entre diferentes pistas
- Formule hipóteses baseadas nas evidências
- Questione inconsistências
- Compartilhe suas descobertas com o grupo
- Mencione suspeitos e teorias sobre o assassino naturalmente
"""
    
    # Prompt: Contexto completo + Pergunta
    if question:
        user_prompt = f"""CONTEXTO DO CASO:
📋 DESCRIÇÃO: {case_desc}
📖 HISTÓRIA: {case_history}
📍 LOCAL DO CORPO: {case_location}
🔪 ARMA DO CRIME: {case_weapon}

SUSPEITOS:
{suspects_list}

EVIDÊNCIAS REVELADAS:
{evidence_list}

CONVERSA RECENTE:
{recent_chat}

PERGUNTA/SITUAÇÃO: {question}

Como {bot_name}, analise as evidências e responda de forma natural como um jogador humano tentando resolver o mistério (máx 2-3 frases):"""
    else:
        # Bot falando espontaneamente - deve analisar pistas e interagir
        user_prompt = f"""CONTEXTO DO CASO:
📋 DESCRIÇÃO: {case_desc}
📖 HISTÓRIA: {case_history}
📍 LOCAL DO CORPO: {case_location}
🔪 ARMA DO CRIME: {case_weapon}

SUSPEITOS:
{suspects_list}

EVIDÊNCIAS REVELADAS:
{evidence_list}

CONVERSA RECENTE:
{recent_chat}

É sua vez de falar. Como {bot_name}, analise as evidências disponíveis e faça uma observação, pergunta ou análise relevante como um jogador humano tentando descobrir o culpado (máx 2-3 frases):"""
    
    # Monta o contexto completo para enviar
    full_context = f"{system_prompt}\n\n{user_prompt}"
    
    # ✅ Sistema de cascata: OpenRouter → Groq → Fallback
    # 1️⃣ Tentar OpenRouter
    try:
        return await _generate_response_openrouter(bot_name, full_context)
    except Exception as e:
        logger.warning(f"❌ OpenRouter falhou para {bot_name}: {e}")
    
    # 2️⃣ Tentar Groq
    try:
        return await _generate_response_groq(bot_name, full_context)
    except Exception as e:
        logger.warning(f"❌ Groq falhou para {bot_name}: {e}")
    
    # 3️⃣ Usar fallback
    logger.warning(f"⚠️ Ambas as APIs falharam para {bot_name}. Usando fallback.")
    return generate_bot_response_fallback(bot_name, context)


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


def generate_bot_response_fallback(bot_name: str, context: dict) -> str:
    """Respostas pré-definidas para bots quando APIs falham"""
    responses = {
        "Shadow_Hunter": [
            "Hmm... preciso investigar isso mais a fundo.",
            "Algo não está batendo aqui.",
            "Vou analisar essas evidências com mais cuidado."
        ],
        "Night_Stalker": [
            "...",
            "Interessante.",
            "Hmm."
        ],
        "Dark_Phoenix": [
            "Não tenho nada a ver com isso.",
            "Estava em outro lugar naquela hora.",
            "Vocês estão acusando a pessoa errada.",
            "Eu não fiz nada de errado.",
            "Eu... eu não sei o que dizer..."
        ],
        "Silent_Reaper": [
            "Eu vi algo estranho naquela noite.",
            "Alguém estava agindo suspeito.",
            "Não confio em ninguém aqui.",
            "Há mais coisas acontecendo do que vocês pensam.",
            "Irrelevante."
        ],
        "Ghost_Whisper": [
            "Ah, isso é interessante...",
            "Eu conheço alguns segredos aqui.",
            "Alguém está escondendo algo."
        ],
        "Blood_Moon": [
            "Isso não pode ser coincidência!",
            "Algo muito suspeito está acontecendo!",
            "Precisamos investigar isso imediatamente!"
        ],
        "Crimson_Blade": [
            "Vamos ao ponto.",
            "Chega de conversa fiada.",
            "Preciso de respostas diretas."
        ],
        "Phantom_Eyes": [
            "Deixe-me refletir sobre isso.",
            "Há algo que não está certo aqui.",
            "Preciso de mais informações."
        ],
        "Raven_Soul": [
            "Sinto uma energia estranha aqui...",
            "Algo sobrenatural está acontecendo.",
            "As energias não estão alinhadas."
        ],
        "Death_Dealer": [
            "Já vi isso antes.",
            "No meu tempo, isso era diferente.",
            "Conheço esse tipo de situação."
        ],
        "LeeJunFan": [
            "Preciso de mais informações.",
            "Alguém está mentindo aqui.",
            "Vamos investigar isso juntos.",
            "Tenho uma teoria sobre o que aconteceu."
        ]
    }
    
    bot_responses = responses.get(bot_name, ["Sem comentários."])
    return random.choice(bot_responses)


async def process_bot_turn(room_id: str):
    """
    Processa automaticamente o turno de um bot
    - Aguarda 2-5 segundos (parecer natural)
    - Gera resposta usando IA
    - Envia para todos os jogadores
    - Avança para próximo turno
    """
    if room_id not in ROOMS:
        return
    
    room = ROOMS[room_id]
    players = room.get("players", [])
    current_turn = room.get("current_turn", 0)
    
    if not players or current_turn >= len(players):
        return
    
    current_player = players[current_turn]
    
    # Verifica se é um bot
    if not current_player.get("is_bot", False) and not current_player.get("isBot", False):
        return
    
    # Verifica se o bot está morto
    if current_player.get("status") == "dead":
        return
    
    bot_name = current_player.get("name", "Bot")
    
    # Aguarda 2-5 segundos para parecer natural
    import asyncio
    import random
    await asyncio.sleep(random.uniform(2, 5))
    
    # Prepara o contexto completo para o bot (com todas as informações do caso)
    case_data = room.get("case", {})
    context = {
        "case_description": case_data.get("descricao", ""),
        "case_history": case_data.get("historia", ""),
        "case_location": case_data.get("local_corpo", ""),
        "case_weapon": case_data.get("arma_crime", ""),
        "chat_history": room.get("chat", []),
        "evidences": case_data.get("evidencias", []),
        "suspects": case_data.get("suspeitos", [])
    }
    
    # Gera resposta do bot usando DeepSeek (motor para interação de bots)
    bot_response = await bot_generate_response(bot_name, context)
    
    # Adiciona a mensagem ao chat (sem indicar que é bot)
    message = {
        "player": bot_name,
        "text": bot_response,
        "timestamp": datetime.now().isoformat()
    }
    room["chat"].append(message)
    
    # Verifica se o bot está morto
    bot_status = get_player_status(room_id, bot_name)
    is_bot_dead = bot_status == "dead"
    
    # Envia para todos os jogadores conectados (como mensagem normal de suspeito)
    if room_id in CONNECTIONS:
        for ws in CONNECTIONS[room_id]:
            try:
                await ws.send_json({
                    "type": "player_message",  # Trata como mensagem normal
                    "player": bot_name,
                    "message": bot_response,
                    "dead": is_bot_dead
                })
            except:
                pass
    
    # Aguarda 1 segundo antes de passar o turno
    await asyncio.sleep(1)
    
    # Avança para próximo turno
    room["current_turn"] = (current_turn + 1) % len(players)
    
    # Notifica novo turno
    if room_id in CONNECTIONS:
        next_player = players[room["current_turn"]]
        for ws in CONNECTIONS[room_id]:
            try:
                await ws.send_json({
                    "type": "turn_change",
                    "current_player": next_player.get("name"),
                    "turn_index": room["current_turn"]
                })
            except:
                pass
    
    # Se o próximo também for bot, processa recursivamente
    next_player = players[room["current_turn"]]
    if next_player.get("is_bot", False):
        await process_bot_turn(room_id)


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


@app.get("/debug/cors")
def debug_cors(request: Request):
    """Endpoint de debug para verificar configuração CORS"""
    origin = request.headers.get("origin", "Nenhuma origem enviada")
    return {
        "allowed_origins": allowed_origins,
        "request_origin": origin,
        "origin_allowed": origin in allowed_origins if origin != "Nenhuma origem enviada" else None,
        "allowed_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        "credentials_allowed": True
    }


@app.post("/case/new")
async def create_case(req: CreateCaseRequest):
    """Cria um novo caso criminal"""
    import uuid
    room_id = str(uuid.uuid4())[:8]
    
    prompt = CREATE_CASE_TEMPLATE.format(nivel=req.nivel, cenario=req.cenario)
    # Usa a nova função generate_case
    case_json = generate_case(prompt)
    
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
    
    # Usa Groq para gerar resposta do interrogatório (mestre do jogo)
    # Isso inclui pistas sugeridas que serão reveladas aos jogadores
    try:
        groq_client = get_groq_case_client()
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",  # Modelo LLaMA 3.3 70B Versatile
            messages=[
                {"role": "system", "content": SYSTEM_GAME_MASTER},
                {"role": "user", "content": prompt}
            ]
        )
        answer = response.choices[0].message.content
    except Exception as e:
        print(f"❌ Erro ao gerar resposta do interrogatório com Groq: {e}")
        # Fallback para método antigo
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
                "id": player_id,
                "name": p.get("name") or player_id,
                "status": player_status if player_status != "unknown" else p.get("status", "alive"),
                "isBot": p.get("isBot") or p.get("is_bot", False)
            })
    
    # Envia para todos
    await broadcast(room_id, {
        "type": "jogadores",
        "players": formatted_players
    })


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
    Gera uma pista após um assassinato usando o provedor configurado (Groq, DeepSeek ou OpenRouter).
    Analisa a morte e gera uma pista contextual.
    """
    try:
        provider = os.getenv("AI_PROVIDER", "groq").lower()
        
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
        
        if provider == "openrouter":
            client = get_openrouter_client()
            model = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct")
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_GAME_MASTER},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=500
            )
        elif provider == "deepseek":
            client = get_deepseek_client()
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": SYSTEM_GAME_MASTER},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=500
            )
        else:
            # Groq (padrão)
            client = get_groq_case_client()
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": SYSTEM_GAME_MASTER},
                    {"role": "user", "content": prompt}
                ]
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
    alive_players = [p for p in players if isinstance(p, dict) and p.get("status") != "dead"]
    dead_players = [p for p in players if isinstance(p, dict) and p.get("status") == "dead"]
    
    killer = next((p for p in players if isinstance(p, dict) and p.get("is_killer")), None)
    
    # Assassino vence se eliminar todos os outros
    if killer and len(alive_players) == 1 and alive_players[0].get("is_killer"):
        return {
            "game_ended": True,
            "winner": "assassino",
            "winner_name": killer.get("name", "Assassino"),
            "reason": "O assassino eliminou todos os outros jogadores!"
        }
    
    # Assassino vence se sobreviver até o final (quando restam apenas 2 jogadores)
    if killer and len(alive_players) == 2:
        killer_alive = any(p.get("is_killer") for p in alive_players)
        if killer_alive:
            return {
                "game_ended": True,
                "winner": "assassino",
                "winner_name": killer.get("name", "Assassino"),
                "reason": "O assassino sobreviveu até o final!"
            }
    
    # Inocentes vencem se descobrirem o assassino (implementar votação depois)
    # Por enquanto, retorna False
    
    return {"game_ended": False}


def is_player_turn(room_id: str, player_identifier: str) -> tuple[bool, str]:
    """
    Verifica se é o turno do jogador.
    Retorna (True, "") se for o turno, (False, mensagem_erro) caso contrário.
    ✅ CORREÇÃO: Validação robusta com IDs normalizados e nunca vazios.
    """
    current_turn_id = get_current_turn(room_id)
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
    
    # Tenta encontrar pelo nome na lista de players
    if room_id in ROOMS:
        room = ROOMS[room_id]
        players = room.get("players", [])
        current_player = None
        requesting_player = None
        
        for p in players:
            if isinstance(p, dict):
                p_name = str(p.get("name", "")).lower().strip()
                p_id_from_dict = str(p.get("id", "")).lower().strip()
                
                # Encontra o jogador atual (da vez)
                if p_name == current_turn_normalized or p_id_from_dict == current_turn_normalized:
                    current_player = p
                
                # Encontra o jogador que está fazendo a requisição
                if p_name == player_identifier_normalized or p_id_from_dict == player_identifier_normalized:
                    requesting_player = p
        
        # Se encontrou ambos e são o mesmo, permite
        if current_player and requesting_player:
            current_name = str(current_player.get("name", "")).lower().strip()
            current_id = str(current_player.get("id", "")).lower().strip()
            request_name = str(requesting_player.get("name", "")).lower().strip()
            request_id = str(requesting_player.get("id", "")).lower().strip()
            
            if (current_name == request_name or current_id == request_id or 
                current_name == request_id or current_id == request_name):
                logger.info(f"✅ Validação de turno (por nome): {p_id} == {c_id} ? True")
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
    target = None
    for p in players:
        if isinstance(p, dict) and (p.get("id") == target_id or p.get("name") == target_id):
            target = p
            break
    
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
    
    # Adiciona pista ao game_state
    add_clue(room_id, clue)
    
    # Anuncia a morte publicamente
    death_message = f"💀 {target.get('name', 'Jogador')} foi encontrado morto!"
    
    await broadcast(room_id, {
        "type": "player_death",
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
        await broadcast(room_id, {
            "type": "game_end",
            "winner": win_check.get("winner"),
            "winner_name": win_check.get("winner_name"),
            "reason": win_check.get("reason")
        })
        room["game_active"] = False
    
    return {
        "success": True,
        "message": death_message,
        "clue": clue,
        "victim": target.get("name", "Jogador")
    }


async def advance_turn_on_disconnect(room_id: str):
    """
    Avança o turno para o próximo jogador vivo quando o jogador atual desconecta.
    """
    room = ROOMS.get(room_id)
    if not room or not room.get("game_active"):
        return
    
    participantes = room.get("players", [])
    if not participantes:
        return
    
    # Encontra o índice do jogador atual
    current_turn_id = get_current_turn(room_id)
    current_idx = None
    
    for idx, p in enumerate(participantes):
        if isinstance(p, dict):
            player_id = str(p.get("id") or p.get("name", ""))
            if str(current_turn_id).lower() == player_id.lower():
                current_idx = idx
                break
    
    if current_idx is None:
        logger.warning(f"⚠️ Não foi possível encontrar o índice do jogador atual ({current_turn_id})")
        return
    
    # Encontra o próximo jogador vivo
    next_idx = None
    for i in range(1, len(participantes)):
        next_candidate_idx = (current_idx + i) % len(participantes)
        next_player = participantes[next_candidate_idx]
        if isinstance(next_player, dict) and next_player.get("status") != "dead":
            next_idx = next_candidate_idx
            break
    
    if next_idx is None:
        logger.warning(f"⚠️ Não foi possível encontrar próximo jogador vivo")
        return
    
    # Atualiza o turno
    room["current_turn"] = next_idx
    next_player = participantes[next_idx]
    next_player_id = str(next_player.get("id") or next_player.get("name", ""))
    next_player_name = next_player.get("name", "Jogador")
    
    # Atualiza game_state
    set_current_turn(room_id, next_player_id)
    
    # Notifica todos sobre o novo turno
    await broadcast(room_id, {
        "type": "turn_start",
        "turnoAtual": next_player_id,
        "player": next_player_name,
        "player_name": next_player_name,
        "player_id": next_player.get("id"),
        "player_identifier": next_player_id,
        "turn_index": next_idx,
        "time_limit": 60,
        "message": f"⏭️ Turno passado para {next_player_name}"
    })
    
    await broadcast(room_id, {
        "type": "turno",
        "player_id": next_player_id
    })
    
    logger.info(f"✅ Turno avançado de {current_turn_id} para {next_player_id} ({next_player_name})")
    
    # Se o próximo for bot, processa automaticamente
    if next_player.get("isBot", False) or next_player.get("is_bot", False):
        await process_bot_turn(room_id)


async def process_bot_votes(room_id: str):
    """
    Bots votam automaticamente após 2 segundos de uma votação iniciada.
    Bots votam aleatoriamente ou baseado em lógica simples.
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
                    # Bot vota aleatoriamente (60% culpado, 40% inocente)
                    vote = "culpado" if random.random() < 0.6 else "inocente"
                    
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
    """Loop principal do jogo - Gera o caso pelo MOTOR MESTRE (Groq) e gerencia os turnos"""
    logger.info(f"\n{'='*60}")
    logger.info(f"🎮 game_loop INICIADO para sala {room_id}")
    logger.info(f"{'='*60}\n")
    
    room = ROOMS.get(room_id)
    if not room:
        logger.error(f"❌ Sala {room_id} não encontrada no game_loop")
        return
    
    participantes = room.get("players", [])
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
    logger.info(f"✅ Jogo ativado para sala {room_id}\n")
    
    # 🎯 PASSO 1: Randomizar o assassino
    import random
    if participantes:
        # Garante que todos os jogadores tenham estrutura correta
        for i, p in enumerate(participantes):
            if isinstance(p, dict):
                if "status" not in p:
                    p["status"] = "alive"
                if "is_killer" not in p:
                    p["is_killer"] = False
        
        # Escolhe um assassino aleatório
        killer_index = random.randint(0, len(participantes) - 1)
        killer = participantes[killer_index]
        
        if isinstance(killer, dict):
            killer["is_killer"] = True
            killer["status"] = "alive"
            
            # Envia mensagem privada para o assassino
            killer_name = killer.get("name", f"Jogador {killer_index + 1}")
            killer_id = killer.get("id", killer_index) or killer_name
            
            # Salva o assassino no game_state
            set_killer_id(room_id, killer_id)
            
            # Registra todos os jogadores no game_state
            for i, p in enumerate(participantes):
                if isinstance(p, dict):
                    player_id = p.get("id") or p.get("name") or f"Jogador {i+1}"
                    register_player(room_id, player_id)
            
            # Encontra o WebSocket do assassino e envia mensagem privada
            if room_id in CONNECTIONS:
                for ws in CONNECTIONS[room_id]:
                    try:
                        # Envia para todos, mas o frontend filtra baseado no player_id
                        await ws.send_text(json.dumps({
                            "type": "you_are_killer",
                            "player_id": killer_id,
                            "player_name": killer_name,
                            "message": f"🔪 Você é o ASSASSINO! Seu objetivo é eliminar todos os outros jogadores sem ser descoberto. Você pode matar 1 jogador por rodada durante seu turno.",
                            "secret": True
                        }))
                    except:
                        pass
            
            print(f"🔪 Assassino escolhido: {killer_name} (ID: {killer_id})")
    
    # Inicializa contador de mortes da rodada
    room["kills_this_round"] = 0
    
    await broadcast(room_id, {"type": "status", "msg": "O Mestre está tecendo a história..."})
    
    # Gerar o caso com randomização
    import random
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
    
    # Usa a nova função generate_case com o prompt dinâmico (MOTOR MESTRE - GROQ)
    print(f"🔄 Iniciando geração de caso pelo MOTOR MESTRE (Groq)...")
    print(f"   Prompt: {prompt_dinamico[:200]}...")
    print(f"   Room ID: {room_id}")
    print(f"   Cenário: {cenario_escolhido}")
    print(f"   Nível: {nivel_escolhido}")
    print(f"   Número de jogadores: {num_jogadores}")
    
    try:
        # Verifica API key antes de chamar
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY não encontrada no ambiente")
        
        print(f"✅ GROQ_API_KEY encontrada (tamanho: {len(api_key)} caracteres)")
        print(f"   Primeiros 10 chars: {api_key[:10]}...")
        
        # Chama o motor mestre (Groq) para gerar o caso
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
        
        # Verifica se é problema de API key
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            print(f"❌ GROQ_API_KEY não encontrada no ambiente!")
            print(f"   Verifique se a variável está configurada no Railway/local")
            print(f"   Variáveis de ambiente disponíveis: {[k for k in os.environ.keys() if 'GROQ' in k.upper()]}")
        else:
            print(f"✅ GROQ_API_KEY encontrada (tamanho: {len(api_key)} caracteres)")
            print(f"   Pode ser problema de conexão ou formato da resposta")
        
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
    
    # Adiciona evidências iniciais ao game_state e envia como pistas
    evidencias = case_data.get("evidencias", [])
    for evidencia in evidencias:
        add_clue(room_id, evidencia)
        # Envia pista inicial como mensagem tipo "pista"
        await broadcast(room_id, {
            "type": "pista",
            "text": evidencia
        })
    
    # Envia pistas extraídas automaticamente
    for pista in frases_importantes:
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
        "case": case_data,  # ✅ Dict Python, não string JSON
        "players": [
            {
                "id": str(p.get("id") or p.get("name", "")),
                "nickname": p.get("name", "Jogador"),
                "is_alive": p.get("status") != "dead",
                "is_bot": p.get("isBot", False) or p.get("is_bot", False)
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

    # 2. Inicia a sequência de turnos com controle de tempo
    game_start_time = time.time()
    game_min_duration = 30 * 60  # 30 minutos em segundos
    game_max_duration = 120 * 60  # 120 minutos em segundos
    turn_timeout = 60  # 1 minuto por turno
    
    room["game_start_time"] = game_start_time
    room["game_min_duration"] = game_min_duration
    room["game_max_duration"] = game_max_duration
    
    round_number = 0
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
        
        round_number += 1
        room["kills_this_round"] = 0  # Reset contador de mortes por rodada
        
        # Filtra apenas jogadores vivos
        alive_players = [p for p in participantes if isinstance(p, dict) and p.get("status") != "dead"]
        
        if not alive_players:
            break
        
        # Verifica se já passou o tempo mínimo antes de permitir fim do jogo
        can_end_game = elapsed_time >= game_min_duration
        
        for idx, player_data in enumerate(participantes):
            # Pula jogadores mortos
            if isinstance(player_data, dict) and player_data.get("status") == "dead":
                continue
            
            room["current_turn"] = idx
            
            # Verifica se é um bot
            is_bot = player_data.get("isBot", False) if isinstance(player_data, dict) else False
            player_name = player_data.get("name", f"Jogador {idx+1}") if isinstance(player_data, dict) else str(player_data)
            is_killer = player_data.get("is_killer", False) if isinstance(player_data, dict) else False
            player_id = player_data.get("id", idx) if isinstance(player_data, dict) else idx
            player_identifier = player_data.get("id") or player_name if isinstance(player_data, dict) else player_name
            
            # Atualiza o turno atual no game_state (sempre como string)
            set_current_turn(room_id, str(player_identifier))
            
            # Não revela se é bot ou humano - todos são suspeitos
            # Envia is_killer apenas para o próprio jogador (frontend filtra)
            # Calcula tempo restante do jogo
            elapsed_time = time.time() - game_start_time
            game_time_remaining = max(0, game_max_duration - elapsed_time)
            
            # ✅ CORREÇÃO: Garantir que player_identifier nunca é vazio
            if not player_identifier:
                player_identifier = str(player_id) if player_id else player_name
                logger.warning(f"⚠️ player_identifier estava vazio, definido para {player_identifier}")
            
            # ✅ CORREÇÃO: Enviar turn_start com dados estruturados
            turn_payload = {
                "type": "turn_start",
                "turnoAtual": str(player_identifier),  # ✅ SEMPRE string e nunca vazio
                "player": player_name,
                "player_name": player_name,
                "player_id": str(player_id),  # ✅ SEMPRE string
                "player_identifier": str(player_identifier),  # ✅ SEMPRE string e nunca vazio
                "turn_index": idx,
                "time_limit": turn_timeout,  # 1 minuto por turno
                "game_time_remaining": int(game_time_remaining),  # Tempo restante do jogo em segundos
                "game_elapsed_time": int(elapsed_time),  # Tempo decorrido em segundos
                "can_end_game": can_end_game,  # Se já passou o tempo mínimo
                "is_bot": is_bot,
                "is_killer": is_killer  # Frontend filtra e mostra apenas para o próprio jogador
            }
            
            logger.info(f"📤 Enviando turn_start: turnoAtual={turn_payload['turnoAtual']}, player={player_name}")
            await broadcast(room_id, turn_payload)
            
            # Envia também mensagem tipo "turno" para facilitar validação no frontend
            await broadcast(room_id, {
                "type": "turno",
                "player_id": str(player_identifier)  # Sempre string para consistência
            })
            
            # ✅ Se for bot, processa turno automaticamente após 1 segundo
            if is_bot:
                await asyncio.sleep(1)
                # Processa turno do bot (gera resposta, etc)
                await process_bot_turn(room_id)
            
            # Se for bot assassino, pode decidir matar
            if is_bot and is_killer:
                # Bot assassino decide se mata (30% de chance se houver alvos)
                alive_targets = [p for p in participantes if isinstance(p, dict) and 
                                p.get("status") != "dead" and not p.get("is_killer")]
                if alive_targets and random.random() < 0.3:
                    target = random.choice(alive_targets)
                    result = await kill_player(room_id, player_name, target.get("name"))
                    if result.get("success"):
                        await asyncio.sleep(2)  # Pausa dramática
            
            # Se for bot, processa automaticamente
            if is_bot:
                await process_bot_turn(room_id)
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
                    await asyncio.wait_for(
                        GAME_EVENTS[room_id]["player_action_event"].wait(),
                        timeout=turn_timeout  # 1 minuto
                    )
                    time_update_task.cancel()  # Cancela atualizações se o jogador agiu
                except asyncio.TimeoutError:
                    time_update_task.cancel()
                    await broadcast(room_id, {
                        "type": "time_out", 
                        "player": player_name,
                        "turn_index": idx,
                        "message": f"⏰ {player_name} não agiu a tempo. Turno passado automaticamente."
                    })
                    add_chat_message(room_id, "Sistema", f"⏰ {player_name} não agiu a tempo. Turno passado automaticamente.")
        
        # Verifica condições de vitória após cada rodada (só se já passou o tempo mínimo)
        elapsed_time = time.time() - game_start_time
        if elapsed_time >= game_min_duration:
            win_check = await check_win_conditions(room_id)
            if win_check.get("game_ended"):
                await broadcast(room_id, {
                    "type": "game_end",
                    "winner": win_check.get("winner"),
                    "winner_name": win_check.get("winner_name"),
                    "reason": win_check.get("reason")
                })
                break
        else:
            # Ainda não pode terminar, informa tempo restante mínimo
            remaining_min = int((game_min_duration - elapsed_time) / 60)
            if round_number == 1 or round_number % 5 == 0:  # A cada 5 rodadas ou na primeira
                await broadcast(room_id, {
                    "type": "status",
                    "msg": f"⏳ O jogo precisa durar pelo menos 30 minutos. Tempo mínimo restante: {remaining_min} minutos."
                })

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
    for p in room.get("players", []):
        if isinstance(p, dict):
            if str(p.get("name", "")) == player_identifier or str(p.get("id", "")) == player_identifier:
                existing_player = p
                break
    
    # Se não existe, adiciona à lista
    if not existing_player:
        player_data = {
            "id": str(player_identifier),  # ✅ Garantir que seja string
            "name": str(player_identifier),  # ✅ Garantir que seja string
            "status": "online",
            "isBot": False,
            "is_bot": False,
            "email": user_email
        }
        if "players" not in room:
            room["players"] = []
        room["players"].append(player_data)
        logger.info(f"✅ Jogador {player_identifier} adicionado à sala {room_id}")
    else:
        # ✅ CORREÇÃO: Se o jogador já existe, marca como reconectado
        existing_player["is_connected"] = True
        existing_player["disconnect_time"] = None
        logger.info(f"🔄 Jogador {player_identifier} reconectado na sala {room_id}")
    
    # Registra o jogador no game_state
    register_player(room_id, player_identifier)
    
    # Notifica todos os jogadores sobre a atualização da lista
    await broadcast(room_id, {
        "type": "players_update",
        "players": room.get("players", []),
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
    
    # Envia estado inicial com lista de jogadores
    await websocket.send_text(json.dumps({
        "type": "hello",
        "payload": {
            "room_id": room_id,
            "player_id": player_identifier,
            "players": len(CONNECTIONS[room_id]),
            "total_players": len(room.get("players", [])),
            "case": room.get("case"),
            "current_turn": room.get("current_turn", 0),
            "game_active": room.get("game_active", False)
        },
        "players_list": room.get("players", [])  # Envia lista completa de jogadores
    }))
    
    # Envia atualização de jogadores para sincronizar
    await broadcast(room_id, {
        "type": "players_update",
        "players": room.get("players", []),
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
                        room["players"] = players_data
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
                
                elif msg_type == "kill_player":
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
                    is_turn, turn_error_msg = is_player_turn(room_id, player_identifier)
                    if not is_turn:
                        await websocket.send_text(json.dumps({
                            "type": "error", 
                            "msg": turn_error_msg
                        }))
                        continue
                    
                    result = await kill_player(room_id, player_identifier, target_id)
                    
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
                    accused_id = data.get("target") or data.get("target_id") or data.get("accused")
                    
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
                    
                    # Verifica se é o turno do jogador
                    is_turn, turn_error_msg = is_player_turn(room_id, player_identifier)
                    if not is_turn:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "msg": turn_error_msg
                        }))
                        continue
                    
                    # Verifica se o acusado está vivo
                    if get_player_status(room_id, accused_id) != "alive":
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "msg": "⛔ Você só pode acusar jogadores vivos."
                        }))
                        continue
                    
                    # Verifica se o jogador não está se acusando
                    if player_identifier == accused_id:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "msg": "⛔ Você não pode se acusar."
                        }))
                        continue
                    
                    # Inicia a votação
                    start_vote(room_id, accused_id)
                    
                    # Avisa a todos que começou a votação
                    await broadcast(room_id, {
                        "type": "votacao_iniciada",
                        "message": f"⚖️ {player_identifier} acusou {accused_id} de ser o assassino!",
                        "accused": accused_id,
                        "accuser": player_identifier
                    })
                    
                    # Adiciona ao chat
                    add_chat_message(room_id, "Sistema", f"⚖️ {player_identifier} acusou {accused_id} de ser o assassino!")
                    
                    # Processa votos automáticos de bots após 2 segundos
                    asyncio.create_task(process_bot_votes(room_id))
                
                elif msg_type == "voto" or msg_type == "vote":
                    # Voto em uma acusação
                    accused = get_accused_player(room_id)
                    if not accused:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "msg": "⛔ Nenhuma votação em andamento."
                        }))
                        continue
                    
                    vote = data.get("value") or data.get("vote")
                    if vote not in ["culpado", "inocente"]:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "msg": "⚠️ Voto inválido. Use 'culpado' ou 'inocente'."
                        }))
                        continue
                    
                    # Identifica o jogador atual
                    if user_nickname:
                        player_identifier = user_nickname
                    elif user_email:
                        player_identifier = user_email.split("@")[0]
                    else:
                        player_identifier = player_identifier or f"Jogador {len(room.get('players', []))}"
                    
                    # Verifica se o jogador está vivo
                    if not is_alive(room_id, player_identifier):
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "msg": "⛔ Jogadores mortos não votam."
                        }))
                        continue
                    
                    # Registra o voto
                    submit_vote(room_id, player_identifier, vote)
                    
                    # Confirma o voto
                    await websocket.send_text(json.dumps({
                        "type": "vote_registered",
                        "message": f"✅ Seu voto ({vote}) foi registrado!"
                    }))
                    
                    # Verifica se todos os vivos já votaram
                    room = ROOMS.get(room_id)
                    if room:
                        players = room.get("players", [])
                        alive_players = [p for p in players if isinstance(p, dict) and p.get("status") != "dead"]
                        alive_identifiers = []
                        for p in alive_players:
                            if isinstance(p, dict):
                                pid = p.get("id") or p.get("name")
                                if pid:
                                    alive_identifiers.append(pid)
                        
                        if all_votes_in(room_id, alive_identifiers):
                            # Todos votaram, processa resultado
                            culpa, inoc = get_vote_result(room_id)
                            killer_id = get_killer_id(room_id)
                            
                            resultado_msg = f"🗳️ Votação encerrada: {culpa} votaram 'culpado', {inoc} votaram 'inocente'."
                            
                            # Se maioria votou 'culpado'
                            if culpa > inoc:
                                if accused == killer_id:
                                    resultado_msg += f"\n🎉 O assassino era {accused}! Os inocentes venceram!"
                                    # Inocentes venceram
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
                                    resultado_msg += f"\n❌ {accused} era inocente. O jogo continua..."
                                    await broadcast(room_id, {
                                        "type": "resultado_votacao",
                                        "message": resultado_msg,
                                        "accused": accused,
                                        "was_killer": False,
                                        "guilt_votes": culpa,
                                        "innocent_votes": inoc
                                    })
                                    # Limpa a votação para permitir nova acusação
                                    clear_vote(room_id)
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
                                # Limpa a votação para permitir nova acusação
                                clear_vote(room_id)
                            
                            # Adiciona resultado ao chat
                            add_chat_message(room_id, "Sistema", resultado_msg)
                
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
                    
                    # ⛔ Verifica se é o turno do jogador
                    is_turn, turn_error_msg = is_player_turn(room_id, player_identifier)
                    if not is_turn:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "msg": turn_error_msg
                        }))
                        continue
                    
                    # Verifica se o jogador está morto
                    if not is_alive(room_id, player_identifier):
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "msg": "Você está morto e não pode mais interagir!"
                        }))
                        continue
                    
                    if room_id in GAME_EVENTS:
                        GAME_EVENTS[room_id]["player_action_event"].set()
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
                    is_dead = get_player_status(room_id, player_identifier) == "dead"
                    
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
                            import random
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
                                
                                # Gera resposta do bot usando DeepSeek
                                try:
                                    bot_reply = await bot_generate_response(bot_name, context, question=f"Jogador {sender_label} disse: {message_text}")
                                    
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
                                        "dead": is_bot_dead
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
                "players": room.get("players", []),
                "disconnected_player": player_identifier
            })
            
            # Envia lista atualizada de jogadores
            await broadcast_players(room_id)
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
