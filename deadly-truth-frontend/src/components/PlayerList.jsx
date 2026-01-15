export default function PlayerList({ players = [] }) {
  return (
    <>
      <h2 className="text-lg mb-3 tracking-widest text-gray-300">
        JOGADORES
      </h2>
      <ul className="space-y-2">
        {players.map((p, i) => (
          <li
            key={i}
            className="px-3 py-2 rounded bg-neutral-800 text-sm"
          >
            {p}
          </li>
        ))}
      </ul>
    </>
  );
}
