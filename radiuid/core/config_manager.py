#!/usr/bin/env python3
"""
Configuration Manager Module
Handles XML configuration parsing, loading, saving, and modification
"""

import re
import os
from typing import Dict, List, Any, Optional, Union
from xml.etree import ElementTree

from ..context import AppContext, RadiUIDConfig, FirewallTarget, get_context
from ..logging_config import get_logger
from ..ui.interface import UserInterface
from ..constants import Paths

logger = get_logger('config_manager')


class ConfigManager:
    """
    Manages RadiUID XML configuration files.
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

    def find_config_file(self, preferred: str = None, alternate: str = None) -> str:
        """
        Locate the configuration file.

        Args:
            preferred: Preferred config path (default: /etc/radiuid/radiuid.conf)
            alternate: Alternate path in working directory

        Returns:
            Path to the configuration file

        Raises:
            FileNotFoundError: If no config file is found
        """
        preferred = preferred or Paths.ETC_CONFIG_FILE
        alternate = alternate or os.path.join(os.getcwd(), 'radiuid.conf')

        if os.path.exists(preferred):
            return preferred
        elif os.path.exists(alternate):
            return alternate
        else:
            raise FileNotFoundError(
                f"Configuration file not found in {preferred} or {alternate}"
            )

    def load(self, config_path: str = None, mode: str = 'quiet') -> None:
        """
        Load configuration from XML file.

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
            xml_data = f.read()

        # Extract and preserve the XML comment block
        comment_regex = r"(?s)<!--.*-->"
        comment_match = re.findall(comment_regex, xml_data)
        if comment_match:
            self.context.config_comment = comment_match[0]
            cleaned_xml = xml_data.replace(self.context.config_comment, "")
        else:
            self.context.config_comment = ""
            cleaned_xml = xml_data

        # Parse XML
        self.context.config_root = ElementTree.fromstring(cleaned_xml)
        self.context.config.config_file = config_path

        # Extend schema if needed
        self._extend_config_schema()

        # Publish configuration values
        self._publish_config(mode)

        self.context.mark_initialized()

        if mode == 'noisy':
            logger.info("Configuration loaded successfully")

    def _extend_config_schema(self) -> None:
        """Add missing configuration elements for schema migration."""
        root = self.context.config_root
        if root is None:
            return

        # Find globalsettings element
        globalsettings = root.find('.//globalsettings')
        if globalsettings is None:
            return

        # Add misc element if missing
        if root.find('.//misc') is None:
            misc = ElementTree.SubElement(globalsettings, 'misc')
            looptime = ElementTree.SubElement(misc, 'looptime')
            looptime.text = "10"
            tlsversion = ElementTree.SubElement(misc, 'tlsversion')
            tlsversion.text = "1.2"
            stop_action = ElementTree.SubElement(misc, 'radiusstopaction')
            stop_action.text = "clear"
            logger.debug("Extended config schema: added misc element")

        # Add acctlogcopypath if missing
        if root.find('.//acctlogcopypath') is None:
            paths = globalsettings.find('paths')
            if paths is not None:
                acctlogcopypath = ElementTree.SubElement(paths, 'acctlogcopypath')
                acctlogcopypath.text = None
                logger.debug("Extended config schema: added acctlogcopypath")

    def _publish_config(self, mode: str = 'quiet') -> None:
        """
        Extract values from XML and populate the context config.

        Args:
            mode: 'noisy' for verbose logging
        """
        config_dict = self.tinyxmltodict(self.context.config_root)
        if 'config' not in config_dict:
            logger.warning("Invalid configuration: missing root 'config' element")
            return

        config_data = config_dict['config']
        cfg = self.context.config

        # Extract global settings
        try:
            gs = config_data.get('globalsettings', {})

            # Paths
            paths = gs.get('paths', {})
            cfg.log_file = paths.get('logfile', cfg.log_file)
            cfg.radius_log_path = paths.get('radiuslogpath', cfg.radius_log_path)
            acct_copy = paths.get('acctlogcopypath')
            cfg.acct_log_copy_path = acct_copy if acct_copy else None
            xml_output = paths.get('xmloutputpath')
            cfg.xml_output_path = xml_output if xml_output else None

            # Logging
            logging_cfg = gs.get('logging', {})
            max_lines = logging_cfg.get('maxloglines', str(cfg.max_log_lines))
            cfg.max_log_lines = int(max_lines) if max_lines else 10000

            # UID Settings
            uid_settings = gs.get('uidsettings', {})
            domain = uid_settings.get('userdomain')
            cfg.user_domain = domain if domain and domain.lower() != 'none' else None
            cfg.timeout = int(uid_settings.get('timeout', cfg.timeout))

            # Misc
            misc = gs.get('misc', {})
            cfg.loop_time = int(misc.get('looptime', cfg.loop_time))
            cfg.tls_version = misc.get('tlsversion', cfg.tls_version)
            cfg.radius_stop_action = misc.get('radiusstopaction', cfg.radius_stop_action)

            # Search Terms
            search_terms = gs.get('searchterms', {})
            cfg.ip_address_term = search_terms.get('ipaddressterm', cfg.ip_address_term)
            cfg.username_term = search_terms.get('usernameterm', cfg.username_term)
            cfg.delineator_term = search_terms.get('delineatorterm', cfg.delineator_term)

            # Munge configuration
            munge = gs.get('munge')
            if munge:
                cfg.munge_config = munge
                cfg.to_munge = True
            else:
                cfg.munge_config = None
                cfg.to_munge = False

            # Live log settings (for NPS/continuously written logs)
            livelog = gs.get('livelog', {})
            live_file = livelog.get('file')
            cfg.live_log_file = live_file if live_file else None
            live_tracker = livelog.get('tracker')
            cfg.live_log_tracker = live_tracker if live_tracker else None
            live_enabled = livelog.get('enabled', 'false')
            cfg.live_log_enabled = live_enabled.lower() in ('true', '1', 'yes', 'on')

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
            targets_data = config_data.get('targets', {}).get('target', [])
            if targets_data:
                # Ensure it's a list
                if not isinstance(targets_data, list):
                    targets_data = [targets_data]

                self.context.targets.clear()
                for target_dict in targets_data:
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

        if self.context.config_root is None:
            raise ValueError("No configuration loaded")

        # Combine comment and XML
        formatted_xml = self.formatxml(
            ElementTree.tostring(self.context.config_root, encoding='unicode')
        )
        new_config = self.context.config_comment + "\n" + formatted_xml

        with open(self.context.config.config_file, 'w') as f:
            f.write(new_config)

        logger.info(f"Configuration saved to {self.context.config.config_file}")

    def get_config_item(self, element_name: str) -> Optional[str]:
        """
        Get a single configuration element value.

        Args:
            element_name: Name of the XML element

        Returns:
            Element text value or None
        """
        if self.context.config_root is None:
            return None

        for value in self.context.config_root.iter(element_name):
            return str(value.text) if value.text else None
        return None

    def set_config_item(self, element_name: str, new_value: str) -> None:
        """
        Set a configuration element value.

        Args:
            element_name: Name of the XML element
            new_value: New text value
        """
        if self.context.config_root is None:
            raise ValueError("No configuration loaded")

        for element in self.context.config_root.iter(element_name):
            element.text = new_value
            return

        # Element not found - create it in the appropriate location
        self._create_config_element(element_name, new_value)

    def _create_config_element(self, element_name: str, value: str) -> None:
        """
        Create a new configuration element in the appropriate section.

        Args:
            element_name: Name of the element to create
            value: Value for the new element
        """
        root = self.context.config_root
        if root is None:
            return

        # Map element names to their parent paths
        path_elements = {
            'logfile': './/globalsettings/paths',
            'radiuslogpath': './/globalsettings/paths',
            'acctlogcopypath': './/globalsettings/paths',
            'xmloutputpath': './/globalsettings/paths',
            'maxloglines': './/globalsettings/logging',
            'userdomain': './/globalsettings/uidsettings',
            'timeout': './/globalsettings/uidsettings',
            'looptime': './/globalsettings/misc',
            'tlsversion': './/globalsettings/misc',
            'radiusstopaction': './/globalsettings/misc',
            'ipaddressterm': './/globalsettings/searchterms',
            'usernameterm': './/globalsettings/searchterms',
            'delineatorterm': './/globalsettings/searchterms',
        }

        parent_path = path_elements.get(element_name)
        if parent_path:
            parent = root.find(parent_path)
            if parent is not None:
                new_elem = ElementTree.SubElement(parent, element_name)
                new_elem.text = value
                logger.info(f"Created new configuration element: {element_name}")
                return

        logger.warning(f"Could not create element '{element_name}' - parent path not found")

    def change_config_item(self, section: str, element_name: str, new_value: str) -> None:
        """
        Set or create a configuration element within a section.

        Args:
            section: Parent section name (e.g., 'livelog', 'paths')
            element_name: Name of the element to set
            new_value: New value for the element
        """
        if self.context.config_root is None:
            raise ValueError("No configuration loaded")

        root = self.context.config_root

        # Map section names to their parent paths
        section_paths = {
            'paths': './/globalsettings/paths',
            'logging': './/globalsettings/logging',
            'uidsettings': './/globalsettings/uidsettings',
            'misc': './/globalsettings/misc',
            'searchterms': './/globalsettings/searchterms',
            'livelog': './/globalsettings/livelog',
        }

        parent_path = section_paths.get(section)
        if not parent_path:
            logger.warning(f"Unknown section '{section}'")
            return

        # Find or create the parent section
        parent = root.find(parent_path)
        if parent is None:
            # Need to create the section
            globalsettings = root.find('.//globalsettings')
            if globalsettings is None:
                logger.warning("No globalsettings section found in config")
                return
            parent = ElementTree.SubElement(globalsettings, section)
            logger.info(f"Created new section: {section}")

        # Find or create the element
        element = parent.find(element_name)
        if element is None:
            element = ElementTree.SubElement(parent, element_name)
            logger.info(f"Created new element: {section}/{element_name}")

        element.text = new_value
        logger.info(f"Set {section}/{element_name} = {new_value}")

    def show_config_item(self, output_format: str, mode: str, element_name: str) -> None:
        """
        Display a configuration element.

        Args:
            output_format: 'xml' for XML format, 'text' for plain text
            mode: Display mode (unused, for compatibility)
            element_name: Name of the XML element to display
        """
        if self.context.config_root is None:
            print("No configuration loaded")
            return

        # Handle special cases for complex elements
        if element_name == 'targets':
            targets_elem = self.context.config_root.find('.//targets')
            if targets_elem is not None:
                xml_str = ElementTree.tostring(targets_elem, encoding='unicode')
                print(self._format_xml(xml_str))
            return

        if element_name == 'munge':
            munge_elem = self.context.config_root.find('.//munge')
            if munge_elem is not None:
                xml_str = ElementTree.tostring(munge_elem, encoding='unicode')
                print(self._format_xml(xml_str))
            return

        # Simple elements
        for element in self.context.config_root.iter(element_name):
            if output_format == 'xml':
                xml_str = ElementTree.tostring(element, encoding='unicode')
                print(self._format_xml(xml_str))
            else:
                print(f"{element_name}: {element.text}")
            return

        print(f"Element '{element_name}' not found in configuration")

    def _format_xml(self, xml_string: str) -> str:
        """Format XML string with proper indentation."""
        import re
        # Simple XML formatting
        result = xml_string
        result = re.sub(r'>\s*<', '>\n<', result)
        return result

    def add_target(self, target_data: Dict[str, str]) -> Dict[str, Any]:
        """
        Add or update a firewall target in the configuration.

        Args:
            target_data: Dictionary with target parameters

        Returns:
            Result dictionary with status and messages
        """
        result = {'status': 'processing', 'messages': []}
        root = self.context.config_root

        if root is None:
            result['status'] = 'error'
            result['messages'].append('No configuration loaded')
            return result

        hostname = target_data.get('hostname')
        vsys = target_data.get('vsys', '1')

        if not hostname:
            result['status'] = 'error'
            result['messages'].append('hostname is required')
            return result

        # Find or create targets element
        targets_elem = root.find('.//targets')
        if targets_elem is None:
            targets_elem = ElementTree.SubElement(root, 'targets')

        # Check if target already exists
        existing_target = None
        for target in root.findall('.//target'):
            host_elem = target.find('hostname')
            vsys_elem = target.find('vsys')
            if (host_elem is not None and host_elem.text == hostname and
                vsys_elem is not None and vsys_elem.text == vsys):
                existing_target = target
                break

        if existing_target is not None:
            # Update existing target
            result['messages'].append(f'Updating existing target {hostname}:vsys{vsys}')
            for param, value in target_data.items():
                if param not in ('hostname', 'vsys'):
                    param_elem = existing_target.find(param)
                    if param_elem is not None:
                        param_elem.text = value
                    else:
                        new_elem = ElementTree.SubElement(existing_target, param)
                        new_elem.text = value
                    result['messages'].append(f'Set {param} = {value}')
        else:
            # Create new target
            target = ElementTree.SubElement(targets_elem, 'target')
            result['messages'].append(f'Created new target {hostname}:vsys{vsys}')

            # Add hostname and vsys first
            hostname_elem = ElementTree.SubElement(target, 'hostname')
            hostname_elem.text = hostname
            vsys_elem = ElementTree.SubElement(target, 'vsys')
            vsys_elem.text = vsys

            # Add other parameters
            for param, value in target_data.items():
                if param not in ('hostname', 'vsys'):
                    param_elem = ElementTree.SubElement(target, param)
                    param_elem.text = value
                    result['messages'].append(f'Set {param} = {value}')

        # Update context targets
        fw_target = FirewallTarget.from_dict(target_data)
        self.context.add_target(fw_target)

        self._format_targets_xml()
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
        root = self.context.config_root

        if root is None:
            result['messages'].append('No configuration loaded')
            return result

        targets_elem = root.find('.//targets')
        if targets_elem is None:
            result['messages'].append('No targets exist')
            return result

        for target in root.findall('.//target'):
            host_elem = target.find('hostname')
            vsys_elem = target.find('vsys')
            if (host_elem is not None and host_elem.text == hostname and
                vsys_elem is not None and vsys_elem.text == vsys):
                targets_elem.remove(target)
                self.context.remove_target(hostname, vsys)
                result['status'] = 'success'
                result['messages'].append(f'Removed target {hostname}:vsys{vsys}')

                # If no targets remain, remove the targets element
                if len(list(targets_elem)) == 0:
                    root.remove(targets_elem)

                return result

        result['messages'].append(f'Target {hostname}:vsys{vsys} not found')
        return result

    def clear_all_targets(self) -> None:
        """Remove all targets from configuration."""
        root = self.context.config_root
        if root is None:
            return

        targets_elem = root.find('.//targets')
        if targets_elem is not None:
            root.remove(targets_elem)

        # Update globalsettings tail
        gs = root.find('.//globalsettings')
        if gs is not None:
            gs.tail = '\n'

        self.context.clear_targets()

    def _format_targets_xml(self) -> None:
        """Format XML indentation for targets."""
        root = self.context.config_root
        if root is None:
            return

        gs = root.find('.//globalsettings')
        if gs is not None:
            gs.tail = "\n\t"

        targets = root.find('.//targets')
        if targets is None:
            return

        targets.text = "\n\t\t"
        targets.tail = "\n"

        target_list = list(targets)
        for i, target in enumerate(target_list):
            target.text = "\n\t\t\t"
            params = list(target)
            for j, param in enumerate(params):
                if j == len(params) - 1:
                    param.tail = "\n\t\t"
                else:
                    param.tail = "\n\t\t\t"

            if i == len(target_list) - 1:
                target.tail = "\n\t"
            else:
                target.tail = "\n\t\t"

    # ============================================================
    # XML Conversion Utilities
    # ============================================================

    def tinyxmltodict(self, input_data: Union[str, ElementTree.Element]) -> Dict[str, Any]:
        """
        Convert XML to nested dictionary.

        Args:
            input_data: XML string, file path, or ElementTree Element

        Returns:
            Dictionary representation of the XML
        """
        if isinstance(input_data, str):
            if "<" not in input_data:
                # Assume it's a file path
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

    def _xmltodict_recurse(self, node: ElementTree.Element) -> Any:
        """Recursive helper for XML to dict conversion."""
        attribute_key = "attributes"

        if len(list(node)) == 0 and len(node.items()) == 0:
            return node.text

        result = {}

        # Handle attributes
        if len(node.items()) > 0:
            result[attribute_key] = dict(node.items())

        # Handle children
        for child in node:
            child_value = self._xmltodict_recurse(child)
            if child.tag not in result:
                result[child.tag] = child_value
            else:
                # Convert to list if multiple same-named children
                if not isinstance(result[child.tag], list):
                    result[child.tag] = [result[child.tag]]
                result[child.tag].append(child_value)

        return result

    def tinydicttoxml(self, dict_data: Dict[str, Any]) -> str:
        """
        Convert dictionary back to XML string.

        Args:
            dict_data: Dictionary to convert

        Returns:
            XML string
        """
        if not isinstance(dict_data, dict) or len(dict_data) > 1:
            dict_data = {"root": dict_data}

        root_tag = list(dict_data.keys())[0]
        xml_root = ElementTree.Element(root_tag)
        self._dicttoxml_recurse(xml_root, dict_data[root_tag])
        return ElementTree.tostring(xml_root, encoding='unicode')

    def _dicttoxml_recurse(self, node: ElementTree.Element, dict_data: Dict[str, Any]) -> None:
        """Recursive helper for dict to XML conversion."""
        attribute_key = "attributes"

        if not isinstance(dict_data, dict):
            return

        for key, value in dict_data.items():
            if key == attribute_key:
                for attr_name, attr_value in value.items():
                    node.set(attr_name, attr_value)
            elif value is None:
                ElementTree.SubElement(node, key)
            elif isinstance(value, str):
                new_node = ElementTree.SubElement(node, key)
                new_node.text = value
            elif isinstance(value, dict):
                new_node = ElementTree.SubElement(node, key)
                self._dicttoxml_recurse(new_node, value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        new_node = ElementTree.SubElement(node, key)
                        self._dicttoxml_recurse(new_node, item)
                    else:
                        new_node = ElementTree.SubElement(node, key)
                        new_node.text = str(item)

    def formatxml(self, xml_data: str) -> str:
        """
        Format XML with proper indentation.

        Args:
            xml_data: XML string to format

        Returns:
            Formatted XML string
        """
        root = ElementTree.fromstring(xml_data)
        self._format_element(root, level=0)
        return ElementTree.tostring(root, encoding='unicode')

    def _format_element(self, elem: ElementTree.Element, level: int) -> None:
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
        root = self.context.config_root

        if root is None:
            result['status'] = 'error'
            result['messages'].append('No configuration loaded')
            return result

        # Find globalsettings
        globalsettings = root.find('.//globalsettings')
        if globalsettings is None:
            result['status'] = 'error'
            result['messages'].append('No globalsettings element found')
            return result

        # Get current munge config
        munge_elem = root.find('.//munge')
        if munge_elem is None:
            if 'clear' in munge_input:
                current_config = {'munge': {}}
            else:
                result['messages'].append('No munge config found. Creating new')
                current_config = {'munge': munge_input}
        else:
            result['messages'].append('Existing munge config found. Editing')
            current_config = self.tinyxmltodict(munge_elem)
            globalsettings.remove(munge_elem)

        # Handle empty input (clear all)
        if munge_input == {}:
            result['messages'].append('Terminating before XML rebuild to remove all munge config')
            self.context.config.munge_config = None
            self.context.config.to_munge = False
            result['status'] = 'OK'
            return result

        # Handle clear operations
        if 'clear' in munge_input:
            clear_target = munge_input['clear']
            if isinstance(clear_target, str):
                # Clear entire rule
                if clear_target in current_config.get('munge', {}):
                    del current_config['munge'][clear_target]
                    result['messages'].append(f'Removed rule {clear_target}')
                else:
                    result['messages'].append(f'Rule {clear_target} not found')
            elif isinstance(clear_target, dict):
                # Clear specific step
                rule_name = list(clear_target.keys())[0]
                step_name = clear_target[rule_name]
                if rule_name in current_config.get('munge', {}):
                    if step_name in current_config['munge'][rule_name]:
                        del current_config['munge'][rule_name][step_name]
                        result['messages'].append(f'Removed step {step_name} from rule {rule_name}')
        else:
            # Update/add rules
            for rule_name, rule_data in munge_input.items():
                if rule_name in current_config.get('munge', {}):
                    result['messages'].append(f'Updating rule {rule_name}')
                    current_config['munge'][rule_name].update(rule_data)
                else:
                    result['messages'].append(f'Creating rule {rule_name}')
                    if 'munge' not in current_config:
                        current_config['munge'] = {}
                    current_config['munge'].update({rule_name: rule_data})

        # Rebuild XML if there are rules
        if current_config.get('munge'):
            self._rebuild_munge_xml(globalsettings, current_config['munge'])
            self.context.config.munge_config = current_config['munge']
            self.context.config.to_munge = True
        else:
            self.context.config.munge_config = None
            self.context.config.to_munge = False

        result['status'] = 'OK'
        return result

    def _rebuild_munge_xml(self, parent: ElementTree.Element, munge_config: Dict[str, Any]) -> None:
        """Rebuild munge XML from config dictionary."""
        munge = ElementTree.SubElement(parent, 'munge')

        # Sort rules by numeric value
        rule_names = sorted(
            [k for k in munge_config.keys() if k.startswith('rule')],
            key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 0
        )

        for rule_name in rule_names:
            rule_data = munge_config[rule_name]
            rule = ElementTree.SubElement(munge, rule_name)

            # Add match statement
            match = ElementTree.SubElement(rule, 'match')
            match_data = rule_data.get('match', {})
            if 'any' in match_data:
                ElementTree.SubElement(match, 'any')
            else:
                if 'regex' in match_data:
                    regex_elem = ElementTree.SubElement(match, 'regex')
                    regex_elem.text = match_data['regex']
                if 'criterion' in match_data:
                    criterion_elem = ElementTree.SubElement(match, 'criterion')
                    criterion_elem.text = match_data['criterion']

            # Add steps (sorted)
            step_names = sorted(
                [k for k in rule_data.keys() if k.startswith('step')],
                key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 0
            )

            for step_name in step_names:
                step_data = rule_data[step_name]
                step = ElementTree.SubElement(rule, step_name)

                for action, value in step_data.items():
                    if action == 'assemble' and isinstance(value, dict):
                        assemble = ElementTree.SubElement(step, action)
                        for var_name, var_value in value.items():
                            var_elem = ElementTree.SubElement(assemble, var_name)
                            var_elem.text = var_value
                    elif action == 'from-match' and isinstance(value, dict):
                        from_match = ElementTree.SubElement(step, action)
                        ElementTree.SubElement(from_match, 'any')
                    else:
                        action_elem = ElementTree.SubElement(step, action)
                        if value is not None:
                            action_elem.text = str(value)

    def show_munge_as_set_commands(self) -> List[str]:
        """
        Convert munge configuration to CLI set commands.

        Returns:
            List of CLI command strings
        """
        result = []
        root = self.context.config_root

        if root is None:
            return result

        globalsettings = root.find('.//globalsettings')
        if globalsettings is None:
            return result

        munge = globalsettings.find('munge')
        if munge is None:
            return result

        for rule in list(munge):
            rule_num = rule.tag.replace('rule', '')

            for step in rule:
                if step.tag == 'match':
                    children = list(step)
                    if children and children[0].tag == 'any':
                        result.append(f"set munge {rule_num}.0 match any")
                    else:
                        regex_elem = step.find('regex')
                        criterion_elem = step.find('criterion')
                        if regex_elem is not None and criterion_elem is not None:
                            regex = regex_elem.text or ''
                            # Escape backslashes for display
                            regex = regex.replace('\\', '\\\\')
                            criterion = criterion_elem.text or ''
                            result.append(f'set munge {rule_num}.0 match "{regex}" {criterion}')
                else:
                    step_num = step.tag.replace('step', '')
                    children = list(step)

                    for child in children:
                        if child.tag in ('accept', 'discard'):
                            result.append(f'set munge {rule_num}.{step_num} {child.tag}')
                        elif child.tag == 'assemble':
                            var_dict = {}
                            for var in list(child):
                                var_dict[var.tag] = var.text
                            var_str = ' '.join(var_dict.values())
                            result.append(f'set munge {rule_num}.{step_num} assemble {var_str}')
                        elif child.tag == 'set-variable':
                            var_name = child.text
                            # Look for source
                            from_match = step.find('from-match')
                            from_string = step.find('from-string')
                            if from_match is not None:
                                if list(from_match):
                                    result.append(f'set munge {rule_num}.{step_num} set-variable {var_name} from-match any')
                                else:
                                    source = from_match.text or ''
                                    source = source.replace('\\', '\\\\')
                                    result.append(f'set munge {rule_num}.{step_num} set-variable {var_name} from-match "{source}"')
                            elif from_string is not None:
                                source = from_string.text or ''
                                result.append(f'set munge {rule_num}.{step_num} set-variable {var_name} from-string "{source}"')

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

        lines.append(f"####################################################")
        lines.append(f"#### Set Commands to configure RadiUID ####")
        lines.append(f"####################################################")
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
