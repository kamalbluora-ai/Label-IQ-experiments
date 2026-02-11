import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { CheckCircle, XCircle, AlertTriangle, ChevronDown, ChevronUp, Pencil, Trash2, Check, X, Plus } from "lucide-react";
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
    editable?: boolean;
    onRowEdit?: (index: number, data: NutrientAudit) => void;
    onRowDelete?: (index: number) => void;
    onRowAdd?: (data: NutrientAudit) => void;
}

export default function NutritionAuditTable({
    auditDetails,
    editable = false,
    onRowEdit,
    onRowDelete,
    onRowAdd
}: NutritionAuditTableProps) {
    const [expandedCrossField, setExpandedCrossField] = useState(true);
    const [editMode, setEditMode] = useState(false);
    const [editingRow, setEditingRow] = useState<number | null>(null);
    const [editValues, setEditValues] = useState<NutrientAudit | null>(null);
    const [addingRow, setAddingRow] = useState(false);
    const [newRowValues, setNewRowValues] = useState<Partial<NutrientAudit>>({});

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

    const startEdit = (idx: number, item: NutrientAudit) => {
        setEditingRow(idx);
        setEditValues({ ...item });
    };

    const saveRowEdit = (idx: number) => {
        if (editValues && onRowEdit) {
            // Validate number parsing if needed, though input type="number" helps
            onRowEdit(idx, editValues);
        }
        setEditingRow(null);
        setEditValues(null);
    };

    const cancelEdit = () => {
        setEditingRow(null);
        setEditValues(null);
    };

    const saveNewRow = () => {
        if (onRowAdd && newRowValues.nutrient_name) {
            onRowAdd({
                nutrient_name: newRowValues.nutrient_name,
                original_value: Number(newRowValues.original_value) || 0,
                expected_value: null,
                unit: newRowValues.unit || "g",
                is_dv: newRowValues.is_dv || false,
                status: "warning", // Default status for manually added
                message: "Manually added",
                rule_applied: "Manual Override"
            });
            setAddingRow(false);
            setNewRowValues({});
        }
    };

    const cancelNewRow = () => {
        setAddingRow(false);
        setNewRowValues({});
    };

    return (
        <div className="space-y-6">
            {/* Nutrient-by-Nutrient Audits */}
            <Card>
                <CardHeader>
                    <div className="flex items-center justify-between">
                        <CardTitle>Nutrient Rounding Compliance</CardTitle>
                        {editable && (
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={() => setEditMode(!editMode)}
                            >
                                {editMode ? "Done" : "Edit"}
                            </Button>
                        )}
                    </div>
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
                                    {editMode && <th className="text-left p-2 font-semibold w-24">Actions</th>}
                                </tr>
                            </thead>
                            <tbody>
                                {auditDetails.nutrient_audits.map((audit, idx) => {
                                    const isEditing = editingRow === idx;
                                    return (
                                        <tr key={idx} className={`border-b hover:bg-muted/50 ${isEditing ? "bg-muted" : ""}`}>
                                            <td className="p-2">
                                                {isEditing ? (
                                                    <div className="flex items-center gap-2">
                                                        <Input
                                                            value={editValues?.nutrient_name || ""}
                                                            onChange={(e) => setEditValues(prev => prev ? { ...prev, nutrient_name: e.target.value } : null)}
                                                            className="h-8 w-32"
                                                        />
                                                        <label className="text-xs flex items-center">
                                                            <input
                                                                type="checkbox"
                                                                checked={editValues?.is_dv || false}
                                                                onChange={(e) => setEditValues(prev => prev ? { ...prev, is_dv: e.target.checked } : null)}
                                                                className="mr-1"
                                                            />
                                                            %DV
                                                        </label>
                                                    </div>
                                                ) : (
                                                    <div className="flex items-center gap-2">
                                                        {getStatusIcon(audit.status)}
                                                        <span className="font-medium">{audit.nutrient_name}</span>
                                                        {audit.is_dv && <Badge variant="outline" className="text-xs">%DV</Badge>}
                                                    </div>
                                                )}
                                            </td>
                                            <td className="p-2">
                                                {isEditing ? (
                                                    <Input
                                                        type="number"
                                                        value={editValues?.original_value ?? 0}
                                                        onChange={(e) => setEditValues(prev => prev ? { ...prev, original_value: parseFloat(e.target.value) } : null)}
                                                        className="h-8 w-20"
                                                    />
                                                ) : (
                                                    audit.original_value
                                                )}
                                            </td>
                                            <td className="p-2">
                                                {audit.expected_value !== null ? audit.expected_value : "-"}
                                            </td>
                                            <td className="p-2">
                                                {isEditing ? (
                                                    <Input
                                                        value={editValues?.unit || ""}
                                                        onChange={(e) => setEditValues(prev => prev ? { ...prev, unit: e.target.value } : null)}
                                                        className="h-8 w-16"
                                                    />
                                                ) : (
                                                    audit.unit
                                                )}
                                            </td>
                                            <td className="p-2">{getStatusBadge(audit.status)}</td>
                                            <td className="p-2 text-xs text-muted-foreground">
                                                {audit.rule_applied || audit.message}
                                            </td>
                                            {editMode && (
                                                <td className="p-2">
                                                    {isEditing ? (
                                                        <div className="flex gap-1">
                                                            <Button size="sm" variant="ghost" onClick={() => saveRowEdit(idx)}>
                                                                <Check className="w-3 h-3 text-green-600" />
                                                            </Button>
                                                            <Button size="sm" variant="ghost" onClick={cancelEdit}>
                                                                <X className="w-3 h-3 text-red-600" />
                                                            </Button>
                                                        </div>
                                                    ) : (
                                                        <div className="flex gap-1">
                                                            <Button size="sm" variant="ghost" onClick={() => startEdit(idx, audit)}>
                                                                <Pencil className="w-3 h-3" />
                                                            </Button>
                                                            <Button size="sm" variant="ghost" onClick={() => onRowDelete?.(idx)}>
                                                                <Trash2 className="w-3 h-3 text-red-500" />
                                                            </Button>
                                                        </div>
                                                    )}
                                                </td>
                                            )}
                                        </tr>
                                    );
                                })}

                                {/* New Row */}
                                {addingRow && (
                                    <tr className="border-b bg-green-50/50">
                                        <td className="p-2">
                                            <div className="flex items-center gap-2">
                                                <Input
                                                    placeholder="Name"
                                                    value={newRowValues.nutrient_name || ""}
                                                    onChange={(e) => setNewRowValues(prev => ({ ...prev, nutrient_name: e.target.value }))}
                                                    className="h-8 w-32"
                                                />
                                                <label className="text-xs flex items-center">
                                                    <input
                                                        type="checkbox"
                                                        checked={newRowValues.is_dv || false}
                                                        onChange={(e) => setNewRowValues(prev => ({ ...prev, is_dv: e.target.checked }))}
                                                        className="mr-1"
                                                    />
                                                    %DV
                                                </label>
                                            </div>
                                        </td>
                                        <td className="p-2">
                                            <Input
                                                type="number"
                                                placeholder="Val"
                                                value={newRowValues.original_value || ""}
                                                onChange={(e) => setNewRowValues(prev => ({ ...prev, original_value: parseFloat(e.target.value) }))}
                                                className="h-8 w-20"
                                            />
                                        </td>
                                        <td className="p-2">-</td>
                                        <td className="p-2">
                                            <Input
                                                placeholder="Unit"
                                                value={newRowValues.unit || ""}
                                                onChange={(e) => setNewRowValues(prev => ({ ...prev, unit: e.target.value }))}
                                                className="h-8 w-16"
                                            />
                                        </td>
                                        <td className="p-2"><Badge className="bg-gray-100 text-gray-800">PENDING</Badge></td>
                                        <td className="p-2 text-xs text-muted-foreground">New Entry</td>
                                        <td className="p-2">
                                            <div className="flex gap-1">
                                                <Button size="sm" variant="ghost" onClick={saveNewRow}>
                                                    <Check className="w-3 h-3 text-green-600" />
                                                </Button>
                                                <Button size="sm" variant="ghost" onClick={cancelNewRow}>
                                                    <X className="w-3 h-3 text-red-600" />
                                                </Button>
                                            </div>
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>

                    {editMode && !addingRow && (
                        <div className="mt-3 flex justify-end">
                            <Button size="sm" variant="outline" onClick={() => setAddingRow(true)}>
                                <Plus className="w-3 h-3 mr-1" /> Add Nutrient
                            </Button>
                        </div>
                    )}
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
