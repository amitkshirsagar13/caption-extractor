#!/bin/bash

# Caption Extractor Startup Script
# This script initializes and runs the caption extractor Python program

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if UV is installed
check_uv() {
    if ! command -v uv &> /dev/null; then
        print_error "UV package manager not found. Please install UV first."
        print_status "Visit: https://docs.astral.sh/uv/getting-started/installation/"
        exit 1
    fi
    print_success "UV package manager found"
}

# Function to setup virtual environment
setup_environment() {
    print_status "Setting up virtual environment and dependencies..."
    
    # Create virtual environment if it doesn't exist
    if [ ! -d ".venv" ]; then
        print_status "Creating virtual environment..."
        uv venv
    fi
    
    # Install dependencies
    print_status "Installing dependencies..."
    uv pip install -e .
    
    print_success "Environment setup completed"
}

# Function to create required directories
create_directories() {
    print_status "Creating required directories..."
    
    mkdir -p logs
    mkdir -p models
    mkdir -p docs
    mkdir -p tests
    
    # Create data directory if it doesn't exist
    if [ ! -d "data" ]; then
        mkdir -p data
        print_warning "Created empty data directory. Please add image files to process."
    fi
    
    print_success "Directories created"
}

# Function to check if data directory has images
check_data() {
    if [ ! "$(ls -A data/ 2>/dev/null)" ]; then
        print_warning "No files found in data directory."
        print_status "Please add image files (.jpg, .jpeg, .png, .bmp, .tiff, .webp) to the data folder"
        return 1
    fi
    
    # Count supported image files
    image_count=$(find data -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.bmp" -o -iname "*.tiff" -o -iname "*.webp" \) | wc -l)
    
    if [ "$image_count" -eq 0 ]; then
        print_warning "No supported image files found in data directory."
        print_status "Supported formats: .jpg, .jpeg, .png, .bmp, .tiff, .webp"
        return 1
    fi
    
    print_success "Found $image_count image files to process"
    return 0
}

# Function to display help
show_help() {
    cat << EOF
Caption Extractor - OCR text extraction using PaddleOCR

Usage: $0 [options]

Options:
    --help, -h          Show this help message
    --setup             Setup environment only (don't run processing)
    --verbose, -v       Enable verbose logging
    --config FILE       Use custom config file (default: config.yml)
    --input-folder DIR  Override input folder from config
    --threads N         Override number of threads from config
    --check             Check environment and data without processing
    
Examples:
    $0                  # Run with default settings
    $0 --verbose        # Run with verbose logging
    $0 --threads 8      # Run with 8 threads
    $0 --setup          # Setup environment only
    $0 --check          # Check environment and data

Configuration:
    Edit config.yml to customize processing settings, model parameters,
    and other options before running.

EOF
}

# Parse command line arguments
SETUP_ONLY=false
CHECK_ONLY=false
VERBOSE=""
CONFIG_FILE=""
INPUT_FOLDER=""
THREADS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --help|-h)
            show_help
            exit 0
            ;;
        --setup)
            SETUP_ONLY=true
            shift
            ;;
        --check)
            CHECK_ONLY=true
            shift
            ;;
        --verbose|-v)
            VERBOSE="--verbose"
            shift
            ;;
        --config)
            CONFIG_FILE="--config $2"
            shift 2
            ;;
        --input-folder)
            INPUT_FOLDER="--input-folder $2"
            shift 2
            ;;
        --threads)
            THREADS="--threads $2"
            shift 2
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Main execution
main() {
    print_status "Starting Caption Extractor initialization..."
    
    # Check prerequisites
    check_uv
    
    # Create directories
    create_directories
    
    # Setup environment
    setup_environment
    
    if [ "$SETUP_ONLY" = true ]; then
        print_success "Environment setup completed. Use '$0' to run processing."
        exit 0
    fi
    
    # Check configuration file
    config_file="${CONFIG_FILE#--config }"
    if [ -z "$config_file" ]; then
        config_file="config.yml"
    fi
    
    if [ ! -f "$config_file" ]; then
        print_error "Configuration file not found: $config_file"
        exit 1
    fi
    print_success "Configuration file found: $config_file"
    
    # Check data
    if ! check_data && [ "$CHECK_ONLY" != true ]; then
        print_error "No image files to process. Add images to data folder and try again."
        exit 1
    fi
    
    if [ "$CHECK_ONLY" = true ]; then
        print_success "Environment and data check completed successfully"
        exit 0
    fi
    
    # Run the caption extractor
    print_status "Starting image processing..."
    echo ""
    
    # Activate virtual environment and run the program
    source .venv/bin/activate
    python -m caption_extractor.main $CONFIG_FILE $INPUT_FOLDER $THREADS $VERBOSE
    
    exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        print_success "Processing completed successfully!"
    else
        print_error "Processing failed with exit code $exit_code"
    fi
    
    exit $exit_code
}

# Run main function
main "$@"