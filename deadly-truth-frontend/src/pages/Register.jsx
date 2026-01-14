import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useAuth } from '../context/AuthContext';
import { Ghost } from 'lucide-react';

const Register = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [localError, setLocalError] = useState(null);
  const { register, loading, error: authError } = useAuth();

  const validateForm = () => {
    setLocalError(null);
    if (!email.includes('@') || !email.includes('.')) {
      setLocalError('Por favor, insira um email válido.');
      return false;
    }
    if (password.length < 6) {
      setLocalError('A senha deve ter pelo menos 6 caracteres.');
      return false;
    }
    if (password !== confirmPassword) {
      setLocalError('As senhas não coincidem.');
      return false;
    }
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (validateForm()) {
      await register(email, password);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: -50 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="min-h-screen flex items-center justify-center bg-charcoalBlack text-offWhite p-4"
      style={{
        background: 'linear-gradient(135deg, #0F0F0F 0%, #1A1A1A 100%)',
      }}
    >
      <motion.div
        initial={{ scale: 0.8 }}
        animate={{ scale: 1 }}
        transition={{ duration: 0.5, delay: 0.2 }}
        className="bg-darkGray p-8 rounded-2xl shadow-2xl w-full max-w-md border-2 border-primaryRed relative overflow-hidden"
        style={{
          background: 'linear-gradient(135deg, #1A1A1A 0%, #2A2A2A 100%)',
        }}
      >
        {/* Decoração de fundo */}
        <div className="absolute inset-0 opacity-10 pointer-events-none">
          <Ghost size={200} className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-primaryRed" />
        </div>

        <div className="relative z-10">
          <h2 className="text-4xl font-black text-center mb-2" style={{
            background: 'linear-gradient(135deg, #DC143C 0%, #8B0000 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}>
            DEADLY TRUTH
          </h2>
          <p className="text-center text-sm text-lightGray mb-8 uppercase tracking-wider">Registrar</p>
          
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label htmlFor="email" className="block text-offWhite text-sm font-bold mb-2">
                Email
              </label>
              <input
                type="email"
                id="email"
                className="w-full py-3 px-4 rounded-xl border-2 transition-all duration-300 focus:outline-none focus:ring-2 focus:ring-primaryRed bg-charcoalBlack text-offWhite"
                style={{
                  borderColor: '#2A2A2A',
                }}
                placeholder="seu@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <div>
              <label htmlFor="password" className="block text-offWhite text-sm font-bold mb-2">
                Senha
              </label>
              <input
                type="password"
                id="password"
                className="w-full py-3 px-4 rounded-xl border-2 transition-all duration-300 focus:outline-none focus:ring-2 focus:ring-primaryRed bg-charcoalBlack text-offWhite"
                style={{
                  borderColor: '#2A2A2A',
                }}
                placeholder="********"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            <div>
              <label htmlFor="confirmPassword" className="block text-offWhite text-sm font-bold mb-2">
                Confirmar Senha
              </label>
              <input
                type="password"
                id="confirmPassword"
                className="w-full py-3 px-4 rounded-xl border-2 transition-all duration-300 focus:outline-none focus:ring-2 focus:ring-primaryRed bg-charcoalBlack text-offWhite"
                style={{
                  borderColor: '#2A2A2A',
                }}
                placeholder="********"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
              />
            </div>
            {(localError || authError) && (
              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="text-red-400 text-sm text-center"
              >
                {localError || authError}
              </motion.p>
            )}
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              type="submit"
              className="w-full font-black py-3 px-4 rounded-xl focus:outline-none transition-all duration-300 flex items-center justify-center text-white"
              style={{
                background: 'linear-gradient(135deg, #8B0000 0%, #DC143C 100%)',
                boxShadow: '0 4px 15px rgba(139, 0, 0, 0.3)',
              }}
              disabled={loading}
            >
              {loading ? (
                <>
                  <svg className="animate-spin h-5 w-5 text-white mr-3" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Registrando...
                </>
              ) : (
                'Registrar'
              )}
            </motion.button>
          </form>
          <p className="text-center text-lightGray text-sm mt-6">
            Já tem uma conta?{' '}
            <Link to="/login" className="text-primaryRed hover:underline font-semibold">
              Faça login aqui
            </Link>
          </p>
        </div>
      </motion.div>
    </motion.div>
  );
};

export default Register;
