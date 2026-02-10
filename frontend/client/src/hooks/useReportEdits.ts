import { useState, useCallback } from "react";

export interface SectionComment {
    sectionKey: string;  // e.g., "bilingual", "common_name"
    comment: string;
}

export interface TableRowEdit {
    sectionKey: string;
    rowIndex: number;
    action: "edit" | "delete" | "add";
    editedData?: Record<string, any>;
}

export function useReportEdits() {
    const [sectionComments, setSectionComments] = useState<Map<string, string>>(new Map());
    const [tableEdits, setTableEdits] = useState<TableRowEdit[]>([]);
    const [isReevaluating, setIsReevaluating] = useState(false);

    const setComment = useCallback((sectionKey: string, comment: string) => {
        setSectionComments(prev => {
            const next = new Map(prev);
            if (comment.trim()) {
                next.set(sectionKey, comment);
            } else {
                next.delete(sectionKey);
            }
            return next;
        });
    }, []);

    const addTableEdit = useCallback((edit: TableRowEdit) => {
        setTableEdits(prev => {
            // Remove existing edit for same row if any
            const filtered = prev.filter(
                e => !(e.sectionKey === edit.sectionKey && e.rowIndex === edit.rowIndex)
            );
            return [...filtered, edit];
        });
    }, []);

    const clearAll = useCallback(() => {
        setSectionComments(new Map());
        setTableEdits([]);
    }, []);

    const hasPendingChanges = sectionComments.size > 0 || tableEdits.length > 0;
    const pendingCount = sectionComments.size + tableEdits.length;

    return {
        sectionComments,
        tableEdits,
        setComment,
        addTableEdit,
        clearAll,
        hasPendingChanges,
        pendingCount,
        isReevaluating,
        setIsReevaluating,
    };
}
