import os
import time
import json
import re
import random
import datetime
import ASCII.Animations.video
import ASCII.ASCII_LevelUp
import ASCII.ASCII_selection_menu
import ASCII.ASCII_start_menu
""" from googletrans import Translator """
from gtts import gTTS
import pyaudio
import wave
from pydub import AudioSegment
import sys
import copy
from colorama import Fore, Back, Style, init
init(autoreset=True)

def lg(a="",b="",c="",d="",e="",f="",g="",h="",i="",j="",k="",l="",m="",n="",o="",p="",q="",r="",s="",t="",u="",v="",w="",x="",y="",z=""):
    global DEBUG
    DEBUG = False
    if len(sys.argv)>1:
        if sys.argv[1]=="-debug":
            DEBUG = True
            print(a,b,c,d,e,f,g,h,i,j,k,l,m,n,o,p,q,r,s,t,u,v,w,x,y,z)

    return DEBUG

def cls():
    lg("cls()")
    if lg() != True:
        os.system('cls')

def get_config(keys=[]):
    lg(f"get_config({keys})")
    if "config.json" not in os.listdir():
        config = {
            "default_quiz_config": {
                "level_1_question_count": 20,
                "level_2_question_count": 50,
                "random_order": True,
                "pronounce_words": True,
                "send_telegram_message": True,
                "save_statistics": True
            }
        }
        with open("config.json", "w", encoding="UTF-8") as file:
            json.dump(config, file, indent=4)
            file.close()
    else:
        with open("config.json", "r", encoding="UTF-8") as file:
            config = json.load(file)
    o = []
    if keys != []:
        for key in keys:
            if key in next(iter(config.keys())):
                o.append(config[key])
    else: 
        o = config
    return o

def set_config(ukey, key, value):
    lg(f"set_config({ukey},{key},{value})")
    config = get_config()
    if ukey in next(iter(config.keys())):
        config[ukey][key] = value
        with open("config.json", "w", encoding="UTF-8") as file:
            json.dump(config, file, indent=4)
            file.close()

def analytics(get_set,time_finish,time_start,type):
    lg(f"analytics({get_set},{time_finish},{time_start},{type})")
    if get_set == "set":
        with open("analytics.csv", "r", encoding="UTF-8") as file:
            lines = file.readlines()
            for line in lines[::-1]:
                if line.startswith(datetime.datetime.now().strftime("%Y-%m-%d")) and type in line:
                    return
            else:
                with open("analytics.csv", "a", encoding="UTF-8") as file:
                    file.write(f"{time_finish},{type},{time_start}\n")
                    file.close()
    elif get_set == "get":
        analytics_data = []
        if not os.path.exists("analytics.csv"):
            with open("analytics.csv", "w", encoding="UTF-8") as file:
                file.close()
        with open("analytics.csv", "r", encoding="UTF-8") as file:
            lines = file.readlines()
            for line in lines[::-1]:
                data = line.strip().split(",")
                if len(data) >= 3:
                    if data[0].startswith(datetime.datetime.now().strftime("%Y-%m-%d")):
                        analytics_data.append({
                            "time_finish": data[0],
                            "type": data[1],
                            "time_start": data[2]
                        })
        return analytics_data

def daily_stat(get_set, correct, wrong, blank, total,level):
    lg(f"daily_stat({get_set},{correct},{wrong},{blank},{total},{level})")
    if get_set == "get":
        if not os.path.exists("daily_stats.csv"):
            permission = "w"
        else: permission = "r"
        with open("daily_stats.csv",permission,encoding="UTF-8") as f:
            return f.read()
    elif get_set == "set":
        if not os.path.exists("daily_stats.csv"):
            permission = "w"
        else: permission = "a"
        with open("daily_stats.csv",permission,encoding="UTF-8") as f:
            f.write(f"{datetime.datetime.now().strftime("%Y-%m-%d")},{correct},{wrong},{blank},{total},{level}\n")
            f.close()
            return f"{datetime.datetime.now().strftime("%Y-%m-%d")},{correct},{wrong},{blank},{total},{level}"



