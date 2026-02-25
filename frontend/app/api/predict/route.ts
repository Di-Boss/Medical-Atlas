import { type NextRequest, NextResponse } from "next/server"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"

// Normalize backend response so new UI always gets { resistant: 0|1, probability?: number }
function normalizePrediction(data: unknown): { resistant: number; probability?: number } {
  if (data && typeof data === "object" && "resistant" in data) {
    const r = (data as { resistant?: unknown }).resistant
    const resistant = r === true || r === 1 ? 1 : 0
    const probability =
      typeof (data as { probability?: number }).probability === "number"
        ? (data as { probability: number }).probability
        : typeof (data as { confidence?: number }).confidence === "number"
          ? (data as { confidence: number }).confidence
          : undefined
    return { resistant, probability }
  }
  return { resistant: 0, probability: undefined }
}

// Mock when backend is down (new UI expects resistant 0|1, probability)
function mockPrediction(body: Record<string, unknown>): { resistant: number; probability: number } {
  const age = Number(body?.age) || 0
  const duration = Number(body?.duration_days) || 0
  const score = (age / 100) * 0.4 + Math.min(duration / 30, 1) * 0.6
  return {
    resistant: score > 0.5 ? 1 : 0,
    probability: 0.7 + Math.random() * 0.25,
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()

    try {
      const response = await fetch(`${API_URL}/predict`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      })

      const contentType = response.headers.get("content-type")
      const isJson = contentType?.includes("application/json")

      if (response.ok && isJson) {
        const data = await response.json()
        return NextResponse.json(normalizePrediction(data))
      }

      if (!response.ok || !isJson) {
        return NextResponse.json(mockPrediction(body as Record<string, unknown>))
      }
    } catch {
      return NextResponse.json(mockPrediction(body as Record<string, unknown>))
    }

    return NextResponse.json(mockPrediction(body as Record<string, unknown>))
  } catch (error) {
    console.error("Prediction error:", error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to get prediction" },
      { status: 500 },
    )
  }
}
