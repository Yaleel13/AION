import type { Metadata, Viewport } from "next"
import { Geist, Geist_Mono, Newsreader } from "next/font/google"
import { WebMcpOpportunityTools } from "@/components/webmcp-opportunity-tools"
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
  metadataBase: new URL("https://aion-siryali.vercel.app"),
  title: "AION",
  description:
    "AION — the Alchemical Intelligence for Ontological Navigation. The guide who remembers who you are becoming.",
  applicationName: "AION",
  alternates: { canonical: "/" },
  icons: {
    icon: [{ url: "/icon.svg", type: "image/svg+xml" }],
    shortcut: "/icon.svg",
  },
  openGraph: {
    type: "website",
    url: "/",
    siteName: "AION",
    title: "AION — Alchemical Intelligence for Ontological Navigation",
    description: "The Guide who remembers who you are becoming.",
    images: [{ url: "/opengraph-image", width: 1200, height: 630, alt: "AION, the Guide Between Worlds" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "AION — Alchemical Intelligence for Ontological Navigation",
    description: "The Guide who remembers who you are becoming.",
    images: ["/opengraph-image"],
  },
  robots: { index: false, follow: false },
}

export const viewport: Viewport = {
  themeColor: "#07111e",
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
        <WebMcpOpportunityTools />
        {children}
      </body>
    </html>
  )
}
