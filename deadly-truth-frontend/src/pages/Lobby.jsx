import LobbyLayout from "../components/LobbyLayout";
import PlayerList from "../components/PlayerList";
import LobbyCenter from "../components/LobbyCenter";
import LobbyChat from "../components/LobbyChat";

export default function Lobby() {
  const players = ["Jogador 1", "Jogador 2"];

  return (
    <LobbyLayout
      left={<PlayerList players={players} />}
      center={<LobbyCenter room="Sala Geral" />}
      right={<LobbyChat />}
    />
  );
}
