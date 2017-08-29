from __future__ import absolute_import, division, print_function, unicode_literals

import datetime
import json
from operator import itemgetter
import os
import random
import re
import sqlite3
import sys
import time

if sys.version_info.major == 2:
    import Tkinter as tk
    import tkFont
    import ttk
    import tkMessageBox as messagebox
    import tkFileDialog as filedialog
else:
    import tkinter as tk
    import tkinter.font as tkFont
    import tkinter.ttk as ttk
    from tkinter import messagebox, filedialog

COLUMN_INDEX = {'Asset Number': 0, 'Item': 1, 'State': 2, 'Loaned To': 3, 
                'Email': 4, 'Date Requested': 5, 'Due Date': 6,
                'Storage Location': 7, 'Purchase Date': 8, 'Description': 9, 
                'Comments': 10}
NOTEBOOK_INDEX = {'Asset List': 0, 'Settings': 1}
SEARCHABLE = ['Asset Number', 'Item', 'Loaned To', 'Email', 
                'Date Requested', 'Due Date', 'Description', 
                'Purchase Date', 'Storage Location']
SEARCH_HINT = 'Search...'
SETTINGS = ['first_name', 'last_name', 'email', 'database_path']
SETTINGS_PATH = os.path.join('settings', 'asset_settings.json')

class LabelEntry(tk.Frame):
    def __init__(self, master, label_text, entry_text):
        tk.Frame.__init__(self, master)
        self.columnconfigure(0, weight=1)

        self.label = tk.Label(self, text=label_text, 
                                font=tkFont.Font(size=8, weight='bold'))
        self.label.grid(row=0, column=0, sticky='w')

        self.entry_var = tk.StringVar()
        self.entry_var.set(entry_text)

        self.entry = tk.Entry(self, textvariable=self.entry_var)
        self.entry.grid(row=1, column=0, sticky='ew')

    def get_text(self):
        return self.entry_var.get()

    def set_text(self, text):
        self.entry_var.set(text)

