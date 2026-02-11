import { useDropzone } from "react-dropzone";
import { UploadCloud, Camera, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useRef, useState } from "react";

interface FileUploadProps {
  onDrop: (files: File[], metadata?: Record<string, unknown>, tags?: string[]) => void;
  className?: string;
}

const VIEW_TAGS = ["Front", "Back", "Left", "Right"];

export default function FileUpload({ onDrop, className }: FileUploadProps) {
  const cameraInputRef = useRef<HTMLInputElement>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [pendingFiles, setPendingFiles] = useState<File[]>([]);
  const [description, setDescription] = useState("");
  // specific tags for each file index
  const [fileTags, setFileTags] = useState<string[]>([]);
  // Store object URLs for preview
  const [previews, setPreviews] = useState<string[]>([]);

  const handleInitialDrop = (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return;
    setPendingFiles(acceptedFiles);
    // Default tag "Front" for all
    setFileTags(new Array(acceptedFiles.length).fill("Front"));
    // Generate previews
    const urls = acceptedFiles.map(file => URL.createObjectURL(file));
    setPreviews(urls);
    setIsOpen(true);
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: handleInitialDrop,
    accept: {
      "image/*": [".png", ".jpg", ".jpeg", ".webp"],
    },
  });

  const handleCameraClick = (e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent dropzone click
    cameraInputRef.current?.click();
  };

  const handleCameraCapture = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleInitialDrop(Array.from(e.target.files));
    }
    // Reset input value to allow capturing the same file again if needed
    if (cameraInputRef.current) {
      cameraInputRef.current.value = "";
    }
  };

  const updateTag = (index: number, value: string) => {
    setFileTags(prev => {
      const next = [...prev];
      next[index] = value;
      return next;
    });
  };

  const handleConfirm = () => {
    // Cleanup previews
    previews.forEach(url => URL.revokeObjectURL(url));
    setPreviews([]);

    // Call parent with files, metadata, and tags
    onDrop(
      pendingFiles,
      { description }, // metadata
      fileTags // tags
    );

    setIsOpen(false);
    setPendingFiles([]);
    setDescription("");
    setFileTags([]);
  };

  const handleCancel = () => {
    previews.forEach(url => URL.revokeObjectURL(url));
    setPreviews([]);
    setPendingFiles([]);
    setIsOpen(false);
  };

  const removeFile = (index: number) => {
    const newFiles = [...pendingFiles];
    newFiles.splice(index, 1);

    const newTags = [...fileTags];
    newTags.splice(index, 1);

    const newPreviews = [...previews];
    URL.revokeObjectURL(newPreviews[index]);
    newPreviews.splice(index, 1);

    if (newFiles.length === 0) {
      handleCancel();
    } else {
      setPendingFiles(newFiles);
      setFileTags(newTags);
      setPreviews(newPreviews);
    }
  };

  return (
    <>
      <div className={cn("space-y-4", className)}>
        <div
          {...getRootProps()}
          className={cn(
            "border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors relative",
            isDragActive
              ? "border-primary bg-primary/5"
              : "border-border hover:border-primary/50 hover:bg-muted/50"
          )}
        >
          <input {...getInputProps()} />
          <div className="flex flex-col items-center justify-center gap-2">
            <div className="p-4 rounded-full bg-muted">
              <UploadCloud className="w-8 h-8 text-muted-foreground" />
            </div>
            <div className="space-y-1">
              <p className="text-sm font-medium">
                <span className="text-primary">Click to upload</span> or drag and drop
              </p>
              <p className="text-xs text-muted-foreground">
                SVG, PNG, JPG or GIF (max. 10MB)
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center justify-center w-full">
          <input
            type="file"
            accept="image/*"
            capture="environment"
            className="hidden"
            ref={cameraInputRef}
            onChange={handleCameraCapture}
          />
          <Button
            type="button"
            variant="secondary"
            className="w-full sm:w-auto gap-2 h-12 text-base shadow-sm border border-input"
            onClick={handleCameraClick}
          >
            <Camera className="w-5 h-5" />
            Take Photo from Mobile
          </Button>
        </div>
      </div>

      <Dialog open={isOpen} onOpenChange={(open) => !open && handleCancel()}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Upload Details</DialogTitle>
          </DialogHeader>

          <div className="space-y-6 py-4">
            <div className="space-y-2">
              <Label htmlFor="desc">Product Description <span className="text-destructive">*</span></Label>
              <Input
                id="desc"
                placeholder="Describe about the food type or anything extra you want the AI know..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>

            <div className="space-y-3">
              <Label>Selected Images ({pendingFiles.length})</Label>
              <div className="grid gap-4">
                {pendingFiles.map((file, idx) => (
                  <div key={idx} className="flex items-start gap-4 p-3 border rounded-lg bg-card text-card-foreground shadow-sm">
                    <img
                      src={previews[idx]}
                      alt="preview"
                      className="w-20 h-20 object-cover rounded-md border"
                    />
                    <div className="flex-1 space-y-2">
                      <div className="flex justify-between items-start">
                        <p className="text-sm font-medium truncate max-w-[200px]" title={file.name}>{file.name}</p>
                        <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => removeFile(idx)}>
                          <X className="h-4 w-4" />
                        </Button>
                      </div>

                      <div className="flex items-center gap-2">
                        <Label htmlFor={`tag-${idx}`} className="text-xs">View:</Label>
                        <Select
                          value={fileTags[idx]}
                          onValueChange={(val) => updateTag(idx, val)}
                        >
                          <SelectTrigger className="w-[120px] h-8 text-xs" id={`tag-${idx}`}>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {VIEW_TAGS.map(t => (
                              <SelectItem key={t} value={t}>{t}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={handleCancel}>Cancel</Button>
            <Button onClick={handleConfirm} disabled={!description.trim() || pendingFiles.length === 0}>
              Analyze
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
