import React, { useState, useEffect } from 'react';
import { User, Lock, Ghost, MessageSquare, Timer } from 'lucide-react';

const BACKEND_URL = "wss://deadlytruth.onrender.com/ws/sala_geral";

function App() {
  const [socket, setSocket] = useState(null);
  const [gameState, setGameState] = useState({ players: [], total_players: 0, game_active: false });
  const [messages, setMessages] = useState([]);
  const [inputMsg, setInputMsg] = useState("");

  useEffect(() => {
    const ws = new WebSocket(BACKEND_URL);
    ws.onopen = () => console.log("🕵️ Conectado ao Deadly Truth");
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "hello") {
        setGameState(prev => ({ ...prev, ...data.payload }));
      } else if (data.type === "game_start") {
        setGameState(prev => ({ ...prev, ...data.payload, game_active: true }));
        setMessages(prev => [...prev, { type: "system", payload: data.payload.msg }]);
      } else if (data.type === "status") {
        setMessages(prev => [...prev, { type: "system", payload: data.msg }]);
      } else if (data.type === "turn_start") {
        setMessages(prev => [...prev, { type: "turn_start", payload: `🔴 Turno do Suspeito ${data.player}` }]);
      } else if (data.type === "time_out") {
        setMessages(prev => [...prev, { type: "system", payload: `⏱️ Tempo esgotado para Suspeito ${data.player}` }]);
      } else if (data.type === "chat" || data.type === "interrogation") {
        setMessages(prev => [...prev, { ...data, player_id: data.player_id || "Sistema" }]);
      }
    };
    setSocket(ws);
    return () => ws.close();
  }, []);

  const sendAction = () => {
    if (socket && inputMsg) {
      socket.send(JSON.stringify({ type: "action", content: inputMsg }));
      setInputMsg("");
    }
  };

  return (
    <div className="min-h-screen bg-[#050505] text-[#e2e8f0] font-serif p-6">
      {/* Header Estilizado */}
      <header className="max-w-6xl mx-auto flex justify-between items-end border-b border-red-900/30 pb-4 mb-8">
        <div>
          <h1 className="text-4xl font-black tracking-tighter text-red-700 underline decoration-double">DEADLY TRUTH</h1>
          <p className="text-xs font-mono text-slate-500 uppercase tracking-widest mt-1">Procedural Noir Mystery Engine</p>
        </div>
        {gameState.game_active && (
          <div className="flex items-center gap-3 bg-red-950/20 border border-red-900/50 px-4 py-2 rounded">
            <Timer className="text-red-600" size={18} />
            <span className="font-mono text-xl text-red-500">02:00</span>
          </div>
        )}
      </header>

      <main className="max-w-6xl mx-auto">
        {!gameState.game_active ? (
          /* TELA DE LOBBY */
          <div className="space-y-8 animate-in fade-in duration-700">
            <div className="text-center space-y-2">
              <h2 className="text-2xl text-slate-400">Aguardando Investigadores...</h2>
              <p className="text-red-900 font-mono animate-pulse">
                {gameState.total_players} / 12 JOGADORES NA SALA
              </p>
            </div>

            <div className="grid-lobby mb-8">
              {[...Array(12)].map((_, i) => {
                const isConnected = i < gameState.total_players;
                const isMe = i + 1 === gameState.player_id;
                return (
                  <div key={i} className={`h-32 rounded border flex flex-col items-center justify-center transition-all duration-500 ${
                    isConnected ? 'border-red-800 bg-red-950/10 shadow-[0_0_15px_rgba(153,27,27,0.1)]' : 'border-slate-800 opacity-20'
                  }`}>
                    <User size={32} className={isConnected ? 'text-red-700' : 'text-slate-600'} />
                    <span className="text-[10px] mt-2 font-mono uppercase tracking-tighter">
                      {isConnected ? `Suspeito ${i + 1}` : 'Vazio'}
                    </span>
                    {isMe && <div className="text-[9px] bg-red-700 text-white px-2 mt-1 rounded-full animate-bounce">VOCÊ</div>}
                  </div>
                );
              })}
            </div>
            
            {gameState.total_players >= 6 && gameState.player_id === 1 && (
              <div className="flex justify-center mt-10">
                <button 
                  onClick={() => socket?.send(JSON.stringify({ type: "start" }))}
                  className="bg-red-700 hover:bg-red-600 text-white px-8 py-3 rounded font-bold tracking-widest flex items-center gap-2 transition-all hover:scale-105 shadow-lg shadow-red-700/20"
                >
                  <Lock size={18} /> INICIAR INVESTIGAÇÃO
                </button>
              </div>
            )}
          </div>
        ) : (
          /* TELA DE JOGO ATIVO */
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 animate-in slide-in-from-bottom-4 duration-1000">
            <aside className="lg:col-span-1 space-y-6">
              <div className="bg-slate-900/50 p-4 border border-slate-800 rounded">
                <h3 className="text-red-700 font-bold mb-2 flex items-center gap-2"><Ghost size={16}/> O CASO</h3>
                <p className="text-sm font-bold text-slate-300 uppercase">{gameState.case?.cenario}</p>
                <p className="text-xs text-slate-500 mt-2 italic leading-relaxed">"{gameState.case?.local_corpo}"</p>
              </div>
            </aside>

            <section className="lg:col-span-3 flex flex-col h-[65vh] bg-[#080808] border border-slate-800 rounded-lg overflow-hidden">
              <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin scrollbar-thumb-red-900">
                {messages.map((m, i) => (
                  <div key={i} className="animate-in fade-in slide-in-from-left-2">
                    <span className="text-[10px] font-mono text-red-900 block mb-1">
                      {m.type === 'turn_start' ? 'SISTEMA' : `JOGADOR ${m.player_id}`}
                    </span>
                    <p className="text-slate-300 text-sm bg-slate-900/30 p-3 rounded border-l border-red-900/50">
                      {m.payload}
                    </p>
                  </div>
                ))}
              </div>
              <div className="p-4 bg-black/60 border-t border-slate-800 flex gap-3">
                <input 
                  className="flex-1 bg-transparent border-b border-slate-700 p-2 outline-none focus:border-red-700 transition-colors text-sm"
                  placeholder="Interrogue um suspeito ou descreva sua ação..."
                  value={inputMsg}
                  onChange={(e) => setInputMsg(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && sendAction()}
                />
                <button onClick={sendAction} className="text-red-700 hover:text-red-500 transition-colors">
                  <MessageSquare size={24} />
                </button>
              </div>
            </section>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
