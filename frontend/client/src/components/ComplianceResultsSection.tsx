import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { CheckCircle, XCircle, AlertTriangle, MessageSquare, Loader2 } from "lucide-react";
import { useState } from "react";
import { QuestionOverride } from "@/hooks/useReportEdits";

interface ComplianceResultsSectionProps {
    title: string;
    checkResults: CheckResult[];
    jobId: string;

    // per-question state matches global hook
    questionComments: Map<string, string>;
    questionOverrides: Map<string, QuestionOverride>;
    pendingQuestions: Set<string>;
    onQuestionCommentChange: (questionId: string, comment: string) => void;
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
    questionComments,
    questionOverrides,
    pendingQuestions,
    onQuestionCommentChange
}: ComplianceResultsSectionProps) {
    const [isExpanded, setIsExpanded] = useState(false);
    // Track which question comment boxes are open
    const [openCommentBoxIds, setOpenCommentBoxIds] = useState<Set<string>>(new Set());

    const toggleCommentBox = (qId: string, e: React.MouseEvent) => {
        e.stopPropagation();
        setOpenCommentBoxIds(prev => {
            const next = new Set(prev);
            if (next.has(qId) && !questionComments.has(qId)) {
                // Only allow closing if no comment exists? 
                // Or user can close, and it will remove from 'open' set.
                // If comment exists, we force it open below anyway.
                next.delete(qId);
            } else {
                next.add(qId);
            }
            return next;
        });
    };

    const failCount = checkResults.filter(c => {
        const override = questionOverrides.get(c.question_id);
        const effectiveResult = override ? override.new_tag : c.result;
        return effectiveResult === "fail";
    }).length;

    const reviewCount = checkResults.filter(c => {
        const override = questionOverrides.get(c.question_id);
        const effectiveResult = override ? override.new_tag : c.result;
        return effectiveResult === "needs_review";
    }).length;

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
                    {checkResults.map((check, idx) => {
                        const override = questionOverrides.get(check.question_id);
                        const isPending = pendingQuestions.has(check.question_id);
                        const hasComment = questionComments.has(check.question_id);
                        // Open if explicitly opened OR if comment exists
                        const isCommentOpen = openCommentBoxIds.has(check.question_id) || hasComment;

                        // Use override values if present
                        const displayResult = override ? override.new_tag : check.result;
                        const displayRationale = override ? override.new_rationale : check.rationale;

                        return (
                            <div
                                key={idx}
                                className={`p-4 rounded-lg border ${override ? "border-blue-300 bg-blue-50/30" : "bg-muted/30"}`}
                            >
                                {/* Header Row */}
                                <div className="flex items-center justify-between mb-2">
                                    <div className="flex items-center gap-2">
                                        {isPending ? <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" /> : getResultIcon(displayResult)}
                                        <span className="font-mono text-sm text-muted-foreground">{check.question_id}</span>
                                        {getResultBadge(displayResult)}
                                        {override && <Badge className="bg-blue-100 text-blue-800 border-blue-200">UPDATED</Badge>}
                                    </div>

                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        className={`h-8 w-8 p-0 ${hasComment ? "text-blue-600 bg-blue-50" : "text-muted-foreground"}`}
                                        onClick={(e) => toggleCommentBox(check.question_id, e)}
                                        disabled={isPending}
                                    >
                                        <MessageSquare className="w-4 h-4" />
                                    </Button>
                                </div>

                                {/* Content */}
                                <p className="text-sm font-medium mb-2">{check.question}</p>
                                {check.selected_value && (
                                    <p className="text-sm text-muted-foreground mb-1">
                                        <span className="font-semibold">Answer:</span> {check.selected_value}
                                    </p>
                                )}
                                <p className="text-sm text-muted-foreground">
                                    <span className="font-semibold">Reasoning:</span> {displayRationale}
                                </p>

                                {/* Comment Box (Expandable) */}
                                {isCommentOpen && (
                                    <div className="mt-3 pt-3 border-t animate-in slide-in-from-top-2 duration-200">
                                        <Textarea
                                            placeholder="Add specific feedback for this question..."
                                            value={questionComments.get(check.question_id) || ""}
                                            onChange={(e) => onQuestionCommentChange(check.question_id, e.target.value)}
                                            className="min-h-[60px] text-sm"
                                        />
                                        <p className="text-xs text-muted-foreground mt-1">
                                            {questionComments.get(check.question_id)
                                                ? "Changes staged. Press 'Update' at bottom to apply."
                                                : "Type a comment to stage changes."}
                                        </p>
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </CardContent>
            )}
        </Card>
    );
}
