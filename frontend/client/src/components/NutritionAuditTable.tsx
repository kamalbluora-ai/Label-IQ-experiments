import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CheckCircle, XCircle, AlertTriangle, ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";

interface NutrientAudit {
    nutrient_name: string;
    original_value: number;
    expected_value: number | null;
    unit: string;
    is_dv: boolean;
    status: string;
    message: string;
    rule_applied: string | null;
}

interface CrossFieldAudit {
    check_name: string;
    status: string;
    message: string;
    tolerance: string | null;
}

interface AuditDetails {
    nutrient_audits: NutrientAudit[];
    cross_field_audits: CrossFieldAudit[];
}

interface NutritionAuditTableProps {
    auditDetails: AuditDetails | null;
}

export default function NutritionAuditTable({ auditDetails }: NutritionAuditTableProps) {
    const [expandedCrossField, setExpandedCrossField] = useState(true);

    if (!auditDetails) {
        return (
            <Card>
                <CardContent className="p-6 text-center text-muted-foreground">
                    No NFT audit details available
                </CardContent>
            </Card>
        );
    }

    const getStatusIcon = (status: string) => {
        switch (status) {
            case "pass":
                return <CheckCircle className="w-4 h-4 text-green-600" />;
            case "fail":
                return <XCircle className="w-4 h-4 text-red-600" />;
            case "warning":
                return <AlertTriangle className="w-4 h-4 text-yellow-600" />;
            default:
                return <AlertTriangle className="w-4 h-4 text-gray-400" />;
        }
    };

    const getStatusBadge = (status: string) => {
        const variants = {
            pass: "bg-green-100 text-green-800 border-green-200",
            fail: "bg-red-100 text-red-800 border-red-200",
            warning: "bg-yellow-100 text-yellow-800 border-yellow-200",
            skip: "bg-gray-100 text-gray-800 border-gray-200"
        };
        return (
            <Badge className={variants[status as keyof typeof variants] || variants.skip}>
                {status.toUpperCase()}
            </Badge>
        );
    };

    return (
        <div className="space-y-6">
            {/* Nutrient-by-Nutrient Audits */}
            <Card>
                <CardHeader>
                    <CardTitle>Nutrient Rounding Compliance</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b">
                                    <th className="text-left p-2 font-semibold">Nutrient</th>
                                    <th className="text-left p-2 font-semibold">Original Value</th>
                                    <th className="text-left p-2 font-semibold">Expected Value</th>
                                    <th className="text-left p-2 font-semibold">Unit</th>
                                    <th className="text-left p-2 font-semibold">Status</th>
                                    <th className="text-left p-2 font-semibold">Rule Applied</th>
                                </tr>
                            </thead>
                            <tbody>
                                {auditDetails.nutrient_audits.map((audit, idx) => (
                                    <tr key={idx} className="border-b hover:bg-muted/50">
                                        <td className="p-2 flex items-center gap-2">
                                            {getStatusIcon(audit.status)}
                                            <span className="font-medium">{audit.nutrient_name}</span>
                                            {audit.is_dv && <Badge variant="outline" className="text-xs">%DV</Badge>}
                                        </td>
                                        <td className="p-2">{audit.original_value}</td>
                                        <td className="p-2">
                                            {audit.expected_value !== null ? audit.expected_value : "-"}
                                        </td>
                                        <td className="p-2">{audit.unit}</td>
                                        <td className="p-2">{getStatusBadge(audit.status)}</td>
                                        <td className="p-2 text-xs text-muted-foreground">
                                            {audit.rule_applied || audit.message}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </CardContent>
            </Card>

            {/* Cross-Field Validations */}
            {auditDetails.cross_field_audits.length > 0 && (
                <Card>
                    <CardHeader
                        className="cursor-pointer hover:bg-muted/50 transition-colors"
                        onClick={() => setExpandedCrossField(!expandedCrossField)}
                    >
                        <div className="flex items-center justify-between">
                            <CardTitle>Cross-Field Validations</CardTitle>
                            <div className="flex items-center gap-2">
                                <Badge variant="outline">
                                    {auditDetails.cross_field_audits.length} checks
                                </Badge>
                                {expandedCrossField ? (
                                    <ChevronUp className="w-4 h-4" />
                                ) : (
                                    <ChevronDown className="w-4 h-4" />
                                )}
                            </div>
                        </div>
                    </CardHeader>
                    {expandedCrossField && (
                        <CardContent>
                            <div className="space-y-3">
                                {auditDetails.cross_field_audits.map((check, idx) => (
                                    <div
                                        key={idx}
                                        className={`p-4 rounded-lg border ${check.status === "fail"
                                                ? "bg-red-50 border-red-200"
                                                : check.status === "warning"
                                                    ? "bg-yellow-50 border-yellow-200"
                                                    : "bg-green-50 border-green-200"
                                            }`}
                                    >
                                        <div className="flex items-start gap-3">
                                            {getStatusIcon(check.status)}
                                            <div className="flex-1">
                                                <h4 className="font-semibold text-sm">{check.check_name}</h4>
                                                <p className="text-sm text-muted-foreground mt-1">{check.message}</p>
                                                {check.tolerance && (
                                                    <p className="text-xs text-muted-foreground mt-1">
                                                        Tolerance: {check.tolerance}
                                                    </p>
                                                )}
                                            </div>
                                            {getStatusBadge(check.status)}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </CardContent>
                    )}
                </Card>
            )}
        </div>
    );
}
