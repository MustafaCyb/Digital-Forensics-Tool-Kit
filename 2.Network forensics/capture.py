import logging
logging.getLogger("scapy").setLevel(logging.ERROR)  # Only show errors


from scapy.all import sniff, wrpcap
import datetime
import os


def capture_traffic(output_file, log_file, duration, filter_exp=None):
    

    try:
        # Capture packets using the default interface
        packets = sniff(filter=filter_exp, timeout=duration)
        

        # Save captured packets to a .pcap file
        wrpcap(output_file, packets)
        

        # Log capture summary
        with open(log_file, 'w') as log:
            log.write("=== Packet Capture Summary ===\n")
            log.write(f"Total Packets Captured: {len(packets)}\n")
            log.write(f"Filter Applied: {filter_exp}\n")
            log.write(f"Capture Duration: {duration} seconds\n")

        

    except Exception as e:
        print(f"Error during capture: {e}")


if __name__ == "__main__":
    try:
        # Enter capture duration
        capture_duration = int(input("Enter capture duration (in seconds): "))

        # Optional packet filter
        packet_filter = input("Enter a filter (e.g., 'tcp', 'udp', 'icmp', or leave blank for no filter): ")

        # Enter a custom file name or use default
        file_name = input("Enter a file name for the capture (leave blank for default): ")

        # Get the current directory where the script is located
        script_directory = os.path.dirname(os.path.realpath(__file__))

        # Create timestamp for unique filenames
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        # Combine the script directory with the file names for saving
        pcap_file = os.path.join(f"{script_directory}\\Pcaps", f"{file_name or 'network_capture'}_{timestamp}.pcap")
        log_file = os.path.join(f"{script_directory}\\Logs", f"{file_name or 'capture_summary'}_{timestamp}.log")

        # Start capturing traffic
        capture_traffic(pcap_file, log_file, capture_duration, filter_exp=packet_filter)
    except Exception as e:
        print(f"Error: {e}")
