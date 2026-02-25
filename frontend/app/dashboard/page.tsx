"use client"

import { useState, useEffect } from "react"
import Image from "next/image"
import Link from "next/link"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { LogOut, Moon, Sun } from 'lucide-react'

export default function Dashboard() {
  const [stats, setStats] = useState({
    checksThisWeek: 0,
    resistantCount: 0,
    notResistantCount: 0,
    topAntibiotics: [] as { name: string; count: number }[],
    averageAge: 0,
  })
  const [isLoading, setIsLoading] = useState(true)
  const [darkMode, setDarkMode] = useState(false)

  useEffect(() => {
    // Fetch dashboard stats from API
    const fetchStats = async () => {
      try {
        const response = await fetch("/api/dashboard-stats")
        if (response.ok) {
          const data = await response.json()
          setStats(data)
        }
      } catch (error) {
        console.error("Failed to fetch dashboard stats:", error)
      } finally {
        setIsLoading(false)
      }
    }

    fetchStats()
  }, [])

  const totalPredictions = stats.resistantCount + stats.notResistantCount
  const resistantPercentage = totalPredictions > 0 ? (stats.resistantCount / totalPredictions) * 100 : 0
  const notResistantPercentage = totalPredictions > 0 ? (stats.notResistantCount / totalPredictions) * 100 : 0

  return (
    <div className={`min-h-screen pb-20 ${darkMode ? "bg-gray-900" : "bg-white"}`}>
      {/* Header */}
      <header className={`px-8 py-4 flex items-center justify-between ${darkMode ? "border-gray-700" : ""}`}>
        <Image src="/ATLas.png" alt="Atlas Medical Portal" width={100} height={100} className="object-contain" />
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setDarkMode(!darkMode)}
            className={darkMode ? "text-gray-300 hover:text-white hover:bg-gray-800" : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"}
          >
            {darkMode ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
          </Button>
          <Link href="/">
            <Button
              variant="ghost"
              className={darkMode ? "text-gray-300 hover:text-white hover:bg-gray-800" : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"}
            >
              <LogOut className="mr-2 h-4 w-4" />
              Log Out
            </Button>
          </Link>
        </div>
      </header>

      {/* Main content */}
      <div className="max-w-6xl mx-auto px-8 py-8">
        <h1 className={`text-4xl font-bold mb-8 ${darkMode ? "text-white" : "text-black"}`}>Dashboard</h1>

        {isLoading ? (
          <div className={`text-center py-12 ${darkMode ? "text-gray-400" : "text-gray-600"}`}>Loading dashboard...</div>
        ) : (
          <>
            <div className={`mb-8 p-6 border-2 rounded-xl flex items-center justify-between ${darkMode ? "bg-gray-800 border-gray-700" : "bg-white border-gray-200"}`}>
              <span className={`text-lg font-medium ${darkMode ? "text-white" : "text-gray-900"}`}>
                Make new prediction:
              </span>
              <Link href="/dashboard/predict">
                <Button className="bg-[#08c7cf] hover:bg-[#07b0b8] text-white font-semibold px-8 py-3">
                  Predict
                </Button>
              </Link>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
              {/* Checks This Week */}
              <Card className={darkMode ? "bg-gray-800 border-gray-700" : "border-gray-200"}>
                <CardHeader className="pb-3">
                  <CardTitle className={`text-sm font-medium ${darkMode ? "text-gray-400" : "text-gray-600"}`}>
                    Checks This Week
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className={`text-3xl font-bold ${darkMode ? "text-white" : "text-[#0566bb]"}`}>
                    {stats.checksThisWeek}
                  </div>
                </CardContent>
              </Card>

              {/* Average Patient Age */}
              <Card className={darkMode ? "bg-gray-800 border-gray-700" : "border-gray-200"}>
                <CardHeader className="pb-3">
                  <CardTitle className={`text-sm font-medium ${darkMode ? "text-gray-400" : "text-gray-600"}`}>
                    Average Patient Age
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className={`text-3xl font-bold ${darkMode ? "text-white" : "text-[#0566bb]"}`}>
                    {stats.averageAge.toFixed(1)}
                  </div>
                </CardContent>
              </Card>

              {/* Resistant Count */}
              <Card className={darkMode ? "bg-gray-800 border-gray-700" : "border-gray-200"}>
                <CardHeader className="pb-3">
                  <CardTitle className={`text-sm font-medium ${darkMode ? "text-gray-400" : "text-gray-600"}`}>
                    Resistant Cases
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold text-red-500">{stats.resistantCount}</div>
                </CardContent>
              </Card>

              {/* Not Resistant Count */}
              <Card className={darkMode ? "bg-gray-800 border-gray-700" : "border-gray-200"}>
                <CardHeader className="pb-3">
                  <CardTitle className={`text-sm font-medium ${darkMode ? "text-gray-400" : "text-gray-600"}`}>
                    Not Resistant Cases
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold text-green-500">{stats.notResistantCount}</div>
                </CardContent>
              </Card>
            </div>

            {/* Charts Row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
              {/* Distribution Pie Chart */}
              <Card className={darkMode ? "bg-gray-800 border-gray-700" : "border-gray-200"}>
                <CardHeader>
                  <CardTitle className={darkMode ? "text-white" : "text-black"}>Resistance Distribution</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center justify-center py-8">
                    <div className="relative w-48 h-48">
                      <svg viewBox="0 0 100 100" className="transform -rotate-90">
                        {/* Not Resistant - Green */}
                        <circle
                          cx="50"
                          cy="50"
                          r="40"
                          fill="none"
                          stroke="#10b981"
                          strokeWidth="20"
                          strokeDasharray={`${notResistantPercentage * 2.51} ${251 - notResistantPercentage * 2.51}`}
                        />
                        {/* Resistant - Red */}
                        <circle
                          cx="50"
                          cy="50"
                          r="40"
                          fill="none"
                          stroke="#ef4444"
                          strokeWidth="20"
                          strokeDasharray={`${resistantPercentage * 2.51} ${251 - resistantPercentage * 2.51}`}
                          strokeDashoffset={`-${notResistantPercentage * 2.51}`}
                        />
                      </svg>
                    </div>
                  </div>
                  <div className="flex justify-center gap-6 mt-4">
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 bg-green-500 rounded" />
                      <span className={`text-sm ${darkMode ? "text-gray-300" : "text-gray-700"}`}>
                        Not Resistant ({notResistantPercentage.toFixed(1)}%)
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 bg-red-500 rounded" />
                      <span className={`text-sm ${darkMode ? "text-gray-300" : "text-gray-700"}`}>
                        Resistant ({resistantPercentage.toFixed(1)}%)
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Most Common Antibiotics */}
              <Card className={darkMode ? "bg-gray-800 border-gray-700" : "border-gray-200"}>
                <CardHeader>
                  <CardTitle className={darkMode ? "text-white" : "text-black"}>Most Common Antibiotics</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {stats.topAntibiotics.length > 0 ? (
                      (() => {
                        const maxCount = Math.max(...stats.topAntibiotics.map((a) => a.count))
                        return stats.topAntibiotics.map((antibiotic, index) => (
                          <div key={index} className="space-y-2">
                            <div className="flex justify-between items-center">
                              <span className={`text-sm font-medium ${darkMode ? "text-gray-300" : "text-gray-700"}`}>
                                {antibiotic.name}
                              </span>
                              <span className={`text-sm ${darkMode ? "text-gray-400" : "text-gray-600"}`}>
                                {antibiotic.count} checks
                              </span>
                            </div>
                            <div className={`h-2 rounded-full ${darkMode ? "bg-gray-700" : "bg-gray-200"}`}>
                              <div
                                className="h-full bg-[#08c7cf] rounded-full"
                                style={{
                                  width: maxCount ? `${(antibiotic.count / maxCount) * 100}%` : "0%",
                                }}
                              />
                            </div>
                          </div>
                        ))
                      })()
                    ) : (
                      <p className={`text-sm ${darkMode ? "text-gray-400" : "text-gray-500"}`}>
                        No data available
                      </p>
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
