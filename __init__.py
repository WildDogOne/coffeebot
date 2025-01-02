import time
import lvgl as lv
from apps.coffeebot.functions import get_plug_status, enable_plug, disable_plug
from apps.coffeebot.config import smartplug_ip


# App Name
NAME = "Countdown of App"

# LVGL widgets
scr = None
label = None

# Countdown parameters
remainder = 0

app_mgr = None
last_recorded_time = 0
timer = 0
heating = False
consumption_low = 0
boiler_ready = False
brewgroup_ready = False


def get_settings_json():
    return {
        "form": [
            {
                "type": "input",
                "default": str(DEFAULT_REMAINDER),
                "caption": "Countdown Timer Duration(s)",
                "name": "remainder",
                "attributes": {"maxLength": 6, "placeholder": "e.g., 300"},
            }
        ]
    }


def update_label():
    global label, heating, brewgroup_ready, boiler_ready
    if label:
        status = get_plug_status(smartplug_ip)
        # print(status)
        if status["relay"]:
            plug_state = "Enabled"
        else:
            plug_state = "Disabled"
        label.set_text(
            f"Heating: {heating}\nBrewgroup Ready: {brewgroup_ready}\nBoiler Ready:{boiler_ready}\nPower: {status['power']}W\nPlug State: {plug_state}"
        )


def event_handler(event):
    global heating, boiler_ready, brewgroup_ready
    if event.get_code() == lv.EVENT.KEY and event.get_key() == lv.KEY.ENTER:
        status = get_plug_status(smartplug_ip)
        if status["relay"]:
            disable_plug(smartplug_ip)
            heating = False
        else:
            heating = True
            enable_plug(smartplug_ip)
        boiler_ready = False
        brewgroup_ready = False
        update_label()


async def on_boot(apm):
    global app_mgr
    app_mgr = apm


async def on_stop():
    print("on stop")
    global scr
    if scr:
        scr.clean()
        scr.del_async()
        scr = None


async def on_start():
    print("on start")
    global scr, label

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


async def on_running_foreground():
    """Called when the app is active, approximately every 200ms."""
    global heating, consumption_low, brewgroup_ready, boiler_ready, last_recorded_time
    if heating:
        if last_recorded_time == 0:
            last_recorded_time = time.time()
        elapsed_time = time.time() - last_recorded_time
        if elapsed_time > 10 and not boiler_ready:
            elapsed_time = 0
            status = get_plug_status(smartplug_ip)
            if float(status["power"]) < 800:
                consumption_low += 1
            elif consumption_low > 0:
                consumption_low -= 1
            last_recorded_time = time.time()
            if consumption_low == 10:
                boiler_ready = True
        elif elapsed_time > 1200 and not brewgroup_ready:
            brewgroup_ready = True
    update_label()
