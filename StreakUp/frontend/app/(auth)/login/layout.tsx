import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Iniciar Sesión – StreakUP",
  description: "Inicia sesión en tu cuenta de StreakUP",
};

export default function LoginLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-8">
      {children}
    </div>
  );
}
