// API client that connects to the FastAPI backend
// API base URL - set at build time via VITE_API_BASE (Cloud Run)
// const API_BASE = import.meta.env.VITE_API_BASE || "https://localhost:8000/api";
declare global {
    interface Window {
        __CONFIG__?: { API_BASE?: string };
    }
}

export const API_BASE =
    window.__CONFIG__?.API_BASE ??
    import.meta.env.VITE_API_BASE ??
    "http://localhost:8000/api";

// Types matching the new GCS-based backend
export interface Job {
    job_id: string;
    status: "QUEUED" | "PROCESSING" | "DONE" | "FAILED";
    mode?: string;
    created_at?: string;
    report_path?: string;
    images?: string[];
}

export interface JobCreateResponse {
    job_id: string;
    status: "QUEUED";
    images: number;
}

export interface ComplianceReport {
    job_id: string;
    created_at: string;
    mode: string;
    source_images: string[];
    label_facts: Record<string, unknown>;
    results: {
        // AI Agent results - nested under agent name
        common_name?: {
            check_results: Array<{
                question_id: string;
                question: string;
                result: "pass" | "fail" | "needs_review";
                selected_value?: string;
                rationale: string;
                section: string;
            }>;
        };
        ingredients?: {
            check_results: Array<{
                question_id: string;
                question: string;
                result: "pass" | "fail" | "needs_review";
                selected_value?: string;
                rationale: string;
                section: string;
            }>;
        };
        date_marking?: {
            check_results: Array<{
                question_id: string;
                question: string;
                result: "pass" | "fail" | "needs_review";
                selected_value?: string;
                rationale: string;
                section: string;
            }>;
        };
        fop_symbol?: {
            check_results: Array<{
                question_id: string;
                question: string;
                result: "pass" | "fail" | "needs_review";
                selected_value?: string;
                rationale: string;
                section: string;
            }>;
        };
        bilingual?: {
            check_results: Array<{
                question_id: string;
                question: string;
                result: "pass" | "fail" | "needs_review";
                selected_value?: string;
                rationale: string;
                section: string;
            }>;
        };
        irradiation?: {
            check_results: Array<{
                question_id: string;
                question: string;
                result: "pass" | "fail" | "needs_review";
                selected_value?: string;
                rationale: string;
                section: string;
            }>;
        };
        country_origin?: {
            check_results: Array<{
                question_id: string;
                question: string;
                result: "pass" | "fail" | "needs_review";
                selected_value?: string;
                rationale: string;
                section: string;
            }>;
        };
        claim_tag?: {
            section: string;
            summary?: string;
            results: Array<{
                question_id: string;
                question: string;
                result: "needs_review";
                selected_value?: string;
                rationale: string;
                section: string; // Added to match other agents
                metadata?: {
                    claim_type: string;
                    certification_body: string | null;
                    rule_violations: string[];
                    supporting_evidence: string[];
                };
            }>;
        };
        // NFT Audit results
        nutrition_facts?: {
            nutrient_audits: Array<{
                nutrient_name: string;
                original_value: number;
                expected_value: number | null;
                unit: string;
                is_dv: boolean;
                status: string;
                message: string;
                rule_applied: string | null;
            }>;
            cross_field_audits: Array<{
                check_name: string;
                status: string;
                message: string;
                tolerance: string | null;
            }>;
        };
        // Detection results
        sweeteners?: {
            detected: Array<{
                name: string;
                category?: string;
                source: string;
                quantity?: string | null;
            }>;
            has_quantity_sweeteners?: boolean;
            has_no_quantity_sweeteners?: boolean;
        };
        supplements?: {
            detected: Array<{
                name: string;
                category?: string;
                source: string;
            }>;
            has_supplements?: boolean;
        };
        additives?: {
            detected: Array<{
                name: string;
                category?: string;
                source: string;
            }>;
            has_additives?: boolean;
        };
    };
    cfia_evidence: Record<string, unknown>;
}

// Legacy types (kept for backward compatibility)
export interface User {
    id: string;
    name: string;
    email: string;
    avatar?: string;
}

// Project type for dashboard
export interface Project {
    id: string;
    name: string;
    description: string;
    tags: string[];
    createdAt: string;
    updatedAt: string;
}

// Project file type
export interface ProjectFile {
    id: string;
    projectId: string;
    name: string;
    type: "image" | "document";
    url: string;
    tags: string[];
    createdAt: string;
    fileObject?: File; // Keep reference to actual file for upload
}

