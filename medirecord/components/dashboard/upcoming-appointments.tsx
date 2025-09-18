"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Clock, User, Plus, Calendar, Phone } from "lucide-react"
import { useRouter } from "next/navigation"
import { useEffect, useState } from "react"
import { getSessionStats } from "@/lib/api"

interface Appointment {
  patient: string;
  time: string;
  type: string;
  status: string;
}

export default function UpcomingAppointments() {
  const router = useRouter()
  const [appointments, setAppointments] = useState<Appointment[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadUpcomingAppointments() {
      setLoading(true)
      // Assumption: Using most_active_patients as a stand-in for upcoming appointments
      // as there is no specific API endpoint for appointments.
      const sessionStats = await getSessionStats()
      const activePatients = sessionStats.most_active_patients || []

      const appointmentData = activePatients.map((patient: any) => ({
        patient: `${patient.session__patient__first_name} ${patient.session__patient__last_name}`,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        type: "Consultation",
        status: "Confirmé",
      }));

      setAppointments(appointmentData)
      setLoading(false)
    }
    loadUpcomingAppointments()
  }, [])

  const handleQuickAction = (action: string) => {
    switch (action) {
      case "new-appointment":
        router.push("/dashboard/appointments")
        break
      case "calendar":
        router.push("/dashboard/appointments")
        break
      case "reminders":
        // Logique pour les rappels automatiques
        console.log("Rappels automatiques activés")
        break
      default:
        break
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Rendez-vous à venir</CardTitle>
        <CardDescription>Vos prochains rendez-vous aujourd'hui</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {loading ? (
            <p>Chargement...</p>
          ) : (
            appointments.map((appointment, index) => (
              <div key={index} className="flex items-center justify-between p-3 border rounded-lg">
                <div className="flex items-center space-x-3">
                  <div className="flex items-center space-x-2 text-sm text-muted-foreground">
                    <Clock className="h-4 w-4" />
                    <span>{appointment.time}</span>
                  </div>
                  <div>
                    <div className="flex items-center space-x-2">
                      <User className="h-4 w-4" />
                      <span className="font-medium">{appointment.patient}</span>
                    </div>
                    <p className="text-sm text-muted-foreground">{appointment.type}</p>
                  </div>
                </div>
                <Badge
                  variant={
                    appointment.status === "Confirmé"
                      ? "default"
                      : appointment.status === "En attente"
                        ? "secondary"
                        : "destructive"
                  }
                >
                  {appointment.status}
                </Badge>
              </div>
            ))
          )}
        </div>

        {/* Actions rapides */}
        <div className="mt-6 space-y-2">
          <h4 className="text-sm font-medium text-muted-foreground">Actions rapides</h4>
          <div className="space-y-2">
            <Button
              variant="outline"
              size="sm"
              className="w-full justify-start"
              onClick={() => handleQuickAction("new-appointment")}
            >
              <Plus className="mr-2 h-4 w-4" />
              Nouveau rendez-vous
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="w-full justify-start"
              onClick={() => handleQuickAction("calendar")}
            >
              <Calendar className="mr-2 h-4 w-4" />
              Voir le calendrier
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="w-full justify-start"
              onClick={() => handleQuickAction("reminders")}
            >
              <Phone className="mr-2 h-4 w-4" />
              Rappels automatiques
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
