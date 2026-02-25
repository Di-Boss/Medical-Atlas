"use client"
import { useState, useMemo } from "react"
import Image from "next/image"
import Link from "next/link"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { ChevronLeft, HelpCircle, Printer, Calendar, Moon, Sun } from "lucide-react"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Calendar as CalendarComponent } from "@/components/ui/calendar"
import { format } from "date-fns"
import { cn } from "@/lib/utils"

export default function PredictPage() {
  const [step, setStep] = useState(1)
  const [formData, setFormData] = useState({
    ssn: "",
    gender: "",
    weight: "",
    age: "",
    admission_date: undefined as Date | undefined,
    pathogen: "",
    antibiotic: "",
    cancerType: "",
    duration: "",
    region: "",
  })

  const [errors, setErrors] = useState({
    weight: "",
    age: "",
    ssn: "",
  })

  const [isLoading, setIsLoading] = useState(false)
  const [prediction, setPrediction] = useState<{
    resistant: number
    probability?: number
  } | null>(null)
  const [error, setError] = useState("")
  const [darkMode, setDarkMode] = useState(false)

  const validateSSN = (value: string) => {
    const digitsOnly = value.replace(/\D/g, "")
    if (digitsOnly.length !== 9) {
      setErrors((prev) => ({ ...prev, ssn: "SSN must be 9 digits (XXX-XX-XXXX)" }))
      return false
    }
    const formatted = `${digitsOnly.slice(0, 3)}-${digitsOnly.slice(3, 5)}-${digitsOnly.slice(5, 9)}`
    setFormData((prev) => ({ ...prev, ssn: formatted }))
    setErrors((prev) => ({ ...prev, ssn: "" }))
    return true
  }

  const validateWeight = (value: string) => {
    const weight = Number.parseFloat(value)
    if (isNaN(weight) || weight < 1 || weight > 350) {
      setErrors((prev) => ({ ...prev, weight: "Weight must be between 1-350 kg" }))
      return false
    }
    if (weight > 300) {
      setErrors((prev) => ({ ...prev, weight: "Weight unrealistic — check again." }))
      return false
    }
    setErrors((prev) => ({ ...prev, weight: "" }))
    return true
  }

  const validateAge = (value: string) => {
    const age = Number.parseInt(value)
    if (isNaN(age) || age < 0 || age > 123) {
      setErrors((prev) => ({ ...prev, age: "Patient age must be realistic." }))
      return false
    }
    setErrors((prev) => ({ ...prev, age: "" }))
    return true
  }

  const isStep1Valid = useMemo(() => {
    const weightValid = formData.weight !== "" && !errors.weight
    const ageValid = formData.age !== "" && !errors.age
    const ssnValid = formData.ssn.trim() !== "" && !errors.ssn
    const admissionDateValid = formData.admission_date !== undefined
    return ssnValid && formData.gender !== "" && weightValid && ageValid && admissionDateValid
  }, [
    formData.ssn,
    formData.gender,
    formData.weight,
    formData.age,
    formData.admission_date,
    errors.weight,
    errors.age,
    errors.ssn,
  ])

  const isStep2Valid = useMemo(() => {
    return (
      formData.pathogen !== "" &&
      formData.antibiotic !== "" &&
      formData.cancerType !== "" &&
      formData.duration !== "" &&
      Number.parseInt(formData.duration) > 0 &&
      formData.region !== ""
    )
  }, [formData.pathogen, formData.antibiotic, formData.cancerType, formData.duration, formData.region])

  const handleStep1Next = () => {
    if (isStep1Valid) {
      setStep(2)
    }
  }

  const handleStep2Submit = async () => {
    if (!isStep2Valid) return

    setIsLoading(true)
    setError("")
    setPrediction(null)

    try {
      const response = await fetch("/api/predict", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          age: Number(formData.age),
          weight_kg: Number(formData.weight),
          gender: formData.gender, // Send "Male" or "Female" as is
          admission_date: formData.admission_date ? format(formData.admission_date, "yyyy-MM-dd") : "",
          cancer_type: formData.cancerType, // Send cancer type as is (e.g., "Lung")
          pathogen_id: Number(formData.pathogen),
          antibiotic_id: Number(formData.antibiotic),
          duration_days: Number(formData.duration),
          region: formData.region,
        }),
      })

      if (!response.ok) {
        throw new Error("Prediction failed")
      }

      const result = await response.json()
      console.log("[v0] API Response:", result)
      console.log("[v0] Resistant value:", result.resistant)
      console.log("[v0] Probability value:", result.probability)
      setPrediction(result)
      setStep(3)
    } catch (err) {
      setError("Failed to get prediction. Please try again.")
    } finally {
      setIsLoading(false)
    }
  }

  const handlePrint = () => {
    window.print()
  }

  return (
    <div className={`min-h-screen pb-20 ${darkMode ? "bg-gray-900" : "bg-white"}`}>
      <header className={`px-8 py-4 flex items-center justify-between print:hidden ${darkMode ? "border-b border-gray-700" : ""}`}>
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

      <div className="max-w-4xl mx-auto px-8 py-6">
        <Card className={darkMode ? "border-gray-700 bg-gray-800 shadow-sm" : "border-gray-200 shadow-sm"}>
          <CardHeader className="px-8 pt-8 pb-4">
            <h1 className={`text-4xl font-bold text-left ${darkMode ? "text-white" : "text-black"}`}>
              {step === 3 ? "Prediction Results" : "Antibiotic Resistance Prediction"}
            </h1>
            <p className={`text-sm mt-2 ${darkMode ? "text-gray-400" : "text-gray-500"}`}>Step {step} of 3</p>
          </CardHeader>
          <CardContent className="px-8 pb-8">
            <TooltipProvider>
              {step === 1 && (
                <div className="space-y-6">
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <Label htmlFor="ssn" className={darkMode ? "text-gray-300" : "text-gray-700"}>
                        SSN
                      </Label>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <HelpCircle className="h-4 w-4 text-gray-400 cursor-help" />
                        </TooltipTrigger>
                        <TooltipContent>
                          <p>Patient's Social Security Number (paste only, format: XXX-XX-XXXX)</p>
                        </TooltipContent>
                      </Tooltip>
                    </div>
                    <Input
                      id="ssn"
                      type="text"
                      value={formData.ssn}
                      onKeyDown={(e) => {
                        if (
                          !e.ctrlKey &&
                          !e.metaKey &&
                          e.key !== "Tab" &&
                          e.key !== "Backspace" &&
                          e.key !== "Delete" &&
                          e.key !== "ArrowLeft" &&
                          e.key !== "ArrowRight"
                        ) {
                          e.preventDefault()
                        }
                      }}
                      onChange={(e) => {
                        e.preventDefault()
                      }}
                      onPaste={(e) => {
                        e.preventDefault()
                        const pastedText = e.clipboardData.getData("text")
                        validateSSN(pastedText)
                      }}
                      placeholder="XXX-XX-XXXX (paste only)"
                      className={darkMode ? "border-gray-600 bg-gray-700 text-white" : "border-gray-300"}
                      readOnly={false}
                    />
                    {errors.ssn && <p className="text-red-600 text-sm">{errors.ssn}</p>}
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <Label htmlFor="age" className={darkMode ? "text-gray-300" : "text-gray-700"}>
                        Age
                      </Label>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <HelpCircle className="h-4 w-4 text-gray-400 cursor-help" />
                        </TooltipTrigger>
                        <TooltipContent>
                          <p>Patient's age in years (0-123)</p>
                        </TooltipContent>
                      </Tooltip>
                    </div>
                    <Input
                      id="age"
                      type="number"
                      min="0"
                      max="123"
                      value={formData.age}
                      onChange={(e) => {
                        setFormData({ ...formData, age: e.target.value })
                        if (e.target.value) validateAge(e.target.value)
                      }}
                      placeholder="45"
                      className={darkMode ? "border-gray-600 bg-gray-700 text-white" : "border-gray-300"}
                    />
                    {errors.age && <p className="text-red-600 text-sm">{errors.age}</p>}
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <Label htmlFor="weight" className={darkMode ? "text-gray-300" : "text-gray-700"}>
                        Weight (kg)
                      </Label>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <HelpCircle className="h-4 w-4 text-gray-400 cursor-help" />
                        </TooltipTrigger>
                        <TooltipContent>
                          <p>Patient's weight in kilograms (1-350 kg)</p>
                        </TooltipContent>
                      </Tooltip>
                    </div>
                    <Input
                      id="weight"
                      type="number"
                      step="1"
                      min="1"
                      max="350"
                      value={formData.weight}
                      onChange={(e) => {
                        setFormData({ ...formData, weight: e.target.value })
                        if (e.target.value) validateWeight(e.target.value)
                      }}
                      placeholder="70"
                      className={darkMode ? "border-gray-600 bg-gray-700 text-white" : "border-gray-300"}
                    />
                    {errors.weight && <p className="text-red-600 text-sm">{errors.weight}</p>}
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <Label className={darkMode ? "text-gray-300" : "text-gray-700"}>Gender</Label>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <HelpCircle className="h-4 w-4 text-gray-400 cursor-help" />
                        </TooltipTrigger>
                        <TooltipContent>
                          <p>Patient's biological sex</p>
                        </TooltipContent>
                      </Tooltip>
                    </div>
                    <RadioGroup
                      value={formData.gender}
                      onValueChange={(value) => setFormData({ ...formData, gender: value })}
                      className="flex gap-6"
                    >
                      <div className="flex items-center space-x-2">
                        <RadioGroupItem value="Male" id="male" />
                        <Label htmlFor="male" className={`font-normal cursor-pointer ${darkMode ? "text-gray-300" : ""}`}>
                          Male
                        </Label>
                      </div>
                      <div className="flex items-center space-x-2">
                        <RadioGroupItem value="Female" id="female" />
                        <Label htmlFor="female" className={`font-normal cursor-pointer ${darkMode ? "text-gray-300" : ""}`}>
                          Female
                        </Label>
                      </div>
                    </RadioGroup>
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <Label htmlFor="admission_date" className={darkMode ? "text-gray-300" : "text-gray-700"}>
                        Admission Date
                      </Label>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <HelpCircle className="h-4 w-4 text-gray-400 cursor-help" />
                        </TooltipTrigger>
                        <TooltipContent>
                          <p>Date when the patient was admitted to the hospital</p>
                        </TooltipContent>
                      </Tooltip>
                    </div>
                    <Popover>
                      <PopoverTrigger asChild>
                        <Button
                          variant="outline"
                          className={cn(
                            "w-full justify-start text-left font-normal",
                            darkMode ? "border-gray-600 bg-gray-700 text-white" : "border-gray-300",
                            !formData.admission_date && "text-muted-foreground",
                          )}
                        >
                          <Calendar className="mr-2 h-4 w-4" />
                          {formData.admission_date ? format(formData.admission_date, "PPP") : "Pick a date"}
                        </Button>
                      </PopoverTrigger>
                      <PopoverContent className="w-auto p-0">
                        <CalendarComponent
                          mode="single"
                          selected={formData.admission_date}
                          onSelect={(date) => setFormData({ ...formData, admission_date: date })}
                          initialFocus
                        />
                      </PopoverContent>
                    </Popover>
                  </div>

                  <Button
                    onClick={handleStep1Next}
                    disabled={!isStep1Valid}
                    className={`w-full font-semibold py-6 text-lg ${
                      isStep1Valid
                        ? "bg-[#08c7cf] hover:bg-[#06a5ac] text-white"
                        : darkMode ? "bg-gray-600 text-gray-400 cursor-not-allowed" : "bg-gray-300 text-gray-500 cursor-not-allowed"
                    }`}
                  >
                    Next
                  </Button>
                </div>
              )}

              {step === 2 && (
                <div className="space-y-6">
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <Label htmlFor="cancerType" className={darkMode ? "text-gray-300" : "text-gray-700"}>
                        Cancer Type
                      </Label>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <HelpCircle className="h-4 w-4 text-gray-400 cursor-help" />
                        </TooltipTrigger>
                        <TooltipContent>
                          <p>Patient's cancer diagnosis</p>
                        </TooltipContent>
                      </Tooltip>
                    </div>
                    <Select
                      value={formData.cancerType}
                      onValueChange={(value) => setFormData({ ...formData, cancerType: value })}
                    >
                      <SelectTrigger className={darkMode ? "border-gray-600 bg-gray-700 text-white" : "border-gray-300"}>
                        <SelectValue placeholder="Select cancer type" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Leukemia">Leukemia</SelectItem>
                        <SelectItem value="Lymphoma">Lymphoma</SelectItem>
                        <SelectItem value="Breast">Breast Cancer</SelectItem>
                        <SelectItem value="Lung">Lung Cancer</SelectItem>
                        <SelectItem value="Colon">Colon Cancer</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <Label htmlFor="pathogen" className={darkMode ? "text-gray-300" : "text-gray-700"}>
                        Pathogen
                      </Label>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <HelpCircle className="h-4 w-4 text-gray-400 cursor-help" />
                        </TooltipTrigger>
                        <TooltipContent>
                          <p>The bacteria causing the infection</p>
                        </TooltipContent>
                      </Tooltip>
                    </div>
                    <Select
                      value={formData.pathogen}
                      onValueChange={(value) => setFormData({ ...formData, pathogen: value })}
                    >
                      <SelectTrigger className={darkMode ? "border-gray-600 bg-gray-700 text-white" : "border-gray-300"}>
                        <SelectValue placeholder="Select pathogen" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="1">E. coli</SelectItem>
                        <SelectItem value="2">Klebsiella pneumoniae</SelectItem>
                        <SelectItem value="3">Staphylococcus aureus</SelectItem>
                        <SelectItem value="4">Pseudomonas aeruginosa</SelectItem>
                        <SelectItem value="5">Enterococcus faecalis</SelectItem>
                        <SelectItem value="6">Acinetobacter baumannii</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <Label htmlFor="antibiotic" className={darkMode ? "text-gray-300" : "text-gray-700"}>
                        Antibiotic
                      </Label>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <HelpCircle className="h-4 w-4 text-gray-400 cursor-help" />
                        </TooltipTrigger>
                        <TooltipContent>
                          <p>The antibiotic being prescribed</p>
                        </TooltipContent>
                      </Tooltip>
                    </div>
                    <Select
                      value={formData.antibiotic}
                      onValueChange={(value) => setFormData({ ...formData, antibiotic: value })}
                    >
                      <SelectTrigger className={darkMode ? "border-gray-600 bg-gray-700 text-white" : "border-gray-300"}>
                        <SelectValue placeholder="Select antibiotic" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="1">Ceftriaxone</SelectItem>
                        <SelectItem value="2">Amoxicillin</SelectItem>
                        <SelectItem value="3">Levofloxacin</SelectItem>
                        <SelectItem value="4">Meropenem</SelectItem>
                        <SelectItem value="5">Vancomycin</SelectItem>
                        <SelectItem value="6">Piperacillin-Tazobactam</SelectItem>
                        <SelectItem value="7">Nitrofurantoin</SelectItem>
                        <SelectItem value="8">Ciprofloxacin</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <Label htmlFor="duration" className={darkMode ? "text-gray-300" : "text-gray-700"}>
                        Duration of Treatment (days)
                      </Label>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <HelpCircle className="h-4 w-4 text-gray-400 cursor-help" />
                        </TooltipTrigger>
                        <TooltipContent>
                          <p>Expected length of antibiotic treatment</p>
                        </TooltipContent>
                      </Tooltip>
                    </div>
                    <Input
                      id="duration"
                      type="number"
                      min="1"
                      value={formData.duration}
                      onChange={(e) => setFormData({ ...formData, duration: e.target.value })}
                      placeholder="7"
                      className={darkMode ? "border-gray-600 bg-gray-700 text-white" : "border-gray-300"}
                    />
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <Label htmlFor="region" className={darkMode ? "text-gray-300" : "text-gray-700"}>
                        Region
                      </Label>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <HelpCircle className="h-4 w-4 text-gray-400 cursor-help" />
                        </TooltipTrigger>
                        <TooltipContent>
                          <p>Geographic region where the patient is being treated</p>
                        </TooltipContent>
                      </Tooltip>
                    </div>
                    <Select
                      value={formData.region}
                      onValueChange={(value) => setFormData({ ...formData, region: value })}
                    >
                      <SelectTrigger className={darkMode ? "border-gray-600 bg-gray-700 text-white" : "border-gray-300"}>
                        <SelectValue placeholder="Select region" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="California">California</SelectItem>
                        <SelectItem value="Texas">Texas</SelectItem>
                        <SelectItem value="Florida">Florida</SelectItem>
                        <SelectItem value="New York">New York</SelectItem>
                        <SelectItem value="Pennsylvania">Pennsylvania</SelectItem>
                        <SelectItem value="Illinois">Illinois</SelectItem>
                        <SelectItem value="Ohio">Ohio</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  {error && <div className="text-red-600 text-sm">{error}</div>}

                  <div className="flex gap-4">
                    <Button
                      onClick={() => setStep(1)}
                      variant="outline"
                      className={`flex-1 font-semibold py-6 text-lg ${darkMode ? "border-gray-600 text-gray-300 hover:bg-gray-700" : ""}`}
                    >
                      Back
                    </Button>
                    <Button
                      onClick={handleStep2Submit}
                      disabled={!isStep2Valid || isLoading}
                      className={`flex-1 font-semibold py-6 text-lg ${
                        isStep2Valid && !isLoading
                          ? "bg-[#08c7cf] hover:bg-[#06a5ac] text-white"
                          : darkMode ? "bg-gray-600 text-gray-400 cursor-not-allowed" : "bg-gray-300 text-gray-500 cursor-not-allowed"
                      }`}
                    >
                      {isLoading ? "Predicting..." : "Predict"}
                    </Button>
                  </div>
                </div>
              )}

              {step === 3 && prediction && (
                <div className="space-y-6">
                  <div
                    className={`p-8 rounded-lg border-2 ${
                      prediction.resistant === 1
                        ? darkMode ? "bg-red-950/50 border-red-500" : "bg-red-50 border-red-500"
                        : darkMode ? "bg-green-950/50 border-green-500" : "bg-green-50 border-green-500"
                    }`}
                  >
                    <div className="flex items-center gap-3 mb-4">
                      <div
                        className={`w-6 h-6 rounded-full ${prediction.resistant === 1 ? "bg-red-500" : "bg-green-500"}`}
                      />
                      <p className={`text-2xl font-bold ${darkMode ? "text-white" : "text-gray-900"}`}>
                        {prediction.resistant === 1 ? "Probably Resistant" : "Probably Not Resistant"}
                      </p>
                    </div>
                    {prediction.probability && (
                      <p className={`text-lg ${darkMode ? "text-gray-300" : "text-gray-700"}`}>
                        Confidence: {(prediction.probability * 100).toFixed(1)}%
                      </p>
                    )}
                  </div>

                  <div className={darkMode ? "bg-gray-700 p-6 rounded-lg space-y-2" : "bg-gray-50 p-6 rounded-lg space-y-2"}>
                    <h3 className={`font-semibold text-lg mb-3 ${darkMode ? "text-white" : ""}`}>Patient Information</h3>
                    <p className={darkMode ? "text-gray-300" : "text-gray-700"}>
                      <span className="font-medium">SSN:</span> {formData.ssn}
                    </p>
                    <p className="text-gray-700">
                      <span className="font-medium">Gender:</span> {formData.gender}
                    </p>
                    <p className={darkMode ? "text-gray-300" : "text-gray-700"}>
                      <span className="font-medium">Age:</span> {formData.age} years
                    </p>
                    <p className={darkMode ? "text-gray-300" : "text-gray-700"}>
                      <span className="font-medium">Weight:</span> {formData.weight} kg
                    </p>
                    <p className={darkMode ? "text-gray-300" : "text-gray-700"}>
                      <span className="font-medium">Cancer Type:</span> {formData.cancerType}
                    </p>
                    <p className={darkMode ? "text-gray-300" : "text-gray-700"}>
                      <span className="font-medium">Treatment Duration:</span> {formData.duration} days
                    </p>
                    <p className={darkMode ? "text-gray-300" : "text-gray-700"}>
                      <span className="font-medium">Admission Date:</span>{" "}
                      {formData.admission_date ? format(formData.admission_date, "PPP") : "Not specified"}
                    </p>
                    <p className={darkMode ? "text-gray-300" : "text-gray-700"}>
                      <span className="font-medium">Region:</span> {formData.region}
                    </p>
                  </div>

                  <div className="flex gap-4 print:hidden">
                    <Button
                      onClick={() => {
                        setStep(1)
                        setPrediction(null)
                        setFormData({
                          ssn: "",
                          gender: "",
                          weight: "",
                          age: "",
                          admission_date: undefined,
                          pathogen: "",
                          antibiotic: "",
                          cancerType: "",
                          duration: "",
                          region: "",
                        })
                      }}
                      variant="outline"
                      className={`flex-1 font-semibold py-6 text-lg ${darkMode ? "border-gray-600 text-gray-300 hover:bg-gray-700" : ""}`}
                    >
                      New Prediction
                    </Button>
                    <Button
                      onClick={handlePrint}
                      className="flex-1 bg-[#0566bb] hover:bg-[#05447b] text-white font-semibold py-6 text-lg"
                    >
                      <Printer className="mr-2 h-5 w-5" />
                      Print Results
                    </Button>
                  </div>
                </div>
              )}
            </TooltipProvider>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
