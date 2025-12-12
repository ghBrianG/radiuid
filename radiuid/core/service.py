#!/usr/bin/env python3
"""
RadiUID Service
Main service loop for RadiUID User-ID processing
"""

import time
from typing import Optional, List

from ..logging_config import get_logger
from ..context import AppContext, get_context
from ..constants import VERSION
from ..ui.interface import UserInterface
from .config_manager import ConfigManager
from .file_manager import FileManager
from .data_processor import DataProcessor
from ..firewall.palo_alto import PaloAltoFirewall


class RadiUIDService:
    """Main RadiUID service for processing RADIUS logs and pushing User-IDs"""

    def __init__(self, context: Optional[AppContext] = None):
        self.context = context or get_context()
        self.logger = get_logger('service')

        # Initialize components
        self.ui = UserInterface()
        self.config_manager = ConfigManager(self.context, self.ui)
        self.file_manager = FileManager(self.context, self.ui)
        self.data_processor = DataProcessor(self.context, self.ui, self.file_manager)
        self.firewall = PaloAltoFirewall(self.context, self.ui, self.file_manager, self.data_processor)

        # Service state
        self.running = False

    def initialize(self) -> None:
        """Initialize the service with configuration and firewall connectivity"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"{timestamp}:   ***********MAIN PROGRAM INITIALIZATION KICKED OFF...***********\n")

        # Log startup
        self.file_manager.log_write(
            "normal",
            f"***********STARTING UP USING RADIUID VERSION {self.ui.color(VERSION, self.ui.green)}***********"
        )

        # Scrub targets for incomplete settings
        self.file_manager.log_write("normal", "***********CHECKING TARGETS FOR INCOMPLETE OR INCORRECT CONFIGS***********")
        self.file_manager.scrub_targets("noisy", "scrub")

        # Log loaded targets
        targets = self.context.targets or []
        if targets:
            target_dicts = [
                {"hostname": t.hostname, "vsys": t.vsys, "username": t.username, "password": t.password}
                for t in targets
            ]
            self.file_manager.log_write("normal", "***********LOADED THE BELOW TARGETS***********")
            table = self.ui.make_table(["hostname", "vsys", "username", "password"], target_dicts)
            self.file_manager.log_write("normal", "\n" + self.ui.indenter("\t\t\t", table))

        # Log initialization warning
        self.file_manager.log_write(
            "normal",
            "***********RADIUID INITIALIZING... IF PROGRAM FAULTS NOW, MAKE SURE YOU SUCCESSFULLY RAN THE INSTALLER ('python radiuid.py install')***********"
        )

        # Connect to firewall and pull API key
        self.file_manager.log_write(
            "normal",
            "***********************************CONNECTING TO PALO ALTO FIREWALL TO EXTRACT THE API KEY...***********************************"
        )
        self.file_manager.log_write(
            "normal",
            "********************IF PROGRAM FREEZES/FAILS RIGHT NOW, THEN THERE IS LIKELY A COMMUNICATION PROBLEM WITH THE FIREWALL********************"
        )

        self.firewall.pull_api_key("noisy", targets)

        # Log successful initialization
        self.file_manager.log_write("normal", "********************SUCCESSFULLY INITIALIZED THE FOLLOWING FIREWALLS********************")
        for idx, target in enumerate(targets, 1):
            self.file_manager.log_write(
                "normal",
                f"{idx}: {self.ui.color(f'{target.hostname}:vsys{target.vsys}', self.ui.green)}"
            )

        self.file_manager.log_write("normal", "*******************************************CONFIG FILE SETTINGS INITIALIZED*******************************************")
        self.file_manager.log_write("normal", "***********************************RADIUID SERVER STARTING WITH INITIALIZED VARIABLES...******************************")

    def run(self) -> None:
        """Run the main service loop"""
        # Load configuration
        self.config_manager.load(mode='noisy')

        # Initialize service
        self.initialize()

        # Start the main loop
        self.running = True
        self._main_loop()

    def _main_loop(self) -> None:
        """Main processing loop"""
        while self.running:
            self._process_once()
            looptime = self.context.config.loop_time
            time.sleep(int(looptime))

    def _process_once(self) -> None:
        """Process one iteration of the service loop"""
        radiuslogpath = self.context.config.radius_log_path

        # If live log processing is enabled, extract new content first
        if self.context.config.live_log_enabled:
            extracted_file = self.file_manager.process_live_log()
            if extracted_file:
                self.file_manager.log_write("normal", f"Extracted new content from live log to {extracted_file}")

        # Get list of log files
        filelist = self.file_manager.list_files(radiuslogpath, mode='noisy')

        if len(filelist) > 0:
            # Parse log files (auto-detects FreeRADIUS vs NPS XML format)
            ipanduserdict = self.data_processor.parse_log_files(filelist)

            # Push User-IDs to firewalls
            self.firewall.push_uids(ipanduserdict, filelist)

    def stop(self) -> None:
        """Stop the service loop"""
        self.running = False
        self.file_manager.log_write("normal", "***********RADIUID SERVICE STOPPING...***********")
