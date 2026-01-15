export default function AuthLayout({ children }) {
  return (
    <div
      className="min-h-screen flex items-center justify-center bg-cover bg-center px-4"
      style={{
        backgroundImage: `
          linear-gradient(rgba(0,0,0,0.75), rgba(0,0,0,0.85)),
          url('/bg-login.jpg')
        `,
      }}
    >
      <div className="w-full max-w-md bg-neutral-900/95 backdrop-blur-xl p-10 rounded-3xl shadow-[0_20px_60px_rgba(0,0,0,0.8)] border border-neutral-700">
        <div className="mb-8 text-center">
          <h1 className="text-4xl font-extrabold tracking-[0.25em] text-white">
            DEADLY
          </h1>
          <h2 className="text-2xl font-light tracking-[0.3em] text-red-600">
            TRUTH
          </h2>
          <p className="mt-3 text-sm text-gray-400">
            Nada fica escondido para sempre
          </p>
        </div>

        {children}
      </div>
    </div>
  );
}
