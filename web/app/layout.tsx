import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "StoryTeling - Video Generator Gratis",
  description: "Bikin video storytelling kayak Zaman Firaun - 100% gratis, tanpa API key",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="id">
      <body className="bg-zinc-950 text-white min-h-screen">{children}</body>
    </html>
  );
}
