import datetime
import os
import pickle
import re
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

meses = {
    'janeiro': '01',
    'fevereiro': '02',
    'março': '03',
    'abril': '04',
    'maio': '05',
    'junho': '06',
    'julho': '07',
    'agosto': '08',
    'setembro': '09',
    'outubro': '10',
    'novembro': '11',
    'dezembro': '12',
    'hoje': datetime.date.today().month
}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# URLs
main_url = "https://student.ulife.com.br/Calendar#pageIndex=1"
login_url = "https://www.ulife.com.br/Login.aspx?ReturnUrl=%Calendar#pageIndex=1"

cookies_str = ''

cookies = {}



# Initialize Chrome options in headless mode
chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--disable-gpu')  # Necessary for headless on Windows
chrome_options.add_argument('--no-sandbox')  # Necessary to avoid certain errors
chrome_options.add_argument('--disable-dev-shm-usage')  # Necessary for headless on Linux
chrome_options.add_argument(f"--user-agent={headers['User-Agent']}")

cookies_name = "cookies.txt"


def generate_date(day, month, year, hour):
    # Get the month number from the dictionary
    month_number = meses[month.lower()]
    date = f"{day}/{month_number}/{year} {hour}"
    return date


def is_date_today(date_str):
    # Parse the provided date string
    date = datetime.datetime.strptime(date_str, "%d/%m/%Y %H:%M")

    # Get the current date and time
    current_datetime = datetime.datetime.now()

    # Compare the year, month, day, hour, and minute components
    if (date.year == current_datetime.year and
            date.month == current_datetime.month and
            date.day == current_datetime.day):
        return True
    else:
        return False


def see_if_day_is_in_the_past(day, month, year, hour):
    # Check if the lowercase month name exists in the dictionary
    if month.lower() in meses:

        date = generate_date(day, month, year, hour)

        # Now we need to convert the date to a datetime object to calculate if the date is in the past or in the future
        date = datetime.datetime.strptime(date, "%d/%m/%Y %H:%M")

        if date <= datetime.datetime.now():
            return True
        else:
            return False
    else:
        return False


def load_stored_cookies(driver):
    # Check if the "cookies.txt" file exists
    if os.path.exists(cookies_name):
        print("Cookies exist. Loading from file.")
        # Load cookies from the file
        with open(cookies_name, "r") as file:
            cookies_str = file.read()

        # Split the cookies string into individual cookies
        cookies_list = cookies_str.split('}{')

        # Create a list to store cookies
        cookies = []

        for cookie_str in cookies_list:
            cookie_str = cookie_str.replace("{", "").replace("}", "")
            cookie_str = "{" + cookie_str + "}"
            try:
                cookie_dict = eval(cookie_str)  # Safely convert string to dictionary

                cookies.append(cookie_dict)
            except SyntaxError as s:
                print(f"Skipping invalid cookie: {cookie_str}")

        # Add cookies to the WebDriver
        i = 0
        y = 0
        for cookie in cookies:
            domain = cookie.get('domain', '')
            if domain:
                domain = domain.strip()  # Remove spaces
            try:
                driver.add_cookie(cookie)
                i += 1
            except Exception as e:
                y += 1
                print(f"Erroneous cookie: {cookie}")
        print(f"Cookies added: {i} cookies\n"
              f"Cookies with errors: {y}")
        return True
    return False


def select_first_non_special_campus(driver):
    try:

        # Encontre o side-menu e clique nele para abrir o campus_chooser
        side_menu = WebDriverWait(driver, 1).until(EC.element_to_be_clickable((By.CLASS_NAME, "sideMenuCheckbox.sideMenu")))
        side_menu.click()
        time.sleep(0.25)

        # Encontre o botão campus_chooser e clique nele para abrir o dropdown
        campus_chooser = WebDriverWait(driver, 1).until(EC.element_to_be_clickable((By.CLASS_NAME, "uOrgSelected")))
        campus_chooser.click()
        time.sleep(0.25)

        # Encontre o elemento <ul> que contém todos os itens do dropdown
        dropdown_list = WebDriverWait(driver, 1).until(EC.presence_of_element_located((By.CLASS_NAME, "uOrgDropdown")))

        # Encontre todos os itens <li> dentro do elemento <ul>
        dropdown_items = dropdown_list.find_elements(By.TAG_NAME, "li")

        # Loop através dos itens para encontrar o primeiro não especial
        for item in dropdown_items:
            item_text = item.text.strip()
            if item_text not in ["Vestibular", "Programa de Nivelamento"]:
                # Clique no item encontrado
                item.click()
                return item_text  # Retorna o texto do item selecionado

        # Se nenhum item não especial for encontrado, você pode tratar isso de acordo com suas necessidades.
        print("Nenhum item não especial encontrado no dropdown.")
        return None

    except Exception as e:
        print(f"Ocorreu um erro: {str(e)}")
        # Adicione aqui o tratamento adequado para outras exceções

    return None  # Retorna None se houver falha na seleção

