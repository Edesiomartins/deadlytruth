# fastapi-server/game_state.py

"""
Gerencia o estado do jogo de forma centralizada.
Armazena resumo do caso, pistas, histórico de chat por sala.
"""

# Armazena o estado do jogo por sala (room_id)
# Estrutura: {room_id: {"case_summary": str, "clues": list, "chat_history": list, "current_turn": str, "killer_id": str, "players": dict}}
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


# ======== Controle de Turno ========

def set_current_turn(room_id: str, player_id: str):
    """Define o jogador atual da vez para uma sala"""
    if room_id not in game_states:
        game_states[room_id] = {"case_summary": "", "clues": [], "chat_history": [], "current_turn": None, "killer_id": None, "players": {}}
    game_states[room_id]["current_turn"] = player_id


def get_current_turn(room_id: str) -> str:
    """Retorna o ID do jogador atual da vez"""
    if room_id not in game_states:
        return None
    return game_states[room_id].get("current_turn")


# ======== Controle de Assassino ========

def set_killer_id(room_id: str, killer_id: str):
    """Define o ID do assassino para uma sala"""
    if room_id not in game_states:
        game_states[room_id] = {"case_summary": "", "clues": [], "chat_history": [], "current_turn": None, "killer_id": None, "players": {}}
    game_states[room_id]["killer_id"] = killer_id


def get_killer_id(room_id: str) -> str:
    """Retorna o ID do assassino"""
    if room_id not in game_states:
        return None
    return game_states[room_id].get("killer_id")


# ======== Status dos Jogadores ========

def register_player(room_id: str, player_id: str):
    """Registra um jogador na sala com status 'alive'"""
    if room_id not in game_states:
        game_states[room_id] = {"case_summary": "", "clues": [], "chat_history": [], "current_turn": None, "killer_id": None, "players": {}}
    if "players" not in game_states[room_id]:
        game_states[room_id]["players"] = {}
    game_states[room_id]["players"][player_id] = {"status": "alive"}


def is_alive(room_id: str, player_id: str) -> bool:
    """Verifica se um jogador está vivo"""
    if room_id not in game_states:
        return False
    players = game_states[room_id].get("players", {})
    return players.get(player_id, {}).get("status") == "alive"


def kill_player_state(room_id: str, player_id: str):
    """Marca um jogador como morto"""
    if room_id not in game_states:
        return
    if "players" not in game_states[room_id]:
        game_states[room_id]["players"] = {}
    if player_id in game_states[room_id]["players"]:
        game_states[room_id]["players"][player_id]["status"] = "dead"
    else:
        game_states[room_id]["players"][player_id] = {"status": "dead"}


def get_player_status(room_id: str, player_id: str) -> str:
    """Retorna o status de um jogador (alive, dead, unknown)"""
    if room_id not in game_states:
        return "unknown"
    players = game_states[room_id].get("players", {})
    return players.get(player_id, {}).get("status", "unknown")


# ======== Sistema de Votação ========

def start_vote(room_id: str, accused_id: str):
    """Inicia uma votação para acusar um jogador"""
    if room_id not in game_states:
        game_states[room_id] = {
            "case_summary": "", 
            "clues": [], 
            "chat_history": [], 
            "current_turn": None, 
            "killer_id": None, 
            "players": {}, 
            "accused_player": None, 
            "votes": {}
        }
    if "accused_player" not in game_states[room_id]:
        game_states[room_id]["accused_player"] = None
    if "votes" not in game_states[room_id]:
        game_states[room_id]["votes"] = {}
    game_states[room_id]["accused_player"] = accused_id
    game_states[room_id]["votes"] = {}  # Reset votos


def submit_vote(room_id: str, voter_id: str, vote: str):
    """Registra o voto de um jogador"""
    if room_id not in game_states:
        return
    if "votes" not in game_states[room_id]:
        game_states[room_id]["votes"] = {}
    game_states[room_id]["votes"][voter_id] = vote.lower()


def all_votes_in(room_id: str, voters_alive: list[str]) -> bool:
    """Verifica se todos os jogadores vivos já votaram"""
    if room_id not in game_states:
        return False
    votes = game_states[room_id].get("votes", {})
    return all(voter in votes for voter in voters_alive)


def get_vote_result(room_id: str) -> tuple:
    """Retorna o resultado da votação (culpado_votes, inocente_votes)"""
    if room_id not in game_states:
        return (0, 0)
    votes = game_states[room_id].get("votes", {})
    guilt_votes = sum(1 for v in votes.values() if v == "culpado")
    innocent_votes = sum(1 for v in votes.values() if v == "inocente")
    return (guilt_votes, innocent_votes)


def get_accused_player(room_id: str) -> str:
    """Retorna o ID do jogador acusado"""
    if room_id not in game_states:
        return None
    return game_states[room_id].get("accused_player")


def clear_vote(room_id: str):
    """Limpa a votação atual"""
    if room_id in game_states:
        game_states[room_id]["accused_player"] = None
        game_states[room_id]["votes"] = {}
