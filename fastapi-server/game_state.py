# fastapi-server/game_state.py

"""
Gerencia o estado do jogo de forma centralizada.
Armazena resumo do caso, pistas, histórico de chat por sala.
"""

# Armazena o estado do jogo por sala (room_id)
# Estrutura: {room_id: {"case_summary": str, "clues": list, "chat_history": list}}
game_states = {}


def set_case_summary(room_id: str, summary: str):
    """Define o resumo do caso para uma sala"""
    if room_id not in game_states:
        game_states[room_id] = {"case_summary": "", "clues": [], "chat_history": []}
    game_states[room_id]["case_summary"] = summary


def add_clue(room_id: str, clue: str):
    """Adiciona uma pista à lista de pistas de uma sala"""
    if room_id not in game_states:
        game_states[room_id] = {"case_summary": "", "clues": [], "chat_history": []}
    if clue not in game_states[room_id]["clues"]:
        game_states[room_id]["clues"].append(clue)


def add_chat_message(room_id: str, username: str, text: str):
    """Adiciona uma mensagem ao histórico de chat de uma sala"""
    if room_id not in game_states:
        game_states[room_id] = {"case_summary": "", "clues": [], "chat_history": []}
    game_states[room_id]["chat_history"].append(f"{username}: {text}")
    # Mantém apenas as últimas 50 mensagens para não sobrecarregar
    if len(game_states[room_id]["chat_history"]) > 50:
        game_states[room_id]["chat_history"] = game_states[room_id]["chat_history"][-50:]


def get_case_summary(room_id: str) -> str:
    """Retorna o resumo do caso de uma sala"""
    if room_id not in game_states:
        return ""
    return game_states[room_id].get("case_summary", "")


def get_clues(room_id: str) -> str:
    """Retorna as pistas de uma sala formatadas"""
    if room_id not in game_states:
        return ""
    clues = game_states[room_id].get("clues", [])
    if not clues:
        return "Nenhuma pista revelada ainda."
    return "\n".join(f"- {clue}" for clue in clues)


def get_chat_history(room_id: str) -> str:
    """Retorna o histórico de chat de uma sala formatado"""
    if room_id not in game_states:
        return ""
    history = game_states[room_id].get("chat_history", [])
    if not history:
        return "Nenhuma conversa ainda."
    return "\n".join(history)


def get_all_clues_list(room_id: str) -> list:
    """Retorna a lista de pistas como lista (não formatada)"""
    if room_id not in game_states:
        return []
    return game_states[room_id].get("clues", [])


def clear_room_state(room_id: str):
    """Limpa o estado de uma sala (útil quando o jogo termina)"""
    if room_id in game_states:
        del game_states[room_id]
