import { useDropzone } from "react-dropzone";
import { UploadCloud, Camera } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { useRef } from "react";

interface FileUploadProps {
  onDrop: (files: File[]) => void;
  className?: string;
}

export default function FileUpload({ onDrop, className }: FileUploadProps) {
  const cameraInputRef = useRef<HTMLInputElement>(null);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
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
      onDrop(Array.from(e.target.files));
    }
    // Reset input value to allow capturing the same file again if needed
    if (cameraInputRef.current) {
      cameraInputRef.current.value = "";
    }
  };

  return (
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
  );
}
