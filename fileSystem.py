# File System Implementation for Threaded File Management System
# CS-330 Operating System Lab 11

import os
import json
import time
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
import threading
import sys

class FileObject:
    """Class representing an open file in the file system"""
    
    def __init__(self, file_system, file_name: str, mode: str):
        self.file_system = file_system
        self.file_name = file_name
        self.mode = mode
        self.file_meta = file_system.get_file_metadata(file_name)
        self.lock = threading.Lock()  # Add lock for thread safety
        self.content = ""  # Store file content in memory
        
        # Check if file exists
        if not self.file_meta and mode != 'w':
            raise FileNotFoundError(f"File '{file_name}' not found")
        
        # If file is new and in write mode, create it
        if not self.file_meta and mode == 'w':
            with self.file_system.lock:  # Use file system lock for metadata operations
                self.file_meta = {
                    'name': file_name,
                    'size': 0,
                    'creation_time': time.time(),
                    'modified_time': time.time(),
                    'start_pos': file_system._allocate_space(0),
                    'is_directory': False
                }
                
                # Add file to current directory
                current_dir = file_system.get_current_directory_meta()
                if file_name not in current_dir['files']:
                    current_dir['files'].append(file_name)
                
                # Update file system metadata
                path_parts = file_system.current_path.split('/')
                path_parts = [p for p in path_parts if p]
                
                dir_path = ""
                if path_parts:
                    dir_path = '/' + '/'.join(path_parts)
                
                file_system.fs_metadata['directories'][dir_path]['files'].append(file_name)
                file_system.fs_metadata['files'][file_name] = self.file_meta
                file_system._save_metadata()
        
        # If file exists, read its content
        elif self.file_meta:
            with open(self.file_system.data_file, 'rb') as df:
                df.seek(self.file_meta['start_pos'])
                self.content = df.read(self.file_meta['size']).decode('utf-8').rstrip('\0')
    
    # Implements requirement 6.a - append mode for writing
    def write_to_file(self, text: str):
        """Write to the file in append mode"""
        if self.mode != 'w':
            raise IOError("File not opened in write mode")
        
        with self.lock:  # Use file lock for write operations
            # Update content in memory
            self.content += text
            
            # Write data to file
            with open(self.file_system.data_file, 'r+b') as df:
                # Move to the start position of the file
                df.seek(self.file_meta['start_pos'])
                # Write the content
                df.write(self.content.encode('utf-8'))
                # Update file size
                self.file_meta['size'] = len(self.content.encode('utf-8'))
            
            # Update file metadata
            with self.file_system.lock:  # Use file system lock for metadata operations
                self.file_meta['modified_time'] = time.time()
                self.file_system.fs_metadata['files'][self.file_name]['size'] = self.file_meta['size']
                self.file_system.fs_metadata['files'][self.file_name]['modified_time'] = self.file_meta['modified_time']
                self.file_system._save_metadata()
    
    # Implements requirement 6.b - write at a specific position
    def write_to_file_at(self, write_at: int, text: str):
        """Write to a specific position in the file"""
        if self.mode != 'w':
            raise IOError("File not opened in write mode")
        
        # Ensure write_at position is valid
        if write_at < 0:
            raise ValueError("Position must be non-negative")
        
        text_bytes = text.encode('utf-8')
        end_pos = write_at + len(text_bytes)
        
        # If writing beyond current size, extend the file
        if end_pos > self.file_meta['size']:
            self.file_meta['size'] = end_pos
            self.file_system.fs_metadata['files'][self.file_name]['size'] = end_pos
        
        # Write data at specific position
        with open(self.file_system.data_file, 'r+b') as df:
            df.seek(self.file_meta['start_pos'] + write_at)
            df.write(text_bytes)
        
        # Update metadata
        self.file_meta['modified_time'] = time.time()
        self.file_system.fs_metadata['files'][self.file_name]['modified_time'] = self.file_meta['modified_time']
        self.file_system._save_metadata()  # Implements requirement 7 (persistence)
    
    # Implements requirement 8.a - sequential access for reading
    def read_from_file(self) -> str:
        """Read entire file content"""
        return self.content
    
    # Implements requirement 8.b - read from specific position
    def read_from_file_at(self, start: int, size: int) -> str:
        """Read part of file from start position for size bytes"""
        if start < 0 or size < 0:
            raise ValueError("Start and size must be non-negative")
        
        if start >= self.file_meta['size']:
            return ""
        
        # Adjust size if it goes beyond file end
        if start + size > self.file_meta['size']:
            size = self.file_meta['size'] - start
        
        with open(self.file_system.data_file, 'rb') as df:
            df.seek(self.file_meta['start_pos'] + start)
            content = df.read(size)
            return content.decode('utf-8')
        
    # Implements requirement 10 - Move content within a file
    def move_within_file(self, start: int, size: int, target: int):
        """Move content within the file from start position for size bytes to target position"""
        if self.mode != 'w':
            raise IOError("File not opened in write mode")
        
        if start < 0 or size < 0 or target < 0:
            raise ValueError("Start, size, and target must be non-negative")
        
        if start >= self.file_meta['size']:
            return  # Nothing to move
        
        # Adjust size if it goes beyond file end
        if start + size > self.file_meta['size']:
            size = self.file_meta['size'] - start
        
        # Read the content to be moved
        with open(self.file_system.data_file, 'rb') as df:
            df.seek(self.file_meta['start_pos'] + start)
            content = df.read(size)
        
        # If target is beyond current file size, extend the file
        new_size = max(self.file_meta['size'], target + size)
        
        # If move requires file expansion
        if new_size > self.file_meta['size']:
            self.file_meta['size'] = new_size
            self.file_system.fs_metadata['files'][self.file_name]['size'] = new_size
        
        # Write the content to the target position
        with open(self.file_system.data_file, 'r+b') as df:
            df.seek(self.file_meta['start_pos'] + target)
            df.write(content)
        
        # Update metadata
        self.file_meta['modified_time'] = time.time()
        self.file_system.fs_metadata['files'][self.file_name]['modified_time'] = self.file_meta['modified_time']
        self.file_system._save_metadata()  # Implements requirement 7 (persistence)

    # Implements requirement 11 - Truncate file to specified size
    def truncate_file(self, max_size: int):
        """Truncate file to specified maximum size"""
        if self.mode != 'w':
            raise IOError("File not opened in write mode")
        
        if max_size < 0:
            raise ValueError("Maximum size must be non-negative")
        
        # If file is already smaller than max_size, do nothing
        if self.file_meta['size'] <= max_size:
            return
        
        # Update file size
        self.file_meta['size'] = max_size
        self.file_system.fs_metadata['files'][self.file_name]['size'] = max_size
        
        # Update metadata
        self.file_meta['modified_time'] = time.time()
        self.file_system.fs_metadata['files'][self.file_name]['modified_time'] = self.file_meta['modified_time']
        self.file_system._save_metadata()  # Implements requirement 7 (persistence)


