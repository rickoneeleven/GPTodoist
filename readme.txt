pip3 install -r requirements.txt

vim ~/.bashrc
export OPENAI_API_KEY=sk-x
export TODOIST_API_KEY=9x
:wq

python3 main.py
CTRL+C

vim j_todoist_filters.json
  [{"id": 1, "filter": "(no due date | today | overdue) & #Inbox", "isActive": 0, "project_id": ""}, {"id": 1, "filter": "(today | overdue | no due date) & #Team Virtue", "isActive": 1, "project_id": "2294289600"}]
  :wq