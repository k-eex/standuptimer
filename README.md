# standuptimer

Small app to track time spent during standups.

The idea is to share the app window using Teams or other collaboration software so that everyone is aware where the time was spent.

Features:
  - Assumes that meetings start on 15-minute boundaries. Tracks time before first speaker up to previous 15-minute period start.
  - Tracks time how much each participant spends on their daily update.
  - Instead of update, any participant's time could be counted as longer "demo".
  - Follow-up questions (and possible tangents) are tracked under QA, associated with the person who gave the update.
  - Automatically shuffle the participants (best used before the updates start).
  - Possibility to drag-drop to manually re-order the agenda.
  - Outputs the tracked time in the console and into daily text file (in yaml format).


Prerequisites:

  - Python 3.x (tested with 3.7)
  - pip install wxPython
  - pip install pyyaml

Configuration:

  - Create speakers.yaml in active directory with list of participants/topics. "Waiting for start" and "Free talk" are automatically generated at the beginning and end of agenda, respectively.

```yaml
- Alice
- Bob
- Charlie
```

Running

  - Execute: python daily-sum-timer.python
  - Start sharing your screen (single window sharing preferable)

Using

  - Double click on topic in agenda to activate it
  - Double click in empty area to pause/unpause the timer
  - Ctrl-double click on topic to create QA (if topic was active, this automatically activates the QA)
  - Shift-click to mark topic as inactive (participant missing) or to delete added QA topic
  - Drag topics to rearrange
  - Right-click on topic in agenda to see possible actions
