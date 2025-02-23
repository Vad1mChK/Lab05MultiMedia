from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager
from src.gui.screens import *

class MultimediaApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(MainScreen(name="main"))
        sm.add_widget(ImageAnalyzerScreen(name="analyze_image"))
        sm.add_widget(VideoConcatenatorScreen(name="download_video"))
        sm.add_widget(AudioVisualizerScreen(name="audio"))
        return sm

if __name__ == "__main__":
    Builder.load_file("src/gui/gui.kv")
    MultimediaApp().run()
