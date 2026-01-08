"""
QServeU Mobile App - FINAL + FEEDBACK
- Added 'Rate Your Experience' screen
- Interactive Star Rating logic
- Checks for unrated completed queues automatically
"""

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner, SpinnerOption
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.graphics import Color, RoundedRectangle, Rectangle, Line
from kivy.core.window import Window
from kivymd.app import MDApp
from kivymd.uix.snackbar import Snackbar
from kivymd.uix.button import MDIconButton
import os
from dotenv import load_dotenv

# --- IMPORTS FROM UTILS ---
from utils.database import MobileDatabase
from utils.wifi_detector import WiFiDetector
from utils.notifications import NotificationManager
from kivymd.uix.button import MDFillRoundFlatIconButton
from kivy.core.text import LabelBase

load_dotenv()

# Force Window Size (Mobile Ratio)
Window.size = (360, 640)
Window.clearcolor = (0.96, 0.97, 0.98, 1)


LabelBase.register(name="Poppins",
                   fn_regular="Poppins-Regular.ttf",
                   fn_bold="Poppins-Bold.ttf")

# 2. Define your theme color (from previous chat)
THEME_COLOR = (10/255, 135/255, 84/255, 1)
# ==================== CUSTOM UI COMPONENTS ====================

class RoundedButton(Button):
    def __init__(self, bg_color=THEME_COLOR, radius=[20], **kwargs):
        super().__init__(**kwargs)
        self.font_name = 'Poppins'  # <--- ADDED THIS
        self.background_normal = ''
        self.background_down = ''
        self.background_color = (0, 0, 0, 0)
        self.custom_bg_color = bg_color
        self.radius = radius
        self.bind(pos=self.update_rect, size=self.update_rect, state=self.update_rect)

    def update_rect(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            if self.state == 'down':
                r, g, b, a = self.custom_bg_color
                Color(r * 0.8, g * 0.8, b * 0.8, a)
            else:
                Color(*self.custom_bg_color)
            RoundedRectangle(pos=self.pos, size=self.size, radius=self.radius)

class CustomSpinnerOption(SpinnerOption):
    """Styles the dropdown list items"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.font_name = 'Poppins'
        self.font_size = '11sp'       # <--- Smaller font size (was default/big)
        self.background_normal = ''
        self.background_color = (0.95, 0.95, 0.95, 1)
        self.color = (0, 0, 0, 1)
        self.height = 65              # <--- Taller to fit 2 lines of text
        self.halign = 'center'        # <--- Center text
        self.valign = 'middle'        # <--- Align to middle vertical
        self.bind(size=self.update_text_size)

    def update_text_size(self, *args):
        # This forces the text to wrap inside the button width
        self.text_size = (self.width - 20, None)

class RoundedSpinner(Spinner):
    def __init__(self, bg_color=(0.6, 0.6, 0.6, 1), **kwargs):
        super().__init__(**kwargs)
        self.font_name = 'Poppins'       # <--- ADDED THIS
        self.option_cls = CustomSpinnerOption  # <--- ADDED THIS
        self.background_normal = ''
        self.background_down = ''
        self.background_color = (0, 0, 0, 0)
        self.custom_bg_color = bg_color
        self.bind(pos=self.update_rect, size=self.update_rect, state=self.update_rect)

    def update_rect(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            if self.state == 'down':
                r, g, b, a = self.custom_bg_color
                Color(r * 0.8, g * 0.8, b * 0.8, a)
            else:
                Color(*self.custom_bg_color)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[9])

class RoundedInput(TextInput):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.font_name = 'Poppins'  # <--- ADDED THIS
        self.background_normal = ''
        self.background_active = ''
        self.background_disabled_normal = ''
        self.background_color = (0, 0, 0, 0)
        self.write_tab = False
        self.cursor_color = THEME_COLOR
        self.foreground_color = (0, 0, 0, 1)
        self.hint_text_color = (0.5, 0.5, 0.5, 1)
        self.padding = [20, 15, 20, 15]
        self.bind(pos=self.update_graphics, size=self.update_graphics, focus=self.on_focus)
        Clock.schedule_once(self.update_graphics)

    def on_focus(self, instance, value):
        self.update_graphics()

    def update_graphics(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(1, 1, 1, 1)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[25])
            if self.focus:
                Color(*THEME_COLOR)
                Line(rounded_rectangle=(self.x, self.y, self.width, self.height, 25), width=1.3)
            else:
                Color(0.6, 0.6, 0.6, 1)
                Line(rounded_rectangle=(self.x, self.y, self.width, self.height, 25), width=1)

# ==================== BASE SCREEN ====================

class BaseScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(0.96, 0.97, 0.98, 1)
            self.bg_rect = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self.update_bg, pos=self.update_bg)

    def update_bg(self, *args):
        self.bg_rect.size = self.size
        self.bg_rect.pos = self.pos

# ==================== SCREENS ====================

class LoadingScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'loading'

        # 1. Create the Rectangle
        with self.canvas.before:
            Color(*THEME_COLOR)
            self.bg_rect = Rectangle(size=self.size, pos=self.pos)

        # 2. Bind it to the screen size (Fixes the white line/gap)
        self.bind(size=self.update_bg, pos=self.update_bg)

        # The Logo
        logo = Image(
            source='qserveulogoname.png',
            size_hint=(0.7, 0.3),
            pos_hint={'center_x': 0.5, 'center_y': 0.55},
            fit_mode="contain"
        )
        self.add_widget(logo)

        Clock.schedule_once(lambda dt: setattr(self.manager, 'current', 'login'), 3.3)

    # 3. This function ensures the background stretches when the window changes
    def update_bg(self, *args):
        self.bg_rect.size = self.size
        self.bg_rect.pos = self.pos

        # 3. Loading Time set to 4 seconds
        # You can change '4' to any number of seconds you want
        Clock.schedule_once(lambda dt: setattr(self.manager, 'current', 'login'), 3)


class LoginScreen(BaseScreen):
    def __init__(self, db, **kwargs):
        super().__init__(**kwargs)
        self.name = 'login'
        self.db = db
        layout = BoxLayout(orientation='vertical', padding=30, spacing=20)
        logo = Label(font_name='Poppins', text='QServeU', font_size='42sp', color=(0.2, 0.7, 0.4, 1), bold=True, size_hint=(1, 0.15))
        subtitle = Label(font_name='Poppins',text='Student Portal', font_size='16sp', color=(0.5, 0.5, 0.5, 1), size_hint=(1, 0.05))
        self.student_num = RoundedInput(hint_text='Email / Student ID', multiline=False, size_hint=(1, None), height=55)
        self.password = RoundedInput(hint_text='Password', password=True, multiline=False, size_hint=(1, None), height=55)
        login_btn = RoundedButton(text='LOGIN', size_hint=(1, None), height=60, bold=True, bg_color=(0.2, 0.7, 0.4, 1))
        login_btn.bind(on_press=self.do_login)
        register_btn = Button(text='Register Here', size_hint=(1, None), height=45, background_normal='',
                              background_color=(0, 0, 0, 0), color=(0.2, 0.7, 0.4, 1))
        register_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'register'))
        layout.add_widget(Label(size_hint=(1, 0.05)))
        layout.add_widget(logo)
        layout.add_widget(subtitle)
        layout.add_widget(Label(size_hint=(1, 0.1)))
        layout.add_widget(self.student_num)
        layout.add_widget(self.password)
        layout.add_widget(Label(size_hint=(1, 0.05)))
        layout.add_widget(login_btn)
        layout.add_widget(register_btn)
        layout.add_widget(Label(size_hint=(1, 0.15)))
        self.add_widget(layout)

    def do_login(self, instance):
        identifier = self.student_num.text.strip()
        password = self.password.text
        if not identifier or not password:
            Snackbar(text="Please fill all fields").open()
            return
        result = self.db.login_student(identifier, password)
        if result['success']:
            app = App.get_running_app()
            app.current_student = result['student']
            Snackbar(text="Login successful!").open()
            self.manager.current = 'choose_office'
        else:
            Snackbar(text=result['message']).open()


class RegisterScreen(BaseScreen):
    def __init__(self, db, **kwargs):
        super().__init__(**kwargs)
        self.name = 'register'
        self.db = db
        scroll = ScrollView()
        layout = BoxLayout(orientation='vertical', padding=30, spacing=15, size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))

        title = Label(font_name='Poppins', text='Create Account', font_size='32sp', color=(0.2, 0.7, 0.4, 1), bold=True,
                      size_hint=(1, None), height=70)

        # --- INPUTS ---
        # Note: You can also add font_size='15sp' here if you want the inputs to match
        self.student_num = RoundedInput(hint_text='Student Number', size_hint=(1, None), height=55)
        self.fullname = RoundedInput(hint_text='Full Name', size_hint=(1, None), height=55)
        self.email = RoundedInput(hint_text='Email Address', size_hint=(1, None), height=55)

        course_values = ('Bachelor Of Arts In Journalism', 'Bachelor Of Elementary Education',
                         'Bachelor Of Science In Business Administration', 'Bachelor Of Science In Computer Science',
                         'Bachelor Of Science In Hospitality Management',
                         'Bachelor Of Science In Information Technology',
                         'Bachelor Of Science In Office Administration', 'Bachelor Of Science In Psychology',
                         'Bachelor Of Secondary Education')

        # 1. ADDED font_size='15sp' TO COURSE SPINNER
        self.course = RoundedSpinner(text='Select Course', values=course_values, size_hint=(1, None), height=55,
                                     font_size='12sp')

        year_values = ('1st Year', '2nd Year', '3rd Year', '4th Year', 'Graduate')

        # 2. ADDED font_size='15sp' TO YEAR SPINNER
        self.year = RoundedSpinner(text='Select Year Level', values=year_values, size_hint=(1, None), height=55,
                                   font_size='12sp')

        self.password = RoundedInput(hint_text='Password', password=True, size_hint=(1, None), height=55)
        self.confirm = RoundedInput(hint_text='Confirm Password', password=True, size_hint=(1, None), height=55)

        # --- BUTTONS ---
        # 3. ADDED font_size='15sp' TO REGISTER BUTTON
        register_btn = RoundedButton(text='REGISTER', size_hint=(1, None), height=60, bold=True, font_size='12sp')
        register_btn.bind(on_press=self.do_register)

        # 4. ADDED font_size='15sp' TO BACK BUTTON
        back_btn = Button(text='Back to Login', size_hint=(1, None), height=45, background_normal='',
                          background_color=(0, 0, 0, 0), color=(0.2, 0.7, 0.4, 1), font_size='12sp')
        back_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'login'))

        widgets = [title, self.student_num, self.fullname, self.email, self.course,
                   self.year, self.password, self.confirm,
                   Label(size_hint=(1, None), height=20), register_btn, back_btn,
                   Label(size_hint=(1, None), height=40)]

        for w in widgets:
            layout.add_widget(w)

        scroll.add_widget(layout)
        self.add_widget(scroll)

    def do_register(self, instance):
        # 1. Validation
        if not all([self.fullname.text, self.student_num.text, self.password.text, self.email.text]):
            Snackbar(text="Fill all required fields").open()
            return

        if "@" not in self.email.text or "." not in self.email.text:
            Snackbar(text="Invalid Email Address").open()
            return

        if self.course.text == 'Select Course' or self.year.text == 'Select Year Level':
            Snackbar(text="Please select course and year").open()
            return

        if self.password.text != self.confirm.text:
            Snackbar(text="Passwords don't match").open()
            return

        # 2. Data Preparation
        student_data = {
            'student_id': self.student_num.text.strip(),
            'full_name': self.fullname.text.strip(),
            'email': self.email.text.strip(),  # <-- Sends real email now
            'password': self.password.text,
            'course': self.course.text,
            'year_level': self.year.text
        }

        # 3. Send to DB
        result = self.db.register_student(student_data)

        if result['success']:
            Snackbar(text="Registration successful! Please login.").open()
            self.manager.current = 'login'
        else:
            Snackbar(text=result['message']).open()


class ChooseOfficeScreen(BaseScreen):
    def __init__(self, db, **kwargs):
        super().__init__(**kwargs)
        self.name = 'choose_office'
        self.db = db
        layout = BoxLayout(orientation='vertical', padding=25, spacing=25)
        header = Label(font_name='Poppins', text='Choose Office', font_size='28sp', color=(0.2, 0.7, 0.4, 1),
                      bold=True, size_hint=(1, 0.15))
        self.office_container = BoxLayout(orientation='vertical', spacing=15, size_hint=(1, 0.7))
        layout.add_widget(header)
        layout.add_widget(self.office_container)
        layout.add_widget(Label(size_hint=(1, 0.15)))
        self.add_widget(layout)

    def on_enter(self):
        self.office_container.clear_widgets()
        offices = self.db.get_offices()
        if not offices:
             self.office_container.add_widget(Label(font_name='Poppins', text="No offices found", color=(0,0,0,1)))
             return
        for office in offices:
            name = office.get('name', 'Office') if isinstance(office, dict) else office.name
            btn = RoundedButton(text=name.upper(), size_hint=(1, None), height=70,
                                bg_color=(0.2, 0.7, 0.4, 1), bold=True, font_size='18sp')
            btn.bind(on_press=lambda x, o=office: self.select_office(o))
            self.office_container.add_widget(btn)

    def select_office(self, office):
        app = App.get_running_app()
        app.selected_office = office
        if 'queue_prefix' not in app.selected_office:
             app.selected_office['queue_prefix'] = office['name'][0].upper()
        self.manager.current = 'home'


class HomeScreen(BaseScreen):
    def __init__(self, db, wifi, notifier, **kwargs):
        super().__init__(**kwargs)
        self.name = 'home'
        self.db = db
        self.wifi = wifi
        self.notifier = notifier
        self.wifi_check_event = None
        layout = BoxLayout(orientation='vertical')

        # --- Top Panel ---
        top_panel = BoxLayout(orientation='vertical', size_hint=(1, 0.25), padding=10, spacing=5)
        with top_panel.canvas.before:
            Color(0.2, 0.7, 0.4, 1) # Fallback if theme not set
            Rectangle(size=top_panel.size, pos=top_panel.pos)
        def update_top(instance, value):
            instance.canvas.before.clear()
            with instance.canvas.before:
                Color(0.2, 0.7, 0.4, 1) # Use Theme Color
                Rectangle(size=instance.size, pos=instance.pos)
        top_panel.bind(size=update_top, pos=update_top)

        # --- Header Row (Home Icon/Text + Status) ---
        header_row = BoxLayout(size_hint=(1, 0.5), orientation='horizontal')

        # 1. Left Side: Home Icon + Text
        left_box = BoxLayout(orientation='horizontal', spacing=5, size_hint_x=0.6)

        home_icon = MDIconButton(
            icon="home",
            theme_text_color="Custom",
            text_color=(1, 1, 1, 1),
            size_hint=(None, None),
            size=("40dp", "40dp"),
            pos_hint={'center_y': 0.5}
        )

        home_label = Label(
            font_name='Poppins',
            text='Home',
            font_size='22sp',
            color=(1, 1, 1, 1),
            bold=True,
            halign='left',
            valign='middle'
        )
        home_label.bind(size=home_label.setter('text_size'))

        left_box.add_widget(home_icon)
        left_box.add_widget(home_label)

        # 2. Right Side: Office Prefix + Wifi Icon
        status_box = BoxLayout(orientation='horizontal', spacing=0, size_hint_x=0.4)

        # Spacer to push content to the right
        status_box.add_widget(Label(size_hint_x=1))

        self.office_label = Label(
            font_name='Poppins',
            text='',
            font_size='24sp',
            color=(1, 1, 1, 1),
            bold=True,
            size_hint=(None, None),
            size=("50dp", "40dp"), # Fixed width to prevent jitter
            halign='right',
            valign='middle',
            pos_hint={'center_y': 0.5}
        )
        self.office_label.bind(size=self.office_label.setter('text_size'))

        self.wifi_label = MDIconButton(
            icon="wifi",
            theme_text_color="Custom",
            text_color=(1, 1, 1, 1),
            font_size="24sp",
            size_hint=(None, None),
            size=("40dp", "40dp"),
            pos_hint={'center_y': 0.5} # Critical for alignment
        )

        status_box.add_widget(self.office_label)
        status_box.add_widget(self.wifi_label)

        header_row.add_widget(left_box)
        header_row.add_widget(status_box)

        # --- Welcome Label ---
        self.welcome_label = Label(
            font_name='Poppins',
            text='Welcome!',
            font_size='16sp',
            color=(1, 1, 1, 1),
            size_hint=(1, 0.5),
            valign='top', # Align top to sit nicely under header
            halign='center'
        )
        self.welcome_label.bind(size=self.welcome_label.setter('text_size'))

        top_panel.add_widget(header_row)
        top_panel.add_widget(self.welcome_label)

        # --- Middle & Bottom Sections (Unchanged) ---
        middle = BoxLayout(orientation='vertical', size_hint=(1, 0.6), padding=25, spacing=20)
        request_btn = RoundedButton(text='REQUEST QUEUE', size_hint=(1, None), height=65,
                                   bg_color=(0.2, 0.7, 0.4, 1), bold=True, font_size='18sp')
        request_btn.bind(on_press=self.request_queue)
        update_btn = RoundedButton(text='UPDATE CREDENTIALS', size_hint=(1, None), height=65,
                                  bg_color=(0.3, 0.6, 0.8, 1), bold=True, font_size='17sp')
        update_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'update_credentials'))
        middle.add_widget(Label(size_hint=(1, 0.3)))
        middle.add_widget(request_btn)
        middle.add_widget(update_btn)
        middle.add_widget(Label(size_hint=(1, 0.3)))
        bottom_nav = self.create_bottom_nav(home_active=True)
        layout.add_widget(top_panel)
        layout.add_widget(middle)
        layout.add_widget(bottom_nav)
        self.add_widget(layout)

    def create_bottom_nav(self, home_active=False):
        bottom_nav = BoxLayout(size_hint=(1, 0.15), padding=0, spacing=0)
        with bottom_nav.canvas.before:
            Color(1, 1, 1, 1)
            Rectangle(size=bottom_nav.size, pos=bottom_nav.pos)
        def update_nav_bg(instance, value):
            instance.canvas.before.clear()
            with instance.canvas.before:
                Color(1, 1, 1, 1)
                Rectangle(size=instance.size, pos=instance.pos)
        bottom_nav.bind(size=update_nav_bg, pos=update_nav_bg)
        def create_nav_btn(icon, active, callback):
            container = AnchorLayout(size_hint_x=1)
            color = (0.2, 0.7, 0.4, 1) if active else (0.6, 0.6, 0.6, 1)
            btn = MDIconButton(icon=icon, font_size="30sp", theme_text_color="Custom", text_color=color)
            btn.bind(on_press=callback)
            container.add_widget(btn)
            return container
        bottom_nav.add_widget(create_nav_btn("home", home_active, lambda x: setattr(self.manager, 'current', 'home')))
        bottom_nav.add_widget(create_nav_btn("ticket-account", False, lambda x: setattr(self.manager, 'current', 'queue_status')))
        bottom_nav.add_widget(create_nav_btn("logout", False, self.logout))
        return bottom_nav

    def on_enter(self):
        app = App.get_running_app()
        if app.current_student:
             self.welcome_label.text = f"Welcome, {app.current_student['full_name']}!"
        if hasattr(app, 'selected_office') and app.selected_office:
            prefix = app.selected_office.get('queue_prefix', 'Q')
            self.office_label.text = prefix
            if self.wifi_check_event: self.wifi_check_event.cancel()
            self.check_wifi()
            self.wifi_check_event = Clock.schedule_interval(self.check_wifi, 2)

    def on_leave(self):
        if self.wifi_check_event:
            self.wifi_check_event.cancel()

    def check_wifi(self, dt=None):
        app = App.get_running_app()
        if hasattr(app, 'selected_office') and app.selected_office:
            ssid = app.selected_office.get('ssid', '')
            status = self.wifi.get_connection_status(ssid)
            connected = status['connected']
            self.wifi_label.icon = "wifi" if connected else "wifi-off"
            self.wifi_label.text_color = (1, 1, 1, 1) if connected else (1, 1, 1, 0.5)
            self.office_label.color = (1, 1, 1, 1) if connected else (1, 1, 1, 0.5)

    def request_queue(self, instance):
        app = App.get_running_app()
        if not hasattr(app, 'selected_office') or not app.selected_office:
            Snackbar(text="Please select an office first").open()
            return
        ssid = app.selected_office.get('ssid', '')
        status = self.wifi.get_connection_status(ssid)
        if not status['connected']:
             Snackbar(text=f"Please connect to {ssid}").open()
             return
        result = self.db.create_queue(
            app.current_student['id'],
            app.selected_office['id'],
            "General Transaction"
        )
        if result['success']:
            app.current_queue = result['queue']
            self.notifier.send_notification(
                "Queue Created",
                f"Your queue number: {result['queue']['queue_number']}"
            )
            self.show_success_popup(result['queue']['queue_number'], result['queue']['people_ahead'])
        else:
            Snackbar(text=result['message']).open()

    def show_success_popup(self, queue_number, people_ahead):
        content = BoxLayout(orientation='vertical', padding=20, spacing=15)
        with content.canvas.before:
            Color(1, 1, 1, 1)
            RoundedRectangle(size=content.size, pos=content.pos, radius=[20])
        def update_rect(instance, value):
            instance.canvas.before.clear()
            with instance.canvas.before:
                Color(1, 1, 1, 1)
                RoundedRectangle(size=instance.size, pos=instance.pos, radius=[20])
        content.bind(size=update_rect, pos=update_rect)
        lbl_title = Label(font_name='Poppins', text="Queue Created!", font_size='24sp', color=(0.2, 0.7, 0.4, 1), bold=True, size_hint=(1, 0.2))
        lbl_number = Label(font_name='Poppins', text=str(queue_number), font_size='64sp', color=(0.1, 0.1, 0.1, 1), bold=True, size_hint=(1, 0.4))
        lbl_info = Label(font_name='Poppins', text=f"{people_ahead} people ahead of you", font_size='16sp', color=(0.5, 0.5, 0.5, 1), size_hint=(1, 0.2))
        btn_ok = RoundedButton(font_name='Poppins', text="GOT IT", size_hint=(1, None), height=55, bg_color=(0.2, 0.7, 0.4, 1), bold=True)
        content.add_widget(lbl_title)
        content.add_widget(lbl_number)
        content.add_widget(lbl_info)
        content.add_widget(btn_ok)
        popup = Popup(title='', separator_height=0, content=content, size_hint=(0.85, 0.55),
                     background_color=(0,0,0,0.5), background='')
        btn_ok.bind(on_press=lambda x: [popup.dismiss(), setattr(self.manager, 'current', 'queue_status')])
        popup.open()

    def logout(self, instance):
        content = BoxLayout(orientation='vertical', padding=25, spacing=15)
        with content.canvas.before:
            Color(1, 1, 1, 1)
            RoundedRectangle(size=content.size, pos=content.pos, radius=[20])
        def update_rect(instance, value):
            instance.canvas.before.clear()
            with instance.canvas.before:
                Color(1, 1, 1, 1)
                RoundedRectangle(size=instance.size, pos=instance.pos, radius=[20])
        content.bind(size=update_rect, pos=update_rect)
        lbl_conf = Label(font_name='Poppins', text="Log out?", font_size='20sp', color=(0.2, 0.2, 0.2, 1), bold=True)
        lbl_sub = Label(font_name='Poppins', text="You will need to sign in again.", font_size='14sp', color=(0.5, 0.5, 0.5, 1))
        btn_box = BoxLayout(spacing=15, size_hint=(1, None), height=55)
        no_btn = RoundedButton(text='Cancel', bg_color=(0.9, 0.9, 0.9, 1))
        no_btn.color = (0.4, 0.4, 0.4, 1)
        yes_btn = RoundedButton(text='Logout', bg_color=(0.9, 0.3, 0.3, 1))
        popup = Popup(title='', separator_height=0, content=content, size_hint=(0.8, 0.35),
                     background_color=(0,0,0,0.5), background='')
        def confirm_logout(x):
            popup.dismiss()
            app = App.get_running_app()
            app.current_student = None
            self.manager.current = 'login'
        yes_btn.bind(on_press=confirm_logout)
        no_btn.bind(on_press=popup.dismiss)
        btn_box.add_widget(no_btn)
        btn_box.add_widget(yes_btn)
        content.add_widget(Label(size_hint=(1, 0.2)))
        content.add_widget(lbl_conf)
        content.add_widget(lbl_sub)
        content.add_widget(Label(size_hint=(1, 0.1)))
        content.add_widget(btn_box)
        popup.open()



class QueueStatusScreen(BaseScreen):
    def __init__(self, db, **kwargs):
        super().__init__(**kwargs)
        self.name = 'queue_status'
        self.db = db
        self.current_rating = 0
        self.unrated_queue = None

        layout = BoxLayout(orientation='vertical')
        top_panel = BoxLayout(orientation='vertical', size_hint=(1, 0.15), padding=10)
        with top_panel.canvas.before:
            Color(0.2, 0.7, 0.4, 1)
            Rectangle(size=top_panel.size, pos=top_panel.pos)
        def update_top(instance, value):
            instance.canvas.before.clear()
            with instance.canvas.before:
                Color(0.2, 0.7, 0.4, 1)
                Rectangle(size=instance.size, pos=instance.pos)
        top_panel.bind(size=update_top, pos=update_top)
        title = Label(font_name='Poppins', text='Queue Status', font_size='22sp', color=(1, 1, 1, 1), bold=True)
        top_panel.add_widget(title)

        # Main content area
        middle = BoxLayout(orientation='vertical', size_hint=(1, 0.7), padding=20, spacing=15)
        self.queue_box = BoxLayout(orientation='vertical', spacing=10)

        # Refresh button (initially added, but can be swapped)
        self.refresh_btn = MDFillRoundFlatIconButton(
            text="REFRESH",
            icon="refresh",  # This pulls the real icon from Material Design
            size_hint=(1, None),
            height=55,
            md_bg_color=(0.2, 0.7, 0.4, 1),  # Green background
            theme_text_color="Custom",
            text_color=(1, 1, 1, 1),  # White text
            icon_color=(1, 1, 1, 1),  # White icon
            font_size='18sp'
        )

        self.refresh_btn.bind(on_press=lambda x: self.load_queue())

        middle.add_widget(self.queue_box)
        middle.add_widget(self.refresh_btn)

        bottom_nav = self.create_bottom_nav(queue_active=True)
        layout.add_widget(top_panel)
        layout.add_widget(middle)
        layout.add_widget(bottom_nav)
        self.add_widget(layout)
        Clock.schedule_interval(self.auto_refresh, 3)

    def create_bottom_nav(self, queue_active=False):
        bottom_nav = BoxLayout(size_hint=(1, 0.15), padding=0, spacing=0)
        with bottom_nav.canvas.before:
            Color(1, 1, 1, 1)
            Rectangle(size=bottom_nav.size, pos=bottom_nav.pos)
        def update_nav_bg(instance, value):
            instance.canvas.before.clear()
            with instance.canvas.before:
                Color(1, 1, 1, 1)
                Rectangle(size=instance.size, pos=instance.pos)
        bottom_nav.bind(size=update_nav_bg, pos=update_nav_bg)
        def create_nav_btn(icon, active, callback):
            container = AnchorLayout(size_hint_x=1)
            color = (0.2, 0.7, 0.4, 1) if active else (0.6, 0.6, 0.6, 1)
            btn = MDIconButton(icon=icon, font_size="30sp", theme_text_color="Custom", text_color=color)
            btn.bind(on_press=callback)
            container.add_widget(btn)
            return container
        bottom_nav.add_widget(create_nav_btn("home", False, lambda x: setattr(self.manager, 'current', 'home')))
        bottom_nav.add_widget(create_nav_btn("ticket-account", queue_active, lambda x: setattr(self.manager, 'current', 'queue_status')))
        bottom_nav.add_widget(create_nav_btn("logout", False, self.logout))
        return bottom_nav

    def logout(self, instance):
        content = BoxLayout(orientation='vertical', padding=25, spacing=15)
        with content.canvas.before:
            Color(1, 1, 1, 1)
            RoundedRectangle(size=content.size, pos=content.pos, radius=[20])
        def update_rect(instance, value):
            instance.canvas.before.clear()
            with instance.canvas.before:
                Color(1, 1, 1, 1)
                RoundedRectangle(size=instance.size, pos=instance.pos, radius=[20])
        content.bind(size=update_rect, pos=update_rect)
        lbl_conf = Label(font_name='Poppins', text="Log out?", font_size='20sp', color=(0.2, 0.2, 0.2, 1), bold=True)
        lbl_sub = Label(font_name='Poppins', text="You will need to sign in again.", font_size='14sp', color=(0.5, 0.5, 0.5, 1))
        btn_box = BoxLayout(spacing=15, size_hint=(1, None), height=55)
        no_btn = RoundedButton(text='Cancel', bg_color=(0.9, 0.9, 0.9, 1))
        no_btn.color = (0.4, 0.4, 0.4, 1)
        yes_btn = RoundedButton(text='Logout', bg_color=(0.9, 0.3, 0.3, 1))
        popup = Popup(title='', separator_height=0, content=content, size_hint=(0.8, 0.35),
                     background_color=(0,0,0,0.5), background='')
        def confirm_logout(x):
            popup.dismiss()
            app = App.get_running_app()
            app.current_student = None
            self.manager.current = 'login'
        yes_btn.bind(on_press=confirm_logout)
        no_btn.bind(on_press=popup.dismiss)
        btn_box.add_widget(no_btn)
        btn_box.add_widget(yes_btn)
        content.add_widget(Label(size_hint=(1, 0.2)))
        content.add_widget(lbl_conf)
        content.add_widget(lbl_sub)
        content.add_widget(Label(size_hint=(1, 0.1)))
        content.add_widget(btn_box)
        popup.open()

    def on_enter(self):
        self.load_queue()

    def auto_refresh(self, dt):
        if self.manager.current == 'queue_status':
            self.load_queue()

    def load_queue(self):
        # 1. Check for Active Queue first
        app = App.get_running_app()
        if not app.current_student: return

        # DEBUG PRINT: Verify this runs every 3 seconds in PyCharm console
        print("DEBUG: Checking database for updates...")

        active_queue = self.db.get_student_queue(app.current_student['id'])

        # --- NEW CODE START ---
        if hasattr(app, 'notifications'):
            app.notifications.update_status(active_queue)
        # --- NEW CODE END ---

        self.queue_box.clear_widgets()

        # If there is an active queue, show it
        if active_queue:
            print(f"DEBUG: Found Queue! People Ahead: {active_queue.get('people_ahead')}")
            self.refresh_btn.disabled = False
            self.refresh_btn.opacity = 1
            self.show_active_queue_ui(active_queue)
            return

        # ... (rest of the function stays the same)

        # 2. If no active queue, check for Unrated Completed Queue
        unrated = self.db.get_pending_feedback(app.current_student['id'])

        if unrated:
            self.unrated_queue = unrated
            self.show_rating_ui(unrated)
            # Hide refresh button during rating
            self.refresh_btn.disabled = True
            self.refresh_btn.opacity = 0
            return

        # 3. Default: No Active Queue
        self.refresh_btn.disabled = False
        self.refresh_btn.opacity = 1
        self.queue_box.add_widget(Label(text='No Active Queue', font_size='18sp', color=(0.6, 0.6, 0.6, 1)))

    def show_active_queue_ui(self, queue):
        q_num = queue.get('queue_number', '---')
        status = queue.get('status', 'waiting')

        # Default Colors
        color = (0.2, 0.7, 0.4, 1)  # Green
        top_text = f'Your Queue\n{q_num}'

        # Safe count
        count = queue.get('people_ahead', 0)
        info_text = f'{count} People Ahead'

        # Special Button Container
        action_button = None

        # 1. HANDLE SERVING
        if status == 'serving':
            top_text = f'NOW SERVING\n{q_num}'
            color = (0.8, 0.2, 0.2, 1)  # Red
            info_text = "Please proceed to counter"

        # 2. HANDLE WAITING (Add Cancel Button Here)
        elif status == 'waiting':
            # Create a Red Cancel Button
            action_button = RoundedButton(
                text="CANCEL QUEUE",
                size_hint=(1, None),
                height=50,
                bg_color=(0.9, 0.3, 0.3, 1),  # Red color
                bold=True
            )
            # Bind to a confirmation popup function
            action_button.bind(on_press=lambda x: self.confirm_cancel(queue['id']))

        # 3. HANDLE CANCELLED
        elif status == 'cancelled':
            top_text = f'CANCELLED\n{q_num}'
            color = (0.5, 0.5, 0.5, 1)  # Grey
            reason = queue.get('notes', 'Cancelled by staff')
            info_text = f"Reason: {reason}"

            # Button to request new queue
            action_button = RoundedButton(
                text="REQUEST NEW QUEUE",
                size_hint=(1, None),
                height=50,
                bg_color=(0.2, 0.7, 0.4, 1)
            )
            action_button.bind(on_press=lambda x: setattr(self.manager, 'current', 'home'))

        # Display Logic
        your_queue = Label(font_name='Poppins', text=top_text, font_size='32sp', color=color, bold=True,
                           size_hint=(1, 0.4), halign='center')
        people_ahead = Label(font_name='Poppins', text=info_text, font_size='18sp', color=(0.5, 0.5, 0.5, 1),
                             size_hint=(1, 0.3))

        # Handle Office Name
        office_data = queue.get('offices')
        office_name_str = "Office"
        if isinstance(office_data, dict):
            office_name_str = office_data.get('name', 'Office')
        office_name = Label(font_name='Poppins', text=f"Office: {office_name_str}", font_size='16sp',
                            color=(0.3, 0.3, 0.3, 1))

        self.queue_box.add_widget(your_queue)
        self.queue_box.add_widget(people_ahead)
        self.queue_box.add_widget(office_name)

        # Add the Action button if it exists
        if action_button:
            self.queue_box.add_widget(Label(size_hint=(1, 0.1)))  # Spacer
            self.queue_box.add_widget(action_button)

    def show_rating_ui(self, queue):
        """Display the Star Rating Interface"""
        self.current_rating = 0

        # Header
        lbl_title = Label(font_name='Poppins', text="Visit Completed!", font_size='22sp', color=(0.2, 0.7, 0.4, 1), bold=True, size_hint=(1, 0.1))
        lbl_sub = Label(font_name='Poppins', text=f"How was your experience at\n{queue['offices']['name']}?",
                       font_size='16sp', color=(0.4, 0.4, 0.4, 1), halign='center', size_hint=(1, 0.15))

        # Stars Container
        stars_box = BoxLayout(size_hint=(1, 0.15), spacing=10, padding=[40, 0, 40, 0])
        self.star_buttons = []
        for i in range(1, 6):
            btn = MDIconButton(icon="star-outline", font_size="36sp", theme_text_color="Custom", text_color=(0.8, 0.8, 0.8, 1))
            btn.bind(on_press=lambda x, rating=i: self.set_rating(rating))
            self.star_buttons.append(btn)
            stars_box.add_widget(btn)

        # Comment Input
        self.comment_input = RoundedInput(hint_text="Optional comment...", size_hint=(1, None), height=100)

        # Submit Button
        submit_btn = RoundedButton(text="SUBMIT FEEDBACK", size_hint=(1, None), height=55, bg_color=(0.2, 0.7, 0.4, 1), bold=True)
        submit_btn.bind(on_press=self.submit_rating)

        self.queue_box.add_widget(lbl_title)
        self.queue_box.add_widget(lbl_sub)
        self.queue_box.add_widget(stars_box)
        self.queue_box.add_widget(Label(size_hint=(1, 0.05)))
        self.queue_box.add_widget(self.comment_input)
        self.queue_box.add_widget(Label(size_hint=(1, 0.05)))
        self.queue_box.add_widget(submit_btn)

    def set_rating(self, rating):
        self.current_rating = rating
        # Update star icons
        for i, btn in enumerate(self.star_buttons):
            if i < rating:
                btn.icon = "star"
                btn.text_color = (1, 0.8, 0, 1) # Gold
            else:
                btn.icon = "star-outline"
                btn.text_color = (0.8, 0.8, 0.8, 1) # Gray

    def submit_rating(self, instance):
        if self.current_rating == 0:
            Snackbar(text="Please select a star rating").open()
            return

        app = App.get_running_app()
        result = self.db.submit_feedback(
            office_id=self.unrated_queue['office_id'],
            student_id=app.current_student['id'],
            queue_id=self.unrated_queue['id'],
            rating=self.current_rating,
            comment=self.comment_input.text
        )

        if result['success']:
            Snackbar(text="Thank you for your feedback!").open()
            self.load_queue() # Refresh to clear rating screen
        else:
            Snackbar(text="Error submitting feedback").open()

    def confirm_cancel(self, queue_id):
        """Show a popup to confirm cancellation"""
        content = BoxLayout(orientation='vertical', padding=20, spacing=15)

        # Style the popup background
        with content.canvas.before:
            Color(1, 1, 1, 1)
            RoundedRectangle(size=content.size, pos=content.pos, radius=[20])

        def update_rect(instance, value):
            instance.canvas.before.clear()
            with instance.canvas.before:
                Color(1, 1, 1, 1)
                RoundedRectangle(size=instance.size, pos=instance.pos, radius=[20])

        content.bind(size=update_rect, pos=update_rect)

        lbl = Label(
            font_name='Poppins',
            text="Cancel your queue?",
            font_size='18sp',
            color=(0.2, 0.2, 0.2, 1),
            bold=True
        )

        lbl_sub = Label(
            font_name='Poppins',
            text="You will lose your spot.",
            font_size='14sp',
            color=(0.5, 0.5, 0.5, 1)
        )

        btn_box = BoxLayout(spacing=10, size_hint=(1, None), height=50)

        btn_no = RoundedButton(text="Keep It", bg_color=(0.5, 0.5, 0.5, 1))
        btn_yes = RoundedButton(text="Yes, Cancel", bg_color=(0.9, 0.3, 0.3, 1))

        popup = Popup(title='', separator_height=0, content=content, size_hint=(0.8, 0.3),
                      background_color=(0, 0, 0, 0.5))

        btn_no.bind(on_press=popup.dismiss)
        btn_yes.bind(on_press=lambda x: self.do_cancel(queue_id, popup))

        btn_box.add_widget(btn_no)
        btn_box.add_widget(btn_yes)

        content.add_widget(lbl)
        content.add_widget(lbl_sub)
        content.add_widget(btn_box)

        popup.open()

    def do_cancel(self, queue_id, popup):
        popup.dismiss()
        app = App.get_running_app()

        result = self.db.cancel_student_queue(queue_id, app.current_student['id'])

        if result['success']:
            Snackbar(text="Queue cancelled").open()
            self.load_queue()  # Refresh UI to show "Cancelled" state
        else:
            Snackbar(text=result['message']).open()


class UpdateCredentialsScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'update_credentials'

        scroll = ScrollView()
        layout = BoxLayout(orientation='vertical', padding=30, spacing=20, size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))

        title = Label(font_name='Poppins', text='Update Credentials', font_size='28sp', color=(0.2, 0.7, 0.4, 1),
                     bold=True, size_hint=(1, None), height=70)

        self.student_num = RoundedInput(hint_text='Student Number', size_hint=(1, None), height=55)
        self.student_num.disabled = True

        self.fullname = RoundedInput(hint_text='Full Name', size_hint=(1, None), height=55)

        course_values = ('Bachelor Of Arts In Journalism', 'Bachelor Of Elementary Education', 'Bachelor Of Science In Business Administration', 'Bachelor Of Science In Computer Science', 'Bachelor Of Science In Hospitality Management', 'Bachelor Of Science In Information Technology', 'Bachelor Of Science In Office Administration', 'Bachelor Of Science In Psychology', 'Bachelor Of Secondary Education')
        self.course = RoundedSpinner(text='Select Course', values=course_values, size_hint=(1, None), height=55)

        year_values = ('1st Year', '2nd Year', '3rd Year', '4th Year', 'Graduate')
        self.year = RoundedSpinner(text='Select Year Level', values=year_values, size_hint=(1, None), height=55)

        self.password = RoundedInput(hint_text='New Password', password=True, size_hint=(1, None), height=55)

        update_btn = RoundedButton(text='UPDATE', size_hint=(1, None), height=60, bold=True)
        update_btn.bind(on_press=self.do_update)

        back_btn = Button(text='Back', size_hint=(1, None), height=45, background_normal='',
                         background_color=(0,0,0,0), color=(0.4, 0.4, 0.4, 1))
        back_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'home'))

        for widget in [title, self.student_num, self.fullname, self.course, self.year, self.password,
                      Label(size_hint=(1, None), height=20), update_btn, back_btn,
                      Label(size_hint=(1, None), height=40)]:
            layout.add_widget(widget)

        scroll.add_widget(layout)
        self.add_widget(scroll)

    def on_enter(self):
        app = App.get_running_app()
        if app.current_student:
            self.student_num.text = app.current_student.get('student_id', '')
            self.fullname.text = app.current_student.get('full_name', '')
            user_course = app.current_student.get('course', '')
            if user_course: self.course.text = user_course
            user_year = app.current_student.get('year_level', '')
            if user_year: self.year.text = user_year

    def do_update(self, instance):
        app = App.get_running_app()
        new_name = self.fullname.text
        new_course = self.course.text
        new_year = self.year.text
        new_pass = self.password.text

        if not new_name or new_course == 'Select Course' or new_year == 'Select Year Level':
            Snackbar(text="All fields are required").open()
            return

        result = app.db.update_student(app.current_student['student_id'], new_name, new_year, new_pass)

        if result['success']:
            app.current_student = result['student']
            Snackbar(text="Credentials updated successfully!").open()
            self.manager.current = 'home'
        else:
            Snackbar(text=result['message']).open()


class QServeUApp(MDApp):
    def build(self):
        self.icon = 'favicon.ico'
        # Force Light Theme
        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "Green"

        sm = ScreenManager(transition=FadeTransition(duration=0.2))

        # Initialize Real Utilities
        self.db = MobileDatabase()
        self.wifi = WiFiDetector()
        self.notifications = NotificationManager()

        self.current_student = None
        self.selected_office = None
        self.current_queue = None

        sm.add_widget(LoadingScreen())
        sm.add_widget(LoginScreen(self.db))
        sm.add_widget(RegisterScreen(self.db))
        sm.add_widget(ChooseOfficeScreen(self.db))
        sm.add_widget(HomeScreen(self.db, self.wifi, self.notifications))
        sm.add_widget(QueueStatusScreen(self.db))
        sm.add_widget(UpdateCredentialsScreen())

        return sm


if __name__ == '__main__':
    QServeUApp().run()
