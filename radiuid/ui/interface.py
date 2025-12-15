#!/usr/bin/env python3
"""
User Interface Module
Handles terminal output, colors, progress bars, and user interaction
"""

import sys
import time
import re
from typing import List, Dict

from ..constants import Colors


class UserInterface:
    """Handles user interface operations including colored output and input"""

    def __init__(self):
        """Initialize the user interface with ANSI colors"""
        # ANSI Colors for use in CLI and logs
        self.black = Colors.BLACK
        self.red = Colors.RED
        self.green = Colors.GREEN
        self.yellow = Colors.YELLOW
        self.blue = Colors.BLUE
        self.magenta = Colors.MAGENTA
        self.cyan = Colors.CYAN
        self.white = Colors.WHITE

    def color(self, text: str, color: str) -> str:
        """
        Add color to text and automatically reset to black

        Args:
            text: The text to colorize
            color: The ANSI color code to use

        Returns:
            Colorized text with reset to black at the end
        """
        return f"{color}{text}{self.black}"

    def progress(self, message: str, seconds: int) -> None:
        """
        Display a progress bar animation

        Args:
            message: Message to display before the progress bar
            seconds: Total duration in seconds for the progress bar
        """
        timer = float(seconds) / 50
        current_whitespace = 50
        current_blackspace = 0

        while current_whitespace > -1:
            sys.stdout.flush()
            sys.stdout.write(f"\r{message}    [")
            sys.stdout.write("=" * current_blackspace)
            sys.stdout.write(" " * current_whitespace)
            sys.stdout.write("]")
            current_whitespace -= 1
            current_blackspace += 1
            time.sleep(timer)
        print("\n")

    def yesorno(self, question: str) -> str:
        """
        Ask a yes/no question and validate the response

        Args:
            question: The question to ask the user

        Returns:
            'yes' or 'no' based on user input
        """
        answer = 'temp'
        valid_yes = ['yes', 'y']
        valid_no = ['no', 'n']

        while answer.lower() not in valid_yes + valid_no:
            answer = input(self.color(f"----- {question} [yes or no]:", self.cyan))

            if answer.lower() in valid_no:
                return "no"
            elif answer.lower() in valid_yes:
                return "yes"
            else:
                print(self.color("'Yes' or 'No' dude...", self.red))

        return "no"  # Default fallback (should never reach here)

    def make_table(self, columnorder: List[str], tabledata: List[Dict[str, str]]) -> str:
        """
        Create a formatted table from a list of dictionaries

        Args:
            columnorder: Ordered list of column headers
            tabledata: List of dictionaries with data for each row

        Returns:
            Formatted ASCII table as a string
        """
        # Check and fix input type
        if not isinstance(tabledata, list):
            tabledata = [tabledata]

        # Set separators and spacers
        tablewrap = "#"
        headsep = "="
        columnsep = "|"
        columnspace = "  "

        # Generate dictionary with length of longest value in each column
        datalengthdict = {}
        for columnhead in columnorder:
            datalengthdict[columnhead] = len(columnhead)

        for row in tabledata:
            for item in columnorder:
                # Strip ANSI codes for length calculation
                clean_text = re.sub(r'\x1b[^m]*m', "", row[item])
                if len(clean_text) > datalengthdict[item]:
                    datalengthdict[item] = len(clean_text)

        # Calculate total table width
        totalwidth = sum(datalengthdict.values())
        totalwidth += len(columnorder) * len(columnspace) * 2
        totalwidth += len(columnorder) - 1
        totalwidth += 2

        # Build Header
        result = tablewrap * totalwidth + "\n" + tablewrap
        columnqty = len(columnorder)

        for columnhead in columnorder:
            spacing_before = int((datalengthdict[columnhead] - len(columnhead)) / 2)
            spacing_after = int((datalengthdict[columnhead] - len(columnhead)) - spacing_before)
            result += columnspace + " " * spacing_before + columnhead + " " * spacing_after + columnspace

            if columnqty > 1:
                result += columnsep
            columnqty -= 1

        result += tablewrap + "\n" + tablewrap + headsep * (totalwidth - 2) + tablewrap + "\n"

        # Build table contents
        result += tablewrap
        for row in tabledata:
            columnqty = len(columnorder)
            for column in columnorder:
                clean_text = re.sub(r'\x1b[^m]*m', "", row[column])
                spacing_before = int((datalengthdict[column] - len(clean_text)) / 2)
                spacing_after = int((datalengthdict[column] - len(clean_text)) - spacing_before)
                result += columnspace + " " * spacing_before + row[column] + " " * spacing_after + columnspace

                if columnqty == 1:
                    result += tablewrap + "\n" + tablewrap
                else:
                    result += columnsep
                columnqty -= 1

        result += tablewrap * (totalwidth - 1)
        return result

    def indenter(self, indent: str, inputdata: str) -> str:
        """
        Add indentation to all lines in a string

        Args:
            indent: The indent string to prepend
            inputdata: The data to indent

        Returns:
            Indented string
        """
        result = indent + inputdata
        result = result.replace("\n", "\n" + indent)
        return result

    def packetsar(self) -> None:
        """Display the PacketSar ASCII art logo"""
        logo = """
                                ###############################################
                  #                                                 #
                #                                                     #
               #                                                       #
              #                                                         #
              #                            #                            #
              #                          # # #                          #
              #                         #  #  #                         #
              #                            #                            #
              # @@@@  @@  @@@@ @  @ @@@@ @@@@@  @@@@  @@  @@@@          #
              # @  @ @  @ @    @ @  @      @   @     @  @ @  @          #
              # @@@@ @@@@ @    @@   @@@    @   @ @ @ @@@@ @@@@          #
              # @    @  @ @    @ @  @      @       @ @  @ @ @           #
              # @    @  @ @@@@ @  @ @@@@   @   @@@@  @  @ @  @          #
              #                            #                            #
              #                                                         #
              #                      #           #                      #
              #                       #   ###   #                       #
              #    #####################  ###  #####################    #
              #                       #   ###   #                       #
              #                      #           #                      #
              #                                                         #
              #                            #                            #
              #                            #                            #
              #                            #                            #
              #                            #                            #
              #                            #                            #
              #                            #                            #
              #                            #                            #
              #                         #  #  #                         #
              #                          # # #                          #
              #                            #                            #
               #                                                       #
                #                                                     #
                  #                                                 #
                    ###############################################
"""
        print(self.color(logo, self.blue))


# Legacy compatibility - old class name
class user_interface(UserInterface):
    """Legacy alias for UserInterface class"""
    pass
