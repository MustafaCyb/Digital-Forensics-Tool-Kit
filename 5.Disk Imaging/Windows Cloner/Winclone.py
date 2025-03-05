import os
import sys
import psutil

def list_partitions():
    """Lists all partitions with their device, mountpoint, and file system type."""
    partitions = []
    for partition in psutil.disk_partitions(all=False):
        partitions.append({
            "device": partition.device,
            "mountpoint": partition.mountpoint,
            "fstype": partition.fstype
        })
    return partitions

def clone_partition(src_partition, dest_file, progress_callback=None, stop_event=None):
    """
    Clones a source partition to a destination file with progress tracking and stop capability.
    """
    if not src_partition.startswith('\\\\.\\'):
        src_partition = f'\\\\.\\{src_partition[0]}:'

    try:
        with open(src_partition, 'rb', buffering=0) as src_f, \
             open(dest_file, 'wb', buffering=0) as dest_f:

            print("Cloning partition. This may take some time...")
            bytes_copied = 0
            
            while True:
                if stop_event and stop_event.is_set():
                    print("\nCloning stopped by user!")
                    break
                
                chunk = src_f.read(8 * 1024 * 1024)  # 8MB chunks
                if not chunk:
                    break
                
                dest_f.write(chunk)
                bytes_copied += len(chunk)
                
                if progress_callback:
                    progress_callback(bytes_copied)

            # Explicitly flush and close handles
            dest_f.flush()
            os.fsync(dest_f.fileno())

    except PermissionError:
        print("Permission denied! Please run with administrative privileges.")
    except Exception as e:
        print(f"Error: {str(e)}")