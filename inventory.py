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
                'Email': 4, 'Due Date': 5, 'Storage Location': 6, 
                'Description': 7, 'Comments': 8}
NOTEBOOK_INDEX = {'Asset List': 0, 'Shopping Cart': 1, 'Settings': 2}
SEARCHABLE = ['Asset Number', 'Item', 'Loaned To', 'Email', 'Due Date', 'Description']
SEARCH_HINT = 'Search...'
SETTINGS = ['first_name', 'last_name', 'email', 'database_path']
SETTINGS_PATH = os.path.join('settings', 'asset_settings.json')

# TEMPORARY DUMMY DATA
items = ['Laptop', 'Microphone', 'Pen', 'Monitor', 'Keyboard', 'Strapped Bag',
            'Mouse', 'Notebook', 'CD', 'USB Stick', 'Desk', 'Key']
states = ['Available', 'Borrowed', 'Shopping Cart']

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

        # Asset list tree configurations
        self.tree.configure(selectmode=tk.BROWSE)  # One item selection at a time

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
        item = self.tree.item(self.tree.focus())
        item_index = self.tree.index(self.tree.focus())
        full_list_index = self.filtered_items_ix[item_index]

        if item['values'] != '':
            asset_number = item['values'][COLUMN_INDEX['Asset Number']]
            item_name = item['values'][COLUMN_INDEX['Item']]
            item_state = item['values'][COLUMN_INDEX['State']]
            new_values = item['values']
            
            if item_state == 'Available':
                self.app_toplevel.history_msg.set('{} was put into shopping cart'.format(item_name))
                new_values[COLUMN_INDEX['State']] = 'Shopping Cart'

                # Edit the item in the initial non-filtered list
                self.app_toplevel.shopping_cart.filtered_items_ix.append(full_list_index)
                self.app_toplevel.update_cart_count()
                self.app_toplevel.shopping_cart.tree.insert('', 'end', values=new_values)

            elif item_state == 'Shopping Cart':
                # Remove item from shopping cart
                self.app_toplevel.history_msg.set('{} was removed from shopping cart'.format(item_name))
                new_values[COLUMN_INDEX['State']] = 'Available'

                for filter_index, ix in enumerate(self.app_toplevel.shopping_cart.filtered_items_ix):
                    current = self.app_toplevel.shopping_cart.items[ix]
                    if current[COLUMN_INDEX['Asset Number']] == asset_number:
                        del self.app_toplevel.shopping_cart.filtered_items_ix[filter_index]
                        self.app_toplevel.update_cart_count()
                        break

                # Remove listing in shopping cart gui
                for leaf_id in self.app_toplevel.shopping_cart.tree.get_children(''):
                    current = self.app_toplevel.shopping_cart.tree.item(leaf_id)

                    if asset_number == current['values'][COLUMN_INDEX['Asset Number']]:
                        self.app_toplevel.shopping_cart.tree.delete(leaf_id)
                        break

            self.items[full_list_index] = new_values
            self.tree.item(self.tree.focus(), values=new_values, tags=[new_values[COLUMN_INDEX['State']]])

class ShoppingCart(MultiColumnListbox):
    def __init__(self, master, app_toplevel, header, items):
        MultiColumnListbox.__init__(self, master, header, items)
        self.master = master
        self.app_toplevel = app_toplevel
        for binding in ['<ButtonRelease-1>', '<KeyRelease-Up>', '<KeyRelease-Down>']:
            self.tree.bind(binding, 
                        lambda event, tree=self.tree: self.app_toplevel.update_description(tree))
        self.tree.bind('<Double-Button-1>', self.select_item)
        self.filtered_items_ix = []
        self.repopulate_list()

    def select_item(self, *args):
        item = self.tree.item(self.tree.focus())

        if item['values'] != '':
            item_index = self.tree.index(self.tree.focus())
            full_list_index = self.filtered_items_ix[item_index]
            asset_number = item['values'][COLUMN_INDEX['Asset Number']]
            item_name = item['values'][COLUMN_INDEX['Item']]
            item_state = item['values'][COLUMN_INDEX['State']]
            new_values = item['values']

            self.app_toplevel.history_msg.set('{} was removed from shopping cart'.format(item_name))
            new_values[COLUMN_INDEX['State']] = 'Available'

            # Remove from shopping cart
            for filter_index, ix in enumerate(self.app_toplevel.shopping_cart.filtered_items_ix):
                current = self.app_toplevel.shopping_cart.items[ix]
                if current[COLUMN_INDEX['Asset Number']] == asset_number:
                    del self.filtered_items_ix[filter_index]
                    self.app_toplevel.update_cart_count()
                    break

            self.items[full_list_index] = new_values
            self.tree.delete(self.tree.focus())

            # Update item listing in asset list
            for leaf_id in self.app_toplevel.asset_list.tree.get_children(''):
                current = self.app_toplevel.asset_list.tree.item(leaf_id)

                if asset_number == current['values'][COLUMN_INDEX['Asset Number']]:
                    self.app_toplevel.asset_list.tree.item(leaf_id, 
                        values=new_values, tags=[new_values[COLUMN_INDEX['State']]])
                    break
        