class FileSystem:
    """Main file system class that implements the distributed file management system"""
    
    # Constants
    METADATA_FILE = "fs_metadata.json"
    DEFAULT_MAX_SIZE = 1024 * 1024  # 1MB default size for data file
    
    def __init__(self, data_file: str = "sample.dat", max_size: int = DEFAULT_MAX_SIZE):
        self.data_file = data_file
        self.max_size = max_size
        self.open_files = {}  # Track open files
        self.current_path = "/"  # Start at root
        self.lock = threading.Lock()  # Add lock for thread safety
        
        # Initialize the file system
        self._initialize()
    
    def _initialize(self):
        """Initialize or load the file system structure"""
        with self.lock:  # Use lock for initialization
            # Check if metadata exists
            if os.path.exists(self.METADATA_FILE):
                # Load existing metadata
                with open(self.METADATA_FILE, 'r') as f:
                    self.fs_metadata = json.load(f)
                    # Convert free_space lists to tuples
                    if 'free_space' in self.fs_metadata:
                        self.fs_metadata['free_space'] = [tuple(block) for block in self.fs_metadata['free_space']]
            else:
                # Create new file system metadata
                self.fs_metadata = {
                    'max_size': self.max_size,
                    'used_size': 0,
                    'files': {},
                    'directories': {
                        '/': {  # Root directory
                            'name': '/',
                            'creation_time': time.time(),
                            'files': [],
                            'subdirectories': []
                        }
                    },
                    'free_space': [(0, self.max_size)]  # Track free space as (start, size) tuples
                }
                self._save_metadata()
            
            # Create or verify data file exists
            if not os.path.exists(self.data_file):
                with open(self.data_file, 'wb') as f:
                    # Initialize with zeros
                    f.write(b'\0' * self.max_size)
    
    # Implements requirement 7 (persistence)
    def _save_metadata(self):
        """Save file system metadata to persist between runs"""
        # Create a copy of metadata with free_space as lists
        metadata_copy = self.fs_metadata.copy()
        if 'free_space' in metadata_copy:
            metadata_copy['free_space'] = [list(block) for block in metadata_copy['free_space']]
        
        with open(self.METADATA_FILE, 'w') as f:
            json.dump(metadata_copy, f, indent=2)
    
    def _allocate_space(self, size: int) -> int:
        """Allocate space in the data file for a new file or expansion"""
        if not self.fs_metadata['free_space']:
            raise IOError("No free space available")
        
        # Find a suitable free space segment
        best_fit_index = -1
        best_fit_size = float('inf')
        
        for i, (start, free_size) in enumerate(self.fs_metadata['free_space']):
            if free_size >= size and free_size < best_fit_size:
                best_fit_index = i
                best_fit_size = free_size
        
        if best_fit_index == -1:
            raise IOError(f"Not enough contiguous free space for {size} bytes")
        
        # Get the free space block
        start, free_size = self.fs_metadata['free_space'][best_fit_index]
        
        # Update or remove the free space entry
        if free_size == size:
            self.fs_metadata['free_space'].pop(best_fit_index)
        else:
            self.fs_metadata['free_space'][best_fit_index] = (start + size, free_size - size)
        
        # Update used size
        self.fs_metadata['used_size'] += size
        
        return start
    
    def _release_space(self, start: int, size: int):
        """Release space back to free space pool"""
        if size <= 0:
            return
            
        # Add to free space list and merge adjacent blocks (simple implementation)
        self.fs_metadata['free_space'].append((start, size))
        self.fs_metadata['used_size'] -= size
        
        # Sort by start position for easier merging
        self.fs_metadata['free_space'].sort()
        
        # Try to merge adjacent blocks
        i = 0
        while i < len(self.fs_metadata['free_space']) - 1:
            curr_start, curr_size = self.fs_metadata['free_space'][i]
            next_start, next_size = self.fs_metadata['free_space'][i + 1]
            
            if curr_start + curr_size == next_start:
                # Merge blocks
                self.fs_metadata['free_space'][i] = (curr_start, curr_size + next_size)
                self.fs_metadata['free_space'].pop(i + 1)
            else:
                i += 1
    
    # Implements requirement 2 - directory structure
    def get_current_directory_meta(self):
        """Get metadata for current directory"""
        # Ensure current path exists in directories
        if self.current_path not in self.fs_metadata['directories']:
            # Create the directory if it doesn't exist
            self.fs_metadata['directories'][self.current_path] = {
                'name': self.current_path.split('/')[-1] if self.current_path != "/" else "/",
                'creation_time': time.time(),
                'files': [],
                'subdirectories': []
            }
            self._save_metadata()
        
        return self.fs_metadata['directories'][self.current_path]
    
    def get_file_metadata(self, file_name: str):
        """Get metadata for a specific file"""
        return self.fs_metadata['files'].get(file_name, None)
    
    # Implements requirement 1.I - Create file
    def create(self, file_name: str) -> bool:
        """Create a new file"""
        # Check if file already exists
        if file_name in self.fs_metadata['files']:
            raise ValueError(f"File '{file_name}' already exists")
        
        # Get current directory
        current_dir = self.get_current_directory_meta()
        
        # Create file metadata
        file_meta = {
            'name': file_name,
            'size': 0,
            'creation_time': time.time(),
            'modified_time': time.time(),
            'start_pos': self._allocate_space(0),  # Initial allocation is 0
            'is_directory': False
        }
        
        # Add file to current directory
        if file_name not in current_dir['files']:
            current_dir['files'].append(file_name)
        
        # Add file to file system metadata
        self.fs_metadata['files'][file_name] = file_meta
        
        # Save changes to persist data
        self._save_metadata()
        
        return True
    
    # Implements requirement 1.II - Delete file
    def delete(self, file_name: str) -> bool:
        """Delete a file"""
        # Check if file exists
        if file_name not in self.fs_metadata['files']:
            raise ValueError(f"File '{file_name}' does not exist")
        
        # Check if file is open
        if file_name in self.open_files:
            raise ValueError(f"Cannot delete open file '{file_name}'")
        
        # Get file metadata
        file_meta = self.fs_metadata['files'][file_name]
        
        # Release space occupied by file
        self._release_space(file_meta['start_pos'], file_meta['size'])
        
        # Remove file from all directories
        for dir_path, dir_meta in self.fs_metadata['directories'].items():
            if file_name in dir_meta['files']:
                dir_meta['files'].remove(file_name)
        
        # Remove file from metadata
        del self.fs_metadata['files'][file_name]
        
        # Save changes to persist data (implements requirement 7)
        self._save_metadata()
        
        return True
    
    # Implements requirement 1.III - Create directory
    def mkdir(self, dir_name: str) -> bool:
        """Create a new directory"""
        # Format path
        if self.current_path == '/':
            new_dir_path = f"/{dir_name}"
        else:
            new_dir_path = f"{self.current_path}/{dir_name}"
        
        # Check if directory already exists
        if new_dir_path in self.fs_metadata['directories']:
            raise ValueError(f"Directory '{dir_name}' already exists")
        
        # Create directory metadata
        dir_meta = {
            'name': dir_name,
            'creation_time': time.time(),
            'files': [],
            'subdirectories': []
        }
        
        # Add to file system metadata
        self.fs_metadata['directories'][new_dir_path] = dir_meta
        
        # Add to parent directory's subdirectories
        parent_dir = self.get_current_directory_meta()
        if dir_name not in parent_dir['subdirectories']:
            parent_dir['subdirectories'].append(dir_name)
        
        # Save changes to persist data (implements requirement 7)
        self._save_metadata()
        
        return True
    
    # Implements requirement 1.IV - Change directory
    def chdir(self, dir_name: str) -> bool:
        """Change current directory"""
        # Handle special cases
        if dir_name == '.':
            return True
        elif dir_name == '..':
            # Go to parent directory
            if self.current_path == '/':
                return True  # Already at root
            
            # Remove last directory from path
            path_parts = self.current_path.split('/')
            path_parts = [p for p in path_parts if p]
            
            if path_parts:
                path_parts.pop()
            
            self.current_path = '/' + '/'.join(path_parts)
            if self.current_path == '':
                self.current_path = '/'
            
            return True
        elif dir_name == '/':
            # Go to root
            self.current_path = '/'
            return True
        
        # Check if directory exists
        if self.current_path == '/':
            target_path = f"/{dir_name}"
        else:
            target_path = f"{self.current_path}/{dir_name}"
        
        if target_path not in self.fs_metadata['directories']:
            raise ValueError(f"Directory '{dir_name}' does not exist")
        
        # Change directory
        self.current_path = target_path
        return True
    
    # Implements requirement 1.V - Move file
    def move(self, source_fname: str, target_dir: str) -> bool:
        """Move a file to a specified directory. Create the directory if it does not exist."""
        # Check if source file exists
        if source_fname not in self.fs_metadata['files']:
            raise ValueError(f"Source file '{source_fname}' does not exist")

        # Check if source file is open
        if source_fname in self.open_files:
            raise ValueError(f"Cannot move open file '{source_fname}'")

        # Handle relative/absolute target_dir
        if not target_dir.startswith('/'):
            if self.current_path == '/':
                target_dir_path = '/' + target_dir
            else:
                target_dir_path = self.current_path + '/' + target_dir
        else:
            target_dir_path = target_dir

        # Remove trailing slash for consistency
        target_dir_path = target_dir_path.rstrip('/')

        # Check if target directory exists
        if target_dir_path not in self.fs_metadata['directories']:
            # Create the directory if it doesn't exist
            parts = [p for p in target_dir_path.split('/') if p]
            curr = ''
            for part in parts:
                curr = curr + '/' + part if curr else '/' + part
                if curr not in self.fs_metadata['directories']:
                    dir_meta = {
                        'name': part,
                        'creation_time': time.time(),
                        'files': [],
                        'subdirectories': []
                    }
                    self.fs_metadata['directories'][curr] = dir_meta
                    # Add to parent subdirectories
                    parent = '/' if curr == '/' + part else curr.rsplit('/', 1)[0]
                    if parent in self.fs_metadata['directories']:
                        if part not in self.fs_metadata['directories'][parent]['subdirectories']:
                            self.fs_metadata['directories'][parent]['subdirectories'].append(part)

        # Remove file from all directories' file lists
        for dir_meta in self.fs_metadata['directories'].values():
            if source_fname in dir_meta['files']:
                dir_meta['files'].remove(source_fname)

        # Add file to the target directory's file list
        if source_fname not in self.fs_metadata['directories'][target_dir_path]['files']:
            self.fs_metadata['directories'][target_dir_path]['files'].append(source_fname)

        # Save changes to persist data
        self._save_metadata()

        return True
    
    # Implements requirement 1.VI - Open file
    def open(self, file_name: str, mode: str) -> FileObject:
        """Open a file and return a file object"""
        # Check if mode is valid
        if mode not in ['r', 'w']:
            raise ValueError("Mode must be 'r' (read) or 'w' (write)")
        
        # Create file object
        file_obj = FileObject(self, file_name, mode)
        
        # Track open file
        self.open_files[file_name] = file_obj
        
        return file_obj
    
    # Implements requirement 1.VII - Close file
    def close(self, file_name: str) -> bool:
        """Close an open file"""
        if file_name not in self.open_files:
            raise ValueError(f"File '{file_name}' is not open")
        
        # Remove from open files
        del self.open_files[file_name]
        
        # Save changes to persist data (implements requirement 7)
        self._save_metadata()
        
        return True
    
    # Implements requirement 1.XII - Show memory map
    def show_memory_map(self):
        """Display memory usage of the file system"""
        print("\n=== MEMORY MAP ===")
        print(f"Total Size: {self.max_size} bytes")
        print(f"Used Size: {self.fs_metadata['used_size']} bytes")
        print(f"Free Size: {self.max_size - self.fs_metadata['used_size']} bytes")
        
        # Print files and their memory ranges
        print("\nFiles:")
        for file_name, file_meta in self.fs_metadata['files'].items():
            print(f"  {file_name}: starts at {file_meta['start_pos']}, size {file_meta['size']} bytes")
        
        # Print free space blocks
        print("\nFree Space Blocks:")
        for start, size in self.fs_metadata['free_space']:
            print(f"  Block at {start}, size {size} bytes")
        print("==================\n")

    def get_current_path(self) -> str:
        """Get current directory path"""
        return self.current_path

    def list_directory(self):
        """List contents of current directory"""
        current_dir = self.get_current_directory_meta()
        
        print(f"\nContents of {self.current_path}:")
        print("Directories:")
        for subdir in current_dir['subdirectories']:
            print(f"  {subdir}/")
        
        print("Files:")
        for file_name in current_dir['files']:
            if file_name in self.fs_metadata['files']:
                size = self.fs_metadata['files'][file_name]['size']
                print(f"  {file_name} ({size} bytes)")
        print()

