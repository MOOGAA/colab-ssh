import random
import string
from subprocess import Popen, PIPE
import shlex
from colab_ssh._command import run_command, run_with_pipe
import os
import time
import requests
import re
from colab_ssh.get_tunnel_config import get_argo_tunnel_config
from .utils.expose_env_variable import expose_env_variable


def launch_cloudflared_ssh(
               password="",
               verbose=False):

    # Kill any ngrok process if running
    os.system("kill $(ps aux | grep 'ngrok' | awk '{print $2}')")

    # Download ngrok
    run_command(
        "wget -q -nc https://bin.equinox.io/c/VdrWdbjqyF/cloudflared-stable-linux-amd64.tgz")
    run_command("tar zxf cloudflared-stable-linux-amd64.tgz")

    # Install the openssh server
    os.system(
        "apt-get -qq update && apt-get -qq install openssh-server > /dev/null")

    # Set the password
    run_with_pipe("echo root:{} | chpasswd".format(password))

    # Configure the openSSH server
    run_command("mkdir -p /var/run/sshd")
    os.system("echo 'PermitRootLogin yes' >> /etc/ssh/sshd_config")
    if password:
        os.system('echo "PasswordAuthentication yes" >> /etc/ssh/sshd_config')

    expose_env_variable("LD_LIBRARY_PATH")
    expose_env_variable("COLAB_TPU_ADDR")
    expose_env_variable("COLAB_GPU")
    expose_env_variable("TBE_CREDS_ADDR")
    expose_env_variable("TF_FORCE_GPU_ALLOW_GROWTH")
    expose_env_variable("TPU_NAME")
    expose_env_variable("XRT_TPU_CONFIG")

    os.system('/usr/sbin/sshd -D &')

    extra_params = []

    # Create tunnel
    proc = Popen(shlex.split(
        f'./cloudflared tunnel --url ssh://localhost:22 --logfile ./cloudflared.log --metrics localhost:45678 {}'.format(
            " ".join(extra_params))
    ), stdout=PIPE)

    time.sleep(4)
    # Get public address
    try:
        info = get_argo_tunnel_config()
    except:
        raise Exception(
            "It looks like something went wrong, please make sure your token is valid")

    if verbose:
        print("DEBUG:", info)

    if info:
        # Extract the host and port
        host = info["domain"]
        port = info["port"]
        print("Successfully running", "{}:{}".format(host, port))
        print("[Optional] You can also connect with VSCode SSH Remote extension using this configuration:")
        print(f'''
	Host google_colab_ssh
		HostName {host}
		User root
		Port {port}
	  ''')
    else:
        print(proc.stdout.readlines())
        raise Exception(
            "It looks like something went wrong, please make sure your token is valid")
    proc.stdout.close()
