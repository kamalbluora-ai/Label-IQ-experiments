import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

interface DetectedItem {
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
}

export default function DetectionResultsTable({ title, data, requiresQuantity = false }: DetectionResultsTableProps) {
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
        return <Badge variant="outline">OK</Badge>;
    };

    return (
        <Card>
            <CardHeader>
                <CardTitle>{title}</CardTitle>
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
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {data.detected.map((item, idx) => (
                            <TableRow key={idx}>
                                <TableCell className="font-medium">{item.name}</TableCell>
                                <TableCell>Yes</TableCell>
                                <TableCell>{item.quantity || "—"}</TableCell>
                                <TableCell>{item.category || "—"}</TableCell>
                                <TableCell className="capitalize">{item.source}</TableCell>
                                <TableCell>{getStatusFlag(item)}</TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </CardContent>
        </Card>
    );
}
