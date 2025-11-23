// Test C file for SmartGrep indexing
#include <stdio.h>
#include <string.h>

struct database_config {
    char connection_string[256];
    int timeout;
};

int connect_to_database(struct database_config *config) {
    printf("Connecting to database: %s\n", config->connection_string);
    return 0;
}

int authenticate_user(const char *username, const char *password) {
    // Authentication middleware
    if (strcmp(username, "admin") == 0 && strcmp(password, "secret") == 0) {
        return 1;
    }
    return 0;
}

void log_message(const char *message) {
    printf("[LOG] %s\n", message);
}

int main() {
    struct database_config config;
    strcpy(config.connection_string, "postgres://localhost:5432");
    config.timeout = 30;
    
    connect_to_database(&config);
    return 0;
}
