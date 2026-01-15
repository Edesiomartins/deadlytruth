export default function GameInput(props) {
  return (
    <input
      {...props}
      className="
        w-full
        px-4 py-3
        rounded-lg
        bg-neutral-800
        text-gray-100
        placeholder-gray-500
        border border-neutral-700
        focus:outline-none
        focus:ring-2
        focus:ring-red-700
      "
    />
  );
}
