import { type NextRequest, NextResponse } from "next/server"

// Demo credentials when backend is unavailable (localhost)
const DEMO_DOCTOR_ID = "123456"
const DEMO_PASSWORD = "password"

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { doctor_id, password } = body ?? {}

    if (!doctor_id || password === undefined) {
      return NextResponse.json(
        { success: false, error: "Doctor ID and password are required" },
        { status: 400 }
      )
    }

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"
    // Backend expects doctor_id as string (6 digits)
    const doctorIdStr = String(doctor_id).trim()
    const passwordStr = typeof password === "string" ? password : ""

    try {
      const response = await fetch(`${apiUrl}/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ doctor_id: doctorIdStr, password: passwordStr }),
      })

      const contentType = response.headers.get("content-type")
      const isJson = contentType?.includes("application/json")
      const data = isJson ? ((await response.json()) as Record<string, unknown>) : {}

      if (response.ok && isJson) {
        // Backend returns { access_token, refresh_token, token_type, expires_in, role }
        const rawRole = (data.role as string) || "Doctor"
        const role = rawRole.toLowerCase() === "admin" ? "Admin" : rawRole
        const res = NextResponse.json({
          success: true,
          role,
          access_token: data.access_token,
          refresh_token: data.refresh_token,
          token_type: data.token_type,
          expires_in: data.expires_in,
        })
        const isSecure =
          request.url.startsWith("https://") ||
          request.headers.get("x-forwarded-proto") === "https"
        res.cookies.set("user_role", role, {
          httpOnly: true,
          sameSite: "lax",
          maxAge: 60 * 60 * 24, // 24 hours
          path: "/",
          secure: isSecure,
        })
        return res
      }

      if (!response.ok) {
        if (doctorIdStr === DEMO_DOCTOR_ID && passwordStr === DEMO_PASSWORD) {
          const res = NextResponse.json({ success: true, role: "Doctor" })
          res.cookies.set("user_role", "Doctor", {
            httpOnly: true,
            sameSite: "lax",
            maxAge: 60 * 60 * 24,
            path: "/",
          })
          return res
        }
        const detail = Array.isArray(data.detail)
          ? (data.detail as Array<{ msg?: string }>)[0]?.msg
          : typeof data.detail === "string"
            ? data.detail
            : null
        const errorMsg =
          response.status === 422
            ? detail || "Doctor ID must be exactly 6 digits and password is required."
            : detail || "Incorrect ID or password."
        return NextResponse.json({ success: false, error: errorMsg }, { status: response.status })
      }
    } catch (err) {
      if (doctorIdStr === DEMO_DOCTOR_ID && passwordStr === DEMO_PASSWORD) {
        const res = NextResponse.json({ success: true, role: "Doctor" })
        res.cookies.set("user_role", "Doctor", {
          httpOnly: true,
          sameSite: "lax",
          maxAge: 60 * 60 * 24,
          path: "/",
        })
        return res
      }
      console.error("Login fetch error:", err)
      return NextResponse.json(
        { success: false, error: "Login service unavailable. Is the backend running on port 8000?" },
        { status: 503 }
      )
    }

    return NextResponse.json({ success: false, error: "Authentication failed" }, { status: 401 })
  } catch {
    return NextResponse.json(
      { success: false, error: "Authentication failed" },
      { status: 500 }
    )
  }
}
