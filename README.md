# Threaded File Management System

A modern file management system that supports multi-threaded file operations with a graphical user interface.

## Features

- Create, delete, and manage files and directories
- Multi-threaded file operations
- Real-time file system monitoring
- Memory map visualization
- Modern and intuitive user interface

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

## Installation

1. Clone the repository:

git clone <https://github.com/Kiranwaqar/Threaded_File_Management_System.git>
cd <repository-directory>


2. Create and activate a virtual environment:

python -m venv myenv
# On Windows
myenv\Scripts\activate


3. Install required packages:

pip install -r requirements.txt


## Running the Application

1. Make sure you're in the virtual environment (you should see `(myenv)` at the start of your command prompt)

2. Run the application:

python fileSystem.py


## Usage

1. **Main Interface**
   - Use the toolbar buttons for file operations
   - Navigate directories using the file tree
   - View file contents by double-clicking files

2. **Thread Manager**
   - Click the "🧵 Thread Manager" button to open the thread manager
   - Enter the number of threads you want to create
   - Click "Start Threads" to begin execution
   - Monitor thread status and execution time in the table
   - View input/output files using the respective buttons

3. **File Operations**
   - Create new files and directories
   - Move files between directories
   - Delete files and directories
   - View memory map of the file system



## Notes

- The application creates necessary files and directories automatically
- Thread input/output files are created when threads are started
- Use the refresh button (🔄) to update the file system view
- Memory map can be viewed using the "🗺️ Memory Map" button

