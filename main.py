import asyncio
import configparser
import json
import os
import platform
import subprocess

from PySide6 import QtCore, QtGui
from pathlib import Path
from PySide6 import QtAsyncio
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QWidget, QPushButton, QMainWindow, QHBoxLayout, QVBoxLayout, QLabel, \
    QFileDialog, QLineEdit, QCheckBox, QProgressBar, QScrollArea, QStyle, QGroupBox
import sys
import fetchers
from fetchers import apply_vanilla_tweaks, update_dll_txt, set_wtf_config

LOG_INFO = 0
LOG_ERROR = 1
LOG_WARNING = 2
LOG_SUCCESS = 3


WINDOWS = False
if platform.system() == "Windows":
    WINDOWS = True
    VT_URL = "https://github.com/brndd/vanilla-tweaks/releases/download/v1.6.0/vanilla-tweaks_v1.6.0_x86_64-pc-windows-gnu.zip"
    CONFIG_PATH = Path.home() / 'AppData/Roaming/Koopa' / 'config.cfg'
    p = Path(Path.home() / 'AppData/Roaming/Koopa')
else:
    VT_URL = "https://github.com/brndd/vanilla-tweaks/releases/download/v1.6.0/vanilla-tweaks_v1.6.0_x86_64-unknown-linux-musl.tar.gz"
    CONFIG_PATH = Path.home() / '.config' / 'Koopa' / 'config.cfg'
    p = Path(Path.home() / '.config' / 'Koopa')

if not p.exists():
    p.mkdir(parents=True, exist_ok=True)


class TweakCheckBox(QCheckBox):
    def __init__(self, tweak: fetchers.Tweak, parent=None):
        super().__init__(parent)
        self.setText(tweak.name)
        self.tweak: fetchers.Tweak = tweak
        self.setToolTip(tweak.description)
        self.setChecked(tweak.default_enabled)

    def set_update_style(self):
        if self.tweak.has_update:
            self.setStyleSheet("""
            color: green;
            """)
            self.setText(f"{self.tweak.name} (update found)")
        else:
            self.setStyleSheet("")
            self.setText(self.tweak.name)


class ModCheckBox(QCheckBox):
    def __init__(self, mod: fetchers.Mod, parent=None):
        super().__init__(parent)
        self.setText(mod.name)
        self.mod: fetchers.Tweak = mod
        self.setToolTip(mod.description)
        self.setChecked(mod.default_enabled)

    def set_update_style(self):
        if self.mod.has_update:
            self.setStyleSheet("""
            color: green;
            """)
            self.setText(f"{self.mod.name} (update found)")
        else:
            self.setStyleSheet("")
            self.setText(self.mod.name)