class AddItemWindow(object):
    def __init__(self, app_toplevel, values=None):
        self.app_toplevel = app_toplevel
        self.root = tk.Toplevel()
        self.root.transient(self.app_toplevel.master)
        self.root.title('Add Asset')
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)

        if values is None:
            asset_num = ''
            item_name = ''
            description = ''
            storage_loc = ''
            purchase_date = ''
        else:
            asset_num = values[COLUMN_INDEX['Asset Number']]
            item_name = values[COLUMN_INDEX['Item']]
            description = values[COLUMN_INDEX['Description']]
            storage_loc = values[COLUMN_INDEX['Storage Location']]
            purchase_date = values[COLUMN_INDEX['Purchase Date']]

            if description == '---':
                description = ''
            if purchase_date == '---':
                purchase_date = ''


        self.entry_frame = tk.Frame(self.root)
        self.entry_frame.grid(row=0, column=0, sticky='nesw', padx=15, pady=15)
        self.entry_frame.columnconfigure(0, weight=1)

        self.asset_num_entry = LabelEntry(self.entry_frame, 'Asset Number', asset_num)
        self.asset_num_entry.grid(row=0, column=0, sticky='ew')
        self.asset_num_entry.entry.focus()
        self.name_entry = LabelEntry(self.entry_frame, 'Item Name', item_name)
        self.name_entry.grid(row=1, column=0, sticky='ew')
        self.description_entry = LabelEntry(self.entry_frame, 'Description (optional)', description)
        self.description_entry.grid(row=2, column=0, sticky='ew')
        self.storage_entry = LabelEntry(self.entry_frame, 'Storage Location (room #)', storage_loc)
        self.storage_entry.grid(row=3, column=0, sticky='ew')
        self.purchase_date_entry = LabelEntry(self.entry_frame, 
                                                'Date of Purchase (optional) [YYYY-MM-DD]', 
                                                purchase_date)
        self.purchase_date_entry.grid(row=4, column=0, sticky='ew')

        self.actions_frame = tk.Frame(self.root)
        self.actions_frame.grid(row=1, column=0, sticky='nes', padx=15, pady=15)

        self.cancel_btn = tk.Button(self.actions_frame, text='Cancel', 
                                    command=self.root.destroy)
        self.cancel_btn.grid(row=0, column=0, sticky='e')


        is_update = values is not None

        self.add_btn = tk.Button(self.actions_frame, 
                                    text='Add' if values is None else 'Update',
                                    command=lambda: self.add_items(is_update))
        self.add_btn.grid(row=0, column=1, sticky='e')


        self.root.geometry('{width}x{height}+{xlocation}+{ylocation}'
                            .format(width=400,
                                    height=300,
                                    xlocation=self.root.winfo_pointerx(),
                                    ylocation=self.root.winfo_pointery()))
        self.root.update()
        self.root.minsize(self.root.winfo_width(), 
                            self.root.winfo_height())
        self.root.mainloop()

    def add_items(self, is_update, *args):
        """
        Add or update items in the asset list database
        """

        database_path = self.app_toplevel.settings['database_path'].get()
        asset_numbers = self.asset_num_entry.get_text()
        asset_name = self.name_entry.get_text()
        description = self.description_entry.get_text()
        storage_location = self.storage_entry.get_text()
        purchase_date = self.purchase_date_entry.get_text()

        if description == '':
                description = None
        if purchase_date == '':
            purchase_date = None

        if '' in [asset_numbers, asset_name, storage_location]:
            messagebox.showerror('Insert Error', 'Required field(s) are empty')
        elif database_path == '':
            self.root.destroy()
            messagebox.showerror('Database Error', 'Database file not found')
        elif purchase_date is not None and not self._valid_date(purchase_date):
            messagebox.showerror('Date Error', 'Invalid date, please use YYYY-MM-DD format')
        else:
            conn = sqlite3.connect(database_path)
            cursor = conn.cursor()

            
            num_count = {}
            asset_num_list = asset_numbers.split(',')

            for num in asset_num_list:
                if num in num_count:
                    num_count[num] += 1
                else:
                    num_count[num] = 1

            non_unique_assets = [num for num in num_count if num_count[num] > 1]

            if not is_update:
                for asset_no in asset_num_list:
                    result = cursor.execute(
                                'SELECT name FROM assets WHERE asset_id={}'.format(asset_no))
                    if list(result):
                        non_unique_assets.append(asset_no)

            if non_unique_assets:
                messagebox.showerror('Update Error', 
                                        'Non-unique asset numbers:' 
                                        + ', '.join(non_unique_assets))
            elif is_update and len(asset_num_list) > 1:
                messagebox.showerror('Update Error',
                                        'Cannot add multiple items for an update')
            else:
                if is_update:
                    values = self.app_toplevel.asset_list.selected_values
                    old_asset_num = values[COLUMN_INDEX['Asset Number']]
                    DELETE_QUERY = 'DELETE FROM assets WHERE asset_id={}'.format(
                                        old_asset_num)

                    UPDATE_QUERY = ('UPDATE borrow_list ' 
                                    'SET asset_id = {} '
                                    'WHERE asset_id = {}').format(old_asset_num, asset_num_list[0])

                    cursor.execute(DELETE_QUERY)
                    cursor.execute(UPDATE_QUERY)

                ADD_QUERY = 'INSERT INTO assets VALUES (?,?,?,?,?)'
                # Split asset number entry by , for bulk entry
                for asset_no in asset_num_list:
                    cursor.execute(ADD_QUERY, [asset_no, asset_name, 
                                                description, purchase_date,
                                                storage_location])
                    conn.commit()
                
                if is_update:
                    new_values = list(values)
                    new_values[COLUMN_INDEX['Asset Number']] = asset_num_list[0]
                    new_values[COLUMN_INDEX['Item']] = asset_name
                    new_values[COLUMN_INDEX['Description']] = description
                    new_values[COLUMN_INDEX['Purchase Date']] = purchase_date
                    new_values[COLUMN_INDEX['Storage Location']] = storage_location
                    self.app_toplevel.asset_list.change_values(new_values)
                else:
                    items = self.app_toplevel.retrieve_assets(database_path)
                    self.app_toplevel.update_asset_items(items)
                    self.app_toplevel.asset_list.filtered_items_ix = list(
                                                    range(len(self.app_toplevel.asset_list_items)))
                    self.app_toplevel.asset_list.repopulate_list()
                
                self.root.destroy()

            conn.close()

    def _valid_date(self, date):
        date_lst = date.split('-')

        if len(date_lst) != 3:
            return False
        else:
            year, month, day = [int(x) for x in date_lst]

        if (not 1 <= month <= 12
            and (month == 2 and not 1 <= month <= 29)
            and not (1 <= day <= 31)):
            return False

        return True


