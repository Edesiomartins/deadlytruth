import React, { useState, useEffect, useRef } from 'react';
import { User, Lock, Ghost, MessageSquare, Timer, Search, AlertCircle, Users } from 'lucide-react';

// --- CONFIGURAÇÃO ---
const BACKEND_URL = "wss://deadlytruth.onrender.com/ws/sala_geral"; // URL do seu backend WebSocket

// --- PALETA DE CORES ---
const COLORS = {
  primaryRed: '#8B0000',    // Dark Crimson
  accentRed: '#DC143C',     // Crimson Red
  lightRed: '#C41E3A',      // Medium Crimson
  charcoalBlack: '#0F0F0F', // Charcoal Black
  darkGray: '#1A1A1A',      // Dark Gray
  mediumGray: '#2A2A2A',    // Medium Gray
  white: '#FFFFFF',         // Pure White
  offWhite: '#F5F5F5',      // Off-white
  agedGold: '#D4AF37',      // Aged Gold
  lightGold: '#C9A961',     // Lighter Aged Gold
};

// --- COMPONENTE PRINCIPAL ---
function App() {
  const [socket, setSocket] = useState(null);
  const [gameState, setGameState] = useState({ 
    players: [], 
    total_players: 0, 
    game_active: false, 
    player_id: null, 
    case: null,
    scenario: null // Adicionado para o cenário
  });
  const [messages, setMessages] = useState([]);
  const [inputMsg, setInputMsg] = useState("");
  const chatEndRef = useRef(null);
  const playerSlotsRef = useRef(null); // Ref para o container dos slots

  // --- EFEITO: CONEXÃO WEBSOCKET ---
  useEffect(() => {
    const ws = new WebSocket(BACKEND_URL);
    ws.onopen = () => {
      console.log("Conectado ao Deadly Truth");
      setSocket(ws);
    };
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log("Mensagem do servidor:", data);

        if (data.type === "game_start" || data.type === "hello") {
          // Atualiza o estado do jogo e a história (case)
          setGameState(prev => ({ 
            ...prev, 
            ...data.payload, 
            game_active: data.type === "game_start" ? true : prev.game_active,
            case: data.payload.case || prev.case 
          }));
        }

        // Lógica para acumular mensagens no chat
        if (data.type === "chat" || data.type === "status" || data.type === "game_start") {
          const msgContent = data.content || data.payload?.msg || data.payload || data.msg;
          const sender = data.player_id || (data.type === "status" ? "SISTEMA" : "MESTRE");
          
          if (msgContent) {
            setMessages(prev => [...prev, { 
              player_id: sender, 
              content: typeof msgContent === 'string' ? msgContent : JSON.stringify(msgContent),
              isSystem: data.type === "status" || data.type === "game_start"
            }]);
          }
        } else if (data.type === "action") {
          // Mensagens de ação também aparecem no chat
          const msgContent = data.content || "Realizou uma ação";
          const sender = data.player_id || "Mestre";
          setMessages(prev => [...prev, { 
            player_id: sender, 
            content: msgContent,
            isSystem: false
          }]);
        } else if (data.type === "turn_start") {
          setMessages(prev => [...prev, { 
            player_id: "SISTEMA", 
            content: `Cuidado: É o turno do Suspeito ${data.player || data.player_id}`,
            isSystem: true
          }]);
        }
      } catch (e) { 
        console.error("Erro no processamento:", e); 
      }
    };
    ws.onclose = () => {
      console.log("Desconectado do Deadly Truth");
      setSocket(null);
      setGameState(prev => ({ ...prev, game_active: false })); // Resetar estado do jogo
    };
    ws.onerror = (error) => {
      console.error("Erro no WebSocket:", error);
    };
    return () => ws.close();
  }, []);

  // --- EFEITO: AUTO-SCROLL DO CHAT ---
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // --- FUNÇÃO: ENVIAR AÇÃO ---
  const sendAction = () => {
    if (socket && inputMsg.trim() && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: "action", content: inputMsg.trim() }));
      setInputMsg("");
    }
  };

  // --- ESTILOS INLINE PARA GRADIENTES E CORES ---
  const bgGradient = {
    background: `linear-gradient(135deg, ${COLORS.charcoalBlack} 0%, ${COLORS.darkGray} 100%)`,
    fontFamily: "'Cinzel', serif", // Usando uma fonte serifada para atmosfera
  };

  const titleGradient = {
    background: `linear-gradient(135deg, ${COLORS.accentRed} 0%, ${COLORS.primaryRed} 100%)`,
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
    filter: `drop-shadow(0 0 20px ${COLORS.primaryRed}50)`,
  };

  const statusBarGradient = {
    background: `linear-gradient(135deg, ${COLORS.darkGray} 0%, ${COLORS.mediumGray} 100%)`,
    borderColor: `${COLORS.primaryRed}50`,
  };

  const cardActiveGradient = {
    background: `linear-gradient(135deg, ${COLORS.primaryRed}30 0%, ${COLORS.lightRed}15 100%)`,
    borderColor: COLORS.primaryRed,
  };

  const cardInactiveGradient = {
    background: `${COLORS.darkGray}50`,
    borderColor: `${COLORS.mediumGray}50`,
  };

  const buttonGradient = {
    background: `linear-gradient(135deg, ${COLORS.primaryRed} 0%, ${COLORS.lightRed} 100%)`,
    color: COLORS.white,
  };

  const buttonHoverGradient = {
    background: `linear-gradient(135deg, ${COLORS.accentRed} 0%, ${COLORS.primaryRed} 100%)`,
  };

  const casePanelGradient = {
    background: `linear-gradient(135deg, ${COLORS.darkGray} 0%, ${COLORS.mediumGray} 100%)`,
    borderColor: `${COLORS.primaryRed}50`,
  };

  const chatBgGradient = {
    background: `linear-gradient(135deg, ${COLORS.darkGray} 0%, ${COLORS.mediumGray} 100%)`,
    borderColor: `${COLORS.primaryRed}50`,
  };

  const chatHeaderGradient = {
    background: `linear-gradient(135deg, ${COLORS.primaryRed}30 0%, ${COLORS.lightRed}15 100%)`,
    borderColor: `${COLORS.primaryRed}50`,
  };

  const messageBgGradient = {
    background: `${COLORS.darkGray}80`,
    borderColor: `${COLORS.mediumGray}50`,
  };

  const systemMessageBgGradient = {
    background: `${COLORS.agedGold}10`,
    borderColor: `${COLORS.agedGold}30`,
  };

  const badgeGradient = {
    background: `linear-gradient(135deg, ${COLORS.agedGold} 0%, ${COLORS.lightGold} 100%)`,
    color: COLORS.charcoalBlack,
  };

  return (
    <div className="min-h-screen text-white" style={bgGradient}>
      {/* Import Google Font Cinzel */}
      <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700;900&display=swap" rel="stylesheet" />

      {/* Background Pattern */}
      <div 
        className="fixed inset-0 opacity-10 pointer-events-none"
        style={{
          backgroundImage: `radial-gradient(circle at 20% 50%, ${COLORS.primaryRed}15 0%, transparent 50%), radial-gradient(circle at 80% 80%, ${COLORS.lightRed}15 0%, transparent 50%), radial-gradient(circle at 40% 20%, ${COLORS.accentRed}10 0%, transparent 50%)`
        }}
      />

      <div className="relative z-10 p-4 md:p-8">
        {/* Header */}
        <header className="text-center mb-12 relative">
          <div className="absolute inset-0 flex items-center justify-center opacity-10">
            <Ghost size={200} className="text-red-900" />
          </div>
          <div className="relative">
            <h1 className="text-6xl md:text-7xl font-black tracking-tighter mb-2" style={titleGradient}>
              DEADLY TRUTH
            </h1>
            <div className="flex items-center justify-center gap-2 text-xs uppercase font-mono" style={{ color: COLORS.offWhite }}>
              <div className={`w-2 h-2 rounded-full ${socket?.readyState === 1 ? 'bg-emerald-500' : 'bg-red-600'}`} style={{
                animation: socket?.readyState === 1 ? 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite' : 'none'
              }} />
              <span>
                {socket?.readyState === 1 ? 'Sistema Ativo' : 'Conexão Perdida'}
              </span>
            </div>
          </div>
        </header>

        {/* Lobby Screen */}
        {!gameState.game_active ? (
          <div className="max-w-7xl mx-auto">
            {/* Status Bar */}
            <div className="border-2 rounded-2xl p-6 mb-8 backdrop-blur-sm shadow-lg" style={statusBarGradient}>
              <div className="flex items-center justify-between flex-wrap gap-4">
                <div className="flex items-center gap-3">
                  <Users size={28} style={{ color: COLORS.accentRed }} />
                  <div>
                    <p className="text-2xl font-bold" style={{ color: COLORS.accentRed }}>{gameState.total_players}/12</p>
                    <p className="text-xs uppercase tracking-wider font-sans" style={{ color: COLORS.offWhite }}>Investigadores Conectados</p>
                  </div>
                </div>
                <div className="flex items-center gap-2 px-4 py-2 rounded-full border" style={{ backgroundColor: `${COLORS.charcoalBlack}30`, borderColor: COLORS.mediumGray }}>
                  <Timer size={18} style={{ color: COLORS.agedGold }} />
                  <span className="text-sm font-mono" style={{ color: COLORS.lightGold }}>Aguardando início...</span>
                </div>
              </div>
            </div>

            {/* Player Slots */}
            <div 
              ref={playerSlotsRef}
              className="flex overflow-x-auto gap-4 pb-4 mb-10 scrollbar-thin"
              style={{
                scrollbarColor: `${COLORS.primaryRed} ${COLORS.darkGray}`
              }}
            >
              {[...Array(12)].map((_, i) => {
                const isConnected = i < gameState.total_players;
                const isMe = gameState.player_id && (i + 1) === gameState.player_id;
                return (
                  <div 
                    key={i} 
                    className={`relative flex-shrink-0 w-[140px] h-40 rounded-xl transition-all duration-300 border-2 ${
                      isConnected 
                        ? 'shadow-lg shadow-primaryRed/20 hover:shadow-primaryRed/40 hover:scale-105' 
                        : 'opacity-40'
                    }`}
                    style={isConnected ? cardActiveGradient : cardInactiveGradient}
                  >
                    {/* Corner Decoration */}
                    <div 
                      className="absolute top-0 left-0 w-6 h-6 border-t-2 border-l-2 rounded-tl-xl" 
                      style={{ borderColor: isConnected ? `${COLORS.accentRed}70` : `${COLORS.mediumGray}70` }}
                    />
                    <div 
                      className="absolute bottom-0 right-0 w-6 h-6 border-b-2 border-r-2 rounded-br-xl" 
                      style={{ borderColor: isConnected ? `${COLORS.accentRed}70` : `${COLORS.mediumGray}70` }}
                    />
                    
                    <div className="h-full flex flex-col items-center justify-center p-4">
                      <div 
                        className="mb-3 p-3 rounded-full"
                        style={{ backgroundColor: isConnected ? `${COLORS.primaryRed}50` : `${COLORS.darkGray}50` }}
                      >
                        <User size={28} style={{ color: isConnected ? COLORS.accentRed : COLORS.mediumGray }} />
                      </div>
                      <span className="text-xs font-mono uppercase tracking-wider" style={{ color: COLORS.offWhite }}>
                        Slot #{i + 1}
                      </span>
                      {isMe && (
                        <div className="absolute top-2 right-2">
                          <span className="text-[9px] px-3 py-1 rounded-full font-bold tracking-wider shadow-lg" style={badgeGradient}>
                            VOCÊ
                          </span>
                        </div>
                      )}
                      {isConnected && (
                        <div className="absolute bottom-2 left-2">
                          <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full" style={{
                            animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite'
                          }} />
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Start Button */}
            <div className="flex justify-center">
              <button 
                onClick={() => socket?.send(JSON.stringify({type: 'start'}))}
                disabled={!socket || socket.readyState !== WebSocket.OPEN || gameState.total_players < 1} // Desabilitar se não houver jogadores
                className="group relative px-12 py-5 rounded-2xl font-black text-lg tracking-widest transition-all duration-300 hover:scale-105 hover:shadow-2xl disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
                style={buttonGradient}
                onMouseEnter={(e) => {
                  if (!e.currentTarget.disabled) {
                    Object.assign(e.currentTarget.style, buttonHoverGradient);
                  }
                }}
                onMouseLeave={(e) => {
                  Object.assign(e.currentTarget.style, buttonGradient);
                }}
              >
                <div className="absolute inset-0 bg-accentRed/20 rounded-2xl blur-xl group-hover:bg-accentRed/30 transition-all" />
                <span className="relative flex items-center gap-3">
                  <Search size={20} />
                  INICIAR INVESTIGAÇÃO
                </span>
              </button>
            </div>
          </div>
        ) : (
          /* Game Screen */
          <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Case File Panel */}
            <div className="lg:col-span-1">
              <div className="sticky top-4 border-2 rounded-2xl p-6 backdrop-blur-sm shadow-2xl" style={casePanelGradient}>
                <div className="flex items-center gap-3 mb-6 pb-4 border-b" style={{borderColor: `${COLORS.primaryRed}50`}}>
                    <div className="p-2 rounded-lg" style={{ backgroundColor: `${COLORS.primaryRed}50` }}>
                    <AlertCircle size={24} style={{ color: COLORS.accentRed }} />
                  </div>
                  <h3 className="text-xl font-black uppercase tracking-wider text-white font-serif">
                    Dossiê do Crime
                  </h3>
                </div>
                
                <div className="space-y-4">
                  <div className="p-4 rounded-xl border" style={{backgroundColor: `${COLORS.charcoalBlack}50`, borderColor: `${COLORS.primaryRed}50`}}>
                    <p className="text-base leading-relaxed italic font-serif" style={{ color: COLORS.white }}>
                      {/* Tenta várias chaves possíveis que a IA pode gerar */}
                      {gameState.case?.descricao || 
                       gameState.case?.enredo || 
                       gameState.case?.historia || 
                       "O Mestre está escrevendo o dossiê neste momento..."}
                    </p>
                  </div>
                  
                  {/* Scenario Tag */}
                  {gameState.scenario && (
                    <div className="flex flex-wrap gap-2">
                      <span className="px-3 py-1 rounded-full text-xs font-mono text-charcoalBlack" style={badgeGradient}>
                        CENÁRIO: {gameState.scenario.toUpperCase()}
                      </span>
                    </div>
                  )}

                  {/* Evidence Tags (Placeholder) */}
                  <div className="flex flex-wrap gap-2">
                    <span className="px-3 py-1 border rounded-full text-xs font-mono text-white" style={{backgroundColor: `${COLORS.primaryRed}30`, borderColor: `${COLORS.primaryRed}40`}}>
                      EVIDÊNCIAS
                    </span>
                    <span className="px-3 py-1 bg-agedGold/30 border border-agedGold/40 rounded-full text-xs font-mono text-white">
                      URGENTE
                    </span>
                  </div>
                </div>
              </div>
            </div>
            
            {/* Interrogation Chat */}
            <div className="lg:col-span-2">
              <div className="border-2 rounded-2xl overflow-hidden backdrop-blur-sm shadow-2xl h-[600px] flex flex-col" style={chatBgGradient}>
                {/* Chat Header */}
                <div className="border-b p-4" style={chatHeaderGradient}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <MessageSquare size={22} style={{ color: COLORS.accentRed }} />
                      <h3 className="font-bold uppercase tracking-wider text-white font-serif">Sala de Interrogatório</h3>
                    </div>
                    <div className="flex items-center gap-2 text-xs font-mono" style={{ color: COLORS.offWhite }}>
                      <div className="w-2 h-2 bg-emerald-500 rounded-full" style={{
                        animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite'
                      }} />
                      <span>{messages.length} mensagens</span>
                    </div>
                  </div>
                </div>

                {/* Messages Area */}
                <div className="flex-1 overflow-y-auto p-6 space-y-4 scrollbar-thin" style={{scrollbarColor: `${COLORS.primaryRed} ${COLORS.darkGray}`}}>
                  {messages.map((m, i) => (
                    <div key={i} className="opacity-0" style={{
                      animation: 'fadeIn 0.3s ease-in forwards',
                      animationDelay: `${Math.min(i * 0.05, 0.5)}s`
                    }}>
                      <div className="flex items-center gap-2 mb-2">
                        <div className="w-6 h-6 rounded-full flex items-center justify-center" style={{backgroundColor: `${COLORS.primaryRed}50`}}>
                          <User size={14} style={{ color: COLORS.accentRed }} />
                        </div>
                        <span className="text-xs font-mono uppercase tracking-wider" style={{ color: COLORS.offWhite }}>
                          {m.player_id === "SISTEMA" ? "Mestre do Jogo" : `Suspeito ${m.player_id}`}
                        </span>
                      </div>
                      <div 
                        className="border p-4 rounded-xl ml-8 transition-all font-serif"
                        onMouseEnter={(e) => e.target.style.borderColor = `${COLORS.accentRed}40`}
                        onMouseLeave={(e) => e.target.style.borderColor = `${COLORS.mediumGray}50`} 
                        style={m.isSystem ? systemMessageBgGradient : messageBgGradient}
                      >
                        <p className="text-sm leading-relaxed" style={{ color: COLORS.offWhite }}>
                          {m.content || m.payload}
                        </p>
                      </div>
                    </div>
                  ))}
                  <div ref={chatEndRef} />
                </div>

                {/* Input Area */}
                <div className="border-t p-4" style={{borderColor: `${COLORS.primaryRed}50`, backgroundColor: `${COLORS.charcoalBlack}40`}}>
                  <div className="flex gap-3">
                    <input 
                      value={inputMsg}
                      onChange={(e) => setInputMsg(e.target.value)}
                      className="flex-1 border-2 rounded-xl px-4 py-3 outline-none transition-all text-sm font-serif"
                      style={{ 
                        backgroundColor: `${COLORS.darkGray}80`, 
                        borderColor: `${COLORS.mediumGray}40`,
                        color: COLORS.white
                      }}
                      onFocus={(e) => e.target.style.borderColor = COLORS.accentRed}
                      onBlur={(e) => e.target.style.borderColor = `${COLORS.mediumGray}40`}
                      placeholder="Digite seu depoimento ou interrogue os suspeitos..."
                      onKeyPress={(e) => e.key === 'Enter' && sendAction()}
                    />
                    <button 
                      onClick={sendAction}
                      className="px-6 py-3 rounded-xl font-bold uppercase tracking-wider transition-all hover:scale-105 hover:shadow-lg text-white"
                      style={buttonGradient}
                      onMouseEnter={(e) => {
                        Object.assign(e.currentTarget.style, buttonHoverGradient);
                      }}
                      onMouseLeave={(e) => {
                        Object.assign(e.currentTarget.style, buttonGradient);
                      }}
                    >
                      Enviar
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Global Styles for Animations */}
      <style>{`
        @keyframes pulse {
          0%, 100% {
            opacity: 1;
          }
          50% {
            opacity: 0.5;
          }
        }
        
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        /* Custom Scrollbar */
        .scrollbar-thin::-webkit-scrollbar {
          width: 8px;
          height: 8px;
        }
        .scrollbar-thin::-webkit-scrollbar-track {
          background: ${COLORS.darkGray};
          border-radius: 10px;
        }
        .scrollbar-thin::-webkit-scrollbar-thumb {
          background-color: ${COLORS.primaryRed};
          border-radius: 10px;
          border: 2px solid ${COLORS.darkGray};
        }
        .scrollbar-thin::-webkit-scrollbar-thumb:hover {
          background-color: ${COLORS.accentRed};
        }

        /* Input Placeholder */
        input::placeholder {
          color: ${COLORS.mediumGray} !important;
        }
      `}</style>
    </div>
  );
}

export default App;
