import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
from datetime import datetime
import locale
from tkcalendar import DateEntry
import csv
from typing import Dict, Any, List, Optional
from database import init_database
from db_manager import UserManager, ClientManager, DatabaseManager

# Устанавливаем русскую локаль для корректного отображения дат
locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')

class CustomDateEntry(ttk.Entry):
    def __init__(self, master=None, **kw):
        # Удаляем неподдерживаемые параметры
        supported_kw = {k: v for k, v in kw.items() if k in [
            'width', 'textvariable', 'state', 'style', 'takefocus', 'cursor',
            'xscrollcommand', 'justify', 'validate', 'validatecommand', 'invalidcommand'
        ]}
        
        # Настройки по умолчанию
        supported_kw['state'] = 'readonly'
        
        # Создаем переменную для хранения даты
        self._date_var = tk.StringVar()
        supported_kw['textvariable'] = self._date_var
        
        super().__init__(master, **supported_kw)
        
        # Создаем всплывающее окно для календаря
        self._top_cal = tk.Toplevel(master)
        self._top_cal.withdraw()
        self._top_cal.overrideredirect(True)
        
        # Русские названия дней недели и месяцев
        self.days = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
        self.months = [
            'Январь', 'Февраль', 'Март', 'Апрель',
            'Май', 'Июнь', 'Июль', 'Август',
            'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
        ]
        
        # Создаем и настраиваем календарь
        self._calendar = DateEntry(
            self._top_cal,
            selectmode='day',
            locale='ru_RU',
            date_pattern='dd.mm.yyyy',
            showweeknumbers=False,
            background='white',
            foreground='black',
            headersbackground='white',
            headersforeground='black',
            selectbackground='gray75',
            selectforeground='black',
            weekendbackground='white',
            weekendforeground='black',
            firstweekday='monday'
        )
        self._calendar.pack()
        
        # Настраиваем внешний вид
        self._top_cal.configure(background='white')
        
        # Привязываем обработчики событий
        self.bind('<Button-1>', self._drop_down)
        self.bind('<Button-3>', self.show_context_menu)
        self._calendar.bind('<<DateEntrySelected>>', self._select_date)
        
        # Добавляем контекстное меню
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Очистить", command=self.clear_date)
        
        # Флаг видимости календаря
        self._calendar_visible = False
        
        # Очищаем поле
        self.clear_date()
    
    def _drop_down(self, event=None):
        """Показывает или скрывает календарь"""
        if self._calendar_visible:
            self._top_cal.withdraw()
            self._calendar_visible = False
            self.unbind_all('<Button-1>')
        else:
            x = self.winfo_rootx()
            y = self.winfo_rooty() + self.winfo_height()
            self._top_cal.geometry('+%i+%i' % (x, y))
            self._top_cal.deiconify()
            self._calendar_visible = True
            self.bind_all('<Button-1>', self._handle_click_outside, '+')
    
    def _handle_click_outside(self, event):
        """Обработчик клика вне календаря"""
        if self._calendar_visible:
            cal_x = self._top_cal.winfo_rootx()
            cal_y = self._top_cal.winfo_rooty()
            cal_w = self._top_cal.winfo_width()
            cal_h = self._top_cal.winfo_height()
            
            if not (cal_x <= event.x_root <= cal_x + cal_w and 
                   cal_y <= event.y_root <= cal_y + cal_h):
                self._top_cal.withdraw()
                self._calendar_visible = False
                self.unbind_all('<Button-1>')
    
    def _select_date(self, event=None):
        """Обработчик выбора даты"""
        date = self._calendar.get_date()
        if date:
            self.configure(state='normal')
            self._date_var.set(date.strftime('%d.%m.%Y'))
            self.configure(state='readonly')
            self._top_cal.withdraw()
            self._calendar_visible = False
            self.unbind_all('<Button-1>')
            self.event_generate('<<DateEntrySelected>>')
    
    def show_context_menu(self, event):
        """Показывает контекстное меню"""
        self.context_menu.tk_popup(event.x_root, event.y_root)
    
    def clear_date(self):
        """Очищает поле даты"""
        self.configure(state='normal')
        self._date_var.set('')
        self.configure(state='readonly')
        if self._calendar_visible:
            self._top_cal.withdraw()
            self._calendar_visible = False
    
    def get_date(self):
        """Возвращает выбранную дату или None"""
        date_str = self._date_var.get()
        if not date_str:
            return None
        try:
            from datetime import datetime
            return datetime.strptime(date_str, '%d.%m.%Y').date()
        except ValueError:
            return None
    
    def set_date(self, date):
        """Устанавливает дату"""
        if date is None:
            self.clear_date()
        else:
            self.configure(state='normal')
            if isinstance(date, str):
                self._date_var.set(date)
            else:
                self._date_var.set(date.strftime('%d.%m.%Y'))
            self.configure(state='readonly')

def center_window(window):
    """Центрирует окно на экране"""
    window.update_idletasks()  # Обновляем размеры окна
    width = window.winfo_width()
    height = window.winfo_height()
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    
    window.geometry(f'{width}x{height}+{x}+{y}')