class ThreadManagerGUI:
    """GUI for managing threads in the file system"""
    
    def __init__(self, root, main_gui):
        self.root = root
        self.main_gui = main_gui  # Store reference to main GUI
        self.root.title("Thread Manager")
        self.root.geometry("800x600")
        
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.setup_gui()
        self.create_sample_input()
    
    def create_sample_input(self):
        """Create sample input file for testing"""
        sample_commands = [
            "create file1.txt",
            "open file1.txt w",
            'write_to_file file1.txt "abcd"',
            "create file2.txt",
            "open file2.txt w",
            "show_memory_map",
            'write_to_file file2.txt "123"',
            'write_to_file file1.txt "xyz"',
            "close file1.txt",
            "close file2.txt",
            "show_memory_map"
        ]
        
        try:
            with open("input_thread1.txt", "w") as f:
                for cmd in sample_commands:
                    f.write(cmd + "\n")
            
            # Show info about sample file creation
            messagebox.showinfo(
                "Success.",
                "Input Files Created."       
            )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create sample input file: {str(e)}")
    
    def setup_gui(self):
        """Setup the thread manager GUI"""
        # Main container
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Thread control section
        control_frame = ctk.CTkFrame(main_frame)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Number of threads input
        ctk.CTkLabel(
            control_frame,
            text="Number of Threads:",
            font=ctk.CTkFont(size=14)
        ).pack(side=tk.LEFT, padx=5)
        
        self.thread_count = ctk.CTkEntry(
            control_frame,
            width=100,
            placeholder_text="Enter number"
        )
        self.thread_count.pack(side=tk.LEFT, padx=5)
        
        # Start threads button
        ctk.CTkButton(
            control_frame,
            text="Start Threads",
            command=self.start_threads,
            width=120,
            height=35
        ).pack(side=tk.LEFT, padx=5)
        
        # Thread status section
        status_frame = ctk.CTkFrame(main_frame)
        status_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create treeview for thread status
        self.thread_tree = ttk.Treeview(
            status_frame,
            columns=("status", "input", "output", "time"),
            show="headings"
        )
        
        # Configure columns with bold and larger font
        style = ttk.Style()
        style.configure("Treeview.Heading", font=('TkDefaultFont', 14, 'bold'))
        style.configure("Treeview", font=('TkDefaultFont', 12))
        
        # Configure columns
        self.thread_tree.heading("status", text="Status")
        self.thread_tree.heading("input", text="Input File")
        self.thread_tree.heading("output", text="Output File")
        self.thread_tree.heading("time", text="Execution Time")
        
        self.thread_tree.column("status", width=120)
        self.thread_tree.column("input", width=220)
        self.thread_tree.column("output", width=220)
        self.thread_tree.column("time", width=170)
        
        # Add scrollbars
        y_scroll = ctk.CTkScrollbar(
            status_frame,
            command=self.thread_tree.yview
        )
        y_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        x_scroll = ctk.CTkScrollbar(
            status_frame,
            orientation="horizontal",
            command=self.thread_tree.xview
        )
        x_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.thread_tree.configure(
            yscrollcommand=y_scroll.set,
            xscrollcommand=x_scroll.set
        )
        self.thread_tree.pack(fill=tk.BOTH, expand=True)
        
        # View output button
        ctk.CTkButton(
            main_frame,
            text="View Output",
            command=self.view_output,
            width=120,
            height=35
        ).pack(pady=10)
        
        # View input button
        ctk.CTkButton(
            main_frame,
            text="View Input",
            command=self.view_input,
            width=120,
            height=35
        ).pack(pady=10)
    
    def view_input(self):
        """View the input file for a selected thread"""
        selected = self.thread_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a thread to view its input")
            return
        
        item = self.thread_tree.item(selected[0])
        input_file = item['values'][1]  # Input file is in the second column
        
        try:
            # Create input viewer window
            viewer = ctk.CTkToplevel(self.root)
            viewer.title(f"Input - {input_file}")
            viewer.geometry("800x600")
            
            # Make window modal
            viewer.transient(self.root)
            viewer.grab_set()
            
            # Center window
            x = self.root.winfo_x() + (self.root.winfo_width() - 800) // 2
            y = self.root.winfo_y() + (self.root.winfo_height() - 600) // 2
            viewer.geometry(f"+{x}+{y}")
            
            # Create text widget for input
            input_text = ctk.CTkTextbox(viewer)
            input_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Read and display input file
            if os.path.exists(input_file):
                with open(input_file, 'r') as f:
                    input_text.insert("1.0", f.read())
            else:
                input_text.insert("1.0", "No input file available")
            
            # Close button
            ctk.CTkButton(
                viewer,
                text="Close",
                command=viewer.destroy,
                width=120,
                height=35
            ).pack(pady=10)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error viewing input: {str(e)}")
    
    def start_threads(self):
        """Start the specified number of threads"""
        try:
            num_threads = int(self.thread_count.get())
            if num_threads <= 0:
                raise ValueError("Number of threads must be positive")
            
            # Clear existing items
            for item in self.thread_tree.get_children():
                self.thread_tree.delete(item)
            
            # Create input files for each thread
            for i in range(num_threads):
                thread_num = i + 1
                input_file = f"input_thread{thread_num}.txt"
                output_file = f"output_thread{thread_num}.txt"
                
                # Create input file for this thread with unique data
                with open(input_file, "w") as f:
                    f.write(f"create file{thread_num}.txt\n")
                    f.write(f"open file{thread_num}.txt w\n")
                    f.write(f'write_to_file file{thread_num}.txt "Data from Thread {thread_num}"\n')
                    f.write("show_memory_map\n")
                    f.write(f"close file{thread_num}.txt\n")
                    f.write("show_memory_map\n")
                
                # Add thread status entry
                self.thread_tree.insert(
                    "",
                    "end",
                    values=("Running", input_file, output_file, "-")
                )
            
            # Create threaded file system
            self.threaded_fs = ThreadedFileSystem(num_threads)
            
            # Start threads in background
            threading.Thread(target=self.run_threads).start()
            
        except ValueError as e:
            messagebox.showerror("Error", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"Unexpected error: {str(e)}")
    
    def run_threads(self):
        """Run the threads and show completion popup"""
        try:
            start_time = time.time()
            self.threaded_fs.run()
            end_time = time.time()
            execution_time = end_time - start_time
            
            # Update status to completed
            for item in self.thread_tree.get_children():
                self.thread_tree.set(item, "status", "Completed")
                self.thread_tree.set(item, "time", f"{execution_time:.2f} seconds")
            
            # Refresh the main file system view
            self.main_gui.refresh_view()
            
            # Show success popup
            messagebox.showinfo(
                "Success",
                "All threads have completed execution successfully!\n\n" 
            )
            
        except Exception as e:
            messagebox.showerror("Error", f"Error during thread execution: {str(e)}")
    
    def view_output(self):
        """View the output of a selected thread"""
        selected = self.thread_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a thread to view its output")
            return
        
        item = self.thread_tree.item(selected[0])
        output_file = item['values'][2]  # Output file is in the third column
        
        try:
            # Create output viewer window
            viewer = ctk.CTkToplevel(self.root)
            viewer.title(f"Output - {output_file}")
            viewer.geometry("800x600")
            
            # Make window modal
            viewer.transient(self.root)
            viewer.grab_set()
            
            # Center window
            x = self.root.winfo_x() + (self.root.winfo_width() - 800) // 2
            y = self.root.winfo_y() + (self.root.winfo_height() - 600) // 2
            viewer.geometry(f"+{x}+{y}")
            
            # Create text widget for output
            output_text = ctk.CTkTextbox(viewer)
            output_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Read and display output file
            if os.path.exists(output_file):
                with open(output_file, 'r') as f:
                    output_text.insert("1.0", f.read())
            else:
                output_text.insert("1.0", "No output available yet")
            
            # Close button
            ctk.CTkButton(
                viewer,
                text="Close",
                command=viewer.destroy,
                width=120,
                height=35
            ).pack(pady=10)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error viewing output: {str(e)}")

    def process_commands(self, thread_id: int):
        """Process commands from input file for a specific thread"""
        input_file = f"input_thread{thread_id}.txt"
        output_file = f"output_thread{thread_id}.txt"
        
        try:
            with open(input_file, 'r') as f:
                commands = f.readlines()
            
            with open(output_file, 'w') as f:
                for command in commands:
                    command = command.strip()
                    if not command:
                        continue
                    
                    try:
                        # Parse and execute command
                        parts = command.split()
                        cmd = parts[0]
                        args = parts[1:]
                        
                        if cmd == "create":
                            if len(args) != 1:
                                f.write(f"Error: Invalid arguments for create command\n")
                                continue
                            self.file_system.create(args[0])
                            f.write(f"Created file: {args[0]}\n")
                        
                        elif cmd == "open":
                            if len(args) != 2:
                                f.write(f"Error: Invalid arguments for open command\n")
                                continue
                            self.file_system.open(args[0], args[1])
                            f.write(f"Opened file: {args[0]} in {args[1]} mode\n")
                        
                        elif cmd == "write_to_file":
                            if len(args) < 2:
                                f.write(f"Error: Invalid arguments for write_to_file command\n")
                                continue
                            file_name = args[0]
                            # Extract text between quotes
                            text = command.split('"')[1] if '"' in command else " ".join(args[1:])
                            file_obj = self.file_system.open_files.get(file_name)
                            if file_obj:
                                # Write the text in append mode
                                file_obj.write_to_file(text)
                                f.write(f"Wrote to file: {file_name}\n")
                                # Read and show current content
                                current_content = file_obj.read_from_file()
                                f.write(f"Current content of {file_name}: {current_content}\n")
                            else:
                                f.write(f"Error: File {file_name} is not open\n")
                        
                        elif cmd == "close":
                            if len(args) != 1:
                                f.write(f"Error: Invalid arguments for close command\n")
                                continue
                            self.file_system.close(args[0])
                            f.write(f"Closed file: {args[0]}\n")
                        
                        elif cmd == "show_memory_map":
                            self.file_system.show_memory_map()
                            f.write("Memory map displayed\n")
                        
                        else:
                            f.write(f"Error: Unknown command: {cmd}\n")
                    
                    except Exception as e:
                        f.write(f"Error executing command '{command}': {str(e)}\n")
        
        except Exception as e:
            print(f"Error processing thread {thread_id}: {str(e)}")

