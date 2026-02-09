import { ComplianceReport } from "@/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { MessageSquare, CheckCircle, XCircle, AlertTriangle, Loader2 } from "lucide-react";
import { useState } from "react";
import { api } from "@/api";

interface ComplianceResultsTableProps {
    report: ComplianceReport;
    jobId: string;
}

interface CheckResult {
    question_id: string;
    section: string;
    question: string;
    result: string;
    selected_value?: string;
    rationale: string;
}

export default function ComplianceResultsTable({ report, jobId }: ComplianceResultsTableProps) {
    const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());
    const [activeComment, setActiveComment] = useState<string | null>(null);
    const [commentText, setCommentText] = useState("");
    const [reevaluating, setReevaluating] = useState<string | null>(null);
    const [updatedResults, setUpdatedResults] = useState<Map<string, CheckResult>>(new Map());

    // Aggregate all agent check_results into one array
    const allCheckResults = [
        ...(report.results.common_name?.check_results || []),
        ...(report.results.ingredients?.check_results || []),
        ...(report.results.date_marking?.check_results || []),
        ...(report.results.fop_symbol?.check_results || []),
        ...(report.results.bilingual?.check_results || []),
        ...(report.results.irradiation?.check_results || []),
        ...(report.results.country_origin?.check_results || []),
    ];

    // Group results by section
    const groupedResults = allCheckResults.reduce((acc, check) => {
        if (!acc[check.section]) {
            acc[check.section] = [];
        }
        acc[check.section].push(check);
        return acc;
    }, {} as Record<string, typeof allCheckResults>);

    const toggleSection = (section: string) => {
        const newExpanded = new Set(expandedSections);
        if (newExpanded.has(section)) {
            newExpanded.delete(section);
        } else {
            newExpanded.add(section);
        }
        setExpandedSections(newExpanded);
    };

    const handleCommentClick = (questionId: string) => {
        if (activeComment === questionId) {
            setActiveComment(null);
            setCommentText("");
        } else {
            setActiveComment(questionId);
            setCommentText("");
        }
    };

    const handleReevaluate = async (check: CheckResult) => {
        if (!commentText.trim()) return;

        setReevaluating(check.question_id);

        try {
            const response = await api.post(`/v1/jobs/${jobId}/reevaluate`, {
                question_id: check.question_id,
                question: check.question,
                original_answer: check.selected_value || "",
                original_tag: check.result,
                original_rationale: check.rationale,
                user_comment: commentText
            });

            // Update the result in state
            const newUpdatedResults = new Map(updatedResults);
            newUpdatedResults.set(check.question_id, {
                ...check,
                result: response.data.new_tag,
                rationale: response.data.new_rationale
            });
            setUpdatedResults(newUpdatedResults);

            // Clear comment input
            setActiveComment(null);
            setCommentText("");
        } catch (error) {
            console.error("Re-evaluation failed:", error);
        } finally {
            setReevaluating(null);
        }
    };

    const getResultIcon = (result: string) => {
        switch (result.toLowerCase()) {
            case "pass":
                return <CheckCircle className="w-4 h-4 text-green-600" />;
            case "fail":
                return <XCircle className="w-4 h-4 text-red-600" />;
            case "needs_review":
                return <AlertTriangle className="w-4 h-4 text-yellow-600" />;
            default:
                return null;
        }
    };

    const getResultBadge = (result: string) => {
        return (
            <Badge variant="outline">
                {result.replace("_", " ").toUpperCase()}
            </Badge>
        );
    };

    const getCheckData = (check: CheckResult): CheckResult => {
        return updatedResults.get(check.question_id) || check;
    };

    return (
        <div className="space-y-4">
            {Object.entries(groupedResults).map(([section, checks]) => {
                const isExpanded = expandedSections.has(section);
                const failCount = checks.filter(c => getCheckData(c).result === "fail").length;
                const reviewCount = checks.filter(c => getCheckData(c).result === "needs_review").length;

                return (
                    <Card key={section}>
                        <CardHeader
                            className="cursor-pointer hover:bg-muted/50 transition-colors"
                            onClick={() => toggleSection(section)}
                        >
                            <div className="flex items-center justify-between">
                                <CardTitle className="text-lg capitalize">
                                    {section.replace(/_/g, " ")}
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
                                        {checks.length} Total
                                    </Badge>
                                </div>
                            </div>
                        </CardHeader>

                        {isExpanded && (
                            <CardContent className="space-y-3">
                                {checks.map((originalCheck, idx) => {
                                    const check = getCheckData(originalCheck);
                                    const isCommentActive = activeComment === check.question_id;
                                    const isReevaluating = reevaluating === check.question_id;
                                    const hasBeenUpdated = updatedResults.has(check.question_id);

                                    return (
                                        <div
                                            key={idx}
                                            className={`p-4 rounded-lg border transition-colors ${hasBeenUpdated ? "bg-blue-50 border-blue-200" : "bg-muted/30"
                                                }`}
                                        >
                                            <div className="space-y-3">
                                                <div className="flex items-start justify-between gap-4">
                                                    <div className="flex-1 space-y-2">
                                                        <div className="flex items-center gap-2">
                                                            {getResultIcon(check.result)}
                                                            <span className="font-mono text-sm text-muted-foreground">
                                                                {check.question_id}
                                                            </span>
                                                            {getResultBadge(check.result)}
                                                            {hasBeenUpdated && (
                                                                <Badge variant="outline" className="bg-blue-100 text-blue-800">
                                                                    <MessageSquare className="w-3 h-3 mr-1" />
                                                                    Re-evaluated
                                                                </Badge>
                                                            )}
                                                        </div>

                                                        <p className="text-sm font-medium">
                                                            {check.question}
                                                        </p>

                                                        {check.selected_value && (
                                                            <p className="text-xs text-muted-foreground">
                                                                <span className="font-semibold">Answer:</span> {check.selected_value}
                                                            </p>
                                                        )}

                                                        <p className="text-sm text-muted-foreground">
                                                            <span className="font-semibold">Reasoning:</span> {check.rationale}
                                                        </p>
                                                    </div>

                                                    <Button
                                                        variant="outline"
                                                        size="sm"
                                                        onClick={() => handleCommentClick(check.question_id)}
                                                        className="shrink-0"
                                                        disabled={isReevaluating}
                                                    >
                                                        <MessageSquare className="w-4 h-4 mr-2" />
                                                        {isCommentActive ? "Cancel" : "Add Comment"}
                                                    </Button>
                                                </div>

                                                {isCommentActive && (
                                                    <div className="space-y-2 pt-2 border-t">
                                                        <Textarea
                                                            placeholder="Add your comment or correction..."
                                                            value={commentText}
                                                            onChange={(e) => setCommentText(e.target.value)}
                                                            className="min-h-[80px]"
                                                        />
                                                        <div className="flex justify-end gap-2">
                                                            <Button
                                                                variant="outline"
                                                                size="sm"
                                                                onClick={() => {
                                                                    setActiveComment(null);
                                                                    setCommentText("");
                                                                }}
                                                            >
                                                                Cancel
                                                            </Button>
                                                            <Button
                                                                size="sm"
                                                                onClick={() => handleReevaluate(check)}
                                                                disabled={!commentText.trim() || isReevaluating}
                                                            >
                                                                {isReevaluating ? (
                                                                    <>
                                                                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                                                        Re-evaluating...
                                                                    </>
                                                                ) : (
                                                                    "Submit & Re-evaluate"
                                                                )}
                                                            </Button>
                                                        </div>
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    );
                                })}
                            </CardContent>
                        )}
                    </Card>
                );
            })}
        </div>
    );
}
