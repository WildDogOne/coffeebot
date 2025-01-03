import time
import time
import urequests
import lvgl as lv

# from apps.coffeebot.config import smartplug_ip

# App Name
NAME = "CoffeeBot"

# LVGL widgets
scr = None
label = None

app_mgr = None
last_recorded_time = 0
timer = 0
heating = False
consumption_low = 0
boiler_ready = False
brewgroup_ready = False
smartplug_ip = None
start_heating = None
start = None


def get_settings_json():
    return {
        "form": [
            {
                "type": "input",
                "default": "192.168.1.1",
                "caption": "Smartplug IP",
                "name": "smartplug_ip",
                "attributes": {"maxLength": 15, "placeholder": "e.g., 192.168.1.1"},
            }
        ]
    }


def update_label():
    global heating, brewgroup_ready, boiler_ready, start_heating
    status = get_plug_status(smartplug_ip)
    if status["relay"]:
        plug_state = "Enabled"
    else:
        plug_state = "Disabled"
    body = f"Heating: {heating}\n"
    body += f"Brewgroup Ready: {brewgroup_ready}\n"
    body += f"Boiler Ready:{boiler_ready}\n"
    body += f"Power: {status['power']:.0f}W\n"
    body += f"Plug State: {plug_state}\n"
    body += f"Plug IP: {smartplug_ip}\n"
    if isinstance(start_heating, float) and start_heating > 0:
        current = time.time()
        elapsed_time = current - start_heating
        body += f"Heating Time: {elapsed_time / 60:.0f}.{elapsed_time % 60:.0f}m\n"
    set_label(body)


def event_handler(event):
    global heating, boiler_ready, brewgroup_ready, scr
    if event.get_code() == lv.EVENT.KEY and event.get_key() == lv.KEY.ENTER:
        status = get_plug_status(smartplug_ip)
        if status["relay"]:
            disable_plug(smartplug_ip)
            stop_heating()
        else:
            heating = True
            print("Enabling Plug")
            enable_plug(smartplug_ip)
            start_heating()
        boiler_ready = False
        brewgroup_ready = False
        update_label()


async def on_boot(apm):
    global app_mgr
    app_mgr = apm


async def on_stop():
    print("on stop")
    disable_plug(smartplug_ip)
    global scr
    if scr:
        scr.clean()
        scr.del_async()
        scr = None


async def on_start():
    print("on start")
    global scr, label, app_mgr, smartplug_ip, heating
    if "smartplug_ip" in app_mgr.config():
        smartplug_ip = app_mgr.config()["smartplug_ip"]

    scr = lv.obj()
    lv.scr_load(scr)

    label = lv.label(scr)
    update_label()
    label.center()

    scr.add_event(event_handler, lv.EVENT.ALL, None)

    group = lv.group_get_default()
    if group:
        group.add_obj(scr)
        lv.group_focus_obj(scr)
        group.set_editing(True)
    status = get_plug_status(smartplug_ip)
    if status["relay"]:
        start_heating()


def stop_heating():
    global heating, scr, boiler_ready, brewgroup_ready
    heating = False
    boiler_ready = False
    brewgroup_ready = False
    scr.set_style_bg_color(lv.color_hex3(0x000), lv.PART.MAIN)
    update_label()


def start_heating():
    global heating, scr, boiler_ready, brewgroup_ready, start_heating, start
    heating = True
    boiler_ready = False
    brewgroup_ready = False
    start_heating = time.time()
    start = time.time()
    scr.set_style_bg_color(lv.color_hex(0xFA8072), lv.PART.MAIN)
    update_label()


async def on_running_foreground():
    """Called when the app is active, approximately every 200ms."""
    global heating, consumption_low, brewgroup_ready, boiler_ready, scr, start_heating, start, smartplug_ip, timer

    if heating:
        current = time.time()
        elapsed_time = current - start
        if elapsed_time > 10 and not boiler_ready:
            print("Check Boiler Temp")
            start = time.time()
            status = get_plug_status(smartplug_ip)
            if not status["relay"]:
                print("Machine is off?")
                stop_heating()
            elif float(status["power"]) < 800:
                consumption_low += 1
            elif consumption_low > 0:
                consumption_low -= 1
            if consumption_low == 10:
                print("Boiler Ready")
                boiler_ready = True
                scr.set_style_bg_color(lv.color_hex(0xFFA500), lv.PART.MAIN)
        elif elapsed_time > 1200 and not brewgroup_ready:
            scr.set_style_bg_color(lv.color_hex(0x98FB98), lv.PART.MAIN)
            print("Brewgroup Ready")
            brewgroup_ready = True

    update_label()


def enable_plug(host):
    if not host:
        set_label("Please configure the app")
    else:
        request = urequests.get(f"http://{host}/relay?state=1")
        if request.status_code == 200:
            print("Turned On")
        else:
            set_label(f"Error enabling plug: {smartplug_ip}")
            return f"Error: {request.status_code}, {request.text}"


def disable_plug(host):
    if not host:
        set_label("Please configure the app")
    else:
        print("Turning off")
        request = urequests.get(f"http://{host}/relay?state=0")
        if request.status_code == 200:
            print("Turned Off")
        else:
            set_label(f"Error disabling plug: {smartplug_ip}")
            return f"Error: {request.status_code}, {request.text}"
        return "Turned Off"


def get_plug_status(host):
    if not host:
        set_label("Please configure the app")
    else:
        try:
            response = urequests.get(f"http://{host}/report")
            if response.status_code == 200:
                return response.json()
            else:
                set_label(f"Error getting Plug State: {smartplug_ip}")
                return {
                    "error": {"status": response.status_code, "text": response.text}
                }
        except Exception as e:
            set_label(f"Failed to connect to plug:\n{smartplug_ip}")


def set_label(text):
    global label
    if label:
        label.set_text(text)
