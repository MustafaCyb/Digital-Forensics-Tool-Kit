import pyshark
import json
import requests
from know_provider import get_ip_info
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from collections import defaultdict
import os
def is_reserved_ip(ip):
    """Check if an IP address is in reserved/non-public ranges."""
    try:
        octets = list(map(int, ip.split('.')))
        
        # IPv4 reserved ranges
        if octets[0] == 10:  # 10.0.0.0/8
            return ("Private", "RFC 1918")
        if octets[0] == 172 and 16 <= octets[1] <= 31:  # 172.16.0.0/12
            return ("Private", "RFC 1918")
        if octets[0] == 192 and octets[1] == 168:  # 192.168.0.0/16
            return ("Private", "RFC 1918")
        if octets[0] == 127:  # Loopback
            return ("Reserved", "Loopback")
        if octets[0] == 169 and octets[1] == 254:  # Link-local
            return ("Reserved", "Link-local")
        if 224 <= octets[0] <= 239:  # Multicast
            return ("Reserved", "Multicast")
        if octets[0] == 255 and octets[1] == 255:  # Broadcast
            return ("Reserved", "Broadcast")
            
        return None
    except (ValueError, IndexError):
        return None

def fetch_ip_from_api(ip):
    """Retrieve IP information from external API."""
    try:
        response = requests.get(f"https://ipinfo.io/{ip}/json", timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"API Error for {ip}: {str(e)}")
        return None

@lru_cache(maxsize=1000)
def cached_get_ip_info(ip):
    """Fetch IP information with caching, fallback to API if not in database."""
    # First try local database
    db_info = get_ip_info(ip)
    if db_info:
        return db_info
    
    # If not found, try API
    api_info = fetch_ip_from_api(ip)
    if api_info:
        # soon....
        # For example: store_ip_info(ip, api_info)
        pass
    return api_info

def process_packet(packet, filter_protocol=None):
    """Process a single packet and return its details."""
    try:
        if filter_protocol and not any(layer.layer_name.upper() == filter_protocol.upper() for layer in packet.layers):
            return None

        packet_details = {
            "time": packet.sniff_time,
            "length": int(packet.length),
            "src_ip": packet.ip.src if "IP" in packet else None,
            "dst_ip": packet.ip.dst if "IP" in packet else None,
            "protocol": None,
            "ip_info": None,
        }

        if "TCP" in packet:
            packet_details["protocol"] = "TCP"
        elif "UDP" in packet:
            packet_details["protocol"] = "UDP"
        elif "DNS" in packet:
            packet_details["protocol"] = "DNS"
        elif "HTTP" in packet:
            packet_details["protocol"] = "HTTP"

        if packet_details["dst_ip"]:
            reserved_info = is_reserved_ip(packet_details["dst_ip"])
            if reserved_info:
                ip_type, description = reserved_info
                packet_details["ip_info"] = {
                    "type": ip_type,
                    "description": description,
                    "note": "Non-routable address"
                }
            else:
                packet_details["ip_info"] = cached_get_ip_info(packet_details["dst_ip"])
        
        return packet_details

    except Exception as e:
        return {"error": str(e)}

