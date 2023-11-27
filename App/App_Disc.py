import json
import discogs_client
import csv
from tkinter import simpledialog
from tkinter import messagebox
import webbrowser
from dotenv import load_dotenv
import os

load_dotenv()

consumer_key = os.getenv('discogs_consumer_key')
consumer_secret = os.getenv('discogs_consumer_secret')

print("Discogs key:" + consumer_key)


def import_collection():
    # supply details to the Client class
    d = discogs_client.Client(
        'my_user_agent/1.0', consumer_key=consumer_key, consumer_secret=consumer_secret
    )

    url = d.get_authorize_url()

    print(type(url[2]))  # print url for user to authorize access
    answer = messagebox.askyesno(
        "Discogs Authentication",
        f"To authorize access, please go to {url[2]}. Would you like to open the URL in your web browser?"
    )
    if answer:
        webbrowser.open(url[2])  # Here you can wait for the user to input the code and return it
    else:
        return

    auth_code = simpledialog.askstring(
        "Dicogs Authentication", f"Please click 'Authorize' in the browser and enter the authorization code below. "
    )
    # auth_code = input(code) #prompt user to input the code from url

    d.get_access_token(auth_code)  # pass code for authorization

    print('authorization code "' + auth_code + '" correct!')

    me = d.identity()  # authorized username

    print('user authorized:')
    print(me)

    collection_size = me.collection_folders[0].count
    print("records in collection: " + str(collection_size))

    question_import = messagebox.askyesno(
        "Discogs Authentication",
        f"Authorized {me} succesfully, you have {collection_size} records in your collection. Would you like to import them now?"
    )

    if not question_import:
        return

    # create a list of records in a collection with artist and album title information

    collection = []

    for item in me.collection_folders[0].releases:
        release = {'artist': item.release.fetch('artists')[0]['name'], 'title': item.release.title,
                   'year': item.release.fetch('year')}
        collection.append(release)

    for index, item in enumerate(collection):
        print(index, item)

    export_to_json(collection)
    export_to_csv(collection)

    return collection


def export_to_json(collection, filename="collection_export.json"):
    app_folder = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(app_folder, filename)

    with open(filepath, 'w') as json_file:
        json.dump(collection, json_file, indent=2)


def export_to_csv(list, filename="discogs_collection.csv"):
    #   Append data to csv
    filename = filename
    f = open(filename, 'w+')
    f.close

    try:
        for index, item in enumerate(list):
            with open(filename, 'a', newline='') as f:
                w = csv.writer(f)
                w.writerow(list[index].values())

        f.close

    except:
        pass
