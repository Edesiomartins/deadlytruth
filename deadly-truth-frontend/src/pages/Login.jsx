import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import AuthLayout from "../components/AuthLayout";
import GameInput from "../components/GameInput";
import GameButton from "../components/GameButton";

export default function Login() {
  const { login, loading, error } = useAuth();

  function handleSubmit(e) {
    e.preventDefault();
    const form = new FormData(e.target);
    login(form.get("email"), form.get("password"));
  }

  return (
    <AuthLayout>
      <h2 className="text-lg text-gray-300 mb-6 text-center">
        Acesso seguro ao jogo
      </h2>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm text-gray-400 mb-1">
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
          <label className="block text-sm text-gray-400 mb-1">
            Senha
          </label>
          <GameInput
            type="password"
            name="password"
            placeholder="Digite sua senha"
            required
          />
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
