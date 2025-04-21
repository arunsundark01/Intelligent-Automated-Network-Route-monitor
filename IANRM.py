#----------------------------------------- Intelligent Automated Network Route Monitor (IANRM) ------------------------------------

import time
import subprocess
import re
from plyer import notification
from datetime import datetime
from pushbullet import Pushbullet

INPUT_FILE = "targets.txt"
LOG_FILE = "network_monitor.log"

def log(msg):
    with open(LOG_FILE, "a") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{timestamp}] {msg}\n")
    print(f"[{timestamp}] {msg}")

def read_targets(file_path):
    with open(file_path, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]
        packets = int(lines[0])
        targets = lines[1:]
    return packets, targets

def before_check(host):
    try:
        output = subprocess.check_output(["ping", "-n", "2", host], stderr=subprocess.STDOUT, text=True)
    except subprocess.CalledProcessError as e:
        output = e.output

    if "Destination host unreachable" in output:
        return False, output, "Destination host unreachable"
    elif "Request timed out" in output:
        return False, output, "Request timed out"
    elif "Ping request could not find host" in output:
        return False, output, "Could not resolve host"
    return True, output, None

def ping_host(host, packets):
    try:
        output = subprocess.check_output(["ping", "-n", str(packets), host], stderr=subprocess.STDOUT, text=True)
        return True, output
    except subprocess.CalledProcessError as e:
        return False, e.output

def trace_route(host):
    try:
        traceoutput = subprocess.check_output(["tracert", host], stderr=subprocess.STDOUT, text=True)
        return traceoutput
    except subprocess.CalledProcessError as e:
        return e.output

def extract_packet_stats(ping_output):
    match = re.search(r'Packets: Sent = (\d+), Received = (\d+), Lost = (\d+)', ping_output)
    if match:
        sent = int(match.group(1))
        received = int(match.group(2))
        lost = int(match.group(3))
        return sent, received, lost
    return None, None, None

def send_desktop_alert(title, message):
    try:
        notification.notify(
            title=title,
            message=message,
            app_name="Intelligent Network Automated Monitor",
            timeout=10  # seconds
        )
        log("Desktop alert sent.")
    except Exception as e:
        log(f"Failed to send desktop alert: {e}")

def send_pushbullet_alert(title, message):
    try:
        pb = Pushbullet("YOUR_TOKEN")  # Replace with your token
        push = pb.push_note(title, message)
        log("Pushbullet alert sent.")
    except Exception as e:
        log(f"Failed to send Pushbullet alert: {e}")

# -------------------------------------Actual Code starts -------------------------------------------------------------

wait_time = 5 
data_packets, ip_list = read_targets(INPUT_FILE)

for TARGET in ip_list:
    log(f"--- Starting check for {TARGET} ---")

    is_reachable, output, error_type = before_check(TARGET)

    if is_reachable:
        log(f"Initial connectivity check successful to {TARGET}")
    else:
        log(f"Initial check failed: {error_type}")
        log(f"Ping output:\n{output}")
        trace_output = trace_route(TARGET)
        log("Traceroute output:\n" + trace_output + "\n")
        alert_title = f"Initial Check failed: {TARGET}"
        alert_message = "Kindly check on the log messages for full details!"
        send_desktop_alert(alert_title, alert_message)
        send_pushbullet_alert(alert_title, alert_message)
        continue

    is_up, output = ping_host(TARGET, data_packets)

    if is_up:
        log("*"*100 +"\n")
        log(f"Ping successful: {TARGET}")
        sent, received, lost = extract_packet_stats(output)
        log(f"Round Trip Results:\n Packets Sent: {sent}, Packets Received: {received}, Packets Lost: {lost}\n")
        if lost == 0:
            log("No Data packet loss detected!!")
            loss_percentage = (lost / (received + lost)) * 100
            alert_title = f"No Data Packet loss detected: {TARGET}"
            alert_message = f"Loss: {loss_percentage:.2f}% | Sent: {sent}, Lost: {lost}"
            send_desktop_alert(alert_title, alert_message)
            send_pushbullet_alert(alert_title, alert_message)
        if lost > 0:
            log("Checking further which router failed to route the data packet...")
            trace_output = trace_route(TARGET)
            log(f"Tracert output:\n{trace_output}")
        if lost > 1:
            loss_percentage = (lost / (received + lost)) * 100
            log(f"Warning: High packet loss detected! Loss: {loss_percentage:.2f}%")
            alert_title = f"High Packet Loss Alert: {TARGET}"
            alert_message = f"Loss: {loss_percentage:.2f}% | Sent: {sent}, Lost: {lost}"
            send_desktop_alert(alert_title, alert_message)
            send_pushbullet_alert(alert_title, alert_message)
    else:
        log(f"Ping failed: {TARGET}")
        log(f"Full error log:\n{output}")
        trace_output = trace_route(TARGET)
        log("Traceroute output:\n" + trace_output + "\n")

    log("*"*50 + " END OF PING TEST " + "*"*50)
    time.sleep(wait_time)

    #----------------------------------------------- END OF CODE -----------------------------------------------------