import { ComplianceReport } from "@/api";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { CheckCircle, XCircle, AlertTriangle } from "lucide-react";
import { useState } from "react";

interface ComplianceResultsSectionProps {
    title: string;
    checkResults: CheckResult[];
    jobId: string;
    comment: string;           // current comment for this section
    onCommentChange: (comment: string) => void;
}

interface CheckResult {
    question_id: string;
    section: string;
    question: string;
    result: string;
    selected_value?: string;
    rationale: string;
}

export default function ComplianceResultsSection({
    title,
    checkResults,
    jobId,
    comment,
    onCommentChange
}: ComplianceResultsSectionProps) {
    const [isExpanded, setIsExpanded] = useState(false);

    const failCount = checkResults.filter(c => c.result === "fail").length;
    const reviewCount = checkResults.filter(c => c.result === "needs_review").length;

    const getResultIcon = (result: string) => {
        if (result === "pass") return <CheckCircle className="w-4 h-4 text-green-600" />;
        if (result === "fail") return <XCircle className="w-4 h-4 text-red-600" />;
        return <AlertTriangle className="w-4 h-4 text-yellow-600" />;
    };

    const getResultBadge = (result: string) => {
        return (
            <Badge variant="outline">
                {result.replace("_", " ").toUpperCase()}
            </Badge>
        );
    };

    return (
        <Card>
            <CardHeader
                className="cursor-pointer hover:bg-muted/50 transition-colors"
                onClick={() => setIsExpanded(!isExpanded)}
            >
                <div className="flex items-center justify-between">
                    <CardTitle className="text-lg capitalize">
                        {title}
                    </CardTitle>
                    <div className="flex items-center gap-2">
                        {failCount > 0 && (
                            <Badge variant="destructive">{failCount} Failed</Badge>
                        )}
                        {reviewCount > 0 && (
                            <Badge className="bg-yellow-100 text-yellow-800">
                                {reviewCount} Need Review
                            </Badge>
                        )}
                        <Badge variant="outline">
                            {checkResults.length} Total
                        </Badge>
                    </div>
                </div>
            </CardHeader>

            {isExpanded && (
                <CardContent className="space-y-3">
                    {/* All questions rendered (read-only, no per-question buttons) */}
                    {checkResults.map((check, idx) => (
                        <div key={idx} className="p-4 rounded-lg border bg-muted/30">
                            <div className="flex items-center gap-2 mb-2">
                                {getResultIcon(check.result)}
                                <span className="font-mono text-sm text-muted-foreground">{check.question_id}</span>
                                {getResultBadge(check.result)}
                            </div>
                            <p className="text-sm font-medium mb-2">{check.question}</p>
                            {check.selected_value && (
                                <p className="text-sm text-muted-foreground mb-1">
                                    <span className="font-semibold">Answer:</span> {check.selected_value}
                                </p>
                            )}
                            <p className="text-sm text-muted-foreground">
                                <span className="font-semibold">Reasoning:</span> {check.rationale}
                            </p>
                        </div>
                    ))}

                    {/* Section-level comment box */}
                    <div className="mt-4 pt-4 border-t">
                        <label className="text-sm font-medium">Expert Comment</label>
                        <Textarea
                            placeholder="Add your comment for this section..."
                            value={comment}
                            onChange={(e) => onCommentChange(e.target.value)}
                            className="mt-2"
                        />
                        {comment.trim() && (
                            <p className="text-xs text-muted-foreground mt-1">
                                ✓ Comment saved. Press "Update" at the bottom to submit.
                            </p>
                        )}
                    </div>
                </CardContent>
            )}
        </Card>
    );
}
