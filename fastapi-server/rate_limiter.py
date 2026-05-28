"""
Rate limiter usando sliding window para proteger o servidor contra spam e flood.
"""

import time
from collections import defaultdict, deque
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Configurações de rate limiting por tipo de ação
RATE_CONFIG = {
    "message":       {"window_seconds": 5, "max_count": 5},     # 5 msgs em 5s
    "kill":          {"window_seconds": 60, "max_count": 1},    # 1 kill por 60s
    "vote":          {"window_seconds": 60, "max_count": 2},    # 2 votos por 60s
    "accusar":       {"window_seconds": 30, "max_count": 1},    # 1 acusação por 30s
    "start":         {"window_seconds": 30, "max_count": 2},    # 2 starts por 30s
}

# Estado de rate limiting:
# { action: { key: deque(timestamps) } }
# key = "{room_id}:{player_identifier}"

_limiters: dict[str, dict[str, deque]] = defaultdict(lambda: defaultdict(deque))


def check_rate_limit(
    room_id: str,
    player_identifier: str,
    action: str,
) -> tuple[bool, Optional[str]]:
    """
    Verifica se o jogador pode executar a ação.

    Returns:
        (True, None) se permitido
        (False, mensagem) se bloqueado
    """
    config = RATE_CONFIG.get(action)
    if not config:
        return (True, None)  # Sem limite para esta ação

    window = config["window_seconds"]
    max_count = config["max_count"]
    key = f"{room_id}:{player_identifier}"

    bucket = _limiters[action][key]
    now = time.time()

    # Remove timestamps expirados
    while bucket and now - bucket[0] > window:
        bucket.popleft()

    if len(bucket) >= max_count:
        remaining = window - (now - bucket[0]) if bucket else 0
        msg = f"⚠️ Aguarde {max(1, int(remaining))}s antes de usar '{action}' novamente."
        return (False, msg)

    # Registra a ação
    bucket.append(now)
    return (True, None)


def reset_player_limits(room_id: str, player_identifier: str):
    """Reseta todos os limites de um jogador em uma sala."""
    for action in RATE_CONFIG:
        key = f"{room_id}:{player_identifier}"
        if key in _limiters[action]:
            del _limiters[action][key]


def clear_room_limits(room_id: str):
    """Remove todos os rate limits de uma sala."""
    for action in RATE_CONFIG:
        to_delete = [k for k in _limiters[action] if k.startswith(f"{room_id}:")]
        for k in to_delete:
            del _limiters[action][k]
