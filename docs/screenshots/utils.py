import os
import os.path
import time


def screenshot(client, name):
    time.sleep(1)
    os.makedirs(
        os.path.join("img", "screenshots", os.path.dirname(name)), exist_ok=True
    )
    client.save_screenshot(os.path.join("img", "screenshots", name))
