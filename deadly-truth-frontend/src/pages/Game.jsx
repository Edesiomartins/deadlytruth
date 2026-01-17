import { useState, useEffect, useRef } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Game() {
  const { roomId } = useParams();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  
  const [ws, setWs] = useState(null);
  const [connected, setConnected] = useState(false);
  const [gameCase, setGameCase] = useState(null);
  const [players, setPlayers] = useState([]);
  const [currentTurn, setCurrentTurn] = useState(0);
  const [currentPlayerName, setCurrentPlayerName] = useState(null); // Nome do jogador da vez
  const [isMyTurn, setIsMyTurn] = useState(false); // Se é a vez do jogador atual
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [votingActive, setVotingActive] = useState(false); // Se há votação ativa
  const [accusedPlayer, setAccusedPlayer] = useState(null); // Jogador acusado
  const [myVote, setMyVote] = useState(null); // Voto do jogador atual
  const [playerStatus, setPlayerStatus] = useState("alive"); // Status do jogador atual (alive/dead)
  const [playersList, setPlayersList] = useState([]); // Lista de jogadores com status
  const [turnTimeRemaining, setTurnTimeRemaining] = useState(60); // Tempo restante do turno em segundos
  const [gameTimeRemaining, setGameTimeRemaining] = useState(7200); // Tempo restante do jogo em segundos (120 min)
  const [gameElapsedTime, setGameElapsedTime] = useState(0); // Tempo decorrido do jogo
  const [canEndGame, setCanEndGame] = useState(false); // Se já passou o tempo mínimo
  
  const messagesEndRef = useRef(null);
  const turnTimerRef = useRef(null);
  const gameTimerRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Limpa timers ao desmontar
  useEffect(() => {
    return () => {
      if (turnTimerRef.current) {
        clearInterval(turnTimerRef.current);
      }
      if (gameTimerRef.current) {
        clearInterval(gameTimerRef.current);
      }
    };
  }, []);
  
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Conecta ao WebSocket
  useEffect(() => {
    const apiUrl = import.meta.env.VITE_API_URL || "https://deadlytruth-backend-production.up.railway.app";
    const wsUrl = apiUrl.replace(/^http/, 'ws');
    const token = localStorage.getItem('jwt_token');
    
    const websocket = new WebSocket(`${wsUrl}/ws/${roomId}?token=${token}`);
    
    websocket.onopen = () => {
      console.log("🔌 Conectado ao WebSocket");
      setConnected(true);
      setLoading(false);
    };
    
    websocket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log("📨 Mensagem recebida:", data);
        
        if (data.type === "game_start") {
          let caseData = data.payload?.case;
          
          // Se o caso vier como string JSON, tenta parsear
          if (typeof caseData === "string") {
            try {
              caseData = JSON.parse(caseData);
            } catch (e) {
              console.error("Erro ao parsear caso:", e);
              caseData = {
                descricao: caseData.substring(0, 500),
                historia: "",
                local_corpo: "",
                arma_crime: "",
                suspeitos: [],
                evidencias: []
              };
            }
          }
          
          // Garante que seja um objeto
          if (!caseData || typeof caseData !== "object") {
            console.error("Caso inválido recebido:", caseData);
            caseData = {
              descricao: "Um novo mistério foi revelado...",
              historia: "",
              local_corpo: "",
              arma_crime: "",
              suspeitos: [],
              evidencias: []
            };
          }
          
          setGameCase(caseData);
          
          // Mensagem do mestre anunciando o caso
          const caseDesc = caseData.descricao || "Um novo mistério foi revelado...";
          addSystemMessage("🎭 O MESTRE ANUNCIA: O mistério começou!");
          
          // Se a descrição for muito longa, mostra apenas os primeiros caracteres
          if (caseDesc.length > 200) {
            addSystemMessage(`📋 ${caseDesc.substring(0, 200)}...`);
          } else {
            addSystemMessage(`📋 ${caseDesc}`);
          }
        }
        
        if (data.type === "turn_start") {
          setCurrentTurn(data.turn_index || 0);
          const playerName = data.player;
          const playerIdentifier = data.player_identifier || playerName;
          setCurrentPlayerName(playerName);
          
          // Atualiza tempos
          if (data.time_limit) {
            setTurnTimeRemaining(data.time_limit);
          }
          if (data.game_time_remaining !== undefined) {
            setGameTimeRemaining(data.game_time_remaining);
          }
          if (data.game_elapsed_time !== undefined) {
            setGameElapsedTime(data.game_elapsed_time);
          }
          if (data.can_end_game !== undefined) {
            setCanEndGame(data.can_end_game);
          }
          
          // Inicia contador do turno
          if (turnTimerRef.current) {
            clearInterval(turnTimerRef.current);
          }
          let turnTime = data.time_limit || 60;
          turnTimerRef.current = setInterval(() => {
            setTurnTimeRemaining(prev => {
              const newTime = Math.max(0, prev - 1);
              if (newTime === 0) {
                clearInterval(turnTimerRef.current);
              }
              return newTime;
            });
          }, 1000);
          
          // Verifica se é a vez do jogador atual (compara com identifier também)
          const myName = user?.nickname || user?.email?.split('@')[0] || "Você";
          setIsMyTurn(playerName === myName || playerIdentifier === myName);
          
          // Todos são suspeitos - não revela se é bot ou humano
          addSystemMessage(`🔍 Vez de ${playerName} (${turnTime}s)`);
        }
        
        if (data.type === "time_update") {
          if (data.turn_time_remaining !== undefined) {
            setTurnTimeRemaining(data.turn_time_remaining);
          }
          if (data.game_time_remaining !== undefined) {
            setGameTimeRemaining(data.game_time_remaining);
          }
          if (data.game_elapsed_time !== undefined) {
            setGameElapsedTime(data.game_elapsed_time);
          }
          if (data.can_end_game !== undefined) {
            setCanEndGame(data.can_end_game);
          }
        }
        
        if (data.type === "time_out") {
          if (turnTimerRef.current) {
            clearInterval(turnTimerRef.current);
          }
          setTurnTimeRemaining(0);
          addSystemMessage(data.message || `⏰ ${data.player} não agiu a tempo.`);
        }
        
        if (data.type === "bot_message" || data.type === "player_message") {
          // Trata todas as mensagens igualmente - todos são suspeitos
          const playerName = data.player || data.player_id || "Suspeito";
          const messageText = data.message || data.content || "";
          const isDead = data.dead || false;
          addMessage(playerName, messageText, isDead);
        }
        
        if (data.type === "chat") {
          // Formato alternativo de mensagens
          const isDead = data.dead || false;
          addMessage(data.player_id || "Suspeito", data.content || "", isDead);
        }
        
        if (data.type === "turn_change") {
          setCurrentTurn(data.turn_index || 0);
          const playerName = data.current_player;
          setCurrentPlayerName(playerName);
          
          // Verifica se é a vez do jogador atual
          const myName = user?.nickname || user?.email?.split('@')[0] || "Você";
          setIsMyTurn(playerName === myName);
          
          // Todos são suspeitos - não revela se é bot ou humano
          addSystemMessage(`🔍 Vez de ${playerName}`);
        }
        
        if (data.type === "hello") {
          console.log("✅ Conectado à sala", data.payload);
          // Inicializa lista de jogadores se disponível
          if (data.payload?.players) {
            setPlayersList(data.payload.players);
          }
        }
        
        if (data.type === "jogadores" || data.type === "players_update") {
          // Atualiza lista de jogadores
          if (data.players) {
            setPlayersList(data.players);
          }
        }
        
        if (data.type === "error") {
          addSystemMessage(`❌ Erro: ${data.msg || "Ocorreu um erro"}`);
        }
        
        if (data.type === "player_death") {
          const victimName = data.victim || "Jogador";
          addSystemMessage(`💀 ${data.message || `${victimName} foi encontrado morto!`}`);
          if (data.clue) {
            addSystemMessage(`🔍 ${data.clue}`);
          }
          
          // Atualiza status se o jogador morto for o usuário atual
          const myName = user?.nickname || user?.email?.split('@')[0];
          if (victimName === myName) {
            setPlayerStatus("dead");
          }
          
          // Atualiza lista de jogadores
          setPlayersList(prev => prev.map(p => 
            p.name === victimName ? { ...p, status: "dead" } : p
          ));
        }
        
        if (data.type === "game_end") {
          addSystemMessage(`🏆 FIM DO JOGO! ${data.reason || ""}`);
          addSystemMessage(`🎯 Vencedor: ${data.winner_name || data.winner}`);
        }
        
        if (data.type === "you_are_killer") {
          // Mensagem privada apenas para o assassino
          const myName = user?.nickname || user?.email?.split('@')[0] || "Você";
          if (data.player_name === myName || data.player_id) {
            addSystemMessage(`🔪 ${data.message || "Você é o ASSASSINO!"}`);
          }
        }
        
        if (data.type === "status") {
          addSystemMessage(`ℹ️ ${data.msg || ""}`);
        }
        
        if (data.type === "votacao_iniciada") {
          setVotingActive(true);
          setAccusedPlayer(data.accused);
          setMyVote(null); // Reset voto
          addSystemMessage(`⚖️ ${data.message || ""}`);
        }
        
        if (data.type === "resultado_votacao") {
          setVotingActive(false);
          setAccusedPlayer(null);
          setMyVote(null);
          addSystemMessage(data.message || "Votação encerrada.");
        }
        
        if (data.type === "vote_registered") {
          addSystemMessage(data.message || "Voto registrado!");
        }
        
      } catch (e) {
        console.error("Erro ao processar mensagem:", e);
      }
    };
    
    websocket.onerror = (error) => {
      console.error("❌ Erro no WebSocket:", error);
    };
    
    websocket.onclose = () => {
      console.log("🔌 Desconectado do WebSocket");
      setConnected(false);
    };
    
    setWs(websocket);
    
    return () => {
      websocket.close();
    };
  }, [roomId]);

  const addMessage = (player, text) => {
    // Todos são suspeitos - não armazena informação de bot ou função
    setMessages(prev => [...prev, {
      id: Date.now(),
      player,
      text,
      time: new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
    }]);
  };

  const addSystemMessage = (text) => {
    setMessages(prev => [...prev, {
      id: Date.now(),
      system: true,
      text,
      time: new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
    }]);
  };

  const sendMessage = () => {
    // Só permite enviar mensagem se for a vez do jogador
    if (!isMyTurn) {
      addSystemMessage("⏳ Aguarde sua vez para enviar mensagens!");
      return;
    }
    
    if (newMessage.trim() && ws && connected) {
      const messageText = newMessage.trim();
      ws.send(JSON.stringify({
        type: "message",
        text: messageText
      }));
      // Não adiciona imediatamente - espera confirmação do servidor
      setNewMessage("");
    }
  };

  const handleLeave = () => {
    if (ws) ws.close();
    navigate("/lobby");
  };

  const handleVote = (vote) => {
    if (!ws || !connected || myVote !== null) return;
    
    ws.send(JSON.stringify({
      type: "voto",
      value: vote
    }));
    
    setMyVote(vote);
  };

  const handleAccuse = (targetPlayer) => {
    if (!ws || !connected || !isMyTurn) return;
    
    if (window.confirm(`Você tem certeza que quer acusar ${targetPlayer} de ser o assassino?`)) {
      ws.send(JSON.stringify({
        type: "acusar",
        target: targetPlayer
      }));
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-charcoalBlack flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin h-16 w-16 border-4 border-accentRed border-t-transparent rounded-full mx-auto mb-4"></div>
          <p className="text-accentRed font-cinzel text-xl">Conectando ao jogo...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-charcoalBlack relative overflow-hidden">
      {/* Background Effect */}
      <div className="absolute inset-0 bg-gradient-to-br from-primaryRed/20 via-charcoalBlack to-accentRed/10"></div>
      
      {/* Animated Grid */}
      <div className="absolute inset-0 opacity-10">
        <div className="absolute inset-0" style={{
          backgroundImage: `linear-gradient(rgba(220, 20, 60, 0.1) 1px, transparent 1px),
                           linear-gradient(90deg, rgba(220, 20, 60, 0.1) 1px, transparent 1px)`,
          backgroundSize: '50px 50px'
        }}></div>
      </div>

      {/* Header */}
      <div className="relative z-10 border-b border-accentRed/30 backdrop-blur-xl bg-darkGray/60">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <h1 className="text-xl font-bold text-white tracking-wide font-cinzel">
                {gameCase?.case_id || "DEADLY TRUTH"}
              </h1>
              <div className="flex items-center gap-3 mt-1 flex-wrap">
                <p className="text-xs text-accentRed/70 tracking-wider font-roboto">
                  {connected ? "🔴 Ao vivo" : "⚫ Desconectado"}
                </p>
                {currentPlayerName && (
                  <>
                    <span className="text-xs text-mediumGray">•</span>
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-accentRed animate-pulse"></div>
                      <p className="text-xs text-accentRed font-medium font-roboto">
                        Vez de: <span className="text-white">{currentPlayerName}</span>
                      </p>
                      {turnTimeRemaining > 0 && (
                        <span className={`text-xs font-bold font-roboto ${
                          turnTimeRemaining <= 10 ? 'text-red-400 animate-pulse' : 
                          turnTimeRemaining <= 30 ? 'text-yellow-400' : 'text-green-400'
                        }`}>
                          ⏱️ {Math.floor(turnTimeRemaining / 60)}:{(turnTimeRemaining % 60).toString().padStart(2, '0')}
                        </span>
                      )}
                    </div>
                  </>
                )}
                <span className="text-xs text-mediumGray">•</span>
                <div className="flex items-center gap-2">
                  <p className="text-xs text-offWhite/70 font-roboto">
                    🕐 {Math.floor(gameElapsedTime / 60)}:{(gameElapsedTime % 60).toString().padStart(2, '0')} / {Math.floor(gameTimeRemaining / 60)}:{(gameTimeRemaining % 60).toString().padStart(2, '0')} restante
                  </p>
                  {!canEndGame && (
                    <span className="text-xs text-yellow-400 font-roboto">
                      (Mín: 30min)
                    </span>
                  )}
                </div>
              </div>
            </div>
            
            <button 
              onClick={handleLeave}
              className="px-4 py-2 bg-primaryRed/20 hover:bg-accentRed/30 border border-accentRed/30 rounded-lg text-accentRed text-sm font-medium tracking-wide transition-all font-roboto"
            >
              Sair da Partida
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="relative z-10 h-[calc(100vh-73px)] flex">
        {/* Left Panel - Case Info */}
        <div className="w-96 border-r border-accentRed/30 backdrop-blur-xl bg-darkGray/40 flex flex-col overflow-y-auto">
          <div className="px-4 py-3 border-b border-accentRed/30">
            <h2 className="text-xs tracking-widest text-accentRed/70 uppercase font-light font-roboto">
              O Caso
            </h2>
          </div>
          
          {gameCase ? (
            <div className="p-4 space-y-4">
              {/* Garante que gameCase seja um objeto */}
              {(() => {
                if (typeof gameCase === 'string') {
                  try {
                    const parsed = JSON.parse(gameCase);
                    gameCase = parsed;
                    setGameCase(parsed); // Atualiza o estado
                  } catch (e) {
                    console.error("Erro ao parsear caso:", e);
                  }
                }
                return null;
              })()}
              
              {gameCase?.descricao && (
                <div>
                  <h3 className="text-sm font-bold text-white mb-2 font-cinzel">Descrição</h3>
                  <p className="text-sm text-offWhite/80 font-roboto leading-relaxed whitespace-pre-wrap">
                    {String(gameCase.descricao)}
                  </p>
                </div>
              )}
              
              {gameCase?.historia && (
                <div>
                  <h3 className="text-sm font-bold text-white mb-2 font-cinzel">História</h3>
                  <p className="text-sm text-offWhite/80 font-roboto leading-relaxed whitespace-pre-wrap">
                    {String(gameCase.historia)}
                  </p>
                </div>
              )}
              
              {gameCase?.local_corpo && (
                <div>
                  <h3 className="text-sm font-bold text-white mb-2 font-cinzel">Local do Crime</h3>
                  <p className="text-sm text-offWhite/80 font-roboto">
                    🏛️ {String(gameCase.local_corpo)}
                  </p>
                </div>
              )}
              
              {gameCase?.arma_crime && (
                <div>
                  <h3 className="text-sm font-bold text-white mb-2 font-cinzel">Arma do Crime</h3>
                  <p className="text-sm text-offWhite/80 font-roboto">
                    ⚔️ {String(gameCase.arma_crime)}
                  </p>
                </div>
              )}

              {gameCase.suspeitos && gameCase.suspeitos.length > 0 && (
                <div>
                  <h3 className="text-sm font-bold text-white mb-2 font-cinzel">Suspeitos</h3>
                  <ul className="space-y-2">
                    {gameCase.suspeitos.map((suspeito, idx) => (
                      <li key={idx} className="text-sm text-offWhite/80 font-roboto">
                        • {suspeito}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {gameCase.evidencias && gameCase.evidencias.length > 0 && (
                <div>
                  <h3 className="text-sm font-bold text-white mb-2 font-cinzel">Evidências</h3>
                  <ul className="space-y-2">
                    {gameCase.evidencias.map((evidencia, idx) => (
                      <li key={idx} className="text-sm text-offWhite/80 font-roboto">
                        🔍 {evidencia}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <div className="p-4 text-center text-lightGray/50">
              <p className="font-roboto">Aguardando o mestre gerar o caso...</p>
            </div>
          )}
          
          {/* Lista de Jogadores */}
          <div className="mt-auto border-t border-accentRed/30 p-4">
            <div className="mb-4">
              <h3 className="text-xs font-bold text-accentRed/70 uppercase tracking-wider font-roboto mb-2">
                🎮 Jogadores
              </h3>
              <ul className="space-y-1">
                {playersList.filter(p => p.status === "alive" || !p.status).map((p, idx) => (
                  <li key={idx} className="text-xs text-offWhite/80 font-roboto flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-green-500"></div>
                    {p.name || p.id || `Jogador ${idx + 1}`}
                  </li>
                ))}
              </ul>
            </div>
            
            {playersList.filter(p => p.status === "dead").length > 0 && (
              <div>
                <h3 className="text-xs font-bold text-gray-400/70 uppercase tracking-wider font-roboto mb-2">
                  👻 Espectadores
                </h3>
                <ul className="space-y-1">
                  {playersList.filter(p => p.status === "dead").map((p, idx) => (
                    <li key={idx} className="text-xs text-gray-400/60 font-roboto flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-gray-500"></div>
                      {p.name || p.id || `Jogador ${idx + 1}`}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>

        {/* Right Panel - Chat */}
        <div className="flex-1 flex flex-col backdrop-blur-xl bg-darkGray/20">
          <div className="px-4 py-3 border-b border-accentRed/30">
            <h2 className="text-xs tracking-widest text-accentRed/70 uppercase font-light font-roboto">
              Investigação
            </h2>
          </div>
          
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {messages.map((msg) => (
              <div key={msg.id} className={`${msg.system ? 'text-center' : ''}`}>
                {msg.system ? (
                  <div className="inline-block px-3 py-1 rounded-full bg-primaryRed/30 border border-accentRed/30">
                    <p className="text-xs text-accentRed/70 font-roboto">{msg.text}</p>
                  </div>
                ) : (
                  <div className={`bg-charcoalBlack/50 border rounded-lg p-3 ${msg.dead ? 'border-gray-600/50 opacity-70' : 'border-primaryRed/20'}`}>
                    <div className="flex items-baseline gap-2 mb-1">
                      <span className={`text-xs font-medium font-roboto ${msg.dead ? 'text-gray-400' : 'text-accentRed'}`}>
                        {msg.dead ? "👻 " : ""}{msg.player}
                      </span>
                      <span className="text-xs text-mediumGray font-roboto">{msg.time}</span>
                    </div>
                    <p className={`text-sm font-roboto ${msg.dead ? 'text-gray-400' : 'text-offWhite'}`}>{msg.text}</p>
                  </div>
                )}
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
          
          {/* Votação Ativa */}
          {votingActive && accusedPlayer && (
            <div className="p-4 border-t border-accentRed/30 bg-accentRed/10">
              <div className="mb-3">
                <p className="text-sm font-bold text-accentRed font-cinzel mb-2">
                  ⚖️ Acusação contra {accusedPlayer}
                </p>
                <p className="text-xs text-offWhite/70 font-roboto mb-3">
                  Vote se você acredita que {accusedPlayer} é o assassino:
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => handleVote("culpado")}
                  disabled={myVote !== null || !connected}
                  className={`flex-1 px-4 py-2 rounded-lg font-medium transition-all font-roboto ${
                    myVote === "culpado"
                      ? "bg-red-600 text-white"
                      : myVote === null
                      ? "bg-red-500/20 hover:bg-red-500/30 border border-red-500/40 text-red-400"
                      : "bg-charcoalBlack/50 border border-primaryRed/20 text-mediumGray cursor-not-allowed"
                  } disabled:opacity-50 disabled:cursor-not-allowed`}
                >
                  🔴 Culpado
                </button>
                <button
                  onClick={() => handleVote("inocente")}
                  disabled={myVote !== null || !connected}
                  className={`flex-1 px-4 py-2 rounded-lg font-medium transition-all font-roboto ${
                    myVote === "inocente"
                      ? "bg-green-600 text-white"
                      : myVote === null
                      ? "bg-green-500/20 hover:bg-green-500/30 border border-green-500/40 text-green-400"
                      : "bg-charcoalBlack/50 border border-primaryRed/20 text-mediumGray cursor-not-allowed"
                  } disabled:opacity-50 disabled:cursor-not-allowed`}
                >
                  🟢 Inocente
                </button>
              </div>
              {myVote && (
                <p className="text-xs text-accentRed/70 font-roboto mt-2 text-center">
                  ✅ Você votou: {myVote === "culpado" ? "🔴 Culpado" : "🟢 Inocente"}
                </p>
              )}
            </div>
          )}
          
          {/* Input */}
          <div className="p-4 border-t border-accentRed/30">
            {playerStatus === "dead" ? (
              <div className="px-3 py-4 bg-gray-800/50 border border-gray-600/50 rounded-lg text-center">
                <p className="text-sm text-gray-400 font-roboto mb-1">
                  👻 Você está morto
                </p>
                <p className="text-xs text-gray-500 font-roboto">
                  Observando o jogo...
                </p>
              </div>
            ) : (
              <>
                {!isMyTurn && currentPlayerName && (
                  <div className="mb-2 px-3 py-2 bg-accentRed/20 border border-accentRed/30 rounded-lg">
                    <p className="text-xs text-accentRed/80 font-roboto text-center">
                      ⏳ Aguarde sua vez. É a vez de <span className="font-bold text-accentRed">{currentPlayerName}</span>
                    </p>
                  </div>
                )}
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newMessage}
                    onChange={(e) => setNewMessage(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                    placeholder={isMyTurn ? "Digite sua mensagem..." : "Aguarde sua vez..."}
                    className="flex-1 px-3 py-2 bg-charcoalBlack/50 border border-primaryRed/40 rounded-lg text-sm text-offWhite placeholder-lightGray/50 focus:outline-none focus:border-accentRed/60 focus:ring-2 focus:ring-accentRed/20 transition-all font-roboto disabled:opacity-50 disabled:cursor-not-allowed"
                    disabled={!connected || !isMyTurn}
                  />
                  <button
                    onClick={sendMessage}
                    disabled={!connected || !isMyTurn}
                    className="px-4 py-2 bg-primaryRed hover:bg-accentRed rounded-lg text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    title={!isMyTurn ? "Aguarde sua vez" : "Enviar mensagem"}
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                    </svg>
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
