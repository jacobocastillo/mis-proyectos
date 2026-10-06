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
      <body className="antialiased overflow-hidden text-[var(--text)] bg-[linear-gradient(160deg,var(--bg1),var(--bg2)_55%,var(--bg3))]">
        <AppProviders>
          <div className="mx-auto w-full max-w-md h-[100dvh] relative overflow-hidden bg-[radial-gradient(circle_at_50%_35%,rgba(255,229,54,0.22),transparent_18%),linear-gradient(160deg,var(--bg1),var(--bg2)_55%,var(--bg3))] shadow-2xl before:content-[''] before:absolute before:-left-[30%] before:-right-[30%] before:h-[34%] before:rounded-b-[50%] before:bg-white/5 before:top-[5%] before:pointer-events-none after:content-[''] after:absolute after:-left-[30%] after:-right-[30%] after:h-[24%] after:rounded-t-[50%] after:bg-white/10 after:bottom-[-8%] after:pointer-events-none">
            {children}
          </div>
        </AppProviders>
      </body>
    </html>
  );
}
