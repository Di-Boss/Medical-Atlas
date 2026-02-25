import { type NextRequest, NextResponse } from "next/server"

// Use 127.0.0.1 for server-side fetch (more reliable on Windows than localhost)
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"

function forwardAuthHeaders(request: NextRequest): HeadersInit {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  }
  const auth = request.headers.get("authorization")
  if (auth) headers["Authorization"] = auth
  const cookie = request.headers.get("cookie")
  if (cookie) headers["Cookie"] = cookie
  return headers
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const type = searchParams.get("type") // "doctor" or "hospital"

  if (!type) {
    return NextResponse.json({ error: "Type parameter required" }, { status: 400 })
  }

  try {
    const endpoint = type === "doctor" ? "doctors" : "hospitals"
    const response = await fetch(`${API_BASE}/admin/${endpoint}`, {
      headers: forwardAuthHeaders(request),
    })
    const data = await response.json().catch(() => ({}))
    if (!response.ok) {
      return NextResponse.json(data, { status: response.status })
    }
    // Backend returns doctors with "id" (actually doctor_id); frontend expects doctor_id and id
    if (type === "doctor" && Array.isArray(data)) {
      const normalized = data.map((d: Record<string, unknown>) => ({
        ...d,
        doctor_id: d.doctor_id ?? d.id,
        id: typeof d.id === "string" ? d.id : d.id,
      }))
      return NextResponse.json(normalized)
    }
    return NextResponse.json(data)
  } catch (error) {
    console.error(`Failed to fetch ${type}s:`, error)
    return NextResponse.json(
      { error: `Failed to fetch ${type}s. Is the backend running at ${API_BASE}?` },
      { status: 500 }
    )
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { type, ...data } = body

    if (!type) {
      return NextResponse.json({ error: "Type field required" }, { status: 400 })
    }

    const endpoint = type === "doctor" ? "doctors" : "hospitals"
    const response = await fetch(`${API_BASE}/admin/${endpoint}`, {
      method: "POST",
      headers: forwardAuthHeaders(request),
      body: JSON.stringify(data),
    })

    const responseData = await response.json()

    if (!response.ok) {
      return NextResponse.json(responseData, { status: response.status })
    }

    return NextResponse.json(responseData)
  } catch (error) {
    console.error("Failed to create resource:", error)
    return NextResponse.json({ error: "Failed to create resource" }, { status: 500 })
  }
}

export async function PUT(request: NextRequest) {
  try {
    const body = await request.json()
    const { type, doctorId, id, ...data } = body

    if (!type) {
      return NextResponse.json({ error: "Type field required" }, { status: 400 })
    }
    // Backend may expect numeric id in path (e.g. /admin/doctors/5) or doctor_id (e.g. /admin/doctors/123456)
    const pathId = id != null ? String(id) : doctorId
    if (!pathId) {
      return NextResponse.json({ error: "id or doctorId required" }, { status: 400 })
    }

    const response = await fetch(`${API_BASE}/admin/doctors/${pathId}`, {
      method: "PUT",
      headers: forwardAuthHeaders(request),
      body: JSON.stringify(data),
    })

    const responseData = await response.json()

    if (!response.ok) {
      return NextResponse.json(responseData, { status: response.status })
    }

    return NextResponse.json(responseData)
  } catch (error) {
    console.error("Failed to update resource:", error)
    return NextResponse.json({ error: "Failed to update resource" }, { status: 500 })
  }
}
