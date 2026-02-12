
import { useState, useCallback } from "react";

export interface TagOverride {
    question_id: string;
    new_tag: "pass" | "fail" | "needs_review";
}

export interface UserComment {
    question_id: string;
    comment: string;
}

export interface TableEdit {
    sectionKey: string;
    rowIndex: number;
    action: "edit" | "delete" | "add";
    editedData?: any;
}

export function useReportEdits() {
    // Phase 1: New State for Manual Edits
    const [tagOverrides, setTagOverrides] = useState<Map<string, TagOverride>>(new Map());
    const [userComments, setUserComments] = useState<Map<string, UserComment>>(new Map());
    const [modifiedQuestions, setModifiedQuestions] = useState<Set<string>>(new Set());

    // Legacy support for Table Edits (from previous implementation, kept for compatibility if needed)
    const [tableEdits, setTableEdits] = useState<TableEdit[]>([]);

    // --- Actions ---

    const setTagOverride = useCallback((questionId: string, tag: string) => {
        if (tag !== "pass" && tag !== "fail" && tag !== "needs_review") return;

        setTagOverrides(prev => {
            const next = new Map(prev);
            next.set(questionId, { question_id: questionId, new_tag: tag as any });
            return next;
        });

        setModifiedQuestions(prev => {
            const next = new Set(prev);
            next.add(questionId);
            return next;
        });
    }, []);

    const setUserComment = useCallback((questionId: string, comment: string) => {
        setUserComments(prev => {
            const next = new Map(prev);
            if (comment.trim() === "") {
                next.delete(questionId);
            } else {
                next.set(questionId, { question_id: questionId, comment });
            }
            return next;
        });

        setModifiedQuestions(prev => {
            const next = new Set(prev);
            next.add(questionId);
            return next;
        });
    }, []);

    // Table edit logic (kept from previous refactor)
    const addTableEdit = useCallback((edit: TableEdit) => {
        setTableEdits(prev => [...prev, edit]);
    }, []);

    const clearAll = useCallback(() => {
        setTagOverrides(new Map());
        setUserComments(new Map());
        setModifiedQuestions(new Set());
        setTableEdits([]);
    }, []);

    // --- Derived State ---

    const isQuestionModified = useCallback((questionId: string) => {
        return modifiedQuestions.has(questionId);
    }, [modifiedQuestions]);

    const getModifiedQuestions = useCallback(() => {
        return Array.from(modifiedQuestions);
    }, [modifiedQuestions]);

    const hasPendingChanges = modifiedQuestions.size > 0 || tableEdits.length > 0;
    const pendingCount = modifiedQuestions.size + tableEdits.length;

    return {
        // State
        tagOverrides,
        userComments,
        modifiedQuestions,
        tableEdits,

        // Actions
        setTagOverride,
        setUserComment,
        addTableEdit,
        clearAll,

        // Helpers
        isQuestionModified,
        getModifiedQuestions,

        // Status
        hasPendingChanges,
        pendingCount
    };
}
