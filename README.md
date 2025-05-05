# Ansible Docker Cluster Automation

This project uses Ansible with a dynamic inventory system to configure Docker environments (including Docker Engine, Docker Compose, and preparing for Swarm) on target nodes based on environment-specific configuration files.

## Prerequisites

- Ansible (version 2.10 or later recommended)
- Python 3.x (usually installed with Ansible)
- `PyYAML` Python library (`pip install PyYAML`)
- SSH access configured from the Ansible control node to the target nodes (using the username/password defined in the config).
- Ansible Vault password (for decrypting sensitive data).

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
2.  **Other Settings:** You can also adjust:
    - `general_config.docker_version`: Specify the desired Docker version.
    - `nodes.<node_name>.docker_node_name`: Assign logical names used within Docker (e.g., for Swarm).
    - `general_config.username`: The user Ansible will connect as (`proot` in the example).
    - `general_config.become_password_vault`: **This holds the Ansible Vault encrypted password** for the connection user (`proot`). See Security section.

**Example `cluster_config.yml` structure:**

```yaml
general_config:
  docker_version: "24.0.5" # Set desired Docker version
  username: proot # User for SSH connection
  become_password_vault: !vault | # Encrypted password (DO NOT EDIT MANUALLY)
    $ANSIBLE_VAULT;1.1;AES256
    # ... (encrypted data) ...

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

You will also need to provide the Ansible Vault password using `--ask-vault-pass` to allow Ansible to decrypt the password stored in `cluster_config.yml`.

**1. Running Playbooks:**

To apply the configuration defined in a playbook (e.g., `playbook.yml`) to a specific environment:

```bash
# Example for 'env1'
ansible-playbook -i env/env1/inventory.config.yml playbook.yml --ask-vault-pass

# Example for 'prod'
ansible-playbook -i env/prod/inventory.config.yml playbook.yml --ask-vault-pass
```

Enter your Vault password when prompted.

**2. Running Ad-hoc Commands:**

To run single commands against hosts in an environment:

```bash
# Example: Ping all hosts in 'env1'
ansible -i env/env1/inventory.config.yml all -m ping --ask-vault-pass

# Example: Check free memory on all hosts in 'prod'
ansible -i env/prod/inventory.config.yml all -m shell -a "free -h" --ask-vault-pass
```

Enter your Vault password when prompted.

**3. Verifying the Dynamic Inventory:**

You can check the inventory that Ansible generates from your `cluster_config.yml` without running any tasks:

```bash
# Show inventory graph for 'env1'
ansible-inventory -i env/env1/inventory.config.yml --graph

# Show detailed inventory list with variables for 'env1'
ansible-inventory -i env/env1/inventory.config.yml --list --ask-vault-pass
```

_(Note: `--list` might require the vault pass if it needs to resolve vaulted variables for display)._

## Security Considerations


- **Ansible Vault:** The user password is **encrypted** using Ansible Vault and stored under the `become_password_vault` key in `cluster_config.yml`.
  - To edit an encrypted file: `ansible-vault edit env/<environment_name>/cluster_config.yml`
  - To encrypt a new password string: `ansible-vault encrypt_string 'your_new_password' --name 'become_password_vault'` (then paste the output into the config file).
- **SSH Host Key Checking:** `ansible.cfg` currently has `host_key_checking = False` for convenience during initial setup. In a production environment, you should set this to `True` and manage SSH known_hosts files properly to prevent man-in-the-middle attacks.
