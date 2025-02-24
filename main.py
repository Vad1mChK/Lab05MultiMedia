from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout

class MultimediaApp(App):
    def build(self):
        self.title = 'Multimedia good morning yeah'
        return Label(text="ELECTRICAL COMMUNICATION")

if __name__ == "__main__":
    MultimediaApp().run()