def get_notifications(driver):
    # Encontre o side-menu e clique nele para abrir o campus_chooser
    side_menu = WebDriverWait(driver, 1).until(EC.element_to_be_clickable((By.CLASS_NAME, "ulIcon.ulIcon-Bell.navbar")))
    side_menu.click()
    time.sleep(2.5)

    user_field = WebDriverWait(driver, 1).until(EC.element_to_be_clickable((By.CLASS_NAME, "userNameTop")))

    listt = user_field.find_elements(By.CLASS_NAME, "ilNotCont.bs")[-1]

    ul = listt.find_element(By.TAG_NAME, "ul")

    notifications = ul.find_elements(By.CLASS_NAME, 'phm.ptm.ng-scope')

    links = []

    for notification in notifications:
        a = notification.find_element(By.TAG_NAME, "a")
        link = a.get_attribute('href')
        splitted_text = notification.text.split('\n')
        link_complete = {
            'text': splitted_text[0],
            'hour': splitted_text[1],
            'link': link
        }
        links.append(link_complete)
    return links


def highlight_element(driver, element):
    # JavaScript to apply temporary styling (change background color)
    driver.execute_script("arguments[0].style.backgroundColor = 'yellow';", element)
    time.sleep(1)  # Add a delay to keep the highlight visible for 1 second
    # JavaScript to remove the styling (reset background color)
    driver.execute_script("arguments[0].style.backgroundColor = '';", element)


def process_month(month):
    month_name = month.find_element(By.CLASS_NAME, 'ltTop.ltTitleSmall')
    month_title = month_name.find_element(By.CLASS_NAME, 'ltTitle')
    month_name_text = month_title.text.strip()

    activ_list = month.find_element(By.CLASS_NAME, 'stActivList')

    if "ng-hide" in activ_list.get_attribute('class'):
        # Click only if it's collapsed
        month_name.click()

    days_in_calendar = month.find_elements(By.CSS_SELECTOR, '.uCalDayLine.pRel.vam.ng-scope:not([class$="ng-hide"])')
    return month_name_text, days_in_calendar


def process_day(day, month_details, month_name, driver, only_future):

    simple_card = False

    # Highlight the current item
    highlight_element(driver, day)

    day_date = day.find_element(By.CLASS_NAME, 'uCalDate')
    day_date_text = day_date.text.strip()

    # Step 1: Get the current date
    current_date = datetime.date.today()

    # Step 2: Get the current year from the current date
    current_year = current_date.year
    only_day = day_date_text.split('\n')[1].strip()
    only_month = month_name.split(' ')[0].strip()

    try:
        info_field = day.find_element(By.CLASS_NAME, "listHover.uCalActivList")
    except Exception:
        info_field = day.find_element(By.CLASS_NAME, "cardLink.ng-scope")

    # Agora vou buscar os textos
    try:
        info_element = info_field.find_element(By.CLASS_NAME, "fm.black")
    except Exception:
        info_element = info_field
        simple_card = True

    # Extract text and attributes
    info_lines = info_element.text.strip().split('\n')

    # Define the regex pattern
    time_pattern = r'\d{2}:\d{2}'

    if simple_card:
        info = info_lines[-1]
    else:
        # Select the first line
        info = info_lines[0]

    # Find all matches in the text
    hours = re.findall(time_pattern, info)

    if only_future:
        is_past = see_if_day_is_in_the_past(only_day, only_month, current_year, hours[0])
    else:
        is_past = False

    date = generate_date(only_day, only_month, current_year, hours[0])

    today = is_date_today(date)

    if not is_past:
        if not simple_card:
            try:
                buttons = day.find_element(By.CLASS_NAME, "fRight.argt.lhn.pm")
            except Exception:
                buttons = None

            link_text = "Couldn't find links"
            links = []
            if buttons is not None and buttons.text != "":
                # print(f"Buttons field found.")
                # print(f"Buttons text: {buttons.text}")
                link_elements = buttons.find_elements(By.CLASS_NAME, "ng-scope")
                # print(f"Link Elements: {len(link_elements)}")
                link_text = ""
                links = []
                for link_element in link_elements:
                    if link_element.text not in link_text:
                        link_element.click()
                        time.sleep(0.25)
                        # Switch to the new tab
                        driver.switch_to.window(driver.window_handles[-1])

                        # Get the URL of the new tab
                        new_tab_url = driver.current_url
                        links.append(new_tab_url)

                        # Close the new tab
                        driver.close()

                        # Switch back to the original tab if needed
                        driver.switch_to.window(driver.window_handles[0])
                        link_text += "\n" + link_element.text + "\n"
                link_text = buttons.text

                # print(f"Inner Link Text: {link_text}")

            # print(f'Day: {day.text.strip()}')

            # Add the details to the current month's dictionary
            day_details = {
                "Hour": hours,
                "Link Text": link_text,
                "Link Href": links,
                "Activ List Text": info,
                "Simple": False,
                "Today": today
            }
            month_details[day_date_text] = [day_details]

        else:

            # Create a list to store unique lines of text
            unique_lines = []

            info_field_childs = info_field.find_elements(By.CLASS_NAME, "pRel.vam.ng-scope")

            days_details = []

            for child in info_field_childs:
                print(f"Simple card found.")
                card_link = child.find_element(By.CLASS_NAME, "cardLink.ng-scope")
                link = card_link.get_attribute('href')
                text = child.text.strip()

                # Find all matches in the text
                hours = [text.split('\n')[-1]]

                text_splitted = text.split('\n')[0]

                # print(f'Day: {text}')

                # Check if the line is not already in the list of unique lines
                if text not in unique_lines:
                    # Add the line to the list of unique lines
                    unique_lines.append(text)

                    # Add the details to the current month's dictionary
                    day_detail = {
                        "Hour": hours,
                        "Link Text": text_splitted,
                        "Link Href": [link],
                        "Activ List Text": text_splitted,
                        "Simple": True,
                        "Today": today
                    }

                    days_details.append(day_detail)

                month_details[day_date_text] = days_details

    return month_details


