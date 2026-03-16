import test_data
from data_collector import get_question
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.button import Button
from kivy.properties import StringProperty, NumericProperty, ListProperty, ColorProperty

DEBUG = True # Debug mode will use generic test data instead of calling the API
base_color = (.7, .7, .7, .5)
selection_color = (.8, .4, 0, .8)
answer_color = (.1, .8, .4, .8)

class MainScreen(Screen):
    pass

# Class for the quiz buttons
class ShinyButton(Button):
    img_source = StringProperty("assets/blank.png")
    option_name = StringProperty("")
    bg_color = ColorProperty((.7, .7, .7, .5))

    def __init__(self, **kwargs):
        super(ShinyButton, self).__init__(**kwargs)

    def prepare(self, data: dict):
        self.bg_color = base_color
        self.img_source = data["sprite"]
        self.option_name = data["name"]

    # Change the button color to green for the correct answer
    def show_correct(self):
        self.bg_color = answer_color

    # Change the button color to red for a selected wrong answer
    def show_incorrect(self):
        self.bg_color = selection_color

# The app entry point
class PokeQuizApp(App):
    question_no = NumericProperty(0)
    score = NumericProperty(0)
    q_text = StringProperty(test_data.q_text)
    q_version = StringProperty(test_data.q_version)
    buttons = ListProperty([])

    max_questions = 4
    answer_received = False
    correct_answer : int
    game_end = False

    def __init__(self, **kwargs):
        super(PokeQuizApp, self).__init__(**kwargs)

    def build(self):
        sm = ScreenManager()
        main_screen = MainScreen(name="main")
        sm.add_widget(main_screen)

        self.buttons = []
        for i in range(4):
            btn = sm.get_screen("main").ids[f"answer_button_{i}"]
            btn.bind(on_release=lambda instance, idx=i: self.receive_answer(idx))
            self.buttons.append(btn)
        
        self.continue_game_loop()
        return sm
    
    # Retrieve and format question data to display
    def prepare_question(self):
        if DEBUG:
             #print(f"Preparing question {self.question_no} with test data")
             question_data = test_data.get_pkg()
        else:
            #print(f"Preparing question {self.question_no}")
            question_data = get_question()
            if not question_data:
                print("Failed to prepare question.")
                return
        
        self.q_version = question_data['version']
        self.q_text = question_data['dex_entry']
        choices = question_data['choices']
        for button, choice in zip(self.buttons, choices):
            button.prepare(choice)
        self.correct_answer = question_data['answer']
        self.answer_received = False

    # Will be called from the answers buttons when clicked by the user
    def receive_answer(self, answer):
        if self.answer_received:
            return
        #print(f"Received answer: {answer}")
        self.answer_received = True
        if answer == self.correct_answer:
            self.add_score()
        else:
            #print(f"Wrong! The correct answer was: {self.correct_answer}")
            pass
        
        # Give feedback about correct answer
        self.buttons[answer].show_incorrect()
        self.buttons[self.correct_answer].show_correct()
        Clock.schedule_once(self.continue_game_loop, 3)

    def add_score(self):
        self.score += 1
    
    # Main game loop, in progress
    def continue_game_loop(self, dt=0):
        if self.question_no > self.max_questions:
            # TODO: End game logic
            # Return to menu?
            return
            pass
        self.question_no += 1
        self.prepare_question()
    
if __name__ == '__main__':
    app = PokeQuizApp()
    app.run()
