# Network Backup Automation

A professional Python tool that automates SSH-based backups of network device configurations. Built for network engineers who need reliable, scheduled backups of routers, switches, firewalls, and other network infrastructure.

## Features

- **Multi-vendor support** - Cisco IOS, ASA, NX-OS, Juniper JunOS, Arista EOS
- - **Concurrent backups** - Thread pool executor backs up multiple devices simultaneously
  - - **Timestamped configs** - Every backup is saved with a date/time stamp for easy versioning
    - - **JSON inventory** - Simple, human-readable device inventory format
      - - **Automated reporting** - Generates a JSON summary report after each run
        - - **Error handling** - Graceful handling of timeouts, auth failures, and connectivity issues
          - - **CLI interface** - Flexible command-line options for integration with cron or task schedulers
           
            - ## Project Structure
           
            - ```
              network-backup-automation/
              |-- network_backup.py      # Main backup automation script
              |-- inventory.json         # Device inventory (template)
              |-- requirements.txt       # Python dependencies
              |-- .gitignore
              |-- LICENSE
              +-- backups/               # Auto-created backup directory
                  +-- 2026-04-08/
                      |-- core-rtr-01_20260408_140000.cfg
                      |-- dist-sw-01_20260408_140005.cfg
                      +-- backup_report.json
              ```

              ## Quick Start

              ### 1. Clone the Repository

              ```bash
              git clone https://github.com/jczaldivar71/network-backup-automation.git
              cd network-backup-automation
              ```

              ### 2. Create a Virtual Environment

              ```bash
              python -m venv venv
              source venv/bin/activate   # Linux/macOS
              venv\Scripts\activate      # Windows
              ```

              ### 3. Install Dependencies

              ```bash
              pip install -r requirements.txt
              ```

              ### 4. Configure Your Device Inventory

              Edit `inventory.json` with your network devices:

              ```json
              [
                  {
                      "hostname": "core-rtr-01",
                      "host": "192.168.1.1",
                      "device_type": "cisco_ios",
                      "username": "admin",
                      "password": "your_password",
                      "port": 22,
                      "secret": "enable_secret"
                  }
              ]
              ```

              ### 5. Run Backups

              ```bash
              python network_backup.py
              ```

              ## Usage

              ```bash
              # Basic usage (uses inventory.json in current directory)
              python network_backup.py

              # Specify a custom inventory file
              python network_backup.py -i /path/to/devices.json

              # Custom output directory
              python network_backup.py -o /var/backups/network

              # Increase concurrent connections
              python network_backup.py --workers 10

              # Enable verbose (debug) logging
              python network_backup.py -v
              ```

              ## Supported Device Types

              | Device Type | device_type Value | Backup Command |
              |---|---|---|
              | Cisco IOS | cisco_ios | show running-config |
              | Cisco ASA | cisco_asa | show running-config |
              | Cisco NX-OS | cisco_nxos | show running-config |
              | Juniper JunOS | juniper_junos | show configuration display set |
              | Arista EOS | arista_eos | show running-config |

              ## Scheduling with Cron

              ```bash
              0 2 * * * cd /opt/network-backup-automation && /opt/venv/bin/python network_backup.py >> /var/log/net_backup.log 2>&1
              ```

              ## Security Best Practices

              - **Never commit credentials** - Use environment variables or a secrets manager
              - - **Restrict file permissions** - chmod 600 inventory.json
                - - **Use SSH keys** - Configure key-based auth where possible
                  - - **Encrypt backups** - Consider encrypting saved configurations at rest
                   
                    - ## Requirements
                   
                    - - Python 3.9+
                      - - Network devices reachable via SSH
                        - - Valid credentials with privilege to view running config
                         
                          - ## License
                         
                          - This project is licensed under the MIT License.
                         
                          - ## Author
                         
                          - **Jonathan Zaldivar**
                          - Blog: [Network ThinkTank](https://networkthinktank.blog)
                          - Certifications: CCNA, CCNA Cyber Ops
