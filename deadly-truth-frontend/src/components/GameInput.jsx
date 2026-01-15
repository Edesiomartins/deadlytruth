export default function GameInput(props) {
  return (
    <input
      {...props}
      className="
        w-full
        px-5 py-4
        rounded-xl
        bg-black/60
        text-red-500
        placeholder-red-400/70
        border border-red-900/50
        focus:outline-none
        focus:ring-2
        focus:ring-red-700
        focus:border-red-700
        transition
      "
    />
  );
}
