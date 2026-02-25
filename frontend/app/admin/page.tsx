"use client"

import { useState, useEffect } from "react"
import Image from "next/image"
import Link from "next/link"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { ChevronLeft, UserPlus, Building2, Users, Lock, UserX, Moon, Sun } from "lucide-react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

const US_REGIONS = ["California", "Texas", "Florida", "New York", "Pennsylvania", "Illinois", "Ohio"]

interface Doctor {
  id: number | string
  name: string
  doctor_id: string
  role: "Admin" | "Doctor"
  region: string
  hospital: string
  status: "Active" | "Suspended"
}

interface Hospital {
  id: number
  name: string
  region: string
}

export default function AdminPanel() {
  const [doctors, setDoctors] = useState<Doctor[]>([])
  const [hospitals, setHospitals] = useState<Hospital[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [fetchError, setFetchError] = useState<string | null>(null)
  const [darkMode, setDarkMode] = useState(false)

  // New Doctor Form
  const [newDoctor, setNewDoctor] = useState({
    name: "",
    doctor_id: "",
    password: "",
    role: "Doctor" as "Admin" | "Doctor",
    region: "",
    hospital: "",
  })

  // New Hospital Form
  const [newHospital, setNewHospital] = useState({
    name: "",
    region: "",
  })

  useEffect(() => {
    fetchDoctors()
    fetchHospitals()
  }, [])

  const fetchDoctors = async () => {
    setFetchError(null)
    try {
      const response = await fetch("/api/admin?type=doctor")
      const data = await response.json().catch(() => ({}))
      if (response.ok) {
        setDoctors(Array.isArray(data) ? data : [])
      } else {
        setFetchError(data?.error || "Failed to load doctors")
      }
    } catch (error) {
      console.error("Failed to fetch doctors:", error)
      setFetchError("Failed to load doctors. Is the backend running on port 8000?")
    } finally {
      setIsLoading(false)
    }
  }

  const fetchHospitals = async () => {
    try {
      const response = await fetch("/api/admin?type=hospital")
      const data = await response.json().catch(() => ({}))
      if (response.ok) {
        setHospitals(Array.isArray(data) ? data : [])
      }
    } catch (error) {
      console.error("Failed to fetch hospitals:", error)
    }
  }

  const handleAddDoctor = async () => {
    if (!newDoctor.name || !newDoctor.doctor_id || !newDoctor.password || !newDoctor.region || !newDoctor.hospital) {
      alert("Please fill in all required fields including password")
      return
    }

    try {
      const response = await fetch("/api/admin", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          type: "doctor",
          name: newDoctor.name,
          doctor_id: newDoctor.doctor_id,
          password: newDoctor.password,
          role: newDoctor.role,
          region: newDoctor.region,
          hospital: newDoctor.hospital,
          status: "Active",
        }),
      })

      const result = await response.json()

      if (response.ok) {
        alert("Doctor added successfully!")
        fetchDoctors()
        setNewDoctor({ name: "", doctor_id: "", password: "", role: "Doctor", region: "", hospital: "" })
      } else {
        alert(`Failed to add doctor: ${result.detail || JSON.stringify(result)}`)
      }
    } catch (error) {
      console.error("Failed to add doctor:", error)
      alert("An error occurred while adding the doctor")
    }
  }

  const handleAddHospital = async () => {
    if (!newHospital.name || !newHospital.region) {
      alert("Please fill in all required fields")
      return
    }

    try {
      const response = await fetch("/api/admin", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          type: "hospital",
          name: newHospital.name,
          region: newHospital.region,
          status: "Active",
        }),
      })

      const result = await response.json()

      if (response.ok) {
        alert("Hospital added successfully!")
        fetchHospitals()
        setNewHospital({ name: "", region: "" })
      } else {
        alert(`Failed to add hospital: ${result.detail || JSON.stringify(result)}`)
      }
    } catch (error) {
      console.error("Failed to add hospital:", error)
      alert("An error occurred while adding the hospital")
    }
  }

  const handleResetPassword = async (doctor: Doctor) => {
    const newPassword = prompt("Enter new password:")
    if (newPassword) {
      try {
        const response = await fetch("/api/admin", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            type: "doctor",
            id: doctor.id,
            doctorId: doctor.doctor_id,
            password: newPassword,
          }),
        })
        if (response.ok) {
          alert("Password reset successfully")
          fetchDoctors()
        } else {
          const error = await response.json()
          alert(`Failed to reset password: ${error.detail || JSON.stringify(error)}`)
        }
      } catch (error) {
        console.error("Failed to reset password:", error)
        alert("An error occurred while resetting password")
      }
    }
  }

  const handleSuspendUser = async (doctor: Doctor, suspend: boolean) => {
    try {
      const response = await fetch("/api/admin", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          type: "doctor",
          id: doctor.id,
          doctorId: doctor.doctor_id,
          status: suspend ? "Suspended" : "Active",
        }),
      })
      if (response.ok) {
        alert(`Doctor ${suspend ? "suspended" : "activated"} successfully`)
        fetchDoctors()
      } else {
        const error = await response.json()
        alert(`Failed to update doctor status: ${error.detail || JSON.stringify(error)}`)
      }
    } catch (error) {
      console.error("Failed to suspend user:", error)
      alert("An error occurred while updating doctor status")
    }
  }

  const handleUpdateRole = async (doctor: Doctor, newRole: "Admin" | "Doctor") => {
    try {
      const response = await fetch("/api/admin", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          type: "doctor",
          id: doctor.id,
          doctorId: doctor.doctor_id,
          role: newRole,
        }),
      })
      if (response.ok) {
        alert("Role updated successfully")
        fetchDoctors()
      } else {
        const error = await response.json()
        alert(`Failed to update role: ${error.detail || JSON.stringify(error)}`)
      }
    } catch (error) {
      console.error("Failed to update role:", error)
      alert("An error occurred while updating role")
    }
  }

  return (
    <div className={`min-h-screen pb-20 ${darkMode ? "bg-gray-900" : "bg-white"}`}>
      {/* Header */}
      <header className={`px-8 py-4 flex items-center justify-between ${darkMode ? "border-b border-gray-700" : ""}`}>
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
          <Link href="/dashboard">
            <Button
              variant="ghost"
              className={darkMode ? "text-gray-300 hover:text-white hover:bg-gray-800" : "text-gray-400 hover:text-gray-600 hover:bg-gray-100"}
            >
              <ChevronLeft className="mr-2 h-4 w-4" />
              Back
            </Button>
          </Link>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-8 py-6">
        <h1 className={`text-4xl font-bold mb-8 ${darkMode ? "text-white" : "text-black"}`}>Admin Panel</h1>

        <Tabs defaultValue="doctors" className="w-full">
          <TabsList className={`grid w-full grid-cols-2 mb-8 ${darkMode ? "bg-gray-800" : ""}`}>
            <TabsTrigger value="doctors" className={darkMode ? "data-[state=active]:bg-gray-700 data-[state=active]:text-white" : ""}>
              Doctors
            </TabsTrigger>
            <TabsTrigger value="hospitals" className={darkMode ? "data-[state=active]:bg-gray-700 data-[state=active]:text-white" : ""}>
              Hospitals
            </TabsTrigger>
          </TabsList>

          {/* Doctors Tab */}
          <TabsContent value="doctors">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Add New Doctor */}
              <Card className={darkMode ? "border-gray-700 bg-gray-800" : "border-gray-200"}>
                <CardHeader>
                  <CardTitle className={`flex items-center gap-2 ${darkMode ? "text-white" : ""}`}>
                    <UserPlus className="h-5 w-5 text-[#0566bb]" />
                    Add New Doctor
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <Label className={darkMode ? "text-gray-300" : ""}>Name</Label>
                    <Input
                      value={newDoctor.name}
                      onChange={(e) => setNewDoctor({ ...newDoctor, name: e.target.value })}
                      placeholder="Dr. John Smith"
                      className={darkMode ? "border-gray-600 bg-gray-700 text-white" : ""}
                    />
                  </div>
                  <div>
                    <Label className={darkMode ? "text-gray-300" : ""}>Doctor ID</Label>
                    <Input
                      value={newDoctor.doctor_id}
                      onChange={(e) => setNewDoctor({ ...newDoctor, doctor_id: e.target.value })}
                      placeholder="123456"
                      maxLength={6}
                      className={darkMode ? "border-gray-600 bg-gray-700 text-white" : ""}
                    />
                  </div>
                  <div>
                    <Label className={darkMode ? "text-gray-300" : ""}>Password</Label>
                    <Input
                      type="password"
                      value={newDoctor.password}
                      onChange={(e) => setNewDoctor({ ...newDoctor, password: e.target.value })}
                      placeholder="Enter password"
                      className={darkMode ? "border-gray-600 bg-gray-700 text-white" : ""}
                    />
                  </div>
                  <div>
                    <Label className={darkMode ? "text-gray-300" : ""}>Role</Label>
                    <Select
                      value={newDoctor.role}
                      onValueChange={(value: "Admin" | "Doctor") => setNewDoctor({ ...newDoctor, role: value })}
                    >
                      <SelectTrigger className={darkMode ? "border-gray-600 bg-gray-700 text-white" : ""}>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Doctor">Doctor</SelectItem>
                        <SelectItem value="Admin">Admin</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label className={darkMode ? "text-gray-300" : ""}>Region</Label>
                    <Select
                      value={newDoctor.region}
                      onValueChange={(value) => setNewDoctor({ ...newDoctor, region: value })}
                    >
                      <SelectTrigger className={darkMode ? "border-gray-600 bg-gray-700 text-white" : ""}>
                        <SelectValue placeholder="Select region" />
                      </SelectTrigger>
                      <SelectContent>
                        {US_REGIONS.map((region) => (
                          <SelectItem key={region} value={region}>
                            {region}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label className={darkMode ? "text-gray-300" : ""}>Hospital</Label>
                    <Select
                      value={newDoctor.hospital}
                      onValueChange={(value) => setNewDoctor({ ...newDoctor, hospital: value })}
                    >
                      <SelectTrigger className={darkMode ? "border-gray-600 bg-gray-700 text-white" : ""}>
                        <SelectValue placeholder="Select hospital" />
                      </SelectTrigger>
                      <SelectContent>
                        {hospitals
                          .filter((h) => h.region === newDoctor.region)
                          .map((hospital) => (
                            <SelectItem key={hospital.id} value={hospital.name}>
                              {hospital.name}
                            </SelectItem>
                          ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <Button onClick={handleAddDoctor} className="w-full bg-[#0566bb] hover:bg-[#05447b]">
                    Add Doctor
                  </Button>
                </CardContent>
              </Card>

              {/* Doctors List */}
              <Card className={darkMode ? "lg:col-span-2 border-gray-700 bg-gray-800" : "lg:col-span-2 border-gray-200"}>
                <CardHeader>
                  <CardTitle className={`flex items-center gap-2 ${darkMode ? "text-white" : ""}`}>
                    <Users className="h-5 w-5 text-[#0566bb]" />
                    All Doctors
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {fetchError && (
                    <div className={`mb-4 p-3 rounded-lg text-sm ${darkMode ? "bg-red-950/50 border border-red-800 text-red-300" : "bg-red-50 border border-red-200 text-red-700"}`}>
                      {fetchError}
                      <button
                        type="button"
                        onClick={() => fetchDoctors()}
                        className="ml-2 underline font-medium"
                      >
                        Retry
                      </button>
                    </div>
                  )}
                  {isLoading ? (
                    <p className={darkMode ? "text-gray-400" : "text-gray-500"}>Loading...</p>
                  ) : (
                    <div className="space-y-4 max-h-[600px] overflow-y-auto">
                      {doctors.map((doctor) => (
                        <div
                          key={doctor.doctor_id ?? String(doctor.id)}
                          className={`p-4 border rounded-lg flex items-center justify-between ${darkMode ? "border-gray-600 bg-gray-700" : "border-gray-200"}`}
                        >
                          <div className="flex-1">
                            <h3 className={`font-semibold ${darkMode ? "text-white" : "text-gray-900"}`}>{doctor.name}</h3>
                            <p className={`text-sm ${darkMode ? "text-gray-300" : "text-gray-600"}`}>ID: {doctor.doctor_id}</p>
                            <div className={`flex gap-4 mt-1 text-xs ${darkMode ? "text-gray-400" : "text-gray-500"}`}>
                              <span>Role: {doctor.role}</span>
                              <span>Region: {doctor.region}</span>
                              <span>Hospital: {doctor.hospital || "Not Assigned"}</span>
                              <span>Status: {doctor.status}</span>
                            </div>
                          </div>
                          <div className="flex gap-2">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleResetPassword(doctor)}
                              className="text-[#0566bb]"
                            >
                              <Lock className="h-4 w-4" />
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleSuspendUser(doctor, doctor.status === "Active")}
                              className={doctor.status === "Suspended" ? "text-green-600" : "text-red-600"}
                            >
                              <UserX className="h-4 w-4" />
                            </Button>
                            <Select
                              value={doctor.role}
                              onValueChange={(value: "Admin" | "Doctor") => handleUpdateRole(doctor, value)}
                            >
                              <SelectTrigger className={darkMode ? "w-24 border-gray-600 bg-gray-600 text-white" : "w-24"}>
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="Doctor">Doctor</SelectItem>
                                <SelectItem value="Admin">Admin</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Hospitals Tab */}
          <TabsContent value="hospitals">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Add New Hospital */}
              <Card className={darkMode ? "border-gray-700 bg-gray-800" : "border-gray-200"}>
                <CardHeader>
                  <CardTitle className={`flex items-center gap-2 ${darkMode ? "text-white" : ""}`}>
                    <Building2 className="h-5 w-5 text-[#0566bb]" />
                    Add New Hospital
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <Label className={darkMode ? "text-gray-300" : ""}>Hospital Name</Label>
                    <Input
                      value={newHospital.name}
                      onChange={(e) => setNewHospital({ ...newHospital, name: e.target.value })}
                      placeholder="General Hospital"
                      className={darkMode ? "border-gray-600 bg-gray-700 text-white" : ""}
                    />
                  </div>
                  <div>
                    <Label className={darkMode ? "text-gray-300" : ""}>Region</Label>
                    <Select
                      value={newHospital.region}
                      onValueChange={(value) => setNewHospital({ ...newHospital, region: value })}
                    >
                      <SelectTrigger className={darkMode ? "border-gray-600 bg-gray-700 text-white" : ""}>
                        <SelectValue placeholder="Select region" />
                      </SelectTrigger>
                      <SelectContent>
                        {US_REGIONS.map((region) => (
                          <SelectItem key={region} value={region}>
                            {region}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <Button onClick={handleAddHospital} className="w-full bg-[#0566bb] hover:bg-[#05447b]">
                    Add Hospital
                  </Button>
                </CardContent>
              </Card>

              {/* Hospitals List */}
              <Card className={darkMode ? "lg:col-span-2 border-gray-700 bg-gray-800" : "lg:col-span-2 border-gray-200"}>
                <CardHeader>
                  <CardTitle className={`flex items-center gap-2 ${darkMode ? "text-white" : ""}`}>
                    <Building2 className="h-5 w-5 text-[#0566bb]" />
                    All Hospitals
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4 max-h-[600px] overflow-y-auto">
                    {hospitals.map((hospital) => (
                      <div
                        key={hospital.id}
                        className={`p-4 border rounded-lg ${darkMode ? "border-gray-600 bg-gray-700" : "border-gray-200"}`}
                      >
                        <h3 className={`font-semibold ${darkMode ? "text-white" : "text-gray-900"}`}>{hospital.name}</h3>
                        <p className={`text-sm ${darkMode ? "text-gray-300" : "text-gray-600"}`}>Region: {hospital.region}</p>
                        <p className={`text-xs mt-1 ${darkMode ? "text-gray-400" : "text-gray-500"}`}>
                          Doctors assigned: {doctors.filter((d) => d.hospital === hospital.name).length}
                        </p>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}
