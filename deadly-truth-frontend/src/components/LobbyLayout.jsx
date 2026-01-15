export default function LobbyLayout({ left, center, right }) {
  return (
    <div className="min-h-screen bg-black text-gray-200 grid grid-cols-1 md:grid-cols-3 gap-4 p-4">
      <div className="bg-neutral-900 rounded-xl p-4 border border-neutral-800">
        {left}
      </div>

      <div className="bg-neutral-900 rounded-xl p-4 border border-neutral-800 flex items-center justify-center text-center text-gray-400">
        {center}
      </div>

      <div className="bg-neutral-900 rounded-xl p-4 border border-neutral-800">
        {right}
      </div>
    </div>
  );
}
