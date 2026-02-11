import Layout from "@/components/layout";
import FilesTab from "@/components/project-tabs/files-tab";
import AnalysisTab from "@/components/project-tabs/analysis-tab";
import ReportsTab from "@/components/project-tabs/reports-tab";
import EditProjectDialog from "@/components/edit-project-dialog";
import { api } from "@/api";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRoute } from "wouter";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Loader2, ArrowLeft } from "lucide-react";
import { Link } from "wouter";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { useState } from "react";
import NotFound from "./not-found";

export default function ProjectView() {
  const [match, params] = useRoute("/project/:id");
  const id = params?.id;
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [activeTab, setActiveTab] = useState("files");

  const { data: project, isLoading } = useQuery({
    queryKey: ["project", id],
    queryFn: () => api.projects.get(id!),
    enabled: !!id,
  });

  const updateMutation = useMutation({
    mutationFn: (data: { name: string; description?: string; tags: string[] }) =>
      api.projects.update(id!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project", id] });
      toast({ title: "Success", description: "Project updated successfully" });
    },
  });

  if (isLoading) {
    return (
      <Layout>
        <div className="flex h-[50vh] items-center justify-center">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      </Layout>
    );
  }

  if (!project) {
    return <NotFound />;
  }

  return (
    <Layout>
      <div className="space-y-8">
        {/* Header */}
        <div className="flex flex-col gap-4">
          <Link href="/dashboard">
            <Button variant="ghost" size="sm" className="self-start -ml-2 text-muted-foreground">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Dashboard
            </Button>
          </Link>

          <div className="flex flex-col md:flex-row justify-between md:items-start gap-4">
            <div className="space-y-2 flex-1">
              <div className="flex items-center gap-2">
                <h1 className="text-3xl font-bold tracking-tight">{project.name}</h1>
                <EditProjectDialog project={project} onEdit={(data) => updateMutation.mutate(data)} />
              </div>
              <p className="text-muted-foreground max-w-2xl">{project.description}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              {project.tags.map((tag) => (
                <Badge key={tag} variant="outline" className="text-sm">
                  {tag}
                </Badge>
              ))}
            </div>
          </div>
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="w-full justify-start h-12 p-1 bg-muted/50">
            <TabsTrigger value="files" className="px-6">Files & Uploads</TabsTrigger>
            <TabsTrigger value="analysis" className="px-6">Analysis</TabsTrigger>
            <TabsTrigger value="reports" className="px-6">Final Reports</TabsTrigger>
          </TabsList>

          <TabsContent value="files">
            <FilesTab project={project} onTabSwitch={setActiveTab} />
          </TabsContent>

          <TabsContent value="analysis">
            <AnalysisTab project={project} onTabSwitch={setActiveTab} />
          </TabsContent>

          <TabsContent value="reports">
            <ReportsTab project={project} />
          </TabsContent>
        </Tabs>
      </div>
    </Layout>
  );
}
