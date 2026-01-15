export default function AuthLayout({ children }) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-black via-neutral-900 to-black">
      <div className="w-full max-w-md bg-neutral-900/90 backdrop-blur rounded-2xl p-8 shadow-2xl border border-neutral-800">
        <h1 className="text-center text-3xl font-bold tracking-widest text-gray-100 mb-6">
          DEADLY TRUTH
        </h1>
        {children}
      </div>
    </div>
  );
}
