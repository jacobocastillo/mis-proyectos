"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { register } from "@/services/auth/authService";

export default function RegisterPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");

    if (password !== confirmPassword) {
      setError("Las contraseñas no coinciden.");
      return;
    }

    setIsLoading(true);

    try {
      await register({ username, email, password });
      router.replace("/login");
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo crear la cuenta.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="absolute inset-0 grid place-items-center p-[26px_22px] overflow-x-hidden overflow-y-auto z-10 animate-[enter_0.28s_ease_both]">
      <div className="w-full max-w-[380px] relative z-10 text-center my-auto py-8">
        <div className="text-[58px] drop-shadow-[0_0_20px_rgba(255,150,30,0.8)] animate-[float_2.4s_ease-in-out_infinite]">🔥</div>
        <div className="mt-[10px] mb-[22px]">
          <h1 className="text-[42px] leading-[1.02] tracking-[-1px] font-bold">Streak Up</h1>
          <p className="text-white/74">Crea tu cuenta</p>
        </div>
        
        <div className="p-[24px] rounded-[28px] bg-[linear-gradient(145deg,rgba(255,255,255,0.20),rgba(255,255,255,0.10))] border border-white/20 shadow-[0_22px_55px_rgba(18,5,72,0.32)] backdrop-blur-[18px]">
          <form onSubmit={handleSubmit}>
            {error && (
              <div role="alert" className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300 text-left">
                {error}
              </div>
            )}

            <div className="text-left mb-[16px]">
              <label htmlFor="reg-username" className="block font-[900] mb-[8px]">Nombre de usuario</label>
              <input
                id="reg-username"
                type="text"
                placeholder="tu_usuario"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                disabled={isLoading}
                className="w-full h-[58px] rounded-[20px] border border-white/14 bg-[#27125e8c] text-white text-[17px] px-[18px] outline-none placeholder:text-white/55 focus-visible:ring-2 focus-visible:ring-white/60"
              />
            </div>

            <div className="text-left mb-[16px]">
              <label htmlFor="reg-email" className="block font-[900] mb-[8px]">Correo</label>
              <input
                id="reg-email"
                type="email"
                placeholder="tu@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                disabled={isLoading}
                className="w-full h-[58px] rounded-[20px] border border-white/14 bg-[#27125e8c] text-white text-[17px] px-[18px] outline-none placeholder:text-white/55 focus-visible:ring-2 focus-visible:ring-white/60"
              />
            </div>

            <div className="text-left mb-[16px]">
              <label htmlFor="reg-password" className="block font-[900] mb-[8px]">Contraseña</label>
              <input
                id="reg-password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                disabled={isLoading}
                className="w-full h-[58px] rounded-[20px] border border-white/14 bg-[#27125e8c] text-white text-[17px] px-[18px] outline-none placeholder:text-white/55 focus-visible:ring-2 focus-visible:ring-white/60"
              />
            </div>

            <div className="text-left mb-[24px]">
              <label htmlFor="reg-confirm-password" className="block font-[900] mb-[8px]">Confirmar contraseña</label>
              <input
                id="reg-confirm-password"
                type="password"
                placeholder="••••••••"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                disabled={isLoading}
                className="w-full h-[58px] rounded-[20px] border border-white/14 bg-[#27125e8c] text-white text-[17px] px-[18px] outline-none placeholder:text-white/55 focus-visible:ring-2 focus-visible:ring-white/60"
              />
            </div>
            
            <Button type="submit" variant="sacro-purple" size="sacro" disabled={isLoading}>
              {isLoading ? <Loader2 className="size-5 animate-spin mr-2" /> : null}
              Crear cuenta
            </Button>
            
            <div className="h-[18px]"></div>
            
            <Button type="button" variant="sacro-ghost" size="sacro" onClick={() => router.push("/login")} disabled={isLoading}>
              Iniciar sesión
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}
