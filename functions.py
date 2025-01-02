import time
import urequests


def enable_plug(host):
    request = urequests.get(f"http://{host}/relay?state=1")
    if request.status_code == 200:
        print("Turned On")
    else:
        set_label("Error enabling plug")
        return f"Error: {request.status_code}, {request.text}"


def disable_plug(host):
    print("Turning off")
    request = urequests.get(f"http://{host}/relay?state=0")
    if request.status_code == 200:
        print("Turned Off")
    else:
        set_label("Error disabling plug")
        return f"Error: {request.status_code}, {request.text}"
    return "Turned Off"


def get_plug_status(host):
    response = urequests.get(f"http://{host}/report")
    if response.status_code == 200:
        return response.json()
    else:
        set_label("Error getting Plug State")
        return {"error": {"status": response.status_code, "text": response.text}}


def set_label(text):
    global label
    if label:
        label.set_text(text)
