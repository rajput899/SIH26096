import type { Metadata } from "next";
import "./globals.css"; import Kiosk from "../components/Kiosk";
import InterfaceLanguage from '../components/InterfaceLanguage';

export const metadata: Metadata = {
  title: "Dr. B. R. Ambedkar · Digital Heritage Archive",
  description: "Read preserved sources and curator-verified archival text.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body><InterfaceLanguage><Kiosk>{children}</Kiosk></InterfaceLanguage></body></html>;
}


