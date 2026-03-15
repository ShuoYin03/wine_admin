import Header from "@/components/Header/Header";
import "./globals.css";
import StyledComponentsRegistry from "./lib/registry";

export const metadata = {
  title: 'Wine Admin Site',
  description: 'Browse, Search, and Manage Wine Lots',
};

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
