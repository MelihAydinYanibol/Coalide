from cobjects.word import Word,_tr_lower
from cobjects.question import Question
import random
import os
import sys

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

def load_words(file_path: str = "words.csv") -> list[Word]:
    """
    Parse words.csv into a list of Word objects.

    Backward compatible: rows with the original 5 columns parse fine
    (past/v3 default to ""); rows with 6 or 7 columns also populate
    past/v3. Malformed rows (<5 columns) are skipped, matching the
    existing load_words() behavior in main.py.
    """
    words: list[Word] = []
    with open(file_path, "r", encoding="UTF-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 5:
                continue
            words.append(Word.from_csv_row(parts))
    return words

def quest(question: Question, quest_num=1) -> bool | str:
    """
    Ask a single question, return True if the answer is correct, False
    if wrong, and "blank" if the user didn't type anything or timed
    out. The OOP version of the original quest() function in main.py.
    """
    print(f"Örnek Cümle: ")
    print(f"{quest_num}. '{question.prompt}' kelimesinin {"Türkçe karşılığı" if question.is_source else "İngilizce Karşılığı"} nedir?\n")
    answer = input("> ")
    ev = Question.evaluate(question, answer)
    if ev is True:
        print("Doğru!")
    elif ev is False:
        if _tr_lower(answer) in Question.expected_word_alternatives(question):
            print(f"Doğru bir cevap! ama başka bir alternatif var!")
            input("Tekrar Dene! Devam etmek için Enter'a basın...")
            quest(question, quest_num)
        print(f"Yanlış! Doğru cevap: {question.expected_answer}")
    else:print(f"Boş cevap! Doğru cevap: {question.expected_answer}")
    input("Devam etmek için Enter'a basın...")
    Question.save_to_stats(question, answer, level=0)

question_number = 1
while True:
    os.system('cls')
    question = Question.random(random.choice(load_words()))
    quest(Question(Word("class","sınıf","name",("sa","as"),expected_word_alternatives=["ders"]),False,112), question_number)
    question_number += 1
