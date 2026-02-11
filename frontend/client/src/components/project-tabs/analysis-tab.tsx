import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, Project, Analysis } from "@/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Play, Loader2, CheckCircle2, AlertCircle, BarChart3, RefreshCw } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { useEffect } from "react";

interface AnalysisTabProps {
  project: Project;
  onTabSwitch: (tab: string) => void;
}

export default function AnalysisTab({ project, onTabSwitch }: AnalysisTabProps) {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const { data: analyses, isLoading } = useQuery({
    queryKey: ["analyses", project.id],
    queryFn: () => api.analysis.list(project.id),
    refetchInterval: (query) => {
      const data = query.state.data as Analysis[] | undefined;
      if (!data || data.length === 0) return 2000; // Keep polling if no data yet
      const allDone = data.every(a => a.status === "completed" || a.status === "failed");
      return allDone ? false : 2000;
    },
  });

  // Auto-switch to reports when all analyses are complete
  useEffect(() => {
    if (!analyses || analyses.length === 0) return;
    const allDone = analyses.every(a => a.status === "completed" || a.status === "failed");
    if (allDone) {
      onTabSwitch("reports");
    }
  }, [analyses, onTabSwitch]);

  const runMutation = useMutation({
    mutationFn: () => {
      // Generate a sequential name based on existing analyses count
      const nextNumber = (analyses?.length || 0) + 1;
      return api.analysis.run(project.id, `Food Labelling Analysis #${nextNumber}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["analyses", project.id] });
      toast({ title: "Analysis Started", description: "The analysis is running in the background." });
    },
  });

  const getStatusIcon = (status: Analysis["status"]) => {
    switch (status) {
      case "completed": return <CheckCircle2 className="w-5 h-5 text-green-500" />;
      case "failed": return <AlertCircle className="w-5 h-5 text-destructive" />;
      case "running": return <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />;
      default: return <div className="w-5 h-5 rounded-full border-2 border-muted" />;
    }
  };

  return (
    <div className="space-y-8">
      <Card>
        <CardHeader>
          <CardTitle>Run Analysis</CardTitle>
          <CardDescription>Start the AI analysis on the uploaded project files. You can run multiple analyses concurrently.</CardDescription>
        </CardHeader>
        <CardContent>
          <Button
            onClick={() => runMutation.mutate()}
            disabled={runMutation.isPending}
            className="w-full sm:w-auto"
          >
            {runMutation.isPending ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Play className="w-4 h-4 mr-2" />}
            {runMutation.isPending ? "Starting..." : "Start New Analysis"}
          </Button>
        </CardContent>
      </Card>

      <div className="space-y-4">
        <h3 className="text-lg font-semibold flex items-center gap-2">
          <BarChart3 className="w-5 h-5" />
          Analysis History
        </h3>

        {isLoading ? (
          <div className="flex justify-center py-8">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
          </div>
        ) : analyses?.length === 0 ? (
          <div className="text-center py-12 border border-dashed rounded-lg">
            <p className="text-muted-foreground">No analyses run yet.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {analyses?.map((analysis) => (
              <Card key={analysis.id}>
                <CardContent className="p-4 flex items-center gap-4">
                  <div className="shrink-0">
                    {getStatusIcon(analysis.status)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex justify-between mb-1">
                      <h4 className="font-medium truncate">{analysis.name}</h4>
                      <span className="text-xs text-muted-foreground uppercase font-bold flex items-center gap-2">
                        {analysis.status}
                      </span>
                    </div>
                    <div className="flex items-center gap-4">
                      <Progress value={analysis.progress} className="h-2" />
                      <span className="text-xs w-10 text-right">{analysis.progress}%</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
