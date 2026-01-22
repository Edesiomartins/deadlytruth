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
    
    // ✅ CONECTAR AO WEBSOCKET
    useEffect(() => {
        const token = localStorage.getItem("jwt_token") || localStorage.getItem("token");
        const playerName = localStorage.getItem("playerName");
        
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
                    player: message.player || message.player_id || "Jogador",
                    message: message.message || message.content || "",
                    dead: message.dead || false
                }]);
                break;
            
            case "pista":
                console.log("🔍 Pista:", message.text);
                setPistas(prev => [...prev, message.text]);
                setMessages(prev => [...prev, {
                    player: "🧠 MESTRE",
                    message: message.text,
                    dead: false
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
                setSystemMessage("🔪 VOCÊ É O ASSASSINO!");
                break;
            
            case "players_update":
            case "jogadores":
                console.log("👥 Jogadores atualizados:", message.players);
                if (Array.isArray(message.players)) {
                    setPlayers(message.players);
                }
                break;
            
            case "player_death":
                const victimName = message.victim || message.player_name || "Jogador";
                setSystemMessage(`💀 ${victimName} foi encontrado morto!`);
                if (message.clue) {
                    setPistas(prev => [...prev, message.clue]);
                }
                // Atualiza lista de jogadores
                setPlayers(prev => prev.map(p => 
                    (p.name === victimName || p.id === victimName || p.nickname === victimName) 
                        ? { ...p, status: "dead" } 
                        : p
                ));
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
    
    // ✅ RENDERIZAR
    return (
        <div className="game-container" style={{ minHeight: "100vh", backgroundColor: "#1a1a1a", color: "#fff", padding: "20px" }}>
            <div className="game-header" style={{ marginBottom: "20px", borderBottom: "2px solid #dc143c", paddingBottom: "10px" }}>
                <h1 style={{ fontSize: "24px", fontWeight: "bold", marginBottom: "10px" }}>🎮 Deadly Truth</h1>
                <p style={{ fontSize: "14px", color: "#ccc" }}>Sala: {roomId}</p>
                <p style={{ fontSize: "12px", color: "#888" }}>
                    Seu ID: {myPlayerId || "Carregando..."} | Seu turno? {isMyTurn ? "✅ SIM" : "❌ NÃO"}
                </p>
            </div>
            
            <div className="game-content" style={{ display: "grid", gridTemplateColumns: "300px 1fr 250px", gap: "20px" }}>
                {/* CASO E PISTAS */}
                <div className="left-panel" style={{ backgroundColor: "#2a2a2a", padding: "15px", borderRadius: "8px", maxHeight: "80vh", overflowY: "auto" }}>
                    <h2 style={{ fontSize: "18px", fontWeight: "bold", marginBottom: "15px", color: "#dc143c" }}>📋 Caso</h2>
                    {caso ? (
                        <div className="caso-content" style={{ marginBottom: "20px" }}>
                            <p><strong>Cenário:</strong> {caso.cenario || "N/A"}</p>
                            <p><strong>Descrição:</strong> {caso.descricao || "N/A"}</p>
                            <p><strong>Local:</strong> {caso.local_corpo || "N/A"}</p>
                            <p><strong>Arma:</strong> {caso.arma_crime || "N/A"}</p>
                            {caso.historia && <p><strong>História:</strong> {caso.historia}</p>}
                            {caso.suspeitos && caso.suspeitos.length > 0 && (
                                <p><strong>Suspeitos:</strong> {caso.suspeitos.join(", ")}</p>
                            )}
                        </div>
                    ) : (
                        <p style={{ color: "#888" }}>Aguardando caso...</p>
                    )}
                    
                    <h3 style={{ fontSize: "16px", fontWeight: "bold", marginTop: "20px", marginBottom: "10px", color: "#dc143c" }}>🔍 Pistas</h3>
                    <div className="pistas-list" style={{ maxHeight: "300px", overflowY: "auto" }}>
                        {pistas.length > 0 ? (
                            pistas.map((pista, idx) => (
                                <div key={idx} className="pista-item" style={{ padding: "8px", marginBottom: "8px", backgroundColor: "#333", borderRadius: "4px", fontSize: "12px" }}>
                                    {pista}
                                </div>
                            ))
                        ) : (
                            <p style={{ color: "#888", fontSize: "12px" }}>Nenhuma pista ainda...</p>
                        )}
                    </div>
                </div>
                
                {/* CHAT */}
                <div className="middle-panel" style={{ display: "flex", flexDirection: "column", backgroundColor: "#2a2a2a", padding: "15px", borderRadius: "8px", maxHeight: "80vh" }}>
                    <h2 style={{ fontSize: "18px", fontWeight: "bold", marginBottom: "15px", color: "#dc143c" }}>💬 Chat</h2>
                    <div className="messages-container" style={{ flex: 1, overflowY: "auto", marginBottom: "15px", padding: "10px", backgroundColor: "#1a1a1a", borderRadius: "4px", minHeight: "400px" }}>
                        {messages.length > 0 ? (
                            messages.map((msg, idx) => (
                                <div key={idx} className={`message ${msg.dead ? "dead" : ""}`} style={{ 
                                    marginBottom: "10px", 
                                    padding: "8px", 
                                    backgroundColor: msg.dead ? "#333" : "#2a2a2a",
                                    borderRadius: "4px",
                                    opacity: msg.dead ? 0.6 : 1
                                }}>
                                    <strong style={{ color: msg.dead ? "#888" : "#dc143c" }}>{msg.player}:</strong> {msg.message}
                                </div>
                            ))
                        ) : (
                            <p style={{ color: "#888", textAlign: "center", marginTop: "50px" }}>Nenhuma mensagem ainda...</p>
                        )}
                    </div>
                    
                    <div className="input-section" style={{ display: "flex", gap: "10px" }}>
                        {isMyTurn ? (
                            <>
                                <input
                                    type="text"
                                    value={messageInput}
                                    onChange={(e) => setMessageInput(e.target.value)}
                                    onKeyPress={(e) => e.key === "Enter" && handleSendMessage()}
                                    placeholder="Digite sua mensagem..."
                                    disabled={false}
                                    style={{ 
                                        flex: 1, 
                                        padding: "10px", 
                                        backgroundColor: "#1a1a1a", 
                                        border: "1px solid #dc143c", 
                                        borderRadius: "4px", 
                                        color: "#fff",
                                        opacity: 1, 
                                        cursor: "text" 
                                    }}
                                />
                                <button 
                                    onClick={handleSendMessage}
                                    style={{ 
                                        padding: "10px 20px", 
                                        backgroundColor: "#dc143c", 
                                        color: "#fff", 
                                        border: "none", 
                                        borderRadius: "4px", 
                                        cursor: "pointer",
                                        fontWeight: "bold"
                                    }}
                                >
                                    Enviar
                                </button>
                            </>
                        ) : (
                            <>
                                <input
                                    type="text"
                                    placeholder="Aguarde seu turno..."
                                    disabled={true}
                                    style={{ 
                                        flex: 1, 
                                        padding: "10px", 
                                        backgroundColor: "#1a1a1a", 
                                        border: "1px solid #555", 
                                        borderRadius: "4px", 
                                        color: "#888",
                                        opacity: 0.5, 
                                        cursor: "not-allowed" 
                                    }}
                                />
                                <button 
                                    disabled
                                    style={{ 
                                        padding: "10px 20px", 
                                        backgroundColor: "#555", 
                                        color: "#888", 
                                        border: "none", 
                                        borderRadius: "4px", 
                                        cursor: "not-allowed"
                                    }}
                                >
                                    Aguarde...
                                </button>
                            </>
                        )}
                    </div>
                </div>
                
                {/* JOGADORES */}
                <div className="right-panel" style={{ backgroundColor: "#2a2a2a", padding: "15px", borderRadius: "8px", maxHeight: "80vh", overflowY: "auto" }}>
                    <h2 style={{ fontSize: "18px", fontWeight: "bold", marginBottom: "15px", color: "#dc143c" }}>👥 Jogadores</h2>
                    <div className="players-list">
                        {players.length > 0 ? (
                            players.map((player) => (
                                <div 
                                    key={player.id || player.name} 
                                    className={`player-item ${player.id === currentTurnPlayerId || player.name === currentTurnPlayerId ? "current-turn" : ""}`}
                                    style={{ 
                                        padding: "10px", 
                                        marginBottom: "8px", 
                                        backgroundColor: (player.id === currentTurnPlayerId || player.name === currentTurnPlayerId) ? "#dc143c20" : "#333", 
                                        borderRadius: "4px",
                                        border: (player.id === currentTurnPlayerId || player.name === currentTurnPlayerId) ? "2px solid #dc143c" : "1px solid #555"
                                    }}
                                >
                                    <span style={{ color: player.status === "dead" ? "#888" : "#fff" }}>
                                        {player.nickname || player.name || player.id}
                                    </span>
                                    {(player.id === currentTurnPlayerId || player.name === currentTurnPlayerId) && <span style={{ marginLeft: "5px" }}>🎯</span>}
                                    {player.is_bot && <span style={{ marginLeft: "5px" }}>🤖</span>}
                                    {player.status === "dead" && <span style={{ marginLeft: "5px" }}>💀</span>}
                                </div>
                            ))
                        ) : (
                            <p style={{ color: "#888", fontSize: "12px" }}>Nenhum jogador ainda...</p>
                        )}
                    </div>
                </div>
            </div>
            
            {/* MENSAGEM DO SISTEMA */}
            {systemMessage && (
                <div className="system-message" style={{ 
                    position: "fixed", 
                    bottom: "20px", 
                    left: "50%", 
                    transform: "translateX(-50%)", 
                    padding: "15px 30px", 
                    backgroundColor: "#dc143c", 
                    color: "#fff", 
                    borderRadius: "8px",
                    zIndex: 1000,
                    boxShadow: "0 4px 6px rgba(0,0,0,0.3)"
                }}>
                    {systemMessage}
                </div>
            )}
        </div>
    );
}
