from tkinter import *
from tkinter import messagebox
from tkinter import simpledialog
import App_Disc
import App_Spot
from App_Disc import import_collection


window=Tk()
window.geometry("800x400")
window.resizable(False, False)
window.wm_title("Discogs to Spotify Exporter")

def get_collection():
    output = App_Disc.import_collection()

    for album in output:
        list1.insert(END, album)
def view_collection():
    pass
def see_report():
    App_Spot.see_report()
def create_playlist():
    App_Spot.create_playlist()

# Create labels

l1=Label(window, text="Discofy - Discogs to Spotify Collection Exporter", bd=2, )
l1.grid(row=0, column=0, padx=10, pady=10)

# Create list section with a scrollbar

list_frame = Frame(window, bg='white')
list_frame.grid(row=3, column=1, rowspan=20, columnspan=7, padx=10, pady=10)

l3=Label(list_frame, text="Albums in Collection")
l3.grid(row=0, column=2, padx=10, pady=10, sticky=N)

list1=Listbox(list_frame, height=15, width=70)
list1.grid(row=1, column=0, rowspan=6, columnspan=5, sticky=N+S+E+W)

sb1 = Scrollbar(list_frame)
sb1.grid(row=1, column=5, rowspan=6, sticky=N+S)
list1.config(yscrollcommand=sb1.set)
sb1.config(command=list1.yview)

sb2=Scrollbar(list_frame, orient=HORIZONTAL)
sb2.grid(row=7, column=0, columnspan=5, sticky=E+W)
list1.config(xscrollcommand=sb2.set)
sb2.config(command=list1.xview)

# Create buttons

button_frame = Frame(window)
button_frame.grid(row=3, column=0, rowspan=3, padx=10, pady=10)

b1=Button(button_frame, text="Import Collection", width=15, command=get_collection)
b1.grid(row=2, column=1, padx=10, pady=10)

b2=Button(button_frame, text="Create Playlist", width=15, command=create_playlist)
b2.grid(row=3, column=1, padx=10, pady=10)

b3=Button(button_frame, text="See Report", width=15, command=see_report)
b3.grid(row=4, column=1, padx=10, pady=10)

b4=Button(button_frame, text="Close", width=15, command=window.destroy)
b4.grid(row=5, column=1, padx=10, pady=10)

# add some style
window.configure(bg="#282828")
button_frame.configure(bg="#282828")
list_frame.configure(bg="#282828")
l1.configure(bg="#282828", fg="white")
l3.configure(bg="#282828", fg="white")
list1.configure(bg="#282828", fg="white", highlightbackground="#1DB954", highlightcolor="#1DB954", selectbackground="#1DB954", selectforeground="white")
sb1.configure(bg="#282828", activebackground="#1DB954")

window.mainloop()