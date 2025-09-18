"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Users, Calendar, MessageSquare, TrendingUp } from "lucide-react";
import { useEffect, useState } from "react";
import { getPatientStats, getSessionStats, getMetricsDashboard } from "@/lib/api";

export default function Overview() {
  const [stats, setStats] = useState([
    {
      title: "Total Patients",
      value: "Loading...",
      description: "",
      icon: Users,
      color: "text-blue-600",
    },
    {
      title: "Rendez-vous aujourd'hui",
      value: "Loading...",
      description: "",
      icon: Calendar,
      color: "text-green-600",
    },
    {
      title: "Messages WhatsApp",
      value: "Loading...",
      description: "",
      icon: MessageSquare,
      color: "text-purple-600",
    },
    {
      title: "Taux de satisfaction",
      value: "Loading...",
      description: "",
      icon: TrendingUp,
      color: "text-orange-600",
    },
  ]);

  useEffect(() => {
    async function fetchData() {
      const patientStats = await getPatientStats();
      const sessionStats = await getSessionStats();
      const metrics = await getMetricsDashboard();

      setStats([
        {
          title: "Total Patients",
          value: patientStats.total_count.toString(),
          description: "",
          icon: Users,
          color: "text-blue-600",
        },
        {
          title: "Rendez-vous aujourd'hui",
          value: sessionStats.conversations_24h?.toString() || "0",
          description: "dans les dernières 24h",
          icon: Calendar,
          color: "text-green-600",
        },
        {
          title: "Messages WhatsApp",
          value: sessionStats.total_sessions?.toString() || "0",
          description: "total",
          icon: MessageSquare,
          color: "text-purple-600",
        },
        {
          title: "Taux de satisfaction",
          value: `${metrics.delivery_success_rate?.toString() || "0"}%`,
          description: "livraison des messages",
          icon: TrendingUp,
          color: "text-orange-600",
        },
      ]);
    }

    fetchData();
  }, []);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {stats.map((stat, index) => (
        <Card key={index}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">{stat.title}</CardTitle>
            <stat.icon className={`h-4 w-4 ${stat.color}`} />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stat.value}</div>
            <p className="text-xs text-muted-foreground">{stat.description}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