// Analysis type
export interface Analysis {
    id: string;
    projectId: string;
    name: string;
    status: "running" | "completed" | "failed";
    progress: number;
    createdAt: string;
    jobId: string;
    resultSummary?: string;
    details?: Record<string, unknown>;
    images?: string[]; // Store image names/urls here
}

// API functions
export const api = {
    // Health check
    health: async (): Promise<{ ok: boolean }> => {
        const res = await fetch(`${API_BASE}/healthz`);
        return res.json();
    },

    // Generic POST method
    post: async (endpoint: string, body: unknown): Promise<{ data: any }> => {
        const res = await fetch(`${API_BASE}${endpoint}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });
        if (!res.ok) throw new Error(`POST ${endpoint} failed`);
        const data = await res.json();
        return { data };
    },

    // Files API - Derived from analyses
    files: {
        list: async (projectId: string): Promise<ProjectFile[]> => {
            const analyses = await api.analysis.list(projectId);

            const files: ProjectFile[] = [];
            for (const analysis of analyses) {
                try {
                    const imagesData = await api.jobs.getImages(analysis.jobId);
                    imagesData.images.forEach((img, idx) => {
                        files.push({
                            id: `${analysis.id}-img-${idx}`,
                            projectId: analysis.projectId,
                            name: img.name,
                            type: "image",
                            url: `${API_BASE}${img.url}`,
                            tags: ["analyzed"],
                            createdAt: analysis.createdAt,
                        });
                    });
                } catch (e) {
                    console.warn(`Could not fetch images for analysis ${analysis.id}`, e);
                }
            }
            return files;
        },
        upload: async (projectId: string, files: File[], tags: string[], metadata?: Record<string, unknown>): Promise<ProjectFile[]> => {
            // Create Job (Uploads to GCS) - backend will create analysis record
            const formData = new FormData();
            files.forEach((file) => {
                formData.append("files", file);
            });
            if (metadata) {
                formData.append("product_metadata", JSON.stringify(metadata));
            }
            if (tags && tags.length > 0) {
                formData.append("tags", JSON.stringify(tags));
            }
            formData.append("project_id", projectId);

            const res = await fetch(`${API_BASE}/v1/jobs`, {
                method: "POST",
                body: formData,
            });
            if (!res.ok) throw new Error("Failed to create job");
            const jobResponse: JobCreateResponse = await res.json();

            return files.map((file, idx) => ({
                id: `${jobResponse.job_id}-img-${idx}`,
                projectId,
                name: file.name,
                type: "image",
                url: `${API_BASE}/v1/jobs/${jobResponse.job_id}/images/${idx}`,
                tags,
                createdAt: new Date().toISOString()
            }));
        },
        delete: async (fileId: string): Promise<void> => {
            // Cannot delete individual files easily since they are part of jobs
            // For now, no-op or throw
            console.warn("Delete not supported in this architecture view");
        },
    },

    // Jobs API - the main workflow
    jobs: {
        /**
         * Upload images and create a new compliance job.
         * Mode is auto-detected based on language in the images.
         */
        create: async (files: File[], metadata?: Record<string, unknown>, tags?: string[]): Promise<JobCreateResponse> => {
            const formData = new FormData();
            files.forEach((file) => {
                formData.append("files", file);
            });
            if (metadata) {
                formData.append("product_metadata", JSON.stringify(metadata));
            }
            if (tags && tags.length > 0) {
                formData.append("tags", JSON.stringify(tags));
            }

            const res = await fetch(`${API_BASE}/v1/jobs`, {
                method: "POST",
                body: formData,
            });
            if (!res.ok) throw new Error("Failed to create job");
            return res.json();
        },

        /**
         * Get job status. Poll this until status is "DONE" or "FAILED".
         */
        getStatus: async (jobId: string): Promise<Job> => {
            const res = await fetch(`${API_BASE}/v1/jobs/${jobId}`);
            if (!res.ok) throw new Error("Job not found");
            return res.json();
        },

        /**
         * Get the compliance report for a completed job.
         */
        getReport: async (jobId: string): Promise<ComplianceReport> => {
            const res = await fetch(`${API_BASE}/v1/jobs/${jobId}/report`);
            if (!res.ok) throw new Error("Report not found");
            return res.json();
        },

        /**
         * Poll job status until complete.
         * Returns the final report when done.
         */
        waitForCompletion: async (
            jobId: string,
            onProgress?: (job: Job) => void,
            pollIntervalMs = 2000
        ): Promise<ComplianceReport> => {
            while (true) {
                const job = await api.jobs.getStatus(jobId);
                if (onProgress) onProgress(job);

                if (job.status === "DONE") {
                    return api.jobs.getReport(jobId);
                }
                if (job.status === "FAILED") {
                    throw new Error("Job failed");
                }

                await new Promise((resolve) => setTimeout(resolve, pollIntervalMs));
            }
        },

        /**
         * Save manual report edits (tags and comments) to backend.
         */
        saveReportEdits: async (jobId: string, edits: {
            question_id: string;
            new_tag?: string;
            user_comment?: string;
        }[]): Promise<void> => {
            const res = await fetch(`${API_BASE}/v1/jobs/${jobId}/save-edits`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ edits }),
            });
            if (!res.ok) throw new Error("Failed to save report edits");
        },

        /**
         * Get images for a job.
         */
        getImages: async (jobId: string): Promise<{ images: { name: string; url: string }[] }> => {
            const res = await fetch(`${API_BASE}/v1/jobs/${jobId}/images`);
            if (!res.ok) throw new Error("Failed to fetch images");
            return res.json();
        },
    },

    // Projects API (backend-persisted)
    projects: {
        list: async (): Promise<Project[]> => {
            const res = await fetch(`${API_BASE}/v1/projects`);
            if (!res.ok) throw new Error("Failed to list projects");
            return res.json();
        },
        create: async (data: { name: string; description?: string; tags?: string[] }): Promise<Project> => {
            const res = await fetch(`${API_BASE}/v1/projects`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data),
            });
            if (!res.ok) throw new Error("Failed to create project");
            return res.json();
        },
        delete: async (id: string): Promise<void> => {
            const res = await fetch(`${API_BASE}/v1/projects/${id}`, {
                method: "DELETE",
            });
            if (!res.ok) throw new Error("Failed to delete project");
        },
        get: async (id: string): Promise<Project | null> => {
            const res = await fetch(`${API_BASE}/v1/projects/${id}`);
            if (!res.ok) return null;
            return res.json();
        },
        update: async (id: string, data: { name: string; description?: string; tags: string[] }): Promise<Project> => {
            const res = await fetch(`${API_BASE}/v1/projects/${id}`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data),
            });
            if (!res.ok) throw new Error("Failed to update project");
            return res.json();
        },
    },

    // Analysis API (backend-persisted)
    analysis: {
        run: async (projectId: string, name: string): Promise<Analysis> => {
            throw new Error("Please upload a new file in the Files tab to start a new analysis.");
        },
        list: async (projectId: string): Promise<Analysis[]> => {
            // Fetch from backend
            const res = await fetch(`${API_BASE}/v1/projects/${projectId}/analyses`);
            if (!res.ok) throw new Error("Failed to list analyses");
            let analyses: Analysis[] = await res.json();

            // Poll status for running analyses
            const updatedAnalyses = await Promise.all(analyses.map(async (analysis) => {
                if (analysis.status === "completed" || analysis.status === "failed") return analysis;

                try {
                    const job = await api.jobs.getStatus(analysis.jobId);
                    if (job.status === "DONE") {
                        let resultSummary = "Analysis complete.";
                        let details: Record<string, unknown> = {};

                        try {
                            const report = await api.jobs.getReport(analysis.jobId);
                            resultSummary = "Analysis complete.";
                            details = {
                                mode: report.mode,
                                created_at: report.created_at
                            };
                        } catch (e) {
                            console.warn("Could not fetch report for completed job:", e);
                        }

                        return {
                            ...analysis,
                            status: "completed" as const,
                            progress: 100,
                            resultSummary,
                            details,
                        };
                    } else if (job.status === "FAILED") {
                        return { ...analysis, status: "failed" as const, progress: 0 };
                    } else if (job.status === "PROCESSING") {
                        const createdAt = new Date(analysis.createdAt).getTime();
                        const elapsed = (Date.now() - createdAt) / 1000;
                        const estimatedProgress = Math.min(90, Math.round(30 * Math.log10(elapsed + 1)));
                        return { ...analysis, status: "running" as const, progress: estimatedProgress };
                    }
                    return analysis;
                } catch (e) {
                    return analysis;
                }
            }));

            return updatedAnalyses as Analysis[];
        },
        downloadReport: async (analysisId: string): Promise<Blob> => {
            const report = await api.jobs.getReport(analysisId);
            const jsonStr = JSON.stringify(report, null, 2);
            return new Blob([jsonStr], { type: "application/json" });
        },
    },

    // Mock auth (placeholder, not connected to backend)
    auth: {
        getMockUser: (): User => ({
            id: "user-1",
            name: "Label IQ",
            email: "labeliq@bluora.ai",
            avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=labeliq",
        }),
    },
};
