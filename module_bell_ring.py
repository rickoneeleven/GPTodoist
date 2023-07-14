import os
import json
from datetime import datetime, date
from rich.console import Console

# Converting python datetime object into string
def datetime_converter(o):
    if isinstance(o, datetime):
        return o.__str__()
        
def ring():
    exists = os.path.isfile('j_ring.json')
    if not exists:
        with open('j_ring.json', 'w') as file:
            json.dump([], file)

    now = datetime.now()
    with open('j_ring.json', 'r') as file:
        data = json.load(file)
    data = [datetime.strptime(item, "%Y-%m-%d %H:%M:%S.%f")
            for item in data 
            if datetime.strptime(item, "%Y-%m-%d %H:%M:%S.%f").date() >= date.today()]
    if not any(d.date() == date.today() for d in data):
        data.append(now)
    with open('j_ring.json', 'w') as file:
        json.dump([d.__str__() for d in data], file, default=datetime_converter, indent=2)

def check_if_rang():
    console = Console()
    if not os.path.isfile('j_ring.json'):
        return
    with open('j_ring.json', 'r') as file:
        data = json.load(file)
    data = [datetime.strptime(item, "%Y-%m-%d %H:%M:%S.%f") for item in data if item]
    for time in data:
        if time.date() == date.today():
            console.print(f'+-+-+-+-+-+-+-+-+-+-+-+- BELL RANG AT {time.strftime("%H:%M")} +-+-+-+-+-+-+-+-+-+-+-+-', style="bold underline red")
            print("- eggs")
            print("- cheese")
            print("- oats")
            return