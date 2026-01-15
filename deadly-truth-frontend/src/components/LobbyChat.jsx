export default function LobbyChat() {
  return (
    <>
      <h2 className="text-lg mb-3 tracking-widest text-gray-300">
        CHAT
      </h2>
      <div className="h-64 bg-neutral-800 rounded mb-3 p-2 text-sm overflow-y-auto">
        <p className="text-gray-500">Conectado à sala…</p>
      </div>
      <input
        placeholder="Digite algo..."
        className="w-full px-3 py-2 rounded bg-neutral-800 text-gray-200 focus:outline-none"
      />
    </>
  );
}
