import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Lobby() {
  const { logout, user } = useAuth();
  const navigate = useNavigate();
  
  const [players, setPlayers] = useState([
    { id: 1, name: user?.email?.split('@')[0] || "Você", status: "online", role: "Detective", isBot: false },
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

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const botNames = [
    "Shadow_Hunter", "Night_Stalker", "Dark_Phoenix", "Silent_Reaper",
    "Ghost_Whisper", "Blood_Moon", "Crimson_Blade", "Phantom_Eyes",
    "Raven_Soul", "Death_Dealer"
  ];

  const botRoles = ["Suspect", "Witness", "Detective", "Unknown", "Informant"];

  const addBot = () => {
    const availableBots = botNames.filter(
      name => !players.some(p => p.name === name)
    );
    
    if (availableBots.length === 0 || players.length >= 10) {
      return;
    }

    const randomName = availableBots[Math.floor(Math.random() * availableBots.length)];
    const randomRole = botRoles[Math.floor(Math.random() * botRoles.length)];

    const newBot = {
      id: players.length + 1,
      name: randomName,
      status: "online",
      role: randomRole,
      isBot: true
    };

    setPlayers([...players, newBot]);
  };

  const fillWithBots = () => {
    const availableBots = botNames.filter(
      name => !players.some(p => p.name === name)
    );
    
    const botsNeeded = Math.min(10 - players.length, availableBots.length);
    const newBots = [];

    for (let i = 0; i < botsNeeded; i++) {
      const randomName = availableBots[i];
      const randomRole = botRoles[Math.floor(Math.random() * botRoles.length)];
      
      newBots.push({
        id: players.length + i + 1,
        name: randomName,
        status: "online",
        role: randomRole,
        isBot: true
      });
    }

    setPlayers([...players, ...newBots]);
  };

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
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-primaryRed to-lightRed flex items-center justify-center">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
              </div>
              <div>
                <h1 className="text-xl font-bold text-white tracking-wide font-cinzel">Sala Geral</h1>
                <p className="text-xs text-accentRed/70 tracking-wider font-roboto">{players.length} jogadores online</p>
              </div>
            </div>
            
            <button 
              onClick={handleLogout}
              className="px-4 py-2 bg-primaryRed/20 hover:bg-accentRed/30 border border-accentRed/30 rounded-lg text-accentRed text-sm font-medium tracking-wide transition-all font-roboto"
            >
              Sair
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="relative z-10 h-[calc(100vh-73px)] flex">
        {/* Left Panel - Players */}
        <div className="w-80 border-r border-accentRed/30 backdrop-blur-xl bg-darkGray/40 flex flex-col">
          <div className="px-4 py-3 border-b border-accentRed/30">
            <h2 className="text-xs tracking-widest text-accentRed/70 uppercase font-light font-roboto">Jogadores</h2>
          </div>
          
          <div className="flex-1 overflow-y-auto p-4 space-y-2">
            {players.map((player) => (
              <div key={player.id} className="group p-3 rounded-lg bg-charcoalBlack/50 border border-primaryRed/20 hover:border-accentRed/40 hover:bg-charcoalBlack/70 transition-all cursor-pointer">
                <div className="flex items-center gap-3">
                  <div className="relative">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primaryRed/50 to-accentRed/50 flex items-center justify-center">
                      <span className="text-white font-bold text-sm font-roboto">{player.name[0]}</span>
                    </div>
                    <div className={`absolute bottom-0 right-0 w-3 h-3 rounded-full border-2 border-charcoalBlack ${
                      player.status === 'online' ? 'bg-green-500' : 'bg-agedGold'
                    }`}></div>
                  </div>
                  
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium text-white font-roboto">{player.name}</p>
                      {player.isBot && (
                        <span className="text-xs px-2 py-0.5 bg-agedGold/20 border border-agedGold/40 rounded text-agedGold font-roboto">
                          BOT
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-accentRed/70 font-roboto">{player.role}</p>
                  </div>
                  
                  <svg className="w-5 h-5 text-accentRed/30 group-hover:text-accentRed/60 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Center Panel - Game Area */}
        <div className="flex-1 flex flex-col items-center justify-center p-8">
          <div className="max-w-2xl w-full">
            {/* Game Status Card */}
            <div className="backdrop-blur-xl bg-darkGray/60 border border-accentRed/30 rounded-2xl p-8 relative overflow-hidden">
              <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-accentRed to-transparent"></div>
              
              {/* Pulsing effect */}
              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-64 h-64 bg-accentRed/5 rounded-full blur-3xl animate-pulse"></div>
              
              <div className="relative z-10 text-center">
                <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-primaryRed/50 border border-accentRed/30 mb-6 relative">
                  <svg className="w-10 h-10 text-accentRed" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <div className="absolute inset-0 rounded-full border border-accentRed/20 animate-ping"></div>
                </div>
                
                <h2 className="text-2xl font-bold text-white mb-2 font-cinzel">Aguardando Jogadores</h2>
                <p className="text-accentRed/70 text-sm mb-8 font-roboto">Mínimo de 3 jogadores para iniciar</p>
                
                <div className="flex items-center justify-center gap-8 mb-8">
                  <div className="text-center">
                    <div className="text-3xl font-bold text-accentRed font-cinzel">{players.length}</div>
                    <div className="text-xs text-lightGray uppercase tracking-wider font-roboto">Online</div>
                  </div>
                  <div className="w-px h-12 bg-accentRed/30"></div>
                  <div className="text-center">
                    <div className="text-3xl font-bold text-mediumGray font-cinzel">3</div>
                    <div className="text-xs text-mediumGray uppercase tracking-wider font-roboto">Mínimo</div>
                  </div>
                  <div className="w-px h-12 bg-accentRed/30"></div>
                  <div className="text-center">
                    <div className="text-3xl font-bold text-mediumGray font-cinzel">10</div>
                    <div className="text-xs text-mediumGray uppercase tracking-wider font-roboto">Máximo</div>
                  </div>
                </div>

                {/* Botões de Bots */}
                <div className="flex gap-3 mb-6">
                  <button 
                    onClick={addBot}
                    disabled={players.length >= 10}
                    className="flex-1 px-4 py-2 bg-darkGray/60 hover:bg-darkGray/80 border border-accentRed/30 hover:border-accentRed/50 text-accentRed text-sm font-medium tracking-wide rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed font-roboto"
                  >
                    + Adicionar Bot
                  </button>
                  <button 
                    onClick={fillWithBots}
                    disabled={players.length >= 10}
                    className="flex-1 px-4 py-2 bg-darkGray/60 hover:bg-darkGray/80 border border-accentRed/30 hover:border-accentRed/50 text-accentRed text-sm font-medium tracking-wide rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed font-roboto"
                  >
                    🤖 Completar com Bots
                  </button>
                </div>
                
                <button 
                  onClick={() => {
                    // TODO: Conectar ao WebSocket e enviar comando de início com lista de jogadores
                    console.log("Iniciando partida com jogadores:", players);
                    alert(`Partida iniciando com ${players.length} jogadores (${players.filter(p => p.isBot).length} bots)`);
                  }}
                  className="w-full px-8 py-3 bg-gradient-to-r from-primaryRed to-lightRed hover:from-accentRed hover:to-lightRed text-white font-medium tracking-wider uppercase text-sm rounded-lg transition-all duration-300 shadow-lg shadow-primaryRed/50 hover:shadow-accentRed/70 hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed font-roboto" 
                  disabled={players.length < 3}
                >
                  Iniciar Partida
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Right Panel - Chat */}
        <div className="w-96 border-l border-accentRed/30 backdrop-blur-xl bg-darkGray/40 flex flex-col">
          <div className="px-4 py-3 border-b border-accentRed/30">
            <h2 className="text-xs tracking-widest text-accentRed/70 uppercase font-light font-roboto">Chat</h2>
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
                      <span className="text-xs font-medium text-accentRed font-roboto">{msg.user}</span>
                      <span className="text-xs text-mediumGray font-roboto">{msg.time}</span>
                    </div>
                    <p className="text-sm text-offWhite font-roboto">{msg.text}</p>
                  </div>
                )}
              </div>
            ))}
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
              />
              <button
                onClick={sendMessage}
                className="px-4 py-2 bg-primaryRed hover:bg-accentRed rounded-lg text-white transition-colors"
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