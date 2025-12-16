// API client that connects to the FastAPI backend
// API base URL - FastAPI runs on port 8000
const API_BASE = "http://localhost:8000/api";

// Types matching the backend models
export interface User {
    id: string;
    name: string;
    email: string;
    avatar?: string;
}

export interface Project {
    id: string;
    name: string;
    description?: string;
    tags: string[];
    createdAt: string;
}

export interface ProjectFile {
    id: string;
    name: string;
    type: "image" | "file";
    url: string;
    tags: string[];
    projectId: string;
}

export interface Analysis {
    id: string;
    name: string;
    status: "pending" | "running" | "completed" | "failed";
    progress: number;
    resultSummary?: string;
    details?: Record<string, string>;
    createdAt: string;
    projectId: string;
}

// API functions
export const api = {
    auth: {
        login: async (): Promise<User> => {
            const res = await fetch(`${API_BASE}/auth/login`, { method: "POST" });
            if (!res.ok) throw new Error("Login failed");
            return res.json();
        },
        logout: async (): Promise<void> => {
            await fetch(`${API_BASE}/auth/logout`, { method: "POST" });
        },
    },

    projects: {
        list: async (): Promise<Project[]> => {
            const res = await fetch(`${API_BASE}/projects`);
            if (!res.ok) throw new Error("Failed to fetch projects");
            return res.json();
        },

        get: async (id: string): Promise<Project> => {
            const res = await fetch(`${API_BASE}/projects/${id}`);
            if (!res.ok) throw new Error("Project not found");
            return res.json();
        },

        create: async (data: { name: string; description?: string; tags: string[] }): Promise<Project> => {
            const res = await fetch(`${API_BASE}/projects`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data),
            });
            if (!res.ok) throw new Error("Failed to create project");
            return res.json();
        },

        update: async (id: string, data: { name: string; description?: string; tags: string[] }): Promise<Project> => {
            const res = await fetch(`${API_BASE}/projects/${id}`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data),
            });
            if (!res.ok) throw new Error("Failed to update project");
            return res.json();
        },

        delete: async (id: string): Promise<void> => {
            const res = await fetch(`${API_BASE}/projects/${id}`, { method: "DELETE" });
            if (!res.ok) throw new Error("Failed to delete project");
        },
    },

    files: {
        list: async (projectId: string): Promise<ProjectFile[]> => {
            const res = await fetch(`${API_BASE}/projects/${projectId}/files`);
            if (!res.ok) throw new Error("Failed to fetch files");
            return res.json();
        },

        upload: async (projectId: string, file: File, tags: string[]): Promise<ProjectFile> => {
            const formData = new FormData();
            formData.append("file", file);
            formData.append("tags", tags.join(","));

            const res = await fetch(`${API_BASE}/projects/${projectId}/files`, {
                method: "POST",
                body: formData,
            });
            if (!res.ok) throw new Error("Failed to upload file");
            return res.json();
        },

        delete: async (fileId: string): Promise<void> => {
            const res = await fetch(`${API_BASE}/files/${fileId}`, { method: "DELETE" });
            if (!res.ok) throw new Error("Failed to delete file");
        },
    },

    analysis: {
        list: async (projectId: string): Promise<Analysis[]> => {
            const res = await fetch(`${API_BASE}/projects/${projectId}/analyses`);
            if (!res.ok) throw new Error("Failed to fetch analyses");
            return res.json();
        },

        run: async (projectId: string, name: string): Promise<Analysis> => {
            const res = await fetch(`${API_BASE}/projects/${projectId}/analyses`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ name }),
            });
            if (!res.ok) throw new Error("Failed to start analysis");
            return res.json();
        },
    },
};