class ClientApp:
    def __init__(self, root, username, role):
        """Инициализация приложения"""
        self.root = root
        self.root.title("Учет клиентов")
        self.root.geometry("1500x800")  # Увеличиваем размер окна
        self.root.minsize(1000, 600)  # Устанавливаем минимальный размер
        
        # Центрируем окно
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - 1500) // 2
        y = (screen_height - 800) // 2
        self.root.geometry(f"1500x800+{x}+{y}")
        
        self.username = username
        self.role = role
        
        # Инициализируем менеджеры базы данных
        self.client_manager = ClientManager()
        self.user_manager = UserManager()
        
        # Флаг для отслеживания состояния сортировки
        self.sort_direction = {}
        for col in ['id', 'last_name', 'first_name', 'middle_name', 'birth_date',
                   'phone', 'email', 'address', 'tariff', 'balance', 'created_at', 'updated_at', 'tariff', 'balance', 'last_call', 'last_caller', 'last_offer']:
            self.sort_direction[col] = 'asc'
            
        self.create_widgets()
        self.show_all_records()
        
        # Центрируем окно после создания всех виджетов
        center_window(self.root)

    def create_widgets(self):
        """Создает все виджеты приложения"""
        # Создаем фрейм поиска
        search_frame = ttk.LabelFrame(self.root, text="Поиск", padding="5")
        search_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.search_entry = ttk.Entry(search_frame)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        
        ttk.Button(search_frame, text="Поиск", command=self.search).pack(side=tk.LEFT, padx=5, pady=5)
        
        if self.role == 'admin': # Создаем фрейм для полей ввода
            self.entry_frame = ttk.LabelFrame(self.root, text="Данные клиента", padding="10")
            self.entry_frame.pack(fill=tk.X, padx=10, pady=5)
            
            # Создаем поля ввода
            self.add_entries = {}
            self.create_entry_fields()
        
        # Создаем фрейм для таблицы с меткой "Данные в базе"
        self.tree_frame = ttk.LabelFrame(self.root, text="Данные в базе", padding="5")
        self.tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Создаем панель с кнопками внутри фрейма таблицы
        buttons_frame = ttk.Frame(self.tree_frame)
        buttons_frame.pack(fill=tk.X, padx=5, pady=5)
        
        if self.role == 'admin':
            # Инициализируем кнопки как атрибуты класса
            self.add_button = ttk.Button(buttons_frame, text="Добавить", command=self.add_client)
            self.add_button.pack(side=tk.LEFT, padx=5)
            
            self.edit_button = ttk.Button(buttons_frame, text="Редактировать", command=self.edit_client)
            self.edit_button.pack(side=tk.LEFT, padx=5)
            
            self.delete_button = ttk.Button(buttons_frame, text="Удалить", command=self.delete_client)
            self.delete_button.pack(side=tk.LEFT, padx=5)
        
        if self.role == 'admin':
            # Кнопка сохранения изменений (изначально скрыта)
            self.save_changes_button = ttk.Button(buttons_frame, text="Сохранить изменения", command=self.save_changes)
        
        if self.role == 'admin':
            # Кнопка очистки полей
            self.clear_button = ttk.Button(buttons_frame, text="Очистить", command=self.clear_fields)
            self.clear_button.pack(side=tk.LEFT, padx=5)
        
        # Кнопка обновления справа
        ttk.Button(buttons_frame, text="Обновить/сбросить фильтр",
                  command=self.show_all_records).pack(side=tk.RIGHT, padx=5)
        
        # Кнопка экспорта в CSV только для админов
        if self.role == 'admin':
            ttk.Button(buttons_frame, text="Экспорт в CSV", 
                      command=self.export_to_csv).pack(side=tk.RIGHT, padx=5)
        
        # Кнопка звонка
        self.call_button = ttk.Button(buttons_frame, text="Позвонить", command=self.make_call)
        self.call_button.pack(side=tk.RIGHT, padx=5)
        
        # Настраиваем таблицу
        self.tree_frame_inner = ttk.Frame(self.tree_frame)
        self.tree_frame_inner.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Создаем вертикальную полосу прокрутки
        vsb = ttk.Scrollbar(self.tree_frame_inner, orient="vertical")
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Создаем горизонтальную полосу прокрутки
        hsb = ttk.Scrollbar(self.tree_frame_inner, orient="horizontal")
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Создаем таблицу с привязкой к обеим полосам прокрутки
        self.tree = ttk.Treeview(self.tree_frame_inner, yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        # Привязываем полосы прокрутки к таблице
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)
        
        # Определяем столбцы
        self.tree['columns'] = ('id', 'last_name', 'first_name', 'middle_name', 'birth_date',
                              'phone', 'email', 'address', 'tariff', 'balance', 'last_call', 'last_caller', 'last_offer',
                              'created_at', 'updated_at')
        
        # Форматируем столбцы
        self.tree.column('#0', width=0, stretch=tk.NO)
        self.tree.column('id', width=50, anchor=tk.CENTER)
        self.tree.column('last_name', width=100, anchor=tk.W)
        self.tree.column('first_name', width=100, anchor=tk.W)
        self.tree.column('middle_name', width=100, anchor=tk.W)
        self.tree.column('birth_date', width=100, anchor=tk.CENTER)
        self.tree.column('phone', width=100, anchor=tk.W)
        self.tree.column('email', width=150, anchor=tk.W)
        self.tree.column('address', width=200, anchor=tk.W)
        self.tree.column('tariff', width=100, anchor=tk.W)
        self.tree.column('balance', width=100, anchor=tk.E)
        self.tree.column('last_call', width=150, anchor=tk.CENTER)
        self.tree.column('last_caller', width=100, anchor=tk.W)
        self.tree.column('last_offer', width=200, anchor=tk.W)
        self.tree.column('created_at', width=150, anchor=tk.CENTER)
        self.tree.column('updated_at', width=150, anchor=tk.CENTER)
        
        # Устанавливаем заголовки
        self.tree.heading('id', text='ID', command=lambda: self.sort_column('id'))
        self.tree.heading('last_name', text='Фамилия', command=lambda: self.sort_column('last_name'))
        self.tree.heading('first_name', text='Имя', command=lambda: self.sort_column('first_name'))
        self.tree.heading('middle_name', text='Отчество', command=lambda: self.sort_column('middle_name'))
        self.tree.heading('birth_date', text='Дата рождения', command=lambda: self.sort_column('birth_date'))
        self.tree.heading('phone', text='Телефон', command=lambda: self.sort_column('phone'))
        self.tree.heading('email', text='Email', command=lambda: self.sort_column('email'))
        self.tree.heading('address', text='Адрес', command=lambda: self.sort_column('address'))
        self.tree.heading('tariff', text='Тариф', command=lambda: self.sort_column('tariff'))
        self.tree.heading('balance', text='Баланс', command=lambda: self.sort_column('balance'))
        self.tree.heading('last_call', text='Последний звонок', command=lambda: self.sort_column('last_call'))
        self.tree.heading('last_caller', text='Звонивший', command=lambda: self.sort_column('last_caller'))
        self.tree.heading('last_offer', text='Коммерческое предложение', command=lambda: self.sort_column('last_offer'))
        self.tree.heading('created_at', text='Создан', command=lambda: self.sort_column('created_at'))
        self.tree.heading('updated_at', text='Обновлен', command=lambda: self.sort_column('updated_at'))
        
        # Привязываем обработчики событий
        if self.role == 'admin':    
            self.tree.bind('<Double-1>', lambda e: self.edit_client())
        else:
        # Для неадминистраторов двойной клик не привязывается или привязывается к пустой функции
            self.tree.bind('<Double-1>', lambda e: None)

        self.tree.bind('<<TreeviewSelect>>', self.handle_selection)

        # Создаем фрейм для кнопок под таблицей
        bottom_buttons_frame = ttk.Frame(self.root)
        bottom_buttons_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Кнопка управления пользователями слева
        if self.role == 'admin':
            ttk.Button(bottom_buttons_frame, text="Управление пользователями",
                      command=self.open_user_management).pack(side=tk.LEFT, padx=5)
        
        # Кнопка выхода справа
        ttk.Button(bottom_buttons_frame, text="Выход",
                  command=self.logout).pack(side=tk.RIGHT, padx=5)

    def show_all_records(self):
        """Отображает все записи в таблице"""
        # Очищаем таблицу
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Получаем все записи из базы данных
        records = self.client_manager.get_all_clients()
        
        # Добавляем записи в таблицу
        for record in records:
            # Преобразуем запись в список значений
            values = []
            for field in ['id', 'last_name', 'first_name', 'middle_name', 'birth_date',
                         'phone', 'email', 'address', 'tariff', 'balance', 'last_call', 'last_caller', 'last_offer', 'created_at', 'updated_at']:
                value = record.get(field)
                
                # Форматируем даты и числа
                if field == 'birth_date' and value:
                    try:
                        date = datetime.strptime(str(value), '%Y-%m-%d')
                        value = date.strftime('%d.%m.%Y')
                    except ValueError:
                        pass
                elif field in ['last_call', 'created_at', 'updated_at'] and value:
                    try:
                        dt = datetime.strptime(str(value), '%Y-%m-%d %H:%M:%S')
                        value = dt.strftime('%d.%m.%Y %H:%M:%S')
                    except ValueError:
                        pass
                elif field == 'balance' and value is not None:
                    value = f"{float(value):.2f}"
                
                values.append(value if value is not None else '')
            
            self.tree.insert('', 'end', values=values)

    def search(self):
        """Поиск клиентов по введенному запросу"""
        query = self.search_entry.get().strip()
        if not query:
            self.show_all_records()
            return
            
        # Очищаем таблицу
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Получаем результаты поиска
        clients = self.client_manager.search_clients(query)
        
        # Добавляем найденные записи в таблицу
        for client in clients:
            values = []
            for field in ['id', 'last_name', 'first_name', 'middle_name', 'birth_date',
                         'phone', 'email', 'address', 'tariff', 'balance', 'last_call', 'last_caller', 'last_offer', 'created_at', 'updated_at']:
                value = client.get(field)
                
                # Форматируем даты и числа
                if field == 'birth_date' and value:
                    try:
                        date = datetime.strptime(str(value), '%Y-%m-%d')
                        value = date.strftime('%d.%m.%Y')
                    except ValueError:
                        pass
                elif field in ['created_at', 'updated_at'] and value:
                    try:
                        dt = datetime.strptime(str(value), '%Y-%m-%d %H:%M:%S')
                        value = dt.strftime('%d.%m.%Y %H:%M:%S')
                    except ValueError:
                        pass
                elif field == 'balance' and value is not None:
                    value = f"{float(value):.2f}"
                
                values.append(value if value is not None else '')
            
            self.tree.insert('', 'end', values=values)

    def add_client(self):
        """Добавляет нового клиента в базу данных"""
        if self.role != 'admin':
            messagebox.showerror("Ошибка", "Недостаточно прав для добавления клиента")
        
        # Собираем данные из полей ввода
        info_data = {}
        financial_data = {}
        
        for field_name, entry in self.add_entries.items():
            if field_name in ['tariff', 'balance']:
                if field_name == 'tariff':
                    financial_data[field_name] = entry.get() or 'Стандарт'
                elif field_name == 'balance':
                    try:
                        value = entry.get().strip()
                        financial_data[field_name] = float(value) if value else 0.00
                    except ValueError:
                        messagebox.showerror("Ошибка", "Неверный формат баланса")
                        return
            else:
                if field_name == 'birth_date':
                    date_value = entry.get_date()
                    if date_value:
                        info_data[field_name] = date_value.strftime('%Y-%m-%d')
                    else:
                        info_data[field_name] = None
                else:
                    value = entry.get().strip()
                    info_data[field_name] = value if value else None
        
        # Проверяем обязательные поля
        if not info_data.get('last_name') or not info_data.get('first_name'):
            messagebox.showerror("Ошибка", "Фамилия и имя обязательны для заполнения")
            return
        
        # Добавляем дату создания и обновления
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        info_data['created_at'] = current_time
        info_data['updated_at'] = current_time
        
        # Добавляем клиента в базу данных
        if self.client_manager.add_client({**info_data, **financial_data}):
            messagebox.showinfo("Успех", "Клиент успешно добавлен")
            self.show_all_records()  # Обновляем отображение данных
            self.clear_fields()  # Очищаем поля после успешного добавления
        else:
            messagebox.showerror("Ошибка", "Не удалось добавить клиента")

    def delete_client(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Предупреждение", "Выберите клиента для удаления")
            return
            
        if messagebox.askyesno("Подтверждение", "Вы уверены, что хотите удалить этого клиента?"):
            client_id = self.tree.item(selected_item)['values'][0]
            if self.client_manager.delete_client(client_id):
                messagebox.showinfo("Успех", "Клиент успешно удален")
                self.show_all_records()
            else:
                messagebox.showerror("Ошибка", "Не удалось удалить клиента")

    def logout(self):
        self.root.destroy()
        login_window()

    def apply_light_theme(self):
        """Применяет светлую тему к элементам интерфейса"""
        style = ttk.Style()
        style.configure('TFrame', background='white')
        style.configure('TLabel', background='white')
        style.configure('TLabelframe', background='white')
        style.configure('TLabelframe.Label', background='white')  # Для заголовка LabelFrame
        style.configure('Treeview', background='white', fieldbackground='white')
        style.configure('TButton', background='white')
        style.configure('TEntry', fieldbackground='white')
        
        # Применяем стили к конкретным элементам
        self.add_frame.configure(style='TLabelframe')
        self.data_frame.configure(style='TLabelframe')
        self.tree_frame.configure(style='TFrame')
        self.edit_buttons_frame.configure(style='TFrame')
        
        # Настраиваем стиль для полей ввода
        for entry in self.add_entries.values():
            if isinstance(entry, CustomDateEntry):
                entry.configure(style='TEntry')

    def format_datetime(self, value):
        """Форматирует дату и время в зависимости от типа поля"""
        if not value:
            return ""
        try:
            if isinstance(value, str):
                # Пробуем разные форматы даты
                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d']:
                    try:
                        value = datetime.strptime(value, fmt)
                        break
                    except ValueError:
                        continue
            
            # Если это все еще строка, значит формат не распознан
            if isinstance(value, str):
                return value
            
            # Определяем формат вывода в зависимости от наличия времени
            if value.hour == 0 and value.minute == 0 and value.second == 0:
                return value.strftime('%d.%m.%Y')
            else:
                return value.strftime('%d.%m.%Y %H:%M:%S')
        except Exception:
            return str(value)

    def get_client_by_id(self, client_id):
        """Получает данные клиента по его ID из таблицы Treeview"""
        for item in self.tree.get_children():
            values = self.tree.item(item)['values']
            if values[0] == client_id:  # Первый элемент - это ID
                return values
        return None

    def edit_client(self):
        """Заполняет поля данными выбранного клиента для редактирования"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Предупреждение", "Выберите клиента для редактирования")
            return
        
        # Получаем данные выбранного клиента
        values = self.tree.item(selected[0])['values']
        if not values:
            return
            
        # Очищаем поля перед заполнением
        self.clear_fields()
        
        # Заполняем поля данными
        fields = ['last_name', 'first_name', 'middle_name', 'birth_date',
                 'phone', 'email', 'address', 'tariff', 'balance']
                 
        for i, field in enumerate(fields, 1):  # start=1 потому что первый элемент - id
            if field not in self.add_entries:
                continue
                
            entry = self.add_entries[field]
            if field == 'birth_date':
                # Преобразуем дату из формата ДД.ММ.ГГГГ в объект datetime
                date_str = values[i]
                if date_str:
                    try:
                        date = datetime.strptime(date_str, '%d.%m.%Y')
                        self.add_entries[field].set_date(date)
                    except ValueError:
                        self.add_entries[field].set_date(None)
                else:
                    self.add_entries[field].set_date(None)
            elif field == 'tariff':
                # Устанавливаем значение тарифа
                if values[i]:
                    self.add_entries[field].set(values[i])
                    if self.role != 'admin':
                        self.add_entries[field]['state'] = 'disabled'
                else:
                    self.add_entries[field].set('Стандарт')
            elif field == 'balance':
                # Устанавливаем значение баланса
                if values[i]:
                    self.add_entries[field].delete(0, tk.END)
                    self.add_entries[field].insert(0, str(values[i]))
                    if self.role != 'admin':
                        self.add_entries[field]['state'] = 'disabled'
            else:
                self.add_entries[field].delete(0, tk.END)
                if values[i]:
                    self.add_entries[field].insert(0, values[i])
        
        # Показываем кнопку сохранения изменений
        self.save_changes_button.pack(side=tk.LEFT, padx=5)
        
        # Сохраняем ID текущего редактируемого клиента
        self.current_edit_id = values[0]

    def save_changes(self):
        """Сохраняет изменения в данных клиента"""
        # Получаем ID выбранного клиента
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Предупреждение", "Выберите клиента для редактирования")
            return
        
        client_id = self.tree.item(selected[0])['values'][0]
        
        # Получаем текущие данные клиента
        current_data = self.client_manager.get_client_by_id(client_id)
        if not current_data:
            messagebox.showerror("Ошибка", "Клиент не найден")
            return
            
        # Определяем поля, доступные для редактирования в зависимости от роли
        info_fields = ['last_name', 'first_name', 'middle_name', 'birth_date',
                      'phone', 'email', 'address']
        financial_fields = ['tariff', 'balance']  # Всегда включаем финансовые поля
        
        # Собираем обновленные данные
        info_data = {'id': client_id}
        financial_data = {'client_id': client_id}
        
        # Копируем все текущие данные
        for field in current_data:
            if field in info_fields:
                info_data[field] = current_data[field]
            elif field in financial_fields:
                financial_data[field] = current_data[field]
        
        # Обновляем данные из полей ввода
        for field_name in info_fields + (financial_fields if self.role == 'admin' else []):
            if field_name not in self.add_entries:
                continue
                
            entry = self.add_entries[field_name]
            if field_name == 'birth_date':
                date_value = entry.get_date()
                if date_value:
                    info_data[field_name] = date_value.strftime('%Y-%m-%d')
                else:
                    info_data[field_name] = None
            elif field_name == 'balance' and self.role == 'admin':
                try:
                    value = entry.get().strip()
                    financial_data[field_name] = float(value) if value else 0.00
                except ValueError:
                    messagebox.showerror("Ошибка", "Неверный формат баланса")
                    return
            elif field_name == 'tariff' and self.role == 'admin':
                financial_data[field_name] = entry.get() or 'Стандарт'
            elif field_name in info_fields:
                value = entry.get().strip()
                info_data[field_name] = value if value else None
        
        # Если пользователь не админ, сохраняем текущие финансовые данные
        if self.role != 'admin':
            financial_data['tariff'] = current_data.get('tariff', 'Стандарт')
            financial_data['balance'] = current_data.get('balance', 0.00)
        
        # Проверяем обязательные поля
        if not info_data.get('last_name') or not info_data.get('first_name'):
            messagebox.showerror("Ошибка", "Фамилия и имя обязательны для заполнения")
            return
        
        # Добавляем дату обновления
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        info_data['updated_at'] = current_time
        financial_data['updated_at'] = current_time
        
        # Обновляем данные в базе
        if self.client_manager.update_client({**info_data, **financial_data}):
            messagebox.showinfo("Успех", "Данные успешно обновлены")
            self.show_all_records()
            self.clear_fields()  # Очищаем поля ввода
            self.save_changes_button.pack_forget()  # Скрываем кнопку сохранения
            self.current_edit_id = None  # Сбрасываем ID редактируемого клиента
        else:
            messagebox.showerror("Ошибка", "Не удалось обновить данные")
            
    def clear_fields(self):
        """Очищает все поля ввода"""
        for field, entry in self.add_entries.items():
            if field == 'birth_date':
                entry.delete(0, tk.END)
            elif field == 'tariff':
                if self.role == 'admin':
                    entry.set('')
                    entry['state'] = 'readonly'
                else:
                    entry.set('Стандарт')
                    entry['state'] = 'disabled'
            elif field == 'balance':
                entry.delete(0, tk.END)
                if self.role == 'admin':
                    entry['state'] = 'normal'
                else:
                    entry.insert(0, '0.00')
                    entry['state'] = 'disabled'
            else:
                entry.delete(0, tk.END)
        
        # Управляем видимостью кнопок
        if hasattr(self, 'save_changes_button'):
            self.save_changes_button.pack_forget()

    def handle_selection(self, event=None):
        """Обработчик выбора строки в таблице"""
        if self.role == 'admin':
            if hasattr(self, 'save_changes_button') and self.save_changes_button.winfo_ismapped():
                # Снимаем выделение со всех строк кроме редактируемой
                current_selection = self.tree.selection()
                if len(current_selection) > 0:
                    current_item = current_selection[0]
                    if current_item != self.current_edit_id:
                        self.tree.selection_remove(current_selection)
                        messagebox.showwarning("Предупреждение", "Завершите редактирование текущего клиента")
                return
        else:
            # Поведение для неадминистраторов при выборе строки
            pass  # Здесь можно добавить дополнительную логику, если необходимо

        # Общая логика для всех пользователей
        selected_items = self.tree.selection()
        if not selected_items:
            return

        item = selected_items[0]
        self.current_edit_id = item


    def sort_column(self, col):
        """Сортировка данных по столбцу"""
        # Инициализируем направление сортировки, если его нет
        if not hasattr(self, 'sort_direction'):
            self.sort_direction = {}
        
        if col not in self.sort_direction:
            self.sort_direction[col] = 'asc'
        else:
            self.sort_direction[col] = 'desc' if self.sort_direction[col] == 'asc' else 'asc'
        
        # Обновляем стрелки в заголовках
        for column in self.tree['columns']:
            header_text = self.tree.heading(column)['text']
            header_text = header_text.rstrip(' ↑↓')
            if column == col:
                arrow = ' ↑' if self.sort_direction[col] == 'asc' else ' ↓'
                self.tree.heading(column, text=header_text + arrow)
            else:
                self.tree.heading(column, text=header_text)
        
        # Получаем все элементы
        items = []
        for item in self.tree.get_children(''):
            value = self.tree.set(item, col)
            # Преобразуем значение в зависимости от типа столбца
            if col == 'id':
                # Преобразуем ID в число для правильной сортировки
                try:
                    sort_value = int(value)
                except ValueError:
                    sort_value = 0
            elif col == 'balance':
                # Преобразуем баланс в число для правильной сортировки
                try:
                    sort_value = float(value.replace(',', '.'))
                except ValueError:
                    sort_value = 0.0
            elif col == 'birth_date':
                # Преобразуем дату для правильной сортировки
                try:
                    if value:
                        sort_value = datetime.strptime(value, '%d.%m.%Y')
                    else:
                        # Если дата не указана, используем самую позднюю возможную дату
                        sort_value = datetime.max
                except ValueError:
                    sort_value = datetime.max
            else:
                sort_value = value
            items.append((sort_value, item))
        
        # Сортируем элементы
        items.sort(reverse=self.sort_direction[col] == 'desc')
        
        # Перемещаем элементы в отсортированном порядке
        for index, (_, item) in enumerate(items):
            self.tree.move(item, '', index)

    def create_entry_fields(self):
        """Создает поля ввода для данных клиента"""
        fields = [
            ('Фамилия:', 'last_name'),
            ('Имя:', 'first_name'),
            ('Отчество:', 'middle_name'),
            ('Дата рождения:', 'birth_date'),
            ('Телефон:', 'phone'),
            ('Email:', 'email'),
            ('Адрес:', 'address')
        ]
        
        if self.role == 'admin':
            fields.extend([
                ('Тариф:', 'tariff'),
                ('Баланс:', 'balance')
            ])
        
        # Создаем дополнительный фрейм для полей и меток
        fields_frame = ttk.Frame(self.entry_frame)
        fields_frame.pack(fill=tk.X, padx=5, pady=5)
        
        for i, (label_text, field_name) in enumerate(fields):
            # Создаем метку с выравниванием по левому краю
            label = ttk.Label(fields_frame, text=label_text)
            label.grid(row=i, column=0, padx=(5, 5), pady=2, sticky="w")
            
            if field_name == 'birth_date':
                entry = DateEntry(
                    fields_frame,
                    width=30,
                    background='white',
                    foreground='black',
                    borderwidth=2,
                    date_pattern='dd.mm.yyyy'
                )
                entry.delete(0, tk.END)  # Очищаем поле даты
            elif field_name == 'tariff':
                entry = ttk.Combobox(fields_frame, width=27, values=['Стандарт', 'Премиум'])
                entry.set('')  # Устанавливаем пустое значение
            elif field_name == 'balance':
                vcmd = (self.root.register(self.validate_float), '%P')
                entry = ttk.Entry(fields_frame, width=30, validate='key', validatecommand=vcmd)
            elif field_name == 'address':
                entry = ttk.Entry(fields_frame, width=100)
            else:
                entry = ttk.Entry(fields_frame, width=30)
            
            entry.grid(row=i, column=1, pady=2, sticky="w")
            self.add_entries[field_name] = entry
            
            
    def validate_float(self, value):
        """Проверяет, является ли введенное значение числом с плавающей точкой"""
        if value == "":
            return True
        try:
            float(value)
            return True
        except ValueError:
            return False

    def open_user_management(self):
        """Открывает окно управления пользователями"""
        if self.role != 'admin':
            messagebox.showerror("Ошибка", "Недостаточно прав для управления пользователями")
            return
        
        # Создаем новое окно
        users_window = tk.Toplevel(self.root)
        users_window.title("Управление пользователями")
        users_window.minsize(600, 400)
        
        # Создаем фрейм для таблицы
        table_frame = ttk.Frame(users_window, padding="10")
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        # Создаем таблицу пользователей
        columns = ('username', 'role')
        tree = ttk.Treeview(table_frame, columns=columns, show='headings')
        
        # Настраиваем заголовки и выравнивание
        tree.heading('username', text='Имя пользователя', anchor=tk.W)
        tree.heading('role', text='Роль', anchor=tk.W)
        
        # Настраиваем столбцы
        tree.column('username', width=200, anchor=tk.W)
        tree.column('role', width=150, anchor=tk.W)
        
        # Добавляем скроллбар
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        # Размещаем элементы
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Создаем фрейм для кнопок
        button_frame = ttk.Frame(users_window, padding="10")
        button_frame.pack(fill=tk.X)
        
        # Добавляем кнопки
        ttk.Button(button_frame, text="Изменить роль", 
                  command=lambda: self.toggle_role(tree)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Удалить пользователя",
                  command=lambda: self.delete_user(tree)).pack(side=tk.LEFT, padx=5)
        
        def refresh():
            """Обновляет список пользователей"""
            for item in tree.get_children():
                tree.delete(item)
            
            users = self.user_manager.get_all_users()
            for user in users:
                tree.insert('', 'end', values=(user['username'], user['role']))
        
        # Добавляем кнопку обновления
        ttk.Button(button_frame, text="Обновить",
                  command=refresh).pack(side=tk.RIGHT, padx=5)
        
        # Заполняем таблицу начальными данными
        refresh()
        
        # Центрируем окно на экране
        center_window(users_window)
        
        # Делаем окно модальным
        users_window.transient(self.root)
        users_window.grab_set()
        self.root.wait_window(users_window)

    def toggle_role(self, tree):
        """Изменяет роль выбранного пользователя"""
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("Предупреждение", "Выберите пользователя")
            return
            
        user_data = tree.item(selected)['values']
        new_role = 'Работник' if user_data[1] == 'admin' else 'admin'
        
        if self.user_manager.update_user_role(user_data[0], new_role):
            messagebox.showinfo("Успех", f"Роль пользователя изменена на {new_role}")
            # Обновляем отображение
            for item in tree.get_children():
                tree.delete(item)
            users = self.user_manager.get_all_users()
            for user in users:
                tree.insert('', 'end', values=(user['username'], user['role']))
        else:
            messagebox.showerror("Ошибка", "Не удалось изменить роль")

    def delete_user(self, tree):
        """Удаляет выбранного пользователя"""
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("Предупреждение", "Выберите пользователя")
            return
            
        user_data = tree.item(selected)['values']
        if messagebox.askyesno("Подтверждение", f"Удалить пользователя {user_data[0]}?"):
            if self.user_manager.delete_user(user_data[0]):
                messagebox.showinfo("Успех", "Пользователь удален")
                # Обновляем отображение
                for item in tree.get_children():
                    tree.delete(item)
                users = self.user_manager.get_all_users()
                for user in users:
                    tree.insert('', 'end', values=(user['username'], user['role']))
            else:
                messagebox.showerror("Ошибка", "Не удалось удалить пользователя")

    def refresh_table_data(self):
        """Обновление данных в таблице"""
        # Очищаем таблицу
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # Получаем данные из базы
        clients = self.client_manager.get_all_clients()
        
        # Добавляем данные в таблицу
        for client in clients:
            # Форматируем даты
            birth_date = datetime.strptime(client['birth_date'], '%Y-%m-%d').strftime('%d.%m.%Y') if client['birth_date'] else ''
            created_at = datetime.strptime(client['created_at'], '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y %H:%M:%S') if client['created_at'] else ''
            updated_at = datetime.strptime(client['updated_at'], '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y %H:%M:%S') if client['updated_at'] else ''
            
            # Вставляем данные
            self.tree.insert('', 'end', iid=client['id'], values=(
                client['id'],
                client['last_name'],
                client['first_name'],
                client['middle_name'],
                birth_date,
                client['phone'],
                client['email'],
                client['address'],
                client['tariff'],
                client['balance'],
                client['last_call'],
                client['last_caller'],
                client['last_offer'],
                created_at,
                updated_at
            ))

    def export_to_csv(self):
        """Экспортирует данные таблицы в CSV файл"""
        # Получаем все записи из таблицы
        records = []
        for item in self.tree.get_children():
            records.append(self.tree.item(item)['values'])
        
        if not records:
            messagebox.showwarning("Предупреждение", "Нет данных для экспорта")
            return
        
        # Открываем диалог сохранения файла
        file_path = filedialog.asksaveasfilename(
            defaultextension='.csv',
            filetypes=[('CSV files', '*.csv'), ('All files', '*.*')],
            title="Сохранить как CSV"
        )
        
        if not file_path:
            return
            
        try:
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.writer(csvfile, delimiter=';')
                
                # Записываем заголовки
                headers = ['ID', 'Фамилия', 'Имя', 'Отчество', 'Дата рождения',
                          'Телефон', 'Email', 'Адрес', 'Тариф', 'Баланс', 'Последний звонок', 'Звонивший', 'Коммерческое предложение', 'Создан', 'Обновлен']
                writer.writerow(headers)
                
                # Записываем данные
                for record in records:
                    writer.writerow(record)
                    
            messagebox.showinfo("Успех", "Данные успешно экспортированы в CSV")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось экспортировать данные: {str(e)}")

    def make_call(self):
        """Обрабатывает нажатие на кнопку звонка"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Пожалуйста, выберите клиента")
            return
            
        client_id = self.tree.item(selection[0])['values'][0]
        
        # Создаем окно выбора акции
        offer_window = tk.Toplevel(self.root)
        offer_window.title("Выберите акцию")
        offer_window.geometry("400x300")
        
        # Делаем окно модальным
        offer_window.transient(self.root)
        offer_window.grab_set()
        
        # Центрируем окно
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - 400) // 2
        y = (screen_height - 300) // 2
        offer_window.geometry(f"400x300+{x}+{y}")
        
        # Создаем фрейм для списка акций
        frame = ttk.Frame(offer_window, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Создаем список акций
        offer_listbox = tk.Listbox(frame, selectmode=tk.SINGLE)
        offer_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Получаем список акций из базы
        with DatabaseManager() as db:
            db.cursor.execute('SELECT offer_text FROM promotions')
            promotions = db.cursor.fetchall()
            
        # Добавляем акции в список
        for promo in promotions:
            offer_listbox.insert(tk.END, promo[0])
            
        def confirm_offer():
            selection = offer_listbox.curselection()
            if not selection:
                messagebox.showwarning("Предупреждение", "Пожалуйста, выберите акцию")
                return
                
            selected_offer = offer_listbox.get(selection[0])
            current_time = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
            
            try:
                with DatabaseManager() as db:
                    db.cursor.execute('''
                        UPDATE client_info 
                        SET last_call = ?, last_caller = ?, last_offer = ?
                        WHERE id = ?
                    ''', (current_time, self.username, selected_offer, client_id))
                    db.conn.commit()
                    
                # Обновляем отображение в таблице
                self.show_all_records()
                messagebox.showinfo("Успех", "Звонок зарегистрирован")
                offer_window.destroy()
                
            except sqlite3.Error as e:
                messagebox.showerror("Ошибка", f"Не удалось обновить информацию о звонке: {e}")
                
        # Добавляем кнопку подтверждения
        ttk.Button(frame, text="Подтвердить", command=confirm_offer).pack(pady=10)

def login_window():
    root = tk.Tk()
    root.title("Авторизация")
    root.minsize(300, 200)
    root.resizable(False, False)
    
    # Настройка стилей
    style = ttk.Style()
    bg_color = "#f0f0f0"
    fg_color = "#333333"
    button_bg = "#ffffff"
    selected_bg = "#e1e1e1"
    
    style.configure("Auth.TFrame",
                   background=bg_color)
    style.configure("Auth.TLabel",
                   background=bg_color,
                   foreground=fg_color)
    style.configure("Auth.TButton",
                   background=button_bg,
                   foreground=fg_color,
                   padding=5)
    style.map("Auth.TButton",
              background=[('active', selected_bg)],
              foreground=[('active', fg_color)])
    
    root.configure(bg=bg_color)
    
    # Основной фрейм
    main_frame = ttk.Frame(root, style="Auth.TFrame")
    main_frame.place(relx=0.5, rely=0.5, anchor="center")
    
    # Фрейм для полей ввода
    input_frame = ttk.Frame(main_frame, style="Auth.TFrame")
    input_frame.pack(pady=10)
    
    # Поля для ввода логина и пароля
    ttk.Label(input_frame, text="Логин:", style="Auth.TLabel").grid(row=0, column=0, padx=5, pady=5, sticky="e")
    username_entry = ttk.Entry(input_frame)
    username_entry.grid(row=0, column=1, padx=5, pady=5)
    
    ttk.Label(input_frame, text="Пароль:", style="Auth.TLabel").grid(row=1, column=0, padx=5, pady=5, sticky="e")
    password_entry = ttk.Entry(input_frame, show="*")
    password_entry.grid(row=1, column=1, padx=5, pady=5)
    
    # Фрейм для кнопок
    button_frame = ttk.Frame(main_frame, style="Auth.TFrame")
    button_frame.pack(pady=10)
    
    def check_login():
        username = username_entry.get().strip()
        password = password_entry.get().strip()
        
        success, role = UserManager.verify_user(username, password)
        if success:
            root.destroy()
            new_root = tk.Tk()
            app = ClientApp(new_root, username, role)
            new_root.mainloop()
        else:
            messagebox.showerror("Ошибка", "Неверный логин или пароль")
    
    def show_registration():
        """Показывает окно регистрации"""
        # Закрываем окно входа
        root.destroy()
        
        # Создаем новое окно регистрации
        reg_window = tk.Tk()
        reg_window.title("Регистрация")
        reg_window.resizable(False, False)
        
        # Создаем и размещаем элементы интерфейса
        frame = ttk.Frame(reg_window, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Логин:").pack(fill=tk.X, pady=(0, 5))
        username_entry = ttk.Entry(frame)
        username_entry.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(frame, text="Пароль:").pack(fill=tk.X, pady=(0, 5))
        password_entry = ttk.Entry(frame, show="*")
        password_entry.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(frame, text="Повторите пароль:").pack(fill=tk.X, pady=(0, 5))
        confirm_entry = ttk.Entry(frame, show="*")
        confirm_entry.pack(fill=tk.X, pady=(0, 20))
        
        def register():
            """Обрабатывает регистрацию пользователя"""
            username = username_entry.get().strip()
            password = password_entry.get()
            confirm = confirm_entry.get()
            
            if not username or not password:
                messagebox.showerror("Ошибка", "Все поля должны быть заполнены")
                return
                
            if password != confirm:
                messagebox.showerror("Ошибка", "Пароли не совпадают")
                return
                
            if UserManager.create_user(username, password):
                messagebox.showinfo("Успех", "Регистрация успешна")
                reg_window.destroy()
                login_window()
            else:
                messagebox.showerror("Ошибка", "Пользователь уже существует")
        
        def back_to_login():
            """Возвращает к окну входа"""
            reg_window.destroy()
            login_window()
        
        # Создаем фрейм для кнопок
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(button_frame, text="Регистрация", command=register).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Назад", command=back_to_login).pack(side=tk.LEFT)
        
        # Центрируем окно на экране
        center_window(reg_window)
        
        reg_window.mainloop()
    
    ttk.Button(button_frame, text="Войти", command=check_login, style="Auth.TButton").pack(side=tk.TOP, pady=5)
    ttk.Button(button_frame, text="Регистрация", command=show_registration, style="Auth.TButton").pack(side=tk.TOP, pady=5)
    
    # Привязываем Enter к функции входа
    root.bind('<Return>', lambda event: check_login())
    username_entry.bind('<Return>', lambda event: check_login())
    password_entry.bind('<Return>', lambda event: check_login())
    
    # Центрируем главное окно на экране
    center_window(root)
    
    root.mainloop()

if __name__ == "__main__":
    init_database()  
    login_window()
