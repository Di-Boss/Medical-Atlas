import { NextResponse } from "next/server"
import type { NextRequest } from "next/server"

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  // Clear role when visiting login page (logout)
  if (pathname === "/") {
    const res = NextResponse.next()
    res.cookies.set("user_role", "", { path: "/", maxAge: 0 })
    return res
  }

  // Protect admin: only allow if user_role cookie is Admin (case-insensitive)
  if (pathname.startsWith("/admin")) {
    const role = request.cookies.get("user_role")?.value
    if (!role || role.toLowerCase() !== "admin") {
      return NextResponse.redirect(new URL("/", request.url))
    }
  }

  return NextResponse.next()
}

export const config = {
  matcher: ["/", "/admin", "/admin/:path*"],
}
