#!/usr/bin/env python3
"""
Service Commands
Handles all 'service' CLI commands for RadiUID
"""

from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from ..main import CLIRouter


def handle(cli: 'CLIRouter', arguments: str, args_list: List[str]) -> None:
    """Handle service commands"""

    # Service help
    if arguments == "service" or arguments == "service ?":
        _show_help()
        return

    # Individual service helps
    if arguments in ("service radiuid", "service radiuid ?"):
        print("\n - service radiuid start        |     Start the RadiUID system service")
        print(" - service radiuid stop         |     Stop the RadiUID system service")
        print(" - service radiuid restart      |     Restart the RadiUID system service\n")
        return

    if arguments in ("service freeradius", "service freeradius ?"):
        print("\n - service freeradius start        |     Start the FreeRADIUS system service")
        print(" - service freeradius stop         |     Stop the FreeRADIUS system service")
        print(" - service freeradius restart      |     Restart the FreeRADIUS system service\n")
        return

    if arguments in ("service all", "service all ?"):
        print("\n - service all start        |     Start the RadiUID and FreeRADIUS system services")
        print(" - service all stop         |     Stop the RadiUID and FreeRADIUS system services")
        print(" - service all restart      |     Restart the RadiUID and FreeRADIUS system services\n")
        return

    # RadiUID service control
    if arguments == "service radiuid start":
        _service_radiuid_start(cli, arguments)
        return

    if arguments == "service radiuid stop":
        _service_radiuid_stop(cli, arguments)
        return

    if arguments == "service radiuid restart":
        _service_radiuid_restart(cli, arguments)
        return

    # FreeRADIUS service control
    if arguments == "service freeradius start":
        _service_freeradius_start(cli, arguments)
        return

    if arguments == "service freeradius stop":
        _service_freeradius_stop(cli, arguments)
        return

    if arguments == "service freeradius restart":
        _service_freeradius_restart(cli, arguments)
        return

    # Combined service control
    if arguments == "service all start":
        _service_all_start(cli, arguments)
        return

    if arguments == "service all stop":
        _service_all_stop(cli, arguments)
        return

    if arguments == "service all restart":
        _service_all_restart(cli, arguments)
        return


def _show_help() -> None:
    """Show help for service commands"""
    print("\n - Usage: radiuid service (radiuid | freeradius | all) (start | stop | restart)")
    print("----------------------------------------------------------------------------------")
    print("\n - service radiuid (start | stop | restart)      |     Control the RadiUID system service")
    print(" - service freeradius (start | stop | restart)   |     Control the FreeRADIUS system service")
    print(" - service all (start | stop | restart)          |     Control the RadiUID and FreeRADIUS system services\n")


def _get_rad_service_name(cli: 'CLIRouter') -> str:
    """Get the FreeRADIUS service name"""
    return cli.context.system_info.radius_service_name if cli.context.system_info else "radiusd"


def _print_service_result(cli: 'CLIRouter', service_name: str, action: str, result: dict) -> None:
    """Print service control result"""
    status = result.get("status", "")

    if action == "start":
        if status == "running":
            print(cli.ui.color(f"\n\n********** {service_name.upper()} SUCCESSFULLY STARTED UP! **********\n\n", cli.ui.green))
        elif status == "dead":
            print(cli.ui.color(f"\n\n********** {service_name.upper()} STARTUP UNSUCCESSFUL. SOMETHING MUST BE WRONG... **********\n\n", cli.ui.red))
        elif status == "not-found":
            print(cli.ui.color(f"\n\n********** LOOKS LIKE {service_name.upper()} IS NOT INSTALLED. YOU NEED TO INSTALL IT **********\n\n", cli.ui.red))
    elif action == "stop":
        if status == "running":
            print(cli.ui.color(f"\n\n********** {service_name.upper()} IS STILL RUNNING! **********\n\n", cli.ui.red))
        elif status == "dead":
            print(cli.ui.color(f"\n\n********** {service_name.upper()} SHUTDOWN SUCCESSFUL **********\n\n", cli.ui.yellow))
        elif status == "not-found":
            print(cli.ui.color(f"\n\n********** LOOKS LIKE {service_name.upper()} IS NOT INSTALLED. YOU NEED TO INSTALL IT **********\n\n", cli.ui.red))
    elif action == "restart":
        if status == "running":
            print(cli.ui.color(f"\n\n********** {service_name.upper()} SUCCESSFULLY RESTARTED! **********\n\n", cli.ui.green))
        elif status == "dead":
            print(cli.ui.color(f"\n\n********** {service_name.upper()} RESTART UNSUCCESSFUL. SOMETHING MUST BE WRONG... **********\n\n", cli.ui.red))
        elif status == "not-found":
            print(cli.ui.color(f"\n\n********** LOOKS LIKE {service_name.upper()} IS NOT INSTALLED. YOU NEED TO INSTALL IT **********\n\n", cli.ui.red))


