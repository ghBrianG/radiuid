#!/usr/bin/env python3
"""
Configuration Manager Module
Handles YAML configuration parsing, loading, saving, and modification.
Includes migration support for legacy XML configuration files.
"""

import os
import re
from typing import Dict, List, Any, Optional

import yaml

from ..constants import Paths
from ..context import AppContext, FirewallTarget, get_context
from ..logging_config import get_logger
from ..ui.interface import UserInterface

logger = get_logger('config_manager')

# Default configuration template
DEFAULT_CONFIG = {
    'paths': {
        'radius_log_path': '/var/log/radius/radacct/',
        'log_file': '/etc/radiuid/radiuid.log',
        'acct_log_copy_path': None,
    },
    'logging': {
        'max_log_lines': 0,
    },
    'uid_settings': {
        'user_domain': 'domain.com',
        'timeout': 60,
    },
    'search_terms': {
        'ip_address_term': 'Framed-IP-Address',
        'username_term': 'User-Name',
        'delineator_term': '[PARAGRAPH]',
    },
    'misc': {
        'loop_time': 10,
        'tls_version': '1.2',
        'radius_stop_action': 'clear',
        'max_uids_per_call': 50,
    },
    'livelog': {
        'enabled': False,
        'file': None,
        'tracker': '/var/lib/radiuid/livelog_tracker',
    },
    'nps': {
        'ip_column': 0,
        'username_column': 1,
        'packet_type_column': 6,
    },
    'munge': {},
    'targets': {},
}


