import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { CheckCircle, XCircle, AlertTriangle, MessageSquare, Info, Pencil } from "lucide-react";
import { useState } from "react";
import { TagOverride, UserComment, AnswerOverride } from "@/hooks/useReportEdits";

interface ComplianceResultsSectionProps {
    title: string;
    checkResults: CheckResult[];

    // Tag overrides
    tagOverrides: Map<string, TagOverride>;
    onTagChange: (questionId: string, tag: string) => void;

    // User comments (no re-evaluation)
    userComments: Map<string, UserComment>;
    onUserCommentChange: (questionId: string, comment: string) => void;

    // Answer overrides
    answerOverrides: Map<string, AnswerOverride>;
    onAnswerChange: (questionId: string, answer: string) => void;

    // Modification tracking
    modifiedQuestions: Set<string>;
}

interface CheckResult {
    question_id: string;
    section: string;
    question: string;
    result: string;
    selected_value?: string;
    rationale: string;
    user_comment?: string;
}

export default function ComplianceResultsSection({
    title,
    checkResults,
    tagOverrides,
    onTagChange,
    userComments,
    onUserCommentChange,
    answerOverrides,
    onAnswerChange,
    modifiedQuestions
}: ComplianceResultsSectionProps) {
    const [isExpanded, setIsExpanded] = useState(false);
    // Track open comment boxes locally
    const [openCommentBoxIds, setOpenCommentBoxIds] = useState<Set<string>>(new Set());
    // Track which questions are in edit mode
    const [editingIds, setEditingIds] = useState<Set<string>>(new Set());

    const toggleEdit = (qId: string, e: React.MouseEvent) => {
        e.stopPropagation();
        setEditingIds(prev => {
            const next = new Set(prev);
            if (next.has(qId)) {
                next.delete(qId);
            } else {
                next.add(qId);
            }
            return next;
        });
    };

    const toggleCommentBox = (qId: string, e: React.MouseEvent) => {
        e.stopPropagation();
        setOpenCommentBoxIds(prev => {
            const next = new Set(prev);
            if (next.has(qId)) {
                next.delete(qId);
            } else {
                next.add(qId);
            }
            return next;
        });
    };

    const getEffectiveResult = (check: CheckResult) => {
        const override = tagOverrides.get(check.question_id);
        return override ? override.new_tag : check.result;
    };

    const failCount = checkResults.filter(c => getEffectiveResult(c) === "fail").length;
    const reviewCount = checkResults.filter(c => getEffectiveResult(c) === "needs_review").length;

    const getResultColor = (result: string) => {
        if (result === "pass") return "text-green-600 border-green-200 bg-green-50";
        if (result === "fail") return "text-red-600 border-red-200 bg-red-50";
        return "text-yellow-600 border-yellow-200 bg-yellow-50";
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
                        // Determine if question has user comment or existing comment
                        const userCommentObj = userComments.get(check.question_id);
                        const userCommentText = userCommentObj ? userCommentObj.comment : (check.user_comment || "");
                        const hasUserComment = !!userCommentText;

                        // Check if modified
                        const isModified = modifiedQuestions.has(check.question_id);
                        const isTagModified = tagOverrides.has(check.question_id);

                        const isCommentOpen = openCommentBoxIds.has(check.question_id) || hasUserComment;
                        const effectiveResult = getEffectiveResult(check);

                        return (
                            <div
                                key={idx}
                                className={`p-4 rounded-lg border ${isModified ? "border-blue-300 bg-blue-50/20" : "bg-muted/30"}`}
                            >
                                {/* Header Row */}
                                <div className="flex items-center justify-between mb-2">
                                    <div className="flex items-center gap-2">
                                        <span className="font-mono text-sm text-muted-foreground">{check.question_id}</span>

                                        {/* Dropdown for Result */}
                                        <div onClick={(e) => e.stopPropagation()}>
                                            <Select
                                                value={effectiveResult}
                                                onValueChange={(val) => onTagChange(check.question_id, val as any)}
                                            >
                                                <SelectTrigger className={`w-[140px] h-8 ${getResultColor(effectiveResult)}`}>
                                                    <SelectValue placeholder="Result" />
                                                </SelectTrigger>
                                                <SelectContent>
                                                    <SelectItem value="pass">PASS</SelectItem>
                                                    <SelectItem value="fail">FAIL</SelectItem>
                                                    <SelectItem value="needs_review">NEEDS REVIEW</SelectItem>
                                                </SelectContent>
                                            </Select>
                                        </div>

                                        {isTagModified && (
                                            <Badge variant="outline" className="text-blue-600 border-blue-200 bg-blue-50 text-[10px] h-5 px-1">
                                                MODIFIED
                                            </Badge>
                                        )}
                                    </div>

                                    {/* Edit + Comment Buttons */}
                                    <div className="flex items-center gap-1">
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            className={`h-8 w-8 p-0 ${editingIds.has(check.question_id) ? "text-orange-600 bg-orange-50" : "text-muted-foreground"}`}
                                            onClick={(e) => toggleEdit(check.question_id, e)}
                                        >
                                            <Pencil className="w-4 h-4" />
                                        </Button>
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            className={`h-8 w-8 p-0 ${hasUserComment ? "text-blue-600 bg-blue-50" : "text-muted-foreground"}`}
                                            onClick={(e) => toggleCommentBox(check.question_id, e)}
                                        >
                                            <MessageSquare className="w-4 h-4" />
                                        </Button>
                                    </div>
                                </div>

                                {/* Content */}
                                <p className="text-sm font-medium mb-2">{check.question}</p>
                                {(() => {
                                    const answerOverride = answerOverrides.get(check.question_id);
                                    const effectiveAnswer = answerOverride ? answerOverride.new_answer : (check.selected_value || "");
                                    const isEditing = editingIds.has(check.question_id);

                                    return check.selected_value !== undefined && (
                                        isEditing ? (
                                            <div className="mb-1" onClick={(e) => e.stopPropagation()}>
                                                <label className="text-xs font-semibold text-muted-foreground mb-1 block">Answer</label>
                                                <Input
                                                    value={effectiveAnswer}
                                                    onChange={(e) => onAnswerChange(check.question_id, e.target.value)}
                                                    className="text-sm"
                                                />
                                            </div>
                                        ) : (
                                            <p className="text-sm text-muted-foreground mb-1">
                                                <span className="font-semibold">Answer:</span> {effectiveAnswer}
                                            </p>
                                        )
                                    );
                                })()}
                                <p className="text-sm text-muted-foreground">
                                    <span className="font-semibold">Reasoning:</span> {check.rationale}
                                </p>

                                {/* Comment Box (Expandable) */}
                                {isCommentOpen && (
                                    <div className="mt-3 pt-3 border-t animate-in slide-in-from-top-2 duration-200">
                                        <div className="flex items-start gap-2">
                                            <Info className="w-4 h-4 text-muted-foreground mt-2" />
                                            <div className="flex-1">
                                                <label className="text-xs font-medium text-muted-foreground mb-1 block">
                                                    User Comment (Saved to Report)
                                                </label>
                                                <Textarea
                                                    placeholder="Add specific feedback or comments for this question..."
                                                    value={userCommentText}
                                                    onChange={(e) => onUserCommentChange(check.question_id, e.target.value)}
                                                    className="min-h-[60px] text-sm resize-y"
                                                />
                                            </div>
                                        </div>
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
