import AuthLayout from "../components/AuthLayout";
import GameInput from "../components/GameInput";
import GameButton from "../components/GameButton";
import { useAuth } from "../context/AuthContext";

export default function Register() {
  const { register } = useAuth();

  function handleSubmit(e) {
    e.preventDefault();
    const form = new FormData(e.target);
    register(form.get("email"), form.get("password"));
  }

  return (
    <AuthLayout>
      <h2 className="text-lg text-gray-300 mb-6 text-center">
        Crie sua conta para entrar
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
            placeholder="Crie uma senha"
            required
          />
        </div>

        <div>
          <label className="block text-sm text-gray-400 mb-1">
            Confirmar senha
          </label>
          <GameInput
            type="password"
            name="confirm"
            placeholder="Digite novamente"
            required
          />
        </div>

        <GameButton>Criar Conta</GameButton>
      </form>

      <p className="mt-4 text-center text-sm text-gray-400">
        Já tem conta?{" "}
        <a href="/login" className="text-red-500 hover:underline">
          Entrar
        </a>
      </p>
    </AuthLayout>
  );
}
