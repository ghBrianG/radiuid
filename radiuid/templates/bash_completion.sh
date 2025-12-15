#!/bin/bash

#####  RadiUID Server BASH Complete Script  #####

_radiuid_complete()
{
  local cur prev
  COMPREPLY=()
  cur=${COMP_WORDS[COMP_CWORD]}
  prev=${COMP_WORDS[COMP_CWORD-1]}
  prev2=${COMP_WORDS[COMP_CWORD-2]}
  if [ $COMP_CWORD -eq 1 ]; then
    COMPREPLY=( $(compgen -W "run install show set push tail clear edit service request version" -- $cur) )
  elif [ $COMP_CWORD -eq 2 ]; then
    case "$prev" in
      show)
        COMPREPLY=( $(compgen -W "log acct-logs livelog run config clients status mappings" -- $cur) )
        ;;
      "set")
        COMPREPLY=( $(compgen -W "tlsversion radiusstopaction looptime logfile maxloglines radiuslogpath acctlogcopypath userdomain timeout target client munge livelog" -- $cur) )
        ;;
      push)
        local targets=$(for target in `radiuid targets`; do echo $target ; done)
        COMPREPLY=( $(compgen -W "${targets} all" -- ${cur}) )
        ;;
      "tail")
        COMPREPLY=( $(compgen -W "log" -- $cur) )
        ;;
      "clear")
        COMPREPLY=( $(compgen -W "log acct-logs livelog target mappings client munge" -- $cur) )
        ;;
      edit)
        COMPREPLY=( $(compgen -W "config clients" -- $cur) )
        ;;
      "service")
        COMPREPLY=( $(compgen -W "radiuid freeradius all" -- $cur) )
        ;;
      "request")
        COMPREPLY=( $(compgen -W "xml-update munge-test auto-complete reinstall uninstall freeradius-install set-mount" -- $cur) )
        ;;
      *)
        ;;
    esac
  elif [ $COMP_CWORD -eq 3 ]; then
    case "$prev" in
      config)
        if [ "$prev2" == "show" ]; then
          COMPREPLY=( $(compgen -W "xml set" -- $cur) )
        fi
        ;;
      livelog)
        if [ "$prev2" == "set" ]; then
          COMPREPLY=( $(compgen -W "file tracker enabled" -- $cur) )
        elif [ "$prev2" == "clear" ]; then
          COMPREPLY=( $(compgen -W "tracker" -- $cur) )
        fi
        ;;
      reinstall)
        if [ "$prev2" == "request" ]; then
          COMPREPLY=( $(compgen -W "replace-config keep-config" -- $cur) )
        fi
        ;;
      uninstall)
        if [ "$prev2" == "request" ]; then
          COMPREPLY=( $(compgen -W "keep-config remove-config" -- $cur) )
        fi
        ;;
      set-mount)
        if [ "$prev2" == "request" ]; then
          COMPREPLY=( $(compgen -W "none" -- $cur) )
        fi
        ;;
      client)
        if [ "$prev2" == "clear" ]; then
          local clients=$(for client in `radiuid clients`; do echo $client ; done)
          COMPREPLY=( $(compgen -W "${clients} all" -- ${cur}) )
        elif [ "$prev2" == "set" ]; then
          COMPREPLY=( $(compgen -W "ipv4 ipv6" -- $cur) )
        fi
        ;;
      freeradius|radiuid)
        if [ "$prev2" == "service" ]; then
          COMPREPLY=( $(compgen -W "start stop restart" -- $cur) )
        fi
        ;;
      mappings)
        local targets=$(for target in `radiuid targets`; do echo $target ; done)
        if [ "$prev2" == "show" ]; then
          COMPREPLY=( $(compgen -W "${targets} all consistency" -- ${cur}) )
        elif [ "$prev2" == "clear" ]; then
          COMPREPLY=( $(compgen -W "${targets} all" -- ${cur}) )
        fi
        ;;
      target)
        local targets=$(for target in `radiuid targets`; do echo $target ; done)
        if [ "$prev2" == "set" ]; then
          COMPREPLY=( $(compgen -W "${targets}" -- ${cur}) )
        elif [ "$prev2" == "clear" ]; then
          COMPREPLY=( $(compgen -W "${targets} all" -- ${cur}) )
        fi
        ;;
      all)
        if [ "$prev2" == "service" ]; then
          COMPREPLY=( $(compgen -W "start stop restart" -- $cur) )
        fi
        ;;
      *)
        ;;
    esac
  elif [ $COMP_CWORD -eq 4 ]; then
    case "$prev" in
      enabled)
        if [ "$prev2" == "livelog" ]; then
          COMPREPLY=( $(compgen -W "on off true false" -- $cur) )
        fi
        ;;
      *)
        ;;
    esac
  fi
}

complete -F _radiuid_complete radiuid
