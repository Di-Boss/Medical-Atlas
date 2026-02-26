import { NextResponse } from "next/server"
import type { NextRequest } from "next/server"

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  // Protect admin: only allow if user_role cookie is Admin (case-insensitive)
  // (Do not clear cookie on "/" — that was removing the cookie so /admin had no Cookie header)
  if (pathname.startsWith("/admin")) {
    let role = request.cookies.get("user_role")?.value
    if (!role) {
      const cookieHeader = request.headers.get("cookie")
      const match = cookieHeader?.match(/\buser_role=([^;]+)/)
      role = match ? match[1].trim() : null
    }
    if (!role || role.toLowerCase() !== "admin") {
      return NextResponse.redirect(new URL("/", request.url))
    }
  }

  return NextResponse.next()
}

export const config = {
  matcher: ["/admin", "/admin/:path*"],
}