class MainWindow(QMainWindow):
    config: configparser.ConfigParser = configparser.ConfigParser()
    update_checked: bool = False

    def __init__(self):
        super().__init__()

        self.load_config()

        self.setWindowTitle("Koopa")
        app_icon = QIcon(str(Path(__file__).parent.resolve() / "koopa.ico"))

        self.setWindowIcon(app_icon)

        layout = QHBoxLayout()
        layout_l = QVBoxLayout()
        layout_r = QVBoxLayout()

        # Left layout
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        self.text_area = QLabel(self)
        self.text_area.setWordWrap(True)
        self.text_area.setTextInteractionFlags(QtCore.Qt.TextSelectableByKeyboard | QtCore.Qt.TextSelectableByMouse)
        self.log("Started Koopa, TurtleWoW patcher.")
        self.text_area.setFont(QtGui.QFont("Monospace", 8))
        self.text_area.setAlignment(QtCore.Qt.AlignTop)
        self.text_area.setTextFormat(QtCore.Qt.RichText)
        self.text_area.setStyleSheet("""
        background-color: rgb(255, 255, 255);
        border: 1px solid black;
        """)
        self.text_area.autoFillBackground()
        scroll_area.setWidget(self.text_area)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)

        # Right layout
        self.path_edit = QLineEdit(self)
        if self.config.has_option("turtle", "turtle_path"):
            self.path_edit.setText(self.config["turtle"]["turtle_path"])

        button_path = QPushButton("Select Turtle folder")
        button_path.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon))
        button_path.clicked.connect(self.path_button_callback)

        layout_r.addWidget(self.path_edit)
        layout_r.addWidget(button_path)

        p = Path(__file__).parent.resolve() / "tweaks.json"
        if p.exists():
            self.log("Found existing tweaks.json, loading...")
            with open(p) as json_file:
                json_data_tweaks = json.load(json_file)
        else:
            json_data_tweaks = {}

        p = Path(__file__).parent.resolve() / "mods.json"
        if p.exists():
            self.log("Found existing mods.json, loading...")
            with open(p) as json_file:
                json_data_mods = json.load(json_file)
        else:
            json_data_mods = {}

        tweaks = fetchers.load_tweaks_from_json(json_data_tweaks)
        mods = fetchers.load_mods_from_json(json_data_mods)

        tweak_group = QGroupBox("Tweaks")
        tweak_vbox = QVBoxLayout()
        mod_group = QGroupBox("Mods")
        mod_vbox = QVBoxLayout()
        patch_group = QGroupBox("Patches")
        patch_vbox = QVBoxLayout()

        layout_r.addWidget(tweak_group)
        layout_r.addWidget(mod_group)
        layout_r.addWidget(patch_group)

        tweak_group.setLayout(tweak_vbox)
        mod_group.setLayout(mod_vbox)
        patch_group.setLayout(patch_vbox)

        self.tweak_buttons = []
        self.mod_buttons = []

        for tweak in tweaks:
            cb = TweakCheckBox(tweak)
            tweak_vbox.addWidget(cb)
            if tweak.name == "SuperWoW" and WINDOWS:
                l = QLabel(self)
                l.setWordWrap(True)
                l.setText("NB: SuperWoW requires you to turn off real time threat monitoring in Windows Security center!")
                l.setStyleSheet("QLabel { color: red; }")
                tweak_vbox.addWidget(l)
            self.tweak_buttons.append(cb)

        for mod in mods:
            cb = ModCheckBox(mod)
            mod_vbox.addWidget(cb)
            self.mod_buttons.append(cb)

        self.patch_cb = QCheckBox(self)
        self.patch_cb.setChecked(True)
        self.patch_cb.setDisabled(True)
        self.patch_cb.setText("VanillaTweaks")
        self.patch_cb.setToolTip("Patch WoW.exe with fixes, this step is mandatory (for now)")
        patch_vbox.addWidget(self.patch_cb)


        self.button_check = QPushButton("Check updates")
        self.button_check.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.button_check.clicked.connect(lambda: asyncio.ensure_future(self.check_updates()))
        if self.validate_turtle_folder(self.path_edit.text()):
            self.button_check.setEnabled(True)

        layout_r.addWidget(self.button_check)

        self.button_start = QPushButton("Install tweaks and patch WoW.exe")
        self.button_start.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogOkButton))
        self.set_start_button_state(False)
        self.button_start.clicked.connect(lambda: asyncio.ensure_future(self.start_button_callback()))

        layout_r.addWidget(self.button_start)

        if WINDOWS or True:
            self.button_launch = QPushButton("Launch game")
            self.button_launch.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
            self.button_launch.clicked.connect(self.launch_game)
            if self.validate_turtle_folder(self.path_edit.text()):
                self.button_launch.setEnabled(True)
            else:
                self.button_launch.setEnabled(False)
            layout_r.addWidget(self.button_launch)

        layout_l.addWidget(scroll_area)
        layout_l.addWidget(self.progress)
        layout_r.setAlignment(QtCore.Qt.AlignTop)
        layout.addLayout(layout_l)
        layout.addLayout(layout_r)

        self.setMinimumSize(650, 400)

        widget = QWidget()
        widget.setLayout(layout)

        # Set the central widget of the Window.
        self.setCentralWidget(widget)
        # asyncio.run(self.check_updates())

    def launch_game(self):
        game_path = Path(self.config["turtle"]["turtle_path"]) / "WoW_tweaked.exe"
        p = str(game_path).replace("/", "\\")
        try:
            subprocess.Popen([p], creationflags=subprocess.DETACHED_PROCESS)
        except FileNotFoundError:
            self.log("Error: WoW_tweaked.exe not found at the specified path.", LOG_ERROR)
        except Exception as e:
            self.log(f"An error occurred: {e}", LOG_ERROR)

    def set_start_button_state(self, enabled: bool):
        if enabled:
            self.button_start.setEnabled(True)
            self.button_start.setStyleSheet("QPushButton { background-color: rgb(70, 150, 0); color: white; }")
        else:
            self.button_start.setEnabled(False)
            self.button_start.setStyleSheet("QPushButton { background-color: rgb(150, 150, 150); color: rgb(50, 50, 50); }")

    async def check_updates(self):
        self.log("Checking updates...", LOG_INFO)
        self.set_start_button_state(False)
        self.button_check.setEnabled(False)
        self.update_checked = False

        updates_found: int = 0
        QApplication.processEvents()
        for tb in self.tweak_buttons:
            has_update = tb.tweak.check_update(self.config)
            if has_update and tb.isChecked():
                updates_found += 1
                tb.set_update_style()
            QApplication.processEvents()

        for mod in self.mod_buttons:
            has_update = mod.mod.check_update(self.config)
            if has_update and mod.isChecked():
                updates_found += 1
                mod.set_update_style()
            QApplication.processEvents()

        self.set_start_button_state(True)
        self.button_check.setEnabled(True)
        self.update_checked = True

        if updates_found > 0:
            self.log(f"There's {updates_found} tweaks/mods to be updated/installed.", LOG_INFO)
        else:
            self.log(f"There's no tweaks/mods to be updated/installed.", LOG_INFO)
        QApplication.processEvents()

    def load_config(self):
        if os.path.exists(CONFIG_PATH):
            self.config.read(CONFIG_PATH)
        else:
            self.config["turtle"] = {}
            self.config["tweaks"] = {}

    def save_config(self):
        self.config["turtle"]["turtle_path"] = self.path_edit.text()
        with open(CONFIG_PATH, 'w') as configfile:
            self.config.write(configfile)

    def log(self, text, level=LOG_INFO):
        if level == LOG_ERROR:
            msg = f"<b><font color='red'>{text.strip()}</font></b>"
        elif level == LOG_WARNING:
            msg = f"<b><font color='orange'>{text.strip()}</font></b>"
        elif level == LOG_SUCCESS:
            msg = f"<b><font color='green'>{text.strip()}</font></b>"
        else:
            msg = text

        self.text_area.setText(self.text_area.text() + f"{msg}<br>")
        print(text)

    def path_button_callback(self):
        old_path = self.path_edit.text()
        self.set_start_button_state(False)
        self.button_launch.setEnabled(False)
        dialog = QFileDialog()
        if self.config.has_option("turtle", "turtle_path"):
            d = self.config["turtle"]["turtle_path"]
            file = dialog.getExistingDirectory(None, "Select TurtleWoW folder", dir=d)
        else:
            file = dialog.getExistingDirectory(None, "Select TurtleWoW folder")
        self.path_edit.setText(file)
        if file:
            if self.validate_turtle_folder(file):
                self.button_check.setEnabled(True)
                self.button_launch.setEnabled(True)
                self.log(f"Selected {file}")
                self.save_config()
                if old_path != file:
                    self.update_checked = False
                    self.set_start_button_state(False)
                elif self.update_checked:
                    self.set_start_button_state(True)

            else:
                self.button_check.setEnabled(False)
                self.button_launch.setEnabled(False)
                self.log("WoW.exe not found in that directory, skipping")

    async def start_button_callback(self):
        # Do stuff here
        errors = 0
        if self.validate_turtle_folder(self.config["turtle"]["turtle_path"]):
            self.progress.setValue(0)
            total = 1
            for tb in self.tweak_buttons:
                if tb.isChecked() and tb.tweak.has_update:
                    total += 1
            for mb in self.mod_buttons:
                if mb.isChecked() and mb.mod.has_update:
                    total += 1
            i = 0
            for tb in self.tweak_buttons:
                if tb.isChecked() and tb.tweak.has_update:
                    i += 1
                    try:
                        success, messages = tb.tweak.install(self.config)
                        self.save_config()
                    except Exception as e:
                        errors += 1
                        self.log(f"Failed to install tweak {tb.tweak.name}: {e}", level=LOG_ERROR)
                        QApplication.processEvents()
                        continue
                    QApplication.processEvents()
                    self.progress.setValue(int(i * (100 / total)))
                    if not success:
                        errors += 1
                    for m in messages:
                        self.log(m, level=LOG_INFO if success else LOG_ERROR)

            for mb in self.mod_buttons:
                if mb.isChecked() and mb.mod.has_update:
                    i += 1
                    try:
                        success, messages = mb.mod.install(self.config)
                    except Exception as e:
                        errors += 1
                        self.log(f"Failed to install mod {mb.mod.name}: {e}", level=LOG_ERROR)
                        QApplication.processEvents()
                        continue
                    QApplication.processEvents()
                    self.progress.setValue(int(i * (100 / total)))
                    if not success:
                        errors += 1
                    for m in messages:
                        self.log(m, level=LOG_INFO if success else LOG_ERROR)

            result, messages = apply_vanilla_tweaks(self.config["turtle"]["turtle_path"], VT_URL, {"windows": WINDOWS, "replace": False, "farclip": 777})
            if not result:
                errors += 1
            for m in messages:
                self.log(m, level=LOG_INFO if result else LOG_ERROR)

            success, messages = update_dll_txt(self.config["turtle"]["turtle_path"], [tb.tweak for tb in self.tweak_buttons if tb.isChecked()])
            if success:
                self.log("Updated dlls.txt with the selected tweaks.")
            else:
                errors += 1
                self.log("Failed to update dlls.txt.", level=LOG_ERROR)
            success, messages = set_wtf_config(self.config["turtle"]["turtle_path"])
            if success:
                self.log("Config updated.", level=LOG_INFO)
            else:
                errors += 1
                self.log("Failed to update config.", level=LOG_ERROR)
            self.progress.setValue(100)
            if errors == 0:
                self.log("SUCCESS! Remember to start the game with WoW_tweaked.exe from now on.", level=LOG_SUCCESS)
            else:
                self.log(f"There were {errors} errors, read log to see what went wrong.", level=LOG_WARNING)


    def validate_turtle_folder(self, path: str) -> bool:
        if not os.path.isdir(path):
            return False
        if not os.path.exists(os.path.join(path, "WoW.exe")):
            return False
        return True


def create_app() -> QApplication:
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()
    QtAsyncio.run()

    return app


if __name__ == '__main__':
    koopa_app = create_app()
