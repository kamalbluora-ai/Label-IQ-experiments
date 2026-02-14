import Layout from "@/components/layout";
import ProjectCard from "@/components/project-card";
import CreateProjectDialog from "@/components/create-project-dialog";
import { api } from "@/api";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useToast } from "@/hooks/use-toast";
import { Loader2, Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { useState } from "react";

export default function Dashboard() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");

  const { data: projects, isLoading } = useQuery({
    queryKey: ["projects"],
    queryFn: api.projects.list,
  });

  const createMutation = useMutation({
    mutationFn: api.projects.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      toast({ title: "Success", description: "Project created successfully" });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: api.projects.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      toast({ title: "Deleted", description: "Project deleted successfully" });
    },
  });

  const filteredProjects = projects?.filter(p =>
    p.name.toLowerCase().includes(search.toLowerCase()) ||
    p.tags.some(t => t.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <Layout>
      <div className="space-y-8">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
            <p className="text-muted-foreground mt-1">
              Manage your food label projects.
            </p>
          </div>
          <CreateProjectDialog onCreate={(data) => createMutation.mutate(data)} />
        </div>

        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground w-4 h-4" />
          <Input
            placeholder="Search projects..."
            className="pl-9 bg-background/50"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        {isLoading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
          </div>
        ) : filteredProjects?.length === 0 ? (
          <div className="text-center py-12 border border-dashed rounded-lg bg-card/50">
            <p className="text-muted-foreground">No projects found. Create one to get started.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredProjects?.map((project) => (
              <ProjectCard
                key={project.id}
                project={project}
                onDelete={(id) => deleteMutation.mutate(id)}
              />
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}