class ModernFileSystemGUI:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Distributed File Management System")
        self.root.geometry("1200x800")
        
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.fs = FileSystem()
        self.current_path = "/"
        self.open_files = {}  # Track open files and their editors
        
        self.setup_gui()
        self.refresh_view()

    def setup_gui(self):
        # Main container
        self.main_container = ctk.CTkFrame(self.root)
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create UI components
        self.setup_toolbar()
        self.setup_file_view()
        self.setup_status_bar()

    def setup_toolbar(self):
        """Setup toolbar with file operations"""
        toolbar = ctk.CTkFrame(self.main_container)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        # Add Thread Manager button
        thread_manager_btn = ctk.CTkButton(
            toolbar,
            text="🧵 Thread Manager",
            command=self.open_thread_manager,
            width=120,
            height=35,
            font=ctk.CTkFont(size=14)
        )
        thread_manager_btn.pack(side=tk.LEFT, padx=5)

        # Add Refresh button
        refresh_btn = ctk.CTkButton(
            toolbar,
            text="🔄 Refresh",
            command=self.refresh_application,
            width=120,
            height=35,
            font=ctk.CTkFont(size=14)
        )
        refresh_btn.pack(side=tk.LEFT, padx=5)

        # Go Up Button
        go_up_btn = ctk.CTkButton(
            toolbar,
            text="⬆️ Go Up",
            command=self.go_up_directory,
            width=120,
            height=35,
            font=ctk.CTkFont(size=14)
        )
        go_up_btn.pack(side=tk.LEFT, padx=5)

        # Create File Button
        create_btn = ctk.CTkButton(
            toolbar,
            text="📄 New File",
            command=self.create_file_dialog,
            width=120,
            height=35,
            font=ctk.CTkFont(size=14)
        )
        create_btn.pack(side=tk.LEFT, padx=5)

        # Create Directory Button
        create_dir_btn = ctk.CTkButton(
            toolbar,
            text="📁 New Directory",
            command=self.create_directory_dialog,
            width=120,
            height=35,
            font=ctk.CTkFont(size=14)
        )
        create_dir_btn.pack(side=tk.LEFT, padx=5)

        # Move Button
        move_btn = ctk.CTkButton(
            toolbar,
            text="↔️ Move",
            command=self.move_selected,
            width=120,
            height=35,
            font=ctk.CTkFont(size=14)
        )
        move_btn.pack(side=tk.LEFT, padx=5)

        # Delete Button
        delete_btn = ctk.CTkButton(
            toolbar,
            text="🗑️ Delete",
            command=self.delete_selected,
            width=120,
            height=35,
            font=ctk.CTkFont(size=14)
        )
        delete_btn.pack(side=tk.LEFT, padx=5)

        # Memory Map Button
        memory_map_btn = ctk.CTkButton(
            toolbar,
            text="🗺️ Memory Map",
            command=self.show_memory_map,
            width=120,
            height=35,
            font=ctk.CTkFont(size=14)
        )
        memory_map_btn.pack(side=tk.LEFT, padx=5)

    def setup_file_view(self):
        """Setup file/directory view"""
        # Container for the file view
        self.file_view_frame = ctk.CTkFrame(self.main_container)
        self.file_view_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # Create Treeview with modern styling
        style = ttk.Style()
        style.configure(
            "Custom.Treeview",
            background="#2a2d2e",
            foreground="white",
            fieldbackground="#2a2d2e",
            borderwidth=0,
            font=('TkDefaultFont', 14),
            rowheight=35
        )
        
        style.configure(
            "Custom.Treeview.Heading",
            font=('TkDefaultFont', 14, 'bold'),
            background="#2a2d2e",
            foreground="black"
        )

        self.tree = ttk.Treeview(
            self.file_view_frame,
            style="Custom.Treeview",
            columns=("type", "size", "modified"),
            show="tree headings"
        )

        # Configure columns
        self.tree.heading("type", text="Type")
        self.tree.heading("size", text="Size (bytes)")
        self.tree.heading("modified", text="Last Modified")
        
        self.tree.column("type", width=100)
        self.tree.column("size", width=150)
        self.tree.column("modified", width=200)

        # Scrollbars
        y_scroll = ctk.CTkScrollbar(
            self.file_view_frame,
            command=self.tree.yview
        )
        y_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        x_scroll = ctk.CTkScrollbar(
            self.file_view_frame,
            orientation="horizontal",
            command=self.tree.xview
        )
        x_scroll.pack(side=tk.BOTTOM, fill=tk.X)

        self.tree.configure(
            yscrollcommand=y_scroll.set,
            xscrollcommand=x_scroll.set
        )
        self.tree.pack(fill=tk.BOTH, expand=True)

        # Bind events
        self.tree.bind("<Double-1>", self.on_double_click)

    def setup_status_bar(self):
        """Setup status bar"""
        self.status_bar = ctk.CTkFrame(self.root, height=25)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.status_label = ctk.CTkLabel(self.status_bar, text="Ready")
        self.status_label.pack(side=tk.LEFT, padx=5)

    def create_file_dialog(self):
        """Create a new file"""
        dialog = ctk.CTkInputDialog(
            text="Enter file name:",
            title="Create New File"
        )
        filename = dialog.get_input()
        
        if filename:
            try:
                if self.fs.create(filename):
                    self.refresh_view()
                    self.show_message(f"File '{filename}' created successfully")
            except Exception as e:
                self.show_message(str(e), is_error=True)

    def create_directory_dialog(self):
        """Create a new directory"""
        dialog = ctk.CTkInputDialog(
            text="Enter directory name:",
            title="Create New Directory"
        )
        dirname = dialog.get_input()
        
        if dirname:
            try:
                if self.fs.mkdir(dirname):
                    self.refresh_view()
                    self.show_message(f"Directory '{dirname}' created successfully")
            except Exception as e:
                self.show_message(str(e), is_error=True)

    def delete_selected(self):
        """Delete selected file or directory"""
        selected = self.tree.selection()
        if not selected:
            return

        item = self.tree.item(selected[0])
        item_type = item['values'][0]
        item_name = item['text']
        
        if item_type == "File":
            # Check if file is open in editor
            if item_name in self.open_files:
                editor_window, _ = self.open_files[item_name]
                editor_window.destroy()
                del self.open_files[item_name]
            
            if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete file '{item_name}'?"):
                try:
                    # Use the file system's delete method instead of manual deletion
                    if self.fs.delete(item_name):
                        self.refresh_view()
                        self.show_message(f"File '{item_name}' deleted")
                except Exception as e:
                    self.show_message(str(e), is_error=True)
        elif item_type == "Directory":
            if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete directory '{item_name}'?"):
                try:
                    # Get current directory metadata
                    current_dir = self.fs.get_current_directory_meta()
                    
                    # Remove directory from parent's subdirectories
                    if item_name in current_dir['subdirectories']:
                        current_dir['subdirectories'].remove(item_name)
                    
                    # Remove directory from metadata
                    dir_path = f"{self.fs.current_path}/{item_name}" if self.fs.current_path != "/" else f"/{item_name}"
                    
                    # Check if directory exists in metadata
                    if dir_path in self.fs.fs_metadata['directories']:
                        # Check if directory is empty
                        dir_meta = self.fs.fs_metadata['directories'][dir_path]
                        if dir_meta['files'] or dir_meta['subdirectories']:
                            raise ValueError(f"Cannot delete non-empty directory '{item_name}'")
                        
                        # Remove directory from metadata
                        del self.fs.fs_metadata['directories'][dir_path]
                        
                        # Remove directory from all parent directories' subdirectories
                        for path, meta in self.fs.fs_metadata['directories'].items():
                            if item_name in meta['subdirectories']:
                                meta['subdirectories'].remove(item_name)
                    
                    # Save changes
                    self.fs._save_metadata()
                    self.refresh_view()
                    self.show_message(f"Directory '{item_name}' deleted")
                except Exception as e:
                    self.show_message(str(e), is_error=True)

    def on_double_click(self, event):
        """Handle double click on item"""
        selected = self.tree.selection()
        if not selected:
            return

        item = self.tree.item(selected[0])
        item_type = item['values'][0]
        item_name = item['text']
        
        if item_type == "Directory":
            # Navigate to the selected directory
            try:
                # Change to the directory using just the directory name
                if self.fs.chdir(item_name):
                    # Update current path
                    if self.current_path == "/":
                        self.current_path = f"/{item_name}"
                    else:
                        self.current_path = f"{self.current_path}/{item_name}"
                    self.refresh_view()
            except Exception as e:
                self.show_message(str(e), is_error=True)
        elif item_type == "File":
            # Create dialog for file operations
            dialog = ctk.CTkToplevel(self.root)
            dialog.title("File Operations")
            dialog.geometry("400x450")
            
            # Make dialog modal
            dialog.transient(self.root)
            dialog.grab_set()
            
            # Center dialog
            x = self.root.winfo_x() + (self.root.winfo_width() - 400) // 2
            y = self.root.winfo_y() + (self.root.winfo_height() - 450) // 2
            dialog.geometry(f"+{x}+{y}")
            
            # Add label
            ctk.CTkLabel(
                dialog,
                text=f"Select operation for '{item_name}':",
                font=ctk.CTkFont(size=14, weight="bold")
            ).pack(pady=20)
            
            # Add buttons
            def open_view_mode():
                dialog.destroy()
                self.open_file_editor(item_name, 'view')
            
            def open_append_mode():
                dialog.destroy()
                self.open_file_editor(item_name, 'append')
            
            def open_position_mode():
                dialog.destroy()
                self.ask_position(item_name)
            
            def open_truncate_mode():
                dialog.destroy()
                self.ask_truncate_size(item_name)
            
            def open_move_content_mode():
                dialog.destroy()
                self.ask_move_content(item_name)
            
            def open_read_position_mode():
                dialog.destroy()
                self.ask_read_position(item_name)
            
            ctk.CTkButton(
                dialog,
                text="View File",
                command=open_view_mode,
                width=200,
                height=35
            ).pack(pady=10)
            
            ctk.CTkButton(
                dialog,
                text="Append to End of File",
                command=open_append_mode,
                width=200,
                height=35
            ).pack(pady=10)
            
            ctk.CTkButton(
                dialog,
                text="Write at Specific Position",
                command=open_position_mode,
                width=200,
                height=35
            ).pack(pady=10)
            
            ctk.CTkButton(
                dialog,
                text="Truncate File",
                command=open_truncate_mode,
                width=200,
                height=35
            ).pack(pady=10)
            
            ctk.CTkButton(
                dialog,
                text="Move Content",
                command=open_move_content_mode,
                width=200,
                height=35
            ).pack(pady=10)
            
            ctk.CTkButton(
                dialog,
                text="Read from Position",
                command=open_read_position_mode,
                width=200,
                height=35
            ).pack(pady=10)

    def ask_position(self, filename):
        """Ask for position before opening editor"""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Enter Position")
        dialog.geometry("400x200")
        
        # Make dialog modal
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center dialog
        x = self.root.winfo_x() + (self.root.winfo_width() - 400) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 200) // 2
        dialog.geometry(f"+{x}+{y}")
        
        # Add label
        ctk.CTkLabel(
            dialog,
            text="Enter position to write at:",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=20)
        
        # Position entry
        position_entry = ctk.CTkEntry(
            dialog,
            width=200,
            placeholder_text="Enter position number"
        )
        position_entry.pack(pady=10)
        
        def proceed():
            try:
                position = int(position_entry.get())
                if position < 0:
                    raise ValueError("Position must be non-negative")
                dialog.destroy()
                self.open_file_editor(filename, 'position', position)
            except ValueError as e:
                self.show_message("Invalid position - Please enter a non-negative number", is_error=True)
        
        # Proceed button
        ctk.CTkButton(
            dialog,
            text="Proceed",
            command=proceed,
            width=200,
            height=35
        ).pack(pady=10)

    def open_file_editor(self, filename, mode, position=None):
        """Open file editor with specified mode"""
        try:
            # Open file in read mode to get current content
            file_obj = self.fs.open(filename, 'r')
            content = file_obj.read_from_file()
            self.fs.close(filename)
            
            # Create editor window
            editor_window = ctk.CTkToplevel(self.root)
            editor_window.title(f"{'Viewing' if mode == 'view' else 'Editing'}: {filename}")
            editor_window.geometry("800x600")
            
            # Make window modal
            editor_window.transient(self.root)
            editor_window.grab_set()
            
            # Center window
            x = self.root.winfo_x() + (self.root.winfo_width() - 800) // 2
            y = self.root.winfo_y() + (self.root.winfo_height() - 600) // 2
            editor_window.geometry(f"+{x}+{y}")
            
            # Create editor
            editor = ctk.CTkTextbox(editor_window)
            editor.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            if mode == 'view':
                # Show current content in view mode
                editor.insert("1.0", content)
                editor.configure(state='disabled')
            elif mode == 'append':
                # Show append mode info
                append_label = ctk.CTkLabel(
                    editor_window,
                    text="Appending text to the end of file",
                    font=ctk.CTkFont(size=12, weight="bold")
                )
                append_label.pack(pady=5)
            else:  # position mode
                # Show position info
                position_label = ctk.CTkLabel(
                    editor_window,
                    text=f"Writing at position: {position}",
                    font=ctk.CTkFont(size=12, weight="bold")
                )
                position_label.pack(pady=5)
            
            # Create button frame
            button_frame = ctk.CTkFrame(editor_window)
            button_frame.pack(fill=tk.X, padx=10, pady=5)
            
            # Save button (not shown in view mode)
            if mode != 'view':
                def save_file():
                    try:
                        new_content = editor.get("1.0", tk.END).strip()
                        file_obj = self.fs.open(filename, 'w')
                        
                        if mode == 'append':
                            # Append to end of file
                            file_obj.write_to_file(content + "\n" + new_content)
                            self.show_message(f"Content appended to '{filename}'")
                        else:
                            # Write at specific position
                            file_obj.write_to_file_at(position, new_content)
                            self.show_message(f"Content written at position {position}")
                        
                        self.fs.close(filename)
                        
                        # Show success popup
                        success_dialog = ctk.CTkToplevel(self.root)
                        success_dialog.title("Success")
                        success_dialog.geometry("300x150")
                        
                        # Make dialog modal
                        success_dialog.transient(self.root)
                        success_dialog.grab_set()
                        
                        # Center dialog
                        x = self.root.winfo_x() + (self.root.winfo_width() - 300) // 2
                        y = self.root.winfo_y() + (self.root.winfo_height() - 150) // 2
                        success_dialog.geometry(f"+{x}+{y}")
                        
                        # Add success message
                        ctk.CTkLabel(
                            success_dialog,
                            text="File saved successfully!",
                            font=ctk.CTkFont(size=14, weight="bold")
                        ).pack(pady=20)
                        
                        # Add OK button
                        ctk.CTkButton(
                            success_dialog,
                            text="OK",
                            command=success_dialog.destroy,
                            width=100,
                            height=35
                        ).pack(pady=10)
                        
                    except Exception as e:
                        self.show_message(str(e), is_error=True)

                save_btn = ctk.CTkButton(
                    button_frame,
                    text="💾 Save",
                    command=save_file,
                    width=100,
                    height=35
                )
                save_btn.pack(side=tk.LEFT, padx=5)
            
            # Close button
            close_btn = ctk.CTkButton(
                button_frame,
                text="✕ Close",
                command=editor_window.destroy,
                width=100,
                height=35
            )
            close_btn.pack(side=tk.RIGHT, padx=5)
            
            # Add helper text
            helper_frame = ctk.CTkFrame(editor_window)
            helper_frame.pack(fill=tk.X, padx=10, pady=2)
            
            if mode == 'view':
                helper_text = "Viewing file content (read-only)"
            elif mode == 'append':
                helper_text = "Enter text to append to the end of the file"
            else:
                helper_text = "Enter text to write at the specified position"
                
            ctk.CTkLabel(
                helper_frame,
                text=helper_text,
                font=ctk.CTkFont(size=10),
                text_color="gray"
            ).pack(pady=2)
            
            # Store editor reference
            self.open_files[filename] = (editor_window, editor)
            
        except Exception as e:
            self.show_message(str(e), is_error=True)

    def ask_truncate_size(self, filename):
        """Ask for truncate size before truncating file"""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Enter Truncate Size")
        dialog.geometry("400x200")
        
        # Make dialog modal
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center dialog
        x = self.root.winfo_x() + (self.root.winfo_width() - 400) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 200) // 2
        dialog.geometry(f"+{x}+{y}")
        
        # Add label
        ctk.CTkLabel(
            dialog,
            text="Enter size to truncate file to:",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=20)
        
        # Size entry
        size_entry = ctk.CTkEntry(
            dialog,
            width=200,
            placeholder_text="Enter size in bytes"
        )
        size_entry.pack(pady=10)
        
        def truncate_file():
            try:
                size = int(size_entry.get())
                if size < 0:
                    raise ValueError("Size must be non-negative")
                
                # Open file in write mode
                file_obj = self.fs.open(filename, 'w')
                file_obj.truncate_file(size)
                self.fs.close(filename)
                
                dialog.destroy()
                self.show_message(f"File '{filename}' truncated to {size} bytes")
            except ValueError as e:
                self.show_message("Invalid size - Please enter a non-negative number", is_error=True)
            except Exception as e:
                self.show_message(str(e), is_error=True)
        
        # Truncate button
        ctk.CTkButton(
            dialog,
            text="Truncate",
            command=truncate_file,
            width=200,
            height=35
        ).pack(pady=10)

    def show_memory_map(self):
        """Show memory map of the file system"""
        try:
            # Create dialog for memory map
            dialog = ctk.CTkToplevel(self.root)
            dialog.title("Memory Map")
            dialog.geometry("1000x800")
            
            # Make dialog modal
            dialog.transient(self.root)
            dialog.grab_set()
            
            # Center dialog
            x = self.root.winfo_x() + (self.root.winfo_width() - 1000) // 2
            y = self.root.winfo_y() + (self.root.winfo_height() - 800) // 2
            dialog.geometry(f"+{x}+{y}")
            
            # Create notebook for tabs
            notebook = ttk.Notebook(dialog)
            notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Memory Usage Tab
            memory_frame = ctk.CTkFrame(notebook)
            notebook.add(memory_frame, text="Memory Usage")
            
            # Create text widget for memory map
            memory_text = ctk.CTkTextbox(memory_frame)
            memory_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Get memory usage information
            memory_text.insert("1.0", "=== MEMORY USAGE ===\n\n")
            memory_text.insert(tk.END, f"Total Size: {self.fs.max_size} bytes\n")
            memory_text.insert(tk.END, f"Used Size: {self.fs.fs_metadata['used_size']} bytes\n")
            memory_text.insert(tk.END, f"Free Size: {self.fs.max_size - self.fs.fs_metadata['used_size']} bytes\n\n")
            
            memory_text.insert(tk.END, "Files and their memory ranges:\n")
            for file_name, file_meta in self.fs.fs_metadata['files'].items():
                memory_text.insert(tk.END, f"  {file_name}: starts at {file_meta['start_pos']}, size {file_meta['size']} bytes\n")
            
            memory_text.insert(tk.END, "\nFree Space Blocks:\n")
            for start, size in self.fs.fs_metadata['free_space']:
                memory_text.insert(tk.END, f"  Block at {start}, size {size} bytes\n")
            
            memory_text.configure(state='disabled')
            
            # File System Structure Tab
            structure_frame = ctk.CTkFrame(notebook)
            notebook.add(structure_frame, text="File System Structure")
            
            # Create treeview for file system structure
            structure_tree = ttk.Treeview(
                structure_frame,
                columns=("type", "size", "modified"),
                show="tree headings"
            )
            
            # Configure columns
            structure_tree.heading("type", text="Type")
            structure_tree.heading("size", text="Size (bytes)")
            structure_tree.heading("modified", text="Last Modified")
            
            structure_tree.column("type", width=100)
            structure_tree.column("size", width=150)
            structure_tree.column("modified", width=200)
            
            # Add scrollbars
            y_scroll = ctk.CTkScrollbar(
                structure_frame,
                command=structure_tree.yview
            )
            y_scroll.pack(side=tk.RIGHT, fill=tk.Y)
            
            x_scroll = ctk.CTkScrollbar(
                structure_frame,
                orientation="horizontal",
                command=structure_tree.xview
            )
            x_scroll.pack(side=tk.BOTTOM, fill=tk.X)
            
            structure_tree.configure(
                yscrollcommand=y_scroll.set,
                xscrollcommand=x_scroll.set
            )
            structure_tree.pack(fill=tk.BOTH, expand=True)
            
            # Add root directory
            root_item = structure_tree.insert("", "end", text="/", values=("Directory", "-", "-"))
            
            # Function to add directories recursively
            def add_directory(parent_path, parent_item):
                dir_meta = self.fs.fs_metadata['directories'][parent_path]
                
                # Add files
                for file_name in dir_meta['files']:
                    if file_name in self.fs.fs_metadata['files']:
                        file_meta = self.fs.fs_metadata['files'][file_name]
                        modified_time = datetime.fromtimestamp(file_meta['modified_time']).strftime('%Y-%m-%d %H:%M:%S')
                        structure_tree.insert(parent_item, "end", text=file_name, 
                                           values=("File", file_meta['size'], modified_time))
                
                # Add subdirectories
                for subdir in dir_meta['subdirectories']:
                    subdir_path = f"{parent_path}/{subdir}" if parent_path != "/" else f"/{subdir}"
                    modified_time = datetime.fromtimestamp(self.fs.fs_metadata['directories'][subdir_path]['creation_time']).strftime('%Y-%m-%d %H:%M:%S')
                    subdir_item = structure_tree.insert(parent_item, "end", text=subdir, 
                                                      values=("Directory", "-", modified_time))
                    add_directory(subdir_path, subdir_item)
            
            # Start building the structure from root
            add_directory("/", root_item)
            
            # Close button
            ctk.CTkButton(
                dialog,
                text="Close",
                command=dialog.destroy,
                width=200,
                height=35
            ).pack(pady=10)
            
        except Exception as e:
            self.show_message(str(e), is_error=True)

    def show_message(self, message, is_error=False):
        """Show message in status bar"""
        if is_error:
            messagebox.showerror("Error", message)
        else:
            self.status_label.configure(text=message)

    def refresh_view(self):
        """Refresh file view"""
        # Get current directory metadata
        current_dir = self.fs.get_current_directory_meta()
        
        # Clear existing items
        self.tree.delete(*self.tree.get_children())
        
        # Add directories and files
        for subdir in current_dir['subdirectories']:
            dir_path = f"{self.fs.current_path}/{subdir}" if self.fs.current_path != "/" else f"/{subdir}"
            dir_meta = self.fs.fs_metadata['directories'][dir_path]
            modified_time = datetime.fromtimestamp(dir_meta['creation_time']).strftime('%Y-%m-%d %H:%M:%S')
            self.tree.insert("", "end", text=subdir, values=("Directory", "-", modified_time))
        
        for file_name in current_dir['files']:
            if file_name in self.fs.fs_metadata['files']:
                file_meta = self.fs.fs_metadata['files'][file_name]
                modified_time = datetime.fromtimestamp(file_meta['modified_time']).strftime('%Y-%m-%d %H:%M:%S')
                self.tree.insert("", "end", text=file_name, values=("File", file_meta['size'], modified_time))

    def move_selected(self):
        """Move selected file or directory"""
        selected = self.tree.selection()
        if not selected:
            return

        item = self.tree.item(selected[0])
        item_type = item['values'][0]
        item_name = item['text']

        # Create dialog for target directory
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Select Target Directory")
        dialog.geometry("400x300")
        
        # Make dialog modal
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center dialog
        x = self.root.winfo_x() + (self.root.winfo_width() - 400) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 300) // 2
        dialog.geometry(f"+{x}+{y}")
        
        # Add label
        ctk.CTkLabel(
            dialog,
            text=f"Select target directory for {item_name}:",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=20)
        
        # Create directory tree
        dir_tree = ttk.Treeview(
            dialog,
            columns=("type",),
            show="tree",
            height=10
        )
        dir_tree.pack(pady=10, padx=20, fill=tk.BOTH, expand=True)
        
        # Add root directory
        dir_tree.insert("", "end", text="/", values=("Directory",), iid="/")
        
        # Add all directories
        def add_directories(parent_path, parent_id):
            for dir_name in self.fs.fs_metadata['directories'][parent_path]['subdirectories']:
                dir_path = f"{parent_path}/{dir_name}" if parent_path != "/" else f"/{dir_name}"
                dir_tree.insert(parent_id, "end", text=dir_name, values=("Directory",), iid=dir_path)
                add_directories(dir_path, dir_path)
        
        add_directories("/", "/")
        
        def move_item():
            selected_dir = dir_tree.selection()
            if not selected_dir:
                self.show_message("Please select a target directory", is_error=True)
                return
            
            target_dir = selected_dir[0]
            try:
                # Get the directory name from the path
                target_dir_name = target_dir.split('/')[-1] if target_dir != "/" else "/"
                
                # First change to the target directory to ensure it exists
                if self.fs.chdir(target_dir_name):
                    # Change back to current directory
                    self.fs.chdir(self.current_path)
                    # Now perform the move
                    if self.fs.move(item_name, target_dir_name):
                        self.refresh_view()
                        self.show_message(f"{item_type} '{item_name}' moved to '{target_dir}'")
                        dialog.destroy()
            except Exception as e:
                self.show_message(str(e), is_error=True)
        
        # Move button
        ctk.CTkButton(
            dialog,
            text="Move",
            command=move_item,
            width=200,
            height=35
        ).pack(pady=10)

    def go_up_directory(self):
        """Navigate to the parent directory"""
        try:
            # Change to parent directory
            if self.fs.chdir(".."):
                # Update current path
                if self.current_path == "/":
                    return  # Already at root
                
                # Remove last directory from path
                path_parts = self.current_path.split('/')
                path_parts = [p for p in path_parts if p]  # Remove empty parts
                
                if len(path_parts) > 1:
                    self.current_path = '/' + '/'.join(path_parts[:-1])
                else:
                    self.current_path = "/"
                
                self.refresh_view()
        except Exception as e:
            self.show_message(str(e), is_error=True)

    def ask_move_content(self, filename):
        """Ask for move content parameters"""
        try:
            # First open the file to show its content
            file_obj = self.fs.open(filename, 'r')
            content = file_obj.read_from_file()
            self.fs.close(filename)
            
            # Create dialog for move content
            dialog = ctk.CTkToplevel(self.root)
            dialog.title(f"Move Content in {filename}")
            dialog.geometry("800x600")
            
            # Make dialog modal
            dialog.transient(self.root)
            dialog.grab_set()
            
            # Center dialog
            x = self.root.winfo_x() + (self.root.winfo_width() - 800) // 2
            y = self.root.winfo_y() + (self.root.winfo_height() - 600) // 2
            dialog.geometry(f"+{x}+{y}")
            
            # Create content display
            content_frame = ctk.CTkFrame(dialog)
            content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Add label
            ctk.CTkLabel(
                content_frame,
                text="File Content:",
                font=ctk.CTkFont(size=14, weight="bold")
            ).pack(pady=5)
            
            # Create text widget for content
            content_text = ctk.CTkTextbox(content_frame)
            content_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
            content_text.insert("1.0", content)
            content_text.configure(state='disabled')
            
            # Create input frame
            input_frame = ctk.CTkFrame(dialog)
            input_frame.pack(fill=tk.X, padx=10, pady=10)
            
            # Add input fields
            ctk.CTkLabel(
                input_frame,
                text="From Position:",
                font=ctk.CTkFont(size=12)
            ).pack(side=tk.LEFT, padx=5)
            
            from_entry = ctk.CTkEntry(
                input_frame,
                width=100,
                placeholder_text="Start position"
            )
            from_entry.pack(side=tk.LEFT, padx=5)
            
            ctk.CTkLabel(
                input_frame,
                text="To Position:",
                font=ctk.CTkFont(size=12)
            ).pack(side=tk.LEFT, padx=5)
            
            to_entry = ctk.CTkEntry(
                input_frame,
                width=100,
                placeholder_text="Target position"
            )
            to_entry.pack(side=tk.LEFT, padx=5)
            
            ctk.CTkLabel(
                input_frame,
                text="Size:",
                font=ctk.CTkFont(size=12)
            ).pack(side=tk.LEFT, padx=5)
            
            size_entry = ctk.CTkEntry(
                input_frame,
                width=100,
                placeholder_text="Size in bytes"
            )
            size_entry.pack(side=tk.LEFT, padx=5)
            
            def move_content():
                try:
                    from_pos = int(from_entry.get())
                    to_pos = int(to_entry.get())
                    size = int(size_entry.get())
                    
                    if from_pos < 0 or to_pos < 0 or size < 0:
                        raise ValueError("Positions and size must be non-negative")
                    
                    # Open file in write mode
                    file_obj = self.fs.open(filename, 'w')
                    file_obj.move_within_file(from_pos, size, to_pos)
                    self.fs.close(filename)
                    
                    dialog.destroy()
                    self.show_message(f"Content moved in '{filename}' from {from_pos} to {to_pos} (size: {size})")
                except ValueError as e:
                    self.show_message("Invalid input - Please enter non-negative numbers", is_error=True)
                except Exception as e:
                    self.show_message(str(e), is_error=True)
            
            # Move button
            ctk.CTkButton(
                dialog,
                text="Move Content",
                command=move_content,
                width=200,
                height=35
            ).pack(pady=10)
            
            # Close button
            ctk.CTkButton(
                dialog,
                text="Close",
                command=dialog.destroy,
                width=200,
                height=35
            ).pack(pady=10)
        except Exception as e:
            self.show_message(str(e), is_error=True)

    def ask_read_position(self, filename):
        """Ask for position and size before reading from file"""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Read from Position")
        dialog.geometry("400x300")
        
        # Make dialog modal
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center dialog
        x = self.root.winfo_x() + (self.root.winfo_width() - 400) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 300) // 2
        dialog.geometry(f"+{x}+{y}")
        
        # Add label
        ctk.CTkLabel(
            dialog,
            text="Enter position and size to read:",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=20)
        
        # Position entry
        position_frame = ctk.CTkFrame(dialog)
        position_frame.pack(pady=10)
        
        ctk.CTkLabel(
            position_frame,
            text="Position:",
            font=ctk.CTkFont(size=12)
        ).pack(side=tk.LEFT, padx=5)
        
        position_entry = ctk.CTkEntry(
            position_frame,
            width=100,
            placeholder_text="Start position"
        )
        position_entry.pack(side=tk.LEFT, padx=5)
        
        # Size entry
        size_frame = ctk.CTkFrame(dialog)
        size_frame.pack(pady=10)
        
        ctk.CTkLabel(
            size_frame,
            text="Size:",
            font=ctk.CTkFont(size=12)
        ).pack(side=tk.LEFT, padx=5)
        
        size_entry = ctk.CTkEntry(
            size_frame,
            width=100,
            placeholder_text="Size in bytes"
        )
        size_entry.pack(side=tk.LEFT, padx=5)
        
        def read_from_position():
            try:
                position = int(position_entry.get())
                size = int(size_entry.get())
                
                if position < 0 or size < 0:
                    raise ValueError("Position and size must be non-negative")
                
                # Open file in read mode
                file_obj = self.fs.open(filename, 'r')
                content = file_obj.read_from_file_at(position, size)
                self.fs.close(filename)
                
                # Create result dialog
                result_dialog = ctk.CTkToplevel(self.root)
                result_dialog.title(f"Read Result - {filename}")
                result_dialog.geometry("600x400")
                
                # Make dialog modal
                result_dialog.transient(self.root)
                result_dialog.grab_set()
                
                # Center dialog
                x = self.root.winfo_x() + (self.root.winfo_width() - 600) // 2
                y = self.root.winfo_y() + (self.root.winfo_height() - 400) // 2
                result_dialog.geometry(f"+{x}+{y}")
                
                # Add label
                ctk.CTkLabel(
                    result_dialog,
                    text=f"Content from position {position} (size: {size} bytes):",
                    font=ctk.CTkFont(size=14, weight="bold")
                ).pack(pady=10)
                
                # Create text widget for content
                content_text = ctk.CTkTextbox(result_dialog)
                content_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                content_text.insert("1.0", content)
                content_text.configure(state='disabled')
                
                # Close button
                ctk.CTkButton(
                    result_dialog,
                    text="Close",
                    command=result_dialog.destroy,
                    width=200,
                    height=35
                ).pack(pady=10)
                
                dialog.destroy()
            except ValueError as e:
                self.show_message("Invalid input - Please enter non-negative numbers", is_error=True)
            except Exception as e:
                self.show_message(str(e), is_error=True)
        
        # Read button
        ctk.CTkButton(
            dialog,
            text="Read",
            command=read_from_position,
            width=200,
            height=35
        ).pack(pady=10)
        
        # Close button
        ctk.CTkButton(
            dialog,
            text="Close",
            command=dialog.destroy,
            width=200,
            height=35
        ).pack(pady=10)

    def open_thread_manager(self):
        """Open the thread manager window"""
        thread_manager = ctk.CTkToplevel(self.root)
        thread_manager.title("Thread Manager")
        thread_manager.geometry("800x600")
        
        # Make window modal
        thread_manager.transient(self.root)
        thread_manager.grab_set()
        
        # Center window
        x = self.root.winfo_x() + (self.root.winfo_width() - 800) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 600) // 2
        thread_manager.geometry(f"+{x}+{y}")
        
        # Create thread manager GUI with reference to main GUI
        ThreadManagerGUI(thread_manager, self)

    def refresh_application(self):
        """Refresh the application like a browser refresh"""
        try:
            # Destroy the current window
            self.root.destroy()
            
            # Create a new instance of the application
            new_app = ModernFileSystemGUI()
            new_app.run()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh application: {str(e)}")

    def run(self):
        self.root.mainloop()

