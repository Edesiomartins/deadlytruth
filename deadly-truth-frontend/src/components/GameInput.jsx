export default function GameInput(props) {
  const { className = "", ...rest } = props;
  return (
    <input
      {...rest}
      className={`
        w-full
        px-4 py-3
        rounded-lg
        bg-neutral-200/90
        text-black
        placeholder-gray-400
        border border-neutral-600
        focus:outline-none
        focus:ring-2
        focus:ring-red-700
        focus:border-red-700
        transition
        ${className}
      `}
    />
  );
}
