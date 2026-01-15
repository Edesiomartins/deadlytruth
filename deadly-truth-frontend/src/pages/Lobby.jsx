import { useState } from "react";

export default function Lobby() {
  const [players] = useState([
    { id: 1, name: "Shadow_Hunter", status: "online", role: "Detective" },
    { id: 2, name: "Night_Stalker", status: "online", role: "Suspect" },
    { id: 3, name: "Dark_Phoenix", status: "away", role: "Witness" },
    { id: 4, name: "Silent_Reaper", status: "online", role: "Unknown" }
  ]);
  
  const [messages, setMessages] = useState([
    { id: 1, user: "Shadow_Hunter", text: "Alguém pronto para começar?", time: "18:45" },
    { id: 2, user: "Night_Stalker", text: "Estou pronto. Vai ser intenso...", time: "18:46" },
    { id: 3, user: "Sistema", text: "Aguardando mais jogadores...", time: "18:47", system: true }
  ]);
  
  const [newMessage, setNewMessage] = useState("");

  const sendMessage = () => {
    if (newMessage.trim()) {
      setMessages([...messages, {
        id: messages.length + 1,
        user: "Você",
        text: newMessage,
        time: new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
      }]);
      setNewMessage("");
    }
  };

  return (
    <div className="min-h-screen bg-black relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-red-950/20 via-black to-purple-950/20"></div>
      
      <div className="absolute inset-0 opacity-10">
        <div
          className="absolute inset-0"
          style={{
            backgroundImage:
              "linear-gradient(rgba(220, 38, 38, 0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(220, 38, 38, 0.1) 1px, transparent 1px)",
            backgroundSize: "50px 50px",
          }}
        ></div>
      </div>

      <div className="relative z-10 border-b border-red-900/30 backdrop-blur-xl bg-black/40">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-red-600 to-red-800 flex items-center justify-center">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
              </div>
              <div>
                <h1 className="text-xl font-bold text-white tracking-wide">Sala Geral</h1>
                <p className="text-xs text-red-400/70 tracking-wider">4 jogadores online</p>
              </div>
            </div>
            
            <button className="px-4 py-2 bg-red-600/20 hover:bg-red-600/30 border border-red-500/30 rounded-lg text-red-400 text-sm font-medium tracking-wide transition-all">
              Sair
            </button>
          </div>
        </div>
      </div>

      <div className="relative z-10 h-[calc(100vh-73px)] flex">
        <div className="w-80 border-r border-red-900/30 backdrop-blur-xl bg-black/20 flex flex-col">
          <div className="px-4 py-3 border-b border-red-900/30">
            <h2 className="text-xs tracking-widest text-red-400/70 uppercase font-light">Jogadores</h2>
          </div>
          
          <div className="flex-1 overflow-y-auto p-4 space-y-2">
            {players.map((player) => (
              <div key={player.id} className="group p-3 rounded-lg bg-black/30 border border-red-900/20 hover:border-red-900/40 hover:bg-black/40 transition-all cursor-pointer">
                <div className="flex items-center gap-3">
                  <div className="relative">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-red-600/50 to-purple-600/50 flex items-center justify-center">
                      <span className="text-white font-bold text-sm">{player.name[0]}</span>
                    </div>
                    <div className={`absolute bottom-0 right-0 w-3 h-3 rounded-full border-2 border-black ${
                      player.status === 'online' ? 'bg-green-500' : 'bg-yellow-500'
                    }`}></div>
                  </div>
                  
                  <div className="flex-1">
                    <p className="text-sm font-medium text-white">{player.name}</p>
                    <p className="text-xs text-red-400/70">{player.role}</p>
                  </div>
                  
                  <svg className="w-5 h-5 text-red-400/30 group-hover:text-red-400/60 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="flex-1 flex flex-col items-center justify-center p-8">
          <div className="max-w-2xl w-full">
            <div className="backdrop-blur-xl bg-black/40 border border-red-900/30 rounded-2xl p-8 relative overflow-hidden">
              <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-red-500 to-transparent"></div>
              
              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-64 h-64 bg-red-600/5 rounded-full blur-3xl animate-pulse"></div>
              
              <div className="relative z-10 text-center">
                <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-red-950/50 border border-red-500/30 mb-6 relative">
                  <svg className="w-10 h-10 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <div className="absolute inset-0 rounded-full border border-red-500/20 animate-ping"></div>
                </div>
                
                <h2 className="text-2xl font-bold text-white mb-2">Aguardando Jogadores</h2>
                <p className="text-red-400/70 text-sm mb-8">Mínimo de 6 jogadores para iniciar</p>
                
                <div className="flex items-center justify-center gap-8 mb-8">
                  <div className="text-center">
                    <div className="text-3xl font-bold text-red-400">4</div>
                    <div className="text-xs text-gray-500 uppercase tracking-wider">Online</div>
                  </div>
                  <div className="w-px h-12 bg-red-900/30"></div>
                  <div className="text-center">
                    <div className="text-3xl font-bold text-gray-600">6</div>
                    <div className="text-xs text-gray-600 uppercase tracking-wider">Mínimo</div>
                  </div>
                  <div className="w-px h-12 bg-red-900/30"></div>
                  <div className="text-center">
                    <div className="text-3xl font-bold text-gray-600">10</div>
                    <div className="text-xs text-gray-600 uppercase tracking-wider">Máximo</div>
                  </div>
                </div>
                
                <button className="px-8 py-3 bg-gradient-to-r from-red-600 to-red-700 hover:from-red-500 hover:to-red-600 text-white font-medium tracking-wider uppercase text-sm rounded-lg transition-all duration-300 shadow-lg shadow-red-900/50 hover:shadow-red-900/70 hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed" disabled>
                  Iniciar Partida
                </button>
              </div>
            </div>
          </div>
        </div>

        <div className="w-96 border-l border-red-900/30 backdrop-blur-xl bg-black/20 flex flex-col">
          <div className="px-4 py-3 border-b border-red-900/30">
            <h2 className="text-xs tracking-widest text-red-400/70 uppercase font-light">Chat</h2>
          </div>
          
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {messages.map((msg) => (
              <div key={msg.id} className={`${msg.system ? 'text-center' : ''}`}>
                {msg.system ? (
                  <div className="inline-block px-3 py-1 rounded-full bg-red-950/30 border border-red-900/30">
                    <p className="text-xs text-red-400/70">{msg.text}</p>
                  </div>
                ) : (
                  <div className="bg-black/30 border border-red-900/20 rounded-lg p-3">
                    <div className="flex items-baseline gap-2 mb-1">
                      <span className="text-xs font-medium text-red-400">{msg.user}</span>
                      <span className="text-xs text-gray-600">{msg.time}</span>
                    </div>
                    <p className="text-sm text-gray-300">{msg.text}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
          
          <div className="p-4 border-t border-red-900/30">
            <div className="flex gap-2">
              <input
                type="text"
                value={newMessage}
                onChange={(e) => setNewMessage(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                placeholder="Digite sua mensagem..."
                className="flex-1 px-3 py-2 bg-black/50 border border-red-900/40 rounded-lg text-sm text-gray-100 placeholder-gray-600 focus:outline-none focus:border-red-500/60 focus:ring-2 focus:ring-red-500/20 transition-all"
              />
              <button
                onClick={sendMessage}
                className="px-4 py-2 bg-red-600 hover:bg-red-500 rounded-lg text-white transition-colors"
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
