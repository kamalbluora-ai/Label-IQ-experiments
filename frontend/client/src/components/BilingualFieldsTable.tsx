import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Pencil } from "lucide-react";
import { useState, useMemo } from "react";

interface BilingualFieldsTableProps {
    fields: Record<string, { text?: string }>;
    editable?: boolean;
    onFieldChange?: (fieldKey: string, value: string) => void;
}

// Helper to convert field key to human-readable label
const formatNutrientLabel = (key: string): string => {
    // Remove nft_ prefix and _en/_fr suffix
    const nutrient = key.replace(/^nft_/, "").replace(/_(en|fr)$/, "");

    // Convert snake_case to Title Case
    return nutrient
        .split("_")
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ");
};

export default function BilingualFieldsTable({
    fields,
    editable = true,
    onFieldChange,
}: BilingualFieldsTableProps) {
    const [isEditing, setIsEditing] = useState(false);

    const handleFieldChange = (fieldKey: string, value: string) => {
        if (onFieldChange) {
            onFieldChange(fieldKey, value);
        }
    };

    const getFieldValue = (key: string): string => {
        return fields?.[key]?.text || "";
    };

    // Dynamically build the field pairs
    const fieldPairs = useMemo(() => {
        const pairs: Array<{ label: string; enKey: string; frKey: string; isNFT: boolean }> = [];

        // Static rows first
        pairs.push({ label: "Common Name", enKey: "common_name_en", frKey: "common_name_fr", isNFT: false });
        pairs.push({ label: "Ingredients List", enKey: "ingredients_list_en", frKey: "ingredients_list_fr", isNFT: false });

        // Dynamically discover all nft_*_en fields (excluding nft_table and nft_text_block)
        const nftKeys = Object.keys(fields || {})
            .filter(key => key.startsWith("nft_") && key.endsWith("_en"))
            .filter(key => !key.includes("table") && !key.includes("text_block"))
            .sort(); // Sort for consistent ordering

        // Add NFT rows
        nftKeys.forEach(enKey => {
            const frKey = enKey.replace("_en", "_fr");
            const label = `NFT: ${formatNutrientLabel(enKey)}`;
            pairs.push({ label, enKey, frKey, isNFT: true });
        });

        return pairs;
    }, [fields]);

    return (
        <Card className="mb-6">
            <CardHeader>
                <div className="flex items-center justify-between">
                    <CardTitle className="text-base">Extracted Bilingual Fields</CardTitle>
                    {editable && (
                        <Button
                            variant="ghost"
                            size="sm"
                            className={`h-8 w-8 p-0 ${isEditing ? "text-orange-600 bg-orange-50" : "text-muted-foreground"}`}
                            onClick={() => setIsEditing(!isEditing)}
                        >
                            <Pencil className="w-4 h-4" />
                        </Button>
                    )}
                </div>
            </CardHeader>
            <CardContent>
                <div className="overflow-x-auto">
                    <table className="w-full border-collapse">
                        <thead>
                            <tr className="border-b bg-muted/30">
                                <th className="text-left p-3 font-semibold text-sm">Field</th>
                                <th className="text-left p-3 font-semibold text-sm">English</th>
                                <th className="text-left p-3 font-semibold text-sm">French</th>
                            </tr>
                        </thead>
                        <tbody>
                            {fieldPairs.map((pair, idx) => {
                                const enValue = getFieldValue(pair.enKey);
                                const frValue = getFieldValue(pair.frKey);

                                return (
                                    <tr key={idx} className="border-b hover:bg-muted/20">
                                        <td className="p-3 font-medium text-sm align-top">
                                            {pair.isNFT ? (
                                                <span className="text-blue-600">{pair.label}</span>
                                            ) : (
                                                pair.label
                                            )}
                                        </td>
                                        <td className="p-3 text-sm align-top">
                                            {isEditing ? (
                                                pair.isNFT ? (
                                                    // For NFT fields, use regular input (shorter values)
                                                    <input
                                                        type="text"
                                                        value={enValue}
                                                        onChange={(e) => handleFieldChange(pair.enKey, e.target.value)}
                                                        className="w-full px-2 py-1 text-sm border rounded"
                                                        placeholder="No value extracted"
                                                    />
                                                ) : (
                                                    <Textarea
                                                        value={enValue}
                                                        onChange={(e) => handleFieldChange(pair.enKey, e.target.value)}
                                                        className="min-h-[60px] text-sm resize-y"
                                                        placeholder="No value extracted"
                                                    />
                                                )
                                            ) : (
                                                <div className="whitespace-pre-wrap text-muted-foreground">
                                                    {enValue || <span className="italic text-muted-foreground/50">No value extracted</span>}
                                                </div>
                                            )}
                                        </td>
                                        <td className="p-3 text-sm align-top">
                                            {isEditing ? (
                                                pair.isNFT ? (
                                                    <input
                                                        type="text"
                                                        value={frValue}
                                                        onChange={(e) => handleFieldChange(pair.frKey, e.target.value)}
                                                        className="w-full px-2 py-1 text-sm border rounded"
                                                        placeholder="No value extracted"
                                                    />
                                                ) : (
                                                    <Textarea
                                                        value={frValue}
                                                        onChange={(e) => handleFieldChange(pair.frKey, e.target.value)}
                                                        className="min-h-[60px] text-sm resize-y"
                                                        placeholder="No value extracted"
                                                    />
                                                )
                                            ) : (
                                                <div className="whitespace-pre-wrap text-muted-foreground">
                                                    {frValue || <span className="italic text-muted-foreground/50">No value extracted</span>}
                                                </div>
                                            )}
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            </CardContent>
        </Card>
    );
}
