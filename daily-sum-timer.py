import sys
import wx
import random
import datetime
import json
import yaml

fontface = "Bernard MT Condensed"
fontFactor = 1.0

def alignTimestamp(t, alignMinutes):
    t.minute -= t.minute % alignMinutes
    t.second,t.millisecond = 0,0
    return t

class Window(wx.Frame):
    def __init__(self):
        size = (1024,768)
        wx.Frame.__init__(self,None,title="SUM",size=size)
        self.BackgroundColour = wx.Colour(60,60,60)
        self.WindowStyle = wx.BORDER_NONE
        self.p = Panel(self,size=(size[0]-14,size[1]-20))
        self.DoubleBuffered = True
        self.p.Bind(wx.EVT_MOUSE_EVENTS,self.mouse)
        self.dragPrevPos = None
        self.dragged_ = False

    def over_exit(self, pos):
        exit_pos = self.p.exit_pos
        exit_delta = wx.Point(10,10)
        return wx.Rect(exit_pos - exit_delta, exit_pos + exit_delta).Contains(pos)

    def mouse(self, e):
        pos = e.EventObject.ClientToScreen(e.Position)
        if e.Dragging() and self.dragPrevPos and e.LeftIsDown():
            delta = pos - self.dragPrevPos
            self.Move(self.Position + delta)
            self.dragPrevPos = pos
            self.dragged_ = True
        elif e.ButtonDown(wx.MOUSE_BTN_LEFT):
            self.dragPrevPos = pos
            self.dragged_ = False
            if self.over_exit(e.Position):
                self.p.exit()
        elif e.ButtonUp(wx.MOUSE_BTN_LEFT):
            self.dragPrevPos = None
        elif e.LeftDClick():
            self.p.toggle_pause()
        elif e.RightDClick():
            self.p.exit()
        elif e.Moving():
            hot = self.over_exit(e.Position)
            if hot != self.p.exit_hot:
                self.p.exit_hot = hot
                self.p.Refresh()

def format_sec(sec):
    neg, sec = sec < 0, abs(sec)
    min, sec = divmod(sec, 60)
    if min < 60:
        ret = "%02d:%02d" % (min, sec)
    else:
        hour, min = divmod(min, 60)
        ret = "%d:%02d:%02d" % (hour, min, sec)
    return ("-" + ret) if neg else ret