class ConfigManager:
    """
    Manages RadiUID YAML configuration files.
    Handles loading, parsing, modifying, and saving configuration.
    """

    def __init__(self, context: Optional[AppContext] = None, ui: Optional[UserInterface] = None):
        """
        Initialize ConfigManager.

        Args:
            context: Application context (uses singleton if not provided)
            ui: User interface for output (creates new instance if not provided)
        """
        self.context = context or get_context()
        self.ui = ui or UserInterface()
        self._config_data: Dict[str, Any] = {}

    @staticmethod
    def find_config_file(preferred: str = None, alternate: str = None) -> str:
        """
        Locate the configuration file.

        Searches in order:
        1. Preferred path (default: /etc/radiuid/radiuid.yaml)
        2. Legacy preferred path (.conf extension)
        3. Alternate path in working directory (.yaml)
        4. Legacy alternate path (.conf)

        Args:
            preferred: Preferred config path (default: /etc/radiuid/radiuid.yaml)
            alternate: Alternate path in working directory

        Returns:
            Path to the configuration file

        Raises:
            FileNotFoundError: If no config file is found
        """
        preferred = preferred or Paths.ETC_CONFIG_FILE
        alternate = alternate or os.path.join(os.getcwd(), 'radiuid.yaml')

        # Also check legacy .conf paths
        preferred_legacy = preferred.replace('.yaml', '.conf') if preferred.endswith('.yaml') else None
        alternate_legacy = alternate.replace('.yaml', '.conf') if alternate.endswith('.yaml') else None

        # Check paths in order of preference
        search_paths = [preferred, preferred_legacy, alternate, alternate_legacy]
        for path in search_paths:
            if path and os.path.exists(path):
                return path

        raise FileNotFoundError(
            f"Configuration file not found. Searched: {preferred}, {alternate}"
        )

    def load(self, config_path: str = None, mode: str = 'quiet') -> None:
        """
        Load configuration from YAML file.
        Automatically detects and migrates XML configuration files.

        Args:
            config_path: Path to config file (auto-detects if not provided)
            mode: 'noisy' for verbose output, 'quiet' for silent
        """
        if config_path is None:
            config_path = self.find_config_file()

        if mode == 'noisy':
            logger.info(f"Loading configuration from {config_path}")

        # Read the config file
        with open(config_path, 'r') as f:
            content = f.read()

        # Detect XML format and migrate if needed
        if content.strip().startswith('<') or '<?xml' in content:
            if mode == 'noisy':
                logger.info("Detected legacy XML configuration, migrating to YAML...")
            self._config_data = self._migrate_xml_to_yaml(content)

            # Rename file from .conf to .yaml if needed
            if config_path.endswith('.conf'):
                new_path = config_path[:-5] + '.yaml'  # Replace .conf with .yaml
                try:
                    os.rename(config_path, new_path)
                    logger.info(f"Renamed config file: {config_path} -> {new_path}")
                    config_path = new_path
                except OSError as e:
                    logger.warning(f"Could not rename config file: {e}")

            # Save migrated config
            self.context.config.config_file = config_path
            self.save()
            logger.info(f"Migrated XML configuration to YAML: {config_path}")
        else:
            # Parse YAML
            self._config_data = yaml.safe_load(content) or {}

        self.context.config.config_file = config_path

        # Ensure all sections exist with defaults
        self._extend_config_schema()

        # Publish configuration values to context
        self._publish_config(mode)

        self.context.mark_initialized()

        if mode == 'noisy':
            logger.info("Configuration loaded successfully")

    def _extend_config_schema(self) -> None:
        """Add missing configuration sections with defaults."""
        for key, default_value in DEFAULT_CONFIG.items():
            if key not in self._config_data:
                self._config_data[key] = default_value
                logger.debug(f"Extended config schema: added {key}")
            elif isinstance(default_value, dict):
                # Ensure nested keys exist
                for sub_key, sub_default in default_value.items():
                    if sub_key not in self._config_data[key]:
                        self._config_data[key][sub_key] = sub_default
                        logger.debug(f"Extended config schema: added {key}.{sub_key}")

    def extend_config_schema(self) -> None:
        """Public method to extend config schema (for reinstall compatibility)."""
        self._extend_config_schema()

    def _publish_config(self, mode: str = 'quiet') -> None:
        """
        Extract values from YAML and populate the context config.

        Args:
            mode: 'noisy' for verbose logging
        """
        cfg = self.context.config
        data = self._config_data

        try:
            # Paths
            paths = data.get('paths', {})
            cfg.log_file = paths.get('log_file', cfg.log_file)
            cfg.radius_log_path = paths.get('radius_log_path', cfg.radius_log_path)
            cfg.acct_log_copy_path = paths.get('acct_log_copy_path')
            cfg.xml_output_path = paths.get('xml_output_path')

            # Logging
            logging_cfg = data.get('logging', {})
            cfg.max_log_lines = int(logging_cfg.get('max_log_lines', cfg.max_log_lines))

            # UID Settings
            uid_settings = data.get('uid_settings', {})
            domain = uid_settings.get('user_domain')
            cfg.user_domain = domain if domain and str(domain).lower() != 'none' else None
            cfg.timeout = int(uid_settings.get('timeout', cfg.timeout))

            # Misc
            misc = data.get('misc', {})
            cfg.loop_time = int(misc.get('loop_time', cfg.loop_time))
            cfg.tls_version = str(misc.get('tls_version', cfg.tls_version))
            cfg.radius_stop_action = misc.get('radius_stop_action', cfg.radius_stop_action)
            cfg.max_uids_per_call = int(misc.get('max_uids_per_call', 50))

            # Search Terms
            search_terms = data.get('search_terms', {})
            cfg.ip_address_term = search_terms.get('ip_address_term', cfg.ip_address_term)
            cfg.username_term = search_terms.get('username_term', cfg.username_term)
            cfg.delineator_term = search_terms.get('delineator_term', cfg.delineator_term)

            # Munge configuration
            munge = data.get('munge', {})
            if munge:
                cfg.munge_config = munge
                cfg.to_munge = True
            else:
                cfg.munge_config = None
                cfg.to_munge = False

            # Live log settings
            livelog = data.get('livelog', {})
            cfg.live_log_file = livelog.get('file')
            cfg.live_log_tracker = livelog.get('tracker')
            live_enabled = livelog.get('enabled', False)
            if isinstance(live_enabled, bool):
                cfg.live_log_enabled = live_enabled
            else:
                cfg.live_log_enabled = str(live_enabled).lower() in ('true', '1', 'yes', 'on')

            # NPS CSV parsing settings (column indices are 0-based)
            # Set column to -1 or null to enable auto-detection mode, which uses
            # RADIUS attribute numbers in the CSV to find IP/username fields
            nps = data.get('nps', {})
            ip_col = nps.get('ip_column', 0)
            cfg.nps_ip_column = int(ip_col) if ip_col is not None else -1
            username_col = nps.get('username_column', 1)
            cfg.nps_username_column = int(username_col) if username_col is not None else -1
            pkt_col = nps.get('packet_type_column', 6)
            cfg.nps_packet_type_column = int(pkt_col) if pkt_col is not None else -1

            if mode == 'noisy':
                logger.info(f"Loaded log_file: {cfg.log_file}")
                logger.info(f"Loaded radius_log_path: {cfg.radius_log_path}")
                logger.info(f"Loaded loop_time: {cfg.loop_time}")
                logger.info(f"Loaded tls_version: {cfg.tls_version}")
                if cfg.live_log_enabled:
                    logger.info(f"Live log processing enabled: {cfg.live_log_file}")

        except Exception as e:
            logger.warning(f"Could not import some settings: {e}")

        # Extract targets
        try:
            targets_data = data.get('targets', {})
            if targets_data:
                self.context.targets.clear()
                for target_key, target_dict in targets_data.items():
                    # Parse key format: "hostname:vsys"
                    if ':' in target_key:
                        hostname, vsys = target_key.rsplit(':', 1)
                        target_dict['hostname'] = hostname
                        target_dict['vsys'] = vsys
                    target = FirewallTarget.from_dict(target_dict)
                    self.context.targets.append(target)

                if mode == 'noisy':
                    logger.info(f"Loaded {len(self.context.targets)} firewall targets")
        except Exception as e:
            logger.warning(f"Could not load targets: {e}")

    def save(self) -> None:
        """Save the current configuration to file."""
        if not self.context.config.config_file:
            raise ValueError("No configuration file path set")

        # Update config data from context before saving
        self._sync_config_from_context()

        # Generate YAML with comments
        yaml_content = self._generate_yaml_with_header()

        with open(self.context.config.config_file, 'w') as f:
            f.write(yaml_content)

        logger.info(f"Configuration saved to {self.context.config.config_file}")

    def _sync_config_from_context(self) -> None:
        """Sync configuration data from context before saving."""
        cfg = self.context.config

        # Paths
        self._config_data.setdefault('paths', {})
        self._config_data['paths']['radius_log_path'] = cfg.radius_log_path
        self._config_data['paths']['log_file'] = cfg.log_file
        self._config_data['paths']['acct_log_copy_path'] = cfg.acct_log_copy_path

        # Logging
        self._config_data.setdefault('logging', {})
        self._config_data['logging']['max_log_lines'] = cfg.max_log_lines

        # UID Settings
        self._config_data.setdefault('uid_settings', {})
        self._config_data['uid_settings']['user_domain'] = cfg.user_domain or ''
        self._config_data['uid_settings']['timeout'] = cfg.timeout

        # Misc
        self._config_data.setdefault('misc', {})
        self._config_data['misc']['loop_time'] = cfg.loop_time
        self._config_data['misc']['tls_version'] = cfg.tls_version
        self._config_data['misc']['radius_stop_action'] = cfg.radius_stop_action
        self._config_data['misc']['max_uids_per_call'] = cfg.max_uids_per_call

        # Search Terms
        self._config_data.setdefault('search_terms', {})
        self._config_data['search_terms']['ip_address_term'] = cfg.ip_address_term
        self._config_data['search_terms']['username_term'] = cfg.username_term
        self._config_data['search_terms']['delineator_term'] = cfg.delineator_term

        # Live log
        self._config_data.setdefault('livelog', {})
        self._config_data['livelog']['enabled'] = cfg.live_log_enabled
        self._config_data['livelog']['file'] = cfg.live_log_file
        self._config_data['livelog']['tracker'] = cfg.live_log_tracker

        # NPS CSV settings
        self._config_data.setdefault('nps', {})
        self._config_data['nps']['ip_column'] = cfg.nps_ip_column
        self._config_data['nps']['username_column'] = cfg.nps_username_column
        self._config_data['nps']['packet_type_column'] = cfg.nps_packet_type_column

        # Munge
        self._config_data['munge'] = cfg.munge_config or {}

        # Targets
        targets_dict = {}
        for target in self.context.targets:
            key = f"{target.hostname}:{target.vsys}"
            targets_dict[key] = {
                'hostname': target.hostname,
                'vsys': target.vsys,
                'username': target.username,
                'password': target.password,
                'port': target.port,
            }
        self._config_data['targets'] = targets_dict

    def _generate_yaml_with_header(self) -> str:
        """Generate YAML content with a descriptive header."""
        header = """# ==============================================================================
# RadiUID Configuration File
# ==============================================================================
# https://github.com/ghBrianG/radiuid
# ==============================================================================

"""
        yaml_content = yaml.dump(
            self._config_data,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True
        )
        return header + yaml_content

    def get_config_item(self, element_name: str) -> Optional[str]:
        """
        Get a single configuration element value.

        Args:
            element_name: Name of the config element (supports dot notation)

        Returns:
            Element value or None
        """
        # Map old XML element names to new YAML paths
        name_mapping = {
            'logfile': 'paths.log_file',
            'radiuslogpath': 'paths.radius_log_path',
            'acctlogcopypath': 'paths.acct_log_copy_path',
            'xmloutputpath': 'paths.xml_output_path',
            'maxloglines': 'logging.max_log_lines',
            'userdomain': 'uid_settings.user_domain',
            'timeout': 'uid_settings.timeout',
            'looptime': 'misc.loop_time',
            'tlsversion': 'misc.tls_version',
            'radiusstopaction': 'misc.radius_stop_action',
            'ipaddressterm': 'search_terms.ip_address_term',
            'usernameterm': 'search_terms.username_term',
            'delineatorterm': 'search_terms.delineator_term',
        }

        path = name_mapping.get(element_name, element_name)
        parts = path.split('.')

        value = self._config_data
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return None

        return str(value) if value is not None else None

    def set_config_item(self, element_name: str, new_value: str) -> None:
        """
        Set a configuration element value.

        Args:
            element_name: Name of the config element
            new_value: New value
        """
        # Map old XML element names to new YAML paths
        name_mapping = {
            'logfile': ('paths', 'log_file'),
            'radiuslogpath': ('paths', 'radius_log_path'),
            'acctlogcopypath': ('paths', 'acct_log_copy_path'),
            'xmloutputpath': ('paths', 'xml_output_path'),
            'maxloglines': ('logging', 'max_log_lines'),
            'userdomain': ('uid_settings', 'user_domain'),
            'timeout': ('uid_settings', 'timeout'),
            'looptime': ('misc', 'loop_time'),
            'tlsversion': ('misc', 'tls_version'),
            'radiusstopaction': ('misc', 'radius_stop_action'),
            'ipaddressterm': ('search_terms', 'ip_address_term'),
            'usernameterm': ('search_terms', 'username_term'),
            'delineatorterm': ('search_terms', 'delineator_term'),
        }

        if element_name in name_mapping:
            section, key = name_mapping[element_name]
            self._config_data.setdefault(section, {})[key] = new_value
        else:
            logger.warning(f"Unknown config element: {element_name}")

    def change_config_item(self, section: str, element_name: str, new_value: str) -> None:
        """
        Set or create a configuration element within a section.

        Args:
            section: Parent section name
            element_name: Name of the element to set
            new_value: New value for the element
        """
        self._config_data.setdefault(section, {})[element_name] = new_value
        logger.info(f"Set {section}.{element_name} = {new_value}")

    def show_config_item(self, _output_format: str, _mode: str, element_name: str) -> None:
        """
        Display a configuration element.

        Args:
            _output_format: Reserved for future format options
            _mode: Reserved for future display modes
            element_name: Name of the element to display ('config' for full config)
        """
        # Show full configuration
        if element_name == 'config':
            if not self._config_data:
                # Config not loaded - try loading it
                try:
                    self.load(mode='quiet')
                except FileNotFoundError:
                    print("Configuration file not found")
                    return
            print(yaml.dump(self._config_data, default_flow_style=False, sort_keys=False))
            return

        if element_name == 'targets':
            targets = self._config_data.get('targets', {})
            print(yaml.dump({'targets': targets}, default_flow_style=False))
            return

        if element_name == 'munge':
            munge = self._config_data.get('munge', {})
            print(yaml.dump({'munge': munge}, default_flow_style=False))
            return

        value = self.get_config_item(element_name)
        if value is not None:
            print(f"{element_name}: {value}")
        else:
            print(f"Element '{element_name}' not found in configuration")

    def add_target(self, target_data: Dict[str, str]) -> Dict[str, Any]:
        """
        Add or update a firewall target in the configuration.

        Args:
            target_data: Dictionary with target parameters

        Returns:
            Result dictionary with status and messages
        """
        result = {'status': 'processing', 'messages': []}

        hostname = target_data.get('hostname')
        vsys = target_data.get('vsys', '1')

        if not hostname:
            result['status'] = 'error'
            result['messages'].append('hostname is required')
            return result

        key = f"{hostname}:{vsys}"
        targets = self._config_data.setdefault('targets', {})

        if key in targets:
            result['messages'].append(f'Updating existing target {key}')
            targets[key].update(target_data)
        else:
            result['messages'].append(f'Created new target {key}')
            targets[key] = target_data

        for param, value in target_data.items():
            if param not in ('hostname', 'vsys'):
                result['messages'].append(f'Set {param} = {value}')

        # Update context targets
        fw_target = FirewallTarget.from_dict(target_data)
        self.context.add_target(fw_target)

        result['status'] = 'success'
        return result

    def remove_target(self, hostname: str, vsys: str) -> Dict[str, Any]:
        """
        Remove a target from the configuration.

        Args:
            hostname: Target hostname
            vsys: Virtual system ID

        Returns:
            Result dictionary with status and messages
        """
        result = {'status': 'fail', 'messages': []}

        key = f"{hostname}:{vsys}"
        targets = self._config_data.get('targets', {})

        if key in targets:
            del targets[key]
            self.context.remove_target(hostname, vsys)
            result['status'] = 'success'
            result['messages'].append(f'Removed target {key}')
        else:
            result['messages'].append(f'Target {key} not found')

        return result

    def clear_all_targets(self) -> None:
        """Remove all targets from configuration."""
        self._config_data['targets'] = {}
        self.context.clear_targets()

    # ============================================================
    # Munge Configuration
    # ============================================================

    def get_munge_config(self) -> Optional[Dict[str, Any]]:
        """Get the current munge configuration."""
        return self.context.config.munge_config

    def set_munge_config(self, munge_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create, modify, or delete munge rules.

        Args:
            munge_input: Munge configuration changes

        Returns:
            Result dictionary with status and messages
        """
        result = {'status': 'working', 'messages': []}

        current_config = self._config_data.get('munge', {})

        # Handle empty input (clear all)
        if munge_input == {}:
            result['messages'].append('Clearing all munge config')
            self._config_data['munge'] = {}
            self.context.config.munge_config = None
            self.context.config.to_munge = False
            result['status'] = 'OK'
            return result

        # Handle clear operations
        if 'clear' in munge_input:
            clear_target = munge_input['clear']
            if isinstance(clear_target, str):
                # Clear entire rule
                if clear_target in current_config:
                    del current_config[clear_target]
                    result['messages'].append(f'Removed rule {clear_target}')
                else:
                    result['messages'].append(f'Rule {clear_target} not found')
            elif isinstance(clear_target, dict):
                # Clear specific step
                rule_name = list(clear_target.keys())[0]
                step_name = clear_target[rule_name]
                if rule_name in current_config:
                    if step_name in current_config[rule_name]:
                        del current_config[rule_name][step_name]
                        result['messages'].append(f'Removed step {step_name} from rule {rule_name}')
        else:
            # Update/add rules
            for rule_name, rule_data in munge_input.items():
                if rule_name in current_config:
                    result['messages'].append(f'Updating rule {rule_name}')
                    current_config[rule_name].update(rule_data)
                else:
                    result['messages'].append(f'Creating rule {rule_name}')
                    current_config[rule_name] = rule_data

        self._config_data['munge'] = current_config

        if current_config:
            self.context.config.munge_config = current_config
            self.context.config.to_munge = True
        else:
            self.context.config.munge_config = None
            self.context.config.to_munge = False

        result['status'] = 'OK'
        return result

    def show_munge_as_set_commands(self) -> List[str]:
        """
        Convert munge configuration to CLI set commands.

        Returns:
            List of CLI command strings
        """
        result = []
        munge = self._config_data.get('munge', {})

        for rule_key, rule_data in sorted(munge.items()):
            rule_num = rule_key.replace('rule', '') if rule_key.startswith('rule') else rule_key

            for step_key, step_data in sorted(rule_data.items()):
                if step_key == 'match' or step_key.endswith('.0'):
                    # Handle match statement
                    if isinstance(step_data, dict):
                        if step_data.get('any'):
                            result.append(f"set munge {rule_num}.0 match any")
                        else:
                            regex = step_data.get('pattern', step_data.get('regex', ''))
                            regex = regex.replace('\\', '\\\\')
                            matchtype = step_data.get('matchtype', step_data.get('criterion', ''))
                            result.append(f'set munge {rule_num}.0 match "{regex}" {matchtype}')
                else:
                    step_num = step_key.replace('step', '') if step_key.startswith('step') else step_key

                    if isinstance(step_data, dict):
                        action = step_data.get('action', '')
                        if action in ('accept', 'discard'):
                            result.append(f'set munge {rule_num}.{step_num} {action}')
                        elif action == 'assemble':
                            template = step_data.get('template', '')
                            result.append(f'set munge {rule_num}.{step_num} assemble {template}')
                        elif action == 'set-variable':
                            var_name = step_data.get('variable', '')
                            source_type = 'from-match' if 'pattern' in step_data else 'from-string'
                            source = step_data.get('pattern', step_data.get('value', ''))
                            source = source.replace('\\', '\\\\')
                            result.append(
                                f'set munge {rule_num}.{step_num} set-variable {var_name} {source_type} "{source}"')

        return result

    def show_config_as_set_commands(self, prepend: str = "radiuid") -> str:
        """
        Generate CLI set commands to recreate current configuration.

        Args:
            prepend: Command prefix (radiuid or python radiuid.py)

        Returns:
            Multi-line string of set commands
        """
        cfg = self.context.config
        lines = []

        lines.append("####################################################")
        lines.append("#### Set Commands to configure RadiUID ####")
        lines.append("####################################################")
        lines.append("!")

        # Global settings
        lines.append(f"{prepend} set radiuslogpath {cfg.radius_log_path}")
        lines.append("!")
        lines.append(f"{prepend} set acctlogcopypath {cfg.acct_log_copy_path or 'none'}")
        lines.append("!")
        lines.append(f"{prepend} set xmloutputpath {cfg.xml_output_path or 'none'}")
        lines.append("!")
        lines.append(f"{prepend} set logfile {cfg.log_file}")
        lines.append("!")
        lines.append(f"{prepend} set maxloglines {cfg.max_log_lines}")
        lines.append("!")
        lines.append(f"{prepend} set userdomain {cfg.user_domain or 'none'}")
        lines.append("!")
        lines.append(f"{prepend} set timeout {cfg.timeout}")
        lines.append("!")
        lines.append(f"{prepend} set looptime {cfg.loop_time}")
        lines.append("!")
        lines.append(f"{prepend} set tlsversion {cfg.tls_version}")
        lines.append("!")
        lines.append(f"{prepend} set radiusstopaction {cfg.radius_stop_action}")
        lines.append("!")

        # Targets
        lines.append(f"{prepend} clear target all")
        lines.append("!")
        for target in self.context.targets:
            params = f"username {target.username} password {target.password}"
            if target.port != "443":
                params += f" port {target.port}"
            lines.append(f"{prepend} set target {target.hostname}:vsys{target.vsys} {params}")
            lines.append("!")

        # Munge rules
        if cfg.to_munge:
            lines.append(f"{prepend} clear munge all")
            lines.append("!")
            for cmd in self.show_munge_as_set_commands():
                lines.append(f"{prepend} {cmd}")
                lines.append("!")

        lines.append("!")
        lines.append("####################################################")

        return "\n".join(lines)

    # ============================================================
    # XML Migration Support
    # ============================================================

    def _migrate_xml_to_yaml(self, xml_content: str) -> Dict[str, Any]:
        """
        Migrate XML configuration to YAML format.

        Args:
            xml_content: XML configuration content

        Returns:
            Dictionary representation suitable for YAML
        """
        from xml.etree import ElementTree

        # Remove XML comments
        comment_regex = r"(?s)<!--.*?-->"
        cleaned_xml = re.sub(comment_regex, "", xml_content)

        try:
            root = ElementTree.fromstring(cleaned_xml)
        except ElementTree.ParseError as e:
            logger.error(f"Failed to parse XML configuration: {e}")
            return DEFAULT_CONFIG.copy()

        config = DEFAULT_CONFIG.copy()

        # Extract global settings
        gs = root.find('.//globalsettings')
        if gs is not None:
            # Paths
            paths = gs.find('paths')
            if paths is not None:
                if paths.find('radiuslogpath') is not None:
                    config['paths']['radius_log_path'] = paths.find('radiuslogpath').text or ''
                if paths.find('logfile') is not None:
                    config['paths']['log_file'] = paths.find('logfile').text or ''
                if paths.find('acctlogcopypath') is not None:
                    text = paths.find('acctlogcopypath').text
                    config['paths']['acct_log_copy_path'] = text if text else None

            # Logging
            logging_elem = gs.find('logging')
            if logging_elem is not None:
                if logging_elem.find('maxloglines') is not None:
                    text = logging_elem.find('maxloglines').text
                    config['logging']['max_log_lines'] = str(int(text)) if text else '0'

            # UID Settings
            uid = gs.find('uidsettings')
            if uid is not None:
                if uid.find('userdomain') is not None:
                    config['uid_settings']['user_domain'] = uid.find('userdomain').text or ''
                if uid.find('timeout') is not None:
                    text = uid.find('timeout').text
                    config['uid_settings']['timeout'] = str(int(text)) if text else '60'

            # Search Terms
            st = gs.find('searchterms')
            if st is not None:
                if st.find('ipaddressterm') is not None:
                    config['search_terms']['ip_address_term'] = st.find('ipaddressterm').text or ''
                if st.find('usernameterm') is not None:
                    config['search_terms']['username_term'] = st.find('usernameterm').text or ''
                if st.find('delineatorterm') is not None:
                    config['search_terms']['delineator_term'] = st.find('delineatorterm').text or ''

            # Misc
            misc = gs.find('misc')
            if misc is not None:
                if misc.find('looptime') is not None:
                    text = misc.find('looptime').text
                    config['misc']['loop_time'] = str(int(text)) if text else '10'
                if misc.find('tlsversion') is not None:
                    config['misc']['tls_version'] = misc.find('tlsversion').text or '1.2'
                if misc.find('radiusstopaction') is not None:
                    config['misc']['radius_stop_action'] = misc.find('radiusstopaction').text or 'clear'

            # Live log
            livelog = gs.find('livelog')
            if livelog is not None:
                if livelog.find('enabled') is not None:
                    text = livelog.find('enabled').text or 'false'
                    config['livelog']['enabled'] = 'true' if text.lower() in ('true', '1', 'yes', 'on') else 'false'
                if livelog.find('file') is not None:
                    config['livelog']['file'] = livelog.find('file').text
                if livelog.find('tracker') is not None:
                    config['livelog']['tracker'] = livelog.find('tracker').text

            # Munge (simplified migration - complex rules may need manual adjustment)
            munge_elem = gs.find('munge')
            if munge_elem is not None:
                munge_dict = self._migrate_munge_xml(munge_elem)
                config['munge'] = munge_dict

        # Extract targets
        targets_dict = {}
        for target in root.findall('.//target'):
            hostname_elem = target.find('hostname')
            vsys_elem = target.find('vsys')
            username_elem = target.find('username')
            password_elem = target.find('password')
            port_elem = target.find('port')

            if hostname_elem is not None:
                hostname = hostname_elem.text or ''
                vsys = vsys_elem.text if vsys_elem is not None else '1'
                key = f"{hostname}:{vsys}"

                targets_dict[key] = {
                    'hostname': hostname,
                    'vsys': vsys,
                    'username': username_elem.text if username_elem is not None else '',
                    'password': password_elem.text if password_elem is not None else '',
                    'port': port_elem.text if port_elem is not None else '443',
                }

        config['targets'] = targets_dict

        return config

    @staticmethod
    def _migrate_munge_xml(munge_elem) -> Dict[str, Any]:
        """Migrate munge XML element to dictionary."""
        munge_dict = {}

        for rule in list(munge_elem):
            rule_name = rule.tag
            rule_dict = {}

            for elem in list(rule):
                if elem.tag == 'match':
                    match_dict = {}
                    any_elem = elem.find('any')
                    if any_elem is not None:
                        match_dict['any'] = True
                    else:
                        regex_elem = elem.find('regex')
                        criterion_elem = elem.find('criterion')
                        if regex_elem is not None:
                            match_dict['pattern'] = regex_elem.text or ''
                        if criterion_elem is not None:
                            match_dict['matchtype'] = criterion_elem.text or ''
                    rule_dict['match'] = match_dict
                else:
                    # Step elements
                    step_dict = {}
                    for child in list(elem):
                        if child.tag in ('accept', 'discard'):
                            step_dict['action'] = child.tag
                        elif child.tag == 'set-variable':
                            step_dict['action'] = 'set-variable'
                            step_dict['variable'] = child.text or ''
                        elif child.tag == 'from-match':
                            if list(child):  # has children (like <any>)
                                step_dict['pattern'] = 'any'
                            else:
                                step_dict['pattern'] = child.text or ''
                        elif child.tag == 'from-string':
                            step_dict['value'] = child.text or ''
                        elif child.tag == 'assemble':
                            step_dict['action'] = 'assemble'
                            parts = []
                            for var in list(child):
                                parts.append(var.text or '')
                            step_dict['template'] = ' '.join(parts)
                    rule_dict[elem.tag] = step_dict

            munge_dict[rule_name] = rule_dict

        return munge_dict

    # ============================================================
    # Legacy Compatibility Methods
    # ============================================================

    def tinyxmltodict(self, input_data) -> Dict[str, Any]:
        """
        Legacy method for XML to dict conversion.
        Kept for backward compatibility with other modules.
        """
        from xml.etree import ElementTree

        if isinstance(input_data, str):
            if "<" not in input_data:
                with open(input_data, 'r') as f:
                    xml_data = f.read()
                root = ElementTree.fromstring(xml_data)
            else:
                root = ElementTree.fromstring(input_data)
        elif isinstance(input_data, ElementTree.Element):
            root = input_data
        else:
            xml_str = ElementTree.tostring(input_data, encoding='unicode')
            root = ElementTree.fromstring(xml_str)

        return {root.tag: self._xmltodict_recurse(root)}

    def _xmltodict_recurse(self, node) -> Any:
        """Recursive helper for XML to dict conversion."""

        if len(list(node)) == 0 and len(node.items()) == 0:
            return node.text

        result = {}

        if len(node.items()) > 0:
            result['attributes'] = dict(node.items())

        for child in node:
            child_value = self._xmltodict_recurse(child)
            if child.tag not in result:
                result[child.tag] = child_value
            else:
                if not isinstance(result[child.tag], list):
                    result[child.tag] = [result[child.tag]]
                result[child.tag].append(child_value)

        return result

    def formatxml(self, xml_data: str) -> str:
        """Legacy method for XML formatting."""
        from xml.etree import ElementTree
        root = ElementTree.fromstring(xml_data)
        self._format_element(root, level=0)
        return ElementTree.tostring(root, encoding='unicode')

    def _format_element(self, elem, level: int) -> None:
        """Recursively format XML element with indentation."""
        indent = "\t"
        i = "\n" + level * indent

        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + indent
            for j, child in enumerate(elem):
                self._format_element(child, level + 1)
                if j < len(elem) - 1:
                    child.tail = i + indent
                else:
                    child.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i