class Application(object):
    def __init__(self, master):
        self.master = master
        self.master.rowconfigure(0, weight=10)
        self.master.rowconfigure(1, weight=1)
        self.master.columnconfigure(0, weight=1)

        self.settings = {setting: tk.StringVar() for setting in SETTINGS}

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

        # Search bar
        self.search_query = tk.StringVar()
        self.search_query.set(SEARCH_HINT)
        self.search_bar = tk.Entry(self.asset_frame, exportselection=0, textvariable=self.search_query)
        self.search_bar.grid(row=0, column=0,
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

        # Shopping cart frame
        self.cart_frame = tk.Frame(self.notebook, name='cart_frame')
        self.cart_frame.grid(row=0, column=0, sticky='nesw')
        self.cart_frame.rowconfigure(0, weight=1)
        self.cart_frame.columnconfigure(0, weight=2)
        self.cart_frame.columnconfigure(1, weight=1)
        self.notebook.add(self.cart_frame, text='Shopping Cart (0)') 
        self.cart_frame.bind('<Visibility>',
                                lambda event: self.tab_update_description("Cart Frame"))

        # Shopping cart list
        self.shopping_cart_header = ['Asset Number', 'Item']
        self.shopping_cart = ShoppingCart(self.cart_frame, self, self.shopping_cart_header, self.asset_list_items)
        self.shopping_cart.grid(row=0, column=0, sticky='nesw')
        self.shopping_cart.rowconfigure(0, weight=1)
        self.shopping_cart.columnconfigure(0, weight=1)

        # User Profile Frame
        self.label_font = tkFont.Font(size=8, weight='bold')

        self.profile_frame = ttk.LabelFrame(self.cart_frame, 
                                            text='Your Info', labelanchor='n')
        self.profile_frame.grid(row=0, column=1, sticky='nesw', padx=20, pady=20)
        self.profile_frame.columnconfigure(0, weight=1)
         
        # Name Label
        self.profile_fname_lbl = tk.Label(self.profile_frame, text='First Name', 
                                            font=self.label_font)
        self.profile_fname_lbl.grid(row=0, column=0, sticky='w', padx=15, pady=(15, 0))
        self.first_name_entry = tk.Entry(self.profile_frame, 
                                            textvariable=self.settings['first_name'])
        self.first_name_entry.grid(row=1, column=0, sticky='ew', padx=15)
        self.profile_lname_lbl = tk.Label(self.profile_frame, text='Last Name', 
                                            font=self.label_font)
        self.profile_lname_lbl.grid(row=2, column=0, sticky='w', padx=15, pady=(15, 0))
        self.last_name_entry = tk.Entry(self.profile_frame, 
                                        textvariable=self.settings['last_name'])
        self.last_name_entry.grid(row=3, column=0, sticky='ew', padx=15)

        self.profile_email_lbl = tk.Label(self.profile_frame, text='Email', 
                                            font=self.label_font)
        self.profile_email_lbl.grid(row=4, column=0, sticky='w', padx=15, pady=(15, 0))
        self.email_entry = tk.Entry(self.profile_frame, 
                                    textvariable=self.settings['email'])
        self.email_entry.grid(row=5, column=0, sticky='ew', padx=15, pady=(0, 10))

        self.reason_lbl = tk.Label(self.profile_frame, text='Reason for Use', 
                                            font=self.label_font)
        self.reason_lbl.grid(row=6, column=0, sticky='w', padx=15, pady=(15, 0))
        self.checkout_reason = tk.Text(self.profile_frame, height=5)
        self.checkout_reason.grid(row=7, column=0, sticky='ew', padx=15)

        # Checkout Button
        self.checkout_button = tk.Button(self.profile_frame, text='Checkout Items',
                                            command=self.checkout_cart)
        self.checkout_button.grid(row=8, column=0, sticky='s', padx=15, pady=15)

        # Settings
        self.settings_frame = tk.Frame(self.notebook, name='settings_frame')
        self.settings_frame.rowconfigure(0, weight=1)
        self.settings_frame.columnconfigure(1, weight=1)
        self.notebook.add(self.settings_frame, text="Settings")

        self.about_frame = tk.Frame(self.settings_frame)
        self.about_frame.grid(row=0, column=1, sticky='new')
        self.about_frame.columnconfigure(0, weight=1)

        # Database Path Finder
        self.db_path_frame = tk.LabelFrame(self.about_frame, text='Database Path',
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

        if os.path.exists(SETTINGS_PATH):
            with open(SETTINGS_PATH, 'r') as config_file:
                in_settings = json.load(config_file)
                for setting in in_settings:
                    self.settings[setting].set(in_settings[setting])

                self.update_asset_items(self.retrieve_assets(self.settings['database_path'].get()))
                self.asset_list.filtered_items_ix = list(range(len(self.asset_list_items)))
                self.shopping_cart.filtered_items_ix = list(range(0))
  
                self.asset_list.repopulate_list()
                self.shopping_cart.repopulate_list()
        else:
            self.notebook.select(self.notebook.tabs()[NOTEBOOK_INDEX['Settings']])
            messagebox.showwarning(title='Missing user profile', 
                                        message='Please insert your information to checkout items.')

    def checkout_cart(self, *args):
        """
        Updates the database to indicate the items in the shopping cart have been requested
        """

        db_path = self.settings['database_path'].get()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        SELECT_QUERY = ('SELECT borrow_list.asset_id, name FROM borrow_list '
                        'LEFT JOIN assets '
                        'WHERE borrow_list.asset_id={}')

        CHECKOUT_QUERY = ('INSERT INTO borrow_list '
                          'VALUES (?,?,?,?,?,?,?)')

        today = datetime.date.today()
        today_formatted = '{}-{:02}-{:02}'.format(
                            today.year, today.month, today.day)
        borrow_time = datetime.timedelta(days=30)
        due_date = today + borrow_time
        due_formatted = '{}-{:02}-{:02}'.format(
                            due_date.year, due_date.month, due_date.day)

        checked_out = []  # Keep track of items that may be requested already

        for ix in self.shopping_cart.filtered_items_ix:
            values = self.shopping_cart.items[ix]

            result = cursor.execute(SELECT_QUERY.format(
                        values[COLUMN_INDEX['Asset Number']]))

            if list(result):
                checked_out.append((values[COLUMN_INDEX['Asset Number']], 
                                    values[COLUMN_INDEX['Item']]))
            else:
                first_name = self.settings['first_name'].get()
                last_name = self.settings['last_name'].get()
                full_name = '{} {}'.format(first_name, last_name)

                cursor.execute(CHECKOUT_QUERY,
                    [values[COLUMN_INDEX['Asset Number']], 
                    full_name,
                    self.settings['email'].get(), 'Requested',
                    today_formatted, due_formatted,
                    self.checkout_reason.get('1.0', tk.END)])
                conn.commit()

        if checked_out:
            checked = ', '.join(['{} ({})'.format(name, asset_num) 
                                 for asset_num, name in checked_out])
            messagebox.showwarning('Checkout Error',
                                   ('The following items have already ' 
                                    'been checked out by someone else: {}').format(checked))

        self.history_msg.set('{} items were checked out'.format(
            len(self.shopping_cart.filtered_items_ix) - len(checked_out)))

        self.shopping_cart.filtered_items_ix = list(range(0))
        self.shopping_cart.repopulate_list()
        self.update_cart_count()

        items = self.retrieve_assets(self.settings['database_path'].get())
        self.update_asset_items(items)
        self.asset_list.repopulate_list()

    def choose_db_file(self, *args):
        db_path = filedialog.askopenfilename(filetypes=(('Database Files', '*.db'),)) 
        items = self.retrieve_assets(db_path)

        if items is not None:
            self.asset_list.tree.delete(*self.asset_list.tree.get_children())
            self.update_asset_items(items)
            self.asset_list.filtered_items_ix = list(range(len(self.asset_list.items)))
            self.settings['database_path'].set(db_path)
            self.shopping_cart.filtered_items_ix = []
            self.shopping_cart.repopulate_list()
            self.update_cart_count()
            self.history_msg.set('Changed database ({})'.format(path))
            
        self.asset_list.repopulate_list()    

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
                        'borrower_email, return_date, storage_location, '
                        'description, comments ' 
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

    def update_cart_count(self):
        self.notebook.tab(self.notebook.tabs()[NOTEBOOK_INDEX['Shopping Cart']], 
                    text='Shopping Cart ({})'.format(len(self.shopping_cart.filtered_items_ix)))
        
    def update_description(self, tree):
        item = None

        try:
            item = tree.item(tree.focus())['values']
        except:
            description = ''
    
        if item is not None and item != '':
            description = item[COLUMN_INDEX['Description']]

            if item[COLUMN_INDEX['Comments']] != '---':
                description += '\n\nBorrower Comments: {}'.format(
                                        item[COLUMN_INDEX['Comments']])
        else:
            description = ''

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
        elif tab_name == 'Cart Frame':
            tree_type = self.shopping_cart.tree

        if tree_type is not None:
            self.update_description(tree_type)
        else:
            self.item_msg.configure(state=tk.NORMAL)
            self.item_msg.delete('1.0', tk.END)
            self.item_msg.insert(tk.END, '')
            self.item_msg.configure(state=tk.DISABLED)


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