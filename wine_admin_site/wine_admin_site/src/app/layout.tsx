'use client';
import SideBar from "@/components/SideBar/NavBar";
import "./globals.css";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <SideBar/>
        {children}
      </body>
    </html>
  );
}
