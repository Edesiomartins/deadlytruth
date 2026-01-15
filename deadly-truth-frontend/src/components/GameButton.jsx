export default function GameButton({ children, ...props }) {
  return (
    <button
      {...props}
      className="
        w-full
        py-4
        rounded-xl
        bg-red-700
        hover:bg-red-800
        text-white
        font-semibold
        tracking-widest
        transition
        disabled:opacity-60
      "
    >
      {children}
    </button>
  );
}
