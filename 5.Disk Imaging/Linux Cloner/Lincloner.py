import os
import sys
import psutil

def list_partitions():
    """List all mounted partitions with detailed information"""
    partitions = []
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
            total_size = usage.total
        except Exception:
            total_size = 0

        partitions.append({
            "device": part.device,
            "mountpoint": part.mountpoint,
            "fstype": part.fstype,
            "total_size": total_size,
            "flags": part.opts.split(',')
        })
    return partitions

def clone_partition(src_device, dest_file, progress_callback=None, stop_event=None):
    """Clone a partition to file with progress tracking and stop capability"""
    # Safety checks
    if not src_device.startswith('/dev/'):
        print(f"Error: {src_device} is not a valid block device path")
        return False

    if not os.path.exists(src_device):
        print(f"Error: Source device {src_device} does not exist")
        return False

    # Root check
    if os.geteuid() != 0:
        print("Error: This operation requires root privileges. Use sudo!")
        return False

    try:
        with open(src_device, 'rb') as f:
            device_size = os.lseek(f.fileno(), 0, os.SEEK_END)
    except Exception as e:
        print(f"Error getting device size: {str(e)}")
        return False

    try:
        with open(src_device, 'rb', buffering=0) as src, \
             open(dest_file, 'wb', buffering=0) as dest:

            print(f"Cloning {src_device} to {dest_file} ({device_size} bytes)")
            bytes_copied = 0
            chunk_size = 8 * 1024 * 1024  # 8MB chunks

            while bytes_copied < device_size:
                if stop_event and stop_event.is_set():
                    print("\nCloning stopped by user!")
                    return False

                remaining = device_size - bytes_copied
                chunk = src.read(min(chunk_size, remaining))
                if not chunk:
                    break

                dest.write(chunk)
                bytes_copied += len(chunk)

                if progress_callback:
                    progress_callback(bytes_copied, device_size)

            # Final flush and sync
            dest.flush()
            os.fsync(dest.fileno())
            print("\nClone completed successfully!")
            return True

    except PermissionError:
        print("Permission denied! Check file permissions")
        return False
    except Exception as e:
        print(f"Error: {str(e)}")
        return False