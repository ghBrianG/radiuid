#!/usr/bin/env python3
"""
File Manager Module
Handles file operations, path validation, logging, and FreeRADIUS client configuration
"""

import os
import re
import shutil
import time
from typing import Dict, List, Any, Optional, Tuple

from ..context import AppContext, get_context
from ..logging_config import get_logger
from ..ui.interface import UserInterface

logger = get_logger('file_manager')


class FileManager:
    """
    Manages file operations, validation, and logging for RadiUID.
    Also handles FreeRADIUS client configuration.
    """

    # FreeRADIUS client config section marker
    RADIUID_SECTION_MARKER = "###################### RadiUID Generated Settings #####################\n"
    RADIUID_SECTION_WARNING = "################### Be Careful When Changing Manually #################\n"

    def __init__(self, context: Optional[AppContext] = None, ui: Optional[UserInterface] = None):
        """
        Initialize FileManager.

        Args:
            context: Application context (uses singleton if not provided)
            ui: User interface for output (creates new instance if not provided)
        """
        self.context = context or get_context()
        self.ui = ui or UserInterface()

    # ============================================================
    # Path Utilities
    # ============================================================

    @staticmethod
    def ensure_trailing_slash(path: str) -> str:
        """
        Ensure the directory path ends with '/'.

        Args:
            path: Directory path

        Returns:
            Path with trailing slash
        """
        if not path.endswith('/'):
            return path + '/'
        return path

    @staticmethod
    def split_filepath(filepath: str) -> Tuple[str, str]:
        """
        Split a filepath into directory and filename.

        Args:
            filepath: Full file path

        Returns:
            Tuple of (directory_path, filename)
        """
        match = re.findall(r"^(.+)/([^/]+)$", filepath)
        if match:
            dir_path, filename = match[0]
            dir_path = FileManager.ensure_trailing_slash(dir_path)
            return dir_path, filename
        else:
            # File is in the root directory.
            return "/", filepath.replace("/", "")

    # ============================================================
    # Path and Input Validation
    # ============================================================

    @staticmethod
    def validate_path(path_type: str, path: str) -> Dict[str, Any]:
        """
        Validate a Unix/Linux file or directory path.

        Args:
            path_type: 'dir' for directory, 'file' for file
            path: Path string to validate

        Returns:
            Dictionary with 'status' ('pass'/'fail') and 'errors' list
        """
        result = {'status': 'pass', 'errors': []}

        # Blacklisted patterns
        blacklist = {
            "space character": r" ",
            "double forward slash": r"\/\/",
            'double quote': r'"',
            "single quote": r"'",
            "pipe character": r"\|",
            "double period": r"\.\.",
            "comma": r",",
            "exclamation point": r"!",
            "grave accent": r"`",
            "ampersand": r"&",
            "asterisk": r"\*",
            "left parenthesis": r"\(",
            "right parenthesis": r"\)"
        }

        # Required patterns
        required = {"begins with /": r"^\/"}

        if path_type == "dir":
            required["ends with /"] = r"\/$"
        elif path_type == "file":
            blacklist["ends with /"] = r"\/$"

        # Check blacklist
        for name, pattern in blacklist.items():
            if re.search(pattern, path):
                result['status'] = 'fail'
                result['errors'].append(f"Pattern not allowed: {name}")

        # Check requirements
        for name, pattern in required.items():
            if not re.search(pattern, path):
                result['status'] = 'fail'
                result['errors'].append(f"Pattern required: {name}")

        return result

    @staticmethod
    def validate_domain_name(domain: str) -> Dict[str, Any]:
        """
        Validate a fully qualified domain name (FQDN).

        Args:
            domain: Domain name string

        Returns:
            Dictionary with 'status' and 'messages'
        """
        result = {'status': 'pass', 'messages': []}

        # Check for legal characters (RFC883, RFC952, plus underscore for AD domains)
        if not re.match(r"^[a-zA-Z0-9\-._]+$", domain):
            result['status'] = 'fail'
            result['messages'].append("Illegal character found. Only a-z, A-Z, 0-9, period (.), hyphen (-), and underscore (_) allowed.")
            return result

        # Check total length (RFC1035: max 253)
        if len(domain) > 253:
            result['status'] = 'fail'
            result['messages'].append("Domain name exceeds maximum length of 253 characters")
            return result

        # Check label lengths (max 63 per label)
        for label in domain.split("."):
            if len(label) > 63:
                result['status'] = 'fail'
                result['messages'].append(f"Label '{label}' exceeds max length of 63 characters")

        # Check first/last characters
        if not re.match(r"^[a-zA-Z0-9]", domain):
            result['status'] = 'fail'
            result['messages'].append("First character must be alphanumeric")

        if not re.search(r"[a-zA-Z0-9]$", domain):
            result['status'] = 'fail'
            result['messages'].append("Last character must be alphanumeric")

        # Check for labels starting/ending with hyphens
        if re.search(r"\.-|-\.", domain):
            result['status'] = 'fail'
            result['messages'].append("Labels cannot start or end with hyphens")

        # Check for double periods or triple hyphens
        if re.search(r"\.\.|---", domain):
            result['status'] = 'fail'
            result['messages'].append("No double periods (..) or triple hyphens (---) allowed")

        return result

    @staticmethod
    def validate_username(username: str) -> Dict[str, Any]:
        """
        Validate a username.

        Args:
            username: Username string

        Returns:
            Dictionary with 'status' and 'messages'
        """
        result = {'status': 'fail', 'messages': []}

        if re.match(r"^[a-zA-Z0-9_.]+$", username):
            result['status'] = 'pass'
            result['messages'].append("Username is valid")
        else:
            result['messages'].append(
                "Illegal characters in username. Valid: alphanumeric, underscore (_), period (.)"
            )

        return result

    @staticmethod
    def validate_password(password: str) -> Dict[str, Any]:
        """
        Validate a password (check for forbidden characters).

        Args:
            password: Password string

        Returns:
            Dictionary with 'status' and 'messages'
        """
        result = {'status': 'pass', 'messages': []}

        if re.search(r"[&<>]", password):
            result['status'] = 'fail'
            result['messages'].append("Characters '&', '<', and '>' are not allowed in passwords")
        else:
            result['messages'].append("Password is valid")

        return result

    @staticmethod
    def validate_ip(ip_type: str, ip_string: str) -> bool:
        """
        Validate an IPv4 address or CIDR block.

        Args:
            ip_type: 'address' or 'cidr'
            ip_string: IP address or CIDR string

        Returns:
            True if valid, False otherwise
        """
        if ip_type == "address":
            pattern = r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
        elif ip_type == "cidr":
            pattern = r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\/(?:[0-9]|1[0-9]|2[0-9]|3[0-2]?)$"
        else:
            return False

        return bool(re.match(pattern, ip_string))

    def check_targets(self, targets: List[Dict[str, str]]) -> Dict[str, Dict[str, Any]]:
        """
        Validate target configurations for completeness and correctness.

        Args:
            targets: List of target dictionaries with hostname, vsys, username, password

        Returns:
            Dictionary with validation results per target
        """
        result = {}

        for target in targets:
            target_name = f"{target.get('hostname', '')}:vsys{target.get('vsys', '1')}"
            result[target_name] = {"status": "working"}

            # Check hostname
            result[target_name]["hostnamecheck"] = {"status": "working", "messages": []}
            hostname = target.get('hostname', '')
            if self.validate_ip("address", hostname):
                result[target_name]["hostnamecheck"]["status"] = "pass"
                result[target_name]["hostnamecheck"]["messages"].append(
                    {"OK": "Target hostname is valid IPv4 address"}
                )
            else:
                hostname_result = self.validate_domain_name(hostname)
                result[target_name]["hostnamecheck"]["status"] = hostname_result['status']
                for msg in hostname_result.get('messages', []):
                    if 'Warning' in msg:
                        result[target_name]["hostnamecheck"]["messages"].append({"WARNING": msg})
                    elif hostname_result['status'] == 'fail':
                        result[target_name]["hostnamecheck"]["messages"].append({"FATAL": msg})
                    else:
                        result[target_name]["hostnamecheck"]["messages"].append({"OK": msg})

            # Check username
            try:
                username = target.get('username')
                if username:
                    username_result = self.validate_username(username)
                    result[target_name]["usernamecheck"] = {
                        "status": username_result['status'],
                        "messages": [{"OK" if username_result['status'] == 'pass' else "FATAL": msg}
                                     for msg in username_result.get('messages', [])]
                    }
                else:
                    result[target_name]["usernamecheck"] = {
                        "status": "fail",
                        "messages": [{"FATAL": "<username> parameter does not exist for this target"}]
                    }
            except KeyError:
                result[target_name]["usernamecheck"] = {
                    "status": "fail",
                    "messages": [{"FATAL": "<username> parameter does not exist for this target"}]
                }

            # Check password
            try:
                password = target.get('password')
                if password:
                    password_result = self.validate_password(password)
                    result[target_name]["passwordcheck"] = {
                        "status": password_result['status'],
                        "messages": [{"OK" if password_result['status'] == 'pass' else "FATAL": msg}
                                     for msg in password_result.get('messages', [])]
                    }
                else:
                    result[target_name]["passwordcheck"] = {
                        "status": "fail",
                        "messages": [{"FATAL": "<password> parameter does not exist for this target"}]
                    }
            except KeyError:
                result[target_name]["passwordcheck"] = {
                    "status": "fail",
                    "messages": [{"FATAL": "<password> parameter does not exist for this target"}]
                }

            # Determine overall status
            warnings = 0
            for check in result[target_name].keys():
                if check != "status":
                    if result[target_name][check]["status"] == "fail":
                        result[target_name]["status"] = "fail"
                        break
                    elif result[target_name][check]["status"] == "warning":
                        warnings += 1
                    elif result[target_name][check]["status"] == "pass":
                        result[target_name]["status"] = "pass"
            if warnings > 0:
                result[target_name]["status"] = "warning"

        return result

    def scrub_targets(self, mainmode: str, submode: str) -> None:
        """
        Validate targets and optionally remove invalid ones.

        Args:
            mainmode: 'noisy' to output messages, 'quiet' for silent
            submode: 'scrub' to remove invalid targets, 'report' to just report
        """
        if mainmode != "noisy":
            return

        # Convert FirewallTarget objects to dicts for check_targets
        targets = self.context.targets or []
        target_dicts = [
            {"hostname": t.hostname, "vsys": t.vsys, "username": t.username, "password": t.password}
            for t in targets
        ]

        checkdict = self.check_targets(target_dicts)

        for target_name in checkdict:
            if checkdict[target_name]["status"] == "pass":
                pass  # Target is valid
            else:
                # Log warnings and errors
                for check in checkdict[target_name]:
                    if check != "status":
                        for message in checkdict[target_name][check].get("messages", []):
                            if isinstance(message, dict):
                                for msg_type, msg_text in message.items():
                                    if msg_type == "WARNING":
                                        self.log_write(
                                            "normal",
                                            self.ui.color(
                                                f"***********TARGET {target_name}: {msg_type}: {msg_text} ***********",
                                                self.ui.yellow
                                            )
                                        )
                                    elif msg_type == "FATAL":
                                        self.log_write(
                                            "normal",
                                            self.ui.color(
                                                f"***********TARGET {target_name}: {msg_type}: {msg_text} ***********",
                                                self.ui.red
                                            )
                                        )

            if submode == "scrub":
                if checkdict[target_name]["status"] == "fail":
                    # Remove the bad target from context.targets
                    for i, t in enumerate(targets):
                        target_id = f"{t.hostname}:vsys{t.vsys}"
                        if target_id == target_name:
                            self.log_write(
                                "normal",
                                self.ui.color(
                                    f"***********Excluding {target_name} from loaded firewall targets***********",
                                    self.ui.red
                                )
                            )
                            self.context.targets.pop(i)
                            break
            elif submode == "report":
                if checkdict[target_name]["status"] == "fail":
                    self.log_write(
                        "normal",
                        self.ui.color(
                            f"***********Target {target_name} configuration is incomplete***********",
                            self.ui.red
                        )
                    )

    def validate_targets(self) -> Dict[str, Dict[str, Any]]:
        """
        Validate all configured firewall targets.

        Returns:
            Dictionary with validation results per target
        """
        results = {}

        for target in self.context.targets:
            target_id = target.identifier
            results[target_id] = {'status': 'pass', 'checks': {}}

            # Validate hostname
            if self.validate_ip('address', target.hostname):
                results[target_id]['checks']['hostname'] = {'status': 'pass', 'message': 'Valid IPv4 address'}
            else:
                hostname_check = self.validate_domain_name(target.hostname)
                results[target_id]['checks']['hostname'] = hostname_check
                if hostname_check['status'] == 'fail':
                    results[target_id]['status'] = 'fail'

            # Validate username
            if target.username:
                username_check = self.validate_username(target.username)
                results[target_id]['checks']['username'] = username_check
                if username_check['status'] == 'fail':
                    results[target_id]['status'] = 'fail'
            else:
                results[target_id]['checks']['username'] = {'status': 'fail', 'messages': ['Username is required']}
                results[target_id]['status'] = 'fail'

            # Validate password
            if target.password:
                password_check = self.validate_password(target.password)
                results[target_id]['checks']['password'] = password_check
                if password_check['status'] == 'fail':
                    results[target_id]['status'] = 'fail'
            else:
                results[target_id]['checks']['password'] = {'status': 'fail', 'messages': ['Password is required']}
                results[target_id]['status'] = 'fail'

        return results

    # ============================================================
    # File Operations
    # ============================================================

    @staticmethod
    def file_exists(filepath: str) -> bool:
        """
        Check if a file exists.

        Args:
            filepath: Path to file

        Returns:
            True if the file exists
        """
        return os.path.isfile(filepath)

    @staticmethod
    def directory_exists(dirpath: str) -> bool:
        """
        Check if a directory exists.

        Args:
            dirpath: Path to directory

        Returns:
            True if the directory exists
        """
        return os.path.isdir(dirpath)

    def list_files(self, path: str, mode: str = 'quiet') -> List[str]:
        """
        List all files in a directory (non-recursive).

        Args:
            path: Directory path
            mode: 'noisy' to log found files, 'quiet' for silent

        Returns:
            List of file paths
        """
        file_list = []
        verbose = (mode == 'noisy')

        if not os.path.isdir(path):
            if verbose:
                self.log_write("normal", f"Directory does not exist: {path}")
            return file_list

        for filename in os.listdir(path):
            filepath = os.path.join(path, filename)
            if os.path.isfile(filepath):
                file_list.append(filepath)
                if verbose:
                    self.log_write("normal", f"Found File: {filepath}...   Adding to file list")

        if len(file_list) == 0 and verbose:
            self.log_write("normal", "No Accounting Logs Found. Nothing to Do.")

        return file_list

    def copy_accounting_log(self, source_file: str) -> None:
        """
        Copy or append an accounting log file to the backup location.

        Args:
            source_file: Source file path
        """
        copy_path = self.context.config.acct_log_copy_path
        if not copy_path:
            return

        filename = os.path.basename(source_file)
        dest_path = os.path.join(copy_path, filename)

        if os.path.isfile(dest_path):
            # Append to the existing file.
            logger.info(f"Appending {source_file} to {dest_path}")
            with open(source_file, 'r') as src:
                with open(dest_path, 'a') as dst:
                    dst.write("\n\n")
                    dst.write(src.read())
        else:
            # Copy the new file.
            logger.info(f"Copying {source_file} to {copy_path}")
            shutil.copy2(source_file, copy_path)

    def remove_files(self, file_list: List[str]) -> None:
        """
        Remove files, optionally copying accounting logs first.

        Args:
            file_list: List of file paths to remove
        """
        for filepath in file_list:
            if not os.path.isfile(filepath):
                logger.warning(f"File not found, skipping: {filepath}")
                continue

            if self.context.config.acct_log_copy_path:
                self.copy_accounting_log(filepath)

            try:
                os.remove(filepath)
                logger.info(f"Removed file: {filepath}")
            except OSError as e:
                logger.error(f"Failed to remove file {filepath}: {e}")

    @staticmethod
    def write_file(filepath: str, content: str) -> None:
        """
        Write content to a file.

        Args:
            filepath: Destination file path
            content: Content to write
        """
        with open(filepath, 'w') as f:
            f.write(content)

    @staticmethod
    def read_file(filepath: str) -> str:
        """
        Read content from a file.

        Args:
            filepath: File path to read

        Returns:
            File content
        """
        with open(filepath, 'r') as f:
            return f.read()

    # ============================================================
    # Live Log Processing (for NPS/continuously written logs)
    # ============================================================

    def process_live_log(self) -> Optional[str]:
        """
        Extract new content from a live log file that is continuously being written to.
        Uses a position tracker file to remember where we left off.

        Returns:
            Path to the extracted log file, or None if no new content
        """
        config = self.context.config

        if not config.live_log_enabled:
            return None

        live_log = config.live_log_file
        tracker_file = config.live_log_tracker
        output_dir = config.radius_log_path

        if not live_log or not tracker_file:
            logger.warning("Live log processing enabled but live_log_file or live_log_tracker not set")
            return None

        if not os.path.isfile(live_log):
            logger.warning(f"Live log file does not exist: {live_log}")
            return None

        # Get the last processed position
        last_pos = self._get_tracker_position(tracker_file)

        # Get the current file size
        current_size = os.path.getsize(live_log)

        # Check if the file was truncated/rotated (size smaller than the last position).
        if current_size < last_pos:
            logger.info(f"Live log file appears to have been rotated (size {current_size} < last pos {last_pos}). Resetting position.")
            last_pos = 0

        # Check if there's new content.
        if current_size <= last_pos:
            logger.debug(f"No new content in live log (size={current_size}, last_pos={last_pos})")
            return None

        # Extract the new content.
        new_content = self._extract_from_position(live_log, last_pos)

        if not new_content or not new_content.strip():
            logger.debug("No new content extracted from live log")
            return None

        # Write to a dated output file.
        timestamp = int(time.time())
        base_name = os.path.basename(live_log).replace('.log', '').replace('.xml', '')
        output_file = os.path.join(output_dir, f"{base_name}-{timestamp}.log")

        # Ensure the output directory exists.
        os.makedirs(output_dir, exist_ok=True)

        with open(output_file, 'w') as f:
            f.write(new_content)

        logger.info(f"Extracted {len(new_content)} bytes from live log to {output_file}")

        # Update the tracker position.
        self._set_tracker_position(tracker_file, current_size)

        return output_file

    @staticmethod
    def _get_tracker_position(tracker_file: str) -> int:
        """
        Get the last processed byte position from the tracker file.

        Args:
            tracker_file: Path to position tracker file

        Returns:
            Last processed byte position (0 if the file doesn't exist)
        """
        try:
            # Ensure the tracker directory exists.
            tracker_dir = os.path.dirname(tracker_file)
            if tracker_dir and not os.path.exists(tracker_dir):
                os.makedirs(tracker_dir, exist_ok=True)

            if os.path.isfile(tracker_file):
                with open(tracker_file, 'r') as f:
                    content = f.read().strip()
                    if content:
                        return int(content)
        except (IOError, ValueError) as e:
            logger.warning(f"Error reading tracker file {tracker_file}: {e}")

        return 0

    @staticmethod
    def _set_tracker_position(tracker_file: str, position: int) -> None:
        """
        Save the current byte position to the tracker file.

        Args:
            tracker_file: Path to position tracker file
            position: Current byte position
        """
        try:
            # Ensure the tracker directory exists.
            tracker_dir = os.path.dirname(tracker_file)
            if tracker_dir and not os.path.exists(tracker_dir):
                os.makedirs(tracker_dir, exist_ok=True)

            with open(tracker_file, 'w') as f:
                f.write(str(position))
        except IOError as e:
            logger.error(f"Error writing tracker file {tracker_file}: {e}")

    @staticmethod
    def _extract_from_position(filepath: str, start_pos: int) -> str:
        """
        Extract content from a file starting at a byte position.

        Args:
            filepath: Path to the file
            start_pos: Starting byte position

        Returns:
            Content from start_pos to end of file
        """
        try:
            with open(filepath, 'rb') as f:
                f.seek(start_pos)
                content = f.read()
                return content.decode('utf-8', errors='ignore')
        except IOError as e:
            logger.error(f"Error reading from {filepath} at position {start_pos}: {e}")
            return ""

    # ============================================================
    # Logging Methods
    # ============================================================

    def log_write(self, mode: str, message: str) -> None:
        """
        Write a timestamped message to the log file.

        Args:
            mode: 'normal' for standard logging, 'quiet' for no console output
            message: Message to log
        """
        log_file = self.context.config.log_file
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"{timestamp}:   {message}\n"

        try:
            with open(log_file, 'a') as f:
                f.write(log_line)

            if mode == "normal":
                print(f"{timestamp}:   {message}")

            # Trim the log if needed.
            max_lines = self.context.config.max_log_lines
            if max_lines > 0:
                self.trim_log_file(log_file, max_lines)

        except IOError as e:
            print(self.ui.color(f"Cannot write to log file {log_file}: {e}", self.ui.red))

    @staticmethod
    def trim_log_file(filepath: str, max_lines: int) -> Dict[str, Any]:
        """
        Trim a log file to maximum line count.

        Args:
            filepath: Path to the log file
            max_lines: Maximum lines to keep

        Returns:
            Result dictionary with status
        """
        result = {'status': 'processing', 'message': ''}

        try:
            with open(filepath, 'r') as f:
                lines = f.readlines()

            if len(lines) > max_lines:
                # Keep only the last max_lines.
                lines_to_remove = len(lines) - max_lines
                new_lines = lines[lines_to_remove:]

                with open(filepath, 'w') as f:
                    f.writelines(new_lines)

                result['status'] = 'success'
                result['message'] = f"Trimmed {lines_to_remove} lines from {filepath}"
            else:
                result['status'] = 'success'
                result['message'] = f"File {filepath} is under max size"

        except IOError as e:
            result['status'] = 'fail'
            result['message'] = f"Error: {e}"

        return result

    # ============================================================
    # FreeRADIUS Client Configuration
    # ============================================================

    def _read_client_config(self) -> Tuple[List[str], int, Optional[str]]:
        """
        Read FreeRADIUS client config and find the RadiUID section.

        Returns:
            Tuple of (lines, section_start_index, error_message)
            section_start_index is -1 if the section not found
            error_message is None on success
        """
        client_path = self.context.system_info.client_config_path

        try:
            with open(client_path, 'r') as f:
                lines = f.readlines()
        except IOError:
            return [], -1, f"Cannot read {client_path}"

        # Find RadiUID section
        section_start = -1
        for i, line in enumerate(lines):
            if line == self.RADIUID_SECTION_MARKER:
                section_start = i
                break

        return lines, section_start, None

    def get_freeradius_clients(self) -> List[Dict[str, str]]:
        """
        Get the list of RadiUID-configured FreeRADIUS clients.

        Returns:
            List of client dictionaries with 'ip_block', 'secret', 'family'
        """
        result = []
        lines, start_line, error = self._read_client_config()

        if error:
            logger.warning(error)
            return result

        if start_line < 0:
            return result

        # Parse client entries after the header.
        client_lines = lines[start_line + 2:]  # Skip marker and warning
        i = 0

        while i < len(client_lines):
            line = client_lines[i].strip()

            if line.startswith('client '):
                # Extract the IP block from the client line.
                ip_block = line.replace('client ', '').replace(' {', '')

                # Look for ipvXaddr and secret in the next lines.
                family = 'ipv4'
                secret = ''

                for j in range(1, 5):
                    if i + j >= len(client_lines):
                        break
                    inner_line = client_lines[i + j].strip()

                    if inner_line.startswith('ipv4addr'):
                        family = 'ipv4'
                    elif inner_line.startswith('ipv6addr'):
                        family = 'ipv6'
                    elif inner_line.startswith('secret'):
                        parts = inner_line.split('=')
                        if len(parts) > 1:
                            secret = parts[1].strip()

                result.append({
                    'ip_block': ip_block,
                    'secret': secret,
                    'family': family
                })

                i += 5  # Skip to the next client block
            else:
                i += 1

        return result

    def add_freeradius_client(self, ip_block: str, secret: str, family: str = 'ipv4') -> str:
        """
        Add a FreeRADIUS client configuration.

        Args:
            ip_block: IP address or CIDR block
            secret: Shared secret
            family: 'ipv4' or 'ipv6'

        Returns:
            'SUCCESS' or error message
        """
        lines, section_start, error = self._read_client_config()

        if error:
            return f"FATAL: {error}"

        if section_start < 0:
            # Add the section header.
            lines.append("\n")
            lines.append(self.RADIUID_SECTION_MARKER)
            lines.append(self.RADIUID_SECTION_WARNING)

        # Build the client entry.
        addr_type = 'ipv4addr' if family == 'ipv4' else 'ipv6addr'
        client_entry = [
            '\n',
            f'client {ip_block} {{\n',
            f'    {addr_type}    = {ip_block}\n',
            f'    secret      = {secret}\n',
            f'    shortname   = Created_By_RadiUID\n',
            ' }\n'
        ]

        lines.extend(client_entry)

        client_path = self.context.system_info.client_config_path
        try:
            with open(client_path, 'w') as f:
                f.writelines(lines)
            return "SUCCESS"
        except IOError as e:
            return f"FATAL: Cannot write to {client_path}: {e}"

    def remove_freeradius_client(self, ip_block: str) -> str:
        """
        Remove a FreeRADIUS client by IP block.

        Args:
            ip_block: IP block to remove (or 'all' to clear all)

        Returns:
            'SUCCESS' or error message
        """
        if ip_block.lower() == 'all':
            return self.clear_freeradius_clients()

        # Get current clients
        current_clients = self.get_freeradius_clients()

        # Filter out the one to remove.
        new_clients = [c for c in current_clients if c['ip_block'] != ip_block]

        if len(new_clients) == len(current_clients):
            return f"Client {ip_block} not found"

        # Clear and re-add.
        self.clear_freeradius_clients()
        for client in new_clients:
            self.add_freeradius_client(client['ip_block'], client['secret'], client['family'])

        return "SUCCESS"

    def clear_freeradius_clients(self) -> str:
        """
        Remove all RadiUID-configured FreeRADIUS clients.

        Returns:
            'SUCCESS' or error message
        """
        lines, section_start, error = self._read_client_config()

        if error:
            return f"FATAL: {error}"

        if section_start < 0:
            return "SUCCESS"  # Nothing to clear

        # Keep only the lines before the RadiUID section.
        new_lines = lines[:section_start]

        client_path = self.context.system_info.client_config_path
        try:
            with open(client_path, 'w') as f:
                f.writelines(new_lines)
            return "SUCCESS"
        except IOError as e:
            return f"FATAL: Cannot write to {client_path}: {e}"

    def get_freeradius_clients_raw(self) -> str:
        """
        Get raw text of the RadiUID section in clients.conf.

        Returns:
            Raw text content
        """
        client_path = self.context.system_info.client_config_path

        try:
            with open(client_path, 'r') as f:
                lines = f.readlines()
        except IOError:
            return ""

        # Find RadiUID section
        section_start = -1
        for i, line in enumerate(lines):
            if line == self.RADIUID_SECTION_MARKER:
                section_start = i
                break

        if section_start < 0:
            return ""

        return ''.join(lines[section_start:])
