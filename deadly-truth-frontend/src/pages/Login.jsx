import AuthLayout from "../components/AuthLayout";
import GameInput from "../components/GameInput";
import GameButton from "../components/GameButton";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { login, loading, error } = useAuth();

  function handleSubmit(e) {
    e.preventDefault();
    const form = new FormData(e.target);
    login(form.get("email"), form.get("password"));
  }

  return (
    <AuthLayout>
      <form onSubmit={handleSubmit}>
        <GameInput type="email" name="email" placeholder="Email" required />
        <GameInput type="password" name="password" placeholder="Senha" required />
        {error && <p className="text-red-400 text-sm text-center">{error}</p>}
        <GameButton disabled={loading}>
          {loading ? "Entrando..." : "Entrar"}
        </GameButton>
      </form>
    </AuthLayout>
  );
}
