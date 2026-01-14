import React, { useState, useEffect, useRef } from 'react';
import { User, Ghost, MessageSquare, Timer, Search, AlertCircle, Users, Sparkles, Zap, Crown, Target } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

// --- CONFIGURAÇÃO ---
// Usa variável de ambiente ou fallback para desenvolvimento local
const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "ws://localhost:8000/ws/sala_geral";

// --- PALETA DE CORES ---
const COLORS = {
  primaryRed: '#8B0000',
  accentRed: '#DC143C',
  lightRed: '#C41E3A',
  charcoalBlack: '#0F0F0F',
  darkGray: '#1A1A1A',
  mediumGray: '#2A2A2A',
  white: '#FFFFFF',
  offWhite: '#F5F5F5',
  agedGold: '#D4AF37',
  lightGold: '#C9A961',
};

function Lobby() {
  const { user, logout, token } = useAuth();
  const [socket, setSocket] = useState(null);
  const [gameState, setGameState] = useState({ 
    players: [], 
    total_players: 0, 
    game_active: false, 
    player_id: null, 
    case: null,
    scenario: null
  });
  const [messages, setMessages] = useState([]);
  const [inputMsg, setInputMsg] = useState("");
  const chatEndRef = useRef(null);
  const playerSlotsRef = useRef(null);

  // --- EFEITO: CONEXÃO WEBSOCKET ---
  useEffect(() => {
    const buildWsUrl = () => {
      try {
        const url = new URL(BACKEND_URL);
        if (token) {
          url.searchParams.set('token', token);
        }
        return url.toString();
      } catch {
        if (token) {
          const separator = BACKEND_URL.includes('?') ? '&' : '?';
          return `${BACKEND_URL}${separator}token=${encodeURIComponent(token)}`;
        }
        return BACKEND_URL;
      }
    };

    const ws = new WebSocket(buildWsUrl());
    ws.onopen = () => {
      console.log("Conectado ao Deadly Truth");
      setSocket(ws);
    };
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log("Mensagem do servidor:", data);

        if (data.type === "game_start" || data.type === "hello") {
          setGameState(prev => ({ 
            ...prev, 
            ...data.payload, 
            game_active: data.type === "game_start" ? true : prev.game_active,
            case: data.payload.case || prev.case 
          }));
        }

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
      setGameState(prev => ({ ...prev, game_active: false }));
    };
    ws.onerror = (error) => {
      console.error("Erro no WebSocket:", error);
    };
    return () => ws.close();
  }, [token]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendAction = () => {
    if (socket && inputMsg.trim() && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: "action", content: inputMsg.trim() }));
      setInputMsg("");
    }
  };

  const bgGradient = {
    background: `linear-gradient(135deg, ${COLORS.charcoalBlack} 0%, ${COLORS.darkGray} 100%)`,
    fontFamily: "'Cinzel', serif",
  };

  const titleGradient = {
    background: `linear-gradient(135deg, ${COLORS.accentRed} 0%, ${COLORS.primaryRed} 100%)`,
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
    filter: `drop-shadow(0 0 20px ${COLORS.primaryRed}50)`,
  };

  const statusBarGradient = {
    background: `linear-gradient(135deg, ${COLORS.darkGray}90 0%, ${COLORS.mediumGray}90 100%)`,
    borderColor: `${COLORS.primaryRed}60`,
    boxShadow: `0 8px 32px ${COLORS.primaryRed}20, inset 0 1px 0 ${COLORS.primaryRed}20`
  };

  return (
    <div className="min-h-screen text-white relative" style={bgGradient}>
      <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700;900&display=swap" rel="stylesheet" />

      {/* Header com Logout */}
      <div className="absolute top-4 right-4 z-20">
        <div className="flex items-center gap-4">
          {user && (
            <span className="text-sm text-offWhite">
              <span className="text-primaryRed font-semibold">{user.email}</span>
            </span>
          )}
          <button
            onClick={logout}
            className="px-4 py-2 rounded-xl font-bold text-sm transition-all duration-300 text-white"
            style={{
              background: `linear-gradient(135deg, ${COLORS.primaryRed} 0%, ${COLORS.accentRed} 100%)`,
            }}
          >
            Sair
          </button>
        </div>
      </div>

      {/* Background Pattern Animado */}
      <div 
        className="fixed inset-0 opacity-10 pointer-events-none"
        style={{
          backgroundImage: `radial-gradient(circle at 20% 50%, ${COLORS.primaryRed}15 0%, transparent 50%), radial-gradient(circle at 80% 80%, ${COLORS.lightRed}15 0%, transparent 50%), radial-gradient(circle at 40% 20%, ${COLORS.accentRed}10 0%, transparent 50%)`,
          animation: 'backgroundPulse 8s ease-in-out infinite'
        }}
      />
      
      {/* Partículas de Fundo */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        {[...Array(20)].map((_, i) => (
          <div
            key={i}
            className="absolute rounded-full opacity-20"
            style={{
              width: `${Math.random() * 4 + 2}px`,
              height: `${Math.random() * 4 + 2}px`,
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              backgroundColor: COLORS.accentRed,
              animation: `float ${Math.random() * 10 + 10}s ease-in-out infinite`,
              animationDelay: `${Math.random() * 5}s`
            }}
          />
        ))}
      </div>

      <div className="relative z-10 p-4 md:p-8">
        {/* Header */}
        <header className="text-center mb-16 relative">
          <div className="absolute inset-0 flex items-center justify-center opacity-5">
            <Ghost size={250} className="text-red-900" style={{
              animation: 'ghostFloat 6s ease-in-out infinite'
            }} />
          </div>
          <div className="relative">
            <div className="flex items-center justify-center gap-4 mb-4">
              <Sparkles size={32} style={{ color: COLORS.agedGold, opacity: 0.7 }} className="animate-pulse" />
              <h1 className="text-6xl md:text-8xl font-black tracking-tighter mb-2 relative" style={titleGradient}>
                <span className="relative z-10">DEADLY TRUTH</span>
                <span 
                  className="absolute inset-0 blur-2xl opacity-50"
                  style={{
                    background: `linear-gradient(135deg, ${COLORS.accentRed} 0%, ${COLORS.primaryRed} 100%)`,
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                    animation: 'glow 3s ease-in-out infinite'
                  }}
                >
                  DEADLY TRUTH
                </span>
              </h1>
              <Sparkles size={32} style={{ color: COLORS.agedGold, opacity: 0.7 }} className="animate-pulse" />
            </div>
            <div className="flex items-center justify-center gap-3 text-sm uppercase font-mono" style={{ color: COLORS.offWhite }}>
              <div className="relative">
                <div className={`w-3 h-3 rounded-full ${socket?.readyState === 1 ? 'bg-emerald-500' : 'bg-red-600'}`} style={{
                  animation: socket?.readyState === 1 ? 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite' : 'none',
                  boxShadow: socket?.readyState === 1 ? `0 0 10px ${COLORS.agedGold}` : 'none'
                }} />
                {socket?.readyState === 1 && (
                  <div className="absolute inset-0 w-3 h-3 rounded-full bg-emerald-500 animate-ping opacity-75" />
                )}
              </div>
              <span className="font-semibold">
                {socket?.readyState === 1 ? 'Sistema Ativo' : 'Conexão Perdida'}
              </span>
              {socket?.readyState === 1 && (
                <Zap size={16} style={{ color: COLORS.agedGold }} className="animate-pulse" />
              )}
            </div>
          </div>
        </header>

        {/* Lobby Screen */}
        {!gameState.game_active ? (
          <div className="max-w-7xl mx-auto">
            {/* Status Bar */}
            <div className="border-2 rounded-3xl p-8 mb-10 backdrop-blur-md shadow-2xl relative overflow-hidden" style={statusBarGradient}>
              <div className="absolute inset-0 opacity-30" style={{
                background: `linear-gradient(90deg, transparent, ${COLORS.accentRed}40, transparent)`,
                animation: 'shimmer 3s ease-in-out infinite'
              }} />
              
              <div className="relative z-10 flex items-center justify-between flex-wrap gap-6">
                <div className="flex items-center gap-4">
                  <div className="relative">
                    <div className="p-3 rounded-2xl backdrop-blur-sm" style={{
                      background: `linear-gradient(135deg, ${COLORS.primaryRed}40 0%, ${COLORS.lightRed}20 100%)`,
                      border: `2px solid ${COLORS.accentRed}50`
                    }}>
                      <Users size={32} style={{ color: COLORS.accentRed }} className="animate-pulse" />
                    </div>
                    {gameState.total_players > 0 && (
                      <div className="absolute -top-2 -right-2 w-6 h-6 rounded-full flex items-center justify-center" style={{
                        background: `linear-gradient(135deg, ${COLORS.accentRed} 0%, ${COLORS.primaryRed} 100%)`,
                        boxShadow: `0 0 10px ${COLORS.accentRed}`
                      }}>
                        <span className="text-xs font-bold text-white">{gameState.total_players}</span>
                      </div>
                    )}
                  </div>
                  <div>
                    <p className="text-4xl font-black mb-1" style={{
                      background: `linear-gradient(135deg, ${COLORS.accentRed} 0%, ${COLORS.agedGold} 100%)`,
                      WebkitBackgroundClip: 'text',
                      WebkitTextFillColor: 'transparent'
                    }}>
                      {gameState.total_players}/12
                    </p>
                    <p className="text-sm uppercase tracking-widest font-semibold" style={{ color: COLORS.offWhite }}>
                      Investigadores Conectados
                    </p>
                  </div>
                </div>
                
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-3 px-5 py-3 rounded-full border backdrop-blur-sm" style={{
                    backgroundColor: `${COLORS.charcoalBlack}40`,
                    borderColor: `${COLORS.agedGold}50`,
                    boxShadow: `0 0 15px ${COLORS.agedGold}20`
                  }}>
                    <Timer size={20} style={{ color: COLORS.agedGold }} className="animate-pulse" />
                    <span className="text-sm font-mono font-semibold" style={{ color: COLORS.lightGold }}>
                      Aguardando início...
                    </span>
                  </div>
                  
                  {gameState.total_players >= 3 && (
                    <div className="flex items-center gap-2 px-4 py-2 rounded-full" style={{
                      background: `linear-gradient(135deg, ${COLORS.agedGold}30 0%, ${COLORS.lightGold}20 100%)`,
                      border: `2px solid ${COLORS.agedGold}50`
                    }}>
                      <Target size={18} style={{ color: COLORS.agedGold }} />
                      <span className="text-xs font-bold uppercase tracking-wider" style={{ color: COLORS.lightGold }}>
                        Pronto para iniciar
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Player Slots */}
            <div 
              ref={playerSlotsRef}
              className="flex overflow-x-auto gap-6 pb-6 mb-12 scrollbar-thin px-2"
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
                    className={`relative flex-shrink-0 w-[160px] h-48 rounded-2xl transition-all duration-500 border-2 group ${
                      isConnected 
                        ? 'shadow-2xl hover:shadow-[0_0_30px_rgba(220,20,60,0.5)] hover:scale-110 hover:-translate-y-2' 
                        : 'opacity-30 hover:opacity-50'
                    }`}
                    style={{
                      ...(isConnected ? {
                        background: `linear-gradient(135deg, ${COLORS.primaryRed}40 0%, ${COLORS.lightRed}20 100%)`,
                        borderColor: `${COLORS.accentRed}60`,
                        backdropFilter: 'blur(10px)',
                        boxShadow: isConnected ? `0 8px 24px ${COLORS.primaryRed}30, inset 0 1px 0 ${COLORS.accentRed}30` : 'none'
                      } : {
                        background: `${COLORS.darkGray}60`,
                        borderColor: `${COLORS.mediumGray}40`,
                        backdropFilter: 'blur(5px)'
                      })
                    }}
                  >
                    {isConnected && (
                      <div className="absolute inset-0 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-500" style={{
                        background: `radial-gradient(circle at center, ${COLORS.accentRed}20, transparent 70%)`
                      }} />
                    )}
                    
                    <div 
                      className="absolute top-0 left-0 w-8 h-8 border-t-3 border-l-3 rounded-tl-2xl transition-all duration-300" 
                      style={{ 
                        borderColor: isConnected ? `${COLORS.accentRed}80` : `${COLORS.mediumGray}50`,
                        boxShadow: isConnected ? `-2px -2px 8px ${COLORS.accentRed}30` : 'none'
                      }}
                    />
                    <div 
                      className="absolute bottom-0 right-0 w-8 h-8 border-b-3 border-r-3 rounded-br-2xl transition-all duration-300" 
                      style={{ 
                        borderColor: isConnected ? `${COLORS.accentRed}80` : `${COLORS.mediumGray}50`,
                        boxShadow: isConnected ? `2px 2px 8px ${COLORS.accentRed}30` : 'none'
                      }}
                    />
                    
                    <div className="h-full flex flex-col items-center justify-center p-5 relative z-10">
                      <div 
                        className="mb-4 p-4 rounded-full transition-all duration-300 group-hover:scale-110"
                        style={{ 
                          background: isConnected 
                            ? `linear-gradient(135deg, ${COLORS.primaryRed}60 0%, ${COLORS.accentRed}40 100%)`
                            : `${COLORS.darkGray}60`,
                          boxShadow: isConnected ? `0 4px 15px ${COLORS.primaryRed}40` : 'none',
                          border: isConnected ? `2px solid ${COLORS.accentRed}50` : 'none'
                        }}
                      >
                        <User size={32} style={{ 
                          color: isConnected ? COLORS.accentRed : COLORS.mediumGray,
                          filter: isConnected ? `drop-shadow(0 0 8px ${COLORS.accentRed})` : 'none'
                        }} />
                      </div>
                      
                      <span className="text-xs font-mono uppercase tracking-widest font-bold mb-1" style={{ 
                        color: isConnected ? COLORS.offWhite : COLORS.mediumGray 
                      }}>
                        Slot #{i + 1}
                      </span>
                      
                      {isConnected && (
                        <span className="text-[10px] font-semibold uppercase tracking-wider" style={{ 
                          color: COLORS.agedGold,
                          textShadow: `0 0 8px ${COLORS.agedGold}50`
                        }}>
                          Online
                        </span>
                      )}
                      
                      {isMe && (
                        <div className="absolute top-3 right-3 animate-bounce">
                          <div className="relative">
                            <Crown size={20} style={{ color: COLORS.agedGold }} className="drop-shadow-lg" />
                            <div className="absolute inset-0 animate-ping">
                              <Crown size={20} style={{ color: COLORS.agedGold, opacity: 0.5 }} />
                            </div>
                          </div>
                        </div>
                      )}
                      
                      {isConnected && (
                        <div className="absolute bottom-3 left-3">
                          <div className="relative">
                            <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" style={{
                              boxShadow: `0 0 10px ${COLORS.agedGold}`
                            }} />
                            <div className="absolute inset-0 w-2 h-2 bg-emerald-500 rounded-full animate-ping opacity-75" />
                          </div>
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
                disabled={!socket || socket.readyState !== WebSocket.OPEN || gameState.total_players < 3}
                className="group relative px-16 py-6 rounded-3xl font-black text-xl tracking-widest transition-all duration-500 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:scale-100 overflow-hidden"
                style={{
                  background: gameState.total_players >= 3
                    ? `linear-gradient(135deg, ${COLORS.primaryRed} 0%, ${COLORS.accentRed} 50%, ${COLORS.primaryRed} 100%)`
                    : `linear-gradient(135deg, ${COLORS.darkGray} 0%, ${COLORS.mediumGray} 100%)`,
                  backgroundSize: '200% 200%',
                  color: COLORS.white,
                  boxShadow: gameState.total_players >= 3
                    ? `0 10px 40px ${COLORS.primaryRed}50, inset 0 1px 0 ${COLORS.accentRed}50`
                    : 'none',
                  border: gameState.total_players >= 3 ? `2px solid ${COLORS.accentRed}60` : `2px solid ${COLORS.mediumGray}40`,
                  animation: gameState.total_players >= 3 ? 'gradientShift 3s ease infinite' : 'none'
                }}
                onMouseEnter={(e) => {
                  if (!e.currentTarget.disabled && gameState.total_players >= 3) {
                    e.currentTarget.style.transform = 'scale(1.05) translateY(-4px)';
                    e.currentTarget.style.boxShadow = `0 15px 50px ${COLORS.accentRed}60, inset 0 1px 0 ${COLORS.accentRed}70`;
                  }
                }}
                onMouseLeave={(e) => {
                  if (!e.currentTarget.disabled) {
                    e.currentTarget.style.transform = 'scale(1)';
                    e.currentTarget.style.boxShadow = gameState.total_players >= 3
                      ? `0 10px 40px ${COLORS.primaryRed}50, inset 0 1px 0 ${COLORS.accentRed}50`
                      : 'none';
                  }
                }}
              >
                <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500" style={{
                  background: `linear-gradient(90deg, transparent, ${COLORS.white}30, transparent)`,
                  animation: 'shimmer 1.5s ease-in-out infinite'
                }} />
                
                <div className="absolute inset-0 opacity-20">
                  {[...Array(6)].map((_, i) => (
                    <div
                      key={i}
                      className="absolute rounded-full"
                      style={{
                        width: '4px',
                        height: '4px',
                        backgroundColor: COLORS.white,
                        left: `${Math.random() * 100}%`,
                        top: `${Math.random() * 100}%`,
                        animation: `sparkle ${Math.random() * 2 + 1}s ease-in-out infinite`,
                        animationDelay: `${Math.random() * 1}s`
                      }}
                    />
                  ))}
                </div>
                
                <span className="relative flex items-center gap-4 z-10">
                  <div className="relative">
                    <Search size={24} className="group-hover:rotate-12 transition-transform duration-300" />
                    {gameState.total_players >= 3 && (
                      <div className="absolute -top-1 -right-1 w-2 h-2 bg-emerald-400 rounded-full animate-ping" />
                    )}
                  </div>
                  <span className="relative">
                    INICIAR INVESTIGAÇÃO
                    {gameState.total_players >= 3 && (
                      <span className="absolute -bottom-1 left-0 right-0 h-0.5 bg-white animate-pulse" style={{
                        boxShadow: `0 0 8px ${COLORS.white}`
                      }} />
                    )}
                  </span>
                  {gameState.total_players >= 3 && (
                    <Zap size={20} className="animate-pulse" />
                  )}
                </span>
                
                {gameState.total_players < 3 && (
                  <span className="absolute -bottom-8 left-1/2 transform -translate-x-1/2 text-xs font-mono text-red-400 whitespace-nowrap">
                    Mínimo de 3 jogadores
                  </span>
                )}
              </button>
            </div>
          </div>
        ) : (
          /* Game Screen */
          <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Case File Panel */}
            <div className="lg:col-span-1">
              <div className="sticky top-4 border-2 rounded-2xl p-6 backdrop-blur-sm shadow-2xl" style={{
                background: `linear-gradient(135deg, ${COLORS.darkGray} 0%, ${COLORS.mediumGray} 100%)`,
                borderColor: `${COLORS.primaryRed}50`,
              }}>
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
                      {gameState.case?.descricao || 
                       gameState.case?.enredo || 
                       gameState.case?.historia || 
                       "O Mestre está escrevendo o dossiê neste momento..."}
                    </p>
                  </div>
                  
                  {gameState.scenario && (
                    <div className="flex flex-wrap gap-2">
                      <span className="px-3 py-1 rounded-full text-xs font-mono text-charcoalBlack" style={{
                        background: `linear-gradient(135deg, ${COLORS.agedGold} 0%, ${COLORS.lightGold} 100%)`,
                        color: COLORS.charcoalBlack
                      }}>
                        CENÁRIO: {gameState.scenario.toUpperCase()}
                      </span>
                    </div>
                  )}

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
              <div className="border-2 rounded-2xl overflow-hidden backdrop-blur-sm shadow-2xl h-[600px] flex flex-col" style={{
                background: `linear-gradient(135deg, ${COLORS.darkGray} 0%, ${COLORS.mediumGray} 100%)`,
                borderColor: `${COLORS.primaryRed}50`,
              }}>
                <div className="border-b p-4" style={{
                  background: `linear-gradient(135deg, ${COLORS.primaryRed}30 0%, ${COLORS.lightRed}15 100%)`,
                  borderColor: `${COLORS.primaryRed}50`,
                }}>
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
                        style={m.isSystem ? {
                          background: `${COLORS.agedGold}10`,
                          borderColor: `${COLORS.agedGold}30`,
                        } : {
                          background: `${COLORS.darkGray}80`,
                          borderColor: `${COLORS.mediumGray}50`,
                        }}
                      >
                        <p className="text-sm leading-relaxed" style={{ color: COLORS.offWhite }}>
                          {m.content || m.payload}
                        </p>
                      </div>
                    </div>
                  ))}
                  <div ref={chatEndRef} />
                </div>

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
                      style={{
                        background: `linear-gradient(135deg, ${COLORS.primaryRed} 0%, ${COLORS.lightRed} 100%)`,
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background = `linear-gradient(135deg, ${COLORS.accentRed} 0%, ${COLORS.primaryRed} 100%)`;
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = `linear-gradient(135deg, ${COLORS.primaryRed} 0%, ${COLORS.lightRed} 100%)`;
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
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
        
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        
        @keyframes backgroundPulse {
          0%, 100% { opacity: 0.1; transform: scale(1); }
          50% { opacity: 0.15; transform: scale(1.05); }
        }
        
        @keyframes float {
          0%, 100% { transform: translateY(0) translateX(0); }
          25% { transform: translateY(-20px) translateX(10px); }
          50% { transform: translateY(-10px) translateX(-10px); }
          75% { transform: translateY(-30px) translateX(5px); }
        }
        
        @keyframes ghostFloat {
          0%, 100% { transform: translateY(0) rotate(0deg); opacity: 0.05; }
          50% { transform: translateY(-30px) rotate(5deg); opacity: 0.08; }
        }
        
        @keyframes glow {
          0%, 100% { filter: blur(20px) brightness(1); }
          50% { filter: blur(25px) brightness(1.2); }
        }
        
        @keyframes shimmer {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(100%); }
        }
        
        @keyframes gradientShift {
          0% { background-position: 0% 50%; }
          50% { background-position: 100% 50%; }
          100% { background-position: 0% 50%; }
        }
        
        @keyframes sparkle {
          0%, 100% { opacity: 0; transform: scale(0); }
          50% { opacity: 1; transform: scale(1); }
        }

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

        input::placeholder {
          color: ${COLORS.mediumGray} !important;
        }
      `}</style>
    </div>
  );
}

export default Lobby;