def extract_calendar_info(driver, only_today=False, only_future=False):
    # Initialize a dictionary to store the calendar details
    calendar_details = {}

    if only_today:
        today_activities = [WebDriverWait(driver, 1).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, 'lineTable.ltNoBorder')))[0]]

        for month in today_activities:
            month_name_text, days_in_calendar = process_month(month)

            # Initialize a dictionary for the current month
            month_details = {}

            for day in days_in_calendar:
                month_details = process_day(day, month_details, month_name_text, driver, only_future)

            # Add the current month's details to the main dictionary
            calendar_details[month_name_text] = month_details
    else:
        # Find all calendar items
        months_calendar = WebDriverWait(driver, 1).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, 'lineTable.ltNoBorder.ng-scope')))

        for month in months_calendar:
            month_name_text, days_in_calendar = process_month(month)

            # Initialize a dictionary for the current month
            month_details = {}

            for day in days_in_calendar:
                month_details = process_day(day, month_details, month_name_text, driver, only_future)

            # Add the current month's details to the main dictionary
            calendar_details[month_name_text] = month_details

    return calendar_details


def go_to_page(driver, page):
    print(f'Going to: {main_url}')
    driver.get(page)
    #driver.implicitly_wait(6)


def login(username, password, driver, only_today, only_future, only_notifications):
    if 'Login.aspx' in driver.current_url:
        calendar_details = None

        print(f'Redirection occurred to: {driver.current_url} - Loggin in..')
        # Find login and password input elements
        username_input = driver.find_element(By.ID, "txtLogin")
        password_input = driver.find_element(By.ID, "txtPassword")
        login_button = driver.find_element(By.ID, "ctl00_b_imbLogin")

        print('Found Login, Password and Submit inputs..')

        # Fill in login and password
        username_input.send_keys(username)
        password_input.send_keys(password)

        print('Setting values to them.. ')

        # Find the login button and click
        login_button.click()

        print('Clicked log-in')
        print('Now waiting for log-in result..')

        # Change the current campus
        selected_campus = select_first_non_special_campus(driver)
        if selected_campus:
            print(f'Selected campus: {selected_campus}')
        else:
            print('Não foi possível selecionar um campus não especial.')
            raise Exception

        go_to_page(driver, main_url)

        # Check if login was successful
        if main_url in driver.current_url or "https://www.ulife.com.br/Calendar" in driver.current_url:
            print('Login successful.')

            if only_notifications[0]:
                calendar_details = get_notifications(driver)
            else:
                calendar_details = extract_calendar_info(driver, only_today=only_today, only_future=only_future)

            print(calendar_details)

        else:
            print('Login failed.')

        return True, calendar_details
    return False, None


