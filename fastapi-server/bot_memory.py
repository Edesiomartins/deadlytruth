"""
Sistema de memória e estratégia para bots.
Cada bot em cada sala mantém:
- Pistas acumuladas que "conhece"
- Scores de suspeição por jogador
- Histórico de declarações próprias
"""

import json
import random
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Estrutura em memória:
# { room_id: { bot_name: {
#     "accumulated_clues": set[str],
#     "suspicion_scores": dict[str, float],  # player_name -> score (0.0 - 1.0)
#     "alliance_with": set[str]              # player_names
#     "past_statements": list[dict],          # [{text, timestamp, context}]
#     "kill_strategy": "paranoid|opportunistic|methodical",
#     "last_action": str                      # "spoke"|"killed"|"voted"|"silent"
# }}}

bot_memories: dict[str, dict[str, dict]] = {}


def init_bot_memory(room_id: str, bot_name: str, personality: str = "neutral"):
    """Inicializa memória para um bot em uma sala."""
    if room_id not in bot_memories:
        bot_memories[room_id] = {}

    if bot_name not in bot_memories[room_id]:
        # Define estratégia de assassinato baseada na personalidade
        kill_strategies = {
            "Shadow_Hunter": "methodical",       # Mata o mais suspeito
            "Night_Stalker": "opportunistic",     # Mata aleatoriamente
            "Dark_Phoenix": "paranoid",          # Mata quem mais o acusa
            "Silent_Reaper": "opportunistic",
            "Ghost_Whisper": "methodical",
            "Blood_Moon": "paranoid",
            "Crimson_Blade": "opportunistic",
            "Phantom_Eyes": "methodical",
            "Raven_Soul": "paranoid",
            "Death_Dealer": "methodical",
        }

        bot_memories[room_id][bot_name] = {
            "accumulated_clues": set(),
            "suspicion_scores": {},
            "alliance_with": set(),
            "past_statements": [],
            "kill_strategy": kill_strategies.get(bot_name, "opportunistic"),
            "last_action": "initialized",
            "personality": personality,
            "messages_sent": 0,
            "contradiction_count": 0,
        }
        logger.info(f"🧠 Memória inicializada para bot {bot_name} (sala {room_id})")


def add_clue_to_bot(room_id: str, bot_name: str, clue: str):
    """Adiciona uma pista à memória do bot."""
    mem = _get_mem(room_id, bot_name)
    if mem:
        mem["accumulated_clues"].add(clue)


def update_suspicion_score(
    room_id: str,
    bot_name: str,
    target_player: str,
    delta: float,
):
    """
    Ajusta o score de suspeição para um jogador.
    delta > 0 = mais suspeito, delta < 0 = menos suspeito.
    Score é limitado entre 0.0 e 1.0.
    """
    mem = _get_mem(room_id, bot_name)
    if mem:
        current = mem["suspicion_scores"].get(target_player, 0.0)
        new_score = max(0.0, min(1.0, current + delta))
        mem["suspicion_scores"][target_player] = new_score


def record_bot_statement(room_id: str, bot_name: str, text: str, context: str = ""):
    """Registra uma declaração do bot para evitar contradições."""
    mem = _get_mem(room_id, bot_name)
    if mem:
        mem["past_statements"].append({
            "text": text,
            "timestamp": datetime.now().isoformat(),
            "context": context,
        })
        mem["messages_sent"] += 1

        # Limita o histórico para não crescer demais
        if len(mem["past_statements"]) > 30:
            mem["past_statements"] = mem["past_statements"][-30:]


def get_bot_suspicion_scores(room_id: str, bot_name: str) -> dict:
    """Retorna cópia dos scores de suspeição do bot."""
    mem = _get_mem(room_id, bot_name)
    if mem:
        return dict(mem["suspicion_scores"])
    return {}


def get_bot_known_clues(room_id: str, bot_name: str) -> list:
    """Retorna as pistas que o bot conhece."""
    mem = _get_mem(room_id, bot_name)
    if mem:
        return list(mem["accumulated_clues"])
    return []


def get_bot_past_statements(room_id: str, bot_name: str, limit: int = 10) -> list:
    """Retorna declarações recentes do bot."""
    mem = _get_mem(room_id, bot_name)
    if mem:
        return mem["past_statements"][-limit:]
    return []


