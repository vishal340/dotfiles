export ZSH="$HOME/.oh-my-zsh"
ZSH_THEME="robbyrussell"
plugins=(git)

source $ZSH/oh-my-zsh.sh

# _setxkbmap -option 'caps:swapescape'
# 	if [ "$(tmux ls | wc -l)" -eq 0 ]; then
# 		exec tmux new-session -A -s main
# 	elif [ "$(tmux ls | grep -c "^main.*(attached)")" -eq 0 ]; then
# 		exec tmux new-session -A -s main
# 	fi
# fi

bindkey '\e[A' history-beginning-search-backward
bindkey '\e[B' history-beginning-search-forward

set -o vi

alias glog="git log --stat --oneline --graph --decorate --all"

alias e='echo $?'

alias python=python3
alias v='nvim'
export NVIM_APPNAME='nvim'
export MANPAGER='nvim +Man!'
alias r=ranger
alias update="eos-update --nvidia --yay --aur"
alias usb_mount="sudo mount /dev/sda1 /home/usb_drive"
alias usb_unmount="sudo umount /home/usb_drive"

# don't put duplicate lines or lines starting with space in the history.
HISTCONTROL=ignoreboth:erasedups

# some more ls aliases
alias ll='eza -alF'
alias la='eza -A'
alias l='eza -CF'

# Add an "alert" alias for long running commands.  Use like so:
#   sleep 10; alert
alias alert='notify-send --urgency=low -i "$([ $? = 0 ] && echo terminal || echo error)" "$(history|tail -n1|sed -e '\''s/^\s*[0-9]\+\s*//;s/[;&|]\s*alert$//'\'')"'

export NVM_DIR="$HOME/.nvm"
[ -s "/opt/homebrew/opt/nvm/nvm.sh" ] && \. "/opt/homebrew/opt/nvm/nvm.sh"  # This loads nvm
[ -s "/opt/homebrew/opt/nvm/etc/bash_completion.d/nvm" ] && \. "/opt/homebrew/opt/nvm/etc/bash_completion.d/nvm"  # This loads nvm bash_completion

export EDITOR="nvim"

alias c='clear'
. "$HOME/.cargo/env"

export PATH=$PATH:/usr/local/go/bin:$HOME/.local/bin:/opt/homebrew/opt/python@3.12/bin

export SPARK_HOME="$HOME/Downloads/Spark"

alias databricks1='databricks --profile INFOGROUP'
alias databricks2='databricks --profile WORKSPACE'


export VCPKG_ROOT="$HOME/Downloads/vcpkg/"

source ~/.avante_gemini

plugins=(... direnv)
