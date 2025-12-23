import React, { useState, useEffect, useRef } from 'react';
import { Ghost, MessageSquare, Timer, User } from 'lucide-react';

function App() {
  const [socket, setSocket] = useState(null);
  const [messages, setMessages] = useState([]);
  const [gameState, setGameState] = useState(null);
  const [inputMsg, setInputMsg] = useState("");

  // Substitua pela sua URL do Render (use wss:// para conexões seguras)
  const BACKEND_URL = "wss://SUA-URL-NO-RENDER.onrender.com/ws/sala_teste";

  useEffect(() => {
    const ws = new WebSocket(BACKEND_URL);

    ws.onopen = () => console.log("✅ Conectado ao Mestre do Jogo");
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === "hello") {
        setGameState(data.payload);
      } else if (data.type === "chat" || data.type === "interrogation") {
        setMessages((prev) => [...prev, data.payload]);
      }
    };

    setSocket(ws);
    return () => ws.close();
  }, []);

  const sendMessage = () => {
    if (socket && inputMsg) {
      socket.send(JSON.stringify({ type: "chat", content: inputMsg }));
      setInputMsg("");
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4 font-serif">
      {/* Header do Jogo */}
      <header className="flex justify-between items-center border-b border-slate-800 pb-4 mb-6">
        <h1 className="text-2xl font-bold tracking-tighter text-red-700">DEADLY TRUTH</h1>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 bg-slate-900 px-3 py-1 rounded">
            <Timer size={18} className="text-red-500" />
            <span className="font-mono">02:00</span>
          </div>
          <User className="text-slate-400" />
        </div>
      </header>

      <main className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Painel do Caso */}
        <section className="md:col-span-1 bg-slate-900 p-4 rounded-lg border border-slate-800">
          <h2 className="text-lg mb-4 flex items-center gap-2">
            <Ghost size={20} /> O Cenário
          </h2>
          <div className="text-sm text-slate-400 space-y-2">
            <p><strong>Local:</strong> {gameState?.case?.cenario || "Carregando..."}</p>
            <p className="italic text-slate-300">"{gameState?.case?.local_corpo || "Aguardando o Mestre..."}"</p>
          </div>
        </section>

        {/* Chat de Investigação */}
        <section className="md:col-span-2 flex flex-col h-[60vh] bg-black/40 rounded-lg border border-slate-800">
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((msg, i) => (
              <div key={i} className="bg-slate-800/50 p-3 rounded border-l-2 border-red-900">
                <p className="text-sm">{typeof msg === 'string' ? msg : JSON.stringify(msg)}</p>
              </div>
            ))}
          </div>
          
          <div className="p-4 border-t border-slate-800 flex gap-2">
            <input 
              className="flex-1 bg-slate-900 border border-slate-700 rounded px-3 py-2 outline-none focus:border-red-700"
              placeholder="Sua pergunta ao suspeito..."
              value={inputMsg}
              onChange={(e) => setInputMsg(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
            />
            <button 
              onClick={sendMessage}
              className="bg-red-900 hover:bg-red-700 px-4 py-2 rounded transition-colors"
            >
              <MessageSquare size={20} />
            </button>
          </div>
        </section>
      </main>
    </div>
  );
}

export default App;
