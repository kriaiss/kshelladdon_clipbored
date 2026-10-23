from collections import deque
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton, QLineEdit, QScrollArea, QApplication
from PyQt6.QtCore import Qt, QTimer

class ClipboardTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 10)
        
        self.input = QLineEdit()
        self.input.setPlaceholderText("clipbored ready to search...")
        self.input.textChanged.connect(self.refresh_list)
        layout.addWidget(self.input)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet("QScrollArea { background: transparent; }")
        
        self.container = QWidget()
        self.container.setObjectName("ClipContainer")
        self.container.setStyleSheet("QWidget#ClipContainer { background: transparent; }")
        self.card_layout = QVBoxLayout(self.container)
        self.card_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)
        
        self.history = deque(maxlen=100)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.sync_clip)
        self.timer.start(800)
        
        self.update_display()

    def reset_search(self):
        self.input.clear()

    def update_display(self):
        self.refresh_list()
        try:
            import AppKit
            is_dark = AppKit.NSUserDefaults.standardUserDefaults().stringForKey_("AppleInterfaceStyle") == "Dark"
            text = "#ffffff" if is_dark else "#000000"
            btn_bg = "rgba(255, 255, 255, 15)" if is_dark else "rgba(0, 0, 0, 10)"
            
            self.setStyleSheet(f"""
            QPushButton#ClipCopyBtn, QPushButton#ClipRemoveBtn {{
                background: {btn_bg};
                border-radius: 6px;
                padding: 4px 8px;
                font-family: 'Menlo';
                font-size: 11px;
                border: none;
            }}
            QPushButton#ClipCopyBtn {{ color: {text}; }}
            QPushButton#ClipCopyBtn:hover {{ background: rgba(128, 128, 128, 40); }}
            
            QPushButton#ClipRemoveBtn {{ color: rgba(255, 68, 68, 200); }}
            QPushButton#ClipRemoveBtn:hover {{ 
                background: rgba(255, 68, 68, 40); 
                color: #ff4444; 
            }}
            """)
        except:
            pass

    def sync_clip(self):
        text = QApplication.clipboard().text().strip()
        if not text or len(text) > 100000: 
            return
            
        if not self.history or text != self.history[0]:
            if text in self.history: 
                self.history.remove(text)
            self.history.appendleft(text)
            # dont rebuild 100 cards on every copy if the shell is closed, waste of ram and cpu
            if self.isVisible() and not self.input.text().strip(): 
                self.refresh_list()

    def refresh_list(self):
        while self.card_layout.count():
            item = self.card_layout.takeAt(0)
            if item.widget(): 
                item.widget().deleteLater()
                
        query = self.input.text().strip().lower()
        for original_text in [t for t in self.history if query in t.lower()][:100]:
            item = QFrame()
            l = QHBoxLayout(item)
            l.setContentsMargins(10, 5, 10, 5)
            preview = " ".join(original_text.split())
            txt = QLabel(preview[:65] + "..." if len(preview) > 65 else preview)
            txt.setTextFormat(Qt.TextFormat.PlainText)
            txt.setObjectName("ClipLabel")
            
            btn_copy = QPushButton("copy")
            btn_copy.setObjectName("ClipCopyBtn")
            btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_copy.clicked.connect(lambda ch, x=original_text: self.copy_and_hide(x))
            
            btn_rm = QPushButton("remove")
            btn_rm.setObjectName("ClipRemoveBtn")
            btn_rm.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_rm.clicked.connect(lambda ch, x=original_text: self.remove_item(x))
            
            l.addWidget(txt)
            l.addStretch()
            l.addWidget(btn_copy)
            l.addWidget(btn_rm)
            self.card_layout.addWidget(item)

    def remove_item(self, text):
        if text in self.history:
            self.history.remove(text)
            
        if text == QApplication.clipboard().text().strip():
            self.timer.stop()
            if self.history:
                QApplication.clipboard().setText(self.history[0])
            else:
                QApplication.clipboard().setText("")
            self.timer.start(800)
            
        self.refresh_list()

    def copy_and_hide(self, text):
        self.timer.stop()
        QApplication.clipboard().setText(text)
        if text in self.history: 
            self.history.remove(text)
        self.history.appendleft(text)
        self.timer.start(800)
        
        win = self.window()
        if win:
            if hasattr(win, 'ktools'):
                win.ktools.toggle_plugin("kshell")
            elif hasattr(win, 'hide_anim'):
                win.hide_anim()
            else:
                win.hide()

    def cleanup(self):
        try:
            self.timer.stop()
        except:
            pass


class Plugin:
    def __init__(self, ktools):
        self.ktools = ktools
        self.name = "kshelladdon_clipboard"
        self.widget = None
        # half the methods dont exist in plugin init yet, so, wait a bit
        QTimer.singleShot(200, self.register)

    def get_actions(self):
        return []
        
    def update_theme(self):
        pass

    def unload(self):
        if self.widget:
            try:
                self.widget.cleanup()
            except Exception: 
                pass
                
            kshell_plugin = self.ktools.plugins.get("kshell")
            if kshell_plugin and hasattr(kshell_plugin, "shell") and kshell_plugin.shell:
                kshell_plugin.shell.unregister_tab("clipboard")
                
            try:
                self.widget.deleteLater()
            except Exception:
                pass
            self.widget = None

    def register(self):
        try:
            kshell_plugin = self.ktools.plugins.get("kshell")
            if kshell_plugin and hasattr(kshell_plugin, "shell") and kshell_plugin.shell:
                if not self.widget:
                    self.widget = ClipboardTab()
                    kshell_plugin.shell.register_tab("clipboard", "clipbored", self.widget)
            else:
                QTimer.singleShot(200, self.register)
        except Exception:
            pass
