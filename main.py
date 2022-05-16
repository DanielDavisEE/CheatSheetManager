import tkinter as tk
from tkinter import ttk
from tkinter.filedialog import askopenfilename, asksaveasfilename, askdirectory
from tkinter import messagebox

import os, shutil, json, pyperclip

from pystray import MenuItem as item
import pystray
from PIL import Image, ImageTk

from VerticalScrollFrame import ScrollFrame
#import DragAndDrop
from collections import namedtuple

Tab = namedtuple("Tab", ["children", "widget"])
Button = namedtuple("Button", ["description", "codestring", "widget"])


class DraggableButton(ttk.Button):
    """This class is unused, and in development for a future feature."""
    
    @property
    def description(self):
        return self._description_var.get()
    
    @description.setter
    def description(self, description):
        return self._description_var.set(description)
    
    @property
    def codestring(self):
        return self._codestring_var.get()
    
    @codestring.setter
    def codestring(self, codestring):
        return self._codestring_var.set(codestring)

    def __init__(self, *args, description=None, codestring=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        self._description_var = tk.StringVar(self, value=description, name=f'{button_id} description')
        self._codestring_var = tk.StringVar(self, value=code_string, name=f'{button_id} codestring')
        
        self.canvas = self.label = self.id = None

    def attach(self, canvas, x=10, y=10):
        if canvas is self.canvas:
            self.canvas.coords(self.id, x, y)
            return
        if self.canvas:
            self.detach()
        if not canvas:
            return
        label = tkinter.Button(canvas, text=self.name, command=lambda: print(self.name),
                               borderwidth=2, relief="raised")
        id = canvas.create_window(x, y, window=label, anchor="nw")
        self.canvas = canvas
        self.label = label
        self.id = id
        label.bind("<ButtonPress>", self.press)

    def detach(self):
        canvas = self.canvas
        if not canvas:
            return
        id = self.id
        label = self.label
        self.canvas = self.label = self.id = None
        canvas.delete(id)
        label.destroy()

    def press(self, event):
        if dnd_start(self, event):
            # where the pointer is relative to the label widget:
            self.x_off = event.x
            self.y_off = event.y
            # where the widget is relative to the canvas:
            self.x_orig, self.y_orig = self.canvas.coords(self.id)

    def move(self, event):
        x, y = self.where(self.canvas, event)
        self.canvas.coords(self.id, x, y)

    def putback(self):
        self.canvas.coords(self.id, self.x_orig, self.y_orig)

    def where(self, canvas, event):
        # where the corner of the canvas is relative to the screen:
        x_org = canvas.winfo_rootx()
        y_org = canvas.winfo_rooty()
        # where the pointer is relative to the canvas widget:
        x = event.x_root - x_org
        y = event.y_root - y_org
        # compensate for initial pointer offset
        return x - self.x_off, y - self.y_off

    def dnd_end(self, target, event):
        pass


class EntryPopup():
    
    def __init__(self, window):
        self.popupWindow = tk.Toplevel(window)
        self.popupWindow.grab_set()
        
        # Frame for main body
        self.input_container = ttk.Frame(self.popupWindow)
        self.input_container.pack(side='top', fill='both', expand=True, padx=10, pady=5)

        # Frame for buttons at bottom
        self.button_container = ttk.Frame(self.popupWindow)
        self.button_container.pack(side='top', fill='x', padx=20, pady=5)            
        
    def add_entry(self, label, default=''):
        label_widget = ttk.Label(self.input_container, text=label)
        label_widget.pack(side='top', fill='x', expand=False)
        
        entry_contents = tk.StringVar(self.popupWindow, value=default)
        text_entry = ttk.Entry(self.input_container, textvariable=entry_contents)
        text_entry.pack(side='top', fill='both', expand=False)
        
        return entry_contents
    
    def add_text(self, label, default=''):
        label_widget = ttk.Label(self.input_container, text=label)
        label_widget.pack(side='top', fill='x', expand=False) 
        
        text_entry_frame = ttk.Frame(self.input_container)
        text_entry_frame.pack(side='top', fill='both', expand=True)  
        
        text_entry = tk.Text(text_entry_frame, height=1, width=1)
        text_entry.insert(1.0, default)
        text_entry.pack(side='left', fill='both', expand=True)   
        
        scrollbar = ttk.Scrollbar(text_entry_frame, orient='vertical', command=text_entry.yview)
        scrollbar.pack(side='right', fill='y')
        text_entry['yscrollcommand'] = scrollbar.set 
        
        return text_entry
    
    def add_combobox(self, label, values, state='readonly', default=None):
        label_widget = ttk.Label(self.input_container, text=label)
        label_widget.pack(side='top', fill='x', expand=False)
        
        if default is None:
            default = values[0]
        selected_item = tk.StringVar(self.popupWindow, value=default)
        text_entry = ttk.Combobox(self.input_container,
                                  values=values,
                                  textvariable=selected_item,
                                  state=state)
        text_entry.pack(side='top', fill='both', expand=False)
        
        return selected_item         
    
    def add_buttons(self, button_info):
        buttons = {}
        for name, command in button_info.items():
            button = ttk.Button(self.button_container, text=name, command=command)
            button.pack(side='left', expand=True)
            buttons[name] = button
        return buttons
        
        
    def size_popup(self):
        self.popupWindow.update()
        width, height = self.popupWindow.winfo_width(), self.popupWindow.winfo_height()
        self.popupWindow.minsize(300, height)
        
        
    def destroy(self):
        self.popupWindow.destroy()

        
class CheatSheet:

    def __init__(self, window):
        self._id_count = 0
        self.edit_mode = False

        self.onTop = True
        window.geometry("350x350-50-50")
        window.resizable(False, True)
        window.title("CheatSheet")
        window.protocol('WM_DELETE_WINDOW', self.hide_window)
        window.attributes("-topmost", self.onTop)
        window.option_add('*tearOff', False)
        self.window = window

        self.profile_folder = os.path.join(os.getcwd(), "profiles")
        self.profile = 'default'
        photo = tk.PhotoImage(file="MyTrashcan15.png")
        self.trashcan = photo.subsample(1, 1)          

        menu = tk.Menu(window)
        window.config(menu=menu)

        optionsMenu = tk.Menu(menu)
        menu.add_cascade(label="Options", menu=optionsMenu)
        optionsMenu.add_command(label="Always on top", command=self.toggle_on_top)
        optionsMenu.add_command(label="Exit", command=window.destroy)

        profileMenu = tk.Menu(menu)
        menu.add_cascade(label="Profile", menu=profileMenu)
        profileMenu.add_command(label="New",    command=self.create_profile)
        profileMenu.add_command(label="Select", command=self.select_profile)
        profileMenu.add_command(label="Rename", command=self.rename_profile)
        profileMenu.add_command(label="Import", command=self.import_profile)
        profileMenu.add_command(label="Export", command=self.export_profile)
        
        self.tabs = {}
        self.buttons = {}
        cs_dict = self.load_cheatsheet()        
        self.generate_gui(cs_dict)

        buttonRow = ttk.Frame(window)
        buttonRow.pack(expand=False, fill="x", side="bottom")
        
        buttons = [('Add Item', self.add_item_popup),
                   ('Edit Items', self.edit_items),
                   ('Add Tab', self.create_tab_popup),
                   ('Delete Tab', self.delete_tab_popup),
                   ]
        
        for name, command in buttons:
            button = ttk.Button(buttonRow,
                                text=name,
                                command=command)
            button.pack(expand=True, fill='y', side="left", padx=5, pady=5)

    def toggle_on_top(self):
        self.onTop = not self.onTop
        window.attributes("-topmost", self.onTop)

    def create_profile(self):
        createProfilePopup = EntryPopup(self.window)
        tab_name_var = createProfilePopup.add_entry("New Profile Name")
        
        # submit button
        def submit_action():
            profile = tab_name_var.get()
            fp = os.path.join(self.profile_folder, profile + '.json')
            if not os.path.isfile(fp):
                self.profile = profile
                cs_dict = self.load_cheatsheet()
                self.generate_gui(cs_dict)        
            else:
                messagebox.showerror(title="Invalid Name", message=f"Profile '{profile}' already exists.")
                
            createProfilePopup.destroy()        
        
        createProfilePopup.add_buttons({"Submit": submit_action,
                                        "Cancel": createProfilePopup.destroy})
        createProfilePopup.size_popup()

    def select_profile(self):
        selectProfilePopup = EntryPopup(self.window)
        values = [os.path.splitext(x)[0] for x in os.listdir(self.profile_folder)]
        profile_name_var = selectProfilePopup.add_combobox("Select Profile", values, default=self.profile)
        
        def submit_action():
            self.profile = profile_name_var.get()
            cs_dict = self.load_cheatsheet()
            self.generate_gui(cs_dict)
                
            selectProfilePopup.destroy()        
        
        selectProfilePopup.add_buttons({"Submit": submit_action,
                                        "Cancel": selectProfilePopup.destroy})
        selectProfilePopup.size_popup()

    def rename_profile(self):
        renameProfilePopup = EntryPopup(self.window)
        tab_name_var = renameProfilePopup.add_entry(f"Change '{self.profile}' to")
        
        # submit button
        def submit_action():
            profile_name = tab_name_var.get()
            
            old_name = os.path.join(self.profile_folder, self.profile + '.json')
            new_name = os.path.join(self.profile_folder, profile_name + '.json')
            
            try:
                os.rename(old_name, new_name)
            except FileExistsError:
                messagebox.showerror(title="Invalid Name", message=f"Profile '{profile_name}' already exists.")
                
            self.profile = profile_name
            renameProfilePopup.destroy()      
        
        renameProfilePopup.add_buttons({"Submit": submit_action,
                                        "Cancel": renameProfilePopup.destroy})
        renameProfilePopup.size_popup()

    def import_profile(self):
        profile_fp = askopenfilename(filetypes=[('JSON', '*.json')], defaultextension='.json' )
        if not profile_fp:
            return
        
        filename = os.path.basename(profile_fp)
        profile_name, ext = os.path.splitext(filename)
        self.profile = profile_name
        
        try:
            shutil.copy(profile_fp, self.profile_folder)
        except shutil.SameFileError:
            messagebox.showerror(title="Invalid Name", message=f"Profile '{profile_name}' already exists. Rename file and try again.")
        else:            
            cs_dict = self.load_cheatsheet()
            self.generate_gui(cs_dict)

    def export_profile(self):
        profile_fp = askdirectory()
        if not profile_fp:
            return
        self.save_cheatsheet(path=profile_fp)

    @staticmethod
    def quit_window(icon, item):
        # Define a function for quit the window
        icon.stop()
        window.destroy()

    @staticmethod
    def show_window(icon, item):
        # Define a function to show the window again
        icon.stop()
        window.after(0, window.deiconify())

    def hide_window(self):
        # Hide the window and show on the system taskbar
        self.window.withdraw()
        image = Image.open("favicon.ico")
        menu = (item('Show', self.show_window), item('Quit', self.quit_window))
        icon = pystray.Icon("name", image, "My System Tray Icon", menu)
        icon.run()

    def load_cheatsheet(self, profile=None):
        """Retrieve cheatsheet info from json file."""
        if profile is None:
            profile = self.profile
        fp = os.path.join(self.profile_folder, profile + '.json')
            
        if not os.path.isfile(fp):
            with open(fp, "w", encoding="utf-8") as cheatsheet:
                json.dump({"Tab 1": []}, cheatsheet)

        with open(fp, encoding="utf-8") as cheatsheet:
            cs_dict = json.load(cheatsheet)
            if not cs_dict:
                cs_dict = {"Tab 1": []}
        
        return cs_dict
    
    def save_cheatsheet(self, profile=None, path=None):
        if profile is None:
            profile = self.profile
        if path is None:
            path = self.profile_folder
        fp = os.path.join(path, profile + '.json')
            
        
        cs_dict = {}
        for tab_name, tab_info in self.tabs.items():
            children = []
            for button_id in tab_info.children:
                button_info = self.buttons[button_id]
                children.append([button_info.description.get(),
                                 button_info.codestring.get()])
                
            cs_dict[tab_name] = children
        
        with open(fp, 'w', encoding='utf-8') as cheatsheet:
            json.dump(cs_dict, cheatsheet, indent=4)
    
    def save(f):
        def inner(self, *args, **kwargs):
            f(self, *args, **kwargs)
            
            self.save_cheatsheet()
                
        return inner
    
    def refresh_buttons(f):
        def inner(self, *args, **kwargs):
            f(self, *args, **kwargs)
            
            for tab_info in self.tabs.values():
                for button_id in tab_info.children:
                    try:
                        button = self.buttons[button_id].widget
                    except KeyError:
                        continue
                    button.pack(fill='x', side='top', padx=10, pady=5)
                
        return inner

    def clear_tab(f):
        def inner(self, tab_name, *args, **kwargs):
            self.tabs[tab_name] = tab_frame
            
            for child in tab_frame.winfo_children():
                child.unpack()
                
            f(self, tab_name, *args, **kwargs)
        return inner

    @refresh_buttons
    def generate_gui(self, cs_dict):
        try:
            self.tabControl.destroy()
        except:
            pass
        
        tabControl = ttk.Notebook(self.window)
        tabControl.bind('<Double-Button-1>', self.edit_tab_popup)
        tabControl.pack(expand=1, fill="both")   
        
        self.tabControl = tabControl

        for tab_name, children in cs_dict.items():
            self.generate_tab(tab_name, children)

    def generate_tab(self, tab_name, current_children=None):
        if current_children is None:
            current_children = []
        
        tab_frame = ScrollFrame(self.tabControl)
        
        children = []
        self.tabs[tab_name] = Tab(children, tab_frame)
        self.tabControl.add(tab_frame, text=tab_name)
   
        for button_info in current_children:
            button_id = self.generate_button(*button_info, tab_frame)
            children.append(button_id)
                 
    def generate_button(self, description, code_string, tab_frame):
        
        button_id = self._id_count
        self._id_count += 1
        
        s = ttk.Style()
        s.configure('LeftAlign.TButton', anchor='w')        
        
        button = ttk.Button(tab_frame.viewPort,
                            style='LeftAlign.TButton',
                            command=lambda: self.button_command(button_id))#pyperclip.copy(code_string))

        description_var = tk.StringVar(button, value=description, name=f'{button_id} description')
        codestring_var = tk.StringVar(button, value=code_string, name=f'{button_id} codestring')

        button.config(textvariable=description_var)

        self.buttons[button_id] = Button(description_var, codestring_var, button)
            
        return button_id
            
    
    def button_command(self, button_id):
        if self.edit_mode:
            self.edit_button_popup(button_id)
        else:
            pyperclip.copy(self.buttons[button_id].codestring.get())


    def add_item_popup(self):
        addItemPopup = EntryPopup(self.window)
        desc_var = addItemPopup.add_entry("Description")
        code_string_widget = addItemPopup.add_text("Code String")
        
        # submit button
        def submit_action():
            tab_name = self.tabControl.tab(self.tabControl.select(), "text")
            self.add_item(desc_var.get(), code_string_widget.get("1.0",'end-1c'), tab_name)
            addItemPopup.destroy()        
        
        addItemPopup.add_buttons({"Submit": submit_action,
                                  "Cancel": addItemPopup.destroy})    
        
        addItemPopup.size_popup()

    @save
    @refresh_buttons
    def add_item(self, desc, code_string, tab_name):
        """Add item to json dict and save it."""
        
        button_id = self.generate_button(desc, code_string, self.tabs[tab_name].widget)
        self.tabs[tab_name].children.append(button_id)
        
    @refresh_buttons
    def edit_items(self):
        # Do something to show its in edit mode
        self.edit_mode = not self.edit_mode
        options = {
            True: {'image': self.trashcan, 'compound': 'right'},
            False: {'image': ''}
        }
        SPACE_WIDTH = 3
        for button_id, button_info in self.buttons.items():
            spaces_needed = int(self.window.winfo_width() / SPACE_WIDTH)
            button_info.description.set(button_info.description.get() + ' ' * spaces_needed)
            
            button_info.widget.configure(**options[self.edit_mode])

    def edit_button_popup(self, button_id):
        button_info = self.buttons[button_id]

        editItemPopup = EntryPopup(self.window)
        desc_var = editItemPopup.add_entry("Change Description", button_info.description.get())
        code_string_widget = editItemPopup.add_text("Change Code String", button_info.codestring.get())

        # submit button
        def submit_action():
            tab_name = self.tabControl.tab(self.tabControl.select(), "text")
            self.edit_button(button_id,
                             desc_var.get(),
                             code_string_widget.get("1.0",'end-1c'))
            editItemPopup.destroy()

        def delete_action():
            current_tab = self.tabControl.tab(self.tabControl.select(), "text")
            confirmation = messagebox.askyesno(title="Delete Tab", message=f"Are you sure you want to delete button '{current_tab}'?")
            if confirmation:
                self.delete_button(button_id)
                editItemPopup.destroy()


        buttons = editItemPopup.add_buttons({"Submit": submit_action,
                                             "Delete": delete_action,
                                             "Cancel": editItemPopup.destroy})
        buttons["Submit"].focus_set()
        editItemPopup.size_popup()

    @save
    def edit_button(self, button_id, new_description, new_codestring):
        button_info = self.buttons[button_id]
        if new_description:
            button_info.description.set(new_description)
        if new_codestring:
            button_info.codestring.set(new_codestring)

    @save
    @refresh_buttons            
    def delete_button(self, button_id):
        button = self.buttons[button_id].widget
        current_tab_name = self.tabControl.tab(button.master.master.master, "text") 
        button.destroy()
        self.tabs[current_tab_name].children.remove(button_id)
        del self.buttons[button_id]


    def create_tab_popup(self):
        createTabPopup = EntryPopup(self.window)
        tab_name_var = createTabPopup.add_entry("New Tab Name")
        
        # submit button
        def submit_action():
            self.create_tab(tab_name_var.get())
            createTabPopup.destroy()        
        
        createTabPopup.add_buttons({"Submit": submit_action,
                                    "Cancel": createTabPopup.destroy})
        createTabPopup.size_popup()

    @save
    def create_tab(self, tab_name):
        """Add a tab to the json dict and save it."""            
        self.generate_tab(tab_name)
        self.tabControl.select(self.tabs[tab_name].widget)
            
    
    def delete_tab_popup(self):
        current_tab = self.tabControl.tab(self.tabControl.select(), "text")  
        confirmation = messagebox.askyesno(title="Delete Tab", message=f"Are you sure you want to delete tab '{current_tab}'?\n\nAll buttons within will be lost.")
        if confirmation:
            self.delete_tab(current_tab)
    
    @save
    def delete_tab(self, tab_name):
        self.tabs[tab_name].widget.destroy()
        for button_id in self.tabs[tab_name].children:
            self.delete_button(button_id)
        del self.tabs[tab_name]
        
        
    def edit_tab_popup(self, event):
        current_tab = self.tabControl.tab(self.tabControl.select(), "text")  
        
        editTabPopup = EntryPopup(self.window)
        tab_name_var = editTabPopup.add_entry(f"Change '{current_tab}' to:")
        
        # submit button
        def submit_action():
            self.edit_tab(current_tab, tab_name_var.get())
            editTabPopup.destroy()   
        
        editTabPopup.add_buttons({"Submit": submit_action,
                                  "Cancel": editTabPopup.destroy})  
        editTabPopup.size_popup()

    @save        
    def edit_tab(self, current_tab, new_tab_name):
        self.tabs[new_tab_name] = self.tabs[current_tab]
        del self.tabs[current_tab]
        
        tab_frame = self.tabs[new_tab_name].widget
        self.tabControl.tab(tab_frame, text=new_tab_name)
        
    
    """ ----------------- BUTTON MOVEMENT----------------- """
    
    # Place holder for future development



if __name__ == '__main__':
    window = tk.Tk()

    app = CheatSheet(window)
        
    window.mainloop()
