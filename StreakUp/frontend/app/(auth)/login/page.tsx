"use client";

import { Suspense, useState, type FormEvent } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Flame, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { login, saveSession } from "@/services/auth/authService";

function LoginPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      const data = await login({ email, password });
      saveSession(data);
      const nextPath = searchParams.get("next");
      router.replace(nextPath && nextPath.startsWith("/") ? nextPath : "/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo iniciar sesión.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="absolute inset-0 grid place-items-center p-[26px_22px] overflow-hidden z-10 animate-[enter_0.28s_ease_both]">
      <div className="w-full max-w-[380px] relative z-10 text-center">
        <div className="mx-auto size-14 rounded-2xl bg-[var(--bg3)] text-[var(--yellow)] grid place-items-center">
          <Flame className="size-8" strokeWidth={2.4} aria-hidden="true" />
        </div>
        <div className="mt-4 mb-6">
          <h1 className="text-[36px] leading-[1.02] tracking-[-1px] font-bold">Streak Up</h1>
          <p className="text-white/70 mt-2">Bienvenido de vuelta</p>
        </div>
        
        <div className="p-[22px] rounded-[24px] bg-[var(--bg2)] border border-white/12">
          <form onSubmit={handleSubmit}>
            {error && (
              <div role="alert" className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300 text-left">
                {error}
              </div>
            )}

            <div className="text-left mb-[16px]">
              <label htmlFor="login-email" className="block font-[900] mb-[8px]">Correo</label>
              <input
                id="login-email"
                type="email"
                placeholder="tu@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                disabled={isLoading}
                className="w-full h-[54px] rounded-[14px] border border-white/20 bg-[var(--bg1)] text-white text-[16px] px-[16px] outline-none placeholder:text-white/65 focus-visible:ring-2 focus-visible:ring-[var(--yellow)]"
              />
            </div>

            <div className="text-left mb-[16px]">
              <label htmlFor="login-password" className="block font-[900] mb-[8px]">Contraseña</label>
              <input
                id="login-password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                disabled={isLoading}
                className="w-full h-[54px] rounded-[14px] border border-white/20 bg-[var(--bg1)] text-white text-[16px] px-[16px] outline-none placeholder:text-white/65 focus-visible:ring-2 focus-visible:ring-[var(--yellow)]"
              />
            </div>
            
            <Button type="submit" variant="sacro-purple" size="sacro" disabled={isLoading}>
              {isLoading ? <Loader2 className="size-5 animate-spin mr-2" /> : null}
              Iniciar sesión
            </Button>
            
            <div className="h-[18px]"></div>
            
            <Button type="button" variant="sacro-ghost" size="sacro" onClick={() => router.push("/register")} disabled={isLoading}>
              Crear cuenta
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="size-8 border-2 border-white border-t-transparent rounded-full animate-spin" />
        </div>
      }
    >
      <LoginPageContent />
    </Suspense>
  );
}
