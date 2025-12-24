import React, { useState, useEffect, useRef } from 'react';
import { User, Lock, Ghost, MessageSquare, Timer, Search, AlertCircle, Users } from 'lucide-react';

const BACKEND_URL = "wss://deadlytruth.onrender.com/ws/sala_geral";

function App() {
  const [socket, setSocket] = useState(null);
  const [gameState, setGameState] = useState({ players: [], total_players: 0, game_active: false, player_id: null, case: null });
  const [messages, setMessages] = useState([]);
  const [inputMsg, setInputMsg] = useState("");
  const chatEndRef = useRef(null);

  useEffect(() => {
    const ws = new WebSocket(BACKEND_URL);
    ws.onopen = () => console.log("Connected to Deadly Truth");
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log("Chegou do servidor:", data); // Para você ver no F12 o que está vindo

        if (data.type === "hello") {
          setGameState(prev => ({ ...prev, ...data.payload }));
        } 
        
        else if (data.type === "game_start") {
          // Quando o jogo começa, salvamos o caso e ativamos a tela de jogo
          setGameState(prev => ({ 
            ...prev, 
            case: data.payload.case, 
            game_active: true 
          }));
          // Adicionamos a mensagem de boas-vindas ao chat
          setMessages(prev => [...prev, { 
            player_id: "SISTEMA", 
            content: data.payload.msg || "A investigação começou!" 
          }]);
        } 
        
        else if (data.type === "chat" || data.type === "action" || data.type === "status") {
          // Esta parte garante que mensagens de chat e ações apareçam na lista
          const newMessage = {
            player_id: data.player_id || data.player || "Mestre",
            content: data.content || data.payload || data.msg
          };
          setMessages(prev => [...prev, newMessage]);
        }
        
        else if (data.type === "turn_start") {
          setMessages(prev => [...prev, { 
            player_id: "SISTEMA", 
            content: `Cuidado: É o turno do Suspeito ${data.player}` 
          }]);
        }
      } catch (error) {
        console.error("Erro ao processar mensagem:", error);
      }
    };
    setSocket(ws);
    return () => ws.close();
  }, []);

  // Auto-scroll do chat quando novas mensagens chegam
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendAction = () => {
    if (socket && inputMsg && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: "action", content: inputMsg }));
      setInputMsg("");
    }
  };

  const bgGradient = {
    background: 'linear-gradient(135deg, #000000 0%, rgba(127, 29, 29, 0.3) 50%, #000000 100%)'
  };

  const titleGradient = {
    background: 'linear-gradient(135deg, #fca5a5 0%, #ef4444 50%, #dc2626 100%)',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
    filter: 'drop-shadow(0 0 30px rgba(220, 38, 38, 0.5))'
  };

  const statusBarGradient = {
    background: 'linear-gradient(135deg, rgba(127, 29, 29, 0.4) 0%, rgba(153, 27, 27, 0.2) 100%)'
  };

  const cardActiveGradient = {
    background: 'linear-gradient(135deg, rgba(127, 29, 29, 0.3) 0%, rgba(153, 27, 27, 0.15) 100%)'
  };

  const buttonGradient = {
    background: 'linear-gradient(135deg, #b91c1c 0%, #7f1d1d 100%)'
  };

  const buttonHoverGradient = {
    background: 'linear-gradient(135deg, #dc2626 0%, #991b1b 100%)'
  };

  const casePanelGradient = {
    background: 'linear-gradient(135deg, rgba(127, 29, 29, 0.5) 0%, rgba(153, 27, 27, 0.3) 100%)'
  };

  const chatBgGradient = {
    background: 'linear-gradient(135deg, rgba(9, 9, 11, 0.9) 0%, rgba(23, 23, 23, 0.8) 100%)'
  };

  const chatHeaderGradient = {
    background: 'linear-gradient(135deg, rgba(127, 29, 29, 0.5) 0%, rgba(153, 27, 27, 0.3) 100%)'
  };

  const messageBgGradient = {
    background: 'linear-gradient(135deg, rgba(24, 24, 27, 0.6) 0%, rgba(38, 38, 38, 0.4) 100%)'
  };

  const badgeGradient = {
    background: 'linear-gradient(135deg, #dc2626 0%, #991b1b 100%)'
  };

  return (
    <div className="min-h-screen text-slate-100" style={bgGradient}>
      {/* Background Pattern */}
      <div 
        className="fixed inset-0 opacity-10 pointer-events-none"
        style={{
          backgroundImage: 'radial-gradient(circle at 20% 50%, rgba(220, 38, 38, 0.15) 0%, transparent 50%), radial-gradient(circle at 80% 80%, rgba(127, 29, 29, 0.15) 0%, transparent 50%), radial-gradient(circle at 40% 20%, rgba(153, 27, 27, 0.1) 0%, transparent 50%)'
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
            <div className="flex items-center justify-center gap-2 text-xs uppercase font-mono">
              <div className={`w-2 h-2 rounded-full ${socket?.readyState === 1 ? 'bg-emerald-500' : 'bg-red-600'}`} style={{
                animation: socket?.readyState === 1 ? 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite' : 'none'
              }} />
              <span className="text-white/90">
                {socket?.readyState === 1 ? 'Sistema Ativo' : 'Conexão Perdida'}
              </span>
            </div>
          </div>
        </header>

        {/* Lobby Screen */}
        {!gameState.game_active ? (
          <div className="max-w-7xl mx-auto">
            {/* Status Bar */}
            <div className="border border-red-900/50 rounded-2xl p-6 mb-8 backdrop-blur-sm" style={statusBarGradient}>
              <div className="flex items-center justify-between flex-wrap gap-4">
                <div className="flex items-center gap-3">
                  <Users className="text-red-500" size={28} />
                  <div>
                    <p className="text-2xl font-bold text-red-500">{gameState.total_players}/12</p>
                    <p className="text-xs text-white/80 uppercase tracking-wider">Investigadores Conectados</p>
                  </div>
                </div>
                <div className="flex items-center gap-2 bg-black/30 px-4 py-2 rounded-full">
                  <Timer className="text-amber-500" size={18} />
                  <span className="text-sm font-mono text-amber-400">Aguardando início...</span>
                </div>
              </div>
            </div>

            {/* Player Grid */}
            <div className="grid grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-10">
              {[...Array(12)].map((_, i) => {
                const isConnected = i < gameState.total_players;
                const isMe = i + 1 === gameState.player_id;
                return (
                  <div 
                    key={i} 
                    className={`relative group h-40 rounded-xl transition-all duration-300 ${
                      isConnected 
                        ? 'border-2 border-red-800/60 shadow-lg shadow-red-900/20 hover:shadow-red-900/40 hover:scale-105' 
                        : 'bg-zinc-900/30 border-2 border-zinc-800/50 opacity-40'
                    }`}
                    style={isConnected ? cardActiveGradient : {}}
                  >
                    {/* Corner Decoration */}
                    <div className="absolute top-0 left-0 w-6 h-6 border-t-2 border-l-2 border-red-700/50 rounded-tl-xl" />
                    <div className="absolute bottom-0 right-0 w-6 h-6 border-b-2 border-r-2 border-red-700/50 rounded-br-xl" />
                    
                    <div className="h-full flex flex-col items-center justify-center p-4">
                      <div className={`mb-3 p-3 rounded-full ${isConnected ? 'bg-red-900/50' : 'bg-zinc-800/50'}`}>
                        <User size={28} className={isConnected ? 'text-red-500' : 'text-zinc-600'} />
                      </div>
                      <span className="text-xs font-mono uppercase tracking-wider text-white !important">
                        Slot #{i + 1}
                      </span>
                      {isMe && (
                        <div className="absolute top-2 right-2">
                          <span className="text-[9px] px-3 py-1 rounded-full font-bold tracking-wider shadow-lg text-white" style={badgeGradient}>
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
                disabled={!socket || socket.readyState !== WebSocket.OPEN}
                className="group relative px-12 py-5 rounded-2xl font-black text-lg tracking-widest transition-all duration-300 hover:scale-105 hover:shadow-2xl hover:shadow-red-900/50 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
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
                <div className="absolute inset-0 bg-red-500/20 rounded-2xl blur-xl group-hover:bg-red-500/30 transition-all" />
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
              <div className="sticky top-4 border-2 border-red-800/60 rounded-2xl p-6 backdrop-blur-sm shadow-2xl shadow-red-900/20" style={casePanelGradient}>
                <div className="flex items-center gap-3 mb-6 pb-4 border-b border-red-800/50">
                  <div className="p-2 bg-red-900/50 rounded-lg">
                    <AlertCircle className="text-red-500" size={24} />
                  </div>
                  <h3 className="text-xl font-black uppercase tracking-wider text-white">
                    Dossiê do Crime
                  </h3>
                </div>
                
                <div className="space-y-4">
                  <div className="bg-black/30 p-4 rounded-xl border border-red-900/30">
                    <p className="text-sm text-white leading-relaxed italic">
                      {/* Tenta pegar descricao, senao historia, senao mostra aviso */}
                      {gameState.case?.descricao || gameState.case?.historia || "O mestre está preparando os detalhes do crime..."}
                    </p>
                  </div>
                  
                  {/* Evidence Tags */}
                  <div className="flex flex-wrap gap-2">
                    <span className="px-3 py-1 bg-red-900/30 border border-red-800/40 rounded-full text-xs font-mono text-white">
                      EVIDÊNCIAS
                    </span>
                    <span className="px-3 py-1 bg-amber-900/30 border border-amber-800/40 rounded-full text-xs font-mono text-white">
                      URGENTE
                    </span>
                  </div>
                </div>
              </div>
            </div>
            
            {/* Interrogation Chat */}
            <div className="lg:col-span-2">
              <div className="border-2 border-red-900/40 rounded-2xl overflow-hidden backdrop-blur-sm shadow-2xl shadow-red-900/10 h-[600px] flex flex-col" style={chatBgGradient}>
                {/* Chat Header */}
                <div className="border-b border-red-800/50 p-4" style={chatHeaderGradient}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <MessageSquare className="text-red-500" size={22} />
                      <h3 className="font-bold uppercase tracking-wider text-white">Sala de Interrogatório</h3>
                    </div>
                    <div className="flex items-center gap-2 text-xs font-mono text-white/80">
                      <div className="w-2 h-2 bg-emerald-500 rounded-full" style={{
                        animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite'
                      }} />
                      <span>{messages.length} mensagens</span>
                    </div>
                  </div>
                </div>

                {/* Messages Area */}
                <div className="flex-1 overflow-y-auto p-6 space-y-4">
                  {messages.map((m, i) => (
                    <div key={i} className="opacity-0" style={{
                      animation: 'fadeIn 0.3s ease-in forwards',
                      animationDelay: `${Math.min(i * 0.05, 0.5)}s`
                    }}>
                      <div className="flex items-center gap-2 mb-2">
                        <div className="w-6 h-6 bg-red-900/50 rounded-full flex items-center justify-center">
                          <User size={14} className="text-red-400" />
                        </div>
                        <span className="text-xs font-mono text-white/90 uppercase tracking-wider">
                          Suspeito {m.player_id}
                        </span>
                      </div>
                      <div className="border border-red-900/20 p-4 rounded-xl ml-8 hover:border-red-800/40 transition-all" style={messageBgGradient}>
                        <p className="text-sm text-white leading-relaxed">
                          {m.content || m.payload}
                        </p>
                      </div>
                    </div>
                  ))}
                  <div ref={chatEndRef} />
                </div>

                {/* Input Area */}
                <div className="border-t border-red-900/50 bg-black/40 p-4">
                  <div className="flex gap-3">
                    <input 
                      value={inputMsg}
                      onChange={(e) => setInputMsg(e.target.value)}
                      className="flex-1 bg-zinc-900/80 border-2 border-red-900/40 rounded-xl px-4 py-3 outline-none focus:border-red-700 transition-all text-sm text-white placeholder:text-zinc-500"
                      style={{ color: 'white' }}
                      placeholder="Digite seu depoimento ou interrogue os suspeitos..."
                      onKeyPress={(e) => e.key === 'Enter' && sendAction()}
                    />
                    <button 
                      onClick={sendAction}
                      className="px-6 py-3 rounded-xl font-bold uppercase tracking-wider transition-all hover:scale-105 hover:shadow-lg hover:shadow-red-900/50 text-white"
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
            transform: translateX(-20px);
          }
          to {
            opacity: 1;
            transform: translateX(0);
          }
        }
      `}</style>
    </div>
  );
}

export default App;
