import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { login, loading, error } = useAuth();

  function handleSubmit(e) {
    e.preventDefault();
    const form = new FormData(e.target);
    login(form.get("email"), form.get("password"));
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-black px-4">
      <div className="w-full max-w-md bg-neutral-900 p-8 rounded-2xl shadow-2xl border border-neutral-800">
        <h1 className="text-center text-3xl font-bold tracking-widest text-gray-100 mb-2">
          DEADLY TRUTH
        </h1>
        <p className="text-center text-sm text-gray-400 mb-6">
          Acesso seguro ao jogo
        </p>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <input
            type="email"
            name="email"
            placeholder="Email"
            className="block w-full px-4 py-3 rounded-lg bg-neutral-800 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-red-700"
            style={{ display: "block" }}
            required
          />
          <input
            type="password"
            name="password"
            placeholder="Senha"
            className="block w-full px-4 py-3 rounded-lg bg-neutral-800 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-red-700"
            style={{ display: "block" }}
            required
          />
          {error && <p className="text-red-400 text-sm text-center">{error}</p>}
          <button
            className="w-full py-3 rounded-lg bg-red-700 text-white font-semibold tracking-wide hover:bg-red-800 transition disabled:opacity-60"
            disabled={loading}
          >
            {loading ? "Entrando..." : "Entrar"}
          </button>
        </form>
        <p className="mt-4 text-center text-sm text-gray-400">
          Não tem conta?{" "}
          <Link to="/register" className="text-red-500 hover:underline">
            Criar conta
          </Link>
        </p>
      </div>
    </div>
  );
}