def select_bot_vote(
    room_id: str,
    bot_name: str,
    accused: str,
    bot_is_killer: bool,
    alive_players: list,
) -> str:
    """
    Decide voto do bot de forma inteligente (não aleatória).
    Retorna 'culpado' ou 'inocente'.

    Lógica:
    - Se ACCUSED tem high suspicion score → vota culpado
    - Se bot é o assassino e o acusado NÃO é muito suspeito → vota culpado (desviar atenção)
    - Se bot é o assassino e acusado é MUITO suspeito → vota inocente (proteger aliado)
    - Caso contrário: voto baseado em suspicion score com algum ruído
    """
    mem = _get_mem(room_id, bot_name)

    if not mem:
        return "culpado" if random.random() < 0.6 else "inocente"

    suspicion = mem["suspicion_scores"].get(accused, 0.3)

    if bot_is_killer:
        # Assassino: se acusado NÃO é muito suspeito, vota culpado (desviar)
        # Se acusado É muito suspeito (> 0.7), vota inocente (tentar salvar)
        if suspicion > 0.7:
            return "inocente" if random.random() < 0.6 else "culpado"
        else:
            return "culpado" if random.random() < 0.7 else "inocente"

    # Bot inocente: voto baseado em suspicion
    if suspicion > 0.5:
        return "culpado" if random.random() < 0.8 else "inocente"
    elif suspicion > 0.3:
        return "culpado" if random.random() < 0.5 else "inocente"
    else:
        return "inocente" if random.random() < 0.7 else "culpado"


def select_bot_kill_target(
    room_id: str,
    bot_name: str,
    alive_targets: list,
) -> Optional[dict]:
    """
    Seleciona alvo para assassinato (bot assassino).
    Usa estratégia configurada na personalidade.

    Strategies:
    - "methodical": mata o jogador com maior suspicion_score (mais perto da verdade)
    - "paranoid": mata o jogador com menor score (quem menos confia no bot)
    - "opportunistic": escolhe aleatoriamente com viés para scores altos
    """
    mem = _get_mem(room_id, bot_name)
    if not mem or not alive_targets:
        return random.choice(alive_targets) if alive_targets else None

    strategy = mem.get("kill_strategy", "opportunistic")
    scores = mem["suspicion_scores"]

    if strategy == "methodical":
        # Mata quem mais suspeita do assassino (maior score)
        scored = []
        for t in alive_targets:
            t_name = t.get("name", "") if isinstance(t, dict) else str(t)
            scored.append((scores.get(t_name, 0.5), t))
        scored.sort(key=lambda x: x[0], reverse=True)
        # 70% chance de matar o mais suspeito, 30% o segundo
        if len(scored) >= 2 and random.random() < 0.3:
            return scored[1][1]
        return scored[0][1]

    elif strategy == "paranoid":
        # Mata quem menos confia (menor score)
        scored = []
        for t in alive_targets:
            t_name = t.get("name", "") if isinstance(t, dict) else str(t)
            scored.append((scores.get(t_name, 0.5), t))
        scored.sort(key=lambda x: x[0])
        return scored[0][1]

    else:  # opportunistic
        # Aleatório com bias
        weights = []
        for t in alive_targets:
            t_name = t.get("name", "") if isinstance(t, dict) else str(t)
            w = scores.get(t_name, 0.3) + 0.1
            weights.append(w)

        # Normaliza
        total = sum(weights) or 1
        weights = [w / total for w in weights]

        try:
            chosen = random.choices(alive_targets, weights=weights, k=1)[0]
            return chosen
        except Exception:
            return random.choice(alive_targets)


def should_bot_respond(room_id: str, bot_name: str, trigger_message: str) -> bool:
    """Decide se o bot deve responder a uma mensagem (baseado em cooldown)."""
    mem = _get_mem(room_id, bot_name)
    if not mem:
        return random.random() < 0.3

    # Limita frequência de respostas (não spam)
    recent = mem.get("past_statements", [])
    if len(recent) >= 3:
        return random.random() < 0.25  # 25% de chance

    return random.random() < 0.35  # 35% de chance padrão


def clear_room_memories(room_id: str):
    """Limpa memórias de bots de uma sala."""
    if room_id in bot_memories:
        del bot_memories[room_id]


def _get_mem(room_id: str, bot_name: str) -> Optional[dict]:
    if room_id in bot_memories and bot_name in bot_memories[room_id]:
        return bot_memories[room_id][bot_name]
    return None
