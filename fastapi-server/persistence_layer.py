"""
Camada de persistência que faz ponte entre o estado em memória (ROOMS) e o banco de dados.

Fluxo:
  1. Cada flush salva snapshots do estado in-memory → DB
  2. No startup, tenta carregar salas ativas do DB → memória
  3. Endpoints HTTP permitem recuperação de estado pós-reconnect
"""

import json
import logging
from typing import Optional

from database import SessionLocal
from game_models import GameRoom, GamePlayer, GameClue, GameChatMessage, BotMemoryEntry

logger = logging.getLogger(__name__)


def _json_dumps(obj) -> Optional[str]:
    """Serializa objeto para JSON string de forma segura."""
    if obj is None:
        return None
    try:
        return json.dumps(obj, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(obj)


def _json_loads(text: Optional[str], default=None):
    """Deserializa JSON string de forma segura."""
    if not text:
        return default
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return default


# ============================================================
# SALVAR ESTADO DO ROOM → DB
# ============================================================

def flush_room_to_db(room_id: str, room_data: dict) -> bool:
    """
    Salva o estado completo de uma sala no banco de dados.
    É chamado periodicamente e em eventos importantes (morte, fim de jogo, etc.).
    """
    db = SessionLocal()
    try:
        room_record = db.query(GameRoom).filter(GameRoom.room_id == room_id).first()

        if room_record:
            # UPDATE
            room_record.case_json = _json_dumps(room_data.get("case"))
            room_record.current_turn_player_id = room_data.get("current_turn_id") or room_data.get("current_turn")
            room_record.game_active = room_data.get("game_active", False)
            room_record.game_start_time = room_data.get("game_start_time")
            room_record.kills_this_round = room_data.get("kills_this_round", 0)
            room_record.round_number = room_data.get("round_number", 0)
            room_record.scenario = room_data.get("cenario")
            room_record.difficulty = room_data.get("nivel")
        else:
            # INSERT
            room_record = GameRoom(
                room_id=room_id,
                case_json=_json_dumps(room_data.get("case")),
                current_turn_player_id=room_data.get("current_turn_id") or room_data.get("current_turn"),
                game_active=room_data.get("game_active", False),
                game_start_time=room_data.get("game_start_time"),
                kills_this_round=room_data.get("kills_this_round", 0),
                round_number=room_data.get("round_number", 0),
                scenario=room_data.get("cenario"),
                difficulty=room_data.get("nivel"),
            )
            db.add(room_record)

        db.flush()  # Garante que room_record.id está disponível

        # Sync players
        _sync_players(db, room_id, room_data.get("players", []))

        db.commit()
        logger.info(f"💾 Sala {room_id} salva no banco de dados")
        return True

    except Exception as e:
        db.rollback()
        logger.error(f"❌ Erro ao salvar sala {room_id} no banco: {e}")
        return False
    finally:
        db.close()


def _sync_players(db, room_id: str, players: list):
    """Sincroniza jogadores da sala no banco (deleta e reinsere para simplicidade)."""
    db.query(GamePlayer).filter(GamePlayer.room_id == room_id).delete()

    for idx, p in enumerate(players):
        if not isinstance(p, dict):
            continue
        db.add(GamePlayer(
            room_id=room_id,
            player_index=idx,
            name=p.get("name", f"Jogador_{idx}"),
            string_id=p.get("id"),
            numeric_id=p.get("numeric_id", idx + 1),
            is_bot=p.get("is_bot") or p.get("isBot", False),
            is_killer=p.get("is_killer", False),
            status=p.get("status", "alive"),
            is_connected=p.get("is_connected", True),
            disconnect_time=p.get("disconnect_time"),
            email=p.get("email"),
        ))


def flush_clue_to_db(room_id: str, clue_text: str):
    """Salva uma pista individual no banco."""
    db = SessionLocal()
    try:
        db.add(GameClue(room_id=room_id, clue_text=clue_text))
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Erro ao salvar pista na sala {room_id}: {e}")
    finally:
        db.close()


def flush_chat_to_db(room_id: str, username: str, text: str):
    """Salva uma mensagem de chat no banco."""
    db = SessionLocal()
    try:
        db.add(GameChatMessage(room_id=room_id, username=username, text=text))
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Erro ao salvar chat na sala {room_id}: {e}")
    finally:
        db.close()


def flush_killer_to_db(room_id: str, killer_id: str):
    """Salva o ID do assassino no banco."""
    db = SessionLocal()
    try:
        room = db.query(GameRoom).filter(GameRoom.room_id == room_id).first()
        if room:
            room.killer_id = killer_id
            db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Erro ao salvar killer na sala {room_id}: {e}")
    finally:
        db.close()


def flush_turn_to_db(room_id: str, player_id: str):
    """Salva o turno atual no banco."""
    db = SessionLocal()
    try:
        room = db.query(GameRoom).filter(GameRoom.room_id == room_id).first()
        if room:
            room.current_turn_player_id = player_id
            db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Erro ao salvar turno na sala {room_id}: {e}")
    finally:
        db.close()


def flush_game_end_to_db(room_id: str):
    """Marca o jogo como terminado no banco."""
    db = SessionLocal()
    try:
        room = db.query(GameRoom).filter(GameRoom.room_id == room_id).first()
        if room:
            room.game_active = False
            db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Erro ao marcar game_end na sala {room_id}: {e}")
    finally:
        db.close()


# ============================================================
# CARREGAR ESTADO DO DB → MEMÓRIA
# ============================================================

def load_active_rooms():
    """
    Carrega salas ativas do banco de dados para memória.
    Retorna dict {room_id: {"room_data": {...}, "players": [...], "clues": [...], "chat": [...]}}
    Chamado no startup do servidor para recuperação pós-reboot.
    """
    db = SessionLocal()
    active_rooms = {}
    try:
        rooms = db.query(GameRoom).filter(GameRoom.game_active == True).all()

        for room in rooms:
            room_data = {
                "case": _json_loads(room.case_json, {}),
                "current_turn": room.current_turn_player_id or 0,
                "current_turn_id": room.current_turn_player_id,
                "game_active": room.game_active,
                "game_start_time": room.game_start_time,
                "kills_this_round": room.kills_this_round,
                "round_number": room.round_number,
                "cenario": room.scenario,
                "nivel": room.difficulty,
                "chat": [],
                "players": [],
            }

            # Carrega jogadores (ordenados por player_index)
            players = (
                db.query(GamePlayer)
                .filter(GamePlayer.room_id == room.room_id)
                .order_by(GamePlayer.player_index)
                .all()
            )
            for p in players:
                room_data["players"].append({
                    "id": p.string_id,
                    "name": p.name,
                    "numeric_id": p.numeric_id,
                    "is_bot": p.is_bot,
                    "isBot": p.is_bot,
                    "is_killer": p.is_killer,
                    "status": p.status,
                    "is_connected": p.is_connected,
                    "disconnect_time": p.disconnect_time,
                    "email": p.email,
                })

            # Carrega pistas
            clues = (
                db.query(GameClue)
                .filter(GameClue.room_id == room.room_id)
                .order_by(GameClue.created_at)
                .all()
            )
            room_data["clues"] = [c.clue_text for c in clues]

            # Carrega últimas 50 mensagens de chat
            chat_msgs = (
                db.query(GameChatMessage)
                .filter(GameChatMessage.room_id == room.room_id)
                .order_by(GameChatMessage.created_at.desc())
                .limit(50)
                .all()
            )
            room_data["chat"] = [
                {"player": m.username, "text": m.text}
                for m in reversed(chat_msgs)
            ]

            active_rooms[room.room_id] = room_data
            logger.info(f"🔄 Sala recuperada do banco: {room.room_id} ({len(room_data['players'])} jogadores)")

    except Exception as e:
        logger.error(f"❌ Erro ao carregar salas ativas do banco: {e}")
    finally:
        db.close()

    return active_rooms


# ============================================================
# ENDPOINT DE RECUPERAÇÃO DE ESTADO
# ============================================================

def get_room_state_snapshot(room_id: str) -> Optional[dict]:
    """
    Retorna um snapshot completo do estado de uma sala do banco.
    Usado pelo endpoint GET /room/{room_id}/state para recuperação pós-reconnect.
    """
    db = SessionLocal()
    try:
        room = db.query(GameRoom).filter(GameRoom.room_id == room_id).first()
        if not room:
            return None

        players = (
            db.query(GamePlayer)
            .filter(GamePlayer.room_id == room_id)
            .order_by(GamePlayer.player_index)
            .all()
        )
        clues = (
            db.query(GameClue)
            .filter(GameClue.room_id == room_id)
            .order_by(GameClue.created_at)
            .all()
        )
        chat_msgs = (
            db.query(GameChatMessage)
            .filter(GameChatMessage.room_id == room_id)
            .order_by(GameChatMessage.created_at.desc())
            .limit(30)
            .all()
        )

        return {
            "room_id": room.room_id,
            "game_active": room.game_active,
            "current_turn_player_id": room.current_turn_player_id,
            "killer_id": room.killer_id,
            "scenario": room.scenario,
            "difficulty": room.difficulty,
            "game_start_time": room.game_start_time,
            "case": _json_loads(room.case_json, {}),
            "players": [
                {
                    "name": p.name,
                    "numeric_id": p.numeric_id,
                    "status": p.status,
                    "is_bot": p.is_bot,
                    "is_killer": p.is_killer,
                    "is_connected": p.is_connected,
                }
                for p in players
            ],
            "clues": [c.clue_text for c in clues],
            "recent_chat": [
                {"player": m.username, "text": m.text}
                for m in reversed(chat_msgs)
            ],
        }
    except Exception as e:
        logger.error(f"❌ Erro ao recuperar snapshot da sala {room_id}: {e}")
        return None
    finally:
        db.close()
