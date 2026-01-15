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
      <div className="w-full max-w-md bg-neutral-900/95 backdrop-blur-xl p-10 rounded-2xl shadow-[0_0_40px_rgba(0,0,0,0.8)] border border-neutral-700">
        <h1 className="text-center text-3xl font-bold tracking-widest text-gray-100 mb-6">
          DEADLY TRUTH
        </h1>
        {children}
      </div>
    </div>
  );
}
