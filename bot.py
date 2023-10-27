import os
import pickle
import threading
import time
import schedule
import telebot
import concurrent.futures  # Import the concurrent.futures module
from main import scrape_data
import queue  # Add this import for the queue

# Replace 'YOUR_BOT_TOKEN' with your actual API token
bot = telebot.TeleBot("XXXXXXXXXXXXXXXXXXXXXX")
user_queue = queue.Queue()



class UlifeBot:
    def __init__(self):
        # Use concurrent.futures to run scraping tasks concurrently
        self.max_workers = int(os.cpu_count() * 0.75)  # Limit to 75% of available CPUs

        self.user_preferences_db = "user_preferences.pkl"
        # Dictionary to store user configuration data
        self.user_config = self.load_user_preferences()

        self.erro_autenticacao_string = "Por favor configure suas credenciais usando o menu Configurar."
        self.opcao_string = "Selecione uma opção:"

        # Define a job that runs every 5 minutes
        schedule.every(60).minutes.do(self.check_for_new_notifications)

        # Schedule the task to run at 7 AM
        schedule.every().day.at("07:00").do(self.check_new_things_everyday)

    @staticmethod
    def send_message_to_telegram(chat_id, message):
        bot.send_message(chat_id, message, parse_mode="HTML")

    # Load user preferences from the database
    def load_user_preferences(self):
        try:
            with open(self.user_preferences_db, "rb") as file:
                user_config = pickle.load(file)
        except FileNotFoundError:
            user_config = {}
        return user_config

    # Define a function to create the keyboard markup
    @staticmethod
    def create_keyboard_markup():
        markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        markup.add("O que há hoje?", "Me dê todas as aulas",
                   "Me dê todas as aulas futuras", "Minhas Notificações", "Configurar", "Aviso", "Dúvidas")
        return markup

    def handle_configurar(self, message):
        chat_id = message.chat.id

        bot.send_message(chat_id, "Por favor, saiba que as informações que vou pedir são sensíveis.\n"
                                  "Você tem a liberdade de não continuar se não se sentir seguro(a).\n"
                                  "Preciso do seu nome de usuário e "
                                  "senha do Ulife para fazer login na sua conta e recuperar as informações.\n"
                                  "Se você não deseja continuar, basta parar aqui. Obrigado.")

        # Solicitar o nome de usuário e senha
        bot.send_message(chat_id, "Se deseja continuar, digite o seu nome de usuário do Ulife:")

        bot.register_next_step_handler(message, self.get_username)

    def get_username(self, message):
        chat_id = message.chat.id
        username = message.text

        # Store the username in the user_config dictionary
        self.user_config[chat_id] = {"username": username}

        # Ask for the password
        bot.send_message(chat_id, "Por favor digite a senha do seu Ulife:")
        bot.register_next_step_handler(message, self.get_password)

    def get_password(self, message):
        chat_id = message.chat.id
        password = message.text

        # Store the password in the user_config dictionary
        self.user_config[chat_id]["password"] = password

        # Notify the user that configuration is complete
        bot.send_message(chat_id, "Configuração completa! \n"
                                  "Você agora pode usa o menu Aviso para definir suas preferencias de notificações.")

        # Save user preferences to the database
        self.save_user_preferences(self.user_config, chat_id)

    def handle_aviso(self, message):
        chat_id = message.chat.id

        # Define keyboard with options
        markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        markup.add("Apenas notificações", "Notificações e o que há hoje", "Apenas o que há hoje")

        # Ask for notification preference
        bot.send_message(chat_id, "Escolhar sua opção de notificação:", reply_markup=markup)
        bot.register_next_step_handler(message, self.get_notification_preference)

    def get_notification_preference(self, message):
        chat_id = message.chat.id
        preference = message.text

        # Store the notification preference in the user_config dictionary
        self.user_config[chat_id]["notification_preference"] = preference

        # Notify the user that the preference is set
        bot.send_message(chat_id, f"Preferências de notificações alteradas para: {preference}")

        # Save user preferences to the database
        self.save_user_preferences(self.user_config, chat_id)

    # Save user preferences to the database
    def save_user_preferences(self, user_config, chat_id):
        with open(self.user_preferences_db, "wb") as file:
            pickle.dump(user_config, file)

        bot.send_message(chat_id, ulife_bot.opcao_string, reply_markup=ulife_bot.create_keyboard_markup())

    def handle_future_data(self, chat_id):
        # Handle "Me dê todas as aulas futuras" option
        username = self.user_config.get(chat_id, {}).get("username")
        password = self.user_config.get(chat_id, {}).get("password")

        if username and password:
            bot.send_message(chat_id, "Carregando todas os compromissos futuros (incluindo hoje, se houver)...")
            # You can implement the logic to fetch and send all future data here using 'scrape_data' function.
            self.fetch_data(chat_id, False, True, [False, False])
        else:
            bot.send_message(chat_id, self.erro_autenticacao_string)

        bot.send_message(chat_id, self.opcao_string, reply_markup=self.create_keyboard_markup())

    def handle_all_data(self, chat_id):
        # Handle "Me dê todas as aulas" option
        username = self.user_config.get(chat_id, {}).get("username")
        password = self.user_config.get(chat_id, {}).get("password")

        if username and password:
            bot.send_message(chat_id, "Buscando todos os seus compromissos, futuros e passados...")
            self.fetch_data(chat_id, False, False, [False, False])
        else:
            bot.send_message(chat_id, self.erro_autenticacao_string)

        bot.send_message(chat_id, self.opcao_string, reply_markup=self.create_keyboard_markup())

    def handle_today_data(self, chat_id):
        # Handle "O que há hoje?" option
        username = self.user_config.get(chat_id, {}).get("username")
        password = self.user_config.get(chat_id, {}).get("password")

        if username and password:
            bot.send_message(chat_id, "Verificando seus compromissos de hoje...")
            self.fetch_data(chat_id, True, False, [False, False])
        else:
            bot.send_message(chat_id, self.erro_autenticacao_string)

        bot.send_message(chat_id, self.opcao_string, reply_markup=self.create_keyboard_markup())

    def handle_notifications(self, chat_id):
        # Handle "O que há hoje?" option
        username = self.user_config.get(chat_id, {}).get("username")
        password = self.user_config.get(chat_id, {}).get("password")

        if username and password:
            bot.send_message(chat_id, "Procurando por notificações não lidas...")
            self.fetch_data(chat_id, False, False, [True, False])
        else:
            bot.send_message(chat_id, self.erro_autenticacao_string)

        bot.send_message(chat_id, self.opcao_string, reply_markup=self.create_keyboard_markup())

    @staticmethod
    def menu_duvida(chat_id):
        markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        markup.add("Por que precisa das minhas credenciais?", "O que você pode fazer?", "Como funciona?",
                   "O que fica salvo dos meus dados?", "Voltar ao menu principal")

        # Ask for notification preference
        bot.send_message(chat_id, "Sobre qual assunto você gostaria de saber?", reply_markup=markup)

    def handle_duvidas(self, message):
        chat_id = message.chat.id
        # Define keyboard with options
        self.menu_duvida(chat_id)

        bot.register_next_step_handler(message, self.get_duvida)

    def get_duvida(self, message):
        chat_id = message.chat.id
        duvida = message.text

        if duvida == "Por que precisa das minhas credenciais?":
            bot.send_message(chat_id, "Preciso das suas credenciais do Ulife para acessar a sua conta "
                                      "e buscar informações sobre seus compromissos e notificações. "
                                      "Essas informações são usadas exclusivamente para fornecer"
                                      " a você este serviço relacionado ao Ulife.")
            self.handle_duvidas(message)

        elif duvida == "O que você pode fazer?":
            bot.send_message(chat_id, "Eu posso ajudar você a gerenciar seus compromissos e notificações no Ulife. "
                                      "Isso inclui a visualização de compromissos do dia, compromissos futuros, "
                                      "notificações não lidas e muito mais. "
                                      "Você pode configurar suas preferências de notificação e "
                                      "escolher como deseja receber informações do Ulife.")
            self.handle_duvidas(message)

        elif duvida == "Como funciona?":
            bot.send_message(chat_id, "Funciono acessando o site do Ulife em seu nome usando as credenciais "
                                      "fornecidas por você. Depois de fazer login, busco as informações relevantes, "
                                      "como compromissos e notificações. "
                                      "Em seguida, envio essas informações para você através do Telegram.")
            self.handle_duvidas(message)

        elif duvida == "O que fica salvo dos meus dados?":
            bot.send_message(chat_id, "Salvo apenas as informações necessárias para fornecer o serviço, "
                                      "como seu nome de usuário, senha e preferências de notificação. "
                                      "Suas informações de login são protegidas e não são compartilhadas com terceiros."
                             )
            self.handle_duvidas(message)

        elif duvida == "Voltar ao menu principal":
            bot.send_message(chat_id, self.opcao_string, reply_markup=self.create_keyboard_markup())
        else:
            bot.send_message(chat_id, "Desculpe, não entendi a pergunta. "
                                      "Por favor, escolha uma das opções fornecidas.")
            # Define keyboard with options
            self.handle_duvidas(message)

    def fetch_data(self, chat_id, only_today, only_future, only_notifications):
        # Extract user credentials and preferences from the user_config dictionary
        if chat_id in self.user_config:
            username = self.user_config[chat_id]["username"]
            password = self.user_config[chat_id]["password"]

            scrape_data(username, password, chat_id, bot, only_today = only_today,
            only_future = only_future, only_notifications = only_notifications)
            return

            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit scraping tasks with user's credentials and preferences
                executor.submit(scrape_data, username, password, chat_id, bot, only_today=only_today,
                                only_future=only_future, only_notifications=only_notifications)

    def load_user_data(self, username):
        try:
            with open(self.user_preferences_db, "rb") as file:
                user_database = pickle.load(file)
                if username in user_database:
                    user_data = user_database[username]
                    return user_data
                else:
                    return None
        except FileNotFoundError:
            return None

    # Define a function to check for new notifications
    def check_for_new_notifications(self):
        # Iterate through user preferences to find users with specific preferences
        for chat_id, preferences in self.user_config.items():
            notification_preference = preferences.get("notification_preference")

            # Check if the user's preference matches "Notificações e o que há hoje" or "Apenas notificações"
            if notification_preference in ["Notificações e o que há hoje", "Apenas notificações"]:
                user_queue.put((chat_id, "check_notifications"))

    def verificar_notificacoes_silenciosamente(self, chat_id):
        self.fetch_data(chat_id, False, False, [True, True])

    def check_new_things_everyday(self):
        # Iterate through user preferences to find users with specific preferences
        for chat_id, preferences in self.user_config.items():
            notification_preference = preferences.get("notification_preference")

            # Check if the user's preference matches "Notificações e o que há hoje" or "Apenas notificações"
            if notification_preference in ["Notificações e o que há hoje", "Apenas o que há hoje"]:
                user_queue.put((chat_id, "check_things_everyday"))

    def verificar_novos_compromissos(self, chat_id):
        bot.send_message(chat_id, "Bom dia! Veremos se hoje teremos algo para fazer...")

        self.handle_today_data(chat_id)

    # Function to run the scheduled jobs
    @staticmethod
    def run_scheduled_jobs():
        while True:
            schedule.run_pending()
            time.sleep(1)  # Sleep for a second to avoid high CPU usage

    # Start the bot
    def start(self):
        # Start the scheduler in a separate thread
        scheduler_thread = threading.Thread(target=self.run_scheduled_jobs)
        scheduler_thread.start()
        bot.polling()

    def process_queue(self):
        # Create a ThreadPoolExecutor to process tasks concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            while True:
                try:
                    chat_id, request_type = user_queue.get()
                    if request_type == "today":
                        executor.submit(self.handle_today_data, chat_id)
                    elif request_type == "all":
                        executor.submit(self.handle_all_data, chat_id)
                    elif request_type == "future":
                        executor.submit(self.handle_future_data, chat_id)
                    elif request_type == "notifications":
                        executor.submit(self.handle_notifications, chat_id)

                    elif request_type == "check_notifications":

                        executor.submit(self.verificar_notificacoes_silenciosamente, chat_id)

                    elif request_type == "check_things_everyday":

                        executor.submit(self.verificar_novos_compromissos, chat_id)

                    user_queue.task_done()
                except Exception as e:
                    print(e)


