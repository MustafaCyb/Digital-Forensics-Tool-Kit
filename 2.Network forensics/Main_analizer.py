# main.py
from report_generator import generate_report

if __name__ == "__main__":
    # Path to the .pcap file
    pcap_file = input("Enter the path to the .pcap file: ")
    output_file = input("Enter the name of the report (without extension): ") + ".html"

    # Optional protocol filter
    protocol_filter = input("Enter a protocol to filter (e.g., TCP, UDP, DNS, or leave blank for all): ")

    # Call the report generator function
    generate_report(pcap_file, f"Generated_Reports\\{output_file}", filter_protocol=protocol_filter)