class MultiColumnListbox(tk.Frame):
    def __init__(self, master, header, items):
        tk.Frame.__init__(self, master)
       
        self.header = header
        self.items = items
        self.filtered_items_ix = list(range(len(items)))  # indexes of filtered items

        self.tree = ttk.Treeview(self, columns=self.header, show='headings')
        v_scroll = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        h_scroll = ttk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        self.tree.grid(row=0, column=0, sticky='nesw')
        v_scroll.grid(row=0, column=1, sticky='ns')
        h_scroll.grid(row=1, column=0, sticky='ew')

        self._build_tree()

    def _build_tree(self):
        """
        Initializes the items in the tree to be displayed on the gui
        """

        for col in self.header:
            self.tree.heading(col, text=col.title(),
                                command=lambda c=col: self.sortby(c, False))
            self.tree.column(col, width=tkFont.Font().measure(col.title())+20)  # +20 for extra padding

        for ix in self.filtered_items_ix:
            self.tree.insert('', index='end', values=self.items[ix])

            # Ensure column width fits values
            for i in range(len(self.header)):
                col_width = tkFont.Font().measure(self.items[ix][i]) + 20
                if self.tree.column(self.header[i], width=None) < col_width:
                    self.tree.column(self.header[i], width=col_width)

    def fit_columns(self):
        """
        Resizes each column to fit the longest text
        """

        column_count = len(self.header)
        widths = [self.tree.column(col)['width'] for col in self.header]

        for ix in self.filtered_items_ix:
            for i in range(column_count):
                item_width = tkFont.Font().measure(self.items[ix][i]) + 20
                widths[i] = max(item_width, widths[i])

        for i in range(len(self.header)):
            self.tree.column(self.header[i], width=widths[i])

    def sortby(self, col, descending):
        """
        Sorts the data in a list column
        """

        data = [(self.tree.set(child, col), child) for child in self.tree.get_children('')]
        data.sort(reverse=descending)

        for i, item in enumerate(data):
            self.tree.move(item[1], '', i)

        self.tree.heading(col, command=lambda c=col: self.sortby(c, not descending))

    def repopulate_list(self):
        """
        Refreshes the view of the list
        """

        for row in self.tree.get_children():
                self.tree.delete(row)
        for ix in self.filtered_items_ix:
            self.tree.insert('', index='end', values=self.items[ix])

        self.fit_columns()

