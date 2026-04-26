import "./globals.css";
import type { Metadata, Viewport } from "next";
import { Toaster } from "react-hot-toast";
import { AuthProvider } from "@/lib/auth";

export const metadata: Metadata = {
  title: "DeepFake Detector — AI Content Authenticity Platform",
  description:
    "Detect AI-generated images, videos, audio, text and URLs with confidence. Production-grade SaaS by DeepFake Detector.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#eef2ff" },
    { media: "(prefers-color-scheme: dark)", color: "#0f172a" },
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">
        <AuthProvider>
          {children}
          <Toaster
            position="top-right"
            toastOptions={{
              style: {
                borderRadius: "12px",
                background: "rgba(17, 24, 39, 0.92)",
                color: "#fff",
                backdropFilter: "blur(8px)",
              },
            }}
          />
        </AuthProvider>
      </body>
    </html>
  );
}
