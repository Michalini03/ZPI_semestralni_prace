from m5stack import *
from m5stack_ui import *
from uiflow import *
import wifiCfg
from m5mqtt import M5mqtt
import time

# Nastavení obrazovky
screen = M5Screen()
screen.clean_screen()
screen.set_screen_bg_color(0xFFFFFF)

# Konstanty
MAX_X = 320  # Šířka obrazovky
MAX_Y = 240  # Výška obrazovky
STR_X = "X"  # Symbol hráče 1
STR_O = "O"  # Symbol hráče 2

# Globální proměnné
playing_player = 1  # 1 = hráč 1, 2 = hráč 2
button_matrix = []  # Matice tlačítek
state_matrix = []   # Stav herního pole
player_won = -1     # -1 = žádný vítěz
field_size = 3


# Kontrola herní plochy
def check_game_state(state_matrix, field_size):
    global player_won
    # Nastavení počtu potřebných znaků pro výhru
    win_condition = 3 if field_size < 5 else 5
    
    # Funkce pro kontrolu řady a určení vítěze
    def check_line(line):
        count = 1
        for i in range(1, len(line)):
            if line[i] == line[i - 1] and line[i] != "-":
                count += 1
                if count == win_condition:
                    return True
            else:
                count = 1
        return False

    # Kontrola řádků
    for row in state_matrix:
        if check_line(row):
            if(row[0] == STR_X):
              player_won = 1
            elif(row[0] == STR_O):
              player_won = 2
            return False

    # Kontrola sloupců
    for col in range(field_size):
        column = [state_matrix[row][col] for row in range(field_size)]
        if check_line(column):
            if(column[0] == STR_X):
              player_won = 1
            elif(column[0] == STR_O):
              player_won = 2
            return False

    # Kontrola hlavní diagonály a vedlejší diagonály
    for i in range(field_size - win_condition + 1):
        for j in range(field_size - win_condition + 1):
            # Kontrola hlavní diagonály
            main_diag = [state_matrix[i + k][j + k] for k in range(win_condition)]
            if check_line(main_diag):
              if(main_diag[0] == STR_X):
                player_won = 1
              elif(main_diag[0] == STR_O):
                player_won = 2
              return False

            # Kontrola vedlejší diagonály
            anti_diag = [state_matrix[i + k][j + win_condition - 1 - k] for k in range(win_condition)]
            if check_line(anti_diag):
              if(anti_diag[0] == STR_X):
                player_won = 1
              elif(anti_diag[0] == STR_O):
                player_won = 2
              return False

    # Kontrola, zda je nějaké volné políčko
    for row in state_matrix:
        if "-" in row:
            player_won = -1  # Indikace, že hra pokračuje
            return True

    # Pokud není žádné volné políčko a nikdo nevyhrál, je to remíza
    player_won = 0
    return False


# Funkce pro fyzická tlačítka
def add_one():
    global field_size
    global field_size_text
    if(field_size == 10):
        field_size = 3
    else:
        field_size += 1
    field_size_text.set_text(str(field_size) + "x" + str(field_size))

def drop_one():
    global field_size
    global field_size_text
    if(field_size == 3):
        field_size = 10
    else:
        field_size -= 1
    field_size_text.set_text(str(field_size) + "x" + str(field_size))

# Vytvoří prázdnou čtvercovou matici
def create_square_matrix(size):
    return [["-" for _ in range(size)] for _ in range(size)]