class Panel(wx.Panel):
    class Timer(wx.Panel):
        def __init__(self, parent, master=None):
            self.parent = parent
            self.master = master or parent
            super().__init__(parent,size=(240,240))
            self.Position = parent.center - self.Size / 2
            self.center = wx.Point(0,0) + self.Size / 2
            self.font = wx.Font(40*fontFactor,wx.SWISS,wx.NORMAL,wx.NORMAL,False,fontface)
            self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
            self.Bind(wx.EVT_PAINT, self.paint)
            self.Bind(wx.EVT_LEFT_DCLICK, lambda e:self.master.toggle_pause())
            self.Bind(wx.EVT_RIGHT_DCLICK, lambda e:self.master.exit())
            self.timer = wx.Timer(self)
            self.Bind(wx.EVT_TIMER, lambda e:self.Refresh(), self.timer)
            self.timer.Start(50)
            self.lastText = ""
            self.popupmenu = wx.Menu()
            self.Bind(wx.EVT_CONTEXT_MENU, self.onShowPopup)


        def paint(self, e):
            dc = wx.BufferedPaintDC(self)
            dc.Background = wx.Brush(self.parent.parent.BackgroundColour)

            dc.Clear()

            dc.Font = self.font
            dc.TextForeground = wx.Colour(250,250,0)
            txt = self.format()
            pos = self.center - dc.GetTextExtent(txt) / 2
            dc.DrawText(txt,*pos)

            if not self.master.Topic.topic.Running:
                dc.Font = self.font.Scaled(0.5)
                pos = self.center - dc.GetTextExtent("||") / 2 + wx.Point(0,-60)
                dc.TextForeground = wx.Colour(0,0,0)
                dc.DrawText("||",*pos)

            dc.Pen = wx.Pen(wx.Colour(95,95,95),10)
            dc.Brush = wx.Brush(self.parent.parent.BackgroundColour, wx.TRANSPARENT)
            dc.DrawEllipticArc(self.center-wx.Point(100,100), wx.Size(200,200), 90, 90 - self.arcLength())
            dc.Pen = wx.Pen(wx.Colour(45,45,45),12)
            dc.DrawEllipticArc(self.center-wx.Point(100,100), wx.Size(200,200), 90 - self.arcLength(), 90)

        def format(self):
            if self.master.Topic is None:
                return "00:00"
            return self.master.Topic.topic.ElapsedStr

        def arcLength(self):
            if self.master.Topic is None:
                return 0
            return self.master.Topic.topic.Elapsed % 60 * 6
                
        def update(self, e=None):
            val = self.format()

        class Popup(wx.Menu):
            def __init__(self):
                super().__init__()

        def onShowPopup(self, e, pos=None):
            # pos = wx.GetMousePosition()
            # pos = self.ScreenToClient(pos)

            for m in self.popupmenu.MenuItems:
                self.popupmenu.DestroyItem(m.Id)

            now = wx.DateTime(); now.SetToCurrent()
            def T(dt, align):
                dt = alignTimestamp(wx.DateTime(dt), align)
                return (dt.hour, dt.minute)

            menuitem = self.popupmenu.AppendCheckItem(-1, "Pause")
            menuitem.Check(self.master.Topic.state == "paused")
            self.Bind(wx.EVT_MENU, lambda e:self.master.toggle_pause(), menuitem)

            if self.master.Topic is self.master.agenda[0]:
                times = {
                    T(now, 1),
                    T(now + wx.TimeSpan(0, min=1), 1),
                    T(now - wx.TimeSpan(0, min=5), 5), 
                    T(now - wx.TimeSpan(0, min=10), 5),
                    T(now, 5),
                    T(now, 10),
                    T(now, 15),
                    T(now, 30),
                    T(now, 60),
                    T(now + wx.TimeSpan(0, min=5), 5),
                    T(now + wx.TimeSpan(0, min=10), 10),
                    T(now + wx.TimeSpan(0, min=15), 15),
                    T(now + wx.TimeSpan(0, min=30), 30),
                }
                times = list(times)
                times.sort()

                self.popupmenu.AppendSeparator()
                for t in times:
                    menuitem = self.popupmenu.Append(-1, ("%02d:%02d" % t))
                    self.Bind(wx.EVT_MENU, lambda e,t=t:self.setStartTime(e, t), menuitem)

            self.PopupMenu(self.popupmenu)

        def setStartTime(self, e, t):
            dt = wx.DateTime.Today()
            dt.hour,dt.minute = t
            self.master.ResetTopicStartTime(dt)

    class Agenda(wx.Panel):
        ITEM_FLAGS = wx.EXPAND + wx.RESERVE_SPACE_EVEN_IF_HIDDEN
        def __init__(self, parent, topics):
            super().__init__(parent, size=(100,200))
            self.parent = parent
            #self.scrolled = wx.ScrolledWindow(self, size=self.Size)
            self.grid = wx.BoxSizer(wx.VERTICAL)
            self.SetSizer(self.grid)
            self.topics = topics
            self.items = list(map(lambda t:Panel.TopicItem(self, self.parent, t), topics))
            self.grid.AddMany(map(lambda i:(i, 2, self.ITEM_FLAGS), self.items))
        
        def __getitem__(self, i):
            return self.items[i]
        def __len__(self):
            return len(self.items)
        def IndexOf(self, topic):
            for i in range(len(self.topics)):
                if i == topic or self.topics[i] == topic or self.items[i] == topic:
                    return i
            return None

        def InsertAfter(self, prev_topic, topic_to_add):
            for item in self.items:
                if item.topic == topic_to_add:
                    return item
            item = Panel.TopicItem(self, self.parent, topic_to_add)
            idx = self.IndexOf(prev_topic)
            if idx != None:
                self.topics.insert(idx+1, topic_to_add)
                self.items.insert(idx+1, item)
                self.grid.Insert(idx+1, item, 2, self.ITEM_FLAGS)
                self.update()
                return item
            return None
        def Remove(self, item):
            idx = self.IndexOf(item)
            self.topics.pop(idx)
            self.grid.Remove(idx)
            self.items.pop(idx).Destroy()
            self.update()

        def Relocate(self, item, new_index):
            old_index = self.IndexOf(item)
            item = self.items[old_index]
            self.topics.insert(new_index, self.topics.pop(old_index))
            self.items.insert(new_index, self.items.pop(old_index))
            self.grid.Detach(old_index)
            self.grid.Insert(new_index, item, 2, self.ITEM_FLAGS)
            self.update()
    
        def update(self):
            self.grid.Layout()
            oldWidth = self.Size.Width
            self.Fit()
            self.Size = (oldWidth, self.Size.Height)

    class TopicItem(wx.Panel):
        inactive_color = wx.Colour(100,100,100)
        nextup_color = wx.Colour(200,200,200)
        active_color = wx.Colour(240,240,0)
        missing_color = wx.Colour(40,40,40)
        def __init__(self, parent, master, topic):
            super().__init__(parent)
            self.master = master
            self.topic = topic

            self.Sizer = wx.BoxSizer(wx.VERTICAL)
            self.hSizer = wx.BoxSizer(wx.HORIZONTAL)
            pad = 6
            self.Sizer.AddSpacer(pad)
            self.Sizer.Add(self.hSizer, 1, wx.EXPAND)
            self.Sizer.AddSpacer(pad)

            self.strike_font = self.font.Strikethrough()
            item_parent = self

            self.hSizer.AddSpacer(4)
            self.prefix = wx.StaticText(item_parent, -1, "")
            self.prefix.ForegroundColour = self.nextup_color
            self.prefix.Font = self.font
            self.prefix.Bind(wx.EVT_MOUSE_EVENTS, self.mouse)
            self.hSizer.Add(self.prefix, 0)

            self.hSizer.AddStretchSpacer()

            style = wx.CENTER + wx.ALIGN_LEFT + wx.ST_ELLIPSIZE_END
            self.item = wx.StaticText(item_parent, -1, self.name, style = style)
            self.item.ForegroundColour = self.inactive_color
            self.item.Font = self.font
            self.item.Bind(wx.EVT_MOUSE_EVENTS, self.mouse)
            self.hSizer.Add(self.item, 0)

            self.hSizer.AddStretchSpacer()
            self.hSizer.AddSpacer(4)

            self.time = wx.StaticText(item_parent, -1, "", style=wx.ALIGN_LEFT)
            self.time.ForegroundColour = self.inactive_color
            self.time.Font = self.font
            self.time.Bind(wx.EVT_MOUSE_EVENTS, self.mouse)
            self.hSizer.Add(self.time, 0)
            self.hSizer.AddSpacer(8)

            self.Layout()
            self.hSizer.Layout()

            self.popupmenu = wx.Menu()
            menuitem = self.popupmenu.Append(-1, "Shuffle")
            self.Bind(wx.EVT_MENU, self.shuffle, menuitem)
            menuitem = self.popupmenu.Append(-1, "Activate/pause (Dblclick)")
            self.Bind(wx.EVT_MENU, self.activate_or_pause, menuitem)
            menuitem = self.popupmenu.Append(-1, "Toggle demo/update")
            self.Bind(wx.EVT_MENU, self.toggle_demo, menuitem)
            menuitem = self.popupmenu.Append(-1, "Add &QA (Ctrl-Dblclick)")
            self.Bind(wx.EVT_MENU, self.add_qa, menuitem)
            menuitem = self.popupmenu.Append(-1, "Toggle missing/&Remove (Shift-click)")
            self.Bind(wx.EVT_MENU, self.set_missing_del, menuitem)
            #
            self.Bind(wx.EVT_CONTEXT_MENU, self.OnShowPopup)
            self.item.Bind(wx.EVT_CONTEXT_MENU, self.OnShowPopup)            
            
            self.Bind(wx.EVT_MOUSE_EVENTS, self.mouse)
            self.Bind(wx.EVT_MOUSE_CAPTURE_LOST, self.captureLost)

            self.Bind(wx.EVT_PAINT, self.paint)

            #self.next = None
            self._state = "inactive"
            self.drag = False

            self.BorderPen = wx.Pen(wx.Colour(130,130,130),1)
            self.BorderPenDrag = wx.Pen(wx.Colour(230,130,0),1)
            self.LightBrush = wx.Brush(wx.Colour(65,65,65))
            self.TransparentBrush = wx.Brush(self.BackgroundColour, wx.TRANSPARENT)

        def paint(self, e):
            dc = wx.PaintDC(self)
            pad = self.Sizer.GetItem(0).Size.Height - 2
            if self.drag:
                dc.Pen = self.BorderPen #Drag
                dc.Brush = self.LightBrush
                dc.DrawRectangle(self.delta.x,self.delta.y,*(self.Size-(2,2*pad)))
            else:
                dc.Pen = self.BorderPen
                dc.Brush = self.TransparentBrush
                dc.DrawRectangle(0,pad,*(self.Size-(2,2*pad)))
        @property
        def name(self):
            return self.topic.Name
        @property
        def title(self):
            return self.topic.Title
        @property
        def font(self):
            return self.master.grid_font
        def update(self):
            if self.time:
                self.time.LabelText = self.topic.ElapsedStr
                self.hSizer.Layout()
        
        def OnShowPopup(self, e, pos=None):
            pos = wx.GetMousePosition()
            pos = self.ScreenToClient(pos)
            self.PopupMenu(self.popupmenu, pos)

        @property
        def state(self):
            return self._state
        @state.setter
        def state(self, state):
            if self._state != state:
                if self._state == "missing":
                    self.item.Font = self.font
                    self.time.Font = self.font
                self._state = state
                if state == "inactive":
                    self.prefix.LabelText = ""
                    self.item.ForegroundColour = self.inactive_color
                    self.time.ForegroundColour = self.inactive_color
                    if self.topic.Elapsed < 1:
                        self.time.LabelText = ""
                elif state == "active" or state == "paused":
                    self.prefix.LabelText = ""
                    self.item.ForegroundColour = self.active_color
                    self.time.ForegroundColour = self.active_color
                elif state == "nextup":
                    self.prefix.LabelText = "Next up:"
                    self.item.ForegroundColour = self.nextup_color
                    self.time.ForegroundColour = self.inactive_color
                elif state == "missing":
                    self.prefix.LabelText = ""
                    self.item.Font = self.strike_font
                    self.time.Font = self.strike_font
                    self.item.ForegroundColour = self.missing_color
                    self.time.ForegroundColour = self.missing_color
                    if self.topic.Elapsed < 1:
                        self.time.LabelText = ""

                if state == "active":
                    self.topic.Start()
                else:
                    self.topic.Stop()

                self.hSizer.Layout()
                self.item.Refresh()
                self.time.Refresh()
                self.Layout()
                self.master.agenda.Layout()
        def UpdateFont(self):
            self.item.Font = self.font
            self.prefix.Font = self.font
            self.time.Font = self.font
            self.item.InvalidateBestSize()
            self.Size = (0,0)
            self.item.Fit()
            self.prefix.InvalidateBestSize()
            self.prefix.Fit()
            self.time.InvalidateBestSize()
            self.time.Fit()
            self.hSizer.Layout()
            self.Sizer.Layout()
            self.prefix.Refresh()
            self.item.Refresh()
            self.time.Refresh()
            self.master.Refresh()
            oldWidth = self.Size.Width
            self.Fit()
            self.Size = (oldWidth, self.Size.Height)

        def captureLost(self, e):
            self.drag = False
            self.master.Refresh()

        def mouse(self, e):
            pos = e.EventObject.ClientToScreen(e.Position)
            if e.Dragging() and e.LeftIsDown():
                agenda = self.master.agenda
                grid = agenda.grid
                if not self.drag:
                    self.CaptureMouse()
                    self.delta = wx.Point(0,2)
                else:
                    self.delta.x = sorted((-22,self.delta.x+pos.x-self.drag.x,22))[1]
                    self.delta.y = sorted((-22,self.delta.y+pos.y-self.drag.y,22))[1]
                self.drag = pos
                gpos = agenda.ScreenToClient(pos)
                above,below,idx = 0,0,0
                sizerItem = None
                for i,c in enumerate(grid.Children):
                    cpos = c.Position.y
                    if sizerItem is None:
                        cpos += c.Size.Height - 10
                    else:
                        cpos += 10
                    if c.Window is self:
                        idx = i
                        sizerItem = c
                    elif gpos.y < cpos:
                        above += 1
                    elif gpos.y > cpos:
                        below += 1
                moveby = below - idx
                if moveby != 0:
                    moveto = idx + moveby
                    s = self.Size
                    self.master.relocate_topic(self, moveto)
                    self.delta.y = -self.delta.y
                self.item.ForegroundColour = wx.Colour(135,125,105)
                self.Refresh()
            elif e.LeftDClick():
                if e.ControlDown():
                    self.add_qa()
                elif self.master.Topic is self:
                    self.master.toggle_pause()
                else:
                    self.master.set_topic(self.topic)
            elif e.LeftUp() and self.drag:
                self.master.dragging = None
                self.drag = False
                self.ReleaseMouse()
                state = self._state
                self._state = ""
                self.state = state
                self.master.Refresh()
            elif e.LeftUp() and e.ShiftDown():
                self.set_missing_del()
            elif e.RightUp():
                self.OnShowPopup(e)
            elif e.WheelRotation != 0:
                # transfer time between previous topic and this topic
                if e.ControlDown():
                    n = e.WheelRotation//e.WheelDelta
                    a = self.master.agenda
                    curIndex = a.IndexOf(self.topic)
                    if curIndex > 0:
                        prev = a[curIndex-1]
                        if prev.topic.Elapsed + n >= 0 and self.topic.Elapsed - n >= 0:
                            prev.topic.Adjust(n)
                            self.topic.Adjust(-n)
                            prev.update()
                            self.update()

        def activate_or_pause(self, e=None):
            if self.master.Topic is self:
                self.master.toggle_pause()
            else:
                self.master.set_topic(self.topic)
        def set_missing_del(self, e=None):
            if self.topic.transient:
                self.master.remove_topic(self)
            else:
                self.master.set_missing(self)
        def add_qa(self, e=None):
            follow_up = self.topic.FollowUp()
            if follow_up:
                t = self.master.insert_topic(self, follow_up)
                if self.master.Topic == self:
                    self.master.set_topic(t.topic)
        def toggle_demo(self, e=None):
            self.topic.ToggleDemo()
            self.item.SetLabel(self.topic.Name)
            self.item.InvalidateBestSize()
            self.item.Fit()
            self.hSizer.Layout()
            self.Layout()
            if self.master.Topic == self:
                self.master.set_title(self.topic.Title)
        def shuffle(self, e=None):
            self.master.shuffle()


    
    def __init__(self, parent, size):
        self.parent = parent
        self.size = size
        super().__init__(parent,size=size)
        self.exit_pos = wx.Point(self.Size.x - 10, 20)
        self.exit_hot = False

        self.center = wx.Point(500,360)
        self.wtitle_text = "Stand-up Timer v1.0"
        self.grid_font = wx.Font(16*fontFactor,wx.SWISS,wx.NORMAL,wx.NORMAL,False,fontface)

        self.title_center = self.center + wx.Point(0, -170)
        self.title = wx.StaticText(self,-1,"...",pos=self.title_center,style=wx.ALIGN_CENTRE_HORIZONTAL)
        self.title.Font = wx.Font(28*fontFactor,wx.SWISS,wx.NORMAL,wx.NORMAL,False,fontface)
        self.title.ForegroundColour = wx.Colour(240, 240, 0)

        self.time = Panel.Timer(self)

        self.agenda = Panel.Agenda(self, topics)
        self.agenda.Rect = (40,120,120,0)

        self.topic_idx = 0
        self.nextup_idx = None

        self.set_topic(self.agenda[0])

        prev15MinBoundary = wx.DateTime()
        prev15MinBoundary.SetToCurrent()
        prev15MinBoundary += wx.TimeSpan(0, min=2)
        alignTimestamp(prev15MinBoundary, 15)
        self.ResetTopicStartTime(prev15MinBoundary)
        self.Topic.topic.Running = True

        self.agenda.grid.Fit(self.agenda)
        self.agenda.Layout()
        self.agenda.Size = (200, self.agenda.Size.Height)

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.update_time, self.timer)
        self.timer.Start(250)

        self.Bind(wx.EVT_PAINT, self.onPaint)

    def ResetTopicStartTime(self, t):
        running = self.Topic.topic.Running
        now = wx.DateTime()
        now.SetToCurrent()
        dt = now.Subtract(t)
        self.Topic.topic.Reset(dt.GetSeconds())
        self.Topic.topic.Running = running

    @property
    def Topic(self):
        return self.agenda[self.topic_idx]

    @property
    def NextUp(self):
        if self.nextup_idx is None:
            return None
        return self.agenda[self.nextup_idx]

    def update_time(self, e=None):
        self.time.update()
        if self.Topic:
            self.Topic.update()

    def insert_topic(self, topic_before, new_topic):
        new_topic_item = self.agenda.InsertAfter(topic_before, new_topic)
        i = self.agenda.IndexOf(new_topic_item)
        if i+1 <= self.topic_idx:
            self.topic_idx += 1
        if self.nextup_idx and i+1 <= self.nextup_idx:
            self.nextup_idx += 1
        while True:
            y = (self.Size.Height-30) / 2 + 30 - self.agenda.Size.Height / 2
            if y + self.agenda.Size.Height >= self.Size.Height:
                y = self.Size.Height - self.agenda.Size.Height
            if y <= 30:
                oldWidth = self.agenda.Size.Width
                print(self.agenda.Position.y,self.agenda.Position.y+self.agenda.Size.Height,self.Size.Height)
                self.grid_font.MakeSmaller()
                for t in self.agenda.items:
                    t.UpdateFont()
                self.agenda.grid.Fit(self.agenda)
                self.agenda.Layout()
                self.agenda.Size = (oldWidth, self.agenda.Size.Height)
                print(self.agenda.Position.y,self.agenda.Position.y+self.agenda.Size.Height,self.Size.Height)
            else:
                break
        if y < self.agenda.Position.y:
            self.agenda.Move(self.agenda.Position.x, y)
        return new_topic_item

    def relocate_topic(self, item, new_index):
        self.clear_nextup()
        active_item = self.Topic
        self.agenda.Relocate(item, new_index)
        self.topic_idx = self.agenda.IndexOf(active_item)
        self.find_nextup()

    def remove_topic(self, topic):
        i = self.agenda.IndexOf(topic)
        if i != None:
            ti = self.agenda[i]
            if ti.state == "active":
                ti.state = "inactive"
            self.agenda.Remove(i)
            if self.topic_idx == i:
                self.topic_idx = len(self.agenda)-1
            elif self.topic_idx > i:
                self.topic_idx -= 1                    
            if self.nextup_idx == i:
                self.nextup_idx = None
            elif self.nextup_idx > i:
                self.nextup_idx -= 1
            self.set_topic(self.Topic.topic)

    def set_topic(self, topic):
        self.clear_nextup()
        if self.Topic:
            self.Topic.state = "inactive"
        i = self.agenda.IndexOf(topic)
        if i != None:
            self.topic_idx = i
            self.set_title(self.Topic.title)
            self.Topic.state = "active"
        self.find_nextup()

    def clear_nextup(self):
        for t in self.agenda:
            if t.state == "nextup":
                t.state = "inactive"
        self.nextup_idx = None

    def find_nextup(self):
        num_topics = len(self.agenda)
        for i in range(num_topics):
            tidx = (self.topic_idx + 1 + i) % num_topics
            t = self.agenda[tidx]
            if t.state == "inactive" and t.topic.Elapsed < 5:
                self.nextup_idx = tidx
                break
        if self.NextUp:
            self.NextUp.state = "nextup"

    def set_missing(self, topic):
        i = self.agenda.IndexOf(topic)
        if i != None:
            itopic = self.agenda[i]
            if itopic.state != "missing":
                old_state = itopic.state
                itopic.state = "missing"
                if old_state == "nextup":
                    self.find_nextup()
            else:
                itopic.state = "inactive"

    def toggle_pause(self):
        if self.Topic.state == "active":
            self.Topic.state = "paused"
        else:
            self.Topic.state = "active"
        
    def set_title(self, title):
        self.title.LabelText = title
        self.title.Position = self.title_center - wx.Point(self.title.Size.Width/2, 0)
        self.title.Update()

    def shuffle(self):
        transpose = list(range(len(self.agenda)))
        transpose[1:-1] = random.sample(transpose[1:-1],k=len(transpose[1:-1]))
        items = list(self.agenda.items)
        for i,ii in enumerate(transpose):
            self.relocate_topic(items[ii],i)
        print(transpose)

    def exit(self, e=None):
        # machine-readable (raw seconds)
        out = { c: [] for c in map(lambda t:t.Category, self.agenda.topics) }
        # human-readable (minutes:seconds)
        out_h = { c: [] for c in map(lambda t:t.Category, self.agenda.topics) }
        for c in list(out.keys()):
            for t in self.agenda.items:
                seconds = int(t.topic.Elapsed)
                if t.topic.Category == c and t.state != "missing" and seconds >= 1:
                    out[c].append({t.topic.Title: t.topic.Elapsed })
                    out_h[c].append({t.topic.Title: "%d:%02d" % divmod(seconds, 60) })
            if len(out[c]) == 0:
                del out[c], out_h[c]
        today = datetime.datetime.today().strftime('%Y-%m-%d')
        print("###### SUM %s ######" % today)
        print(yaml.dump(out_h))
        try:
            with open("SUM %s.yaml" % today, "a") as outf:
                print("###### SUM %s ######" % today, file=outf)
                yaml.dump(out, outf)
        except OSError as e:
            print(e)
        #print(json.dumps(out))
        sys.exit()

    def onPaint(self, e):
        dc = wx.PaintDC(self)

        dc.Pen = wx.Pen("BLACK", 0, wx.PENSTYLE_TRANSPARENT)
        #dc.Brush = wx.Brush(wx.Colour(55,55,55))
        dc.Brush = wx.TRANSPARENT_BRUSH
        #dc.DrawRectangle(4,4,self.Size.Width-8,32)

        gc = wx.GraphicsContext.Create(dc)
        gc.SetBrush(gc.CreateLinearGradientBrush(0, 0, self.Size.Width/2, 0, wx.Colour(55,55,55), self.parent.BackgroundColour))
        gc.DrawRoundedRectangle(4,4,self.Size.Width/2-4,32,4)
        wx.GraphicsContext.Flush(gc)

        dc.TextForeground = wx.Colour(70,70,70)
        dc.Font = self.grid_font
        dc.DrawText(self.wtitle_text, 10, 7)

        if self.exit_hot:
            dc.Pen = wx.Pen(wx.Colour(130,30,30),1)
        else:
            dc.Pen = wx.Pen(wx.Colour(0,0,0),1)
        #dc.Brush = wx.Brush(self.parent.BackgroundColour)
        p = self.exit_pos
        dc.DrawCircle(p,8)
        dc.DrawLine(p,p+wx.Point(6,6))
        dc.DrawLine(p,p+wx.Point(-6,6))
        dc.DrawLine(p,p-wx.Point(6,6))
        dc.DrawLine(p,p-wx.Point(-6,6))

        dc.Pen = wx.Pen(wx.Colour(255,255,255), 1, wx.PENSTYLE_SOLID)
        dc.Brush = wx.Brush(wx.Colour(255,255,255), wx.BRUSHSTYLE_TRANSPARENT)

