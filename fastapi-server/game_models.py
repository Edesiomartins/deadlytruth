"""
Modelos SQLAlchemy para persistência de estado do jogo.
Permite recuperação pós-reboot, desconexões e escalabilidade.
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, Float, DateTime, ForeignKey, UniqueConstraint, func, CheckConstraint, JSON as SQLJSON
from sqlalchemy.orm import relationship

from database import Base


class GameRoom(Base):
    """Sala de jogo com metadados do caso."""
    __tablename__ = "game_rooms"

    id = Column(Integer, primary_key=True, autoincrement=True)
    room_id = Column(String(16), unique=True, nullable=False, index=True)
    case_json = Column(Text, nullable=True)  # JSON serializado do caso
    case_summary = Column(Text, nullable=True)
    current_turn_player_id = Column(String(128), nullable=True)
    killer_id = Column(String(128), nullable=True)
    accused_player = Column(String(128), nullable=True)  # Jogador sendo votado
    votes_json = Column(Text, nullable=True)  # {"voter_id": "culpado|inocente"}
    game_active = Column(Boolean, default=False)
    game_start_time = Column(Float, nullable=True)
    game_min_duration = Column(Float, default=1800.0)  # 30 min
    game_max_duration = Column(Float, default=7200.0)  # 120 min
    kills_this_round = Column(Integer, default=0)
    round_number = Column(Integer, default=0)
    scenario = Column(String(64), nullable=True)
    difficulty = Column(String(32), default="Iniciante")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    players = relationship("GamePlayer", back_populates="room", cascade="all, delete-orphan")
    clues = relationship("GameClue", back_populates="room", cascade="all, delete-orphan")
    chat_messages = relationship("GameChatMessage", back_populates="room", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<GameRoom {self.room_id} active={self.game_active}>"


class GamePlayer(Base):
    """Jogador registrado em uma sala."""
    __tablename__ = "game_players"

    __table_args__ = (
        UniqueConstraint("room_id", "player_index", name="uq_room_player_index"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    room_id = Column(String(16), ForeignKey("game_rooms.room_id", ondelete="CASCADE"), nullable=False, index=True)
    player_index = Column(Integer, nullable=False)  # Posição na lista (0-based)
    name = Column(String(128), nullable=False)
    string_id = Column(String(128), nullable=True)  # O ID original (string)
    numeric_id = Column(Integer, nullable=True)  # ID numérico (1-based)
    is_bot = Column(Boolean, default=False)
    is_killer = Column(Boolean, default=False)
    status = Column(String(16), default="alive")  # alive, dead
    is_connected = Column(Boolean, default=True)
    disconnect_time = Column(Float, nullable=True)
    email = Column(String(255), nullable=True)

    room = relationship("GameRoom", back_populates="players")

    def __repr__(self):
        return f"<GamePlayer {self.name} room={self.room_id} status={self.status}>"


class GameClue(Base):
    """Pista descoberta em uma sala."""
    __tablename__ = "game_clues"

    id = Column(Integer, primary_key=True, autoincrement=True)
    room_id = Column(String(16), ForeignKey("game_rooms.room_id", ondelete="CASCADE"), nullable=False, index=True)
    clue_text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    room = relationship("GameRoom", back_populates="clues")

    __repr__ = lambda self: f"<GameClue id={self.id} room={self.room_id}>"


class GameChatMessage(Base):
    """Mensagem de chat em uma sala."""
    __tablename__ = "game_chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    room_id = Column(String(16), ForeignKey("game_rooms.room_id", ondelete="CASCADE"), nullable=False, index=True)
    username = Column(String(128), nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    room = relationship("GameRoom", back_populates="chat_messages")

    __repr__ = lambda self: f"<GameChatMessage id={self.id} user={self.username}>"


class BotMemoryEntry(Base):
    """Memória acumulada de um bot em uma sala."""
    __tablename__ = "bot_memory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    room_id = Column(String(16), nullable=False, index=True)
    bot_name = Column(String(128), nullable=False, index=True)
    accumulated_clues = Column(Text, nullable=True)  # JSON list de pistas que o bot "sabe"
    suspicion_scores_json = Column(Text, nullable=True)  # JSON {"player_name": float}
    alliance_with_json = Column(Text, nullable=True)  # JSON list de aliados
    past_statements_json = Column(Text, nullable=True)  # JSON list de {msg, timestamp}
    personality = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __repr__ = lambda self: f"<BotMemory bot={self.bot_name} room={self.room_id}>"
