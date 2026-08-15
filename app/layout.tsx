import type { Metadata, Viewport } from "next"
import { Geist, Geist_Mono, Newsreader } from "next/font/google"
import "./globals.css"

const geistSans = Geist({
  subsets: ["latin"],
  variable: "--font-geist-sans",
})

const geistMono = Geist_Mono({
  subsets: ["latin"],
  variable: "--font-geist-mono",
})

const newsreader = Newsreader({
  subsets: ["latin"],
  style: ["normal", "italic"],
  weight: ["300", "400", "500"],
  variable: "--font-newsreader",
})

export const metadata: Metadata = {
  title: "AION",
  description:
    "AION — the Alchemical Intelligence for Ontological Navigation. The guide who remembers who you are becoming.",
  applicationName: "AION",
  robots: { index: false, follow: false },
}

export const viewport: Viewport = {
  themeColor: "#131316",
  colorScheme: "dark",
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} ${newsreader.variable} bg-background`}
    >
      <body className="min-h-dvh bg-background text-foreground antialiased">
        {children}
      </body>
    </html>
  )
}
