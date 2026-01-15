export default function GameButton({ children, ...props }) {
  return (
    <button
      {...props}
      className="w-full mt-4 py-3 rounded-lg bg-red-700 hover:bg-red-800 transition text-white font-semibold tracking-wide"
    >
      {children}
    </button>
  );
}
