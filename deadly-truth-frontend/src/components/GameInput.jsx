export default function GameInput(props) {
  const { className = "", ...rest } = props;
  return (
    <input
      {...rest}
      className={`
        w-full
        px-5 py-4
        rounded-xl
        bg-neutral-800
        text-gray-100
        placeholder-gray-400
        border border-neutral-700
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