def generate_report(file_path, output_file, filter_protocol=None):
    """Analyzes the pcap file and generates an HTML report with enhanced visualization."""
    try:
        # Validate input file
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PCAP file not found: {file_path}")
        if not os.path.isfile(file_path):
            raise ValueError(f"Invalid file path: {file_path}")

        # Initialize capture with error handling
        try:
            capture = pyshark.FileCapture(file_path, use_json=True)
        except Exception as e:
            raise RuntimeError(f"Failed to open PCAP file: {str(e)}")

        # Initialize tracking variables
        protocol_counts = defaultdict(int)
        total_size = 0
        results = []
        size_data = []
        ip_counts = defaultdict(int)
        timeline_data = []

        # Process packets in parallel
        with ThreadPoolExecutor() as executor:
            packet_results = list(executor.map(
                lambda p: process_packet(p, filter_protocol),
                capture
            ))

        # Filter and count valid packets
        processed_count = 0
        for result in packet_results:
            if result and not result.get("error"):
                results.append(result)
                processed_count += 1
                
                # Update statistics
                total_size += result["length"]
                protocol_counts[result["protocol"] or "Unknown"] += 1
                
                if result["src_ip"]:
                    ip_counts[result["src_ip"]] += 1
                if result["dst_ip"]:
                    ip_counts[result["dst_ip"]] += 1
                
                size_data.append(result["length"])
                timeline_data.append({
                    "time": result["time"].timestamp(),
                    "size": result["length"]
                })

        # Calculate statistics
        avg_packet_size = total_size / processed_count if processed_count else 0
        top_ips = sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        size_bins = [
            len([x for x in size_data if x < 500]),
            len([x for x in size_data if 500 <= x < 1000]),
            len([x for x in size_data if 1000 <= x < 1500]),
            len([x for x in size_data if x >= 1500])
        ]

        # Generate HTML content
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PCAP Analysis Report</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://unpkg.com/ionicons@4.5.10-0/dist/css/ionicons.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --accent: #8b5cf6;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --glass: rgba(255, 255, 255, 0.05);
        }}

        body {{
            font-family: 'Inter', system-ui, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
        }}

        .header {{
            background: linear-gradient(135deg, var(--bg-secondary), #2e1065);
            padding: 4rem 2rem;
            margin: -20px -20px 3rem -20px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
            position: relative;
            overflow: hidden;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }}

        .header::before {{
            content: '';
            position: absolute;
            top: -50px;
            left: -50px;
            width: 150px;
            height: 150px;
            background: var(--accent);
            opacity: 0.1;
            border-radius: 50%;
            filter: blur(40px);
        }}

        .header::after {{
            content: '';
            position: absolute;
            bottom: -50px;
            right: -50px;
            width: 200px;
            height: 200px;
            background: var(--accent);
            opacity: 0.05;
            border-radius: 50%;
            filter: blur(60px);
        }}

        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 2rem;
            margin: 2rem 0;
        }}

        .card {{
            background: linear-gradient(145deg, var(--bg-secondary), #1a2333);
            border-radius: 20px;
            padding: 2rem;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.18);
            border: 1px solid rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            transition: transform 0.2s ease;
        }}

        .card:hover {{
            transform: translateY(-5px);
        }}

        .chart-container {{
            height: 320px;
            position: relative;
            margin-top: 1.5rem;
        }}

        .packet-card {{
            background: var(--bg-secondary);
            border-radius: 16px;
            margin-bottom: 1.5rem;
            padding: 2rem;
            border: 1px solid rgba(255, 255, 255, 0.1);
            transition: all 0.2s ease;
        }}

        .packet-card:hover {{
            background: #1e293b;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}

        .packet-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
            padding-bottom: 1.5rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }}

        .packet-details {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap: 1.5rem;
            margin-top: 1.5rem;
        }}

        .detail-item {{
            background: var(--glass);
            padding: 1.5rem;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }}

        .badge {{
            display: inline-flex;
            align-items: center;
            padding: 0.5rem 1rem;
            border-radius: 24px;
            font-size: 0.9em;
            gap: 0.75rem;
            transition: all 0.2s ease;
        }}

        .protocol-badge {{
            background: linear-gradient(135deg, var(--accent), #6d28d9);
            color: white;
            box-shadow: 0 2px 8px rgba(139, 92, 246, 0.2);
        }}

        .size-badge {{
            background: linear-gradient(135deg, var(--warning), #d97706);
            color: black;
        }}

        .ip-info {{
            margin-top: 1.5rem;
            padding: 1.5rem;
            background: rgba(139, 92, 246, 0.08);
            border-radius: 12px;
            display: grid;
            gap: 0.75rem;
            border: 1px solid rgba(139, 92, 246, 0.15);
        }}

        .error-card {{
            background: var(--danger);
            color: white;
            padding: 2.5rem;
            border-radius: 16px;
            margin: 2rem 0;
            text-align: center;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 1.5rem;
        }}

        th, td {{
            padding: 1rem;
            text-align: left;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }}

        th {{
            font-weight: 600;
            background: rgba(255, 255, 255, 0.05);
        }}

        tr:hover td {{
            background: rgba(255, 255, 255, 0.02);
        }}

        h2 {{
            margin: 0 0 1.5rem 0;
            font-size: 1.5rem;
            display: flex;
            align-items: center;
            gap: 1rem;
        }}

        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        .card, .packet-card {{
            animation: fadeIn 0.6s ease forwards;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1 style="margin:0;font-size:2.75rem;font-weight:700;letter-spacing:-0.05em">
            <i class="icon ion-md-pulse" style="color: var(--accent);"></i>
            Network Intelligence Report
        </h1>
        <div style="opacity:0.8;margin:1rem 0 0 0;display:flex;gap:1.5rem;font-size:0.95em">
            <div style="display:flex;align-items:center;gap:0.5rem">
                <i class="icon ion-md-document"></i>
                {os.path.basename(file_path)}
            </div>
            <div style="display:flex;align-items:center;gap:0.5rem">
                <i class="icon ion-md-stats"></i>
                {processed_count} packets analyzed
            </div>
        </div>
    </div>

    {f'''
    <div class="grid">
        <div class="card">
            <h2><i class="icon ion-md-pie" style="color: var(--accent);"></i>Protocol Distribution</h2>
            <div class="chart-container">
                <canvas id="protocolChart"></canvas>
            </div>
        </div>

        <div class="card">
            <h2><i class="icon ion-md-stats" style="color: var(--warning);"></i>Packet Size Analysis</h2>
            <div class="chart-container">
                <canvas id="sizeChart"></canvas>
            </div>
        </div>
    </div>

    <div class="card">
        <h2><i class="icon ion-md-trending-up" style="color: var(--success);"></i>Top Communicators</h2>
        <table>
            <thead>
                <tr>
                    <th>IP Address</th>
                    <th>Packet Count</th>
                </tr>
            </thead>
            <tbody>
                {'\n'.join([f'<tr><td>{ip}</td><td>{count}</td></tr>' for ip, count in top_ips])}
            </tbody>
        </table>
    </div>

    <div class="card">
        <h2><i class="icon ion-md-time" style="color: #6366f1;"></i>Traffic Timeline</h2>
        <div class="chart-container">
            <canvas id="timelineChart"></canvas>
        </div>
    </div>

    <h2 style="margin:3rem 0 1.5rem 0;"><i class="icon ion-md-list" style="color: var(--text-secondary);"></i>Packet Details</h2>
    {'\n'.join([f'''
    <div class="packet-card">
        <div class="packet-header">
            <div style="display:flex; gap:1.5rem; align-items:center">
                <span class="badge protocol-badge">
                    <i class="icon ion-md-arrow-round-forward"></i>
                    {p['protocol'] or 'Unknown'}
                </span>
                <span class="badge size-badge">
                    <i class="icon ion-md-speedometer"></i>
                    {p['length']} bytes
                </span>
                <span style="opacity:0.7; font-size:0.9em;display:flex;align-items:center;gap:0.5rem">
                    <i class="icon ion-md-time"></i>
                    {p['time']}
                </span>
            </div>
        </div>
        
        <div class="packet-details">
            <div class="detail-item">
                <h3 style="margin:0 0 0.75rem 0;font-size:1.1em">
                    <i class="icon ion-md-locate" style="color: #7c3aed;"></i>
                    Source Address
                </h3>
                <div style="opacity:0.9;font-family:monospace">{p['src_ip'] or 'N/A'}</div>
            </div>
            
            <div class="detail-item">
                <h3 style="margin:0 0 0.75rem 0;font-size:1.1em">
                    <i class="icon ion-md-pin" style="color: #ef4444;"></i>
                    Destination Address
                </h3>
                <div style="opacity:0.9;font-family:monospace">{p['dst_ip'] or 'N/A'}</div>
            </div>
            
            {f'''
            <div class="ip-info">
                <h3 style="margin:0 0 1rem 0;font-size:1.1em">
                    <i class="icon ion-md-information-circle-outline"></i>
                    GeoIP Intelligence
                </h3>
                {'\n'.join([f'''
                <div style="display:flex; justify-content: space-between; align-items: center; padding: 0.5rem 0; border-bottom: 1px solid rgba(139, 92, 246, 0.1);">
                    <span style="opacity:0.8">{k}:</span>
                    <span style="font-weight:500;color: var(--accent)">{v}</span>
                </div>
                ''' for k, v in p['ip_info'].items() if v])}
            </div>
            ''' if p.get('ip_info') else ''}
        </div>
    </div>
    ''' for p in results])}
    ''' if processed_count > 0 else '''
    <div class="error-card">
        <h2 style="margin:0 0 1.5rem 0;"><i class="icon ion-md-warning" style="font-size:2em;"></i>No Processable Packets Detected</h2>
        <div style="background: rgba(255, 255, 255, 0.1); padding: 1.5rem; border-radius: 12px; text-align: left;">
            <p style="margin:0 0 1rem 0;font-weight:500">Troubleshooting Guide:</p>
            <ul style="margin:0;padding-left:1.5rem;opacity:0.9">
                <li>Verify protocol filter settings</li>
                <li>Check file format compatibility</li>
                <li>Inspect network capture permissions</li>
                <li>Review file encryption status</li>
            </ul>
        </div>
    </div>
    '''}

    <script>
        {f'''
        // Protocol Chart
        new Chart(document.getElementById('protocolChart'), {{
            type: 'doughnut',
            data: {{
                labels: {json.dumps(list(protocol_counts.keys()))},
                datasets: [{{
                    data: {json.dumps(list(protocol_counts.values()))},
                    backgroundColor: [
                        '#8b5cf6', '#7c3aed', '#6d28d9', '#5b21b6', '#4c1d95'
                    ],
                    borderWidth: 0,
                    hoverOffset: 20
                }}]
            }},
            options: {{
                plugins: {{
                    legend: {{
                        position: 'right',
                        labels: {{
                            color: '#f8fafc',
                            font: {{ size: 14 }}
                        }}
                    }},
                    tooltip: {{
                        backgroundColor: 'rgba(17, 24, 39, 0.9)',
                        titleColor: '#f8fafc',
                        bodyColor: '#e5e7eb'
                    }}
                }}
            }}
        }});

        // Size Distribution
        new Chart(document.getElementById('sizeChart'), {{
            type: 'bar',
            data: {{
                labels: ['<500', '500-1000', '1000-1500', '>1500'],
                datasets: [{{
                    label: 'Packet Count',
                    data: {json.dumps(size_bins)},
                    backgroundColor: 'rgba(139, 92, 246, 0.3)',
                    borderColor: '#8b5cf6',
                    borderWidth: 2,
                    borderRadius: 8
                }}]
            }},
            options: {{
                responsive: true,
                scales: {{
                    y: {{
                        beginAtZero: true,
                        grid: {{ color: 'rgba(255, 255, 255, 0.1)' }},
                        ticks: {{ color: '#94a3b8' }}
                    }},
                    x: {{
                        grid: {{ display: false }},
                        ticks: {{ color: '#94a3b8' }}
                    }}
                }},
                plugins: {{
                    legend: {{
                        labels: {{
                            color: '#f8fafc',
                            font: {{ size: 14 }}
                        }}
                    }}
                }}
            }}
        }});

        // Timeline Chart
        new Chart(document.getElementById('timelineChart'), {{
            type: 'line',
            data: {{
                datasets: [{{
                    label: 'Packet Size Over Time',
                    data: {json.dumps(timeline_data)},
                    borderColor: '#8b5cf6',
                    backgroundColor: 'rgba(139, 92, 246, 0.1)',
                    tension: 0.4,
                    pointRadius: 3,
                    pointHoverRadius: 6
                }}]
            }},
            options: {{
                parsing: {{
                    xAxisKey: 'time',
                    yAxisKey: 'size'
                }},
                scales: {{
                    x: {{
                        type: 'linear',
                        position: 'bottom',
                        grid: {{ color: 'rgba(255, 255, 255, 0.1)' }},
                        ticks: {{
                            color: '#94a3b8',
                            callback: function(value) {{
                                return new Date(value * 1000).toLocaleTimeString();
                            }}
                        }}
                    }},
                    y: {{
                        beginAtZero: true,
                        grid: {{ color: 'rgba(255, 255, 255, 0.1)' }},
                        ticks: {{ color: '#94a3b8' }}
                    }}
                }},
                plugins: {{
                    tooltip: {{
                        callbacks: {{
                            title: function(context) {{
                                return 'Time: ' + new Date(context[0].parsed.x * 1000).toLocaleString();
                            }},
                            label: function(context) {{
                                return 'Size: ' + context.parsed.y + ' bytes';
                            }}
                        }}
                    }}
                }}
            }}
        }});
        ''' if processed_count > 0 else ''}
    </script>
</body>
</html>
''')

    except Exception as e:
        error_html = f'''
        <html>
        <head><title>Report Error</title></head>
        <body style="background:#0f172a;color:white;padding:2rem">
            <h1>⚠️ Report Generation Failed</h1>
            <div style="background:#ef444455;padding:1rem;border-radius:8px">
                <p><strong>Error:</strong> {str(e)}</p>
                <p>Possible solutions:</p>
                <ul>
                    <li>Verify PCAP file integrity</li>
                    <li>Check network permissions</li>
                    <li>Ensure tshark is installed</li>
                    <li>Try without protocol filters</li>
                </ul>
            </div>
        </body>
        </html>
        '''
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(error_html)
        print(f"Report generation error: {str(e)}")