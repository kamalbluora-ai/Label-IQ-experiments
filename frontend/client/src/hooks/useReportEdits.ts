import { useState, useCallback } from "react";

export interface TableRowEdit {
    sectionKey: string;
    rowIndex: number;
    action: "edit" | "delete" | "add";
    editedData?: Record<string, any>;
}

export interface QuestionOverride {
    question_id: string;
    new_tag: string;
    new_rationale: string;
}

export function useReportEdits() {
    // Map<question_id, comment>
    const [questionComments, setQuestionComments] = useState<Map<string, string>>(new Map());

    // Map<question_id, OverrideResult> - stores the result from re-evaluation
    const [questionOverrides, setQuestionOverrides] = useState<Map<string, QuestionOverride>>(new Map());

    // Set<question_id> - tracks which questions are currently updating
    const [pendingQuestions, setPendingQuestions] = useState<Set<string>>(new Set());

    const [tableEdits, setTableEdits] = useState<TableRowEdit[]>([]);
    const [isReevaluating, setIsReevaluating] = useState(false);

    /**
     * Add or update a comment for a specific question.
     */
    const setQuestionComment = useCallback((questionId: string, comment: string) => {
        setQuestionComments(prev => {
            const next = new Map(prev);
            if (comment.trim()) {
                next.set(questionId, comment);
            } else {
                next.delete(questionId);
            }
            return next;
        });
    }, []);

    /**
     * Merge a re-evaluation result into the local state overrides.
     */
    const addQuestionOverride = useCallback((override: QuestionOverride) => {
        setQuestionOverrides(prev => {
            const next = new Map(prev);
            next.set(override.question_id, override);
            return next;
        });

        // Also clear the comment since it's now applied
        setQuestionComments(prev => {
            const next = new Map(prev);
            next.delete(override.question_id);
            return next;
        });
    }, []);

    /**
     * Mark a question as pending update.
     */
    const setQuestionPending = useCallback((questionId: string, isPending: boolean) => {
        setPendingQuestions(prev => {
            const next = new Set(prev);
            if (isPending) {
                next.add(questionId);
            } else {
                next.delete(questionId);
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
        setQuestionComments(new Map());
        setTableEdits([]);
        setQuestionOverrides(new Map());
        setPendingQuestions(new Set());
    }, []);

    const hasPendingChanges = questionComments.size > 0 || tableEdits.length > 0;
    const pendingCount = questionComments.size + tableEdits.length;

    return {
        questionComments,
        questionOverrides,
        pendingQuestions,
        tableEdits,

        setQuestionComment,
        addQuestionOverride,
        setQuestionPending,
        addTableEdit,
        clearAll,

        hasPendingChanges,
        pendingCount,
        isReevaluating,
        setIsReevaluating,
    };
}
