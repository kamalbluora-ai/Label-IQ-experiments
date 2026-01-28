import { ComplianceReport } from "@/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MessageSquare, CheckCircle, XCircle, AlertTriangle } from "lucide-react";
import { useState } from "react";

interface ComplianceResultsTableProps {
    report: ComplianceReport;
    onAddComment: (questionId: string, section: string, result: string) => void;
    feedbackCount: Map<string, number>;
}

export default function ComplianceResultsTable({
    report,
    onAddComment,
    feedbackCount
}: ComplianceResultsTableProps) {
    const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());

    // Group results by section
    const groupedResults = report.results.check_results.reduce((acc, check) => {
        if (!acc[check.section]) {
            acc[check.section] = [];
        }
        acc[check.section].push(check);
        return acc;
    }, {} as Record<string, typeof report.results.check_results>);

    const toggleSection = (section: string) => {
        const newExpanded = new Set(expandedSections);
        if (newExpanded.has(section)) {
            newExpanded.delete(section);
        } else {
            newExpanded.add(section);
        }
        setExpandedSections(newExpanded);
    };

    const getResultIcon = (result: string) => {
        switch (result) {
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
        const variants = {
            pass: "bg-green-100 text-green-800 border-green-200",
            fail: "bg-red-100 text-red-800 border-red-200",
            needs_review: "bg-yellow-100 text-yellow-800 border-yellow-200"
        };
        return (
            <Badge className={variants[result as keyof typeof variants] || ""}>
                {result.replace("_", " ").toUpperCase()}
            </Badge>
        );
    };

    return (
        <div className="space-y-4">
            {Object.entries(groupedResults).map(([section, checks]) => {
                const isExpanded = expandedSections.has(section);
                const failCount = checks.filter(c => c.result === "fail").length;
                const reviewCount = checks.filter(c => c.result === "needs_review").length;

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
                                {checks.map((check, idx) => {
                                    const hasFeedback = feedbackCount.has(check.question_id);

                                    return (
                                        <div
                                            key={idx}
                                            className={`p-4 rounded-lg border transition-colors ${hasFeedback ? "bg-blue-50 border-blue-200" : "bg-muted/30"
                                                }`}
                                        >
                                            <div className="flex items-start justify-between gap-4">
                                                <div className="flex-1 space-y-2">
                                                    <div className="flex items-center gap-2">
                                                        {getResultIcon(check.result)}
                                                        <span className="font-mono text-sm text-muted-foreground">
                                                            {check.question_id}
                                                        </span>
                                                        {getResultBadge(check.result)}
                                                        {hasFeedback && (
                                                            <Badge variant="outline" className="bg-blue-100 text-blue-800">
                                                                <MessageSquare className="w-3 h-3 mr-1" />
                                                                Comment Added
                                                            </Badge>
                                                        )}
                                                    </div>

                                                    <p className="text-sm font-medium">
                                                        {check.question}
                                                    </p>

                                                    {check.selected_value && (
                                                        <p className="text-xs text-muted-foreground">
                                                            <span className="font-semibold">Value:</span> {check.selected_value}
                                                        </p>
                                                    )}

                                                    <p className="text-sm text-muted-foreground">
                                                        {check.rationale}
                                                    </p>
                                                </div>

                                                <Button
                                                    variant="outline"
                                                    size="sm"
                                                    onClick={() => onAddComment(check.question_id, check.section, check.result)}
                                                    className="shrink-0"
                                                >
                                                    <MessageSquare className="w-4 h-4 mr-2" />
                                                    {hasFeedback ? "Edit" : "Add"} Comment
                                                </Button>
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
