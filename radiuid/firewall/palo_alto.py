#!/usr/bin/env python3
"""
Palo Alto Firewall Interaction Module
Handles User-ID API calls to Palo Alto Networks firewalls
"""

import os
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import List, Dict, Optional, Union, TYPE_CHECKING

from ..context import AppContext, get_context, FirewallTarget
from ..logging_config import get_logger
from ..constants import TLSVersions

if TYPE_CHECKING:
    from ..ui.interface import UserInterface
    from ..core.file_manager import FileManager
    from ..core.data_processor import DataProcessor

logger = get_logger('palo_alto')


def _get_target_attr(target: Union[FirewallTarget, Dict[str, str]], attr: str, default: str = '') -> str:
    """Helper to get attribute from FirewallTarget or dict"""
    if isinstance(target, FirewallTarget):
        return getattr(target, attr, default)
    return target.get(attr, default)


class PaloAltoFirewall:
    """
    Manages User-ID interactions with Palo Alto Networks firewalls
    """

    def __init__(
        self,
        context: Optional[AppContext] = None,
        ui: Optional['UserInterface'] = None,
        filemgmt: Optional['FileManager'] = None,
        dataprocessor: Optional['DataProcessor'] = None,
        max_uids_per_call: int = 50,
        tls_version: Optional[ssl.TLSVersion] = None
    ):
        """
        Initialize firewall interaction

        Args:
            context: Application context (uses singleton if not provided)
            ui: User interface instance (optional)
            filemgmt: File management instance (optional)
            dataprocessor: Data processor instance (optional)
            max_uids_per_call: Maximum UIDs per API call
            tls_version: TLS version to use for connections
        """
        self.context = context or get_context()
        self.ui = ui
        self.filemgmt = filemgmt
        self.dpr = dataprocessor
        self.max_uids_per_call = max_uids_per_call
        self.tls_version = tls_version or self._get_tls_version()

    def _get_tls_version(self) -> Optional[ssl.TLSVersion]:
        """Get TLS version from context config"""
        if self.context and self.context.config:
            tls_ver = self.context.config.tls_version
            if tls_ver:
                return TLSVersions.get_tls_version(tls_ver)
        return None

    def _create_ssl_context(self) -> ssl.SSLContext:
        """Create an SSL context with appropriate TLS version settings"""
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        if self.tls_version:
            # Set both min and max to force specific TLS version
            context.minimum_version = self.tls_version
            context.maximum_version = self.tls_version

        return context

    @staticmethod
    def xml_formatter_v67(
        ipanduserdict: Dict[str, Dict[str, str]],
        targetlist: List[Union[FirewallTarget, Dict[str, str]]],
        userdomain: Optional[str] = None,
        timeout: int = 1440
    ) -> Dict[str, List[str]]:
        """
        Format IP-to-User mappings as XML entries

        Args:
            ipanduserdict: Dictionary with IP addresses and usernames
            targetlist: List of firewall targets
            userdomain: Optional domain to prepend to usernames
            timeout: Timeout in minutes for User-ID mappings

        Returns:
            Dictionary with hostname:vsys as key and list of XML entries as value
        """
        xmldict = {}

        for target in targetlist:
            hostname = _get_target_attr(target, 'hostname')
            vsys = _get_target_attr(target, 'vsys', '1')
            target_key = f"{hostname}:vsys{vsys}"
            xmldict[target_key] = []

            for ip, user_info in ipanduserdict.items():
                username = user_info["username"]

                if userdomain is None:
                    entry = f'<entry name="{username}" ip="{ip}" timeout="{timeout}">'
                else:
                    entry = rf'<entry name="{userdomain}\{username}" ip="{ip}" timeout="{timeout}">'

                xmldict[target_key].append(entry)

        return xmldict

    def xml_assembler_v67(
        self,
        ipuserxmldict: Dict[str, List[str]],
        targetlist: List[Union[FirewallTarget, Dict[str, str]]]
    ) -> tuple:
        """
        Assemble XML entries into complete User-ID API URLs

        Args:
            ipuserxmldict: Dictionary of XML entries per target
            targetlist: List of firewall targets with credentials

        Returns:
            Tuple of (url_dict, xml_dict) where:
                url_dict: Dictionary with hostname:vsys as key and list of URLs as value
                xml_dict: Dictionary with hostname:vsys as key and list of XML payloads as value
        """
        finishedurldict = {}
        finishedxmldict = {}

        for host in targetlist:
            hostname = _get_target_attr(host, 'hostname')
            vsys = _get_target_attr(host, 'vsys', '1')
            port = _get_target_attr(host, 'port', '443')
            apikey = _get_target_attr(host, 'api_key') or _get_target_attr(host, 'apikey')

            hostxmlentries = ipuserxmldict[f"{hostname}:vsys{vsys}"].copy()
            finishedurllist = []
            finishedxmllist = []
            xmluserdata = ""

            # Palo Alto User-ID API has a limit on UIDs per call (default 50)
            # Must batch large mappings into multiple API requests
            while hostxmlentries:
                batch = hostxmlentries[:self.max_uids_per_call]

                for entry in batch:
                    xmluserdata += entry + "\n</entry>\n"
                    hostxmlentries.remove(entry)

                urldecoded = f'''<uid-message>
    <version>1.0</version>
    <type>update</type>
    <payload>
    <login>
    {xmluserdata}
    </login>
    </payload>
    </uid-message>'''

                finishedxmllist.append(urldecoded)
                urljunk = urllib.parse.quote_plus(urldecoded)
                # Palo Alto API requires vsysN format (e.g., vsys1) - virtual system ID
                url = f'https://{hostname}:{port}/api/?key={apikey}&type=user-id&vsys=vsys{vsys}&cmd={urljunk}'
                finishedurllist.append(url)
                xmluserdata = ""

            finishedurldict[f"{hostname}:vsys{vsys}"] = finishedurllist
            finishedxmldict[f"{hostname}:vsys{vsys}"] = finishedxmllist

        return finishedurldict, finishedxmldict

    def pull_api_key(
        self,
        mode: str,
        targetlist: List[Union[FirewallTarget, Dict[str, str]]]
    ) -> None:
        """
        Retrieve API keys from firewalls using credentials

        Args:
            mode: 'noisy' for verbose logging, 'quiet' for silent
            targetlist: List of targets to retrieve keys for (modified in place)

        Raises:
            FirewallConnectionError: If firewall cannot be accessed
            FirewallAPIError: If credentials are invalid
        """
        if not isinstance(targetlist, list):
            raise ValueError('API Key function requires a list as input')

        for target in targetlist[:]:  # Iterate over copy to allow removal
            username = _get_target_attr(target, 'username')
            password = _get_target_attr(target, 'password')
            port = _get_target_attr(target, 'port', '443')
            hostname = _get_target_attr(target, 'hostname')
            vsys = _get_target_attr(target, 'vsys', '1')

            encodedusername = urllib.parse.quote_plus(username)
            encodedpassword = urllib.parse.quote_plus(password)

            url = f'https://{hostname}:{port}/api/?type=keygen&user={encodedusername}&password={encodedpassword}'

            try:
                gcontext = self._create_ssl_context()
                response = urllib.request.urlopen(url, context=gcontext).read().decode('utf-8')
            except urllib.error.URLError as e:
                logger.error(f'Firewall {hostname}:vsys{vsys} inaccessible: {e}')
                response = "FATAL: Firewall Inaccessible"

            if mode == "noisy":
                logger.info(f"Pulling API key from {hostname}:vsys{vsys}")

            if 'success' in response:
                # Extract API key from response
                stripped1 = response.replace("<response status = 'success'><result><key>", "")
                stripped2 = stripped1.replace("</key></result></response>", "")
                api_key = stripped2.strip()

                # Set the API key on the target
                if isinstance(target, FirewallTarget):
                    target.api_key = api_key
                else:
                    target['apikey'] = api_key

                if mode == "noisy":
                    logger.info(f"Added API key to {hostname}:vsys{vsys}")

            elif "Firewall Inaccessible" in response:
                logger.error(f'Firewall {hostname}:vsys{vsys} cannot be accessed. Removing from targets')
                targetlist.remove(target)

            elif "Invalid credentials" in response:
                logger.error(f'Invalid credentials for {hostname}:vsys{vsys}. Removing from targets')
                targetlist.remove(target)

    def push_uids(
        self,
        ipanduserdict: Dict[str, Dict[str, str]],
        filelist: List[str],
        targets: Optional[List[Union[FirewallTarget, Dict[str, str]]]] = None,
        radiusstopaction: Optional[str] = None,
        userdomain: Optional[str] = None,
        timeout: Optional[int] = None,
        tomunge: Optional[bool] = None,
        mungeconfig: Optional[Dict] = None
    ) -> None:
        """
        Push User-ID mappings to firewalls

        Args:
            ipanduserdict: Dictionary of IP to username mappings
            filelist: List of log files to remove after push
            targets: List of firewall targets (uses context.targets if not provided)
            radiusstopaction: Action for RADIUS stop messages ('clear', 'ignore', 'push')
            userdomain: Optional domain to prepend
            timeout: Timeout for mappings
            tomunge: Whether to apply munge rules
            mungeconfig: Munge configuration if tomunge is True
        """
        # Get values from context if not provided
        if targets is None:
            targets = self.context.targets or []
        if radiusstopaction is None:
            radiusstopaction = getattr(self.context.config, 'radius_stop_action', 'push') or 'push'
        if userdomain is None:
            userdomain = getattr(self.context.config, 'user_domain', None)
        if timeout is None:
            timeout = int(getattr(self.context.config, 'timeout', 1440) or 1440)
        if tomunge is None:
            tomunge = bool(getattr(self.context.config, 'munge_config', None))
        if mungeconfig is None:
            mungeconfig = getattr(self.context.config, 'munge_config', None)

        removelist = []

        # Handle RADIUS stop messages (user logged out or session ended)
        # Actions: "clear" = remove from firewall, "ignore" = skip but don't push,
        #          "push" = push mapping anyway (useful for some auth flows)
        if radiusstopaction == "clear":
            logger.info("Processing RADIUS stop messages: Clearing from firewalls")
            for ip, user_info in list(ipanduserdict.items()):
                if user_info["status"] == "stop":
                    removelist.append(ip)
                    logger.info(f"Clearing IP: {ip}, User: {user_info['username']}")
                    self.clear_uids(targets, ip)

        elif radiusstopaction == "ignore":
            logger.info("Ignoring RADIUS stop messages")
            for ip, user_info in list(ipanduserdict.items()):
                if user_info["status"] == "stop":
                    logger.info(f"Ignoring IP: {ip}, User: {user_info['username']}")
                    removelist.append(ip)

        elif radiusstopaction == "push":
            logger.info("Pushing RADIUS stop messages")

        # Remove entries marked for removal
        for ip in removelist:
            del ipanduserdict[ip]

        # Apply munge rules if configured
        if tomunge and mungeconfig and self.dpr:
            modipanduserdict = {}
            for ip, user_info in ipanduserdict.items():
                try:
                    newuname = self.dpr.munge([user_info["username"]], mungeconfig)[0]
                    status = user_info["status"]
                    modipanduserdict[ip] = {"username": newuname, "status": status}

                    if newuname != user_info["username"]:
                        logger.info(f"Munge modified: {user_info['username']} -> {newuname}")
                except IndexError:
                    logger.info(f"Munge discarded: {user_info['username']}")
        else:
            modipanduserdict = ipanduserdict

        # Format and push to firewalls
        xml_dict = self.xml_formatter_v67(modipanduserdict, targets, userdomain, timeout)
        urldict, xmldict = self.xml_assembler_v67(xml_dict, targets)

        # Log the mappings being sent
        if self.filemgmt:
            self.filemgmt.log_write("normal", f"Preparing to push {len(modipanduserdict)} User-ID mappings")
            for ip, info in modipanduserdict.items():
                uname = info.get('username', 'unknown')
                if userdomain:
                    self.filemgmt.log_write("normal", f"  Mapping: {userdomain}\\{uname} -> {ip}")
                else:
                    self.filemgmt.log_write("normal", f"  Mapping: {uname} -> {ip}")

        # Save XML to disk if configured
        xml_output_path = getattr(self.context.config, 'xml_output_path', None)
        if xml_output_path and os.path.isdir(xml_output_path):
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            for host, xmllist in xmldict.items():
                safe_host = host.replace(":", "_").replace("/", "_")
                for idx, xml_content in enumerate(xmllist, 1):
                    filename = f"uid-push_{safe_host}_{timestamp}_{idx}.xml"
                    filepath = os.path.join(xml_output_path, filename)
                    try:
                        with open(filepath, 'w') as f:
                            f.write(xml_content)
                        if self.filemgmt:
                            self.filemgmt.log_write("normal", f"Saved XML to {filepath}")
                    except IOError as e:
                        if self.filemgmt:
                            self.filemgmt.log_write("normal", f"ERROR: Failed to save XML to {filepath}: {e}")

        for host, urllist in urldict.items():
            numofcalls = len(urllist)
            if self.filemgmt:
                self.filemgmt.log_write("normal", f"Pushing {len(modipanduserdict)} mappings to {host} via {numofcalls} API call(s)")

            for idx, url in enumerate(urllist, 1):
                try:
                    gcontext = self._create_ssl_context()
                    response = urllib.request.urlopen(url, context=gcontext).read().decode('utf-8')

                    if "success" in response:
                        if self.filemgmt:
                            self.filemgmt.log_write("normal", f"SUCCESS: UID push to {host} ({idx}/{numofcalls})")
                        logger.info(f"Successful UID push to {host} ({idx}/{numofcalls})")
                    else:
                        if self.filemgmt:
                            self.filemgmt.log_write("normal", f"WARNING: Unexpected response from {host}: {response[:200]}")
                        logger.warning(f"Unexpected response from {host}: {response[:200]}")

                except urllib.error.HTTPError as e:
                    if self.filemgmt:
                        self.filemgmt.log_write("normal", f"ERROR: HTTP error pushing to {host}: {e}")
                    logger.error(f"HTTP error pushing to {host}: {e}")
                except urllib.error.URLError as e:
                    if self.filemgmt:
                        self.filemgmt.log_write("normal", f"ERROR: URL error pushing to {host}: {e}")
                    logger.error(f"URL error pushing to {host}: {e}")

        # Remove processed log files
        logger.info(f"File removal check: filemgmt={self.filemgmt is not None}, filelist count={len(filelist) if filelist else 0}")
        if self.filemgmt and filelist:
            # Log which files we're about to remove and their existence status
            for f in filelist:
                exists = os.path.isfile(f)
                logger.info(f"File to remove: {f} (exists={exists})")
            logger.info(f"Removing {len(filelist)} processed log files")
            self.filemgmt.remove_files(filelist)
        else:
            if not self.filemgmt:
                logger.warning("filemgmt is None - cannot remove files")
            if not filelist:
                logger.warning("filelist is empty - no files to remove")

    def pull_uids(self, targetlist: Optional[List[Union[FirewallTarget, Dict[str, str]]]] = None) -> Dict[str, str]:
        """
        Pull current User-ID mappings from firewalls

        Args:
            targetlist: List of firewall targets (uses context.targets if not provided)

        Returns:
            Dictionary with hostname:vsys as key and XML response as value
        """
        if targetlist is None:
            targetlist = self.context.targets or []

        encodedcall = urllib.parse.quote_plus("<show><user><ip-user-mapping><all></all></ip-user-mapping></user></show>")
        result = {}

        for target in targetlist:
            hostname = _get_target_attr(target, 'hostname')
            vsys = _get_target_attr(target, 'vsys', '1')
            port = _get_target_attr(target, 'port', '443')
            apikey = _get_target_attr(target, 'api_key') or _get_target_attr(target, 'apikey')

            url = f'https://{hostname}:{port}/api/?key={apikey}&type=op&vsys=vsys{vsys}&cmd={encodedcall}'

            try:
                gcontext = self._create_ssl_context()
                response = urllib.request.urlopen(url, context=gcontext).read().decode('utf-8')

                result[f"{hostname}:vsys{vsys}"] = response
                logger.info(f"Successfully pulled UIDs from {hostname}:vsys{vsys}")

            except Exception as e:
                logger.error(f"Error pulling UIDs from {hostname}:vsys{vsys}: {e}")

        return result

    def clear_uids(
        self,
        targetlist: Optional[List[Union[FirewallTarget, Dict[str, str]]]] = None,
        userip: str = "all"
    ) -> Dict[str, Dict[str, str]]:
        """
        Clear User-ID mappings from firewalls

        Args:
            targetlist: List of firewall targets (uses context.targets if not provided)
            userip: IP address to clear, or 'all' for all mappings

        Returns:
            Dictionary with results from DP and MP cache clears
        """
        if targetlist is None:
            targetlist = self.context.targets or []

        # Palo Alto has two separate User-ID caches that must both be cleared:
        # - user-cache: Data Plane cache (used for traffic forwarding decisions).
        # - user-cache-mp: Management Plane cache (used for reporting/monitoring).
        if userip == "all":
            encodedcall1 = urllib.parse.quote_plus("<clear><user-cache><all></all></user-cache></clear>")
            encodedcall2 = urllib.parse.quote_plus("<clear><user-cache-mp><all></all></user-cache-mp></clear>")
        else:
            encodedcall1 = urllib.parse.quote_plus(f"<clear><user-cache><ip>{userip}</ip></user-cache></clear>")
            encodedcall2 = urllib.parse.quote_plus(f"<clear><user-cache-mp><ip>{userip}</ip></user-cache-mp></clear>")

        result = {}

        for target in targetlist:
            hostname = _get_target_attr(target, 'hostname')
            vsys = _get_target_attr(target, 'vsys', '1')
            port = _get_target_attr(target, 'port', '443')
            apikey = _get_target_attr(target, 'api_key') or _get_target_attr(target, 'apikey')

            url1 = f'https://{hostname}:{port}/api/?key={apikey}&type=op&vsys=vsys{vsys}&cmd={encodedcall1}'
            url2 = f'https://{hostname}:{port}/api/?key={apikey}&type=op&vsys=vsys{vsys}&cmd={encodedcall2}'

            result[f"{hostname}:vsys{vsys}"] = {}

            try:
                gcontext = self._create_ssl_context()
                result1 = urllib.request.urlopen(url1, context=gcontext).read().decode('utf-8')
                result2 = urllib.request.urlopen(url2, context=gcontext).read().decode('utf-8')

                result[f"{hostname}:vsys{vsys}"]["DP-CLEAR"] = result1
                result[f"{hostname}:vsys{vsys}"]["MP-CLEAR"] = result2

            except Exception as e:
                logger.error(f"Error clearing UIDs on {hostname}:vsys{vsys}: {e}")
                result[f"{hostname}:vsys{vsys}"]["DP-CLEAR"] = str(e)
                result[f"{hostname}:vsys{vsys}"]["MP-CLEAR"] = str(e)

        return result


# Legacy compatibility - old class name
# noinspection PyPep8Naming
class palo_alto_firewall_interaction(PaloAltoFirewall):  # noqa: N801
    """Legacy alias for PaloAltoFirewall class"""
    pass