class Topic(object):
    def __init__(self, title, category="Misc"):
        self.Title = title
        self.Name = title
        self.Category = category
        self._running = False
        self.stopwatch = wx.StopWatch()
        self.stopwatch.Pause()
        self.transient = False
        self.adjustment = 0
    
    def Reset(self, seconds=0):
        self.adjustment = 0
        self.stopwatch.Start(milliseconds=seconds*1000)
        self.stopwatch.Pause()
        self._running = False

    def Adjust(self, seconds):
        self.adjustment += seconds

    @property 
    def Running(self):
        return self._running

    @Running.setter
    def Running(self, value):
        if value == self._running:
            return
        if value:
            self.Start()
        else:
            self.Stop()

    @property 
    def Elapsed(self):
        return int(self.stopwatch.Time() / 1000.) + self.adjustment

    @Elapsed.setter
    def Elapsed(self, value):
        self.stopwatch.Start(value * 1000)
        if not self._running:
            self.stopwatch.Pause()

    @property
    def ElapsedStr(self):
        return format_sec(self.Elapsed)

    def Start(self):
        if not self._running:
            self._running = True
            self.stopwatch.Resume()

    def Stop(self):
        if self._running:
            self._running = False
            self.stopwatch.Pause()

    def FollowUp(self):
        return None
    def ToggleDemo(self):
        pass

