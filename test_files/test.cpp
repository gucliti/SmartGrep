// Test C++ file for SmartGrep indexing
#include <iostream>
#include <string>

namespace database {
    class Connection {
    private:
        std::string connection_string;
        int pool_size;
        
    public:
        Connection(const std::string& conn_str) 
            : connection_string(conn_str), pool_size(10) {}
        
        bool connect() {
            std::cout << "Connecting to: " << connection_string << std::endl;
            return true;
        }
        
        void disconnect() {
            std::cout << "Disconnecting..." << std::endl;
        }
    };
}

struct User {
    std::string username;
    std::string email;
};

bool authenticate_user(const std::string& username, const std::string& password) {
    // Simple authentication middleware
    return username == "admin" && password == "secret";
}

int main() {
    database::Connection db("postgres://localhost:5432");
    db.connect();
    return 0;
}
