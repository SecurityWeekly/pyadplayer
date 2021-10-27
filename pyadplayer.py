#! /usr/bin/python3
import shutil
import subprocess
import shlex
import time
import argparse
import os
import toml
import validators
import requests
from urllib.parse import urlparse


#
# Check to see if a file exists on the file system
#
def filesyscheck(path):
    if os.path.exists(path):
        print("The file: "+path+" exists!")
        return True
    else:
        #print("ERROR: The file: "+path+" does not exist!")
        return False


#
# Get the command line arguments
#
def get_args():
    # Assign description to the help doc
    parser = argparse.ArgumentParser(
        description='This script plays audio and video, trust me its awesome!')
    # Add arguments
    parser.add_argument(
        '-s', '--show', type=str, help='What show are you doing?', required=True)
    parser.add_argument(
        '-e', '--seg', type=int, help='The episode number', required=True)
    parser.add_argument(
        '-c', '--config', type=str, help='The config file', required=False)
    parser.add_argument(
        '-d', '--download', default=False, action='store_true', help='If a video source is a URL, download it and play locally.', required=False)
    # Array for all arguments passed to script
    args = parser.parse_args()
    # Assign args to variables
    show_name = args.show
    segment_position = args.seg
    config = args.config
    download_vids = args.download
    # Return all variable values
    return show_name,segment_position, config, download_vids


#
# Read the specified values from the configuration file
#
def GetConfig(config, section, value):

    option_value = None
    try:
        option_value = config[section][value]
    except Exception as e:
        print("exception on %s %s!" % section, value)

    return option_value

#
# Match return values from get_arguments() and assign to their respective variables
# The user must tell us the show name and which segment to play videos for
#
config_file = None
show_name, segment_position, config_file, download_vids = get_args()

print("Playing videos for: " + show_name + " Segment: " + str(segment_position))

#
# Read config values from the config.toml file
# If one was not specified by the user, look for a config.toml file in the same directory
#
if config_file is not None:
    try:
        config = toml.load(config_file)
        print("Config file: "+config_file)
    except Exception as e:
        print("ERROR: Unable to find config file: "+str(e))
        exit(0)
else:
    if filesyscheck("config.toml"):
        config = toml.load("config.toml")
    else:
        print("ERROR: Could not find a configuration file.")
        exit(0)

#
# Make sure there is a show section in the config, otherwise abort
#
if "shows" not in config:
    print("ERROR: Missing critical configuration element: shows.")
    exit(0)

#
# Declare some variables
#
tmp_dir = "tmp"
tmp_vid_dir = None
base_dir = ''
show_directory = ''
vid_commercials = []
show_audio_theme = ''
show_audio_subtheme = ''
show_intro_vid = ''
host_montage_vid = ''
net_trailer_vid = ''
blank_vid = ''

#
# Make sure the base directory exists, otherwise abort
#
if filesyscheck(GetConfig(config, 'Dirs', 'base_dir')):
    base_dir = GetConfig(config, 'Dirs', 'base_dir')
else:
    print("ERROR: Path does not exist: base_dir.")
    exit(0)

#
# Check all config file values and assign them to local variables
#
try:
    for show in config['shows']:
        if 'name' in show and show['name'] == show_name:
            if 'directory' in show and filesyscheck(os.path.join(base_dir, show['directory'])):
                show_directory = show['directory']
            else:
                print('ERROR: Unable to find the show directory: Path does not exist or configuration option missing.')
                exit(0)

            if 'show_audio_theme' in show and filesyscheck(os.path.join(base_dir, show_directory, show['show_audio_theme'])):
                show_audio_theme = os.path.join(base_dir, show_directory, show['show_audio_theme'])
            else:
                print("INFO: Not able to set the show_audio_theme.")

            if filesyscheck(os.path.join(base_dir, show_directory, show['show_audio_subtheme'])):
                show_audio_subtheme = os.path.join(base_dir, show_directory, show['show_audio_subtheme'])
            else:
                print("INFO: Not able to set the show_audio_subtheme.")

            if filesyscheck(os.path.join(base_dir, show_directory, show['show_intro_vid'])):
                show_intro_vid = os.path.join(base_dir, show_directory, show['show_intro_vid'])
            else:
                print("INFO: Not able to set the show_intro_vid.")

            if filesyscheck(os.path.join(base_dir, show_directory, show['host_montage_vid'])):
                host_montage_vid = os.path.join(base_dir,show_directory, show['host_montage_vid'])
            else:
                print("INFO: Not able to set the host_montage_vid.")

            for seg in show['segments']:
                if seg['position'] == segment_position:
                    if 'ad' in seg:
                        for ad in seg['ads']:
                            ad_position = ad['position'] - 1
                            vid_commercials.insert(ad_position, ad['video'])
