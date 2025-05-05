# 🐳 Ansible Docker Swarm Cluster Automation ⚙️

This project utilizes Ansible with a dynamic inventory system to automatically configure Docker environments, including Docker Engine, Docker Compose, and Docker Swarm, on target nodes. Configuration is driven by environment-specific files, and authentication relies on SSH keys.

## ✅ Prerequisites

Before you begin, ensure you have the following:

*   **Ansible:** Version 2.10 or later recommended (`ansible --version`).
*   **Python:** Version 3.x (usually installed with Ansible).
*   **PyYAML:** Python library (`pip install PyYAML`).
*   **SSH Access:** 🔑 Configured from the Ansible control node to all target nodes:
    *   The user specified in `general_config.username` must exist on target nodes.
    *   Target nodes must authorize SSH login for that user via the specified private key.
    *   The private key file (`.pem` or similar) must exist on the Ansible control node.
*   **Passwordless `sudo`:** Configured for the connection user on target nodes (required for tasks using `become: yes`).

## 📁 Directory Structure

```
ansible_project/
├── ansible.cfg                 # Ansible configuration (plugin path, etc.)
├── inventory_plugins/          # Custom inventory plugin directory
│   └── custom_cluster_inventory.py # Python script to parse cluster_config.yml
├── env/                        # Environment-specific configurations
│   ├── prod/                   # Example: Production environment
│   │   ├── cluster_config.yml    # 🌟 **SOURCE OF TRUTH for 'prod'**
│   │   └── inventory.config.yml  # Inventory pointer for 'prod'
│   ├── env1/                   # Example: Env1 environment
│   │   ├── cluster_config.yml    # 🌟 **SOURCE OF TRUTH for 'env1'**
│   │   └── inventory.config.yml  # Inventory pointer for 'env1'
│   └── env2/                   # Example: Env2 environment
│       ├── cluster_config.yml    # 🌟 **SOURCE OF TRUTH for 'env2'**
│       └── inventory.config.yml  # Inventory pointer for 'env2'
├── roles/                      # Ansible roles
│   ├── docker_dependencies/    # Role: Install Docker, Compose, etc.
│   │   └── ... (tasks, handlers, etc.)
│   └── docker_swarm/           # Role: Configure Docker Swarm
│       └── ... (tasks, etc.)
└── playbook.yml                # Main playbook orchestrating roles
```

## ⚙️ Configuration: The Source of Truth

The core configuration for each environment resides within its respective `cluster_config.yml` file inside the `env/` directory (e.g., `env/prod/cluster_config.yml`).

**⚠️ These files are the single source of truth for defining your cluster nodes and settings for each environment.**

**✍️ You MUST update these files manually:**

1.  **Node IPs (`docker_node_ip`):** Update with the actual IP addresses (Public or Private) of your target machines within the `nodes:` section. This is critical!
2.  **SSH Key Path (`ssh_private_key_file`):** Update `general_config.ssh_private_key_file` with the **absolute path** to the SSH private key file on your Ansible control node.
3.  **Other Settings (Optional):**
    *   `general_config.docker_version`: Specify the desired Docker version.
    *   `nodes.<node_name>.docker_node_name`: Assign logical names (e.g., `docker-master`, `docker-worker-1`). These are used for setting hostnames and determining Swarm roles.
    *   `general_config.username`: The user Ansible will connect as (must be authorized via the key).

**Example `cluster_config.yml` structure:**

```yaml
general_config:
  docker_version: "25.0.8" # Set desired Docker version
  username: proot          # User for SSH connection
  ssh_private_key_file: /home/user/.ssh/my-aws-key.pem # ❗ **UPDATE THIS ABSOLUTE PATH**

nodes:
  node01: # Logical name used by Ansible
    docker_node_name: docker-master # Designates Swarm Master & Hostname
    docker_node_ip: 192.168.1.101   # ❗ **UPDATE THIS IP ADDRESS**

  node02:
    docker_node_name: docker-worker-1 # Designates Swarm Worker & Hostname
    docker_node_ip: 192.168.1.102   # ❗ **UPDATE THIS IP ADDRESS**

  node03:
    docker_node_name: docker-worker-2 # Designates Swarm Worker & Hostname
    docker_node_ip: 192.168.1.103   # ❗ **UPDATE THIS IP ADDRESS**
```

## ▶️ Usage

All Ansible commands need to target a specific environment using the `-i` flag pointing to the `inventory.config.yml` file for that environment.

**1. Running the Main Playbook:**

Apply the full configuration (Docker install, Swarm setup, hostname setting) defined in `playbook.yml`:

```bash
# Example for 'env1'
ansible-playbook -i env/env1/inventory.config.yml playbook.yml

# Example for 'prod'
ansible-playbook -i env/prod/inventory.config.yml playbook.yml
```
*(No extra flags like `--ask-become-pass` are typically needed due to passwordless sudo.)*

**2. Running Ad-hoc Commands:**

Execute single commands against hosts in an environment:

```bash
# Example: Ping all hosts in 'env1' 핑
ansible -i env/env1/inventory.config.yml all -m ping

# Example: Check free memory on all hosts in 'prod' 💾
ansible -i env/prod/inventory.config.yml all -m shell -a "free -h"

# Example: Run 'whoami' as root on all hosts in 'env1' (requires privilege) 👑
ansible -i env/env1/inventory.config.yml all -m shell -a "whoami" --become

# Example: Check Swarm node status from the master 🚢
ansible -i env/env1/inventory.config.yml swarm_master -m command -a "sudo docker node ls"
# Note: 'swarm_master' group only exists during playbook runs, use direct master hostname/IP for ad-hoc checks if needed.
```

**3. Verifying the Dynamic Inventory:**

Check the inventory Ansible generates without running tasks:

```bash
# Show inventory graph for 'env1' 📊
ansible-inventory -i env/env1/inventory.config.yml --graph

# Show detailed inventory list with variables for 'env1' 📋
ansible-inventory -i env/env1/inventory.config.yml --list
```
*(Note: `--list` might require `--ask-vault-pass` if you encrypt *other* variables in `cluster_config.yml`.)*

## 🔒 Security Considerations

*   **SSH Private Key Security:** Protect the private key specified in `ssh_private_key_file`. Ensure strict file permissions (`chmod 400 /path/to/key.pem`). Compromise of this key grants access to your servers.
*   **Passwordless Sudo:** This setup relies on the connection user having passwordless sudo. Ensure this configuration is intentional and secured appropriately (e.g., limit sudo privileges in the `/etc/sudoers` file if necessary).
*   **SSH Host Key Checking:** `ansible.cfg` currently has `host_key_checking = False`. For production, set this to `True` and manage SSH `known_hosts` files to prevent Man-in-the-Middle (MitM) attacks.
*   **Network Security (Firewalls/Security Groups):** Ensure your network configuration (e.g., AWS Security Groups, on-prem firewalls) allows the necessary traffic between nodes for Swarm operation (TCP 2377, UDP 7946, UDP 4789).

