export default function AuthLayout({ children }) {
  return (
    <div
      className="min-h-screen flex items-center justify-center bg-cover bg-center px-4"
      style={{
        backgroundImage: `
          linear-gradient(
            rgba(0,0,0,0.75),
            rgba(0,0,0,0.85)
          ),
          url('/login-hero.png')
        `,
      }}
    >
      <div className="w-full max-w-md bg-black/70 backdrop-blur-xl p-10 rounded-3xl shadow-[0_20px_60px_rgba(0,0,0,0.85)] border border-red-900/40">
        {children}
      </div>
    </div>
  );
}
