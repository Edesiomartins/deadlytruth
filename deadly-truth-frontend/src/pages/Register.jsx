import { useState } from "react";

export default function Register() {
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");

  function handleSubmit(e) {
    e.preventDefault();
    if (password !== confirm) {
      alert("As senhas não conferem");
      return;
    }
    console.log("Registrando:", email);
  }

  return (
    <div className="min-h-screen bg-black relative overflow-hidden flex items-center justify-center">
      <div className="absolute inset-0 bg-gradient-to-br from-red-950/20 via-black to-purple-950/20"></div>
      
      <div className="absolute inset-0 opacity-20">
        <div
          className="absolute inset-0"
          style={{
            backgroundImage:
              "linear-gradient(rgba(220, 38, 38, 0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(220, 38, 38, 0.1) 1px, transparent 1px)",
            backgroundSize: "50px 50px",
          }}
        ></div>
      </div>

      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-red-600/10 rounded-full blur-3xl animate-pulse"></div>
      <div
        className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-600/10 rounded-full blur-3xl animate-pulse"
        style={{ animationDelay: "1s" }}
      ></div>

      <div className="relative z-10 w-full max-w-md px-6">
        <div className="backdrop-blur-xl bg-black/40 border border-red-900/30 rounded-2xl shadow-2xl shadow-red-900/20 p-8 relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-red-500 to-transparent"></div>
          
          <div className="absolute inset-0 opacity-5 pointer-events-none">
            <div className="h-full w-full bg-gradient-to-b from-transparent via-red-500/20 to-transparent animate-pulse"></div>
          </div>

          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-red-950/50 border border-red-500/30 mb-4">
              <svg className="w-8 h-8 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
            </div>
            <h2 className="text-sm text-red-400/80 tracking-[0.3em] uppercase font-light">
              Criar Identidade
            </h2>
            <div className="mt-2 h-px w-24 mx-auto bg-gradient-to-r from-transparent via-red-500/50 to-transparent"></div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="group">
              <label className="block text-xs tracking-widest text-red-400/70 mb-2 uppercase font-light">
                Email
              </label>
              <div className="relative">
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="usuario@email.com"
                  required
                  className="w-full px-4 py-3 bg-black/50 border border-red-900/40 rounded-lg text-gray-100 placeholder-gray-600 focus:outline-none focus:border-red-500/60 focus:ring-2 focus:ring-red-500/20 transition-all duration-300 group-hover:border-red-900/60"
                />
                <div className="absolute inset-0 rounded-lg bg-gradient-to-r from-red-500/0 via-red-500/5 to-red-500/0 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"></div>
              </div>
            </div>

            <div className="group">
              <label className="block text-xs tracking-widest text-red-400/70 mb-2 uppercase font-light">
                Senha
              </label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Crie uma senha"
                  required
                  className="w-full px-4 py-3 pr-12 bg-black/50 border border-red-900/40 rounded-lg text-gray-100 placeholder-gray-600 focus:outline-none focus:border-red-500/60 focus:ring-2 focus:ring-red-500/20 transition-all duration-300 group-hover:border-red-900/60"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-3 flex items-center text-red-400/50 hover:text-red-400 transition-colors"
                >
                  {showPassword ? (
                    <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M2.81 2.81a1 1 0 0 1 1.41 0l16.97 16.97a1 1 0 0 1-1.41 1.41l-2.4-2.4A10.94 10.94 0 0 1 12 20C7 20 2.73 16.89 1 12c.75-2.1 2.06-3.88 3.7-5.18L2.81 4.22a1 1 0 0 1 0-1.41ZM6.23 7.64a8.93 8.93 0 0 0-3.13 4.36C4.58 15.54 8 18 12 18a8.9 8.9 0 0 0 3.87-.87l-1.7-1.7a4 4 0 0 1-5.24-5.24l-1.7-1.7ZM12 8a4 4 0 0 1 4 4c0 .64-.15 1.24-.41 1.77l-1.62-1.62A2 2 0 0 0 12 10c-.25 0-.49.05-.71.13L9.46 8.3C10.06 8.11 10.87 8 12 8Zm0-4c5 0 9.27 3.11 11 8-.64 1.8-1.68 3.36-3 4.57l-1.42-1.42A8.93 8.93 0 0 0 20.9 12C19.42 8.46 16 6 12 6c-1.06 0-2.08.19-3.02.54L7.49 5.05C8.89 4.39 10.41 4 12 4Z" />
                    </svg>
                  ) : (
                    <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M12 5c5 0 9.27 3.11 11 8-1.73 4.89-6 8-11 8S2.73 16.89 1 12c1.73-4.89 6-8 11-8Zm0 2c-4 0-7.42 2.46-8.9 5 1.48 2.54 4.9 5 8.9 5s7.42-2.46 8.9-5C19.42 9.46 16 7 12 7Zm0 2a3 3 0 1 1 0 6 3 3 0 0 1 0-6Zm0 2a1 1 0 1 0 0 2 1 1 0 0 0 0-2Z" />
                    </svg>
                  )}
                </button>
                <div className="absolute inset-0 rounded-lg bg-gradient-to-r from-red-500/0 via-red-500/5 to-red-500/0 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"></div>
              </div>
            </div>

            <div className="group">
              <label className="block text-xs tracking-widest text-red-400/70 mb-2 uppercase font-light">
                Confirmar Senha
              </label>
              <div className="relative">
                <input
                  type={showConfirm ? "text" : "password"}
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  placeholder="Digite novamente"
                  required
                  className="w-full px-4 py-3 pr-12 bg-black/50 border border-red-900/40 rounded-lg text-gray-100 placeholder-gray-600 focus:outline-none focus:border-red-500/60 focus:ring-2 focus:ring-red-500/20 transition-all duration-300 group-hover:border-red-900/60"
                />
                <button
                  type="button"
                  onClick={() => setShowConfirm(!showConfirm)}
                  className="absolute inset-y-0 right-3 flex items-center text-red-400/50 hover:text-red-400 transition-colors"
                >
                  {showConfirm ? (
                    <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M2.81 2.81a1 1 0 0 1 1.41 0l16.97 16.97a1 1 0 0 1-1.41 1.41l-2.4-2.4A10.94 10.94 0 0 1 12 20C7 20 2.73 16.89 1 12c.75-2.1 2.06-3.88 3.7-5.18L2.81 4.22a1 1 0 0 1 0-1.41ZM6.23 7.64a8.93 8.93 0 0 0-3.13 4.36C4.58 15.54 8 18 12 18a8.9 8.9 0 0 0 3.87-.87l-1.7-1.7a4 4 0 0 1-5.24-5.24l-1.7-1.7ZM12 8a4 4 0 0 1 4 4c0 .64-.15 1.24-.41 1.77l-1.62-1.62A2 2 0 0 0 12 10c-.25 0-.49.05-.71.13L9.46 8.3C10.06 8.11 10.87 8 12 8Zm0-4c5 0 9.27 3.11 11 8-.64 1.8-1.68 3.36-3 4.57l-1.42-1.42A8.93 8.93 0 0 0 20.9 12C19.42 8.46 16 6 12 6c-1.06 0-2.08.19-3.02.54L7.49 5.05C8.89 4.39 10.41 4 12 4Z" />
                    </svg>
                  ) : (
                    <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M12 5c5 0 9.27 3.11 11 8-1.73 4.89-6 8-11 8S2.73 16.89 1 12c1.73-4.89 6-8 11-8Zm0 2c-4 0-7.42 2.46-8.9 5 1.48 2.54 4.9 5 8.9 5s7.42-2.46 8.9-5C19.42 9.46 16 7 12 7Zm0 2a3 3 0 1 1 0 6 3 3 0 0 1 0-6Zm0 2a1 1 0 1 0 0 2 1 1 0 0 0 0-2Z" />
                    </svg>
                  )}
                </button>
                <div className="absolute inset-0 rounded-lg bg-gradient-to-r from-red-500/0 via-red-500/5 to-red-500/0 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"></div>
              </div>
            </div>

            <button
              type="submit"
              className="relative w-full py-3 px-6 bg-gradient-to-r from-red-600 to-red-700 hover:from-red-500 hover:to-red-600 text-white font-medium tracking-wider uppercase text-sm rounded-lg transition-all duration-300 shadow-lg shadow-red-900/50 hover:shadow-red-900/70 hover:scale-[1.02] active:scale-[0.98] overflow-hidden group"
            >
              <span className="relative z-10">Criar Conta</span>
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent translate-x-[-200%] group-hover:translate-x-[200%] transition-transform duration-700"></div>
            </button>
          </form>

          <div className="mt-6 pt-6 border-t border-red-900/20">
            <p className="text-center text-sm text-gray-500">
              Já tem conta?{" "}
              <a href="/login" className="text-red-400 hover:text-red-300 transition-colors font-medium">
                Entrar
              </a>
            </p>
          </div>
        </div>

        <div className="absolute -bottom-20 left-1/2 -translate-x-1/2 w-3/4 h-20 bg-red-500/20 blur-3xl rounded-full"></div>
      </div>
    </div>
  );
}
import { useState } from "react";

