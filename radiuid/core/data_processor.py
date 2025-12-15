#!/usr/bin/env python3
"""
Data Processing Module
Handles RADIUS log parsing, data cleaning, validation, and munge operations
Supports both FreeRADIUS text format and Windows NPS XML format
"""

import re
import xml.etree.ElementTree as ElementTree
from typing import List, Dict, Any, Optional, TYPE_CHECKING

from ..context import AppContext, get_context
from ..logging_config import get_logger

if TYPE_CHECKING:
    from ..ui.interface import UserInterface
    from .file_manager import FileManager

logger = get_logger('data_processor')

# RADIUS packet type codes mapped to accounting status (RFC 2866, RFC 3575)
# Values 1-3, 11 are authentication events (Access-Request/Accept/Reject) - no IP is assigned yet.
# Values 4-5 are accounting events with IP info that we process.
NPS_PACKET_TYPES = {
    '1': 'access_request',   # Skip - no IP yet
    '2': 'access_accept',    # Skip - no IP yet
    '3': 'access_reject',    # Skip
    '4': 'start',  # Accounting-Start (session began)
    '5': 'stop',  # Accounting-Stop (session ended)
    '11': 'access_accept',   # Skip - no IP yet
}


class DataProcessor:
    """
    Processes RADIUS accounting data and performs string munging operations
    """

    def __init__(
        self,
        context: Optional[AppContext] = None,
        ui: Optional['UserInterface'] = None,
        filemgmt: Optional['FileManager'] = None
    ):
        """
        Initialize the data processor

        Args:
            context: Application context (uses singleton if not provided)
            ui: User interface instance (optional)
            filemgmt: File management instance (optional)
        """
        self.context = context or get_context()
        self.ui = ui
        self.filemgmt = filemgmt

    def search_to_dict(
        self,
        filelist: List[str],
        delineator: str,
        searchterm: str
    ) -> Dict[int, str]:
        """
        Search files for a term and return dictionary of matches

        Args:
            filelist: List of file paths to search
            delineator: Term to differentiate log entries
            searchterm: Term to search for

        Returns:
            Dictionary with entry number as key and line as value
        """
        result_dict = {}
        entry = 0

        if delineator == "[PARAGRAPH]":
            for filename in filelist:
                if self.filemgmt:
                    self.filemgmt.log_write("normal", f'Searching File: {filename} for {searchterm}')
                else:
                    logger.info(f'Searching File: {filename} for {searchterm}')

                with open(filename) as filetext:
                    for line in filetext:
                        if searchterm in line:
                            result_dict[entry] = line
                        elif line == "\n":
                            entry += 1
        else:
            for filename in filelist:
                if self.filemgmt:
                    self.filemgmt.log_write("normal", f'Searching File: {filename} for {searchterm}')
                else:
                    logger.info(f'Searching File: {filename} for {searchterm}')

                with open(filename, 'r') as filetext:
                    for line in filetext:
                        if delineator in line:
                            entry += 1
                        if searchterm in line:
                            result_dict[entry] = line

        return result_dict

    def clean_ips(self, dictionary: Dict[int, str]) -> Dict[int, str]:
        """
        Extract IP addresses from dictionary values

        Args:
            dictionary: Dictionary with lines containing IP addresses

        Returns:
            Dictionary with cleaned IP addresses
        """
        newdict = {}
        ipaddress_regex = r"(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)"

        for key, value in dictionary.items():
            matches = re.findall(ipaddress_regex, value, flags=0)
            if matches:
                newdict[key] = matches[0]

        if self.filemgmt:
            self.filemgmt.log_write("normal", "IP Address List Cleaned Up!")
        else:
            logger.info("IP Address List Cleaned Up!")

        return newdict

    def clean_names(self, dictionary: Dict[int, str]) -> Dict[int, str]:
        """
        Extract usernames from dictionary values

        Args:
            dictionary: Dictionary with lines containing usernames

        Returns:
            Dictionary with cleaned usernames
        """
        newdict = {}

        for key, value in dictionary.items():
            words = value.split(" ")
            cleaned = words[-1]
            cleaned = cleaned[1:-2] if len(cleaned) > 2 else cleaned
            newdict[key] = cleaned

        if self.filemgmt:
            self.filemgmt.log_write("normal", "Username List Cleaned Up!")
        else:
            logger.info("Username List Cleaned Up!")

        return newdict

    def clean_statuses(self, dictionary: Dict[int, str]) -> Dict[int, str]:
        """
        Extract RADIUS accounting status types

        Args:
            dictionary: Dictionary with lines containing status types

        Returns:
            Dictionary with cleaned status values
        """
        newdict = {}

        for key, value in dictionary.items():
            value_lower = value.lower()
            if "update" in value_lower:
                cleaned = "update"
            elif "start" in value_lower:
                cleaned = "start"
            elif "stop" in value_lower:
                cleaned = "stop"
            else:
                logger.warning(f"Unrecognized RADIUS Accounting status type: {value}")
                continue

            newdict[key] = cleaned

        if self.filemgmt:
            self.filemgmt.log_write("normal", "Status List Cleaned Up!")
        else:
            logger.info("Status List Cleaned Up!")

        return newdict

    def merge_dicts(
        self,
        ipdict: Dict[int, str],
        unamedict: Dict[int, str],
        statusdict: Dict[int, str]
    ) -> Dict[str, Dict[str, str]]:
        """
        Merge IP, username, and status dictionaries

        Args:
            ipdict: Dictionary of IP addresses
            unamedict: Dictionary of usernames
            statusdict: Dictionary of status types

        Returns:
            Dictionary with IP as key and username/status as value
        """
        newdict = {}

        for key in ipdict.keys():
            try:
                uname = unamedict[key]
                ip = ipdict[key]
                status = statusdict[key]
                newdict[ip] = {"username": uname, "status": status}
            except KeyError:
                logger.error(f"Missing username, IP, or status in entry {key}")
                logger.debug(f"IP dict: {ipdict}, Username dict: {unamedict}")

        if self.filemgmt:
            self.filemgmt.log_write("normal", "Dictionary values merged")
        else:
            logger.info("Dictionary values merged")

        return newdict

    # ========== Format Detection and Unified Parsing ==========

    def detect_log_format(self, filepath: str) -> str:
        """
        Detect log file format: NPS/IAS CSV (may have XML header), or FreeRADIUS text

        NPS files may have XML <Event> lines at the start followed by CSV data.
        We detect CSV format if we find CSV lines with IAS/NPS markers.

        Args:
            filepath: Path to the log file

        Returns:
            'nps_csv' or 'freeradius'
        """
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                # Read line by line to handle files with very long XML lines
                # Limit scan to first 100 lines to avoid memory issues on large files
                # (NPS XML files can have extremely long lines that would slow detection)
                lines_checked = 0
                max_lines = 100

                for line in f:
                    lines_checked += 1
                    if lines_checked > max_lines:
                        break

                    line = line.strip()

                    # Skip empty lines and XML lines
                    if not line or line.startswith('<'):
                        continue

                    # Check if this looks like NPS CSV (starts with IP, has IAS/NPS marker)
                    if ',' in line and ('IAS' in line or 'NPS' in line):
                        # Verify first field looks like an IP
                        first_field = line.split(',')[0].strip()
                        if self._is_valid_ip(first_field):
                            logger.info(f"Detected NPS CSV format in {filepath}")
                            return 'nps_csv'

                logger.debug(f"Checked {lines_checked} lines, no NPS CSV format detected")
        except Exception as e:
            logger.warning(f"Error detecting log format for {filepath}: {e}")

        return 'freeradius'

    def parse_log_files(self, filelist: List[str]) -> Dict[str, Dict[str, str]]:
        """
        Parse log files with auto-detection of format

        Args:
            filelist: List of file paths to parse

        Returns:
            Dictionary with IP as key and {username, status} as value
        """
        if not filelist:
            return {}

        # Detect format from first file
        format_type = self.detect_log_format(filelist[0])

        if self.filemgmt:
            self.filemgmt.log_write("normal", f"Detected log format: {format_type}")
        else:
            logger.info(f"Detected log format: {format_type}")

        if format_type == 'nps_csv':
            return self.parse_nps_csv(filelist)
        else:
            return self._parse_freeradius(filelist)

    def parse_nps_xml(self, filelist: List[str]) -> Dict[str, Dict[str, str]]:
        """
        Parse NPS (Windows Network Policy Server) XML log files

        Args:
            filelist: List of NPS XML log file paths

        Returns:
            Dictionary with IP as key and {username, status} as value
        """
        result = {}

        for filepath in filelist:
            if self.filemgmt:
                self.filemgmt.log_write("normal", f"Parsing NPS XML file: {filepath}")
            else:
                logger.info(f"Parsing NPS XML file: {filepath}")

            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # NPS XML files are fragments without root - wrap them
                wrapped_content = f"<root>{content}</root>"

                try:
                    root = ElementTree.fromstring(wrapped_content)
                except ElementTree.ParseError as e:
                    logger.warning(f"XML parse error in {filepath}: {e}")
                    continue

                # Process each Event element
                for event in root.findall('.//Event'):
                    mapping = self._parse_nps_event(event)
                    if mapping:
                        ip, data = mapping
                        result[ip] = data

            except Exception as e:
                logger.error(f"Error parsing NPS file {filepath}: {e}")

        if self.filemgmt:
            self.filemgmt.log_write("normal", f"Parsed {len(result)} IP-to-user mappings from NPS logs")
        else:
            logger.info(f"Parsed {len(result)} IP-to-user mappings from NPS logs")

        return result

    def _parse_nps_event(self, event: ElementTree.Element) -> Optional[tuple]:
        """
        Parse a single NPS Event element

        Args:
            event: XML Event element

        Returns:
            Tuple of (ip, {username, status}) or None if invalid/incomplete
        """
        # Get Packet-Type to determine event type
        packet_type_elem = event.find('Packet-Type')
        if packet_type_elem is None or packet_type_elem.text is None:
            return None

        packet_type = packet_type_elem.text.strip()
        status = NPS_PACKET_TYPES.get(packet_type)

        # Auth events (types 1-3, 11) don't have Acct-Status-Type field
        # If we have IP+username info from auth response, treat as session start
        # (Some NPS configs include Framed-IP in Access-Accept responses)
        if status not in ('start', 'stop'):
            status = 'start'

        # Get IP address - try Client-IP-Address first, then Framed-IP-Address
        ip = None

        client_ip_elem = event.find('Client-IP-Address')
        if client_ip_elem is not None and client_ip_elem.text:
            ip = client_ip_elem.text.strip()

        if not ip:
            framed_ip_elem = event.find('Framed-IP-Address')
            if framed_ip_elem is not None and framed_ip_elem.text:
                ip = framed_ip_elem.text.strip()

        if not ip:
            return None

        # Get username from SAM-Account-Name (has DOMAIN\user format)
        # e.g., "JINDAL_DOMAIN\dawnc" -> "dawnc"
        username = None

        sam_elem = event.find('SAM-Account-Name')
        if sam_elem is not None and sam_elem.text:
            sam_value = sam_elem.text.strip()
            # Extract username from DOMAIN\username format
            if '\\' in sam_value:
                username = sam_value.split('\\')[-1]
            else:
                username = sam_value

        # Fallback to User-Name if SAM-Account-Name not found
        if not username:
            user_elem = event.find('User-Name')
            if user_elem is not None and user_elem.text:
                username = user_elem.text.strip()

        if not username:
            return None

        return (ip, {"username": username, "status": status})

    def parse_nps_csv(self, filelist: List[str]) -> Dict[str, Dict[str, str]]:
        """
        Parse NPS/IAS CSV log files

        Files may contain XML <Event> lines at the start - these are skipped.
        Column positions are configurable via nps_csv settings.

        Default CSV format fields (comma-separated):
        0: IP address (e.g., 10.1.75.8)
        1: Username (e.g., Larryg or jindal_domain\\metlab)
        6: Packet type (4=start, 5=stop, 11=access-accept, etc.)

        When columns are set to -1, auto-detection is used based on RADIUS
        attribute numbers in the CSV (e.g., "8,10.1.2.3" for Framed-IP-Address).

        Args:
            filelist: List of NPS CSV log file paths

        Returns:
            Dictionary with IP as key and {username, status} as value
        """
        result = {}

        # Get column settings from config (default to standard positions)
        ip_col = 0
        username_col = 1
        packet_type_col = 6

        if self.context and self.context.config:
            ip_col = self.context.config.nps_ip_column
            username_col = self.context.config.nps_username_column
            packet_type_col = self.context.config.nps_packet_type_column

        use_auto_detect = ip_col < 0 or username_col < 0

        for filepath in filelist:
            if self.filemgmt:
                self.filemgmt.log_write("normal", f"Parsing NPS CSV file: {filepath}")
            else:
                logger.info(f"Parsing NPS CSV file: {filepath}")

            csv_lines_parsed = 0
            xml_lines_skipped = 0

            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if not line:
                            continue

                        # Skip XML lines (they start with <)
                        if line.startswith('<'):
                            xml_lines_skipped += 1
                            continue

                        fields = line.split(',')

                        if use_auto_detect:
                            # Auto-detect mode: look for RADIUS attribute numbers
                            mapping = self._parse_nps_csv_auto(fields, line_num)
                            if mapping:
                                ip, data = mapping
                                result[ip] = data
                                csv_lines_parsed += 1
                            continue

                        # Fixed column mode
                        min_fields = max(ip_col, username_col, packet_type_col) + 1
                        if len(fields) < min_fields:
                            logger.debug(
                                f"Skipping line {line_num}: not enough fields ({len(fields)}, need {min_fields})")
                            continue

                        ip = fields[ip_col].strip() if ip_col >= 0 else None
                        username_raw = fields[username_col].strip() if username_col >= 0 else None
                        packet_type = fields[packet_type_col].strip() if packet_type_col >= 0 and packet_type_col < len(
                            fields) else '4'

                        # Validate IP address
                        if not ip or not self._is_valid_ip(ip):
                            logger.debug(f"Skipping line {line_num}: invalid IP '{ip}'")
                            continue

                        # Extract username (handle DOMAIN\user format)
                        if username_raw and '\\' in username_raw:
                            username = username_raw.split('\\')[-1]
                        else:
                            username = username_raw

                        if not username:
                            logger.debug(f"Skipping line {line_num}: empty username")
                            continue

                        # Map packet type to status
                        status = NPS_PACKET_TYPES.get(packet_type, 'start')
                        if status not in ('start', 'stop'):
                            status = 'start'

                        result[ip] = {"username": username, "status": status}
                        csv_lines_parsed += 1

            except Exception as e:
                logger.error(f"Error parsing NPS CSV file {filepath}: {e}")

            if xml_lines_skipped > 0:
                logger.info(f"Skipped {xml_lines_skipped} XML lines in {filepath}")

        if self.filemgmt:
            self.filemgmt.log_write("normal", f"Parsed {len(result)} IP-to-user mappings from NPS CSV logs")
        else:
            logger.info(f"Parsed {len(result)} IP-to-user mappings from NPS CSV logs")

        return result

    def _parse_nps_csv_auto(self, fields: List[str], line_num: int) -> Optional[tuple]:
        """
        Parse NPS CSV line using auto-detection based on RADIUS attribute numbers.

        Looks for attribute patterns like "8,10.1.2.3" (Framed-IP-Address) or
        "1,username" (User-Name) in the CSV fields.

        RADIUS Attribute Numbers:
        - 1: User-Name
        - 4: NAS-IP-Address (access point IP - skip this)
        - 8: Framed-IP-Address (user's assigned IP)
        - 40: Acct-Status-Type (1=start, 2=stop)
        - 4108: MS-RAS-Client-IP-Address
        - 4129: MS-User-Name

        Args:
            fields: CSV fields from a single line
            line_num: Line number for debug logging

        Returns:
            Tuple of (ip, {username, status}) or None if not parseable
        """
        ip = None
        username = None
        status = 'start'

        # Join fields and look for attribute patterns
        line_content = ','.join(fields)

        # RADIUS attribute numbers for IP address (RFC 2865)
        # 8: Framed-IP-Address - the user's assigned IP (preferred)
        # 4108: MS-RAS-Client-IP - Microsoft vendor-specific attribute (fallback)
        # Note: We skip attribute 4 (NAS-IP-Address) - that's the access point's IP, not the user's
        ip_patterns = [
            (r'\b8,(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b', 'Framed-IP-Address'),
            (r'\b4108,(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b', 'MS-RAS-Client-IP'),
        ]

        for pattern, attr_name in ip_patterns:
            match = re.search(pattern, line_content)
            if match:
                candidate_ip = match.group(1)
                if self._is_valid_ip(candidate_ip):
                    ip = candidate_ip
                    logger.debug(f"Line {line_num}: Found IP via {attr_name}: {ip}")
                    break

        # RADIUS attribute numbers for username (RFC 2865)
        # 1: User-Name - standard RADIUS username (preferred)
        # 4129: MS-User-Name - Microsoft vendor-specific attribute (fallback)
        username_patterns = [
            (r'\b1,([^,]+)', 'User-Name'),
            (r'\b4129,([^,]+)', 'MS-User-Name'),
        ]

        for pattern, attr_name in username_patterns:
            match = re.search(pattern, line_content)
            if match:
                username_raw = match.group(1).strip()
                if username_raw and not username_raw.isdigit():
                    # Handle DOMAIN\user format
                    if '\\' in username_raw:
                        username = username_raw.split('\\')[-1]
                    else:
                        username = username_raw
                    logger.debug(f"Line {line_num}: Found username via {attr_name}: {username}")
                    break

        # RADIUS Acct-Status-Type attribute (40) values per RFC 2866:
        # 1 = Start (session began), 2 = Stop (session ended)
        # Other values (3=Interim-Update, 7=Accounting-On, etc.) default to 'start'
        status_match = re.search(r'\b40,(\d+)\b', line_content)
        if status_match:
            status_code = status_match.group(1)
            if status_code == '1':
                status = 'start'
            elif status_code == '2':
                status = 'stop'

        if ip and username:
            return (ip, {"username": username, "status": status})

        return None

    def _is_valid_ip(self, ip: str) -> bool:
        """
        Check if string is a valid IPv4 address

        Args:
            ip: String to check

        Returns:
            True if valid IPv4 address, False otherwise
        """
        ipaddress_regex = r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
        return bool(re.match(ipaddress_regex, ip))

    def _parse_freeradius(self, filelist: List[str]) -> Dict[str, Dict[str, str]]:
        """
        Parse FreeRADIUS text log files (existing logic refactored)

        Args:
            filelist: List of FreeRADIUS log file paths

        Returns:
            Dictionary with IP as key and {username, status} as value
        """
        # Get search terms from context
        delineatorterm = "[PARAGRAPH]"
        usernameterm = "User-Name"
        ipaddressterm = "Framed-IP-Address"

        if self.context and self.context.config:
            delineatorterm = self.context.config.delineator_term or delineatorterm
            usernameterm = self.context.config.username_term or usernameterm
            ipaddressterm = self.context.config.ip_address_term or ipaddressterm

        # Extract data using existing methods
        usernames = self.search_to_dict(filelist, delineatorterm, usernameterm)
        ipaddresses = self.search_to_dict(filelist, delineatorterm, ipaddressterm)
        statustypes = self.search_to_dict(filelist, delineatorterm, "Acct-Status-Type")

        # Clean the extracted data
        usernames = self.clean_names(usernames)
        ipaddresses = self.clean_ips(ipaddresses)
        statustypes = self.clean_statuses(statustypes)

        # Merge into IP-to-User dictionary
        return self.merge_dicts(ipaddresses, usernames, statustypes)

    def find_index_in_list(
        self,
        querylist: List[str],
        listinput: List[str]
    ) -> Dict[str, int]:
        """
        Find indices of queries in a list

        Args:
            querylist: List of search queries
            listinput: List to search through

        Returns:
            Dictionary with query as key and index as value
        """
        result = {}

        for query in querylist:
            indexpointer = 0
            for entry in listinput:
                if query == entry:
                    result[query] = indexpointer
                indexpointer += 1

        return result

    def sortlist(self, input_list: List[str]) -> List[str]:
        """
        Sort list of strings by numerical values within them

        Args:
            input_list: List of strings containing numbers

        Returns:
            Sorted list
        """
        nums = []
        mappings = {}
        result = []
        nonums = []

        for entry in input_list:
            matches = re.findall(r'[0-9]+', entry)
            if matches:
                num = int(matches[0])
                mappings[num] = entry
                nums.append(num)
            else:
                nonums.append(entry)

        nums.sort()

        for num in nums:
            result.append(mappings[num])

        result.extend(nonums)

        return result

    def munge(
        self,
        inputdatalist: List[str],
        mungeruledict: Dict[str, Any]
    ) -> List[str]:
        """
        Munge (manipulate) strings based on rule set

        Args:
            inputdatalist: List of input strings
            mungeruledict: Dictionary-based rule set

        Returns:
            List of munged strings
        """
        result = []
        ruleindex = {'rules': []}
        debug = 'debug' in mungeruledict.keys()

        # Build rule index
        for rule in mungeruledict:
            if 'rule' in rule:
                ruleindex['rules'].append(rule)
                ruleindex[rule] = []
                for step in mungeruledict[rule]:
                    if 'step' in step:
                        ruleindex[rule].append(step)
                ruleindex[rule] = self.sortlist(ruleindex[rule])

        ruleindex['rules'] = self.sortlist(ruleindex['rules'])

        if debug:
            print(f"\n\n----- Sorted index of rules and steps: {ruleindex} -----")

        # Process each input
        for input_item in inputdatalist:
            if debug:
                print(f"\n\n----- Input String: {input_item} -----")

            inputresult = input_item
            added = False
            interrupt = "none"
            variables = {}

            # Process each rule
            for rule in ruleindex['rules']:
                if debug:
                    print(f"\n\n\t----- {rule} -----")
                    print(f"\t\t----- Rule beginning with input: {inputresult} -----")

                if interrupt in ['accept', 'discard']:
                    break

                currentrule = mungeruledict[rule]

                # Check if input matches rule
                if 'any' in currentrule['match'].keys():
                    inputmatches = True
                else:
                    criterion = currentrule['match']['criterion']
                    regex = currentrule['match']['regex']

                    if criterion == 'complete':
                        inputmatches = str(inputresult) in re.findall(regex, str(inputresult))
                    elif criterion == 'partial':
                        inputmatches = len(re.findall(regex, str(inputresult))) > 0
                    else:
                        inputmatches = False

                if inputmatches:
                    if debug:
                        print(f"\n\t\t----- Matched pattern for {rule} -----")

                    # Process each step in the rule
                    for step in ruleindex[rule]:
                        currentstep = mungeruledict[rule][step]

                        if debug:
                            print(f"\n\t\t----- Loaded {step}: {currentstep} -----")

                        step_key = list(currentstep.keys())[0]

                        if step_key == 'accept':
                            interrupt = "accept"
                            if debug:
                                print("\t\t\t----- Accept interrupt detected -----")
                            break

                        elif step_key == 'discard':
                            interrupt = "discard"
                            if debug:
                                print("\t\t\t----- Discard interrupt detected -----")
                            break

                        elif 'set-variable' in currentstep.keys():
                            variablename = currentstep['set-variable']
                            variablevalue = ''  # Default value

                            if 'from-string' in currentstep.keys():
                                variablevalue = currentstep['from-string']
                            elif 'from-match' in currentstep.keys():
                                if isinstance(currentstep['from-match'], dict):
                                    variablevalue = inputresult
                                else:
                                    try:
                                        matches = re.findall(currentstep['from-match'], inputresult)
                                        variablevalue = matches[0] if matches else ''
                                    except IndexError:
                                        variablevalue = ''

                            variables[variablename] = variablevalue

                            if debug:
                                print(f"\t\t\t----- Setting variable {variablename} = {variablevalue} -----")

                        elif step_key == 'assemble':
                            variableindex = list(currentstep['assemble'].keys())
                            variableindex = self.sortlist(variableindex)

                            if debug:
                                print(f"\t\t\t----- Assembling Variables: {variableindex} -----")

                            assembleresult = ''
                            for variableid in variableindex:
                                variablename = ''  # Default value
                                try:
                                    variablename = currentstep['assemble'][variableid]
                                    variablevalue = variables[variablename]
                                    assembleresult += variablevalue
                                except KeyError:
                                    if debug:
                                        print(f"\t\t\t###### ERROR: CANNOT FIND VARIABLE {variablename}")

                            if debug:
                                print(f"\t\t\t----- Assemble Result: {assembleresult} -----")

                            inputresult = assembleresult

                else:
                    if debug:
                        print(f"\t\t----- No match in {rule} for input {inputresult} -----")

            # Add to result
            if interrupt != "discard" and not added:
                result.append(inputresult)
                added = True
                if debug:
                    print(f"\t----- Input {inputresult} added to result -----")

        return result


# Legacy compatibility - old class name
class data_processing(DataProcessor):
    """Legacy alias for DataProcessor class"""
    pass
