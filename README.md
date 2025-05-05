# Ansible Docker Cluster Automation

This project uses Ansible with a dynamic inventory system to configure Docker environments (including Docker Engine, Docker Compose, and preparing for Swarm) on target nodes based on environment-specific configuration files. Authentication is handled via SSH keys.

## Prerequisites

- Ansible (version 2.10 or later recommended)
- Python 3.x (usually installed with Ansible)
- `PyYAML` Python library (`pip install PyYAML`)
- SSH access configured from the Ansible control node to the target nodes:
    - The user specified in the config (`general_config.username`) must exist on target nodes.
    - The target nodes must be configured to allow SSH login for that user using the specified private key.
    - The private key file must exist on the Ansible control node.
- Passwordless `sudo` configured for the connection user on the target nodes (required for tasks using `become: yes`).

## Directory Structure

```
ansible_project/
├── ansible.cfg                 # Ansible configuration (defines plugin path)
├── inventory_plugins/          # Contains the custom inventory plugin
│   └── custom_cluster_inventory.py # Python script to parse cluster_config.yml
├── env/
│   ├── prod/
│   │   ├── cluster_config.yml    # **SOURCE OF TRUTH for 'prod'**
│   │   └── inventory.config.yml
│   ├── env1/
│   │   ├── cluster_config.yml    # **SOURCE OF TRUTH for 'env1'**
│   │   └── inventory.config.yml
│   └── env2/
│       ├── cluster_config.yml    # **SOURCE OF TRUTH for 'env2'**
│       └── inventory.config.yml
├── roles/                      # Contains Ansible roles
│   └── docker_dependencies/    # Role to install Docker, Compose, etc.
│       ├── tasks/
│       ├── handlers/
│       ├── defaults/
│       └── meta/
└── playbook.yml                # Playbook applying roles
```

## Configuration: The Source of Truth

The core configuration for each environment resides within its respective `cluster_config.yml` file inside the `env/` directory (e.g., `env/prod/cluster_config.yml`, `env/env1/cluster_config.yml`).

**These files are the single source of truth for defining your cluster nodes and settings for each environment.**

**You MUST update these files manually:**

1.  **Node IPs:** The most critical values to update are the `docker_node_ip` for each node within the `nodes:` section. These should be the actual IP addresses (Public or Private, depending on your network setup) of your target EC2 instances or other machines.
2.  **SSH Key Path:** Update `general_config.ssh_private_key_file` with the **absolute path** to the SSH private key file (`.pem` or similar) located on your Ansible control node. This key will be used for authentication.
3.  **Other Settings:** You can also adjust:
    - `general_config.docker_version`: Specify the desired Docker version.
    - `nodes.<node_name>.docker_node_name`: Assign logical names used within Docker (e.g., for Swarm).
    - `general_config.username`: The user Ansible will connect as (e.g., `proot`). This user must be authorized to log in with the specified key.

**Example `cluster_config.yml` structure:**

```yaml
general_config:
  docker_version: "24.0.5" # Set desired Docker version
  username: proot # User for SSH connection (must exist on targets)
  ssh_private_key_file: /home/user/.ssh/my-aws-key.pem # **UPDATE THIS ABSOLUTE PATH**

nodes:
  node01: # Logical name used by Ansible
    docker_node_name: docker-master # Name used within Docker
    docker_node_ip: 192.168.1.101 # **UPDATE THIS IP ADDRESS**

  node02:
    docker_node_name: docker-worker-1
    docker_node_ip: 192.168.1.102 # **UPDATE THIS IP ADDRESS**

  node03:
    docker_node_name: docker-worker-2
    docker_node_ip: 192.168.1.103 # **UPDATE THIS IP ADDRESS**
```

## Usage

All Ansible commands need to be pointed to the specific environment you want to target using the `-i` flag followed by the path to the `inventory.config.yml` file within that environment's directory.


**1. Running Playbooks:**

To apply the configuration defined in a playbook (e.g., `playbook.yml`) to a specific environment:

```bash
# Example for 'env1'
ansible-playbook -i env/env1/inventory.config.yml playbook.yml

# Example for 'prod'
ansible-playbook -i env/prod/inventory.config.yml playbook.yml
```
*(If your playbook tasks require privilege escalation, they should include `become: yes`. No extra flags are needed on the command line due to passwordless sudo.)*

**2. Running Ad-hoc Commands:**

To run single commands against hosts in an environment:

```bash
# Example: Ping all hosts in 'env1'
ansible -i env/env1/inventory.config.yml all -m ping

# Example: Check free memory on all hosts in 'prod' (no privilege needed)
ansible -i env/prod/inventory.config.yml all -m shell -a "free -h"

# Example: Run 'whoami' as root on all hosts in 'env1' (requires privilege)
ansible -i env/env1/inventory.config.yml all -m shell -a "whoami" --become
```

**3. Verifying the Dynamic Inventory:**

You can check the inventory that Ansible generates from your `cluster_config.yml` without running any tasks:

```bash
# Show inventory graph for 'env1'
ansible-inventory -i env/env1/inventory.config.yml --graph

# Show detailed inventory list with variables for 'env1'
ansible-inventory -i env/env1/inventory.config.yml --list
```
*(Note: If you choose to encrypt *other* variables in `cluster_config.yml` using Ansible Vault, you might need `--ask-vault-pass` for the `--list` command to display them.)*

## Security Considerations

- **SSH Private Key Security:** The private key specified in `ssh_private_key_file` must be kept secure on your Ansible control node. Ensure its file permissions restrict access (e.g., `chmod 400 /path/to/your/key.pem`). Anyone with access to this key can potentially access your target servers.
- **Passwordless Sudo:** This setup assumes the connection user (`general_config.username`) has passwordless sudo configured on the target machines. Ensure this is intentional and appropriately secured (e.g., limited to specific commands if necessary via the `sudoers` file).
- **SSH Host Key Checking:** `ansible.cfg` currently has `host_key_checking = False` for convenience during initial setup. In a production environment, you should set this to `True` and manage SSH known_hosts files properly to prevent man-in-the-middle attacks.

