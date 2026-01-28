import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { MessageSquare, X, Send } from "lucide-react";

interface FeedbackSubmitBarProps {
    feedbackCount: number;
    isSubmitting: boolean;
    onClearAll: () => void;
    onSubmit: () => void;
}

export default function FeedbackSubmitBar({
    feedbackCount,
    isSubmitting,
    onClearAll,
    onSubmit,
}: FeedbackSubmitBarProps) {
    if (feedbackCount === 0) return null;

    return (
        <Card className="fixed top-20 left-1/2 -translate-x-1/2 z-50 shadow-lg border-2 border-primary/20">
            <div className="flex items-center gap-4 px-6 py-3">
                <div className="flex items-center gap-2">
                    <MessageSquare className="w-5 h-5 text-primary" />
                    <span className="font-medium">
                        {feedbackCount} comment{feedbackCount !== 1 ? "s" : ""} pending
                    </span>
                </div>

                <div className="flex items-center gap-2">
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={onClearAll}
                        disabled={isSubmitting}
                    >
                        <X className="w-4 h-4 mr-2" />
                        Clear All
                    </Button>

                    <Button
                        size="sm"
                        onClick={onSubmit}
                        disabled={isSubmitting}
                    >
                        <Send className="w-4 h-4 mr-2" />
                        {isSubmitting ? "Submitting..." : "Submit Feedback"}
                    </Button>
                </div>
            </div>
        </Card>
    );
}
