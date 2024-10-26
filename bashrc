HISTSIZE=10000
HISTFILESIZE=10000

# Enable history-completion on Up/Down Key
bind '"\e[A": history-search-backward'
bind '"\e[B": history-search-forward'

# Make local npm-modules executable in terminal
export PATH="./node_modules/.bin:$PATH"
# Make pip installed packages executable in terminal (include `python3 -m site --user-base`/bin)
export PATH="$PATH:$HOME/.local/bin"
# add ~/bin
export PATH="$HOME/bin:$PATH"

alias ..='cd ..'
alias ...='cd ../..'

alias update_keyring='sudo pacman -Sy archlinux-keyring'
alias update='sudo pacman -Syyu'
# https://wiki.archlinux.org/title/Mirrors#Fetching_and_ranking_a_live_mirror_list
update_mirrors() {
  curl -s "https://archlinux.org/mirrorlist/?country=DE&protocol=https&use_mirror_status=on" | sed -e 's/^#Server/Server/' -e '/^#/d' | rankmirrors -n 5 - >/etc/pacman.d/mirrorlist
}
alias i="sudo pacman -S"
alias u="sudo pacman -Rs"
alias chx='chmod +x'
alias remove_orphans='sudo pacman -Rns $(pacman -Qtdq)'

alias ls='ls --color=auto'
alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'

alias ga='git add'
alias gall='git add -A'
alias gs='git status'
alias gl='git pull'
alias gp='git push'
alias gc='git commit -v'
alias gd='git diff'
alias glog="git log --pretty=format:'%C(bold)%h %C(cyan)%cr %C(reset)%C(yellow)%an %C(reset) %s %C(green)%d' --graph --decorate"

prompt() {
  if [ $? -ne 0 ]; then
    PS1="\[\033[33m\][\[\033[1;32m\]\W\[\033[22;33m\]]\[\033[39m\] "
  else
    PS1="[\[\033[1;32m\]\W\[\033[22;39m\]] "
  fi

  if git branch 1>/dev/null 2>&1; then
    PS1="$PS1\[\033[2;32m\]$(git branch --no-color | cut -d' ' -f2)\[\033[22;39m\] "
  fi
}
PROMPT_COMMAND=prompt

alias t='trizen'
