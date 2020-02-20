from datetime import date, datetime, timedelta

import sublime

import sublime_plugin

HTML_STYLE_HEADER = '''<body id="todo-phantom-style">
                         <style>
                             div.due {
                                 background-color: red;
                                 color: white;
                                 padding: 2px;
                                 border-radius: 10px; 
                                 font-family: sans-serif;
                                 font-size: .8rem;
                             }
                             div.tag {
                                 background-color: blue;
                                 color: white;
                                 padding: 2px;
                                 border-radius: 10px; 
                                 font-family: sans-serif;
                                 font-size: .8rem;
                             }
                             div.current {
                                 background-color: lime;
                                 color: black;
                                 padding: 2px;
                                 border-radius: 10px; 
                                 font-family: sans-serif;
                                 font-size: .8rem;
                             }
                         </style>'''
HTML_STYLE_FOOTER = '</body>'

DONE_DIVIDER = '==='
FILE_EXTENSION = 'todo'


class DoneListener(sublime_plugin.EventListener):
    def on_modified(self, view):
        self.style_all(view, view.file_name())

    def on_activated(self, view):
        self.style_all(view, view.file_name())

    def style_all(self, view, file_name):
        if file_name:
            if file_name.split('.')[-1] == FILE_EXTENSION:
                self.tag_phantoms = sublime.PhantomSet(view, 'todo-tags')
                view.erase_phantoms('todo-tags')
                self.style_tags(view.find_all(r'\[.*?\]'))
                self.due_phantoms = sublime.PhantomSet(view, 'todo-due')
                view.erase_phantoms('todo-due')
                self.style_due_today(view)
                self.current_phantoms = sublime.PhantomSet(view, 'todo-current')
                view.erase_phantoms('todo-current')
                self.style_current(view)

    def style_tags(self, tag_regions):
        phantoms = []
        for tag_region in tag_regions:
            html = HTML_STYLE_HEADER +\
                '<div class="tag">&nbsp;tag:</div>' +\
                HTML_STYLE_FOOTER
            p = sublime.Phantom(tag_region,
                                html,
                                sublime.LAYOUT_INLINE)
            phantoms.append(p)
        self.tag_phantoms.update(phantoms)

    def style_due_today(self, view):
        divider = view.find(DONE_DIVIDER, 0)
        due_today_regions = view.find_all(r'\%due \d\d\d\d-\d\d-\d\d')
        html = HTML_STYLE_HEADER +\
            '<div class="due">●</div>' +\
            HTML_STYLE_FOOTER
        phantoms = []
        for due_today_region in due_today_regions:
            if due_today_region.end() < divider.begin():
                date_parts = view.substr(due_today_region).split()[1].split('-')
                due_date = date(int(date_parts[0]), int(date_parts[1]), int(date_parts[2]))
                if due_date <= date.today():
                    p = sublime.Phantom(due_today_region,
                                        html,
                                        sublime.LAYOUT_INLINE)
                    phantoms.append(p)
        self.due_phantoms.update(phantoms)
    
    def style_current(self, view):
        divider = view.find(DONE_DIVIDER, 0)
        current_regions = view.find_all(r'\* .*? \%start \d\d\d\d-\d\d-\d\d')
        html = HTML_STYLE_HEADER +\
            '<div class="current">⇒</div>' +\
            HTML_STYLE_FOOTER
        phantoms = []
        for current_region in current_regions:
            if current_region.end() < divider.begin():
                p = sublime.Phantom(current_region,
                                        html,
                                        sublime.LAYOUT_INLINE)
                phantoms.append(p)
        self.current_phantoms.update(phantoms)


class DonedoneCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        # find divider
        divider = self.view.find(DONE_DIVIDER, 0)
        if divider:
            # move current line past divider
            for region in self.view.sel():
                if region.empty():  # no selection just a cursor
                    line = self.view.line(region)  # region
                    line_done = '\n{l} %done {d}'.format(
                        l=self.view.substr(line),
                        d=datetime.now().strftime('%y-%m-%d %H:%M'))
                    self.view.insert(edit, divider.end(), line_done)
                    x, y = self.view.rowcol(line.b)
                    erase_line = sublime.Region(line.a,
                                                self.view.text_point(x + 1, 0))
                    self.view.erase(edit, erase_line)


class DonedueCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        due = ['today', 'tomorrow', 'next week', 'next month']
        self.view.show_popup_menu(due, self.set_due)

    def set_due(self, idx):
        if idx >= 0:
            self.view.run_command('insert', {"characters": ' %due ' + self.get_due_date(idx)})

    def get_due_date(self, idx):
        due_date = date.today()
        if idx == 1:
            due_date = due_date + timedelta(days=1)
        elif idx == 2:
            due_date = due_date + timedelta(days=7)
        elif idx == 3:
            due_date = due_date + timedelta(days=30)
        return due_date.isoformat()


class DonetagCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        # init
        self.tag_regions = self.view.find_all(r'\[.*?\]')
        # select tag
        self.tags = self.get_tags()
        self.view.show_popup_menu(self.tags, self.add_tag)

    def get_tags(self):
        tags = []
        for tag_region in self.tag_regions:
            tag = self.view.substr(tag_region)
            if tag not in tags:
                tags.append(tag)
        return tags

    def add_tag(self, idx):
        if idx >= 0:
            self.view.run_command('insert', {"characters": ' ' + self.tags[idx]})


class DonenewtagCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        self.view.window().show_input_panel(
            'new tag', '',
            self.on_done, None, None)

    def on_done(self, text):
        self.view.run_command('insert', {"characters": ' [' + text + ']'})


class DonenewtodoCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        eols = []
        for region in self.view.sel():
            eols.append(self.view.line(region).end())
        self.view.sel().clear()
        for eol in eols:
            self.view.sel().add(eol)
        self.view.window().show_input_panel(
            'new todo', '',
            self.on_done, None, None)

    def on_done(self, text):
        self.view.run_command('insert', {"characters": '\n* ' + text})


class DoneshowdueCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        today = date.today().isoformat()
        self.due_today_regions = self.view.find_all(r'\%due ' + today)
        due_today = []
        for due_today_region in self.due_today_regions:
            due_today.append(
                self.view.substr(self.view.line(due_today_region)))
        self.view.sel().clear()
        self.view.window().show_quick_panel(due_today, self.on_done)

    def on_done(self, idx):
        if idx >= 0:
            self.view.sel().add(self.due_today_regions[idx].end())


class DonebegintaskCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        start_date = date.today().isoformat()
        self.view.run_command('insert', {"characters": r' %start ' + start_date})
