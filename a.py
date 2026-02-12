import time;import datetime;import os

def daily_stat(get_set, correct, wrong, blank, total,level):
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
    

with open("statistics.csv", "r", encoding="UTF-8") as f:
    correct_counter__ = wrong_counter__ = blank_counter__ = total_counter__ = 0
    lines = f.readlines()
    todays=[]
    for line in lines[::-1]:
        print(line)
        if datetime.datetime.now().strftime("%Y-%m-%d") in line:
            if line.strip() not in todays:
                todays.append(line.strip())
    time.sleep(.3)
    print(todays)
    for line in todays:
        print(line)
        if line.split(",")[5] == "2":
            print(line)
            """ print(line)
            print(line.split(","))
            print(line.split(",")[4])
            time.sleep(999) """
            """ print(line.split(",")) """
            if line.split(",")[4] == "True":
                
                correct_counter__ += 1
            elif line.split(",")[4] == "False":
                wrong_counter__ += 1
            else: blank_counter__ += 1
            total_counter__ += 1
    f.close()
daily_stat("set",correct_counter__,wrong_counter__,blank_counter__,total_counter__,2)