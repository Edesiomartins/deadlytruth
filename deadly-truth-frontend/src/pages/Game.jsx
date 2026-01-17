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
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState("");
  const [loading, setLoading] = useState(true);
  
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

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
          setGameCase(data.payload.case);
          addSystemMessage("🎭 O mistério começou! Investigue com cuidado...");
        }
        
        if (data.type === "turn_start") {
          setCurrentTurn(data.turn_index || 0);
          const playerName = data.player;
          // Todos são suspeitos - não revela se é bot ou humano
          addSystemMessage(`🔍 Vez de ${playerName}`);
        }
        
        if (data.type === "bot_message" || data.type === "player_message") {
          // Trata todas as mensagens igualmente - todos são suspeitos
          const playerName = data.player || data.player_id || "Suspeito";
          const messageText = data.message || data.content || "";
          addMessage(playerName, messageText);
        }
        
        if (data.type === "chat") {
          // Formato alternativo de mensagens
          addMessage(data.player_id || "Suspeito", data.content || "");
        }
        
        if (data.type === "turn_change") {
          setCurrentTurn(data.turn_index || 0);
          const playerName = data.current_player;
          // Todos são suspeitos - não revela se é bot ou humano
          addSystemMessage(`🔍 Vez de ${playerName}`);
        }
        
        if (data.type === "hello") {
          console.log("✅ Conectado à sala", data.payload);
        }
        
        if (data.type === "error") {
          addSystemMessage(`❌ Erro: ${data.msg || "Ocorreu um erro"}`);
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
            <div>
              <h1 className="text-xl font-bold text-white tracking-wide font-cinzel">
                {gameCase?.case_id || "DEADLY TRUTH"}
              </h1>
              <p className="text-xs text-accentRed/70 tracking-wider font-roboto">
                {connected ? "🔴 Ao vivo" : "⚫ Desconectado"}
              </p>
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
                  <div className="bg-charcoalBlack/50 border border-primaryRed/20 rounded-lg p-3">
                    <div className="flex items-baseline gap-2 mb-1">
                      <span className="text-xs font-medium text-accentRed font-roboto">
                        {msg.player}
                      </span>
                      <span className="text-xs text-mediumGray font-roboto">{msg.time}</span>
                    </div>
                    <p className="text-sm text-offWhite font-roboto">{msg.text}</p>
                  </div>
                )}
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
          
          {/* Input */}
          <div className="p-4 border-t border-accentRed/30">
            <div className="flex gap-2">
              <input
                type="text"
                value={newMessage}
                onChange={(e) => setNewMessage(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                placeholder="Digite sua mensagem..."
                className="flex-1 px-3 py-2 bg-charcoalBlack/50 border border-primaryRed/40 rounded-lg text-sm text-offWhite placeholder-lightGray/50 focus:outline-none focus:border-accentRed/60 focus:ring-2 focus:ring-accentRed/20 transition-all font-roboto"
                disabled={!connected}
              />
              <button
                onClick={sendMessage}
                disabled={!connected}
                className="px-4 py-2 bg-primaryRed hover:bg-accentRed rounded-lg text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