export default function Register() {
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");

  function handleSubmit(e) {
    e.preventDefault();
    if (password !== confirm) {
      alert("As senhas não conferem");
      return;
    }
    console.log("Registrando:", email);
  }

  return (
    <div className="min-h-screen bg-black relative overflow-hidden flex items-center justify-center">
      <div className="absolute inset-0 bg-gradient-to-br from-red-950/20 via-black to-purple-950/20"></div>
      
      <div className="absolute inset-0 opacity-20">
        <div
          className="absolute inset-0"
          style={{
            backgroundImage:
              "linear-gradient(rgba(220, 38, 38, 0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(220, 38, 38, 0.1) 1px, transparent 1px)",
            backgroundSize: "50px 50px",
          }}
        ></div>
      </div>

      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-red-600/10 rounded-full blur-3xl animate-pulse"></div>
      <div
        className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-600/10 rounded-full blur-3xl animate-pulse"
        style={{ animationDelay: "1s" }}
      ></div>

      <div className="relative z-10 w-full max-w-md px-6">
        <div className="backdrop-blur-xl bg-black/40 border border-red-900/30 rounded-2xl shadow-2xl shadow-red-900/20 p-8 relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-red-500 to-transparent"></div>
          
          <div className="absolute inset-0 opacity-5 pointer-events-none">
            <div className="h-full w-full bg-gradient-to-b from-transparent via-red-500/20 to-transparent animate-pulse"></div>
          </div>

          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-red-950/50 border border-red-500/30 mb-4">
              <svg
                className="w-8 h-8 text-red-500"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
                />
              </svg>
            </div>
            <h2 className="text-sm text-red-400/80 tracking-[0.3em] uppercase font-light">
              Criar Identidade
            </h2>
            <div className="mt-2 h-px w-24 mx-auto bg-gradient-to-r from-transparent via-red-500/50 to-transparent"></div>
          </div>

          <div className="space-y-6">
            <div className="group">
              <label className="block text-xs tracking-widest text-red-400/70 mb-2 uppercase font-light">
                Email
              </label>
              <div className="relative">
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="usuario@email.com"
                  required
                  className="w-full px-4 py-3 bg-black/50 border border-red-900/40 rounded-lg text-gray-100 placeholder-gray-600 focus:outline-none focus:border-red-500/60 focus:ring-2 focus:ring-red-500/20 transition-all duration-300 group-hover:border-red-900/60"
                />
                <div className="absolute inset-0 rounded-lg bg-gradient-to-r from-red-500/0 via-red-500/5 to-red-500/0 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"></div>
              </div>
            </div>

            <div className="group">
              <label className="block text-xs tracking-widest text-red-400/70 mb-2 uppercase font-light">
                Senha
              </label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Crie uma senha"
                  required
                  className="w-full px-4 py-3 pr-12 bg-black/50 border border-red-900/40 rounded-lg text-gray-100 placeholder-gray-600 focus:outline-none focus:border-red-500/60 focus:ring-2 focus:ring-red-500/20 transition-all duration-300 group-hover:border-red-900/60"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-3 flex items-center text-red-400/50 hover:text-red-400 transition-colors"
                >
                  {showPassword ? (
                    <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M2.81 2.81a1 1 0 0 1 1.41 0l16.97 16.97a1 1 0 0 1-1.41 1.41l-2.4-2.4A10.94 10.94 0 0 1 12 20C7 20 2.73 16.89 1 12c.75-2.1 2.06-3.88 3.7-5.18L2.81 4.22a1 1 0 0 1 0-1.41ZM6.23 7.64a8.93 8.93 0 0 0-3.13 4.36C4.58 15.54 8 18 12 18a8.9 8.9 0 0 0 3.87-.87l-1.7-1.7a4 4 0 0 1-5.24-5.24l-1.7-1.7ZM12 8a4 4 0 0 1 4 4c0 .64-.15 1.24-.41 1.77l-1.62-1.62A2 2 0 0 0 12 10c-.25 0-.49.05-.71.13L9.46 8.3C10.06 8.11 10.87 8 12 8Zm0-4c5 0 9.27 3.11 11 8-.64 1.8-1.68 3.36-3 4.57l-1.42-1.42A8.93 8.93 0 0 0 20.9 12C19.42 8.46 16 6 12 6c-1.06 0-2.08.19-3.02.54L7.49 5.05C8.89 4.39 10.41 4 12 4Z" />
                    </svg>
                  ) : (
                    <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M12 5c5 0 9.27 3.11 11 8-1.73 4.89-6 8-11 8S2.73 16.89 1 12c1.73-4.89 6-8 11-8Zm0 2c-4 0-7.42 2.46-8.9 5 1.48 2.54 4.9 5 8.9 5s7.42-2.46 8.9-5C19.42 9.46 16 7 12 7Zm0 2a3 3 0 1 1 0 6 3 3 0 0 1 0-6Zm0 2a1 1 0 1 0 0 2 1 1 0 0 0 0-2Z" />
                    </svg>
                  )}
                </button>
                <div className="absolute inset-0 rounded-lg bg-gradient-to-r from-red-500/0 via-red-500/5 to-red-500/0 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"></div>
              </div>
            </div>

            <div className="group">
              <label className="block text-xs tracking-widest text-red-400/70 mb-2 uppercase font-light">
                Confirmar Senha
              </label>
              <div className="relative">
                <input
                  type={showConfirm ? "text" : "password"}
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  placeholder="Digite novamente"
                  required
                  className="w-full px-4 py-3 pr-12 bg-black/50 border border-red-900/40 rounded-lg text-gray-100 placeholder-gray-600 focus:outline-none focus:border-red-500/60 focus:ring-2 focus:ring-red-500/20 transition-all duration-300 group-hover:border-red-900/60"
                />
                <button
                  type="button"
                  onClick={() => setShowConfirm(!showConfirm)}
                  className="absolute inset-y-0 right-3 flex items-center text-red-400/50 hover:text-red-400 transition-colors"
                >
                  {showConfirm ? (
                    <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M2.81 2.81a1 1 0 0 1 1.41 0l16.97 16.97a1 1 0 0 1-1.41 1.41l-2.4-2.4A10.94 10.94 0 0 1 12 20C7 20 2.73 16.89 1 12c.75-2.1 2.06-3.88 3.7-5.18L2.81 4.22a1 1 0 0 1 0-1.41ZM6.23 7.64a8.93 8.93 0 0 0-3.13 4.36C4.58 15.54 8 18 12 18a8.9 8.9 0 0 0 3.87-.87l-1.7-1.7a4 4 0 0 1-5.24-5.24l-1.7-1.7ZM12 8a4 0 0 1 4 4c0 .64-.15 1.24-.41 1.77l-1.62-1.62A2 2 0 0 0 12 10c-.25 0-.49.05-.71.13L9.46 8.3C10.06 8.11 10.87 8 12 8Zm0-4c5 0 9.27 3.11 11 8-.64 1.8-1.68 3.36-3 4.57l-1.42-1.42A8.93 8.93 0 0 0 20.9 12C19.42 8.46 16 6 12 6c-1.06 0-2.08.19-3.02.54L7.49 5.05C8.89 4.39 10.41 4 12 4Z" />
                    </svg>
                  ) : (
                    <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M12 5c5 0 9.27 3.11 11 8-1.73 4.89-6 8-11 8S2.73 16.89 1 12c1.73-4.89 6-8 11-8Zm0 2c-4 0-7.42 2.46-8.9 5 1.48 2.54 4.9 5 8.9 5s7.42-2.46 8.9-5C19.42 9.46 16 7 12 7Zm0 2a3 3 0 1 1 0 6 3 3 0 0 1 0-6Zm0 2a1 1 0 1 0 0 2 1 1 0 0 0 0-2Z" />
                    </svg>
                  )}
                </button>
                <div className="absolute inset-0 rounded-lg bg-gradient-to-r from-red-500/0 via-red-500/5 to-red-500/0 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"></div>
              </div>
            </div>

            <button
              onClick={handleSubmit}
              className="relative w-full py-3 px-6 bg-gradient-to-r from-red-600 to-red-700 hover:from-red-500 hover:to-red-600 text-white font-medium tracking-wider uppercase text-sm rounded-lg transition-all duration-300 shadow-lg shadow-red-900/50 hover:shadow-red-900/70 hover:scale-[1.02] active:scale-[0.98] overflow-hidden group"
            >
              <span className="relative z-10">Criar Conta</span>
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent translate-x-[-200%] group-hover:translate-x-[200%] transition-transform duration-700"></div>
            </button>
          </div>

          <div className="mt-6 pt-6 border-t border-red-900/20">
            <p className="text-center text-sm text-gray-500">
              Já tem conta?{" "}
              <a href="/login" className="text-red-400 hover:text-red-300 transition-colors font-medium">
                Entrar
              </a>
            </p>
          </div>
        </div>

        <div className="absolute -bottom-20 left-1/2 -translate-x-1/2 w-3/4 h-20 bg-red-500/20 blur-3xl rounded-full"></div>
      </div>
    </div>
  );
}