def _service_radiuid_start(cli: 'CLIRouter', arguments: str) -> None:
    """Start RadiUID service"""
    cli._log_command(arguments)
    svcctloutput = cli.service_controller.control_service("start", "radiuid")

    header = "########################## STARTING RADIUID ##########################"
    print(cli.ui.color(header, cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    print(svcctloutput.get("after", ""))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))

    _print_service_result(cli, "radiuid", "start", svcctloutput)


def _service_radiuid_stop(cli: 'CLIRouter', arguments: str) -> None:
    """Stop RadiUID service"""
    cli._log_command(arguments)
    print(cli.ui.color("\n***** ARE YOU SURE YOU WANT TO STOP IT?", cli.ui.yellow))
    input(cli.ui.color("\n\nHit CTRL-C to quit. Hit ENTER to continue\n>>>>>", cli.ui.cyan))

    svcctloutput = cli.service_controller.control_service("stop", "radiuid")

    header = "########################## STOPPING RADIUID ##########################"
    print(cli.ui.color(header, cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    print(svcctloutput.get("after", ""))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))

    _print_service_result(cli, "radiuid", "stop", svcctloutput)


def _service_radiuid_restart(cli: 'CLIRouter', arguments: str) -> None:
    """Restart RadiUID service"""
    cli._log_command(arguments)
    print(cli.ui.color("\n***** ARE YOU SURE YOU WANT TO RESTART IT?", cli.ui.yellow))
    input(cli.ui.color("\n\nHit CTRL-C to quit. Hit ENTER to continue\n>>>>>", cli.ui.cyan))

    # Stop
    svcctloutput = cli.service_controller.control_service("stop", "radiuid")
    header = "########################## STOPPING RADIUID ##########################"
    print(cli.ui.color(header, cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    print(svcctloutput.get("after", ""))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    _print_service_result(cli, "radiuid", "stop", svcctloutput)

    # Start
    svcctloutput = cli.service_controller.control_service("start", "radiuid")
    header = "########################## STARTING RADIUID ##########################"
    print(cli.ui.color(header, cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    print(svcctloutput.get("after", ""))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    _print_service_result(cli, "radiuid", "restart", svcctloutput)


def _service_freeradius_start(cli: 'CLIRouter', arguments: str) -> None:
    """Start FreeRADIUS service"""
    cli._log_command(arguments)
    radservicename = _get_rad_service_name(cli)
    svcctloutput = cli.service_controller.control_service("start", radservicename)

    header = "########################## STARTING FREERADIUS ##########################"
    print(cli.ui.color(header, cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    print(svcctloutput.get("after", ""))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))

    _print_service_result(cli, "freeradius", "start", svcctloutput)


def _service_freeradius_stop(cli: 'CLIRouter', arguments: str) -> None:
    """Stop FreeRADIUS service"""
    cli._log_command(arguments)
    print(cli.ui.color("\n***** ARE YOU SURE YOU WANT TO STOP IT?", cli.ui.yellow))
    input(cli.ui.color("\n\nHit CTRL-C to quit. Hit ENTER to continue\n>>>>>", cli.ui.cyan))

    radservicename = _get_rad_service_name(cli)
    svcctloutput = cli.service_controller.control_service("stop", radservicename)

    header = "########################## STOPPING FREERADIUS ##########################"
    print(cli.ui.color(header, cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    print(svcctloutput.get("after", ""))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))

    _print_service_result(cli, "freeradius", "stop", svcctloutput)


def _service_freeradius_restart(cli: 'CLIRouter', arguments: str) -> None:
    """Restart FreeRADIUS service"""
    cli._log_command(arguments)
    print(cli.ui.color("\n***** ARE YOU SURE YOU WANT TO RESTART IT?", cli.ui.yellow))
    input(cli.ui.color("\n\nHit CTRL-C to quit. Hit ENTER to continue\n>>>>>", cli.ui.cyan))

    radservicename = _get_rad_service_name(cli)

    # Stop
    svcctloutput = cli.service_controller.control_service("stop", radservicename)
    header = "########################## STOPPING FREERADIUS ##########################"
    print(cli.ui.color(header, cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    print(svcctloutput.get("after", ""))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    _print_service_result(cli, "freeradius", "stop", svcctloutput)

    # Start
    svcctloutput = cli.service_controller.control_service("start", radservicename)
    header = "########################## STARTING FREERADIUS ##########################"
    print(cli.ui.color(header, cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    print(svcctloutput.get("after", ""))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    _print_service_result(cli, "freeradius", "restart", svcctloutput)


def _service_all_start(cli: 'CLIRouter', arguments: str) -> None:
    """Start both RadiUID and FreeRADIUS services"""
    cli._log_command(arguments)

    # Start RadiUID
    svcctloutput = cli.service_controller.control_service("start", "radiuid")
    header = "########################## STARTING RADIUID ##########################"
    print(cli.ui.color(header, cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    print(svcctloutput.get("after", ""))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    _print_service_result(cli, "radiuid", "start", svcctloutput)

    # Start FreeRADIUS
    radservicename = _get_rad_service_name(cli)
    svcctloutput = cli.service_controller.control_service("start", radservicename)
    header = "########################## STARTING FREERADIUS ##########################"
    print(cli.ui.color(header, cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    print(svcctloutput.get("after", ""))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    _print_service_result(cli, "freeradius", "start", svcctloutput)


def _service_all_stop(cli: 'CLIRouter', arguments: str) -> None:
    """Stop both RadiUID and FreeRADIUS services"""
    cli._log_command(arguments)
    print(cli.ui.color("\n***** ARE YOU SURE YOU WANT TO STOP BOTH SERVICES?", cli.ui.yellow))
    input(cli.ui.color("\n\nHit CTRL-C to quit. Hit ENTER to continue\n>>>>>", cli.ui.cyan))

    # Stop RadiUID
    svcctloutput = cli.service_controller.control_service("stop", "radiuid")
    header = "########################## STOPPING RADIUID ##########################"
    print(cli.ui.color(header, cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    print(svcctloutput.get("after", ""))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    _print_service_result(cli, "radiuid", "stop", svcctloutput)

    # Stop FreeRADIUS
    radservicename = _get_rad_service_name(cli)
    svcctloutput = cli.service_controller.control_service("stop", radservicename)
    header = "########################## STOPPING FREERADIUS ##########################"
    print(cli.ui.color(header, cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    print(svcctloutput.get("after", ""))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    _print_service_result(cli, "freeradius", "stop", svcctloutput)


def _service_all_restart(cli: 'CLIRouter', arguments: str) -> None:
    """Restart both RadiUID and FreeRADIUS services"""
    cli._log_command(arguments)
    print(cli.ui.color("\n***** ARE YOU SURE YOU WANT TO RESTART BOTH SERVICES?", cli.ui.yellow))
    input(cli.ui.color("\n\nHit CTRL-C to quit. Hit ENTER to continue\n>>>>>", cli.ui.cyan))

    radservicename = _get_rad_service_name(cli)

    # Stop RadiUID
    svcctloutput = cli.service_controller.control_service("stop", "radiuid")
    header = "########################## STOPPING RADIUID ##########################"
    print(cli.ui.color(header, cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    print(svcctloutput.get("after", ""))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    _print_service_result(cli, "radiuid", "stop", svcctloutput)

    # Stop FreeRADIUS
    svcctloutput = cli.service_controller.control_service("stop", radservicename)
    header = "########################## STOPPING FREERADIUS ##########################"
    print(cli.ui.color(header, cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    print(svcctloutput.get("after", ""))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    _print_service_result(cli, "freeradius", "stop", svcctloutput)

    # Start RadiUID
    svcctloutput = cli.service_controller.control_service("start", "radiuid")
    header = "########################## STARTING RADIUID ##########################"
    print(cli.ui.color(header, cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    print(svcctloutput.get("after", ""))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    _print_service_result(cli, "radiuid", "restart", svcctloutput)

    # Start FreeRADIUS
    svcctloutput = cli.service_controller.control_service("start", radservicename)
    header = "########################## STARTING FREERADIUS ##########################"
    print(cli.ui.color(header, cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    print(svcctloutput.get("after", ""))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    _print_service_result(cli, "freeradius", "restart", svcctloutput)
