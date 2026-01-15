export default function LobbyCenter({ room }) {
  return (
    <div>
      <h1 className="text-2xl tracking-widest mb-2">
        {room}
      </h1>
      <p className="text-sm text-gray-500">
        Aguarde. A verdade sempre aparece.
      </p>
    </div>
  );
}
