import type { Metadata } from 'next'
import { Geist, Geist_Mono } from 'next/font/google'
import { Analytics } from '@vercel/analytics/next'
import './globals.css'

const _geist = Geist({ subsets: ["latin"] });
const _geistMono = Geist_Mono({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: 'Medical Atlas',
  description: 'Atlas Research Medical System',
  generator: 'v0.app',
  icons: {
    icon: '/favicon-32x32.png',
    apple: '/favicon-32x32.png',
  },
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en">
      <body className={`font-sans antialiased`}>
        {children}
        <Analytics />
        <footer className="fixed bottom-4 left-0 right-0 text-center">
          <p className="text-xs text-[#0566bb]">© 2025 Atlas Research Medical System All Rights reserved</p>
        </footer>
      </body>
    </html>
  )
}
