import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Pencil, Trash2, Plus, Check, X } from "lucide-react";
import { useState } from "react";

export interface DetectedItem {
    name: string;
    category?: string;
    source: string;
    quantity?: string | null;
}

interface DetectionResult {
    detected: DetectedItem[];
    has_additives?: boolean;
    has_supplements?: boolean;
    has_quantity_sweeteners?: boolean;
    has_no_quantity_sweeteners?: boolean;
}

interface DetectionResultsTableProps {
    title: string;
    data: DetectionResult;
    requiresQuantity?: boolean;
    editable?: boolean;
    onRowEdit?: (index: number, data: DetectedItem) => void;
    onRowDelete?: (index: number) => void;
    onRowAdd?: (data: DetectedItem) => void;
}

export default function DetectionResultsTable({
    title,
    data,
    requiresQuantity = false,
    editable = false,
    onRowEdit,
    onRowDelete,
    onRowAdd
}: DetectionResultsTableProps) {
    const [editMode, setEditMode] = useState(false);
    const [editingRow, setEditingRow] = useState<number | null>(null);
    const [editValues, setEditValues] = useState<DetectedItem | null>(null);
    const [addingRow, setAddingRow] = useState(false);
    const [newRowValues, setNewRowValues] = useState<Partial<DetectedItem>>({});

    if (!data || !data.detected || data.detected.length === 0) {
        return null;
    }

    const getStatusFlag = (item: DetectedItem) => {
        const missingCategory = !item.category || item.category === "";
        const missingQuantity = requiresQuantity && (!item.quantity || item.quantity === null);

        if (missingCategory && missingQuantity) {
            return <Badge variant="destructive">INCOMPLETE</Badge>;
        }
        if (missingQuantity) {
            return <Badge className="bg-yellow-100 text-yellow-800 border-yellow-200">MISSING_QUANTITY</Badge>;
        }
        if (missingCategory) {
            return <Badge className="bg-yellow-100 text-yellow-800 border-yellow-200">MISSING_CATEGORY</Badge>;
        }
        return <Badge className="bg-yellow-100 text-yellow-800 border-yellow-200">NEEDS_REVIEW</Badge>;
    };

    const startEdit = (idx: number, item: DetectedItem) => {
        setEditingRow(idx);
        setEditValues({ ...item });
    };

    const saveRowEdit = (idx: number) => {
        if (editValues && onRowEdit) {
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
        if (onRowAdd && newRowValues.name) {
            onRowAdd({
                name: newRowValues.name,
                category: newRowValues.category || "",
                source: newRowValues.source || "user",
                quantity: newRowValues.quantity || null,
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
        <Card>
            <CardHeader>
                <div className="flex items-center justify-between">
                    <CardTitle>{title}</CardTitle>
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
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead>Attribute</TableHead>
                            <TableHead>Detected</TableHead>
                            <TableHead>Quantity</TableHead>
                            <TableHead>Category</TableHead>
                            <TableHead>Source</TableHead>
                            <TableHead>Status</TableHead>
                            {editMode && <TableHead className="w-24">Actions</TableHead>}
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {data.detected.map((item, idx) => {
                            const isEditing = editingRow === idx;

                            return (
                                <TableRow key={idx} className={isEditing ? "border-2 border-yellow-400" : ""}>
                                    <TableCell className="font-medium">
                                        {isEditing ? (
                                            <Input
                                                value={editValues?.name || ""}
                                                onChange={(e) => setEditValues(prev => prev ? { ...prev, name: e.target.value } : null)}
                                                className="h-8"
                                            />
                                        ) : (
                                            item.name
                                        )}
                                    </TableCell>
                                    <TableCell>Yes</TableCell>
                                    <TableCell>
                                        {isEditing ? (
                                            <Input
                                                value={editValues?.quantity || ""}
                                                onChange={(e) => setEditValues(prev => prev ? { ...prev, quantity: e.target.value } : null)}
                                                className="h-8"
                                            />
                                        ) : (
                                            item.quantity || "—"
                                        )}
                                    </TableCell>
                                    <TableCell>
                                        {isEditing ? (
                                            <Input
                                                value={editValues?.category || ""}
                                                onChange={(e) => setEditValues(prev => prev ? { ...prev, category: e.target.value } : null)}
                                                className="h-8"
                                            />
                                        ) : (
                                            item.category || "—"
                                        )}
                                    </TableCell>
                                    <TableCell className="capitalize">
                                        {isEditing ? (
                                            <Input
                                                value={editValues?.source || ""}
                                                onChange={(e) => setEditValues(prev => prev ? { ...prev, source: e.target.value } : null)}
                                                className="h-8"
                                            />
                                        ) : (
                                            item.source
                                        )}
                                    </TableCell>
                                    <TableCell>{getStatusFlag(item)}</TableCell>
                                    {editMode && (
                                        <TableCell>
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
                                                    <Button size="sm" variant="ghost" onClick={() => startEdit(idx, item)}>
                                                        <Pencil className="w-3 h-3" />
                                                    </Button>
                                                    <Button size="sm" variant="ghost" onClick={() => onRowDelete?.(idx)}>
                                                        <Trash2 className="w-3 h-3 text-red-500" />
                                                    </Button>
                                                </div>
                                            )}
                                        </TableCell>
                                    )}
                                </TableRow>
                            );
                        })}

                        {/* New row being added */}
                        {addingRow && (
                            <TableRow className="border-2 border-green-400">
                                <TableCell>
                                    <Input
                                        placeholder="Name"
                                        value={newRowValues.name || ""}
                                        onChange={(e) => setNewRowValues(prev => ({ ...prev, name: e.target.value }))}
                                        className="h-8"
                                    />
                                </TableCell>
                                <TableCell>Yes</TableCell>
                                <TableCell>
                                    <Input
                                        placeholder="Quantity"
                                        value={newRowValues.quantity || ""}
                                        onChange={(e) => setNewRowValues(prev => ({ ...prev, quantity: e.target.value }))}
                                        className="h-8"
                                    />
                                </TableCell>
                                <TableCell>
                                    <Input
                                        placeholder="Category"
                                        value={newRowValues.category || ""}
                                        onChange={(e) => setNewRowValues(prev => ({ ...prev, category: e.target.value }))}
                                        className="h-8"
                                    />
                                </TableCell>
                                <TableCell>
                                    <Input
                                        placeholder="Source"
                                        value={newRowValues.source || "user"}
                                        onChange={(e) => setNewRowValues(prev => ({ ...prev, source: e.target.value }))}
                                        className="h-8"
                                    />
                                </TableCell>
                                <TableCell>—</TableCell>
                                {editMode && (
                                    <TableCell>
                                        <div className="flex gap-1">
                                            <Button size="sm" variant="ghost" onClick={saveNewRow}>
                                                <Check className="w-3 h-3 text-green-600" />
                                            </Button>
                                            <Button size="sm" variant="ghost" onClick={cancelNewRow}>
                                                <X className="w-3 h-3 text-red-600" />
                                            </Button>
                                        </div>
                                    </TableCell>
                                )}
                            </TableRow>
                        )}
                    </TableBody>
                </Table>

                {/* Add button at end of table (only visible in edit mode) */}
                {editMode && !addingRow && (
                    <div className="mt-3 flex justify-end">
                        <Button size="sm" variant="outline" onClick={() => setAddingRow(true)}>
                            <Plus className="w-3 h-3 mr-1" /> Add Row
                        </Button>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
