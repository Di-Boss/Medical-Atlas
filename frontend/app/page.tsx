"use client"

import type React from "react"

import { useState, useRef, useEffect } from "react"
import Image from "next/image"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Moon, Sun } from "lucide-react"

export default function DoctorLogin() {
  const [doctorId, setDoctorId] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [idError, setIdError] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [darkMode, setDarkMode] = useState(false)
  const doctorIdRef = useRef<HTMLInputElement>(null)

  // Auto-focus the Doctor ID field on load
  useEffect(() => {
    doctorIdRef.current?.focus()
  }, [])

  // Validate Doctor ID (must be 6 digits)
  const handleDoctorIdChange = (value: string) => {
    // Only allow numeric input
    const numericValue = value.replace(/\D/g, "")
    setDoctorId(numericValue)

    // Show error if user has typed something but it's not 6 digits
    if (numericValue.length > 0 && numericValue.length < 6) {
      setIdError("Doctor ID must be 6 digits")
    } else {
      setIdError("")
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")

    // Validate before submitting
    if (doctorId.length !== 6) {
      setIdError("Doctor ID must be 6 digits")
      return
    }

    setIsLoading(true)

    try {
      const response = await fetch("/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          doctor_id: doctorId,
          password: password,
        }),
      })

      const data = await response.json().catch(() => ({}))

      if (data.success) {
        window.location.href = "/dashboard"
      } else {
        setError(data.error || "Incorrect ID or password.")
      }
    } catch (err) {
      setError("An error occurred. Please try again.")
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className={`min-h-screen p-4 ${darkMode ? "bg-gray-900" : "bg-white"}`}>
      <div className="absolute top-6 left-6">
        <Image src="/ATLas.png" alt="Atlas Medical Portal" width={100} height={100} priority />
      </div>
      <div className="absolute top-6 right-6">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setDarkMode(!darkMode)}
          className={darkMode ? "text-gray-300 hover:text-white hover:bg-gray-800" : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"}
        >
          {darkMode ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
        </Button>
      </div>

      {/* Login Card - centered */}
      <div className="min-h-screen flex items-center justify-center">
        <Card className={`w-full max-w-[450px] shadow-lg ${darkMode ? "border-gray-700 bg-gray-800" : "border-gray-200"}`}>
          <CardHeader className="space-y-1 pb-6 pt-12 px-8">
            <h1 className={`text-4xl font-bold text-left ${darkMode ? "text-white" : "text-black"}`}>Login</h1>
          </CardHeader>
          <CardContent className="px-8 pb-8">
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Doctor ID Field */}
              <div className="space-y-2">
                <Label htmlFor="doctor-id" className={`text-sm font-medium ${darkMode ? "text-gray-300" : ""}`}>
                  Doctor ID
                </Label>
                <Input
                  id="doctor-id"
                  ref={doctorIdRef}
                  type="text"
                  inputMode="numeric"
                  maxLength={6}
                  value={doctorId}
                  onChange={(e) => handleDoctorIdChange(e.target.value)}
                  placeholder="Enter 6-digit ID"
                  className={`h-11 ${darkMode ? "border-gray-600 bg-gray-700 text-white placeholder:text-gray-400" : ""}`}
                  disabled={isLoading}
                />
                {idError && <p className="text-sm text-red-600">{idError}</p>}
              </div>

              {/* Password Field */}
              <div className="space-y-2">
                <Label htmlFor="password" className={`text-sm font-medium ${darkMode ? "text-gray-300" : ""}`}>
                  Password
                </Label>
                <Input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter password"
                  className={`h-11 ${darkMode ? "border-gray-600 bg-gray-700 text-white placeholder:text-gray-400" : ""}`}
                  disabled={isLoading}
                />
                <p className={`text-sm text-center pt-1 ${darkMode ? "text-gray-400" : "text-gray-500"}`}>
                  forgotten password •{" "}
                  <a href="mailto:it@atlas.com" className="text-[#0566bb] hover:underline">
                    contact IT
                  </a>
                </p>
              </div>

              {/* Error Message */}
              {error && <div className="text-sm text-red-600 text-center">{error}</div>}

              {/* Login Button */}
              <Button
                type="submit"
                className="w-full h-11 bg-[#08c7cf] hover:bg-[#06a8af] text-white font-medium transition-colors"
                disabled={isLoading}
              >
                {isLoading ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg
                      className="animate-spin h-5 w-5"
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      />
                    </svg>
                    Logging in...
                  </span>
                ) : (
                  "Login"
                )}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>

      <footer className="fixed bottom-4 left-0 right-0 text-center">
        <p className={`text-xs ${darkMode ? "text-gray-400" : "text-[#0566bb]"}`}>
          © 2025 Atlas Research Medical System All Rights reserved
        </p>
      </footer>
    </div>
  )
}