# Funkce pro vytvoření pole tlačítek
def create_field_by_size(field_size):
    global button_matrix
    screen.clean_screen()
    screen.set_screen_bg_color(0xFFFFFF)
    
    for i in range(field_size):
        for j in range(field_size):
            def make_on_press(x, y):
                return lambda: change_button(x, y)

            # Vytvoření tlačítka
            button = M5Btn(
                text='', 
                x=(MAX_X // field_size) * j, 
                y=(MAX_Y // field_size) * i, 
                w=(MAX_X // field_size), 
                h=(MAX_Y // field_size), 
                bg_c=0xFFFFFF, 
                text_c=0x000000, 
                font=FONT_MONT_14, 
                parent=None
            )
            button.pressed(make_on_press(i, j))
            button_matrix[i][j] = button


# Změna tlačítka po stisknutí
def change_button(row, col):
    global playing_player
    global state_matrix
    global button_matrix
    global player_won
    global m5mqtt
    
    # Pokud tlačítko není označené
    if state_matrix[row][col] == "-":
        if playing_player == 2:
            return
        else:
            button_matrix[row][col].set_btn_text(STR_X)
            state_matrix[row][col] = STR_X
            playing_player = 2  # Přepnutí na hráče 2
            m5mqtt.publish(str('player_one_played'), str(str(row)+str(col)), 0)
            

# MQTT funkce pro zpracování odehry hráče 1
def player_two_played(topic_data):
  global state_matrix
  global button_matrix
  global playing_player
  playing_player = 1
  x = int(topic_data[0])
  y = int(topic_data[1])
  state_matrix[x][y] = STR_O
  button_matrix[x][y].set_btn_text(STR_O)
  pass

# Připojení k Wi-Fi
label0 = M5Label('Not Connected', x=110, y=120, color=0x000, font=FONT_MONT_14, parent=None)
wifiCfg.doConnect('SSID', 'Password')

if not wifiCfg.wlan_sta.isconnected():
    for _ in range(5):  # Zkus připojit 5x
        wifiCfg.reconnect()
        if wifiCfg.wlan_sta.isconnected():
            break

if wifiCfg.wlan_sta.isconnected():
    # Připojení k serveru
    screen.set_screen_bg_color(0x9999ff)
    m5mqtt = M5mqtt('', 'test.mosquitto.org', 1883, '', '', 300)
    m5mqtt.subscribe(str('player_two_played'), player_two_played)
    m5mqtt.start()
    screen.clean_screen()
else:
    label0.set_text('Connection Failed')

# Inicializace UI prvků
st = M5Label('START', x=137, y=219, color=0x000, font=FONT_MONT_14, parent=None)
line_top = M5Line(x1=1, y1=204, x2=321, y2=204, color=0x000, width=1, parent=None)
minus_one_text = M5Label('-1', x=43, y=219, color=0x000, font=FONT_MONT_14, parent=None)
line_left = M5Line(x1=107, y1=204, x2=107, y2=240, color=0x000, width=1, parent=None)
line_right = M5Line(x1=214, y1=204, x2=214, y2=240, color=0x000, width=1, parent=None)
add_one_text = M5Label('+1', x=260, y=219, color=0x000, font=FONT_MONT_14, parent=None)
field_size_text = M5Label('3x3', x=129, y=101, color=0x000, font=FONT_MONT_38, parent=None)

# Hlavní cyklus
while True:
    while not btnB.wasPressed():
        btnA.wasPressed(drop_one)
        btnC.wasPressed(add_one)
        wait(0.2)
    
    screen.clean_screen()
    btnA.wasPressed()
    btnC.wasPressed()
    
    # Vytvoření matice a tlačítek
    state_matrix = create_square_matrix(field_size)
    button_matrix = create_square_matrix(field_size)
    
    create_field_by_size(field_size)
    m5mqtt.publish(str('create_field'), str(field_size), 0)
    break

while check_game_state(state_matrix, field_size) == True:
    wait(3)
    
# Počkejte, dokud není výsledek zobrazený
    
screen.clean_screen()
END = M5Label('THE END', x=83, y=69, color=0x000, font=FONT_MONT_34, parent=None)
winner = M5Label('Winner:', x=66, y=109, color=0x000, font=FONT_MONT_22, parent=None)
if(player_won == 1):
    player_who_won = M5Label('Player 1', x=163, y=109, color=0xfe0000, font=FONT_MONT_22, parent=None)
elif(player_won == 2):
    player_who_won = M5Label('Player 2', x=163, y=109, color=0x18ad03, font=FONT_MONT_22, parent=None)
elif(player_won == 0):
    player_who_won = M5Label('Draw', x=163, y=109, color=0x000, font=FONT_MONT_22, parent=None)
