'use client';
import Header from "@/components/Header/Header";
import "./globals.css";
import { ThemeProvider } from "styled-components";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <Header/>
        {children}
      </body>
    </html>
  );
}
