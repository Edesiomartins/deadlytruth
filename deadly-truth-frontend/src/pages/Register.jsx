import { useState } from "react";
import AuthLayout from "../components/AuthLayout";
import GameInput from "../components/GameInput";
import GameButton from "../components/GameButton";
import { useAuth } from "../context/AuthContext";
import suspenseBg from "../assets/images/login-hero.png.png";

export default function Register() {
  const { register, loading, error } = useAuth();
  const [localError, setLocalError] = useState(null);

  function handleSubmit(e) {
    e.preventDefault();
    setLocalError(null);

    const form = new FormData(e.target);
    const email = form.get("email");
    const password = form.get("password");
    const confirmPassword = form.get("confirmPassword");

    if (password.length < 6) {
      setLocalError("A senha deve ter pelo menos 6 caracteres.");
      return;
    }

    if (password !== confirmPassword) {
      setLocalError("As senhas não coincidem.");
      return;
    }

    register(email, password);
  }

  return (
    <div className="min-h-screen relative flex items-center justify-center bg-black px-4">
      <div
        className="absolute inset-0 bg-cover bg-center"
        style={{ backgroundImage: `url(${suspenseBg})` }}
      />
      <div className="absolute inset-0 bg-black/70" />
      <div className="relative z-10 w-full max-w-md bg-neutral-900/90 backdrop-blur p-8 rounded-2xl shadow-2xl border border-neutral-800">
        <h1 className="text-center text-3xl font-bold tracking-widest text-gray-100 mb-2">
          DEADLY TRUTH
        </h1>
        <p className="text-center text-sm text-gray-400 mb-6">
          Crie sua conta para entrar
        </p>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <GameInput type="email" name="email" placeholder="Email" required />
          <GameInput type="password" name="password" placeholder="Senha" required />
          <GameInput
            type="password"
            name="confirmPassword"
            placeholder="Confirmar senha"
            required
          />
          {(localError || error) && (
            <p className="text-red-400 text-sm text-center">
              {localError || error}
            </p>
          )}
          <GameButton disabled={loading}>
            {loading ? "Criando..." : "Criar Conta"}
          </GameButton>
        </form>
      </div>
    </div>
  );
}
