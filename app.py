import pandas as pd
import csv
import tweepy
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import numpy as np
import re
import sqlite3
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory

factory = StemmerFactory()
stemmer = factory.create_stemmer()

key = open('key twitter.csv')
key = csv.reader(key, delimiter=',')
token = []
for row in key:
    token.append(row[1])

#token keamanan
consumer_key = token[0]
consumer_secret = token[1]
access_token = token[3]
access_token_secret = token[4]

#inisiasi variabel untuk akses
auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth)

def menu(api):
    print("--------------------------------Menu------------------------")
    print("Apa yang ingin Anda lakukan:")
    print("1. Update Data")
    print("2. Update Nilai Sentiment")
    print("3. Lihat Data")
    print("4. Visualisasi")
    print("5. Keluar")
    print("Input Anda (angka):")
    inp = input()
    try:
        inp = int(inp)
    except:
        print("input Anda bukan angka")

    if (inp == 1):
        update_data(api)
    elif (inp == 2):
        update_nilai_sentimen(api)
    elif(inp == 3):
        lihat_data(api)
    elif (inp == 4):
        visualisasi(api)
    elif (inp == 5):
        keluar()
    else:
        print("angka tidak ada dalam menu")

def update_data(api):
    search_words = "vaksin covid"
    since = datetime.now() + timedelta(days=-1)
    date_since = since.strftime('%Y-%m-%d')
    new_search = search_words + " -filter:retweets"

    tweets = tweepy.Cursor(api.search,
            q=new_search,
            tweet_mode='extended',
            lang="id",
            since=date_since).items(50)
    
    items = []
    for tweet in tweets:
        item = []
        item.append(str(tweet.created_at)[:-8])
        item.append(tweet.user.screen_name)
        item.append (stemmer.stem(' '.join(re.sub("(@[A-Za-z0-9]+)|([^0-9A-Za-z \t])|(\w+:\/\/\S+)", " ", tweet.full_text).split())))
        items.append(item)
    hasil = pd.DataFrame(data=items, columns=['Tanggal', 'username', 'tweet'])
    to_db = [(i,hasil['Tanggal'][i],hasil['username'][i],hasil['tweet'][i]) for i in range(len(hasil))]
    conn = sqlite3.connect('twitter.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS Tweets(id INTEGER PRIMARY KEY NOT NULL, Tanggal TEXT NOT NULL, username TEXT NOT NULL, Tweet TEXT NOT NULL);')
    c.execute('DELETE FROM Tweets')
    c.execute('CREATE TABLE IF NOT EXISTS Tweets(id INTEGER PRIMARY KEY NOT NULL, Tanggal TEXT NOT NULL, username TEXT NOT NULL, Tweet TEXT NOT NULL);')
    c.executemany('INSERT OR IGNORE INTO Tweets(id, Tanggal, username, Tweet) VALUES (?,?,?,?);',to_db)
    conn.commit()
    conn.close()

    print("\n")
    menu(api)

def update_nilai_sentimen(api):
    pos_list= open("kata_positif.txt","r")
    pos_kata = pos_list.readlines()
    neg_list= open("kata_negatif.txt","r")
    neg_kata = neg_list.readlines()

    conn = sqlite3.connect('twitter.db')
    c = conn.cursor()
    c.execute('SELECT * FROM Tweets')
    hasil = c.fetchall()
    c.close()
    conn.commit()
    conn.close()

    S = []
    for item in hasil:
        count_p = 0
        count_n = 0
        for kata_pos in pos_kata:
            if kata_pos.strip() in item[3]:
                count_p +=1
        for kata_neg in neg_kata:
            if kata_neg.strip() in item[3]:
                count_n +=1
        # print ("positif: "+str(count_p))
        # print ("negatif: "+str(count_n))
        S.append(count_p - count_n)

    to_db = [(hasil[i][0], S[i]) for i in range(len(S))]
    conn = sqlite3.connect('twitter.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS Sentiment(id INTEGER PRIMARY KEY NOT NULL, Sentiment INTEGER NOT NULL);')
    c.execute('DELETE FROM Sentiment')
    c.execute('CREATE TABLE IF NOT EXISTS Sentiment(id INTEGER PRIMARY KEY NOT NULL, Sentiment INTEGER NOT NULL);')
    c.executemany('INSERT OR IGNORE INTO Sentiment(id, Sentiment) VALUES (?, ?);',to_db)
    conn.commit()
    conn.close()

    print("\n")
    menu(api)

def lihat_data(api):
    awal = input("Tanggal Awal  (format: 2020-04-24) : ")
    akhir= input("Tanggal Akhir (format: 2020-04-24) : ")
    conn = sqlite3.connect('twitter.db')
    c = conn.cursor()
    c.execute('SELECT * FROM Tweets')
    hasil = c.fetchall()
    c.close()
    conn.commit()
    conn.close()

    df = pd.DataFrame(hasil, columns=['id','Tanggal','username','Tweet'])
    df['Tanggal'] = pd.to_datetime(df['Tanggal'])

    i = 0
    for h in hasil:
        if(datetime.strptime(awal, '%Y-%m-%d') <= df['Tanggal'][i] and datetime.strptime(akhir, '%Y-%m-%d') >= df['Tanggal'][i]):
            print("-----------------------------------------------------------")
            print("Tanggal  : " + h[1])
            print("Username : " + h[2])
            print("Tweet    : " + h[3])
        i+=1
    menu(api)

def visualisasi(api):
    awal = input("Tanggal Awal  (format: 2020-04-24) : ")
    akhir= input("Tanggal Akhir (format: 2020-04-24) : ")

    conn = sqlite3.connect('twitter.db')
    c = conn.cursor()
    c.execute('SELECT * FROM Sentiment')
    hasil = c.fetchall()
    c.close()
    conn.commit()
    conn.close()

    conn = sqlite3.connect('twitter.db')
    c = conn.cursor()
    c.execute('SELECT id, Tanggal FROM Tweets')
    tgl = c.fetchall()
    c.close()
    conn.commit()
    conn.close()

    df = pd.DataFrame(tgl, columns=['id','Tanggal'])
    df['Tanggal'] = pd.to_datetime(df['Tanggal'])
    list_id = []
    i = 0
    for t in tgl:
        if(datetime.strptime(awal, '%Y-%m-%d') <= df['Tanggal'][i] and datetime.strptime(akhir, '%Y-%m-%d') >= df['Tanggal'][i]):
            list_id.append(t[0])
            i+=1

    sent = [hasil[i][1]  for i in range(len(hasil)) if hasil[i][0] in list_id]
    df_sent = pd.DataFrame(sent, columns=['Sentiment'])

    print ("Nilai rata-rata: "+str(np.mean(df_sent["Sentiment"])))
    print ("Nilai tengah   : "+str(np.median(df_sent["Sentiment"])))
    print ("Standar deviasi: "+str(np.std(df_sent["Sentiment"])))

    labels, counts = np.unique(df_sent["Sentiment"], return_counts=True)
    plt.bar(labels, counts, align='center', color='lightblue')
    plt.xlabel("Nilai Sentiment")
    plt.ylabel("Banyak Tweet")
    plt.title("Sentiment Warga Twitter terhadap Topik 'Vaksin Covid'")
    plt.gca().set_xticks(labels)
    plt.show()

    print("\n")
    menu(api)

def keluar():
    exit()

menu(api)