class ThreadedFileSystem:
    """Class that manages multiple threads for file system operations"""
    
    def __init__(self, num_threads: int):
        self.num_threads = num_threads
        self.file_system = FileSystem()
        self.threads = []
    
    def process_commands(self, thread_id: int):
        """Process commands from input file for a specific thread"""
        input_file = f"input_thread{thread_id}.txt"
        output_file = f"output_thread{thread_id}.txt"
        
        try:
            with open(input_file, 'r') as f:
                commands = f.readlines()
            
            with open(output_file, 'w') as f:
                for command in commands:
                    command = command.strip()
                    if not command:
                        continue
                    
                    try:
                        # Parse and execute command
                        parts = command.split()
                        cmd = parts[0]
                        args = parts[1:]
                        
                        if cmd == "create":
                            if len(args) != 1:
                                f.write(f"Error: Invalid arguments for create command\n")
                                continue
                            self.file_system.create(args[0])
                            f.write(f"Created file: {args[0]}\n")
                        
                        elif cmd == "open":
                            if len(args) != 2:
                                f.write(f"Error: Invalid arguments for open command\n")
                                continue
                            self.file_system.open(args[0], args[1])
                            f.write(f"Opened file: {args[0]} in {args[1]} mode\n")
                        
                        elif cmd == "write_to_file":
                            if len(args) < 2:
                                f.write(f"Error: Invalid arguments for write_to_file command\n")
                                continue
                            file_name = args[0]
                            # Extract text between quotes
                            text = command.split('"')[1] if '"' in command else " ".join(args[1:])
                            file_obj = self.file_system.open_files.get(file_name)
                            if file_obj:
                                # Write the text in append mode
                                file_obj.write_to_file(text)
                                f.write(f"Wrote to file: {file_name}\n")
                                # Read and show current content
                                current_content = file_obj.read_from_file()
                                f.write(f"Current content of {file_name}: {current_content}\n")
                            else:
                                f.write(f"Error: File {file_name} is not open\n")
                        
                        elif cmd == "close":
                            if len(args) != 1:
                                f.write(f"Error: Invalid arguments for close command\n")
                                continue
                            self.file_system.close(args[0])
                            f.write(f"Closed file: {args[0]}\n")
                        
                        elif cmd == "show_memory_map":
                            self.file_system.show_memory_map()
                            f.write("Memory map displayed\n")
                        
                        else:
                            f.write(f"Error: Unknown command: {cmd}\n")
                    
                    except Exception as e:
                        f.write(f"Error executing command '{command}': {str(e)}\n")
        
        except Exception as e:
            print(f"Error processing thread {thread_id}: {str(e)}")
    
    def run(self):
        """Start all threads and wait for them to complete"""
        # Create and start threads
        for i in range(self.num_threads):
            thread = threading.Thread(target=self.process_commands, args=(i+1,))
            self.threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in self.threads:
            thread.join()

def main():
    # Create and run the GUI
    app = ModernFileSystemGUI()
    app.run()

if __name__ == "__main__":
    main()
