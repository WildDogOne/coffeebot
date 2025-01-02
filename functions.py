import time
import urequests


def enable_plug(host):
    request = urequests.get(f"http://{host}/relay?state=1")
    if request.status_code == 200:
        print("Turned On")
    else:
        return f"Error: {request.status_code}, {request.text}"


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
    print("Turning off")
    request = urequests.get(f"http://{host}/relay?state=0")
    if request.status_code == 200:
        print("Turned Off")
    else:
        return f"Error: {request.status_code}, {request.text}"
    return "Turned Off"


def get_plug_status(host):
    response = urequests.get(f"http://{host}/report")
    return response.json()
