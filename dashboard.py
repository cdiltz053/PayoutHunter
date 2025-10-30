import json
import os
from flask import Flask, render_template_string, jsonify

app = Flask(__name__)

STATS_FILE = "hunt_stats.json"
FOUND_LINKS_FILE = "found_payouts.json"

@app.route('/')
def index():
    # HTML template for the dashboard
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Payout Hunter Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background-color: #f4f4f9; color: #333; }
            .container { max-width: 1400px; margin: auto; background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
            h1 { color: #007bff; border-bottom: 2px solid #007bff; padding-bottom: 10px; }
            .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }
            .stat-box { background: #e9ecef; padding: 15px; border-radius: 6px; text-align: center; }
            .stat-box h2 { margin: 0 0 5px 0; font-size: 1.2em; color: #555; }
            .stat-box p { margin: 0; font-size: 2em; font-weight: bold; color: #007bff; }
            .links-table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            .links-table th, .links-table td { border: 1px solid #ddd; padding: 10px; text-align: left; }
            .links-table th { background-color: #007bff; color: white; }
            .links-table tr:nth-child(even) { background-color: #f2f2f2; }
            .links-table tr:hover { background-color: #ddd; }
            .key-found { color: #28a745; font-weight: bold; }
            .key-not-found { color: #dc3545; font-weight: bold; }
            .key-bypass { color: #ffc107; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Payout Hunter Real-Time Dashboard</h1>
            <div class="stats-grid" id="stats-grid">
                <div class="stat-box"><h2>Total Checked</h2><p id="total_checked">0</p></div>
                <div class="stat-box"><h2>Total Found</h2><p id="total_found">0</p></div>
                <div class="stat-box"><h2>Checks Per Second</h2><p id="checks_per_sec">0/s</p></div>
                <div class="stat-box"><h2>Last Found</h2><p id="last_found">N/A</p></div>
            </div>

            <h2>Found Payout Links</h2>
            <table class="links-table">
                <thead>
                    <tr>
                        <th>Found At</th>
                        <th>Link ID</th>
                        <th>Verification Key</th>
                        <th>Status</th>
                        <th>Link</th>
                    </tr>
                </thead>
                <tbody id="links-tbody">
                    <!-- Links will be inserted here by JavaScript -->
                </tbody>
            </table>
        </div>

        <script>
            function getStatusClass(status) {
                if (status.includes('PASSIVE')) return 'key-found';
                if (status.includes('BYPASS')) return 'key-bypass';
                return 'key-not-found';
            }

            function getVerificationKey(status) {
                // Key is the first word after Key:
                const match = status.match(/Key:\s*(\S+)/);
                if (match && match[1] !== 'NOT') {
                    return match[1].replace(/'/g, ''); // Clean up quotes if any
                }
                return 'N/A';
            }

            function fetchData() {
                fetch('/data')
                    .then(response => response.json())
                    .then(data => {
                        // Update Stats Grid
                        document.getElementById('total_checked').textContent = data.stats.total_checked.toLocaleString();
                        document.getElementById('total_found').textContent = data.stats.total_found;
                        document.getElementById('checks_per_sec').textContent = data.stats.checks_per_sec.toFixed(0) + '/s';
                        document.getElementById('last_found').textContent = data.stats.last_found || 'N/A';

                        // Update Links Table
                        const tbody = document.getElementById('links-tbody');
                        tbody.innerHTML = ''; // Clear existing rows
                        
                        data.links.forEach(link => {
                            const row = tbody.insertRow();
                            row.insertCell().textContent = new Date(link.found_at).toLocaleTimeString();
                            row.insertCell().textContent = link.id;
                            
                            // Verification Key Cell
                            const keyCell = row.insertCell();
                            keyCell.textContent = getVerificationKey(link.key_status);
                            keyCell.className = getStatusClass(link.key_status);

                            // Status Cell
                            const statusCell = row.insertCell();
                            statusCell.textContent = link.key_status.replace(/Key:\s*(\S+)/, 'Key: ...'); // Hide key in status column
                            statusCell.className = getStatusClass(link.key_status);
                            
                            const linkCell = row.insertCell();
                            const a = document.createElement('a');
                            a.href = link.url;
                            a.target = '_blank';
                            a.textContent = 'Open Link';
                            linkCell.appendChild(a);
                        });
                    })
                    .catch(error => console.error('Error fetching data:', error));
            }

            // Fetch data immediately and then every 5 seconds
            fetchData();
            setInterval(fetchData, 5000);
        </script>
    </body>
    </html>
    """
    return render_template_string(html_template)

@app.route('/data')
def data():
    # Load stats
    stats = {}
    try:
        with open(STATS_FILE, 'r') as f:
            stats = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        stats = {'total_checked': 0, 'total_found': 0, 'last_found': 'N/A', 'checks_per_sec': 0}

    # Load links
    links = []
    try:
        with open(FOUND_LINKS_FILE, 'r') as f:
            data = json.load(f)
            links = data.get('links', [])
            # Sort by found_at descending
            links.sort(key=lambda x: x.get('found_at', ''), reverse=True)
            # Limit to last 50 links for dashboard performance
            links = links[:50]
    except (FileNotFoundError, json.JSONDecodeError):
        links = []

    stats['checks_per_sec'] = stats.get('checks_per_sec', 0)

    return jsonify(stats=stats, links=links)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