class AssetList(MultiColumnListbox):
    def __init__(self, master, app_toplevel, header, items):
        MultiColumnListbox.__init__(self, master, header, items)
        self.master = master
        self.app_toplevel = app_toplevel
        self.selected_values = None

        # Asset list tree configurations
        self.tree.bind('<Button-3>', self.popup_menu)
        for binding in ['<ButtonRelease-1>', '<KeyRelease-Up>', '<KeyRelease-Down>']:
            self.tree.bind(binding, 
                        lambda event, tree=self.tree: self.app_toplevel.update_description(tree))
        self.tree.bind('<Double-Button-1>', self.select_item)
        self.tree.bind('<Return>', self.select_item)
        self.tree.tag_configure('Borrowed', background='#EF9A9A')
        self.tree.tag_configure('Requested', background='#FFCC80')
        self.tree.tag_configure('Shopping Cart', background='#90CAF9')
        self.tree.tag_configure('Overdue', background='#B39DDB')
        self.items.sort(key=itemgetter(COLUMN_INDEX['Asset Number']))
        self.repopulate_list()

    def approve_request(self, *args):
        """ 
        Changes an items state to borrowed
        """

        values = self.selected_values

        if values[COLUMN_INDEX['State']] == 'Requested':
            self.set_state('Borrowed')
        else:
            messagebox.showerror('Approve Error', 
                '{} is not requested'.format(values[COLUMN_INDEX['Item']]))

    def change_values(self, new_values):
        """
        Change the values of the selected item on the list
        """

        asset_number = self.selected_values[COLUMN_INDEX['Asset Number']]

        for leaf_id in self.tree.get_children(''):
                current = self.tree.item(leaf_id)

                if asset_number == current['values'][COLUMN_INDEX['Asset Number']]:
                    self.tree.item(leaf_id, values=new_values, 
                                    tags=[new_values[COLUMN_INDEX['State']]])
                    break

    def delete_item(self, *args):
        """
        Delete the selected item from the database
        """

        values = self.selected_values
        asset_id = values[COLUMN_INDEX['Asset Number']]

        confirm = messagebox.askokcancel('Delete item?',
                                         'Are you sure you want to delete {}?'.format(
                                           values[COLUMN_INDEX['Item']]),
                                         default=messagebox.CANCEL)

        if confirm:
            db_path = self.app_toplevel.settings['database_path'].get()
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(('DELETE FROM assets '
                            'WHERE asset_id={}').format(asset_id))
            conn.commit()
            conn.close()

            self.app_toplevel.history_msg.set(
                'Deleted {} from database'.format(values[COLUMN_INDEX['Item']]))
            self.tree.delete(self.tree.selection()[0])

    def extend_due_date(self, *args):
        """
        Extend the due date of an item by 30 days
        """

        values = self.selected_values
        asset_num = values[COLUMN_INDEX['Asset Number']]
        year, month, day = [int(d) for d in values[COLUMN_INDEX['Due Date']].split('-')]

        old_due = datetime.date(year=year, month=month, day=day)
        extra = datetime.timedelta(days=30)
        new_due = old_due + extra

        due_formatted = '{}-{:02}-{:02}'.format(
                            new_due.year, new_due.month, new_due.day)

        db_path = self.app_toplevel.settings['database_path'].get()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(('UPDATE borrow_list '
                        'SET return_date = "{}" '
                        'WHERE asset_id={}').format(due_formatted, asset_num))
        conn.commit()
        conn.close()

        values[COLUMN_INDEX['Due Date']] = due_formatted
        self.change_values(values)
        self.app_toplevel.history_msg.set('Extended due date of {} by 30 days'.format(
            values[COLUMN_INDEX['Item']]))

    def make_available(self):
        """
        Changes an item's state to available
        """

        db_path = self.app_toplevel.settings['database_path'].get()
        asset_id = self.selected_values[COLUMN_INDEX['Asset Number']]

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(('DELETE FROM borrow_list '
                        'WHERE asset_id={}').format(asset_id))
        conn.commit()
        conn.close()

        self.set_state('Available')


    def repopulate_list(self):
        """
        Refreshes the view of the list
        """

        for row in self.tree.get_children():
                self.tree.delete(row)
        for ix in self.filtered_items_ix:
            item = self.items[ix]
            self.tree.insert('', index='end', values=item, 
                                tags=[item[COLUMN_INDEX['State']]])
        self.fit_columns()

    def select_item(self, *args):
        """
        Update the selected item on the list
        """

        item = self.tree.item(self.tree.focus())
        item_index = self.tree.index(self.tree.focus())
        full_list_index = self.filtered_items_ix[item_index]

    def set_state(self, state, *args):
        """ 
        Changes an items state to desired value
        """

        database_path = self.app_toplevel.settings['database_path'].get()
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()

        values = self.selected_values
        asset_number = values[COLUMN_INDEX['Asset Number']]

        QUERY = ('UPDATE borrow_list '
                 'SET state = "{}"'
                 'WHERE asset_id={}').format(state, asset_number)

        cursor.execute(QUERY)

        conn.commit()

        values[COLUMN_INDEX['State']] = state

        if state == 'Available':
            for column in ['Loaned To', 'Email', 'Date Requested', 'Due Date']:
                values[COLUMN_INDEX[column]] = '---'

        self.change_values(values)
        self.app_toplevel.history_msg.set(
            '{} is now {}'.format(values[COLUMN_INDEX['Item']].lower(), state))

    def popup_menu(self, event):
        """
        Right click menu for items on the list
        """

        iid = self.tree.identify_row(event.y)
        self.selected_values = self.tree.item(iid)['values']

        if iid:
            values = self.selected_values

            rclick_menu = tk.Menu(self, tearoff=0)
            rclick_menu.add_command(label="Edit", 
                           command=lambda: 
                           AddItemWindow(self.app_toplevel,
                                           self.selected_values))
            rclick_menu.add_command(label="Delete",
                           command=self.delete_item)

            if values[COLUMN_INDEX['State']] != 'Available':
                rclick_menu.add_command(label="Make Available",
                                            command=self.make_available)
                rclick_menu.add_command(label="Extend Due Date by 30 days",
                                            command=self.extend_due_date)

                if values[COLUMN_INDEX['State']] == 'Requested':
                    rclick_menu.add_command(label="Approve Request",
                                   command=self.approve_request)
            
            self.tree.selection_set(iid)
            rclick_menu.tk_popup(event.x_root, event.y_root)
            self.selected_values = self.tree.item(iid)['values']
        