# words.csv --> comma seperate values

def load_words(file_path):
    final_words = []
    f_words = []
    with open(file_path, 'r', encoding="UTF-8") as file:
        for line in file:
            # Strip the whole line, then split, then strip each part
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 3: continue 
            
            eng, tr, w_type = parts[0], parts[1], parts[2]
            
            final_words.append({eng: tr})
            f_words.append({eng: [tr, w_type]})
    return final_words, f_words


def get_audio(word,lang_="en",t=1):
    lg(f"get_audio({word},{lang_})")
    words,typer = load_words('words.csv')
    for word_ in words:
        key = next(iter(word_.keys()))
        lg(key, word)
        if key.lower() == word.lower():
            language = "en"
            break
    else:
        if word not in words:
            lg("This word is not in the database.")
            return None
        else:language = 'tr'

    if lang_ == language:
        lg(f"Detected language: {language}")
        # Generate audio using gTTS
        tts = gTTS(text=word, lang=language)
        filename = f"pronunciations/{word.lower()}.mp3"
        tts.save(filename)
        if os.path.exists(filename):
            file_size = os.path.getsize(filename)
            if file_size == 0:
                if t != 3:
                    lg(f"Hata: {filename} boş (0 byte) oluşturuldu. Siliniyor...")
                    os.remove(filename)
                    get_audio(word,lang_,t+1)
                else:
                    lg(f"Hata: {filename} 3 defa indirildi ama başarısız olundu.")
            else:
                lg(f"Pronunciation audio saved as {filename}")
                return filename
    else:
        lg(f"Language mismatch: word is in {language}, but lang_ is {lang_}. No audio generated.")
        return None
    
def play_audio(filename):
    lg(f"play_audio({filename})")
    import pyglet
    from time import sleep

    music = pyglet.media.load(filename, streaming=False)
    from mutagen.mp3 import MP3
    try:
        audio = MP3(filename)
        duration = audio.info.length  # Duration in seconds
    except Exception as e:
        print(f"An error occurred: {e}")
        duration = music.duration
    
    music.play()
    sleep(duration)

    """ os.remove(mp3_file) """

