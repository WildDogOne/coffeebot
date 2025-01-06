import time
import urequests
import lvgl as lv
import peripherals

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
timer_start_heating = None
timer_start = None
last_status_pull = None
status = None
power_graph = []
power_graph_updated = False
graph_enabled = False
chart = None
series = None


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


def display_graph():
    # Chart help: https://docs.lvgl.io/8.2/widgets/extra/chart.html
    global power_graph, scr, chart, series, power_graph_updated
    if power_graph_updated or not chart:
        print("Updating chart")
        graph_offset = 0
        power_graph_updated = False

        # Create a chart if it doesn't exist
        if not chart:
            chart = lv.chart(lv.scr_act())
            chart.set_size(320 - graph_offset, 240)
            chart.center()
            # chart.align(lv.ALIGN.CENTER, int(graph_offset / 2), 0)
            chart.set_range(lv.chart.AXIS.PRIMARY_Y, 0, 1300)
            # TODO: Figure out how to set the number of ticks
            # LVGL v9.1 uses scale instead of set_axis_tick
            # chart.set_axis_tick(lv.chart.AXIS.PRIMARY_Y, 3, 0, 5, 1, True, graph_offset)
            # chart.set_total_tick_count(lv.chart.AXIS.PRIMARY_Y, 5)
            # Add a data series if it doesn't exist
            series = chart.add_series(lv.color_hex(0xFF0000), lv.chart.AXIS.PRIMARY_Y)

        # Clear the existing data points
        chart.set_point_count(len(power_graph))
        chart.set_all_value(series, 0)

        # Set data points
        for value in power_graph:
            value = int(value)
            chart.set_next_value(series, value)
        chart.refresh()


def set_background_color():
    global scr, heating, graph_enabled, brewgroup_ready, boiler_ready
    # Set Background to Black if graph enabled
    if graph_enabled:
        scr.set_style_bg_color(lv.color_hex(0x00000), lv.PART.MAIN)
    else:
        # Set background color to red if heating and not ready
        if heating and not brewgroup_ready and not boiler_ready:
            scr.set_style_bg_color(lv.color_hex(0xFA8072), lv.PART.MAIN)
        # Set background color to orange if heating and boiler ready but not brewgroup
        if heating and boiler_ready and not brewgroup_ready:
            scr.set_style_bg_color(lv.color_hex(0xFFA500), lv.PART.MAIN)
        # Set background color to green if heating and both boiler and brewgroup ready
        if heating and brewgroup_ready and boiler_ready:
            scr.set_style_bg_color(lv.color_hex(0x98FB98), lv.PART.MAIN)
            scr.set_style_text_color(
                lv.color_hex(0x000000), lv.PART.MAIN
            )  # Set text color to black


def update_label():
    global heating, brewgroup_ready, boiler_ready, timer_start_heating, graph_enabled, chart
    set_background_color()
    if graph_enabled:
        display_graph()
    elif chart:
        print("Deleted chart")
        chart.delete()
        chart = None
    else:
        status = get_status()
        if status["relay"]:
            plug_state = "Enabled"
        else:
            plug_state = "Disabled"
        body = f"Heating: {heating}\n"
        body += f"Boiler Ready:{boiler_ready}\n"
        body += f"Brewgroup Ready: {brewgroup_ready}\n"
        body += f"Power: {status['power']:.0f}W\n"
        body += f"Plug State: {plug_state}\n"
        body += f"Plug IP: {smartplug_ip}\n"
        if (
            isinstance(timer_start_heating, float)
            or isinstance(timer_start_heating, int)
        ) and timer_start_heating > 0:
            current = time.time()
            elapsed_time = current - timer_start_heating
            body += f"Heating Time: {elapsed_time / 60:.0f}.{elapsed_time % 60:.0f}m\n"
        set_label(body)


def event_handler(event):
    global heating, boiler_ready, brewgroup_ready, scr, graph_enabled
    if event.get_code() == lv.EVENT.KEY and event.get_key() == lv.KEY.ENTER:
        status = get_status()
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
    if event.get_code() == lv.EVENT.KEY and (
        event.get_key() == lv.KEY.LEFT or event.get_key() == lv.KEY.RIGHT
    ):
        graph_enabled = not graph_enabled
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


def stop_heating():
    global heating, scr, boiler_ready, brewgroup_ready, timer_start_heating, status
    heating = False
    boiler_ready = False
    brewgroup_ready = False
    timer_start_heating = None
    status = None
    scr.set_style_bg_color(lv.color_hex3(0x000), lv.PART.MAIN)
    scr.set_style_text_color(lv.color_hex3(0xFFF), lv.PART.MAIN)
    update_label()


def start_heating():
    global heating, scr, boiler_ready, brewgroup_ready, timer_start_heating, timer_start, status, power_graph
    power_graph = []
    heating = True
    boiler_ready = False
    brewgroup_ready = False
    status = None
    timer_start_heating = time.time()
    timer_start = time.time()
    update_label()


def get_status():
    global last_status_pull, status, smartplug_ip, power_graph, heating, power_graph_updated
    if not last_status_pull:
        last_status_pull = time.time()
    current = time.time()
    elapsed_time = current - last_status_pull
    if elapsed_time > 15 or not status:
        last_status_pull = time.time()
        status = get_plug_status(smartplug_ip)
        if heating:
            power_graph.append(status["power"])
            power_graph_updated = True
    return status


def check_heating(status):
    global consumption_low, brewgroup_ready, boiler_ready, scr, timer_start
    current = time.time()
    elapsed_time = current - timer_start
    print(elapsed_time)

    if not status["relay"]:
        print("Machine is off?")
        stop_heating()
    elif elapsed_time > 10 and not boiler_ready:
        print("Checking boiler")
        timer_start = time.time()
        if float(status["power"]) < 800:
            consumption_low += 1
        elif consumption_low > 0:
            consumption_low -= 1
        if consumption_low >= 10:
            boiler_ready = True
            buzzbuzz()
    elif elapsed_time > 1200 and not brewgroup_ready:
        timer_start = time.time()
        brewgroup_ready = True
        buzzbuzz()
    elif brewgroup_ready and boiler_ready and elapsed_time > 60:
        timer_start = time.time()
        buzzbuzz()


async def on_running_foreground():
    """Called when the app is active, approximately every 200ms."""
    global heating, smartplug_ip
    status = get_status()
    if status["relay"] and not heating:
        start_heating()
    if heating:
        check_heating(status)
    update_label()


def buzzbuzz():
    if peripherals.buzzer.enabled:
        peripherals.buzzer.acquire()  # Get buzzer control
        peripherals.buzzer.set_freq(400)  # Set buzzer frequency
        peripherals.buzzer.set_volume(100)  # Set buzzer volume
        peripherals.buzzer.release()  # Release buzzer control


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
