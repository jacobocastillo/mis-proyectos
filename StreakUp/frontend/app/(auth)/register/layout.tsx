import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Crear Cuenta – StreakUP",
  description: "Crea tu cuenta en StreakUP",
};

export default function RegisterLayout({
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
