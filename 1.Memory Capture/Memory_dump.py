import os
import subprocess
import platform
import time
import ctypes
import sys



def add_raw_extension(filename):
    """
    Ensure the output file name ends with '.raw'.
    """
    if not filename.lower().endswith(".raw"):
        return filename + ".raw"
    
    return filename

def run_memory_dump(command, output_file, shell=False):
    """
    Run the memory dump command and handle errors.
    """
    try:
        if shell:
            # Construct command string when using shell=True
            full_command = f"{command} {output_file}"
            subprocess.run(full_command, shell=True, check=True)
        else:

            subprocess.run([command,"--output" ,output_file], check=True)
        print("Memory dump completed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred during the memory dump: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

def main():
    os_type = platform.system()
    print(f"Detected OS: {os_type}")

    # Set the appropriate dump command based on the operating system
    if os_type == "Windows":
            # Ensure the script runs as administrator
        if not ctypes.windll.shell32.IsUserAnAdmin():
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
            sys.exit()

        dump_command = "winpmem.exe"

    elif os_type == "Linux":
        # Check if running with root privileges
        if os.geteuid() != 0:
            print("Error", "This script must be run as root. Please run with sudo.")
            sys.exit()
        dump_command = "./linpmem"
    else:
        print("Unsupported Operating System")
        return

    # Get the output file name from the user and ensure it ends with .raw
    file_output = input("Enter the output file name: ").strip()
    file_output = add_raw_extension(file_output)

    print(f"Starting memory dump for {os_type} using {dump_command} with output file '{file_output}'...")
    time.sleep(3)

    # Use shell=True for Windows if required
    run_memory_dump(dump_command, file_output, shell=(os_type == "Windows"))

if __name__ == "__main__":
    main()
