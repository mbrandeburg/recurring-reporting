#!/bin/bash

# Path to your virtual environment
VENV_PATH="venv/bin/activate"

# Path to your requirements.txt file
REQUIREMENTS_FILE="requirements.txt"

# Check if the virtual environment exists and activate it
if [ -f "$VENV_PATH" ]; then
    echo "Activating virtual environment..."
    source "$VENV_PATH"
else
    echo "Virtual environment not found. Please ensure it is created at $VENV_PATH"
    exit 1
fi

# Fist update pip
pip install --upgrade pip

# Outer loop to repeat the process twice
for i in {1..2}; do
    echo "Run #$i: Installing packages..."

    # Loop through each line in the requirements file
    while IFS= read -r package; do
        # Extract the package name before the '==' (if it exists)
        pkg_name=$(echo "$package" | cut -d'=' -f1)

        echo "Installing/upgrading package: $pkg_name"
        pip3 install "$pkg_name" --upgrade
    done < "$REQUIREMENTS_FILE"

    # Now reset it
    rm -r requirements.txt
    pip3 freeze >> requirements.txt
done

echo "Updates Complete!"