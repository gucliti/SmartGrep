// TypeScript API handler
interface User {
    id: number;
    email: string;
    role: string;
}

class ApiHandler {
    async fetchUser(userId: number): Promise<User> {
        const response = await fetch(`/api/users/${userId}`);
        return response.json();
    }

    validateEmail(email: string): boolean {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    }
}

export default ApiHandler;