def get_folder(folder="pronunciations"):
    lg(f"get_folder({folder})")
    try:
        # Check if the folder exists
        if not os.path.exists(folder):
            lg(f"Folder '{folder}' does not exist.")
            return []
        # List all files in the folder
        files = [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
        lg(f"Files in '{folder}': {files}")
        return files
    except Exception as e:
        lg(f"An error occurred while listing files: {e}")
        return []

def pronounce_word(word, lang_="en"):
    lg(f"pronounce_word({word},{lang_})")
    files = get_folder("pronunciations")
    for file in files:
        if file.lower() == f"{word.lower()}.mp3":
            lg(f"Playing existing pronunciation for '{word}'.")
            play_audio(os.path.join("pronunciations", file))
            return
    else:
        audio_file = get_audio(word, lang_)
        if audio_file:
            play_audio(audio_file)

def detect_language(text):
    lg(f"detect_language({text})")
    words,typer = load_words('words.csv')
    for word in words:
        key = next(iter(word.keys()))
        val = next(iter(word.values()))
        if text.lower() == key.lower():
            return "en"
        elif text.lower() == val.lower():
            return "tr"

""" def admin_interface(buffer=True):
    print("heia")
    main() """

def admin_login_interface(just_auth=False,legacy_selection_menu=False):
    lg(f"admin_login_interface()")
    cls()
    import getpass
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        # dotenv not available; continue and rely on environment or fallback
        pass

    admin_password = os.getenv("ADMIN_PASSWORD")
    password = getpass.getpass("Admin Şifresini giriniz: ")
    if password == admin_password:
        if just_auth == False:
            """ admin_ = admin_console() """
        else:
            return True
    else:
        for i in range(3):
            cls()
            print("Geçersiz şifre! {} saniye içinde ana menüye dönülüyor...".format(3-i))
            time.sleep(i)
        main()

def save_stat(time_,word,translation,answer,correct,level):
    lg(f"save_stat({time_},{word},{translation},{answer},{correct},{level})")
    stat_line = f"{time_},{word},{translation},{answer},{correct},{level}\n"
    with open("statistics.csv", "a", encoding="UTF-8") as file:
        file.write(stat_line)
        file.close()

def quest(question_amount, wordlist, word_progression, dd, typer, quiz_config, current_level):

    if question_amount > len(wordlist):
        question_amount = len(wordlist)

    selected_words = random.sample(wordlist, question_amount)

    for i, word in enumerate(selected_words):
        cls()
        
        time_ = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
        type_of_word = next((d[word][1] for d in typer if word in d), "Not found")
        
        if random.randint(1,2) == 1:
            # --- Logic for Turkish -> English ---
            if word in word_progression:
                basari = word_progression[word][2]*100
                if basari >= 80: cc = Fore.GREEN
                elif basari >= 50: cc = Fore.YELLOW
                elif basari > 20: cc = Fore.LIGHTRED_EX
                else: cc = Fore.RED
            try:
                if word in word_progression:
                    basari = int(basari)
                    print(f"{word} kelimesi için başarı oranınız: ",end="")
                    print(f"{cc}%{basari:.2f}{Style.RESET_ALL}",end="")
                    print(f" ({word_progression[word][0]}/{word_progression[word][1]})\n")      
                else: print(f"{word} kelimesi ilk kez soruluyor.\n")
            except Exception as e: 
                if word in word_progression:
                    print(f"Hata : {e}")
            
            answer = input(f"{i+1}. '{word}' ({type_of_word}) kelimesinin Türkçe karşılığı nedir? ")
            
            if answer.lower() == dd[word].lower():
                print(Fore.GREEN+"\nDoğru!"+Style.RESET_ALL)
                save_stat(time_,word,dd[word],answer,True,current_level)
            elif answer == "":
                print(Fore.LIGHTRED_EX+f"Boş bırakıldı! Doğru cevap: {dd[word]}"+Style.RESET_ALL)
                save_stat(time_,word,dd[word],answer,"blank",current_level)
            elif answer.lower() == "exit":
                os._exit(1)
            else:
                print(Fore.RED+f"Yanlış! Doğru cevap: {dd[word]}"+Style.RESET_ALL)
                save_stat(time_,word,dd[word],answer,False,current_level)
        else:
            # --- Logic for English -> Turkish ---
            if word in word_progression:
                basari = word_progression[word][2]*100
                if basari >= 80: cc = Fore.GREEN
                elif basari >= 50: cc = Fore.YELLOW
                elif basari > 20: cc = Fore.LIGHTRED_EX
                else: cc = Fore.RED
            try:
                if word in word_progression:
                    basari = int(basari)
                    print(f"{dd[word]} kelimesi için başarı oranınız: ",end="")
                    print(f"{cc}%{basari:.2f}{Style.RESET_ALL}",end="")
                    print(f" ({word_progression[word][0]}/{word_progression[word][1]})\n")      
                else: print(f"{dd[word]} kelimesi ilk kez soruluyor.\n")
            except Exception as e: 
                if word in word_progression:
                    print(f"Hata : {e}")
            
            answer = input(f"{i+1}. '{dd[word]}' ({type_of_word}) kelimesinin İngilizce karşılığı nedir? ")
            
            if answer.lower() == word.lower():
                print(Fore.GREEN+"\nDoğru!"+Style.RESET_ALL)
                save_stat(time_,word,dd[word],answer,True,current_level)
            elif answer == "":
                print(Fore.LIGHTRED_EX+f"Boş bırakıldı! Doğru cevap: {word}"+Style.RESET_ALL)
                save_stat(time_,word,dd[word],"","blank",current_level)
            elif answer.lower() == "exit":
                os._exit(1)
            else:
                print(Fore.RED+f"Yanlış! Doğru cevap: {word}"+Style.RESET_ALL)
                save_stat(time_,word,dd[word],answer,False,current_level)    
        
        if quiz_config.get("pronounce_words") == True:
            pronounce_word(word)

### IN BETA ADMIN INTERFACE ###
""" loop = True
while loop:
    cls()
    tim = int(datetime.datetime.now().strftime("%H"))
    txt = ""
    if 6 > tim > 11: txt="Günaydın"
    elif 12 > tim > 18: txt="Tünaydın"
    elif 18 > tim > 1: txt="İyi Akşamlar"
    else:txt = "İyi Geceler"
    print(f"{txt} {username}!\n\n{Fore.LIGHTBLUE_EX}Admin Arayüzü{Style.RESET_ALL}")
    print("1-Çıkış") """
####################################


## MAIN ##


def main(quiz_config={}, legacy_start_menu=False,mode="play"):
    global LEVEL_1_PASSED,LEVEL_2_PASSED, DEBUG
    lg("main()")
    options = {"1": "Başla","2": "Admin Girişi"}
    if legacy_start_menu:
        print("Coalide'a hoş geldiniz!\n")
        try:
            if sys.argv[1] == "-debug":
                
                print(Fore.RED + "DEBUG MODU AKTİF" + Style.RESET_ALL + "\n")
        
        except:pass
    
        
        print("Seçenekler:\n")
        for key, value in options.items():
            print(f"{key}. {value}")
        choice = input("\n\n> ")
    else:
        try:
            choice = c_
        except:choice = "play"

    if choice == list(options.keys())[1] or choice == "admin" or mode == "admin":
        admin_login_interface()
    elif choice == list(options.keys())[0] or choice == "play" or mode == "play":
        try:
            if not DEBUG:
                c__ = ASCII.ASCII_selection_menu.main()
                cls()
                legacy_selection_menu = False
            else: raise
        except:
            print("An error occurred in selection_menu. Falling back to legacy start menu.")
            legacy_selection_menu = True
        
        choices = {"1": "Varsayılan modda başlat", "2": "Admin kontrolü"}

        if legacy_selection_menu:
            print("Seçenekler:\n")
            for key, value in choices.items():
                print(f"{key}. {value}")
            choice_ = input("\n\n> ")
        else:
            choice_ = c__
            if choice_ == "exit":
                print("Çıkış yapılıyor...")
                os._exit(1)
        if choice_ == list(choices.keys())[1] or choice_ == "admin":
            auth = admin_login_interface(just_auth=True,legacy_selection_menu=legacy_selection_menu)
            cls()
            if auth:
                print("Admin kontrolüne hoş geldiniz!")
                default_config = get_config(["default_quiz_config"])
                if quiz_config == {}:
                    temp_config = copy.deepcopy(default_config)
                else:
                    temp_config = [quiz_config]
                print("Mevcut quiz yapılandırması:\n")
                for key, value in temp_config[0].items():
                    for key_, value_ in default_config[0].items():
                        if key == key_:
                            if value != value_:txt = f" (Varsayılan : {value_})"
                            else:txt = ""
                            
                            print(f"{key}: {value}{txt}")

                loop=True
                while loop == True:
                    command = input("\n\n> ")
                    if command.startswith("set "):
                        if "--help" in command:
                            print("set komutu, geçici quiz yapılandırmasını güncellemek için kullanılır. Kullanım: set <anahtar> <değer>")
                            print("Anahtarlar:")
                            for key in temp_config[0].keys():
                                print(f"- {key}")
                        else:
                            try:
                                _, key, value = command.split(" ", 2)
                                if key in temp_config[0]:
                                    if value.lower() in ["true", "false"]:
                                        value = value.lower() == "true"
                                    elif value.isdigit():
                                        value = int(value)
                                    temp_config[0][key] = value
                                    print(f"{key} başarıyla {value} olarak güncellendi.")
                                    print(temp_config)
                                else:
                                    print(f"Geçersiz anahtar: {key}")
                            except ValueError:
                                print("Geçersiz komut formatı. Kullanım: set <anahtar> <değer>")
                    elif command.startswith("dset "):
                        if "--help" in command:
                            print("dset komutu, varsayılan quiz yapılandırmasını güncellemek için kullanılır. Kullanım: dset <anahtar> <değer>")
                            print("Anahtarlar:")
                            for key in default_config[0].keys():
                                print(f"- {key}")
                        else:
                            try:
                                print("dset <anahtar> <değer>: Varsayılan quiz yapılandırmasını günceller.")
                                _, key, value = command.split(" ", 2)
                                if key in default_config[0]:
                                    if value.lower() in ["true", "false"]:
                                        value = value.lower() == "true"
                                    elif value.isdigit():
                                        value = int(value)
                                    default_config[0][key] = value
                                    temp_config[0][key] = value
                                    set_config("default_quiz_config", key, value)
                                    print(f"{key} başarıyla {value} olarak güncellendi.")
                                else:
                                    print(f"Geçersiz anahtar: {key}")
                            except ValueError:
                                print("Geçersiz komut formatı. Kullanım: dset <anahtar> <değer>")

                    elif command == "show":
                        if "--help" in command:
                            print("show komutu, mevcut quiz yapılandırmasını gösterir. Kullanım: show")
                        else:
                            print("Mevcut quiz yapılandırması:\n")
                            for key, value in temp_config[0].items():
                                for key_, value_ in default_config[0].items():
                                    if key == key_:
                                        if value != value_:txt = f" (Varsayılan : {value_})"
                                        else:txt = ""
                                        print(value,value_,txt,key,key_)
                                        print(f"{key}: {value}{txt}")
                    elif command == "exit":
                        if "--help" in command:
                            print("exit komutu, admin kontrolünden çıkar ve ana menüye döner. Kullanım: exit")
                        else:
                            loop = False
                            if temp_config:
                                main(quiz_config=temp_config[0])
                            else:
                                main(quiz_config=default_config[0])
                            return
                    elif command == "cls" or command == "clear":
                        if "--help" in command:
                            print("cls/clear komutu, ekranı temizler. Kullanım: cls/clear")
                        else:
                            cls()
                    elif command == "help":
                        print("Komutlar:")
                        print("- set <anahtar> <değer>: Geçici quiz yapılandırmasını günceller.")
                        print("- dset <anahtar> <değer>: Varsayılan quiz yapılandırmasını günceller.")
                        print("- show: Mevcut quiz yapılandırmasını gösterir.")
                        print("- cls/clear: Ekranı temizler.")
                        print("- help: Komut listesini gösterir.")
                        print("- exit: Admin kontrolünden çıkar ve ana menüye döner.")
                    else:
                        print("Geçersiz komut! Komutlar: set <anahtar> <değer>, dset <anahtar> <değer>, show, cls/clear, help, exit")   

                
        if choice_ == list(choices.keys())[0] or choice_ == "dstart":
            if quiz_config == {}:
                quiz_config = get_config(["default_quiz_config"])[0]
            
            question_amount = 0

            # GET PROGRESSION DATA TO CHOOSE WETHER TO START LEVEL 1 OR 2
            analytics_data = analytics("get",None,None,None)

            ### LEVEL 1 ###
            if analytics_data == []:
                """ known_words = ["give","go","have","make","say","see","take","want"] """
                known_words = []
                word_progression = {}
                if os.path.exists("statistics.csv"):
                    with open("statistics.csv", "r") as f:
                        lines = f.readlines()
                        words = []
                        for line in lines[::-1]:
                            data = line.strip().split(",")
                            if len(data) >= 5:
                                if data[1] not in words:
                                    words.append(data[1])
                        for word in words:
                            amount_counter = correct_counter = 0
                            for line in lines[::-1]:
                                data = line.strip().split(",")
                                if len(data) >= 5 and data[1] == word:
                                    if amount_counter > 5:
                                        break
                                    amount_counter += 1
                                    if data[4] == "True":
                                        correct_counter += 1
                                if amount_counter == correct_counter == 5:
                                    if word not in known_words:
                                        known_words.append(word)
                            
                            word_progression[word] = [correct_counter,amount_counter,correct_counter / amount_counter if amount_counter > 0 else 0]
                    f.close()

                all_words,typer = load_words("words.csv")
                start_time = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
                dd = {}
                for word_dict in all_words:
                    dd[list(word_dict)[0]] = word_dict.get(list(word_dict)[0])
                if len(known_words) < quiz_config["level_1_question_count"]:
                    question_amount = len(known_words)
                else:
                    question_amount = quiz_config["level_1_question_count"]
                lg(known_words)
                quest(question_amount=question_amount,wordlist=known_words,word_progression=word_progression,dd=dd,typer=typer,quiz_config=quiz_config,current_level=1)
                analytics("set",datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S"),start_time,"level_1_passed")
                if not os.path.exists("statistics.csv"):
                    with open("statistics.csv","w",encoding="UTF-8") as f:f.close()
                with open("statistics.csv", "r", encoding="UTF-8") as f:
                    correct_counter_ = wrong_counter_ = blank_counter_ = total_counter_ = 0
                    lines = f.readlines()
                    todays=[]
                    for line in lines[::-1]:
                        if datetime.datetime.now().strftime("%Y-%m-%d") in line:
                            if line.strip() not in todays:
                                todays.append(line.strip())
                    time.sleep(.3)
                    for line in todays:
                        if line.split(",")[5] == "1":
                            """ print(line)
                            print(line.split(","))
                            print(line.split(",")[4])
                            time.sleep(999) """
                            if line.split(",")[4] == "True":
                                correct_counter_ += 1
                            elif line.split(",")[4] == "False":
                                wrong_counter_ += 1
                            else: blank_counter_ += 1
                            total_counter_ += 1
                    f.close()
                analytics_data = analytics("get",None,None,None)
                daily_stat("set",correct_counter_,wrong_counter_,blank_counter_,total_counter_,level=1)
                if not DEBUG:
                    """ try: """
                    ASCII.ASCII_LevelUp.main(f"{correct_counter_/total_counter_*100:.2f}",correct_counter_,total_counter_) if total_counter_ != 0 else ASCII.ASCII_LevelUp.main(f"0",correct_counter_,total_counter_)
                    cls()
                    from random import randint
                    indx = randint(0,len(ASCII.Animations.video.get_files())+1)
                    if indx > len(ASCII.Animations.video.get_files()):
                        """ chose_ani() """
                    else:
                        ASCII.Animations.video.play(ASCII.Animations.video.get_files()[indx])
                    """ except:print("HELP ME") """
            if analytics_data != []:
                for data in analytics_data:
                    if data["type"] == "level_1_passed" and data["time_finish"].startswith(datetime.datetime.now().strftime("%Y-%m-%d")):
                        LEVEL_1_PASSED = True
                        break
                else:
                    LEVEL_1_PASSED = False
                for data in analytics_data:
                    if LEVEL_1_PASSED == True and data["type"] == "level_2_passed" and data["time_finish"].startswith(datetime.datetime.now().strftime("%Y-%m-%d")):
                        LEVEL_2_PASSED = True
                        break
                else:
                    LEVEL_2_PASSED = False
            if analytics_data != [] or question_amount == 0:
                if question_amount == 0:
                    LEVEL_1_PASSED = True
                d = analytics("get",None,None,None)
                for data in d:
                    if data["type"] == "level_2_passed" and data["time_finish"].startswith(datetime.datetime.now().strftime("%Y-%m-%d")):
                        LEVEL_2_PASSED = True
                        break
                else:
                    LEVEL_2_PASSED = False
                if LEVEL_1_PASSED == True and LEVEL_2_PASSED == False:
                    if question_amount != 0: 
                        print("Seviye 1'i geçtiğiniz tespit edildi! Seviye 2'ye geçiliyor...")
                    else: 
                        print("Seviye 1'de yeterli veri bulunamadığı için Seviye 2'ye geçiliyor...")

                    time.sleep(3);  cls()

                    ### LEVEL 2 ###
                    unknown_words = []
                    word_progression = {}
                    if not os.path.exists("statistics.csv"):
                        with open("statistics.csv", "w") as f:
                            f.close()
                    stat_words = []
                    if os.path.exists("statistics.csv"):
                        with open("statistics.csv", "r") as f:
                            lines = f.readlines()
                            words = []
                            for line in lines[::-1]:
                                data = line.strip().split(",")
                                if len(data) >= 5:
                                    if data[1] not in words:
                                        words.append(data[1])
                            for word in words:
                                amount_counter = 0
                                correct_counter = 0
                                for line in lines[::-1]:
                                    data = line.strip().split(",")
                                    if len(data) >= 5 and data[1] == word:
                                        if amount_counter > 5:
                                            break
                                        amount_counter += 1
                                        if data[4] == "True":
                                            correct_counter += 1
                                    if amount_counter != correct_counter != 5:
                                        if word not in unknown_words:
                                            unknown_words.append(word)
                                    if word not in stat_words:
                                        stat_words.append(word)
                                
                                word_progression[word] = [correct_counter,amount_counter,correct_counter / amount_counter if amount_counter > 0 else 0]
                        f.close()
                    start_time = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
                    all_words,typer = load_words("words.csv")
                    for word in all_words:
                        if list(word.keys())[0] not in stat_words:
                            if list(word.keys())[0] not in unknown_words:
                                unknown_words.append(list(word.keys())[0])
                    dd = {}
                    for word_dict in all_words:
                        dd[list(word_dict)[0]] = word_dict.get(list(word_dict)[0])
                    if len(unknown_words) < quiz_config["level_2_question_count"]:
                        question_amount = len(unknown_words)
                    else:
                        question_amount = quiz_config["level_2_question_count"]

                    lg(unknown_words)
                    quest(question_amount=question_amount,wordlist=unknown_words,word_progression=word_progression,dd=dd,typer=typer,quiz_config=quiz_config,current_level=2)
                    LEVEL_2_PASSED = True
                    analytics("set",datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S"),start_time,"level_2_passed")
                    """ daily_stat("set,") """
                    with open("statistics.csv", "r", encoding="UTF-8") as f:
                        correct_counter__ = wrong_counter__ = blank_counter__ = total_counter__ = 0
                        lines = f.readlines()
                        todays=[]
                        for line in lines[::-1]:
                            if datetime.datetime.now().strftime("%Y-%m-%d") in line:
                                if line.strip() not in todays:
                                    todays.append(line.strip())
                        time.sleep(.3)
                        for line in todays:
                            lg(line.split(","))
                            if line.split(",")[5] == "2":
                                """ print(line)
                                print(line.split(","))
                                print(line.split(",")[4])
                                time.sleep(999) """
                                """ print(line.split(",")) """
                                if line.split(",")[4] == "True":
                                    
                                    correct_counter__ += 1
                                    lg(+1)
                                elif line.split(",")[4] == "False":
                                    wrong_counter__ += 1
                                    lg(-1)
                                else: blank_counter__ += 1
                                total_counter__ += 1
                        f.close()
                    lg(correct_counter__,wrong_counter__,blank_counter__,total_counter__)
                    daily_stat("set",correct_counter__,wrong_counter__,blank_counter__,total_counter__,2)

                if LEVEL_1_PASSED == True and LEVEL_2_PASSED == True:
                    print("Tebrikler! Seviye 2'yi de geçtiğiniz tespit edildi! Tüm seviyeleri tamamladınız!")
                    if quiz_config.get("send_telegram_message"):
                        m_ = []
                        with open("daily_stats.csv", "r", encoding="UTF-8") as fg:
                            liness = fg.readlines()
                            for line in liness[::-1]:
                                if datetime.datetime.now().strftime("%Y-%m-%d") in line:
                                    m_.append(line)
                            fg.close()
                        o_ = []
                        if len(m_) == 2:
                            for i in range(1,5):
                                ox = 0
                                for x in m_:
                                    ox += int(x.split(",")[i])
                                o_.append(ox)
                        else:
                            for i in range(1,5):
                                o_.append(int(m_[0].split(",")[i]))
                        lg(o_)
                        print("Sending Report.")
                        if o_[0] == 0: puan = 0; net=0
                        else:
                            net = o_[0]+(-o_[1]-o_[2])*.25
                            if o_[3] != 0:
                                puan = o_[0]/o_[3]*100
                            else: puan = 0
                        tdy = datetime.datetime.now().strftime("%Y-%m-%d")
                        tdy_stats = []
                        with open("statistics.csv","r",encoding="UTF-8") as ff:
                            lineies = ff.readlines()
                            for lime in lineies[::-1]:
                                if tdy in lime:
                                    tdy_stats.append(lime)
                            ff.close()
                        flb = {}
                        for stat in tdy_stats:
                            parts = stat.split(",")
                            key = parts[1]
                            is_success = parts[4] == "True"

                            current_true, current_total = flb.get(key, [0, 0])

                            new_true = current_true + 1 if is_success else current_true
                            new_total = current_total + 1
                            
                            flb[key] = [new_true, new_total]
                        for key,val in flb.items():
                            if val[1] != 0:
                                flb[key] = [val[0],val[1],(val[0]/val[1])*100]
                            else:
                                flb[key] = [val[0],val[1],0]
                        flb = dict(sorted(flb.items(), key=lambda item: item[1][2], reverse=True))
                        lb = ""
                        """ print("hiaa")
                        print(flb)
                        print("hi")
                        time.sleep(999) """
                        for key, a in list(flb.items())[:20]:
                            lb = f"{lb}{key} -> %{a[2]} ({a[0]}/{a[1]})\n"

                        lb2 = ""
                        for key, a in list(flb.items())[-20:]:
                            lb2 = f"{lb2}{key} -> %{a[2]} ({a[0]}/{a[1]})\n"
                        
                        telegram_text = f"📅 Günlük Analiz 📅 ({datetime.datetime.now().strftime("%Y/%m/%d")})\n\nPuan : %{puan:.2f}\nNet : {net:.2f}\n\n✅ Doğru : {o_[0]}\n❌ Yanlış : {o_[1]}\n⚪ Boş : {o_[2]}\n📝 Total Soru Sayısı : {o_[3]}\n\n🏆 Top 20 : \n\n{lb}\n📉 Worst 20 : \n\n{lb2}"
                        try:
                            with open("sent_tg_messages.json","r",encoding="UTF-8") as x:
                                ddt = json.load(x)
                                x.close()
                        except (json.JSONDecodeError, FileNotFoundError):
                            ddt = {}
                        if datetime.datetime.now().strftime("%Y-%m-%d") not in ddt:
                            import telegram_report
                            try:
                                telegram_report.send_telegram_report(telegram_text)
                                with open("sent_tg_messages.json","w",encoding="UTF-8") as h:
                                    ddt[datetime.datetime.now().strftime("%Y-%m-%d")] = telegram_text
                                    json.dump(ddt,h,indent=4)
                                    h.close()
                            except:
                                time.sleep(60)
                                telegram_report.send_telegram_report(telegram_text)
                                with open("sent_tg_messages.json","w",encoding="UTF-8") as h:
                                    ddt[datetime.datetime.now().strftime("%Y-%m-%d")] = telegram_text
                                    json.dump(ddt,h,indent=4)
                                    h.close()
                        if DEBUG:
                            int(input(""))

                    time.sleep(3)
                    cls()
                    main(quiz_config=quiz_config)


if __name__ == "__main__":
    try:
        if "--debug" in sys.argv:
            c_ = ASCII.ASCII_start_menu.main(debug=True)
        else:c_ = ASCII.ASCII_start_menu.main()
        cls()
        leg = False
       
    except Exception as e:
        print(f"An error occurred in start_menu: {e}.\n\n Falling back to legacy start menu.")
        leg = True
        c_ = "play"
    cls()
    try:
        main(legacy_start_menu=leg,mode=c_)
    except KeyboardInterrupt:
        print("Exiting the application")































