#
# To run it:
#
pyadplayer.py -c config.toml -s psw -e 1

#
# Run it remotely via SSH
# Note: Make sure the user you are logging in via ssh as is the same user that is currently logged into display 0
#
ssh -t user@host "DISPLAY=:0 /home/user/mpvplayer/mpvplayer.py -c /home/user/mpvplayer/config.toml -s psw -e 1"

#
# To stop it:
#
ssh -t user@host "killall mpv"
