import time
import urequests

def enable_plug(host):
    status = get_plug_status(host)
    print(f"Enabling: {status['power']} - {status['Ws']}")
    if status["relay"]:
        print("Already on")
    else:
        print("Turning on")
        urequests.get(f"http://{host}/relay?state=1")
    print("Turned on Smartplug")
    return True

def watch_heatup(host):
    go = True
    check_down = 0
    while go:
        time.sleep(10)
        status = get_plug_status(host)
        Ws = float(status["Ws"])
        power = float(status["power"])
        print(f"{Ws} average since last call - {power} w")
        if power < 800:
            check_down += 1
        elif check_down > 0:
            check_down -= 1
        if check_down == 10:
            print("Coffee Maker Ready")
            go = False
        else:
            print(f"Watt Check: {check_down}")
    return True

def disable_plug(host):
    status = get_plug_status(host)["relay"]
    if status:
        print("Turning off")
        urequests.get(f"http://{host}/relay?state=0").status_code
        return "Turned Off"
    else:
        print("Already Off")
        urequests.get(f"http://{host}/relay?state=0").status_code
        return "Already Off"

def get_plug_status(host):
    response = urequests.get(f"http://{host}/report")
    return response.json()