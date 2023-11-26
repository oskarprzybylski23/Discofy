import discogs_client
import csv
from tkinter import simpledialog
from tkinter import messagebox
import webbrowser
from dotenv import load_dotenv
import os

load_dotenv()

consumer_key=os.getenv('discogs_consumer_key')
consumer_secret=os.getenv('discogs_consumer_secret')

print ("Discogs key:" + consumer_key)
def import_collection():
    # supply details to the Client class
    d = discogs_client.Client(
        'my_user_agent/1.0',
        consumer_key=consumer_key,
        consumer_secret=consumer_secret

    )
    url = d.get_authorize_url()



    print(type(url[2])) #print url for user to authorize access

    answer = messagebox.askyesno("Discogs Authentication",
                                 f"To authorize access, please go to {url[2]}. Would you like to open the URL in your web browser?")
    if answer:
        webbrowser.open(url[2])
        # Here you can wait for the user to input the code and return it
    else:
        return

    auth_code = simpledialog.askstring("Dicogs Authentication", f"Please click 'Authorize' in the browser and enter the authorization code below. ")
    # auth_code = input(code) #prompt user to input the code from url

    d.get_access_token(auth_code) #pass code for authorization

    print('authorization code "' + auth_code + '" correct!')

    me = d.identity()  # authorized username

    print('user authorized:')
    print(me)

    collection_size = me.collection_folders[0].count
    print("records in collection: " + str(collection_size))

    question_import = messagebox.askyesno("Discogs Authentication", f"Authorized {me} succesfully, you have {collection_size} records in your collection. Would you like to import them now?")

    if question_import:
        pass
    else:
        return

    # create a list of records in a collection with artist and album title information

    collection = []

    for item in me.collection_folders[0].releases:
        release = {'artist': item.release.fetch('artists')[0]['name'], 'title': item.release.title,
                   'year': item.release.fetch('year')}

        collection.append(release)

    for index, item in enumerate(collection):
        print(index, item)

    #   Export collection contents to a csv file
        #   Create first row
    # with open('discogs_collection.csv', 'a', newline='') as f:
    #     first_row = ["ARTIST", "TITLE", "YEAR"]
    #     w = csv.writer(f)
    #     w.writerow(first_row)
    #     f.close

        #   Append data to csv
    filename = "discogs_collection.csv"
    f = open(filename, 'w+')
    f.close

    try:
        for index, item in enumerate(collection):
            with open(filename, 'a', newline='') as f:
                w = csv.writer(f)
                w.writerow(collection[index].values())

        f.close

        # with open('discogs_collection.csv', 'r') as collection:
        #     reader = csv.reader(collection)
        #
        #     albums = [row[1] for row in reader]
        #     collection.seek(0)
        #     artists = [row[0] for row in reader]
        #     releases = list(zip(artists, albums))



    except:
        pass

    return collection
