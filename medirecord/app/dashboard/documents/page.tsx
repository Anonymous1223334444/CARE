"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Upload, Search, Filter, FileText, ImageIcon, File, Download, Eye, Trash2, Calendar, User } from "lucide-react"
import { getDocuments } from "@/lib/api"

interface Document {
  id: number
  original_filename: string
  file_type: string
  patient: { full_name: string }
  created_at: string
  file_size: number
  upload_status: string
  icon: any
  description?: string
  category?: string
}

export default function DocumentsPage() {
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null)
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadDocuments() {
      setLoading(true)
      const documentData = await getDocuments()
      const formattedDocuments = documentData.map((doc: any) => ({
        ...doc,
        icon: getIcon(doc.file_type),
      }));
      setDocuments(formattedDocuments)
      setLoading(false)
    }
    loadDocuments()
  }, [])

  const getIcon = (file_type: string) => {
    if (file_type.includes('pdf')) return FileText;
    if (file_type.includes('image') || file_type.includes('jpg') || file_type.includes('png')) return ImageIcon;
    return File;
  }

  const handleDocumentClick = (document: Document) => {
    setSelectedDocument(document)
  }

  const stats = {
    indexed: documents.filter(d => d.upload_status === 'indexed').length,
    processing: documents.filter(d => d.upload_status === 'processing' || d.upload_status === 'pending').length,
    errors: documents.filter(d => d.upload_status === 'failed').length,
  }

  return (
    <>
      <div className="space-y-6 p-4 lg:p-6">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl lg:text-3xl font-bold text-slate-900 dark:text-white">Documents médicaux</h1>
            <p className="text-slate-600 dark:text-slate-400">Gérez et indexez les documents de vos patients</p>
          </div>
          <Button className="gradient-bg text-slate-900 font-semibold hover:opacity-90">
            <Upload className="mr-2 h-4 w-4" />
            Télécharger document
          </Button>
        </div>

        <div className="flex flex-col lg:flex-row items-center space-y-4 lg:space-y-0 lg:space-x-4">
          <div className="relative flex-1 max-w-sm">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
            <Input placeholder="Rechercher un document..." className="pl-10" />
          </div>
          <Button variant="outline">
            <Filter className="mr-2 h-4 w-4" />
            Filtres
          </Button>
        </div>

        <Tabs defaultValue="all" className="space-y-4">
          <TabsList className="grid w-full grid-cols-2 lg:grid-cols-4">
            <TabsTrigger value="all">Tous les documents</TabsTrigger>
            <TabsTrigger value="ordonnances">Ordonnances</TabsTrigger>
            <TabsTrigger value="analyses">Analyses</TabsTrigger>
            <TabsTrigger value="imagerie">Imagerie</TabsTrigger>
          </TabsList>

          <TabsContent value="all" className="space-y-4">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2">
                <Card>
                  <CardHeader>
                    <CardTitle>Documents récents</CardTitle>
                    <CardDescription>Liste de tous vos documents médicaux</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {loading ? (
                        <p>Chargement...</p>
                      ) : (
                        documents.map((doc) => (
                          <div
                            key={doc.id}
                            className="flex flex-col lg:flex-row lg:items-center justify-between p-4 border rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors cursor-pointer"
                            onClick={() => handleDocumentClick(doc)}
                          >
                            <div className="flex items-center space-x-4 mb-4 lg:mb-0">
                              <div className="p-2 bg-blue-100 dark:bg-blue-900/20 rounded-lg flex-shrink-0">
                                <doc.icon className="h-6 w-6 text-blue-600" />
                              </div>
                              <div className="min-w-0 flex-1">
                                <h3 className="font-semibold truncate">{doc.original_filename}</h3>
                                <p className="text-sm text-muted-foreground flex items-center">
                                  <User className="h-3 w-3 mr-1 flex-shrink-0" />
                                  <span className="truncate">Patient: {doc.patient.full_name}</span>
                                </p>
                                <p className="text-sm text-muted-foreground flex items-center">
                                  <Calendar className="h-3 w-3 mr-1 flex-shrink-0" />
                                  <span>
                                    {new Date(doc.created_at).toLocaleDateString()} • {(doc.file_size / 1024 / 1024).toFixed(2)} MB
                                  </span>
                                </p>
                              </div>
                            </div>

                            <div className="flex flex-wrap items-center gap-4">
                              <Badge
                                variant={
                                  doc.upload_status === "indexed"
                                    ? "default"
                                    : doc.upload_status === "processing" || doc.upload_status === "pending"
                                      ? "secondary"
                                      : "destructive"
                                }
                              >
                                {doc.upload_status}
                              </Badge>

                              <div className="flex items-center space-x-2">
                                <Button variant="ghost" size="icon" onClick={(e) => e.stopPropagation()}>
                                  <Eye className="h-4 w-4" />
                                </Button>
                                <Button variant="ghost" size="icon" onClick={(e) => e.stopPropagation()}>
                                  <Download className="h-4 w-4" />
                                </Button>
                                <Button variant="ghost" size="icon" onClick={(e) => e.stopPropagation()}>
                                  <Trash2 className="h-4 w-4" />
                                </Button>
                              </div>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </CardContent>
                </Card>
              </div>

              <div className="space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle>Statistiques</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="text-center p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
                      <div className="text-2xl font-bold text-green-600">{stats.indexed}</div>
                      <div className="text-sm text-muted-foreground">Documents indexés</div>
                    </div>
                    <div className="text-center p-4 bg-orange-50 dark:bg-orange-900/20 rounded-lg">
                      <div className="text-2xl font-bold text-orange-600">{stats.processing}</div>
                      <div className="text-sm text-muted-foreground">En cours d'indexation</div>
                    </div>
                    <div className="text-center p-4 bg-red-50 dark:bg-red-900/20 rounded-lg">
                      <div className="text-2xl font-bold text-red-600">{stats.errors}</div>
                      <div className="text-sm text-muted-foreground">Erreurs</div>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>Actions rapides</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <Button variant="outline" className="w-full justify-start">
                      <Upload className="mr-2 h-4 w-4" />
                      Télécharger document
                    </Button>
                    <Button variant="outline" className="w-full justify-start">
                      <FileText className="mr-2 h-4 w-4" />
                      Créer ordonnance
                    </Button>
                    <Button variant="outline" className="w-full justify-start">
                      <Search className="mr-2 h-4 w-4" />
                      Recherche avancée
                    </Button>
                  </CardContent>
                </Card>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="ordonnances">
            <Card>
              <CardHeader>
                <CardTitle>Ordonnances</CardTitle>
                <CardDescription>Toutes les ordonnances de vos patients</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground">Contenu des ordonnances à venir...</p>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="analyses">
            <Card>
              <CardHeader>
                <CardTitle>Analyses médicales</CardTitle>
                <CardDescription>Résultats d'analyses et examens</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground">Contenu des analyses à venir...</p>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="imagerie">
            <Card>
              <CardHeader>
                <CardTitle>Imagerie médicale</CardTitle>
                <CardDescription>Radiographies, scanners, IRM</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground">Contenu de l'imagerie à venir...</p>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>

      {/* Document Details Dialog */}
      <Dialog open={!!selectedDocument} onOpenChange={() => setSelectedDocument(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center space-x-3">
              <div className="p-2 bg-blue-100 dark:bg-blue-900/20 rounded-lg">
                {selectedDocument?.icon && <selectedDocument.icon className="h-6 w-6 text-blue-600" />}
              </div>
              <div>
                <h2 className="text-xl font-bold">{selectedDocument?.original_filename}</h2>
                <p className="text-sm text-muted-foreground">{selectedDocument?.file_type}</p>
              </div>
            </DialogTitle>
            <DialogDescription>Détails du document médical</DialogDescription>
          </DialogHeader>

          {selectedDocument && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Informations</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center space-x-2">
                    <User className="h-4 w-4 text-muted-foreground" />
                    <span>{selectedDocument.patient.full_name}</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Calendar className="h-4 w-4 text-muted-foreground" />
                    <span>{new Date(selectedDocument.created_at).toLocaleDateString()}</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <File className="h-4 w-4 text-muted-foreground" />
                    <span>{(selectedDocument.file_size / 1024 / 1024).toFixed(2)} MB</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="text-sm">Catégorie:</span>
                    <Badge variant="outline">{selectedDocument.category}</Badge>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Description</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm">{selectedDocument.description}</p>
                </CardContent>
              </Card>

              <Card className="md:col-span-2">
                <CardHeader>
                  <CardTitle className="text-lg">Actions</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2">
                    <Button variant="outline" size="sm">
                      <Eye className="mr-2 h-4 w-4" />
                      Visualiser
                    </Button>
                    <Button variant="outline" size="sm">
                      <Download className="mr-2 h-4 w-4" />
                      Télécharger
                    </Button>
                    <Button variant="outline" size="sm">
                      <FileText className="mr-2 h-4 w-4" />
                      Partager
                    </Button>
                    <Button variant="outline" size="sm">
                      <Trash2 className="mr-2 h-4 w-4" />
                      Supprimer
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  )
}
