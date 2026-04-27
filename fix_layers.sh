#!/bin/bash

# Target directories and files
TARGETS="skills/ templates/ AGENTS.md CLAUDE.md"

# Find all markdown files in these targets
FILES=$(find $TARGETS -type f -name "*.md")

for file in $FILES; do
    # Replace long lists first
    sed -i '' 's/memory\/data movement, interconnect\/network, storage\/checkpoint\/data pipeline, runtime\/serving/memory\/storage\/data movement, interconnect\/network, runtime\/system/g' "$file"
    sed -i '' 's/memory\/data movement, interconnect\/network, storage\/data pipeline, or runtime\/serving/memory\/storage\/data movement, interconnect\/network, or runtime\/system/g' "$file"
    sed -i '' 's/memory\/data movement, interconnect\/network, storage\/checkpoint\/data pipeline, and runtime\/serving/memory\/storage\/data movement, interconnect\/network, and runtime\/system/g' "$file"
    sed -i '' 's/\[compute\/accelerator | memory\/data movement | interconnect\/network | storage\/checkpoint\/data pipeline | runtime\/serving\]/\[compute\/accelerator | memory\/storage\/data movement | interconnect\/network | runtime\/system\]/g' "$file"
    
    # Replace individual ones that might remain
    sed -i '' 's/storage\/checkpoint\/data pipeline/memory\/storage\/data movement/g' "$file"
    sed -i '' 's/storage\/data pipeline/memory\/storage\/data movement/g' "$file"
    
    # Replace the remaining standalone phrases (if they weren't caught by the long lists)
    sed -i '' 's/memory\/data movement/memory\/storage\/data movement/g' "$file"
    sed -i '' 's/runtime\/serving/runtime\/system/g' "$file"

    # Fix duplicates in case memory/storage/data movement was replaced twice
    sed -i '' 's/memory\/storage\/storage\/data movement/memory\/storage\/data movement/g' "$file"
    sed -i '' 's/memory\/storage\/data movement\/storage\/data movement/memory\/storage\/data movement/g' "$file"
done

echo "Done"
