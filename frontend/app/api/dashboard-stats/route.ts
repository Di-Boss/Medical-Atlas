import { NextResponse } from "next/server"

export async function GET() {
  try {
    // Replace this URL with your actual FastAPI backend endpoint
    const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"
    const response = await fetch(`${API_BASE}/dashboard-stats`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    })

    if (!response.ok) {
      throw new Error("Failed to fetch dashboard stats")
    }

    const data = await response.json()

    // Expected format from your API:
    // {
    //   "checks_this_week": 145,
    //   "resistant_count": 58,
    //   "not_resistant_count": 87,
    //   "top_antibiotics": [
    //     { "name": "Amoxicillin", "count": 45 },
    //     { "name": "Ciprofloxacin", "count": 38 },
    //     { "name": "Vancomycin", "count": 32 }
    //   ],
    //   "average_age": 52.3
    // }

    return NextResponse.json({
      checksThisWeek: data.checks_this_week || 0,
      resistantCount: data.resistant_count || 0,
      notResistantCount: data.not_resistant_count || 0,
      topAntibiotics: data.top_antibiotics || [],
      averageAge: data.average_age || 0,
    })
  } catch (error) {
    console.error("Dashboard stats error:", error)
    
    // Return mock data if API is unavailable
    return NextResponse.json({
      checksThisWeek: 145,
      resistantCount: 58,
      notResistantCount: 87,
      topAntibiotics: [
        { name: "Amoxicillin", count: 45 },
        { name: "Ciprofloxacin", count: 38 },
        { name: "Vancomycin", count: 32 },
      ],
      averageAge: 52.3,
    })
  }
}
