import type { Metadata } from "next";
import { AppProviders } from "@/providers/AppProviders";
import "./globals.css";

export const metadata: Metadata = {
  title: "StreakUp",
  description: "Boost your productivity!"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es" suppressHydrationWarning>
      <body className="antialiased overflow-hidden text-[var(--text)] bg-[var(--bg1)]">
        <AppProviders>
          <div className="mx-auto w-full max-w-md h-[100dvh] relative overflow-hidden bg-[var(--bg1)] shadow-2xl">
            {children}
          </div>
        </AppProviders>
      </body>
    </html>
  );
}