class Speaker(Topic):
    def __init__(self, shortname, fullname=None):
        fullname = fullname or shortname
        super().__init__("%s's update" % shortname, category=shortname)
        self.Name = shortname
        self.shortname = shortname
        self.fullname = fullname
        self.follow_up = None

    def FollowUp(self):
        if not self.follow_up:
            class FollowUp(Topic):
                def __init__(self, speaker):
                    super().__init__("%s's QA" % speaker.shortname, category=speaker.shortname)
                    self.transient = True
            self.follow_up = FollowUp(self)
        return self.follow_up

    def ToggleDemo(self):
        if self.Name.endswith(" demo"):
            self.Name = self.shortname
            self.Title = "%s's update" % self.shortname
        else:
            self.Name = "%s's demo" % self.shortname
            self.Title = self.Name

try:
    with open(r"speakers.yaml") as speakers_file:
        speakers = yaml.safe_load(speakers_file)
except:
    speakers = []

topics = [Topic("Waiting to start")] + \
    list(map(Speaker, speakers)) + \
    [Topic("Free talk")]

if __name__ == "__main__":
    random.seed()
    app = wx.App(False)
    main = Window()
    main.SetSize((1024,668))
    center = wx.Point(wx.DisplaySize()) / 2
    main.Move(center - main.Size / 2 ) #- wx.Point(200,0))
    main.Show()
    app.MainLoop()
