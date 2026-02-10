import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, Project } from "@/api";
import FileUpload from "@/components/file-upload";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Loader2, Trash2, FileImage } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

interface FilesTabProps {
  project: Project;
  onTabSwitch: (tab: string) => void;
}

export default function FilesTab({ project, onTabSwitch }: FilesTabProps) {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // Query for listing files
  const { data: files, isLoading } = useQuery({
    queryKey: ["files", project.id],
    queryFn: () => api.files.list(project.id),
  });

  // Mutation for uploading
  const uploadMutation = useMutation({
    mutationFn: async ({ files, metadata, tags }: { files: File[], metadata: Record<string, unknown>, tags: string[] }) => {
      await api.files.upload(project.id, files, tags, metadata);
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["files", project.id] });
      queryClient.invalidateQueries({ queryKey: ["analyses", project.id] });
      onTabSwitch("analysis");
      toast({
        title: "Uploaded",
        description: `${variables.files.length} files uploaded successfully.`
      });
    },
    onError: (error) => {
      toast({
        title: "Upload Failed",
        description: error instanceof Error ? error.message : "Unknown error",
        variant: "destructive"
      });
    }
  });

  const deleteMutation = useMutation({
    mutationFn: api.files.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["files", project.id] });
      toast({ title: "Deleted", description: "File deleted." });
    },
  });

  // Handle the drop event from FileUpload component
  // Now receives metadata and tags directly from the FileUpload's internal dialog
  const handleDrop = (files: File[], metadata?: Record<string, unknown>, tags?: string[]) => {
    if (files.length === 0) return;

    uploadMutation.mutate({
      files,
      metadata: metadata || {},
      tags: tags || []
    });
  };

  return (
    <div className="space-y-8">
      <div className="grid gap-6">
        <Card>
          <CardContent className="pt-6">
            <FileUpload onDrop={handleDrop} />
            {uploadMutation.isPending && (
              <div className="mt-4 flex items-center justify-center text-sm text-muted-foreground">
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Uploading and analyzing...
              </div>
            )}
          </CardContent>
        </Card>

        {isLoading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
          </div>
        ) : files?.length === 0 ? (
          <div className="text-center py-12 text-muted-foreground">
            No files uploaded yet.
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
            {files?.map((file) => (
              <div key={file.id} className="group relative aspect-square bg-muted rounded-lg overflow-hidden border border-border">
                {file.type === "image" ? (
                  <img src={file.url} alt={file.name} className="w-full h-full object-cover" />
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <FileImage className="w-12 h-12 text-muted-foreground/50" />
                  </div>
                )}

                <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col justify-between p-3">
                  <div className="flex justify-end">
                    <Button
                      variant="destructive"
                      size="icon"
                      className="h-8 w-8"
                      onClick={() => deleteMutation.mutate(file.id)}
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                  <div className="space-y-1">
                    <p className="text-xs text-white truncate font-medium">{file.name}</p>
                    <div className="flex flex-wrap gap-1">
                      {file.tags.map(tag => (
                        <span key={tag} className="text-[10px] bg-primary/80 text-white px-1.5 py-0.5 rounded">
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
