import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";

export default function Game() {
    const { roomId } = useParams();
    const navigate = useNavigate();
    const ws = useRef(null);
    
    // ✅ ESTADO DO JOGO
    const [myPlayerId, setMyPlayerId] = useState(null);  // ID numérico (1, 2, 3)
    const [myPlayerName, setMyPlayerName] = useState(null);  // Nome do jogador
    const [currentTurnPlayerId, setCurrentTurnPlayerId] = useState(null);
    const [players, setPlayers] = useState([]);
    const [caso, setCaso] = useState(null);
    const [pistas, setPistas] = useState([]);
    const [messages, setMessages] = useState([]);
    const [messageInput, setMessageInput] = useState("");
    const [gameActive, setGameActive] = useState(false);
    const [gameState, setGameState] = useState("lobby");
    const [systemMessage, setSystemMessage] = useState("");
    const [loading, setLoading] = useState(true);
    const [currentPlayerName, setCurrentPlayerName] = useState(null);
    const [turnTimeRemaining, setTurnTimeRemaining] = useState(60);
    const [gameTimeRemaining, setGameTimeRemaining] = useState(7200);
    const [gameElapsedTime, setGameElapsedTime] = useState(0);
    const [canEndGame, setCanEndGame] = useState(false);
    const [playerStatus, setPlayerStatus] = useState("alive");
    
    // ✅ NOVOS ESTADOS PARA O SISTEMA DE ASSASSINATO
    const [isKiller, setIsKiller] = useState(false);
    const [selectedTarget, setSelectedTarget] = useState(null);
    const [showKillModal, setShowKillModal] = useState(false);
    const [alivePlayersForKill, setAlivePlayersForKill] = useState([]);
    
    const messagesEndRef = useRef(null);
    const turnTimerRef = useRef(null);
    const gameTimerRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

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
    
    // ✅ CONECTAR AO WEBSOCKET
    useEffect(() => {
        const token = localStorage.getItem("jwt_token") || localStorage.getItem("token");
        
        if (!token) {
            navigate("/login");
            return;
        }
        
        const apiUrl = import.meta.env.VITE_API_URL || "https://deadlytruth-backend-production.up.railway.app";
        const wsUrl = apiUrl.replace(/^http/, 'ws');
        const wsUrlFinal = `${wsUrl}/ws/${roomId}?token=${token}`;
        
        ws.current = new WebSocket(wsUrlFinal);
        
        ws.current.onopen = () => {
            console.log("✅ WebSocket conectado");
            setLoading(false);
        };
        
        ws.current.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                console.log("📨 Mensagem recebida:", message.type, message);
                
                handleWebSocketMessage(message);
            } catch (error) {
                console.error("❌ Erro ao processar mensagem:", error);
            }
        };
        
        ws.current.onerror = (error) => {
            console.error("❌ Erro WebSocket:", error);
        };
        
        ws.current.onclose = () => {
            console.log("🔌 WebSocket desconectado");
        };
        
        return () => {
            if (ws.current) ws.current.close();
        };
    }, [roomId, navigate]);
    
    // ✅ HANDLER DE MENSAGENS WEBSOCKET
    const handleWebSocketMessage = (message) => {
        switch (message.type) {
            case "hello":
                console.log("👋 Conectado à sala");
                // Extrair seu ID do payload
                if (message.payload?.player_id) {
                    setMyPlayerId(String(message.payload.player_id));
                    console.log("✅ Seu ID:", message.payload.player_id);
                }
                // Também pode vir diretamente
                if (message.player_id) {
                    setMyPlayerId(String(message.player_id));
                    console.log("✅ Seu ID (direto):", message.player_id);
                }
                // Inicializa lista de jogadores se disponível
                if (message.payload?.players && Array.isArray(message.payload.players)) {
                    setPlayers(message.payload.players);
                }
                // Handler para caso recebido via hello
                if (message.case) {
                    setCaso(message.case);
                }
                break;
            
            case "game_start":
                console.log("🎮 Jogo iniciado!");
                setCaso(message.case || message.payload?.case);
                setPistas([]);
                setPlayers(message.players || []);
                setGameActive(true);
                setGameState("playing");
                
                // ✅ Definir current_turn_player_id
                const currentTurnId = String(message.current_turn_player_id || message.turnoAtual || "");
                if (currentTurnId) {
                    setCurrentTurnPlayerId(currentTurnId);
                    console.log("🎯 Turno atual:", currentTurnId);
                } else {
                    console.warn("⚠️ current_turn_player_id está vazio!");
                }
                
                setSystemMessage("🎭 O MESTRE ANUNCIA: O mistério começou!");
                break;
            
            case "turn_start":
                console.log("🎯 Novo turno:", message.player_name);
                
                // ✅ CRÍTICO: Usar player_id, não turnoAtual
                const newTurnoId = String(message.player_id || message.turnoAtual || message.player_identifier || "");
                if (newTurnoId) {
                    setCurrentTurnPlayerId(newTurnoId);
                    console.log("🎯 Turno ID:", newTurnoId);
                    console.log("✅ Seu turno?", myPlayerId === newTurnoId);
                } else {
                    console.warn("⚠️ turnoAtual está vazio!");
                }
                
                setCurrentPlayerName(message.player_name || message.player || "Jogador");
                
                if (message.time_limit) {
                    setTurnTimeRemaining(message.time_limit);
                }
                if (message.game_time_remaining !== undefined) {
                    setGameTimeRemaining(message.game_time_remaining);
                }
                if (message.game_elapsed_time !== undefined) {
                    setGameElapsedTime(message.game_elapsed_time);
                }
                if (message.can_end_game !== undefined) {
                    setCanEndGame(message.can_end_game);
                }
                
                // Inicia contador do turno
                if (turnTimerRef.current) {
                    clearInterval(turnTimerRef.current);
                }
                let turnTime = message.time_limit || 60;
                turnTimerRef.current = setInterval(() => {
                    setTurnTimeRemaining(prev => {
                        const newTime = Math.max(0, prev - 1);
                        if (newTime === 0) {
                            clearInterval(turnTimerRef.current);
                        }
                        return newTime;
                    });
                }, 1000);
                
                setSystemMessage(`🎯 Turno de ${message.player_name || message.player || "Jogador"}`);
                break;
            
            case "turno":
                console.log("🎯 Turno atualizado:", message.player_id);
                const turnoId = String(message.player_id || "");
                if (turnoId) {
                    setCurrentTurnPlayerId(turnoId);
                }
                break;
            
            case "player_message":
            case "bot_message":
            case "chat":
                console.log("💬 Mensagem:", message.player || message.player_id, message.message || message.content);
                setMessages(prev => [...prev, {
                    id: Date.now(),
                    player: message.player || message.player_id || "Jogador",
                    text: message.message || message.content || "",
                    dead: message.dead || false,
                    time: new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
                }]);
                break;
            
            case "pista":
                console.log("🔍 Pista:", message.text);
                setPistas(prev => [...prev, message.text]);
                setMessages(prev => [...prev, {
                    id: Date.now(),
                    player: "🧠 MESTRE",
                    text: message.text,
                    dead: false,
                    system: true,
                    time: new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
                }]);
                break;
            
            case "caso":
                console.log("📋 Caso recebido via mensagem tipo 'caso'");
                try {
                    let jsonStr = message.text;
                    // Tenta extrair JSON de markdown se necessário
                    if (jsonStr.includes('```json')) {
                        const match = jsonStr.match(/```json\s*([\s\S]*?)\s*```/);
                        if (match) jsonStr = match[1];
                    }
                    const parsed = JSON.parse(jsonStr);
                    if (parsed && typeof parsed === "object") {
                        setCaso(parsed);
                        setSystemMessage("🎭 O MESTRE ANUNCIA: O mistério começou!");
                    }
                } catch (error) {
                    console.error("❌ Erro ao parsear caso:", error);
                }
                break;
            
            case "status":
                console.log("📊 Status:", message.msg || message.message);
                setSystemMessage(message.msg || message.message || "");
                break;
            
            case "you_are_killer":
                console.log("🔪 Você é o assassino!");
                setIsKiller(true); // ✅ ATUALIZA ESTADO isKiller
                setSystemMessage("🔪 VOCÊ É O ASSASSINO! Mate seus inimigos sem ser descoberto.");
                // Atualiza lista de alvos vivos
                const allPlayers = players.length > 0 ? players : (message.players || []);
                const alive = allPlayers.filter(p => 
                    p.is_alive && String(p.id) !== String(myPlayerId)
                );
                setAlivePlayersForKill(alive);
                break;
            
            case "player_death": // ✅ NOVO: TRATAR MORTE DE JOGADOR
                console.log("💀 Jogador morto:", message.victim_name || message.victim);
                const victimName = message.victim_name || message.victim || "Jogador";
                setMessages(prev => [...prev, {
                    id: Date.now(),
                    player: "SISTEMA",
                    text: `💀 ${victimName} foi encontrado morto!`,
                    dead: false,
                    system: true,
                    time: new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
                }]);
                // Atualizar o estado dos jogadores para refletir a morte
                setPlayers(prev => prev.map(p => 
                    String(p.id) === String(message.victim_id) || p.name === victimName || p.nickname === victimName
                        ? { ...p, is_alive: false, status: "dead" } 
                        : p
                ));
                // Se for assassino, atualizar lista de alvos
                if (isKiller) {
                    setAlivePlayersForKill(prev => prev.filter(p => 
                        String(p.id) !== String(message.victim_id) && p.name !== victimName && p.nickname !== victimName
                    ));
                }
                // Adiciona pista se houver
                if (message.clue) {
                    setPistas(prev => [...prev, message.clue]);
                }
                break;
            
            case "players_update":
            case "jogadores":
                console.log("👥 Jogadores atualizados:", message.players);
                if (Array.isArray(message.players)) {
                    setPlayers(message.players);
                    // ✅ ATUALIZAR LISTA DE ALVOS SE FOR ASSASSINO
                    if (isKiller) {
                        const alive = message.players.filter(p => 
                            p.is_alive && String(p.id) !== String(myPlayerId)
                        );
                        setAlivePlayersForKill(alive);
                    }
                }
                break;
            
            case "time_update":
                if (message.turn_time_remaining !== undefined) {
                    setTurnTimeRemaining(message.turn_time_remaining);
                }
                if (message.game_time_remaining !== undefined) {
                    setGameTimeRemaining(message.game_time_remaining);
                }
                if (message.game_elapsed_time !== undefined) {
                    setGameElapsedTime(message.game_elapsed_time);
                }
                if (message.can_end_game !== undefined) {
                    setCanEndGame(message.can_end_game);
                }
                break;
            
            case "error":
                console.error("❌ Erro:", message.message || message.msg);
                setSystemMessage(`❌ Erro: ${message.message || message.msg || "Ocorreu um erro"}`);
                break;
            
            default:
                console.log("📨 Mensagem desconhecida:", message.type);
        }
    };
    
    // ✅ VALIDAR SE É SEU TURNO
    const isMyTurn = myPlayerId && currentTurnPlayerId && 
                     String(myPlayerId) === String(currentTurnPlayerId);
    
    console.log("🔍 DEBUG:", {
        myPlayerId,
        currentTurnPlayerId,
        isMyTurn,
        comparison: `${myPlayerId} === ${currentTurnPlayerId}`
    });
    
    // ✅ ENVIAR MENSAGEM
    const handleSendMessage = () => {
        console.log("📤 Tentando enviar mensagem");
        console.log("   isMyTurn:", isMyTurn);
        console.log("   myPlayerId:", myPlayerId);
        console.log("   currentTurnPlayerId:", currentTurnPlayerId);
        
        if (!isMyTurn) {
            console.warn("⏳ Não é sua vez!");
            setSystemMessage("⏳ Aguarde sua vez!");
            return;
        }
        
        if (!messageInput.trim()) {
            setSystemMessage("📝 Digite uma mensagem");
            return;
        }
        
        if (!ws.current || ws.current.readyState !== WebSocket.OPEN) {
            setSystemMessage("❌ Não conectado ao servidor");
            return;
        }
        
        // ✅ Enviar para o backend
        ws.current.send(JSON.stringify({
            type: "message",
            text: messageInput,
            player_id: myPlayerId
        }));
        
        setMessageInput("");
        console.log("✅ Mensagem enviada");
    };

    const handleLeave = () => {
        if (ws.current) ws.current.close();
        navigate("/lobby");
    };

    // ✅ FUNÇÃO PARA INICIAR PROCESSO DE MATAR
    const handleKill = (targetId) => {
        console.log("🔪 Tentando matar:", targetId);
        
        if (!isKiller) {
            setSystemMessage("❌ Você não é o assassino!");
            return;
        }
        
        if (!isMyTurn) {
            setSystemMessage("❌ Não é sua vez!");
            return;
        }
        
        setSelectedTarget(targetId);
        setShowKillModal(true); // Abre o modal de confirmação
    };

    // ✅ FUNÇÃO PARA CONFIRMAR A MORTE
    const confirmKill = () => {
        console.log("🔪 Confirmando morte de:", selectedTarget);
        
        if (!ws.current || ws.current.readyState !== WebSocket.OPEN) {
            setSystemMessage("❌ Não conectado ao servidor");
            return;
        }
        
        ws.current.send(JSON.stringify({
            type: "kill",
            target_id: selectedTarget,
            player_id: myPlayerId // O assassino
        }));
        
        setShowKillModal(false); // Fecha o modal
        setSelectedTarget(null);
        setSystemMessage("🔪 Você matou um jogador!");
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
    
    // ✅ RENDERIZAR
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
                                {caso?.case_id || "DEADLY TRUTH"}
                            </h1>
                            <div className="flex items-center gap-3 mt-1 flex-wrap">
                                <p className="text-xs text-accentRed/70 tracking-wider font-roboto">
                                    {ws.current?.readyState === WebSocket.OPEN ? "🔴 Ao vivo" : "⚫ Desconectado"}
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
                    
                    {/* Exibe caso recebido via mensagem tipo "caso" */}
                    {caso && (
                        <div className="p-4 space-y-3 border-b border-accentRed/30">
                            <h2 className="text-lg font-bold text-accentRed font-cinzel">🗂️ Caso #{caso.case_id}</h2>
                            <div className="space-y-2 text-sm font-roboto">
                                <p><strong className="text-white">Nível:</strong> <span className="text-offWhite/80">{caso.nivel}</span></p>
                                <p><strong className="text-white">Cenário:</strong> <span className="text-offWhite/80">{caso.cenario}</span></p>
                                {caso.descricao && (
                                    <div>
                                        <p className="text-white font-semibold mb-1">Descrição:</p>
                                        <p className="text-offWhite/80 leading-relaxed">{caso.descricao}</p>
                                    </div>
                                )}
                                {caso.historia && (
                                    <div>
                                        <p className="text-white font-semibold mb-1">História:</p>
                                        <p className="text-offWhite/80 leading-relaxed">{caso.historia}</p>
                                    </div>
                                )}
                                {caso.suspeitos && caso.suspeitos.length > 0 && (
                                    <p><strong className="text-white">Suspeitos:</strong> <span className="text-offWhite/80">{caso.suspeitos.join(", ")}</span></p>
                                )}
                            </div>
                        </div>
                    )}
                    
                    {/* Exibe pistas descobertas */}
                    {pistas.length > 0 && (
                        <div className="p-4 border-b border-accentRed/30">
                            <h3 className="text-sm font-bold text-accentRed/70 uppercase tracking-wider font-roboto mb-3">
                                🧩 Pistas Descobertas
                            </h3>
                            <ul className="space-y-2 max-h-64 overflow-y-auto">
                                {pistas.map((pista, index) => (
                                    <li key={index} className="text-xs text-offWhite/80 font-roboto flex items-start gap-2">
                                        <span className="text-accentRed mt-1">•</span>
                                        <span>{pista}</span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}
                    
                    {!caso && (
                        <div className="p-4 text-center text-lightGray/50">
                            <p className="font-roboto">Aguardando o mestre gerar o caso...</p>
                        </div>
                    )}
                    
                    {/* Lista de Jogadores */}
                    <div className="mt-auto border-t border-accentRed/30 p-4">
                        {(() => {
                            const alivePlayers = Array.isArray(players)
                                ? players.filter(p => p.status === "alive" || !p.status)
                                : [];
                            
                            const deadPlayers = Array.isArray(players)
                                ? players.filter(p => p.status === "dead")
                                : [];
                            
                            return (
                                <>
                                    {alivePlayers.length > 0 && (
                                        <div className="mb-4">
                                            <h3 className="text-xs font-bold text-accentRed/70 uppercase tracking-wider font-roboto mb-2">
                                                🎮 Jogadores
                                            </h3>
                                            <ul className="space-y-1">
                                                {alivePlayers.map((p, idx) => (
                                                    <li key={idx} className={`text-xs text-offWhite/80 font-roboto flex items-center gap-2 ${
                                                        (p.id === currentTurnPlayerId || p.name === currentTurnPlayerId) ? 'text-accentRed font-bold' : ''
                                                    }`}>
                                                        <div className={`w-2 h-2 rounded-full ${
                                                            (p.id === currentTurnPlayerId || p.name === currentTurnPlayerId) ? 'bg-accentRed animate-pulse' : 'bg-green-500'
                                                        }`}></div>
                                                        {p.nickname || p.name || p.id || `Jogador ${idx + 1}`}
                                                        {(p.id === currentTurnPlayerId || p.name === currentTurnPlayerId) && <span>🎯</span>}
                                                        {p.is_bot && <span>🤖</span>}
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}
                                    
                                    {deadPlayers.length > 0 && (
                                        <div>
                                            <h3 className="text-xs font-bold text-gray-400/70 uppercase tracking-wider font-roboto mb-2">
                                                👻 Espectadores
                                            </h3>
                                            <ul className="space-y-1">
                                                {deadPlayers.map((p, idx) => (
                                                    <li key={idx} className="text-xs text-gray-400/60 font-roboto flex items-center gap-2">
                                                        <div className="w-2 h-2 rounded-full bg-gray-500"></div>
                                                        {p.nickname || p.name || p.id || `Jogador ${idx + 1}`}
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}
                                </>
                            );
                        })()}
                        
                        {/* ✅ BOTÃO DE MATAR - APENAS SE FOR ASSASSINO E SEU TURNO */}
                        {isKiller && isMyTurn && alivePlayersForKill.length > 0 && (
                            <div className="mt-4 pt-4 border-t border-accentRed/30">
                                <h3 className="text-xs font-bold text-accentRed/70 uppercase tracking-wider font-roboto mb-2">
                                    🔪 Matar Jogador
                                </h3>
                                <div className="space-y-2">
                                    {alivePlayersForKill.map(player => (
                                        <button
                                            key={player.id}
                                            onClick={() => handleKill(player.id)}
                                            className="w-full px-3 py-2 bg-accentRed/20 hover:bg-accentRed/30 border border-accentRed/40 rounded-lg text-xs text-accentRed font-roboto transition-all"
                                        >
                                            🔪 Matar {player.nickname || player.name || player.id}
                                        </button>
                                    ))}
                                </div>
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
                                {(() => {
                                    const meuID = localStorage.getItem("player_id") || myPlayerId || "Você";
                                    const naoEhMinhaVez = currentTurnPlayerId && currentTurnPlayerId !== meuID && String(currentTurnPlayerId) !== String(meuID);
                                    
                                    return naoEhMinhaVez && currentPlayerName && (
                                        <div className="mb-2 px-3 py-2 bg-accentRed/20 border border-accentRed/30 rounded-lg">
                                            <p className="text-xs text-accentRed/80 font-roboto text-center">
                                                ⏳ Aguarde sua vez. É a vez de <span className="font-bold text-accentRed">{currentPlayerName}</span>
                                            </p>
                                        </div>
                                    );
                                })()}
                                <div className="flex gap-2">
                                    <input
                                        type="text"
                                        value={messageInput}
                                        onChange={(e) => setMessageInput(e.target.value)}
                                        onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                                        placeholder={isMyTurn ? "Digite sua mensagem..." : "Aguarde sua vez..."}
                                        className="flex-1 px-3 py-2 bg-charcoalBlack/50 border border-primaryRed/40 rounded-lg text-sm text-offWhite placeholder-lightGray/50 focus:outline-none focus:border-accentRed/60 focus:ring-2 focus:ring-accentRed/20 transition-all font-roboto disabled:opacity-50 disabled:cursor-not-allowed"
                                        disabled={!isMyTurn || ws.current?.readyState !== WebSocket.OPEN}
                                    />
                                    <button
                                        onClick={handleSendMessage}
                                        disabled={!isMyTurn || ws.current?.readyState !== WebSocket.OPEN}
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
            
            {/* MENSAGEM DO SISTEMA */}
            {systemMessage && (
                <div className="fixed bottom-4 left-1/2 transform -translate-x-1/2 px-6 py-3 bg-accentRed text-white rounded-lg shadow-lg z-50 font-roboto">
                    {systemMessage}
                </div>
            )}

            {/* ✅ MODAL DE CONFIRMAÇÃO DE MORTE */}
            {showKillModal && (
                <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center">
                    <div className="bg-darkGray border-2 border-accentRed rounded-lg p-6 max-w-md w-full mx-4">
                        <h2 className="text-xl font-bold text-accentRed font-cinzel mb-4">
                            ⚠️ Confirmar Morte
                        </h2>
                        {(() => {
                            const target = players.find(p => String(p.id) === String(selectedTarget));
                            return (
                                <>
                                    <p className="text-offWhite font-roboto mb-2">
                                        Você tem certeza que quer matar <strong className="text-accentRed">{target?.nickname || target?.name || "este jogador"}</strong>?
                                    </p>
                                    <p className="text-yellow-400 font-roboto text-sm mb-4">
                                        ⚠️ Esta ação é irreversível!
                                    </p>
                                    
                                    <div className="flex gap-3">
                                        <button 
                                            onClick={confirmKill}
                                            className="flex-1 px-4 py-2 bg-accentRed hover:bg-red-600 text-white rounded-lg font-medium transition-colors font-roboto"
                                        >
                                            ✅ Confirmar
                                        </button>
                                        <button 
                                            onClick={() => {
                                                setShowKillModal(false);
                                                setSelectedTarget(null);
                                            }}
                                            className="flex-1 px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg font-medium transition-colors font-roboto"
                                        >
                                            ❌ Cancelar
                                        </button>
                                    </div>
                                </>
                            );
                        })()}
                    </div>
                </div>
            )}
        </div>
    );
}