class Application(object):
    def __init__(self, master):
        self.master = master
        self.master.rowconfigure(0, weight=10)
        self.master.rowconfigure(1, weight=1)
        self.master.columnconfigure(0, weight=1)

        self.settings = {setting: tk.StringVar() for setting in SETTINGS}
        self.label_font = tkFont.Font(size=8, weight='bold')

        # Items
        self.asset_list_header = [header[0] for header in 
                                    sorted([(column, COLUMN_INDEX[column]) 
                                                for column in COLUMN_INDEX], key=itemgetter(1))
                                    if header[0] not in ['Description', 'Comments']]
        self.asset_list_items = []

        # Tabs for asset list / shopping cart
        self.notebook = ttk.Notebook(self.master)
        self.notebook.grid(row=0, column=0, sticky='nesw')
        self.notebook.rowconfigure(0, weight=1)
        self.notebook.columnconfigure(0, weight=1)

        # Asset list frame
        self.asset_frame = ttk.Frame(self.notebook, name='asset_frame')
        self.asset_frame.grid(row=0, column=0, sticky='nesw')
        self.asset_frame.rowconfigure(1, weight=1)
        self.asset_frame.columnconfigure(0, weight=1)
        self.notebook.add(self.asset_frame, text='Asset List')
        self.asset_frame.bind('<Visibility>',
                                lambda event: self.tab_update_description("Asset Frame"))

        self.actions_frame = tk.Frame(self.asset_frame)
        self.actions_frame.grid(row=0, column=0, sticky='nesw')
        self.actions_frame.columnconfigure(1, weight=1)

        # Add item buttom
        self.add_button = tk.Button(self.actions_frame, text="Add Item", 
                                    command=lambda: AddItemWindow(self))
        self.add_button.grid(row=0, column=0, sticky='nesw')

        # Search bar
        self.search_query = tk.StringVar()
        self.search_query.set(SEARCH_HINT)
        self.search_bar = tk.Entry(self.actions_frame, exportselection=0, textvariable=self.search_query)
        self.search_bar.grid(row=0, column=1,
                                 sticky='nesw')
        self.search_bar.bind('<FocusIn>', self.search_clear)
        self.search_query.trace('w', self.search)

        # Asset List
        self.asset_list = AssetList(self.asset_frame, self, self.asset_list_header, self.asset_list_items)
        self.asset_list.grid(row=1, column=0, sticky='nesw')
        self.asset_list.rowconfigure(0, weight=1)
        self.asset_list.columnconfigure(0, weight=1)

        # Item Description Frame
        self.item_frame = ttk.LabelFrame(self.master, text='Description')
        self.item_frame.rowconfigure(0, weight=1)
        self.item_frame.columnconfigure(0, weight=1)
        self.item_frame.grid(row=1, column=0, sticky='nesw', padx=10, pady=10)

        self.item_msg = tk.Text(self.item_frame, wrap=tk.WORD, state=tk.DISABLED, height=3)
        self.item_msg.grid(row=0, column=0, sticky='nesw')
        msg_vsb = ttk.Scrollbar(self.item_frame, orient=tk.VERTICAL, command=self.item_msg.yview)
        msg_vsb.grid(row=0, column=1, sticky='nes')

        # History message
        self.history_msg = tk.StringVar()
        self.history_msg.set('No action performed yet')
        self.history_label = tk.Label(self.master, textvariable=self.history_msg, justify=tk.LEFT,
                                        anchor=tk.W)
        self.history_label.grid(row=2, column=0, sticky='nesw')

        # Settings
        self.settings_frame = tk.Frame(self.notebook, name='settings_frame')
        self.settings_frame.rowconfigure(0, weight=1)
        self.settings_frame.columnconfigure(0, weight=1)
        self.notebook.add(self.settings_frame, text="Settings")

        # Database Path Finder
        self.db_path_frame = tk.LabelFrame(self.settings_frame, text='Database Path',
                                            labelanchor='n')
        self.db_path_frame.grid(row=0, column=0, sticky='new', 
                                padx=15, pady=(25, 0))
        self.db_path_frame.columnconfigure(0, weight=0)
        self.db_path_frame.columnconfigure(1, weight=1)

        self.file_choose_btn = tk.Button(self.db_path_frame, text='Choose', 
                                            command=self.choose_db_file)
        self.file_choose_btn.grid(row=0, column=0, sticky='new', padx=(15, 0), pady=15)
        self.db_path_msg = tk.Entry(self.db_path_frame, 
                                    textvariable=self.settings['database_path'],
                                    disabledforeground='black',
                                    disabledbackground='white',
                                    state=tk.DISABLED)
        self.db_path_msg.grid(row=0, column=1, sticky='new', padx=(0, 15), pady=15)
        self.db_warning_lbl = tk.Label(self.db_path_frame, 
                                        text='WARNING: all unsaved changes will be lost',
                                        font=self.label_font)
        self.db_warning_lbl.grid(row=1, column=0, columnspan=2, padx=15, pady=5)

        self.options_frame = tk.LabelFrame(self.settings_frame, text='More options',
                                            labelanchor='n')
        self.options_frame.grid(row=1, column=0, sticky='nsw', 
                                padx=15, pady=(0, 25))
        self.create_db_btn = tk.Button(self.options_frame, text='Create New Database',
                                        command=self.create_database)
        self.create_db_btn.grid(row=0, column=0, sticky='nesw', padx=15, pady=15)

        if os.path.exists(SETTINGS_PATH):
            with open(SETTINGS_PATH, 'r') as config_file:
                in_settings = json.load(config_file)
                for setting in in_settings:
                    self.settings[setting].set(in_settings[setting])

                self.update_asset_items(self.retrieve_assets(self.settings['database_path'].get()))
                self.asset_list.filtered_items_ix = list(range(len(self.asset_list_items))) 
                self.asset_list.repopulate_list()
        else:
            self.notebook.select(self.notebook.tabs()[NOTEBOOK_INDEX['Settings']])
            messagebox.showwarning(title='Missing user profile', 
                                        message='Please insert your information to checkout items.')

    def choose_db_file(self, *args):
        db_path = filedialog.askopenfilename(filetypes=(('Database File', '*.db'),)) 

        # Exit if user cancels
        if not db_path:
            return

        items = self.retrieve_assets(db_path)

        if items is not None:
            self.asset_list.tree.delete(*self.asset_list.tree.get_children())
            self.update_asset_items(items)
            self.asset_list.filtered_items_ix = list(range(len(self.asset_list.items)))
            self.settings['database_path'].set(db_path)
            self.save_settings()
            self.history_msg.set('Changed default database ({})'.format(db_path))

        self.asset_list.repopulate_list()  

    def create_database(self, *args):
        """
        Creates a new database at the path specified by the user
        """

        path = filedialog.asksaveasfilename(defaultextension='.db',
                                            filetypes=(('Database File', '*.db'),),
                                            title='Create new database')

        if path != '':
            if os.path.exists(path):
                os.remove(path)

                # List is empty because user overwrote old database with new empty one
                self.update_asset_items([])
                self.asset_list.filtered_items_ix = []
                self.asset_list.repopulate_list()

            conn = sqlite3.connect(path)
            cursor = conn.cursor()

            # Make asset list
            cursor.execute(('CREATE TABLE assets ('
                            'asset_id INTEGER PRIMARY KEY,'
                            'name TEXT NOT NULL,'
                            'description TEXT,'
                            'purchase_date TEXT,'
                            'storage_location TEXT)'))

            # Make borrow list
            cursor.execute(('CREATE TABLE borrow_list ('
                            'asset_id INTEGER PRIMARY KEY,'
                            'borrower_name TEXT NOT NULL,'
                            'borrower_email TEXT NOT NULL,'
                            'state TEXT NOT NULL,'
                            'date_requested TEXT NOT NULL,'
                            'return_date TEXT NOT NULL,'
                            'comments TEXT)'))

            conn.commit()
            conn.close()

            self.history_msg.set('Created database ({})'.format(path))

    def _match_searchables(self, query, columns):
        """
        Goes through all searchable columns and returns True if query matches at least one, else False
        """

        for column in SEARCHABLE:
            if str(columns[COLUMN_INDEX[column]]).lower().find(query.lower()) != -1:
                return True 
        return False

    def retrieve_assets(self, db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        SELECT_QUERY = ('SELECT assets.asset_id, name, state, borrower_name, ' 
                        'borrower_email, date_requested, return_date, '
                        'storage_location, purchase_date, description, comments ' 
                        'from assets LEFT JOIN borrow_list '
                        'ON assets.asset_id=borrow_list.asset_id')
        items = []
        today = datetime.date.today()

        try:
            for item in list(cursor.execute(SELECT_QUERY)):
                item = [value if value is not None else '---' for value in item]
                if item[COLUMN_INDEX['State']] == '---':
                    item[COLUMN_INDEX['State']] = 'Available'
                elif item[COLUMN_INDEX['State']] == 'Borrowed':
                    year, month, day = [int(d) for d in item[COLUMN_INDEX['Due Date']].split('-')]
                    due_date = datetime.date(year=year, month=month, day=day)

                    if today > due_date:
                        item[COLUMN_INDEX['State']] = 'Overdue'

                items.append(item)
        except Exception as ex:
            print('ERROR:', str(ex))

        conn.close()
        return items
        
    def search_clear(self, *args):
        """
        Clears the search bar if the search hint is present
        """

        if self.search_bar.get() == SEARCH_HINT:
            self.search_query.set('')
 
    def search(self, *args):
        """
        Filters the indexes of the asset list that matches the search query, then refreshes the list view
        """

        query = self.search_bar.get() 
        if len(query) > 0 and query != SEARCH_HINT:
            self.asset_list.filtered_items_ix = [index for index in range(len(self.asset_list.items))
                                                    if self._match_searchables(query, self.asset_list.items[index])]
        else:
            self.asset_list.filtered_items_ix = list(range(len(self.asset_list.items)))

        self.asset_list.repopulate_list()

    def update_asset_items(self, items):
        del self.asset_list_items[:]
        for item in items:
            self.asset_list_items.append(item)

    def update_description(self, tree):
        item = None

        try:
            item = tree.item(tree.focus())['values']
        except KeyError as ke:
            pass
    
        if item is not None and item != '':
            description = item[COLUMN_INDEX['Description']]

            if item[COLUMN_INDEX['Comments']] != '---':
                description += '\n\nBorrower Comments: {}'.format(
                                        item[COLUMN_INDEX['Comments']])

            self.item_msg.configure(state=tk.NORMAL)
            self.item_msg.delete('1.0', tk.END)
            self.item_msg.insert(tk.END, description)
            self.item_msg.configure(state=tk.DISABLED)

    def save_settings(self, *args):
        new_settings = {setting: self.settings[setting].get() 
                        for setting in self.settings}

        if not os.path.exists(os.path.dirname(SETTINGS_PATH)):
            os.makedirs(os.path.dirname(SETTINGS_PATH))

        with open(SETTINGS_PATH, 'w') as wp:
            json.dump(new_settings, wp)

        self.history_msg.set('Settings saved')

    def tab_update_description(self, tab_name):
        tree_type = None
        
        if tab_name == 'Asset Frame':
            tree_type = self.asset_list.tree

        if tree_type is not None:
            self.update_description(tree_type)

def main():
    root = tk.Tk()
    app = Application(root)
    root.title('Inventory Manager')
    MYFONT = tkFont.Font(root, size=12)

    root.update()
    root.minsize(root.winfo_width(), root.winfo_height())
    root.mainloop()

if __name__ == '__main__':
    main()