def send_calendar_details_to_telegram(chat_id, calendar_details, bot):
    for month_name, month_data in calendar_details.items():
        message = ""
        message += f"\n<b>{month_name}</b>\n" if month_data != {} else ""
        for day_date, day_data in month_data.items():
            for day_segments in day_data:
                day_final_date = day_date.split('\n')
                message += '--------------------------------------------------------------------------------\n'
                message += f"Dia do mês: {day_final_date[1]} {day_final_date[0]} {' - HOJE!' if day_segments['Today'] else ''}\n\n"

                # Include links with their corresponding text
                link_texts = day_segments['Link Text'].split('\n')
                link_hrefs = day_segments['Link Href']

                message += f"O que há hoje: {day_segments['Activ List Text']}\n\n"

                message += f"Horário: {'até as' if day_segments['Simple'] else 'começa'} às {day_segments['Hour'][0] if len(day_segments['Hour']) > 0 else day_segments['Hour']}{' termina às ' + day_segments['Hour'][1] if len(day_segments['Hour']) > 1 else ''}\n\n"

                i = 0
                for link_text in link_hrefs:
                    message += f"<a href='{link_text}'>{link_texts[i]}</a> "
                    i += 1
                message += '\n'
        if month_name == "HOJE" and month_data == {}:
            message += "Você não tem nenhum compromisso pra hoje."

        if message != "":
            bot.send_message(chat_id, message, parse_mode="HTML")


def send_recent_notifications(chat_id, calendar_details, silent, bot):
    # Get the current date and time
    current_time = datetime.datetime.now()

    user_data = load_user_data(chat_id)

    seen_notifications = user_data['seen_notifications']

    zero_notifications = True

    # Iterate through notifications and send only recent ones
    for notification in calendar_details:
        skip = False
        for saw_notification in seen_notifications:
            if saw_notification['text'] == notification['text'] and saw_notification['link'] == notification['link']:
                skip = True
                break
        if skip:
            continue  # Skip already seen notifications

        zero_notifications = False
        without_ha = notification['hour'].replace('há ', '')
        # Parse the 'without_ha' string to extract the time duration
        duration_parts = without_ha.split(' ')
        if len(duration_parts) != 2:
            continue  # Skip notifications with invalid formats

        # Extract the duration value and unit (e.g., '7' and 'days')
        duration_value, duration_unit = int(duration_parts[0]), duration_parts[1]

        # Define a mapping of time units to their approximate timedelta in days
        unit_to_days = {
            'dias': 1,
            'horas': 1 / 24,
            'minutos': 1 / (24 * 60),
            'meses': 30,  # Assuming 30 days in a month
        }

        # Calculate the number of days based on the duration unit
        days = duration_value * unit_to_days.get(duration_unit, 0)

        # Calculate the datetime when the notification was posted
        notification_time = current_time - datetime.timedelta(days=days)

        # Check if the notification is less than 7 days old
        if current_time - notification_time <= datetime.timedelta(days=7):
            bot.send_message(chat_id, f"<a href='{notification['link']}'>{notification['text']}</a>\n"
                                      f"{notification['hour']}", parse_mode="HTML")

    if zero_notifications and not silent:
        bot.send_message(chat_id, "Nenhuma notificação recente encontrada.")

# Define a function to encapsulate the scraping logic
def scrape_data(username, password, chat_id, bot, only_today=False, only_future=False, only_notifications=None):
    if only_notifications is None:
        only_notifications = [True, True]
    for attempt in range(5):
        try:
            # Initialize a Selenium WebDriver with the options
            driver = webdriver.Chrome(options=chrome_options)

            # Open the main URL using the WebDriver
            go_to_page(driver, main_url)

            had_logged_in, calendar_details = login(username, password, driver,
                                                    only_today, only_future, only_notifications)

            if had_logged_in:
                if only_notifications[0]:
                    send_recent_notifications(chat_id, calendar_details, only_notifications[1], bot)

                    # Save the user data to the database
                    save_user_data(chat_id, "seen_notifications", calendar_details)
                else:
                    send_calendar_details_to_telegram(chat_id, calendar_details, bot)
                    # Save the user data to the database
                    save_user_data(chat_id, "calendar_details", calendar_details)

            # Close the WebDriver
            driver.quit()

            # Operation completed successfully, break out of the retry loop
            break

        except Exception as e:
            if attempt < 5 - 1:
                time.sleep(1)
            else:
                print("I tried 5 times without success. Try again.")


def save_user_data(chat_id, field, calendar_details):

    user_data = load_user_data(chat_id)
    if user_data is not None:
        user_data[field] = calendar_details
        # Load the existing database or create an empty dictionary if it doesn't exist
        try:
            with open("user_preferences.pkl", "rb") as file:
                user_database = pickle.load(file)
        except FileNotFoundError:
            user_database = {}

        # Update or add the user data in the database
        user_database[chat_id] = user_data

        # Save the updated database
        with open("user_preferences.pkl", "wb") as file:
            pickle.dump(user_database, file)

        print(f"User data for {user_data['username']} saved to the database.")


def load_user_data(chat_id):
    try:
        with open("user_preferences.pkl", "rb") as file:
            user_database = pickle.load(file)
            if chat_id in user_database:
                user_data = user_database[chat_id]
                return user_data
            else:
                print(f"User data for {chat_id} not found in the database.")
                return None
    except FileNotFoundError:
        print("User database file not found.")
        return None