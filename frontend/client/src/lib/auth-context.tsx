import { createContext, useContext, useState, ReactNode } from "react";
import { api, User } from "@/api";

interface AuthContextType {
    user: User | null;
    isLoading: boolean;
    login: (username?: string, password?: string) => Promise<boolean>;
    logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [isLoading, setIsLoading] = useState(false);

    const login = async (username?: string, password?: string) => {
        setIsLoading(true);

        // Mock check
        if (username === "admin" && password === "admin") {
            // Simulate a brief loading state
            await new Promise(resolve => setTimeout(resolve, 500));
            setUser(api.auth.getMockUser());
            setIsLoading(false);
            return true;
        } else {
            // Simulate a brief loading state
            await new Promise(resolve => setTimeout(resolve, 500));
            setIsLoading(false);
            return false;
        }
    };

    const logout = () => {
        setUser(null);
    };

    return (
        <AuthContext.Provider value={{ user, isLoading, login, logout }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error("useAuth must be used within an AuthProvider");
    }
    return context;
}