ulife_bot = UlifeBot()


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id

    if message.text == "O que há hoje?":
        user_queue.put((chat_id, "today"))

    elif message.text == "Me dê todas as aulas":
        user_queue.put((chat_id, "all"))

    elif message.text == "Me dê todas as aulas futuras":
        user_queue.put((chat_id, "future"))

    elif message.text == "Configurar":
        # Handle "Configurar" option
        ulife_bot.handle_configurar(message)

    elif message.text == "Aviso":
        # Handle "Aviso" option
        ulife_bot.handle_aviso(message)

    elif message.text == "Minhas Notificações":
        user_queue.put((chat_id, "notifications"))

    elif message.text == "Dúvidas":
        ulife_bot.handle_duvidas(message)

    else:
        bot.send_message(chat_id, "Oi! Estou feliz que esteja aqui para testar meus serviços. \n"
                                  "Sou um bot feito para ajudar alunos do ecossistema Ânima ao usar o Ulife. \n"
                                  "Eu automatizo simples funções como: \n"
                                  "1 - Avisar por compromissos, todos os dias, por volta das 7am.\n"
                                  "2 - Mostrar compromissos de hoje, passados, ou futuros.\n"
                                  "3 - Avisar sobre notificações não lidas.\n")
        usuario = ulife_bot.user_config.get(chat_id, {})
        if usuario == {}:
            bot.send_message(chat_id, "Parece que é a sua primeira vez aqui! "
                                      "Gostaria de continuar ? Para continuar, selecione Configurar no menu.")

        bot.send_message(chat_id, ulife_bot.opcao_string, reply_markup=ulife_bot.create_keyboard_markup())



if __name__ == "__main__":
    ulife_bot = UlifeBot()
    # Start the queue processing in a separate thread
    queue_thread = threading.Thread(target=ulife_bot.process_queue)
    queue_thread.start()

    while True:
        try:
            ulife_bot.start()
        except Exception as e:
            print(e)
