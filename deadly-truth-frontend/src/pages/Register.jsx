import { useState } from "react";
import AuthLayout from "../components/AuthLayout";
import GameInput from "../components/GameInput";
import GameButton from "../components/GameButton";
import { useAuth } from "../context/AuthContext";

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
    <AuthLayout>
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
    </AuthLayout>
  );
}
