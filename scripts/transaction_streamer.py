import random
import requests
import time

while True:

    requests.post(
        "http://localhost:8000/api/internal/event",
        json={
            "source":
            f"A{random.randint(1,500)}",

            "target":
            f"B{random.randint(1,500)}",

            "amount":
            random.randint(
                100,
                100000
            )
        }
    )

    time.sleep(1)
