import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { useState } from "react";
import { FeedbackItem } from "@/hooks/useFeedback";

interface FeedbackDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    questionId: string;
    section: string;
    question: string;
    currentResult: string;
    onSave: (feedback: FeedbackItem) => void;
    existingFeedback?: FeedbackItem;
}

export default function FeedbackDialog({
    open,
    onOpenChange,
    questionId,
    section,
    question,
    currentResult,
    onSave,
    existingFeedback,
}: FeedbackDialogProps) {
    const [comment, setComment] = useState(existingFeedback?.user_comment || "");
    const [suggestedResult, setSuggestedResult] = useState<"pass" | "fail" | null>(
        existingFeedback?.suggested_result || null
    );

    const handleSave = () => {
        if (!comment.trim()) return;

        onSave({
            question_id: questionId,
            question: question,
            section,
            original_result: currentResult,
            user_comment: comment.trim(),
            suggested_result: suggestedResult,
        });

        onOpenChange(false);
    };

    const handleCancel = () => {
        setComment(existingFeedback?.user_comment || "");
        setSuggestedResult(existingFeedback?.suggested_result || null);
        onOpenChange(false);
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[600px]">
                <DialogHeader>
                    <DialogTitle>Add Feedback for {questionId}</DialogTitle>
                    <DialogDescription>
                        Provide expert feedback to help re-evaluate this compliance question.
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-4 py-4">
                    <div className="space-y-2">
                        <Label className="text-sm font-medium">Question</Label>
                        <p className="text-sm text-muted-foreground">{question}</p>
                    </div>

                    <div className="space-y-2">
                        <Label className="text-sm font-medium">Current Result</Label>
                        <div className="inline-flex">
                            <span className={`px-2 py-1 rounded text-xs font-medium ${currentResult === "pass" ? "bg-green-100 text-green-800" :
                                currentResult === "fail" ? "bg-red-100 text-red-800" :
                                    "bg-yellow-100 text-yellow-800"
                                }`}>
                                {currentResult.replace("_", " ").toUpperCase()}
                            </span>
                        </div>
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="comment">Your Comment *</Label>
                        <Textarea
                            id="comment"
                            placeholder="e.g., Measured with ruler - font is 2mm, meets 1.6mm minimum requirement"
                            value={comment}
                            onChange={(e) => setComment(e.target.value)}
                            rows={4}
                            className="resize-none"
                        />
                        <p className="text-xs text-muted-foreground">
                            Provide additional context or measurements not visible in the extracted data.
                        </p>
                    </div>

                    <div className="space-y-2">
                        <Label>Suggested Result (optional)</Label>
                        <RadioGroup
                            value={suggestedResult || "ai_decide"}
                            onValueChange={(value) =>
                                setSuggestedResult(value === "ai_decide" ? null : value as "pass" | "fail")
                            }
                        >
                            <div className="flex items-center space-x-2">
                                <RadioGroupItem value="pass" id="pass" />
                                <Label htmlFor="pass" className="font-normal cursor-pointer">
                                    Pass
                                </Label>
                            </div>
                            <div className="flex items-center space-x-2">
                                <RadioGroupItem value="fail" id="fail" />
                                <Label htmlFor="fail" className="font-normal cursor-pointer">
                                    Fail
                                </Label>
                            </div>
                            <div className="flex items-center space-x-2">
                                <RadioGroupItem value="ai_decide" id="ai_decide" />
                                <Label htmlFor="ai_decide" className="font-normal cursor-pointer">
                                    Let AI decide based on my comment
                                </Label>
                            </div>
                        </RadioGroup>
                    </div>
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={handleCancel}>
                        Cancel
                    </Button>
                    <Button onClick={handleSave} disabled={!comment.trim()}>
                        Save Comment
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
