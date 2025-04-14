'use client';
import Header from "@/components/Header/Header";
import "./globals.css";
import StyledComponentsRegistry from "./lib/registry";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <StyledComponentsRegistry>
          <Header/>
          {children}
        </StyledComponentsRegistry>
      </body>
    </html>
  );
}
