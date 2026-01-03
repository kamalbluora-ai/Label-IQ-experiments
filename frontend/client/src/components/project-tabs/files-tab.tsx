import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, Project, ProjectFile } from "@/api";
import FileUpload from "@/components/file-upload";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Loader2, Trash2, FileImage, Tag as TagIcon } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

interface FilesTabProps {
  project: Project;
}

const STANDARD_TAGS = ["front", "back", "top", "bottom", "side"];

export default function FilesTab({ project }: FilesTabProps) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [uploadQueue, setUploadQueue] = useState<File[]>([]);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [customTag, setCustomTag] = useState("");
  const [isUploadDialogOpen, setIsUploadDialogOpen] = useState(false);

  const { data: files, isLoading } = useQuery({
    queryKey: ["files", project.id],
    queryFn: () => api.files.list(project.id),
  });

  const uploadMutation = useMutation({
    mutationFn: async () => {
      const tags = [...selectedTags];
      if (customTag) tags.push(customTag);

      // Upload all files as a single batch (one job)
      if (uploadQueue.length > 0) {
        await api.files.upload(project.id, uploadQueue, tags);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["files", project.id] });
      toast({ title: "Uploaded", description: `${uploadQueue.length} files uploaded successfully.` });
      setUploadQueue([]);
      setSelectedTags([]);
      setCustomTag("");
      setIsUploadDialogOpen(false);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: api.files.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["files", project.id] });
      toast({ title: "Deleted", description: "File deleted." });
    },
  });

  const handleDrop = (acceptedFiles: File[]) => {
    setUploadQueue(acceptedFiles);
    setIsUploadDialogOpen(true);
  };

  const toggleTag = (tag: string) => {
    setSelectedTags(prev =>
      prev.includes(tag) ? prev.filter(t => t !== tag) : [...prev, tag]
    );
  };

  return (
    <div className="space-y-8">
      <div className="grid gap-6">
        <Card>
          <CardContent className="pt-6">
            <FileUpload onDrop={handleDrop} />
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

      <Dialog open={isUploadDialogOpen} onOpenChange={(open) => !uploadMutation.isPending && setIsUploadDialogOpen(open)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Upload {uploadQueue.length} Files</DialogTitle>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Standard Tags</Label>
              <div className="flex flex-wrap gap-2">
                {STANDARD_TAGS.map(tag => (
                  <div key={tag} className="flex items-center space-x-2">
                    <Checkbox
                      id={`tag-${tag}`}
                      checked={selectedTags.includes(tag)}
                      onCheckedChange={() => toggleTag(tag)}
                    />
                    <label
                      htmlFor={`tag-${tag}`}
                      className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                    >
                      {tag}
                    </label>
                  </div>
                ))}
              </div>
            </div>

            <div className="space-y-2">
              <Label>Custom Tag</Label>
              <div className="flex gap-2">
                <Input
                  placeholder="e.g. crack-detection"
                  value={customTag}
                  onChange={(e) => setCustomTag(e.target.value)}
                />
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setIsUploadDialogOpen(false)}
              disabled={uploadMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              onClick={() => uploadMutation.mutate()}
              disabled={uploadMutation.isPending}
            >
              {uploadMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Confirm Upload
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
