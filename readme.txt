built on replit, expects secrets:
{
  "OPENAI_API_KEY": "sk-x",
  "TODOIST_API_KEY": "x",
  "OPEN_WEATHER_MAP_API": "x"
}

python repo, pip install requirements.txt - maybe you can use pyproject.toml?

change weather location, search for code: observation = mgr.weather_at_place('Billinge, UK')

use:
  i have replit set to "python3 main.py" when "Run" is pressed
  it starts a console, which is generally a gpt3.5 chatbot
  type "commands" to see what you can do

i commit changes with ./blueberryballs.sh as it formats code and sets some git parameters that you end up repeating on replit