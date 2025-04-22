# inventory_plugins/custom_cluster_inventory.py
import os
import yaml

from ansible.errors import AnsibleError, AnsibleParserError
from ansible.plugins.inventory import BaseInventoryPlugin
from ansible.utils.display import Display

DOCUMENTATION = r"""
    name: custom_cluster_inventory
    plugin_type: inventory
    short_description: Generates inventory from a cluster_config.yml file
    description:
        - Reads a specific cluster_config.yml file based on the inventory source path.
        - Creates hosts based on the 'nodes' section.
        - Assigns variables from 'general_config' and node-specific details.
    options:
      config_file:
          description: Path to the cluster configuration YAML file.
          required: True
          env:
            - name: CUSTOM_CLUSTER_CONFIG_FILE
"""

display = Display()


class InventoryModule(BaseInventoryPlugin):
    NAME = "custom_cluster_inventory"  # Used in inventory.config.yml

    def verify_file(self, path):
        """Return true/false if this is possibly a valid file for this plugin to consume"""
        valid = False
        if super(InventoryModule, self).verify_file(path):
            # Ensures the file ends with '.config.yml' or similar trigger
            if path.endswith((".config.yml", ".config.yaml")):
                valid = True
        return valid

    def parse(self, inventory, loader, path, cache=True):
        """Loads and parses the cluster_config.yml file"""
        super(InventoryModule, self).parse(inventory, loader, path, cache)

        # Read the plugin configuration file (e.g., env/prod/inventory.config.yml)
        self._read_config_data(path)

        try:
            config_file_path_rel = self.get_option("config_file")
            if not config_file_path_rel:
                raise AnsibleParserError("...")  # Keep error handling

            inventory_dir = os.path.dirname(path)
            config_file_path_abs = os.path.join(inventory_dir, config_file_path_rel)

            display.v(f"Custom Inventory: Reading config from: {config_file_path_abs}")

            # --- Use Ansible's loader to read the cluster config file ---
            # This loader is Vault-aware
            try:
                data = loader.load_from_file(config_file_path_abs, cache=False)
            except Exception as e:
                raise AnsibleParserError(
                    f"Failed to load cluster config file {config_file_path_abs} using Ansible loader: {e}"
                )
            # --- End of change ---
            if not data:
                raise AnsibleParserError(
                    f"Cluster config file is empty or invalid: {config_file_path_abs}"
                )

            # --- Process Data and Populate Inventory ---

            general_config = data.get("general_config", {})
            nodes = data.get("nodes", {})

            # Extract common variables (handle potential missing keys)
            ansible_user = general_config.get("username")
            # ansible_password = general_config.get("password")  # Insecure!
            become_password_vault = general_config.get("become_password_vault")
            docker_version = general_config.get("docker_version")

            # Get the environment name from the directory structure (e.g., 'prod')
            env_name = os.path.basename(inventory_dir)
            self.inventory.add_group(env_name)  # Create a group named after the env

            # Process each node
            for node_logical_name, node_data in nodes.items():
                try:
                    ip_address = node_data.get("docker_node_ip")
                    docker_node_name = node_data.get("docker_node_name")

                    if not ip_address:
                        display.warning(
                            f"Skipping node '{node_logical_name}' due to missing "
                            "'docker_node_ip'."
                        )
                        continue

                    # Add the host to the inventory using its logical name
                    self.inventory.add_host(host=node_logical_name, group=env_name)

                    # Set host variables
                    self.inventory.set_variable(
                        node_logical_name, "ansible_host", ip_address
                    )

                    # *** Explicitly set the Python interpreter ***
                    # Use the known path for AL2023 or 'auto'/'auto_silent'
                    self.inventory.set_variable(
                        node_logical_name,
                        "ansible_python_interpreter",
                        "/usr/bin/python3.9",  # Be explicit
                        # OR use 'auto_silent' to let Ansible choose but hide warnings
                        # "auto_silent"
                    )

                    if ansible_user:
                        self.inventory.set_variable(
                            node_logical_name, "ansible_user", ansible_user
                        )
                    # Logic for hardcoded password
                    # if ansible_password:
                    #     # WARNING: Setting password directly is insecure. Use Vault.
                    #     self.inventory.set_variable(
                    #         node_logical_name,
                    #         "ansible_password",
                    #         ansible_password,
                    #     )
                    #     # Tell Ansible to use the same password for sudo (become)
                    #     self.inventory.set_variable(
                    #         node_logical_name,
                    #         "ansible_become_pass",
                    #         ansible_password,
                    #     )
                    #########################################
                    # Logic for ansible vault password
                    if become_password_vault:
                        # Set both login and become password from the vault variable
                        self.inventory.set_variable(
                            node_logical_name,
                            "ansible_password",
                            become_password_vault,
                        )
                        self.inventory.set_variable(
                            node_logical_name,
                            "ansible_become_pass",
                            become_password_vault,
                        )
                    if docker_version:
                        self.inventory.set_variable(
                            node_logical_name, "docker_version", docker_version
                        )
                    if docker_node_name:
                        self.inventory.set_variable(
                            node_logical_name,
                            "docker_node_name",
                            docker_node_name,
                        )

                    # Add any other node-specific vars if needed
                    # for key, value in node_data.items():
                    #    if key not in ['docker_node_ip', 'docker_node_name']:
                    #        self.inventory.set_variable(node_logical_name, key, value)

                except Exception as e:
                    display.warning(
                        f"Could not process node '{node_logical_name}': {e}"
                    )

        except Exception as e:
            raise AnsibleParserError(f"Failed to parse inventory plugin config: {e}")
