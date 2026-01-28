import { Badge } from "@/components/ui/badge";

interface FeedbackBadgeProps {
    count: number;
}

export default function FeedbackBadge({ count }: FeedbackBadgeProps) {
    if (count === 0) return null;

    return (
        <Badge variant="outline" className="bg-blue-100 text-blue-800 border-blue-200">
            💬 {count}
        </Badge>
    );
}
