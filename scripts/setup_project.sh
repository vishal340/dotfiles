#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Ask user for the project name
read -p "Enter your project name (e.g., my_project): " PROJECT_NAME

# Convert project name to lowercase and replace spaces with underscores
PROJECT_NAME=$(echo "$PROJECT_NAME" | tr '[:upper:]' '[:lower:]' | tr ' ' '_')

echo "Creating C++ project structure for: $PROJECT_NAME..."

# 1. Create directories (cleaner to do it from the root directory context)
mkdir -p "$PROJECT_NAME/src"
mkdir -p "$PROJECT_NAME/include"

# Move into the project directory
cd "$PROJECT_NAME"

# 2. Create .gitignore
cat <<'EOF' >.gitignore
build/
.cache/
.vscode/
.idea/
*.user
EOF

# 3. Create README.md
cat <<EOF >README.md
# $PROJECT_NAME

A small C++ project template.

## How to Build

\`\`\`bash
mkdir build && cd build
cmake ..
cmake --build .
./$PROJECT_NAME
\`\`\`
EOF

# 4. Create CMakeLists.txt (With Clangd Support Added)
cat <<EOF >CMakeLists.txt
cmake_minimum_required(VERSION 3.15)
project($PROJECT_NAME VERSION 1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Enable compile_commands.json generation for Clangd
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

add_executable($PROJECT_NAME
    src/main.cpp
    src/utils.cpp
)

target_include_directories($PROJECT_NAME PRIVATE include)

# Automatically symlink compile_commands.json to the project root for Clangd
if(NOT EXISTS "\${CMAKE_SOURCE_DIR}/compile_commands.json")
    execute_process(
        COMMAND \${CMAKE_COMMAND} -E create_symlink
        "\${CMAKE_BINARY_DIR}/compile_commands.json"
        "\${CMAKE_SOURCE_DIR}/compile_commands.json"
    )
endif()
EOF

# 6. Create src/utils.cpp
cat <<EOF >src/utils.cpp
#include "$PROJECT_NAME/utils.hpp"
#include <iostream>

namespace utils {
    void print_hello() {
        std::cout << "Hello from the generated project structure!" << std::endl;
    }
}
EOF

# 7. Create src/main.cpp
cat <<EOF >src/main.cpp
#include "$PROJECT_NAME/utils.hpp"

int main() {
    utils::print_hello();
    return 0;
}
EOF

echo "----------------------------------------"
echo "Success! Project '$PROJECT_NAME' is ready."
echo "To build it and generate compile-commands for clangd, run:"
echo "  cd $PROJECT_NAME"
echo "  mkdir build && cd build"
echo "  cmake .."
echo "  cmake --build ."
echo "  ./$PROJECT_NAME"
echo "----------------------------------------"
