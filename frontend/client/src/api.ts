// API client that connects to the FastAPI backend (core/main.py)
// API base URL - FastAPI runs on port 8000
const API_BASE = "http://127.0.0.1:8000";

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
        verdict: "PASS" | "FAIL" | "NEEDS_REVIEW";
        issues: Array<{
            code: string;
            message: string;
            severity: string;
            references: unknown[];
        }>;
        mode: string;
        compliance_score: number;
        checks_passed: number;
        checks_total: number;
        check_results: Record<string, string>;
        relabel_plan?: Record<string, unknown>;
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

    // Files API - Now derived from Analyses/Jobs
    files: {
        list: async (projectId: string): Promise<ProjectFile[]> => {
            const stored = localStorage.getItem("mock_analyses");
            const analyses: Analysis[] = stored ? JSON.parse(stored) : [];
            const projectAnalyses = analyses.filter(a => a.projectId === projectId);

            // Extract files from analyses
            const files: ProjectFile[] = [];
            projectAnalyses.forEach(analysis => {
                const imgs = analysis.images || [];
                imgs.forEach((imgUrl, idx) => {
                    files.push({
                        id: `${analysis.id}-img-${idx}`,
                        projectId: analysis.projectId,
                        name: imgUrl.split('/').pop() || `Image ${idx + 1}`,
                        type: "image",
                        url: imgUrl, // In a real app this would be a GCS signed URL
                        tags: ["analyzed"],
                        createdAt: analysis.createdAt,
                    });
                });
            });
            return files;
        },
        upload: async (projectId: string, files: File[], tags: string[]): Promise<ProjectFile[]> => {
            // "Upload" now implies starting a job/analysis immediately
            // because the backend combines upload and processing.

            // 1. Create Job (Uploads to GCS)
            const jobResponse = await api.jobs.create(files);

            // 2. Create Analysis record linked to Job
            const objectUrls = files.map(f => URL.createObjectURL(f)); // For local preview only

            const analysisName = files.length === 1
                ? `Analysis of ${files[0].name}`
                : `Analysis of ${files.length} files`;

            const newAnalysis: Analysis = {
                id: jobResponse.job_id,
                projectId,
                name: analysisName,
                status: "running",
                progress: 0,
                createdAt: new Date().toISOString(),
                jobId: jobResponse.job_id,
                images: objectUrls, // Store local preview URLs
            };

            const stored = localStorage.getItem("mock_analyses");
            const analyses: Analysis[] = stored ? JSON.parse(stored) : [];
            analyses.push(newAnalysis);
            localStorage.setItem("mock_analyses", JSON.stringify(analyses));

            return files.map((file, idx) => ({
                id: `${newAnalysis.id}-img-${idx}`,
                projectId,
                name: file.name,
                type: "image",
                url: objectUrls[idx],
                tags,
                createdAt: newAnalysis.createdAt
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
        create: async (files: File[], metadata?: Record<string, unknown>): Promise<JobCreateResponse> => {
            const formData = new FormData();
            files.forEach((file) => {
                formData.append("files", file);
            });
            if (metadata) {
                formData.append("product_metadata", JSON.stringify(metadata));
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
    },

    // Mock projects API (stored in localStorage)
    projects: {
        list: async (): Promise<Project[]> => {
            const stored = localStorage.getItem("mock_projects");
            return stored ? JSON.parse(stored) : [];
        },
        create: async (data: { name: string; description?: string; tags?: string[] }): Promise<Project> => {
            const stored = localStorage.getItem("mock_projects");
            const projects: Project[] = stored ? JSON.parse(stored) : [];
            const newProject: Project = {
                id: `project-${Date.now()}`,
                name: data.name,
                description: data.description || "",
                tags: data.tags || [],
                createdAt: new Date().toISOString(),
                updatedAt: new Date().toISOString(),
            };
            projects.push(newProject);
            localStorage.setItem("mock_projects", JSON.stringify(projects));
            return newProject;
        },
        delete: async (id: string): Promise<void> => {
            const stored = localStorage.getItem("mock_projects");
            const projects: Project[] = stored ? JSON.parse(stored) : [];
            const filtered = projects.filter(p => p.id !== id);
            localStorage.setItem("mock_projects", JSON.stringify(filtered));
        },
        get: async (id: string): Promise<Project | null> => {
            const stored = localStorage.getItem("mock_projects");
            const projects: Project[] = stored ? JSON.parse(stored) : [];
            return projects.find(p => p.id === id) || null;
        },
        update: async (id: string, data: { name: string; description?: string; tags: string[] }): Promise<Project> => {
            const stored = localStorage.getItem("mock_projects");
            const projects: Project[] = stored ? JSON.parse(stored) : [];
            const index = projects.findIndex(p => p.id === id);
            if (index === -1) throw new Error("Project not found");
            projects[index] = {
                ...projects[index],
                name: data.name,
                description: data.description || projects[index].description,
                tags: data.tags,
                updatedAt: new Date().toISOString(),
            };
            localStorage.setItem("mock_projects", JSON.stringify(projects));
            return projects[index];
        },
    },

    // Analysis API (bridging Projects and Jobs)
    analysis: {
        run: async (projectId: string, name: string): Promise<Analysis> => {
            // This function is now somewhat redundant since "upload" starts the analysis.
            // But if we wanted to support "re-run", we'd need files again.
            // Since we deleted in-memory storage, we can't strictly re-run without re-upload.
            // For now, we'll throw to inform the user.
            throw new Error("Please upload a new file in the Files tab to start a new analysis.");
        },
        list: async (projectId: string): Promise<Analysis[]> => {
            const stored = localStorage.getItem("mock_analyses");
            let analyses: Analysis[] = stored ? JSON.parse(stored) : [];
            analyses = analyses.filter(a => a.projectId === projectId);

            // Poll status for running analyses
            const updatedAnalyses = await Promise.all(analyses.map(async (analysis) => {
                if (analysis.status === "completed" || analysis.status === "failed") return analysis;

                try {
                    const job = await api.jobs.getStatus(analysis.jobId);
                    if (job.status === "DONE") {
                        // Get report details
                        const report = await api.jobs.getReport(analysis.jobId);
                        return {
                            ...analysis,
                            status: "completed",
                            progress: 100,
                            resultSummary: `Verdict: ${report.results.verdict}. Found ${report.results.issues.length} issues.`,
                            details: {
                                verdict: report.results.verdict,
                                mode: report.results.mode,
                                issues_count: report.results.issues.length,
                                created_at: report.created_at
                            }
                        };
                    } else if (job.status === "FAILED") {
                        return { ...analysis, status: "failed", progress: 0 };
                    } else if (job.status === "PROCESSING") {
                        return { ...analysis, status: "running", progress: 50 };
                    }
                    return analysis;
                } catch (e) {
                    return analysis;
                }
            }));

            // Sync updates back to storage
            const allStored = stored ? JSON.parse(stored) : [];
            const merged = allStored.map((a: Analysis) => {
                const updated = updatedAnalyses.find(u => u.id === a.id);
                return updated || a;
            });
            localStorage.setItem("mock_analyses", JSON.stringify(merged));

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
