import { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import AuthLayout from "../components/AuthLayout";
import GameInput from "../components/GameInput";
import GameButton from "../components/GameButton";

export default function Login() {
  const { login, loading, error } = useAuth();
  const [showPassword, setShowPassword] = useState(false);

  function handleSubmit(e) {
    e.preventDefault();
    const form = new FormData(e.target);
    login(form.get("email"), form.get("password"));
  }

  return (
    <AuthLayout>
      <h2 className="text-sm text-gray-400 mb-8 text-center tracking-widest uppercase">
        Acesso restrito
      </h2>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <label className="block text-sm font-medium tracking-wide text-gray-300 mb-2">
            Email
          </label>
          <GameInput
            type="email"
            name="email"
            placeholder="ex: usuario@email.com"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium tracking-wide text-gray-300 mb-2">
            Senha
          </label>
          <div className="relative">
            <GameInput
              type={showPassword ? "text" : "password"}
              name="password"
              placeholder="Digite sua senha"
              className="pr-10"
              required
            />
            <button
              type="button"
              onClick={() => setShowPassword((prev) => !prev)}
              className="absolute inset-y-0 right-3 flex items-center text-gray-600 hover:text-gray-800"
              aria-label={showPassword ? "Ocultar senha" : "Mostrar senha"}
            >
              {showPassword ? (
                <svg viewBox="0 0 24 24" className="h-5 w-5 fill-current">
                  <path d="M2.81 2.81a1 1 0 0 1 1.41 0l16.97 16.97a1 1 0 0 1-1.41 1.41l-2.4-2.4A10.94 10.94 0 0 1 12 20C7 20 2.73 16.89 1 12c.75-2.1 2.06-3.88 3.7-5.18L2.81 4.22a1 1 0 0 1 0-1.41ZM6.23 7.64a8.93 8.93 0 0 0-3.13 4.36C4.58 15.54 8 18 12 18a8.9 8.9 0 0 0 3.87-.87l-1.7-1.7a4 4 0 0 1-5.24-5.24l-1.7-1.7ZM12 8a4 4 0 0 1 4 4c0 .64-.15 1.24-.41 1.77l-1.62-1.62A2 2 0 0 0 12 10c-.25 0-.49.05-.71.13L9.46 8.3C10.06 8.11 10.87 8 12 8Zm0-4c5 0 9.27 3.11 11 8-.64 1.8-1.68 3.36-3 4.57l-1.42-1.42A8.93 8.93 0 0 0 20.9 12C19.42 8.46 16 6 12 6c-1.06 0-2.08.19-3.02.54L7.49 5.05C8.89 4.39 10.41 4 12 4Z" />
                </svg>
              ) : (
                <svg viewBox="0 0 24 24" className="h-5 w-5 fill-current">
                  <path d="M12 5c5 0 9.27 3.11 11 8-1.73 4.89-6 8-11 8S2.73 16.89 1 12c1.73-4.89 6-8 11-8Zm0 2c-4 0-7.42 2.46-8.9 5 1.48 2.54 4.9 5 8.9 5s7.42-2.46 8.9-5C19.42 9.46 16 7 12 7Zm0 2a3 3 0 1 1 0 6 3 3 0 0 1 0-6Zm0 2a1 1 0 1 0 0 2 1 1 0 0 0 0-2Z" />
                </svg>
              )}
            </button>
          </div>
        </div>

        {error && <p className="text-red-400 text-sm text-center">{error}</p>}

        <GameButton disabled={loading}>
          {loading ? "Entrando..." : "Entrar"}
        </GameButton>
      </form>

      <p className="mt-4 text-center text-sm text-gray-400">
        Não tem conta?{" "}
        <Link to="/register" className="text-red-500 hover:underline">
          Criar conta
        </Link>
      </p>
    </AuthLayout>
  );
}