except Exception as e:
    print("Error reading configuration file for given show name: "+str(e))
    exit(0)

#
# See if the user specified a network trailer and blank video
# Check to see if the network trailer and blank videos exist
#
if GetConfig(config, 'Files', 'net_trailer_vid'):
    if filesyscheck(os.path.join(base_dir, GetConfig(config, 'Files', 'net_trailer_vid'))):
        net_trailer_vid = os.path.join(base_dir, GetConfig(config, 'Files', 'net_trailer_vid'))
    else:
        print('ERROR: Unable to find the network trailer video on the file system.')
else:
    print("INFO: Unable to find network trailer video, skipping.")

if GetConfig(config, 'Files', 'blank_vid'):
    if filesyscheck(os.path.join(base_dir, GetConfig(config, 'Files', 'blank_vid'))):
        blank_vid = os.path.join(base_dir, GetConfig(config, 'Files', 'blank_vid'))
    else:
        print('ERROR: Unable to find the blank video on the file system.')
else:
    print("INFO: Unable to find blank video, skipping.")

print("base dir="+base_dir)
print("nettrailer="+net_trailer_vid)
print("blankvid="+blank_vid)

#
# Setup the video player
# TODO: Make sure the command exists on the system first!
#
audio_cmd = GetConfig(config, 'Cmds', 'audio_cmd')
video_cmd = GetConfig(config, 'Cmds', 'video_cmd')

for index, ad in enumerate(vid_commercials):
    if filesyscheck(os.path.join(base_dir, show_directory, ad)):
        vid_commercials[index] = os.path.join(base_dir, show_directory, ad)
        print('INFO: Commercial is a valid file.')
    elif validators.url(ad):
        print('INFO: Commercial is a valid URL.')
        # If the user told us, download the video and play it locally:
        # Hopefully preserving the order...
        if download_vids:
            tmp_vid_dir = os.path.join(base_dir, show_directory, tmp_dir)
            if not filesyscheck(tmp_vid_dir):
                print("Creating directory: " + tmp_vid_dir)
                os.mkdir(tmp_vid_dir)
            ad_file = requests.get(ad)
            ad_url = urlparse(ad)
            ad_filename = os.path.basename(ad_url.path)
            open(os.path.join(tmp_vid_dir, ad_filename), 'wb').write(ad_file.content)
            vid_commercials[index] = os.path.join(tmp_vid_dir, ad_filename)
    else:
        print("ERROR: %s is not a valid URL or file. Exiting...", ad)
        exit(0)

#
# Make a string, space separated, of all the ad video filenames (if there are ads to play):
#
if len(vid_commercials) > 0:
    ad_filenames = ' '.join(map(str, vid_commercials))
else:
    ad_filenames = ''

#
# If we got a video to play at the end, append it:
#
if isinstance(blank_vid, str) and len(blank_vid) > 0:
    ad_filenames = ' '.join((ad_filenames, blank_vid))

if segment_position == 1:
    audio_cmd_raw = ' '.join((audio_cmd, show_audio_theme))
    video_cmd_raw = ' '.join((video_cmd, net_trailer_vid, show_intro_vid, host_montage_vid, ad_filenames))
else:
    audio_cmd_raw = ' '.join((audio_cmd, show_audio_subtheme))
    video_cmd_raw = ' '.join((video_cmd, ad_filenames))

print("Playing the audio with this command: " + audio_cmd_raw)
print("Playing the video with this command: " + video_cmd_raw)

audio_cmd = shlex.split(audio_cmd_raw)
video_cmd = shlex.split(video_cmd_raw)

video_p = subprocess.Popen(video_cmd, stdout=subprocess.PIPE)

if segment_position == 1:
    sleep_time = GetConfig(config, 'Timing', 'first_audio_delay')
    time.sleep(int(sleep_time))

audio_p = subprocess.Popen(audio_cmd, stdout=subprocess.PIPE)

vid_pid = video_p.pid
audio_pid = audio_p.pid

video_p.poll()
video_proc_status = video_p.returncode
print(str(video_proc_status))

audio_p.poll()
audio_proc_status = audio_p.returncode
print(str(audio_proc_status))

while str(video_proc_status) == "None":
    video_p.poll()
    video_proc_status = video_p.returncode
    
print("About to kill video...")
video_p.kill()

while str(audio_proc_status) == "None":
    audio_p.poll()
    audio_proc_status = audio_p.returncode

print("About to kill audio...")
audio_p.kill()

if filesyscheck(tmp_vid_dir):
    shutil.rmtree(tmp_vid_dir)
