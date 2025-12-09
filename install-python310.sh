#!/bin/bash
set -e

PYTHON_VERSION="3.10.13"
BUILD_DATE="20231002"
INSTALL_DIR="/opt/python310"

echo "Installing Python ${PYTHON_VERSION} to ${INSTALL_DIR} using pre-compiled binaries..."

# Detect architecture
ARCH=$(uname -m)
if [ "$ARCH" = "x86_64" ]; then
    PLATFORM="x86_64-unknown-linux-gnu"
elif [ "$ARCH" = "aarch64" ]; then
    PLATFORM="aarch64-unknown-linux-gnu"
else
    echo "Unsupported architecture: $ARCH"
    exit 1
fi

# Download Python standalone build
DOWNLOAD_URL="https://github.com/indygreg/python-build-standalone/releases/download/${BUILD_DATE}/cpython-${PYTHON_VERSION}+${BUILD_DATE}-${PLATFORM}-install_only.tar.gz"
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"

echo "Downloading Python binaries from python-build-standalone..."
echo "URL: ${DOWNLOAD_URL}"
wget -q --show-progress "${DOWNLOAD_URL}" -O python.tar.gz

# Create installation directory
echo "Creating installation directory..."
sudo mkdir -p "${INSTALL_DIR}"

# Extract binaries
echo "Extracting Python to ${INSTALL_DIR}..."
sudo tar -xzf python.tar.gz -C "${INSTALL_DIR}" --strip-components=1

# Set proper permissions
sudo chmod -R 755 "${INSTALL_DIR}"

# Upgrade pip to latest version
echo "Upgrading pip..."
"${INSTALL_DIR}/bin/python3.10" -m pip install --upgrade pip

# Create convenience symlinks
echo "Creating convenience symlinks..."
sudo ln -sf "${INSTALL_DIR}/bin/python3.10" "${INSTALL_DIR}/bin/python"
sudo ln -sf "${INSTALL_DIR}/bin/python3.10" "${INSTALL_DIR}/bin/python3"
sudo ln -sf "${INSTALL_DIR}/bin/pip3" "${INSTALL_DIR}/bin/pip"

# Cleanup
cd /
rm -rf "$TEMP_DIR"

# Verify installation
echo ""
echo "✓ Installation complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Installation Directory: ${INSTALL_DIR}"
echo "Python Version: $("${INSTALL_DIR}/bin/python3.10" --version)"
echo "Pip Version: $("${INSTALL_DIR}/bin/pip" --version)"
echo ""
echo "Usage:"
echo "  ${INSTALL_DIR}/bin/python3.10"
echo "  ${INSTALL_DIR}/bin/pip"
echo ""
echo "Create virtual environment:"
echo "  ${INSTALL_DIR}/bin/python3.10 -m venv myproject"
echo "  source myproject/bin/activate"
echo ""
echo "Add to PATH (add to ~/.bashrc for permanent):"
echo "  export PATH=\"${INSTALL_DIR}/bin:\$PATH\""
echo ""
echo "Your system Python is unchanged:"
which python3 && python3 --version || echo "No system python3 in PATH"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"