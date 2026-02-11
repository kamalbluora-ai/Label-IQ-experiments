import { useState } from "react";

export interface FeedbackItem {
    question_id: string;
    question: string;
    section: string;
    original_result: string;
    user_comment: string;
    suggested_result?: "pass" | "fail" | null;
}

interface FeedbackState {
    pendingFeedback: Map<string, FeedbackItem>;
    isSubmitting: boolean;
    lastUpdated: Date | null;
}

export function useFeedback(jobId: string) {
    const [state, setState] = useState<FeedbackState>({
        pendingFeedback: new Map(),
        isSubmitting: false,
        lastUpdated: null,
    });

    const addFeedback = (item: FeedbackItem) => {
        setState(prev => {
            const newFeedback = new Map(prev.pendingFeedback);
            newFeedback.set(item.question_id, item);
            return {
                ...prev,
                pendingFeedback: newFeedback,
                lastUpdated: new Date(),
            };
        });
    };

    const removeFeedback = (questionId: string) => {
        setState(prev => {
            const newFeedback = new Map(prev.pendingFeedback);
            newFeedback.delete(questionId);
            return {
                ...prev,
                pendingFeedback: newFeedback,
                lastUpdated: new Date(),
            };
        });
    };

    const clearAllFeedback = () => {
        setState(prev => ({
            ...prev,
            pendingFeedback: new Map(),
            lastUpdated: new Date(),
        }));
    };

    const submitAllFeedback = async (onSubmit: (feedback: FeedbackItem[]) => Promise<void>) => {
        setState(prev => ({ ...prev, isSubmitting: true }));

        try {
            const feedbackArray = Array.from(state.pendingFeedback.values());
            await onSubmit(feedbackArray);

            // Clear feedback after successful submission
            setState(prev => ({
                ...prev,
                pendingFeedback: new Map(),
                isSubmitting: false,
                lastUpdated: new Date(),
            }));
        } catch (error) {
            setState(prev => ({ ...prev, isSubmitting: false }));
            throw error;
        }
    };

    return {
        state,
        addFeedback,
        removeFeedback,
        submitAllFeedback,
        clearAllFeedback,
    };
}
