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
    
    // ✅ NOVOS ESTADOS PARA O SISTEMA DE VOTACAO E ACUSACAO
    const [votingActive, setVotingActive] = useState(false);
    const [accusedPlayerId, setAccusedPlayerId] = useState(null);
    const [accusedPlayerName, setAccusedPlayerName] = useState("");
    const [accuserPlayerName, setAccuserPlayerName] = useState("");
    const [hasVoted, setHasVoted] = useState(false);
    const [endgameData, setEndgameData] = useState(null);
    
    // ✅ NOVOS ESTADOS PARA O SISTEMA DE INTERROGATORIO
    const [showInterrogateModal, setShowInterrogateModal] = useState(false);
    const [interrogatedTarget, setInterrogatedTarget] = useState(null);
    const [questionInput, setQuestionInput] = useState("");
    const [activeInterrogation, setActiveInterrogation] = useState(null); // { interrogator, target, question }
    const [interrogationResponseInput, setInterrogationResponseInput] = useState("");
    
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
                console.log("👋 Conectado à sala", message);
                // ✅ CORREÇÃO: Extrair player_id NUMÉRICO do payload
                if (message.payload?.player_id) {
                    // player_id agora é numérico (1, 2, 3, ...)
                    setMyPlayerId(String(message.payload.player_id));
                    console.log("✅ Seu ID numérico:", message.payload.player_id);
                }
                // Também pode vir diretamente
                if (message.player_id) {
                    setMyPlayerId(String(message.player_id));
                    console.log("✅ Seu ID (direto):", message.player_id);
                }
                // ✅ Salvar também o nome do jogador
                if (message.payload?.player_name) {
                    setMyPlayerName(message.payload.player_name);
                    console.log("✅ Seu nome:", message.payload.player_name);
                }
                // Inicializa lista de jogadores se disponível
                if (message.players_list && Array.isArray(message.players_list)) {
                    setPlayers(message.players_list);
                } else if (message.payload?.players && Array.isArray(message.payload.players)) {
                    setPlayers(message.payload.players);
                }
                // Handler para caso recebido via hello
                if (message.case || message.payload?.case) {
                    setCaso(message.case || message.payload.case);
                }
                // ✅ Se houver current_turn no hello, definir
                if (message.current_turn || message.current_turn_player_id || message.payload?.current_turn) {
                    const turnId = String(message.current_turn || message.current_turn_player_id || message.payload?.current_turn || "");
                    if (turnId) {
                        setCurrentTurnPlayerId(turnId);
                        console.log("🎯 Turno inicial do hello:", turnId);
                    }
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
            
            case "turn_change":
                console.log("🔄 Mudança de turno:", message.current_player);
                
                // ✅ CORREÇÃO: Usar current_player_id (numérico) se disponível
                if (message.current_player_id !== undefined) {
                    const turnId = String(message.current_player_id);
                    setCurrentTurnPlayerId(turnId);
                    setCurrentPlayerName(message.current_player || "Jogador");
                    console.log("🎯 Novo turno ID (numérico):", turnId);
                } else if (message.current_player) {
                    // Fallback: Buscar o ID do jogador pelo nome
                    const player = players.find(p => 
                        p.name === message.current_player || 
                        p.nickname === message.current_player ||
                        String(p.id) === String(message.current_player) ||
                        String(p.numeric_id) === String(message.current_player)
                    );
                    if (player) {
                        // Usar numeric_id se disponível, senão usar id ou name
                        const playerId = String(player.numeric_id || player.id || player.name || message.current_player);
                        setCurrentTurnPlayerId(playerId);
                        setCurrentPlayerName(message.current_player);
                        console.log("🎯 Turno ID encontrado pelo nome:", playerId);
                    } else {
                        // Se não encontrar, usar o nome diretamente
                        setCurrentTurnPlayerId(String(message.current_player));
                        setCurrentPlayerName(message.current_player);
                        console.warn("⚠️ Jogador não encontrado na lista, usando nome como ID");
                    }
                }
                
                if (message.message) {
                    setSystemMessage(message.message);
                } else {
                    setSystemMessage(`🔄 Turno de ${message.current_player || "Jogador"}`);
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
            
            case "votacao_iniciada":
                console.log("⚖️ Votação iniciada:", message.accused);
                setAccusedPlayerId(message.accused);
                setAccusedPlayerName(message.accused);
                setAccuserPlayerName(message.accuser);
                setVotingActive(true);
                setHasVoted(false);
                setSystemMessage(message.message || `Votação iniciada contra ${message.accused}!`);
                break;
                
            case "voto_registrado":
                console.log("🗳️ Voto de bot registrado:", message.player_name, message.voto);
                setMessages(prev => [...prev, {
                    id: Date.now() + Math.random(),
                    player: "SISTEMA",
                    text: message.message || `🤖 ${message.player_name} votou!`,
                    dead: false,
                    system: true,
                    time: new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
                }]);
                break;
                
            case "vote_registered":
                console.log("✅ Seu voto foi registrado com sucesso!");
                setHasVoted(true);
                setSystemMessage(message.message || "Seu voto foi registrado!");
                break;
                
            case "resultado_votacao":
                console.log("🗳️ Resultado da votação:", message.message);
                setVotingActive(false);
                setAccusedPlayerId(null);
                setAccusedPlayerName("");
                setAccuserPlayerName("");
                setHasVoted(false);
                setSystemMessage(message.message);
                setMessages(prev => [...prev, {
                    id: Date.now() + Math.random(),
                    player: "SISTEMA",
                    text: message.message,
                    dead: false,
                    system: true,
                    time: new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
                }]);
                break;

            case "interrogatorio_iniciado":
                console.log("🔍 Interrogatório iniciado:", message);
                setActiveInterrogation({
                    interrogator: message.interrogator,
                    target: message.target,
                    question: message.question
                });
                setSystemMessage(message.message || `Interrogatório contra ${message.target} iniciado!`);
                break;

            case "resposta_interrogatorio":
                console.log("🔍 Resposta do interrogatório:", message);
                setActiveInterrogation(null);
                setMessages(prev => [...prev, {
                    id: Date.now() + Math.random(),
                    player: "SISTEMA",
                    text: `🔍 Resposta de ${message.player}: "${message.message}"`,
                    dead: false,
                    system: true,
                    time: new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
                }]);
                setSystemMessage(`Interrogatório de ${message.player} concluído!`);
                break;

            case "game_end":
                console.log("🏆 Fim de jogo:", message.winner_name, message.reason);
                setVotingActive(false);
                setEndgameData({
                    winner: message.winner,
                    winner_name: message.winner_name,
                    reason: message.reason
                });
                setSystemMessage(`🏆 Fim de Jogo! Vencedor: ${message.winner_name || message.winner}. ${message.reason || ""}`);
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
    // Compara tanto por ID quanto por nome
    const isMyTurn = myPlayerId && currentTurnPlayerId && (
        String(myPlayerId) === String(currentTurnPlayerId) ||
        String(myPlayerName) === String(currentTurnPlayerId) ||
        String(myPlayerId) === String(currentPlayerName) ||
        String(myPlayerName) === String(currentPlayerName)
    );
    
    console.log("🔍 DEBUG:", {
        myPlayerId,
        myPlayerName,
        currentTurnPlayerId,
        currentPlayerName,
        isMyTurn,
        comparison: `${myPlayerId}/${myPlayerName} === ${currentTurnPlayerId}/${currentPlayerName}`
    });
    
    // ✅ ENVIAR MENSAGEM
    const handleSendMessage = () => {
        console.log("📤 Tentando enviar mensagem");
        console.log("   playerStatus:", playerStatus);
        
        if (playerStatus === "dead") {
            console.warn("💀 Você está morto!");
            setSystemMessage("💀 Você está morto e não pode mais falar no chat!");
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

    // ✅ PASSAR A VEZ
    const handlePassTurn = () => {
        if (!isMyTurn) return;
        if (!ws.current || ws.current.readyState !== WebSocket.OPEN) return;
        
        ws.current.send(JSON.stringify({
            type: "pass_turn"
        }));
        setSystemMessage("⏭️ Você passou a vez!");
    };

    // ✅ INICIAR INTERROGATÓRIO (CLICK NO BOTÃO)
    const handleInterrogateClick = (targetId) => {
        if (!isMyTurn) {
            setSystemMessage("❌ Não é sua vez!");
            return;
        }
        setInterrogatedTarget(targetId);
        setQuestionInput("");
        setShowInterrogateModal(true);
    };

    // ✅ ENVIAR PERGUNTA DO INTERROGATÓRIO
    const submitInterrogation = () => {
        if (!interrogatedTarget || !questionInput.trim()) {
            setSystemMessage("⚠️ Digite uma pergunta válida.");
            return;
        }
        
        if (!ws.current || ws.current.readyState !== WebSocket.OPEN) {
            setSystemMessage("❌ Não conectado ao servidor");
            return;
        }
        
        ws.current.send(JSON.stringify({
            type: "interrogar",
            target: interrogatedTarget,
            question: questionInput.trim()
        }));
        
        setShowInterrogateModal(false);
        setInterrogatedTarget(null);
        setQuestionInput("");
        setSystemMessage("🔍 Pergunta enviada!");
    };

    // ✅ ENVIAR RESPOSTA AO INTERROGATÓRIO (QUANDO INTERROGADO)
    const submitInterrogationResponse = () => {
        if (!interrogationResponseInput.trim()) {
            setSystemMessage("⚠️ A resposta não pode ser vazia.");
            return;
        }
        
        if (!ws.current || ws.current.readyState !== WebSocket.OPEN) {
            setSystemMessage("❌ Não conectado ao servidor");
            return;
        }
        
        ws.current.send(JSON.stringify({
            type: "resposta_interrogatorio",
            message: interrogationResponseInput.trim()
        }));
        
        setInterrogationResponseInput("");
        setSystemMessage("✅ Sua defesa foi enviada!");
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

    // ✅ FUNÇÃO PARA REALIZAR UMA ACUSAÇÃO
    const handleAccuse = (targetId) => {
        console.log("⚖️ Tentando acusar:", targetId);
        
        if (!isMyTurn) {
            setSystemMessage("❌ Não é sua vez!");
            return;
        }
        
        if (!ws.current || ws.current.readyState !== WebSocket.OPEN) {
            setSystemMessage("❌ Não conectado ao servidor");
            return;
        }
        
        ws.current.send(JSON.stringify({
            type: "acusar",
            target: targetId
        }));
        
        setSystemMessage(`⚖️ Você acusou ${targetId}!`);
    };

    // ✅ FUNÇÃO PARA VOTAR
    const handleVote = (voteValue) => {
        console.log("🗳️ Enviando voto:", voteValue);
        
        if (hasVoted) {
            setSystemMessage("⚠️ Você já votou nesta rodada!");
            return;
        }
        
        if (!ws.current || ws.current.readyState !== WebSocket.OPEN) {
            setSystemMessage("❌ Não conectado ao servidor");
            return;
        }
        
        ws.current.send(JSON.stringify({
            type: "voto",
            vote: voteValue // "culpado" ou "inocente"
        }));
        
        setHasVoted(true);
        setSystemMessage(`🗳️ Você votou: ${voteValue}`);
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
                        
                        <div className="flex items-center gap-2">
                            {isMyTurn && (
                                <button 
                                    onClick={handlePassTurn}
                                    className="px-4 py-2 bg-green-600/20 hover:bg-green-600/30 border border-green-600/40 rounded-lg text-green-400 text-sm font-semibold tracking-wide transition-all font-roboto flex items-center gap-2 shadow-md hover:scale-[1.02]"
                                >
                                    Passar Vez ⏭️
                                </button>
                            )}
                            <button 
                                onClick={handleLeave}
                                className="px-4 py-2 bg-primaryRed/20 hover:bg-accentRed/30 border border-accentRed/30 rounded-lg text-accentRed text-sm font-medium tracking-wide transition-all font-roboto"
                            >
                                Sair da Partida
                            </button>
                        </div>
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
                                                    <li key={idx} className={`text-xs text-offWhite/80 font-roboto flex items-center gap-2 py-1 border-b border-white/5 ${
                                                        (p.id === currentTurnPlayerId || p.name === currentTurnPlayerId) ? 'text-accentRed font-bold' : ''
                                                    }`}>
                                                        <div className={`w-2 h-2 rounded-full ${
                                                            (p.id === currentTurnPlayerId || p.name === currentTurnPlayerId) ? 'bg-accentRed animate-pulse' : 'bg-green-500'
                                                        }`}></div>
                                                        <span>{p.nickname || p.name || p.id || `Jogador ${idx + 1}`}</span>
                                                        {(p.id === currentTurnPlayerId || p.name === currentTurnPlayerId) && <span>🎯</span>}
                                                        {p.is_bot && <span>🤖</span>}
                                                        {isMyTurn && (String(p.id) !== String(myPlayerId) && p.name !== myPlayerName) && (
                                                            <div className="ml-auto flex items-center gap-1.5">
                                                                <button 
                                                                    onClick={() => handleInterrogateClick(p.id || p.name)}
                                                                    className="px-2 py-0.5 bg-accentRed/20 hover:bg-accentRed/40 border border-accentRed/30 rounded text-[10px] text-accentRed font-roboto transition-all"
                                                                    title={`Interrogar ${p.nickname || p.name}`}
                                                                >
                                                                    🔍 Interrogar
                                                                </button>
                                                                <button 
                                                                    onClick={() => handleAccuse(p.id || p.name)}
                                                                    className="px-2 py-0.5 bg-accentRed/20 hover:bg-accentRed/40 border border-accentRed/30 rounded text-[10px] text-accentRed font-roboto transition-all"
                                                                    title={`Acusar ${p.nickname || p.name}`}
                                                                >
                                                                    ⚖️ Acusar
                                                                </button>
                                                            </div>
                                                        )}
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
                                {currentPlayerName && (
                                    <div className="mb-2 px-3 py-2 bg-charcoalBlack/40 border border-accentRed/30 rounded-lg">
                                        <p className="text-xs text-offWhite/80 font-roboto text-center">
                                            💬 Chat livre para debate. Vez de realizar ações: <span className="font-bold text-accentRed">{currentPlayerName}</span>
                                        </p>
                                    </div>
                                )}
                                <div className="flex gap-2">
                                    <input
                                        type="text"
                                        value={messageInput}
                                        onChange={(e) => setMessageInput(e.target.value)}
                                        onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                                        placeholder="Digite sua mensagem para o debate..."
                                        className="flex-1 px-3 py-2 bg-charcoalBlack/50 border border-primaryRed/40 rounded-lg text-sm text-offWhite placeholder-lightGray/50 focus:outline-none focus:border-accentRed/60 focus:ring-2 focus:ring-accentRed/20 transition-all font-roboto disabled:opacity-50 disabled:cursor-not-allowed"
                                        disabled={playerStatus === "dead" || ws.current?.readyState !== WebSocket.OPEN}
                                    />
                                    <button
                                        onClick={handleSendMessage}
                                        disabled={playerStatus === "dead" || ws.current?.readyState !== WebSocket.OPEN}
                                        className="px-4 py-2 bg-primaryRed hover:bg-accentRed rounded-lg text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                        title="Enviar mensagem"
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

            {/* 🔍 MODAL DE ENVIO DE INTERROGATÓRIO */}
            {showInterrogateModal && (
                <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center">
                    <div className="bg-darkGray border-2 border-accentRed rounded-xl p-6 max-w-md w-full mx-4 shadow-2xl">
                        <h2 className="text-xl font-bold text-accentRed font-cinzel mb-4 flex items-center gap-2">
                            🔍 Interrogar Suspeito
                        </h2>
                        {(() => {
                            const target = players.find(p => String(p.id) === String(interrogatedTarget) || p.name === interrogatedTarget);
                            const targetName = target?.nickname || target?.name || interrogatedTarget;
                            return (
                                <>
                                    <p className="text-offWhite font-roboto text-sm mb-4">
                                        Digite a pergunta que deseja fazer para <strong className="text-accentRed">{targetName}</strong>. 
                                        {target?.is_bot && " Como ele é um robô de IA, ele responderá imediatamente baseando-se em sua personalidade."}
                                    </p>
                                    
                                    <textarea
                                        value={questionInput}
                                        onChange={(e) => setQuestionInput(e.target.value)}
                                        placeholder="Ex: Onde você estava no momento do crime? O que você sabe sobre a pista encontrada?"
                                        rows={3}
                                        className="w-full px-3 py-2 bg-charcoalBlack/50 border border-primaryRed/40 rounded-lg text-sm text-offWhite placeholder-lightGray/50 focus:outline-none focus:border-accentRed/60 focus:ring-2 focus:ring-accentRed/20 transition-all font-roboto mb-4"
                                    />
                                    
                                    <div className="flex gap-3">
                                        <button 
                                            onClick={submitInterrogation}
                                            className="flex-1 px-4 py-2.5 bg-gradient-to-r from-primaryRed to-accentRed hover:from-accentRed hover:to-lightRed text-white rounded-lg font-bold font-roboto transition-all duration-300 shadow-md shadow-primaryRed/20 hover:scale-[1.02] active:scale-[0.98]"
                                        >
                                            🔍 Perguntar
                                        </button>
                                        <button 
                                            onClick={() => {
                                                setShowInterrogateModal(false);
                                                setInterrogatedTarget(null);
                                                setQuestionInput("");
                                            }}
                                            className="flex-1 px-4 py-2.5 bg-gray-600 hover:bg-gray-700 text-white rounded-lg font-bold font-roboto transition-all"
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

            {/* 🔍 PAINEL DE INTERROGATÓRIO ATIVO */}
            {activeInterrogation && (
                <div className="fixed inset-0 bg-black/80 backdrop-blur-md z-50 flex items-center justify-center">
                    <div className="bg-darkGray border-2 border-accentRed rounded-xl p-8 max-w-lg w-full mx-4 shadow-2xl relative overflow-hidden">
                        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-accentRed to-transparent animate-pulse"></div>
                        
                        <div className="text-center mb-6">
                            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-accentRed/10 border border-accentRed/30 mb-4 text-accentRed">
                                <svg className="w-8 h-8 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                                </svg>
                            </div>
                            <h2 className="text-2xl font-bold text-white font-cinzel tracking-wider">
                                🔍 Interrogatório em Andamento
                            </h2>
                            <p className="text-xs text-lightGray/60 font-roboto mt-1">
                                Uma pergunta crucial foi feita
                            </p>
                        </div>
                        
                        <div className="bg-charcoalBlack/60 border border-accentRed/20 rounded-lg p-5 mb-6">
                            <p className="text-xs text-accentRed uppercase font-bold tracking-wider mb-2 font-roboto">
                                Pergunta de {activeInterrogation.interrogator} para {activeInterrogation.target}:
                            </p>
                            <p className="text-sm font-roboto text-offWhite leading-relaxed italic">
                                "{activeInterrogation.question}"
                            </p>
                        </div>
                        
                        {(() => {
                            const isMeTarget = String(myPlayerId).toLowerCase() === String(activeInterrogation.target).toLowerCase() || 
                                               String(myPlayerName).toLowerCase() === String(activeInterrogation.target).toLowerCase();
                            
                            if (isMeTarget) {
                                return (
                                    <div className="space-y-4">
                                        <p className="text-xs text-yellow-400 font-roboto text-center font-semibold">
                                            ⚠️ Você está sendo interrogado! Digite sua defesa ou resposta abaixo:
                                        </p>
                                        <textarea
                                            value={interrogationResponseInput}
                                            onChange={(e) => setInterrogationResponseInput(e.target.value)}
                                            placeholder="Escreva sua resposta de defesa de forma convincente..."
                                            rows={3}
                                            className="w-full px-3 py-2 bg-charcoalBlack border border-primaryRed/40 rounded-lg text-sm text-offWhite placeholder-lightGray/50 focus:outline-none focus:border-accentRed/60 focus:ring-2 focus:ring-accentRed/20 transition-all font-roboto"
                                        />
                                        <button 
                                            onClick={submitInterrogationResponse}
                                            className="w-full px-4 py-3 bg-gradient-to-r from-primaryRed to-accentRed hover:from-accentRed hover:to-lightRed text-white rounded-lg font-bold font-roboto transition-all duration-300 shadow-md shadow-primaryRed/20 hover:scale-[1.01]"
                                        >
                                            📤 Enviar Defesa
                                        </button>
                                    </div>
                                );
                            } else {
                                return (
                                    <div className="text-center p-5 bg-gray-800/40 border border-gray-700/50 rounded-lg">
                                        <div className="animate-spin h-6 w-6 border-2 border-accentRed border-t-transparent rounded-full mx-auto mb-3"></div>
                                        <p className="text-sm text-gray-400 font-roboto">
                                            Aguardando resposta de <strong className="text-white">{activeInterrogation.target}</strong>...
                                        </p>
                                        <p className="text-xs text-gray-500 font-roboto mt-1">
                                            Todos os jogadores podem acompanhar a resposta no chat.
                                        </p>
                                    </div>
                                );
                            }
                        })()}
                    </div>
                </div>
            )}

            {/* ✅ MODAL DE VOTAÇÃO EM ANDAMENTO */}
            {votingActive && (
                <div className="fixed inset-0 bg-black/85 backdrop-blur-md z-50 flex items-center justify-center">
                    <div className="bg-darkGray border-2 border-accentRed rounded-xl p-8 max-w-md w-full mx-4 shadow-2xl relative overflow-hidden">
                        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-accentRed to-transparent animate-pulse"></div>
                        
                        <div className="text-center mb-6">
                            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-accentRed/10 border border-accentRed/30 mb-4 text-accentRed">
                                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3" />
                                </svg>
                            </div>
                            <h2 className="text-2xl font-bold text-white font-cinzel tracking-wider">
                                ⚖️ Tribunal de Acusação
                            </h2>
                            <p className="text-xs text-lightGray/60 font-roboto mt-1">
                                O destino de um suspeito está em jogo
                            </p>
                        </div>
                        
                        <div className="bg-charcoalBlack/60 border border-accentRed/20 rounded-lg p-5 mb-6 text-center">
                            <p className="text-sm font-roboto text-offWhite leading-relaxed">
                                <strong className="text-accentRed font-semibold">{accuserPlayerName}</strong> acusou formalmente <strong className="text-white font-semibold">{accusedPlayerName}</strong> de ser o Assassino!
                            </p>
                        </div>
                        
                        {playerStatus === "dead" ? (
                            <div className="text-center p-4 bg-gray-800/40 border border-gray-700/50 rounded-lg">
                                <p className="text-sm text-gray-400 font-roboto">
                                    👻 Você está morto e não pode votar nesta rodada.
                                </p>
                                <p className="text-xs text-gray-500 font-roboto mt-1">
                                    Aguardando apuração dos votos...
                                </p>
                            </div>
                        ) : hasVoted ? (
                            <div className="text-center p-4 bg-green-950/20 border border-green-500/30 rounded-lg">
                                <div className="w-8 h-8 rounded-full bg-green-500/20 border border-green-500/40 flex items-center justify-center mx-auto mb-2 text-green-400 text-sm">✓</div>
                                <p className="text-sm text-green-400 font-medium font-roboto">
                                    Seu voto foi registrado!
                                </p>
                                <p className="text-xs text-lightGray/50 font-roboto mt-1">
                                    Aguardando outros jogadores votarem...
                                </p>
                            </div>
                        ) : (
                            <div className="space-y-3">
                                <p className="text-xs text-lightGray font-roboto text-center mb-2">
                                    Qual é o seu veredicto?
                                </p>
                                <div className="flex gap-3">
                                    <button 
                                        onClick={() => handleVote("culpado")}
                                        className="flex-1 px-4 py-3 bg-gradient-to-r from-primaryRed to-accentRed hover:from-accentRed hover:to-lightRed text-white rounded-lg font-bold font-roboto transition-all duration-300 shadow-md shadow-primaryRed/20 hover:scale-[1.02] active:scale-[0.98]"
                                    >
                                        ☠️ CULPADO
                                    </button>
                                    <button 
                                        onClick={() => handleVote("inocente")}
                                        className="flex-1 px-4 py-3 bg-gray-800 hover:bg-gray-700 border border-gray-600/40 text-offWhite rounded-lg font-bold font-roboto transition-all duration-300 hover:scale-[1.02] active:scale-[0.98]"
                                    >
                                        🕊️ INOCENTE
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* ✅ OVERLAY DE FIM DE JOGO (ENDGAME SCREEN) */}
            {endgameData && (
                <div className="fixed inset-0 bg-black/95 z-50 flex items-center justify-center p-4">
                    <div className="max-w-md w-full bg-darkGray border-2 border-accentRed rounded-2xl p-8 shadow-2xl relative overflow-hidden text-center">
                        <div className="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-transparent via-accentRed to-transparent animate-pulse"></div>
                        
                        <div className="mb-6">
                            <div className="inline-flex items-center justify-center w-24 h-24 rounded-full bg-accentRed/10 border border-accentRed/30 mb-4 animate-bounce">
                                <span className="text-4xl">🏆</span>
                            </div>
                            <h2 className="text-3xl font-bold text-accentRed font-cinzel tracking-wider uppercase">
                                Fim de Partida
                            </h2>
                            <p className="text-sm text-lightGray/60 font-roboto mt-2">
                                A verdade foi revelada
                            </p>
                        </div>
                        
                        <div className="bg-charcoalBlack/70 border border-accentRed/30 rounded-xl p-6 mb-8">
                            <p className="text-xs text-accentRed uppercase tracking-widest font-bold mb-1">
                                Vencedores
                            </p>
                            <h3 className="text-2xl font-bold text-white font-cinzel mb-4">
                                {endgameData.winner_name || endgameData.winner}
                            </h3>
                            <div className="w-12 h-0.5 bg-accentRed/30 mx-auto mb-4"></div>
                            <p className="text-sm text-offWhite/80 font-roboto leading-relaxed italic">
                                "{endgameData.reason}"
                            </p>
                        </div>
                        
                        <button 
                            onClick={handleLeave}
                            className="w-full px-6 py-3.5 bg-gradient-to-r from-primaryRed to-accentRed hover:from-accentRed hover:to-lightRed text-white font-bold tracking-wider uppercase text-sm rounded-lg transition-all duration-300 shadow-lg shadow-primaryRed/30 hover:scale-[1.02] active:scale-[0.98]"
                        >
                            Voltar ao Lobby
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
