# ~/.bash_logout: executed by bash(1) when login shell exits.

# when leaving the console clear the screen to increase privacy
if [ "$(tmux ls | grep "^main.*")" != "" ]; then
  if [ "$(tmux ls | grep "^main.*(attached)" | wc -l)" -eq 0 ]; then
    tmux kill-session -t main
  # elif [ "$(tmux lsw -tmain | wc -l)" -eq 1 ] && [ "$(tmux lsw -tmain | grep "(1 panes)" | wc -l)" -eq 1 ]; then
  #   tmux kill-session -t main
  fi
fi
if [ "$SHLVL" = 1 ]; then
  [ -x /usr/bin/clear_console ] && /usr/bin/clear_console -q
fi
